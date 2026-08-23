"""Validate curated records and discover new SSP meetings for human review.

Published records are never generated automatically. New meetings are appended to
data/assembly_records_inbox.json with ``pending_review`` status so an inaccurate
summary cannot reach the public API.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import requests


ROOT = Path(__file__).resolve().parents[1]
RECORDS_PATH = ROOT / "data" / "assembly_records.json"
INBOX_PATH = ROOT / "data" / "assembly_records_inbox.json"
SSP_API_ROOT = "https://ssp.kaigiroku.net/dnp/search"


def load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.exists() and default is not None:
        return default
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def validate_dataset(dataset: Dict[str, Any]) -> None:
    if dataset.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")

    discussion_ids: Set[str] = set()
    statement_ids: Set[str] = set()
    for assembly_id, assembly in dataset.get("assemblies", {}).items():
        records = assembly.get("records", [])
        dates = [record.get("meeting_date", "") for record in records]
        if dates != sorted(dates, reverse=True):
            raise ValueError(f"{assembly_id}: records must be newest first")
        for record in records:
            discussion_id = record["discussion_id"]
            if discussion_id in discussion_ids:
                raise ValueError(f"Duplicate discussion_id: {discussion_id}")
            discussion_ids.add(discussion_id)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["meeting_date"]):
                raise ValueError(f"Invalid meeting_date: {record['meeting_date']}")
            for statement in record.get("statements", []):
                statement_id = statement["statement_id"]
                if statement_id in statement_ids:
                    raise ValueError(f"Duplicate statement_id: {statement_id}")
                statement_ids.add(statement_id)


def parse_jsonp(body: str) -> Dict[str, Any]:
    start = body.find("(")
    end = body.rfind(")")
    if start < 0 or end <= start:
        raise ValueError("Invalid JSONP response")
    return json.loads(body[start + 1:end])


def ssp_post(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(
        f"{SSP_API_ROOT}/{endpoint}",
        params={"callback": "gijiraku"},
        data=data,
        timeout=30,
        headers={"User-Agent": "MachiVoice assembly-record-discovery/1.0"},
    )
    response.raise_for_status()
    return parse_jsonp(response.text)


def iter_latest_ssp_councils(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    years: List[Dict[str, Any]] = []
    for group in payload.get("councils", []):
        years.extend(group.get("view_years", []))
    if not years:
        return []
    latest_year = max(int(year["view_year"]) for year in years)

    councils: List[Dict[str, Any]] = []
    for year in years:
        if int(year["view_year"]) != latest_year:
            continue
        for council_type in year.get("council_type", []):
            if council_type.get("council_type_name2") != "本会議":
                continue
            councils.extend(council_type.get("councils", []))
    return councils


def discover_ssp(assembly_id: str, source: Dict[str, Any]) -> List[Dict[str, Any]]:
    tenant_id = source["tenant_id"]
    tenant = source["tenant"]
    councils_payload = ssp_post("councils/index", {"tenant_id": tenant_id})
    candidates: List[Dict[str, Any]] = []
    for council in iter_latest_ssp_councils(councils_payload):
        council_id = council["council_id"]
        schedules_payload = ssp_post(
            "minutes/get_schedule",
            {"tenant_id": tenant_id, "council_id": council_id},
        )
        schedules = [
            {
                "schedule_id": schedule["schedule_id"],
                "name": schedule["name"],
                "source_url": (
                    f"https://ssp.kaigiroku.net/tenant/{tenant}/SpMinuteView.html"
                    f"?council_id={council_id}&schedule_id={schedule['schedule_id']}"
                ),
            }
            for schedule in schedules_payload.get("council_schedules", [])
        ]
        candidates.append(
            {
                "external_id": f"ssp:{tenant}:{council_id}",
                "assembly_id": assembly_id,
                "meeting_name": council["name"],
                "publication_status": "pending_review",
                "schedules": schedules,
            }
        )
    return candidates


def discover(dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for assembly_id, assembly in dataset["assemblies"].items():
        source = assembly.get("source", {})
        if source.get("provider") == "ssp":
            published_urls = [record.get("source_url", "") for record in assembly.get("records", [])]
            for candidate in discover_ssp(assembly_id, source):
                council_id = candidate["external_id"].rsplit(":", 1)[-1]
                if any(f"council_id={council_id}" in url for url in published_urls):
                    continue
                candidates.append(candidate)
    return sorted(candidates, key=lambda item: item["external_id"])


def update_inbox(candidates: List[Dict[str, Any]]) -> bool:
    current = load_json(INBOX_PATH, {"schema_version": 1, "candidates": []})
    current_by_id = {item["external_id"]: item for item in current.get("candidates", [])}
    now = datetime.now(timezone.utc).isoformat()

    merged_by_id = dict(current_by_id)
    for candidate in candidates:
        previous = current_by_id.get(candidate["external_id"], {})
        merged_by_id[candidate["external_id"]] = {
            **candidate,
            "first_seen_at": previous.get("first_seen_at", now),
        }

    next_payload = {
        "schema_version": 1,
        "candidates": [merged_by_id[key] for key in sorted(merged_by_id)],
    }
    if current == next_payload:
        return False

    temporary = INBOX_PATH.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(next_payload, target, ensure_ascii=False, indent=2)
        target.write("\n")
    temporary.replace(INBOX_PATH)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    dataset = load_json(RECORDS_PATH)
    validate_dataset(dataset)
    if args.check_only:
        print("assembly_records.json: OK")
        return

    changed = update_inbox(discover(dataset))
    print("assembly_records_inbox.json: updated" if changed else "assembly_records_inbox.json: unchanged")


if __name__ == "__main__":
    main()

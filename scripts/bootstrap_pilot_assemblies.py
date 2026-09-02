"""Bootstrap pilot assembly coverage from SSP tenant metadata."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
RECORDS_PATH = ROOT / "data" / "assembly_records.json"
PILOT_PATH = ROOT / "data" / "pilot_assembly_sources.json"
JST = timezone(timedelta(hours=9))


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2)
        target.write("\n")
    temporary.replace(path)


def resolve_tenant_id(tenant: str) -> int | None:
    response = requests.get(
        f"https://ssp.kaigiroku.net/tenant/{tenant}/js/tenant.js",
        timeout=20,
    )
    if response.status_code != 200:
        return None
    match = re.search(r"tenant_id\s*=\s*(\d+)", response.text)
    return int(match.group(1)) if match else None


def assembly_block(entry: dict) -> dict:
    tenant_id = entry.get("tenant_id") or resolve_tenant_id(entry["tenant"])
    if tenant_id is None:
        raise ValueError(f"Could not resolve tenant_id for {entry['assembly_id']}")
    code = entry["open_data_code"]
    resource_url = entry["resource_url"]
    return {
        "assembly_name": entry["assembly_name"],
        "source": {
            "provider": "ssp",
            "tenant": entry["tenant"],
            "tenant_id": tenant_id,
            "index_url": f"https://ssp.kaigiroku.net/tenant/{entry['tenant']}/SpTop.html",
            "open_data": {
                "title": "議会だより",
                "catalog_url": f"https://catalog.data.metro.tokyo.lg.jp/dataset/t{code}d2024000001",
                "resource_url": resource_url,
                "format": "CSV",
                "license_id": "CC-BY-4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/deed.ja",
                "usage": "議会刊行物の発行年月と原典URLの確認",
            },
        },
        "records": [],
    }


def ensure_pilot_assemblies() -> list[str]:
    pilot = load_json(PILOT_PATH)
    dataset = load_json(RECORDS_PATH)
    added: list[str] = []
    for entry in pilot["assemblies"]:
        assembly_id = entry["assembly_id"]
        if assembly_id in dataset["assemblies"]:
            continue
        dataset["assemblies"][assembly_id] = assembly_block(entry)
        added.append(assembly_id)
    if added:
        dataset["updated_at"] = datetime.now(JST).replace(microsecond=0).isoformat()
        write_json(RECORDS_PATH, dataset)
    return added


def main() -> int:
    added = ensure_pilot_assemblies()
    print(f"Added assemblies: {added or 'none'}")
    if "--skip-crawl" in sys.argv:
        return 0
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "update_assembly_records.py"),
            "--auto-publish",
            "--max-records-per-assembly",
            "40",
            "--ssp-years",
            "3",
        ],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

"""Discover and safely ingest official assembly records.

The scheduled job auto-publishes only extractive records: dates, speakers and
excerpts come directly from the official transcript. No generative summary is
created, so the crawler cannot invent a person, number or policy statement.
Schedules that cannot be parsed or verified remain in the review inbox.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import requests


ROOT = Path(__file__).resolve().parents[1]
RECORDS_PATH = ROOT / "data" / "assembly_records.json"
INBOX_PATH = ROOT / "data" / "assembly_records_inbox.json"
SSP_API_ROOT = "https://ssp.kaigiroku.net/dnp/search"
JST = timezone(timedelta(hours=9))


def load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.exists() and default is not None:
        return default
    with path.open(encoding="utf-8") as source:
        return json.load(source)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(payload, target, ensure_ascii=False, indent=2)
        target.write("\n")
    temporary.replace(path)


def clean_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalize_digits(value: str) -> str:
    return value.translate(str.maketrans("０１２３４５６７８９", "0123456789"))


def parse_meeting_date(
    council_name: str,
    schedule_name: str,
    minutes: List[Dict[str, Any]],
    schedule_metadata: str = "",
) -> Optional[str]:
    transcript = " ".join(
        [clean_html(schedule_metadata)]
        + [clean_html(item.get("body", "")) for item in minutes[:3]]
    )
    normalized = normalize_digits(transcript)
    gregorian = re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日", normalized)
    if gregorian:
        year, month, day = map(int, gregorian.groups())
        return f"{year:04d}-{month:02d}-{day:02d}"

    japanese_date = re.search(
        r"令和\s*(\d+)年\s*(\d{1,2})月\s*(\d{1,2})日",
        normalized,
    )
    if japanese_date:
        japanese_year, month, day = map(int, japanese_date.groups())
        return f"{2018 + japanese_year:04d}-{month:02d}-{day:02d}"

    council = normalize_digits(council_name)
    schedule = normalize_digits(schedule_name)
    japanese_year = re.search(r"令和\s*(\d+)年", council)
    month_day = re.search(r"(\d{1,2})月\s*(\d{1,2})日", schedule)
    if japanese_year and month_day:
        year = 2018 + int(japanese_year.group(1))
        month, day = map(int, month_day.groups())
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def remove_speaker_prefix(value: str) -> str:
    return re.sub(
        r"^[◆◎○△]?(?:[^（）\s]{1,50}（[^）]+）|【[^】]+】)\s+",
        "",
        value,
    ).strip()


def excerpt(value: str, limit: int) -> str:
    value = remove_speaker_prefix(clean_html(value))
    return value if len(value) <= limit else value[:limit].rstrip()


def extract_topic(question: str) -> Optional[str]:
    text = remove_speaker_prefix(question)
    for sentence in re.split(r"[。\n]", text[:1200]):
        if "について" not in sentence or not any(
            word in sentence
            for word in ("質問", "伺", "お尋ね", "提案", "討論", "報告")
        ):
            continue
        topic = sentence.split("について", 1)[0]
        topic = re.sub(
            r"^.*?(?:まず初めは|まずは|まず|初めに|次に|続いて|それでは次に)[、，]?\s*",
            "",
            topic,
        ).strip(" 、，『』「」")
        if 2 <= len(topic) <= 100:
            return topic

    for sentence in re.split(r"[。\n]", text[:1200]):
        debate = re.search(r"(.{2,100}?)に(?:賛成|反対)の立場で討論", sentence)
        if debate:
            return debate.group(1).strip(" 、，『』「」")
    return None


def speaker_from_title(title: str, assembly_name: str, is_answer: bool) -> Dict[str, str]:
    title = clean_html(title).lstrip("◆◎○△")
    match = re.search(r"（([^）]+)）", title)
    if match:
        speaker_name = re.sub(r"(?:君|議員)$", "", match.group(1).strip())
        office = title[:match.start()].strip()
    else:
        bracketed = re.search(r"【([^】]+)】", title)
        raw = bracketed.group(1).strip() if bracketed else title
        raw = re.sub(r"^\d+番", "", raw)
        office_match = re.match(r"(.+?)(議員|区長|市長|教育長|部長|局長|次長)$", raw)
        speaker_name = raw
        office = ""
        if office_match and office_match.group(2) != "議員":
            speaker_name = office_match.group(1)
            office = office_match.group(2)

    municipality = assembly_name.removesuffix("議会")
    if not is_answer:
        role = f"{assembly_name}議員"
    elif office.startswith(("区", "市")) and municipality.endswith(office[0]):
        role = f"{municipality[:-1]}{office}"
    elif office:
        role = f"{municipality}{office}"
    else:
        role = f"{municipality}行政執行部"
    return {"speaker_name": speaker_name, "speaker_role": role}


def validate_dataset(dataset: Dict[str, Any]) -> None:
    if dataset.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")

    discussion_ids: Set[str] = set()
    statement_ids: Set[str] = set()
    for assembly_id, assembly in dataset.get("assemblies", {}).items():
        open_data = assembly.get("source", {}).get("open_data")
        if not isinstance(open_data, dict):
            raise ValueError(f"{assembly_id}: open_data source is required")
        for key in ("catalog_url", "resource_url", "format", "license_id", "license_url", "usage"):
            if not open_data.get(key):
                raise ValueError(f"{assembly_id}: open_data.{key} is required")
        if open_data["license_id"] != "CC-BY-4.0":
            raise ValueError(f"{assembly_id}: unsupported open data license")

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


def discover_ssp(
    assembly_id: str,
    source: Dict[str, Any],
) -> List[Dict[str, Any]]:
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
        for schedule in schedules_payload.get("council_schedules", []):
            schedule_id = schedule["schedule_id"]
            source_url = (
                f"https://ssp.kaigiroku.net/tenant/{tenant}/SpMinuteView.html"
                f"?council_id={council_id}&schedule_id={schedule_id}"
            )
            candidates.append(
                {
                    "external_id": f"ssp:{tenant}:{council_id}:{schedule_id}",
                    "provider": "ssp",
                    "assembly_id": assembly_id,
                    "council_id": council_id,
                    "schedule_id": schedule_id,
                    "meeting_name": council["name"],
                    "schedule_name": schedule["name"],
                    "schedule_metadata": clean_html(
                        schedule.get("member_list", "")
                    )[:1000],
                    "source_url": source_url,
                    "publication_status": "pending_review",
                }
            )
    return candidates


def discover(dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for assembly_id, assembly in dataset["assemblies"].items():
        source = assembly.get("source", {})
        if source.get("provider") == "ssp":
            candidates.extend(discover_ssp(assembly_id, source))
    return sorted(candidates, key=lambda item: item["external_id"])


def build_ssp_records(
    dataset: Dict[str, Any],
    candidate: Dict[str, Any],
    max_records: int,
) -> List[Dict[str, Any]]:
    assembly_id = candidate["assembly_id"]
    assembly = dataset["assemblies"][assembly_id]
    source = assembly["source"]
    payload = ssp_post(
        "minutes/get_minute",
        {
            "tenant_id": source["tenant_id"],
            "council_id": candidate["council_id"],
            "schedule_id": candidate["schedule_id"],
        },
    )
    minutes = payload.get("tenant_minutes", [])
    meeting_date = parse_meeting_date(
        candidate["meeting_name"],
        candidate["schedule_name"],
        minutes,
        candidate.get("schedule_metadata", ""),
    )
    if not meeting_date:
        candidate["review_reason"] = "meeting_date_not_found"
        return []

    transcript = " ".join(clean_html(item.get("body", "")) for item in minutes)
    records: List[Dict[str, Any]] = []
    for index, minute in enumerate(minutes):
        if minute.get("minute_type_code") != 5:
            continue
        question_text = clean_html(minute.get("body", ""))
        topic = extract_topic(question_text)
        if not topic or len(question_text) < 40:
            continue

        answers: List[Dict[str, Any]] = []
        for following in minutes[index + 1:]:
            if following.get("minute_type_code") != 6:
                break
            answer_text = clean_html(following.get("body", ""))
            if len(answer_text) >= 20:
                answers.append(following)

        import_id = (
            f"ssp:{source['tenant']}:{candidate['council_id']}:"
            f"{candidate['schedule_id']}:{minute['minute_id']}"
        )
        question_excerpt = excerpt(minute.get("body", ""), 180)
        if question_excerpt not in transcript:
            continue
        question_speaker = speaker_from_title(
            minute.get("title", ""), assembly["assembly_name"], False
        )
        statements: List[Dict[str, Any]] = [
            {
                "statement_id": f"{assembly_id}-auto-{meeting_date}-{candidate['council_id']}-{candidate['schedule_id']}-{minute['minute_id']}-q",
                **question_speaker,
                "committee_name": "本会議",
                "stance_label": "質問" if answers else "議員発言",
                "summary_quote": f"【公式原文抜粋】{question_excerpt}",
                "full_summary": (
                    "公式会議録から自動抽出した発言です。AIによる要約ではありません。"
                    f" 原文冒頭: {excerpt(minute.get('body', ''), 420)}"
                ),
                "source_excerpt": question_excerpt,
                "question_type": "本会議質問" if answers else "本会議発言",
                "avatar_color": "sky",
            }
        ]
        for answer in answers[:4]:
            answer_excerpt = excerpt(answer.get("body", ""), 180)
            if answer_excerpt not in transcript:
                continue
            answer_speaker = speaker_from_title(
                answer.get("title", ""), assembly["assembly_name"], True
            )
            statements.append(
                {
                    "statement_id": f"{assembly_id}-auto-{meeting_date}-{candidate['council_id']}-{candidate['schedule_id']}-{answer['minute_id']}-a",
                    **answer_speaker,
                    "party_name": "行政執行部",
                    "committee_name": "本会議・答弁",
                    "stance_label": "答弁",
                    "summary_quote": f"【公式原文抜粋】{answer_excerpt}",
                    "full_summary": (
                        "公式会議録から自動抽出した発言です。AIによる要約ではありません。"
                        f" 原文冒頭: {excerpt(answer.get('body', ''), 420)}"
                    ),
                    "source_excerpt": answer_excerpt,
                    "question_type": "行政答弁",
                    "avatar_color": "emerald",
                }
            )
        meeting_name = f"{candidate['meeting_name']} {candidate['schedule_name']}"
        proceeding = "質問と答弁" if answers else "議員発言"
        records.append(
            {
                "discussion_id": f"{assembly_id}-auto-{meeting_date}-{candidate['council_id']}-{candidate['schedule_id']}-{minute['minute_id']}",
                "meeting_date": meeting_date,
                "meeting_name": re.sub(r"\s+", " ", meeting_name).strip(),
                "source_url": candidate["source_url"],
                "source_import_id": import_id,
                "ingestion_method": "official-transcript-extractive-v1",
                "topic": topic,
                "what_changes": f"「{topic}」について、本会議で{proceeding}が行われました。",
                "target_audience": f"この議題に関心のある{assembly['assembly_name'].removesuffix('議会')}の住民",
                "current_stage": f"{meeting_date}の本会議で{proceeding}済み",
                "budget_info": "予算・数値はリンク先の公式会議録原文を参照",
                "original_quote": f"「{excerpt(minute.get('body', ''), 120)}」",
                "publication_status": "published",
                "statements": statements,
            }
        )
        if len(records) >= max_records:
            break
    if not records:
        candidate["review_reason"] = "verified_question_answer_pair_not_found"
    return records


def auto_publish(
    dataset: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    max_records_per_assembly: int,
) -> int:
    changed = 0
    added_by_assembly: Dict[str, int] = {}
    existing_import_ids = {
        record.get("source_import_id")
        for assembly in dataset["assemblies"].values()
        for record in assembly.get("records", [])
        if record.get("source_import_id")
    }
    existing_by_import_id = {
        record["source_import_id"]: record
        for assembly in dataset["assemblies"].values()
        for record in assembly.get("records", [])
        if record.get("source_import_id")
    }
    curated_source_topics = {
        (record.get("source_url", ""), re.sub(r"\s+", "", record.get("topic", "")))
        for assembly in dataset["assemblies"].values()
        for record in assembly.get("records", [])
        if (
            record.get("source_url")
            and record.get("topic")
            and not record.get("source_import_id")
        )
    }
    for candidate in candidates:
        assembly_id = candidate["assembly_id"]
        remaining = max_records_per_assembly - added_by_assembly.get(assembly_id, 0)
        if remaining <= 0 or candidate.get("provider") != "ssp":
            continue
        records: List[Dict[str, Any]] = []
        for record in build_ssp_records(dataset, candidate, 1000):
            import_id = record.get("source_import_id")
            existing = existing_by_import_id.get(import_id)
            if existing is not None:
                if existing != record:
                    existing.clear()
                    existing.update(record)
                    changed += 1
                continue
            source_topic = (
                record.get("source_url", ""),
                re.sub(r"\s+", "", record.get("topic", "")),
            )
            if record.get("source_import_id") in existing_import_ids:
                continue
            if source_topic in curated_source_topics:
                continue
            records.append(record)
            if len(records) >= remaining:
                break
        if not records:
            continue
        dataset["assemblies"][assembly_id].setdefault("records", []).extend(records)
        dataset["assemblies"][assembly_id]["records"].sort(
            key=lambda record: record.get("meeting_date", ""), reverse=True
        )
        for record in records:
            existing_import_ids.add(record["source_import_id"])
            existing_by_import_id[record["source_import_id"]] = record
        changed += len(records)
        added_by_assembly[assembly_id] = added_by_assembly.get(assembly_id, 0) + len(records)
        candidate["publication_status"] = "published"
        candidate["auto_published_records"] = len(records)

    if changed:
        for assembly in dataset["assemblies"].values():
            assembly.get("records", []).sort(
                key=lambda record: record.get("meeting_date", ""),
                reverse=True,
            )
        dataset["updated_at"] = datetime.now(JST).replace(microsecond=0).isoformat()
    return changed


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

    write_json(INBOX_PATH, next_payload)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--auto-publish", action="store_true")
    parser.add_argument("--max-records-per-assembly", type=int, default=50)
    args = parser.parse_args()

    dataset = load_json(RECORDS_PATH)
    validate_dataset(dataset)
    if args.check_only:
        print("assembly_records.json: OK")
        return

    candidates = discover(dataset)
    changed_records = 0
    if args.auto_publish:
        if args.max_records_per_assembly < 1:
            raise ValueError("--max-records-per-assembly must be at least 1")
        changed_records = auto_publish(dataset, candidates, args.max_records_per_assembly)
        validate_dataset(dataset)
        if changed_records:
            write_json(RECORDS_PATH, dataset)

    changed = update_inbox(candidates)
    print(f"assembly_records.json: {changed_records} added/refreshed record(s)")
    print("assembly_records_inbox.json: updated" if changed else "assembly_records_inbox.json: unchanged")


if __name__ == "__main__":
    main()

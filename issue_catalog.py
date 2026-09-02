"""Build a compact, validated catalog from source-verified assembly records."""

from __future__ import annotations

import re
from collections import Counter
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from assembly_records import load_dataset
from catalog_metadata import VERIFIED_EXTRACTIVE_ISSUE_IDS, public_title
from citizen_question_store import QUESTION_DEFINITIONS


# Extractive records are public only when manually reviewed or when a strict
# source-matching gate proves that one compact topic occurs in both the
# question and its single corresponding administrative answer.
AUTO_PUBLIC_TOPIC_BOILERPLATE = re.compile(
    r"議案第|第.{0,3}号議案|議題とな|討論|大きく.{0,5}項目|質問.{0,4}中で|"
    r"^(?:続きまして|最後に|また[、，]|そこで[、，]|私は[、，]|初めに[、，]|"
    r"最初に[、，]|今回は|本日|ちょっと|あと[、，])"
)
THEMES = (
    ("children", "子育て・教育", ("子ども", "子育て", "保育", "学校", "教育", "教員", "いじめ", "若者", "学習")),
    ("digital", "行政DX・AI", ("DX", "ＡＩ", "AI", "デジタル", "アプリ", "マイナンバー", "EBPM", "エビデンス")),
    ("health", "医療・福祉", ("医療", "福祉", "介護", "健康", "ワクチン", "熱中症", "孤独死", "合理的配慮")),
    ("housing", "住まい・まちづくり", ("住宅", "家賃", "空き家", "再開発", "まちづくり", "民泊")),
    ("transport", "交通", ("交通", "自転車", "バス", "移動")),
    ("economy", "暮らし・経済", ("物価", "給付", "雇用", "予算", "通貨", "費用", "負担")),
    ("safety", "防災・安全", ("防災", "災害", "避難", "安全", "防犯")),
    ("community", "地域・環境", ("地域", "町会", "自治会", "ごみ", "環境", "猫", "路上")),
)


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _question_by_issue() -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for question_id, definition in QUESTION_DEFINITIONS.items():
        if definition.get("test_only"):
            continue
        issue_id = definition["issue_id"]
        if issue_id in result:
            raise ValueError(f"Multiple public questions for issue_id: {issue_id}")
        result[issue_id] = {"question_id": question_id, **definition}
    return result


def classify_theme(record: Dict[str, Any]) -> Dict[str, str]:
    text = " ".join(
        public_title(record) if key == "topic" else str(record.get(key, ""))
        for key in ("topic", "what_changes", "target_audience", "budget_info")
    )
    for theme_id, label, keywords in THEMES:
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return {"id": theme_id, "label": label}
    return {"id": "administration", "label": "行政・議会"}


def normalize_stage(value: str) -> str:
    if "答弁済み" in value:
        return "答弁済み"
    if "議員発言済み" in value or "討論" in value:
        return "審議中"
    if "実施" in value or "開始" in value:
        return "実施中"
    return "対応確認中"


def _compact_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def is_source_matched_extractive(record: Dict[str, Any]) -> bool:
    """Accept only an unambiguous one-question/one-answer official excerpt."""
    if record.get("ingestion_method") != "official-transcript-extractive-v1":
        return False
    if not str(record.get("source_import_id", "")).startswith("ssp:"):
        return False
    if urlparse(str(record.get("source_url", ""))).hostname != "ssp.kaigiroku.net":
        return False

    topic = str(record.get("topic", "")).strip()
    if not 6 <= len(topic) <= 60 or AUTO_PUBLIC_TOPIC_BOILERPLATE.search(topic):
        return False
    statements = record.get("statements", [])
    if not isinstance(statements, list) or len(statements) != 2:
        return False
    question, answer = statements
    if question.get("stance_label") != "質問" or answer.get("stance_label") != "答弁":
        return False
    if not all(
        str(statement.get("summary_quote", "")).startswith("【公式原文抜粋】")
        for statement in statements
    ):
        return False

    compact_topic = _compact_text(topic)
    return all(
        compact_topic in _compact_text(statement.get("source_excerpt"))
        for statement in statements
    )


def is_catalog_eligible(record: Dict[str, Any]) -> bool:
    issue_id = str(record.get("discussion_id", ""))
    return (
        record.get("publication_status") == "published"
        and (
            "-auto-" not in issue_id
            or issue_id in VERIFIED_EXTRACTIVE_ISSUE_IDS
            or is_source_matched_extractive(record)
        )
    )


def validate_issue_catalog(dataset: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fail closed when list/detail/source relationships are incomplete."""
    source = dataset or load_dataset()
    questions = _question_by_issue()
    issue_ids: set[str] = set()
    statement_ids: set[str] = set()
    counts: Counter[str] = Counter()
    errors: List[str] = []

    for assembly_id, assembly in source["assemblies"].items():
        open_data = assembly.get("source", {}).get("open_data") or {}
        for record in assembly.get("records", []):
            if not is_catalog_eligible(record):
                continue
            issue_id = str(record.get("discussion_id", ""))
            prefix = f"{assembly_id}/{issue_id or '<missing>'}"
            if issue_id in issue_ids:
                errors.append(f"{prefix}: duplicate issue_id")
            issue_ids.add(issue_id)
            counts[assembly_id] += 1

            required = (
                "discussion_id", "meeting_name", "meeting_date", "topic",
                "what_changes", "target_audience", "current_stage",
                "original_quote", "source_url", "statements",
            )
            for key in required:
                if not record.get(key):
                    errors.append(f"{prefix}: missing {key}")
            if not assembly.get("assembly_name"):
                errors.append(f"{prefix}: missing assembly_name")
            if not _is_http_url(record.get("source_url")):
                errors.append(f"{prefix}: invalid source_url")
            for key in ("title", "catalog_url", "resource_url"):
                if not open_data.get(key):
                    errors.append(f"{prefix}: missing source dataset {key}")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(record.get("meeting_date", ""))):
                errors.append(f"{prefix}: invalid meeting_date")
            if len(public_title(record)) > 80:
                errors.append(f"{prefix}: title is too long for the public list")

            speakers: set[str] = set()
            administrative_answers = 0
            for statement in record.get("statements", []):
                statement_id = str(statement.get("statement_id", ""))
                if statement_id in statement_ids:
                    errors.append(f"{prefix}: duplicate statement_id {statement_id}")
                statement_ids.add(statement_id)
                for key in ("statement_id", "speaker_name", "speaker_role", "summary_quote", "source_excerpt"):
                    if not statement.get(key):
                        errors.append(f"{prefix}: statement missing {key}")
                speakers.add(str(statement.get("speaker_name", "")))
                role = str(statement.get("speaker_role", ""))
                if "議員" not in role:
                    administrative_answers += 1
            if not speakers:
                errors.append(f"{prefix}: no speaker linked to statement text")
            if "答弁済み" in str(record.get("current_stage", "")) and administrative_answers == 0:
                errors.append(f"{prefix}: answer stage has no administrative answer statement")

            question = questions.get(issue_id)
            if question:
                theme = str(question.get("theme", ""))
                topic = public_title(record)
                if not theme or not (theme in topic or topic in theme):
                    errors.append(f"{prefix}: citizen question theme does not match detail title")

    if errors:
        raise ValueError("Issue catalog integrity check failed:\n" + "\n".join(errors))
    return {"issue_count": len(issue_ids), "counts_by_assembly": dict(counts)}


def get_issue_catalog(
    *,
    assembly_id: Optional[str] = None,
    theme: Optional[str] = None,
    stage: Optional[str] = None,
) -> Dict[str, Any]:
    dataset = load_dataset()
    validation = validate_issue_catalog(dataset)
    questions = _question_by_issue()
    issues: List[Dict[str, Any]] = []

    for current_assembly_id, assembly in dataset["assemblies"].items():
        if assembly_id and current_assembly_id != assembly_id:
            continue
        open_data = assembly.get("source", {}).get("open_data") or {}
        for record in assembly.get("records", []):
            if not is_catalog_eligible(record):
                continue
            theme_data = classify_theme(record)
            stage_label = normalize_stage(str(record["current_stage"]))
            if theme and theme_data["id"] != theme:
                continue
            if stage and stage_label != stage:
                continue
            speakers = list(dict.fromkeys(
                str(statement["speaker_name"]) for statement in record["statements"]
            ))
            question = questions.get(record["discussion_id"])
            issues.append({
                "issue_id": record["discussion_id"],
                "assembly_id": current_assembly_id,
                "assembly_name": assembly["assembly_name"],
                "meeting_name": record["meeting_name"],
                "meeting_date": record["meeting_date"],
                "title": public_title(record),
                "theme": theme_data,
                "summary": record["what_changes"],
                "people": speakers,
                "speaker_count": len(speakers),
                "stage": stage_label,
                "stage_detail": record["current_stage"],
                "answer_count": None,
                "question_id": question["question_id"] if question else None,
                "source_url": record["source_url"],
                "source_dataset": {
                    "title": open_data["title"],
                    "catalog_url": open_data["catalog_url"],
                    "resource_url": open_data["resource_url"],
                },
            })

    issues.sort(key=lambda item: (item["meeting_date"], item["issue_id"]), reverse=True)
    return {
        "updated_at": dataset.get("updated_at"),
        "issue_count": len(issues),
        "total_catalog_issue_count": validation["issue_count"],
        "counts_by_assembly": validation["counts_by_assembly"],
        "themes": [
            {"id": theme_id, "label": label}
            for theme_id, label, _ in THEMES
        ] + [{"id": "administration", "label": "行政・議会"}],
        "issues": deepcopy(issues),
    }

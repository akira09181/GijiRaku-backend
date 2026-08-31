"""Load curated, source-verified assembly records from the backend JSON store."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "assembly_records.json"
ASSEMBLY_ALIASES = {
    "machida-shi": "machida-city",
    "shinagawa-ku": "shinagawa-ward",
}


def _data_path() -> Path:
    return Path(os.getenv("GIJIRAKU_ASSEMBLY_RECORDS_PATH", str(DEFAULT_DATA_PATH)))


def load_dataset() -> Dict[str, Any]:
    with _data_path().open(encoding="utf-8") as source:
        dataset = json.load(source)

    if dataset.get("schema_version") != 1 or not isinstance(dataset.get("assemblies"), dict):
        raise ValueError("Unsupported assembly records schema")
    return dataset


def normalize_assembly_id(assembly_id: str) -> str:
    return ASSEMBLY_ALIASES.get(assembly_id, assembly_id)


def get_assembly_records(
    assembly_id: str,
    limit: Optional[int] = None,
    discussion_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_id = normalize_assembly_id(assembly_id)
    dataset = load_dataset()
    assembly = dataset["assemblies"].get(normalized_id)
    if assembly is None:
        raise KeyError(normalized_id)

    records: List[Dict[str, Any]] = [
        deepcopy(record)
        for record in assembly.get("records", [])
        if record.get("publication_status") == "published"
        and (
            discussion_id is None
            or record.get("discussion_id") == discussion_id
        )
    ]
    records.sort(key=lambda record: record.get("meeting_date", ""), reverse=True)
    if limit is not None:
        records = records[:limit]

    return {
        "assembly_id": normalized_id,
        "assembly_name": assembly["assembly_name"],
        "updated_at": dataset.get("updated_at"),
        "open_data_source": deepcopy(assembly.get("source", {}).get("open_data")),
        "records": records,
    }


def get_assembly_record_stats() -> Dict[str, Any]:
    """Return published dataset totals for the public evidence counters."""
    dataset = load_dataset()
    assemblies = dataset["assemblies"]
    published_records = [
        record
        for assembly in assemblies.values()
        for record in assembly.get("records", [])
        if record.get("publication_status") == "published"
    ]
    return {
        "updated_at": dataset.get("updated_at"),
        "open_data_source_count": sum(
            1
            for assembly in assemblies.values()
            if assembly.get("source", {}).get("open_data")
        ),
        "assembly_count": len(assemblies),
        "record_count": len(published_records),
        "statement_count": sum(
            len(record.get("statements", [])) for record in published_records
        ),
    }


def get_latest_record(assembly_id: str) -> Optional[Dict[str, Any]]:
    result = get_assembly_records(assembly_id, limit=1)
    return result["records"][0] if result["records"] else None


def record_to_rag_response(assembly_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    assembly = get_assembly_records(assembly_id, limit=0)
    statements = record.get("statements", [])
    speaker_utterances = [
        {
            "statement_id": statement.get("statement_id"),
            "speaker_name": statement["speaker_name"],
            "speaker_role": statement["speaker_role"],
            "party_name": statement.get("party_name"),
            "committee_name": statement.get("committee_name"),
            "stance_label": statement.get("stance_label", "課題提起"),
            "vote_record": statement.get("vote_record"),
            "summary_quote": statement["summary_quote"],
            "full_summary": statement.get("full_summary"),
            "source_excerpt": statement.get("source_excerpt"),
            "meeting_name": record["meeting_name"],
            "meeting_date": record["meeting_date"],
            "question_type": statement.get("question_type"),
            "avatar_color": statement.get("avatar_color", "emerald"),
            "source_url": record["source_url"],
        }
        for statement in statements
    ]
    return {
        "assembly_name": assembly["assembly_name"],
        "what_changes": record["what_changes"],
        "target_audience": record["target_audience"],
        "current_stage": record["current_stage"],
        "budget_info": record["budget_info"],
        "speaker_utterances": speaker_utterances,
        "original_quote": record["original_quote"],
        "source_url": record["source_url"],
        "live_sources": [{"title": record["meeting_name"], "urls": [record["source_url"]]}],
        "verified": True,
    }

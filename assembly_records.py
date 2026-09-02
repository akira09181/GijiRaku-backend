"""Load source-verified records from Firestore with a safe JSON fallback."""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from catalog_metadata import public_title
from assembly_record_store import (
    AssemblyRecordStoreError,
    canonical_dataset_hash,
    load_firestore_dataset,
    save_firestore_dataset,
)
from store_mode import prefer_memory_store


DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "assembly_records.json"
ASSEMBLY_ALIASES = {
    "machida-shi": "machida-city",
    "shinagawa-ku": "shinagawa-ward",
}
logger = logging.getLogger(__name__)
_active_backend = "json"


def _data_path() -> Path:
    return Path(os.getenv("GIJIRAKU_ASSEMBLY_RECORDS_PATH", str(DEFAULT_DATA_PATH)))


def _load_json_dataset() -> Dict[str, Any]:
    with _data_path().open(encoding="utf-8") as source:
        dataset = json.load(source)

    if dataset.get("schema_version") != 1 or not isinstance(dataset.get("assemblies"), dict):
        raise ValueError("Unsupported assembly records schema")
    return dataset


def _json_fallback_enabled() -> bool:
    return os.getenv("ASSEMBLY_RECORDS_JSON_FALLBACK", "1").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _configured_backend() -> str:
    configured = os.getenv("ASSEMBLY_RECORDS_BACKEND", "").strip().lower()
    if configured:
        return configured
    return "auto" if os.getenv("RENDER", "").strip().lower() == "true" else "json"


def load_dataset() -> Dict[str, Any]:
    global _active_backend
    backend = _configured_backend()
    if prefer_memory_store():
        backend = "json"
    if backend not in {"json", "firestore", "auto"}:
        raise ValueError("ASSEMBLY_RECORDS_BACKEND must be json, firestore, or auto")
    if backend in {"firestore", "auto"}:
        try:
            dataset = load_firestore_dataset()
            _active_backend = "firestore"
            return dataset
        except Exception:
            if backend == "firestore" and not _json_fallback_enabled():
                raise
            logger.exception("Firestore assembly records unavailable; using JSON fallback")
            _active_backend = "json-fallback"
            return _load_json_dataset()
    _active_backend = "json"
    return _load_json_dataset()


def sync_json_snapshot_to_firestore() -> Dict[str, Any]:
    """On Render startup, atomically sync JSON changes through existing credentials."""
    global _active_backend
    backend = _configured_backend()
    if backend == "json":
        _active_backend = "json"
        return {"status": "skipped", "storage_backend": "json"}

    source = _load_json_dataset()
    source_version = canonical_dataset_hash(source)
    try:
        current = load_firestore_dataset(use_cache=False)
        if canonical_dataset_hash(current) == source_version:
            _active_backend = "firestore"
            return {
                "status": "unchanged",
                "storage_backend": "firestore",
                "dataset_version": source_version,
            }
    except Exception:
        logger.info("Firestore assembly record snapshot is not initialized yet")

    try:
        result = save_firestore_dataset(source)
        verified = load_firestore_dataset(use_cache=False)
        if canonical_dataset_hash(verified) != source_version:
            raise AssemblyRecordStoreError("Firestore assembly record verification failed")
        _active_backend = "firestore"
        return {"status": "synchronized", "storage_backend": "firestore", **result}
    except Exception:
        if backend == "firestore" and not _json_fallback_enabled():
            raise
        logger.exception("Firestore assembly record sync failed; keeping JSON fallback")
        _active_backend = "json-fallback"
        return {"status": "fallback", "storage_backend": "json-fallback"}


def get_active_storage_backend() -> str:
    return _active_backend


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
    for record in records:
        record["topic"] = public_title(record)
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
        "storage_backend": get_active_storage_backend(),
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
        "issue_id": record["discussion_id"],
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

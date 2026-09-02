"""Versioned Cloud Firestore storage for official assembly records."""

from __future__ import annotations

import hashlib
import json
import threading
from copy import deepcopy
from typing import Any, Dict, Iterable, Optional, Tuple

from reaction_store import ReactionStoreError, get_firestore_client


META_COLLECTION = "assembly_record_meta"
META_DOCUMENT = "current"
SOURCES_COLLECTION = "assembly_record_sources"
RECORDS_SUBCOLLECTION = "records"
BATCH_WRITE_LIMIT = 400
FIRESTORE_SAFE_DOCUMENT_BYTES = 900_000


class AssemblyRecordStoreError(RuntimeError):
    """Raised when the versioned assembly-record dataset cannot be served."""


_cache_lock = threading.Lock()
_cached_client_id: Optional[int] = None
_cached_version: Optional[str] = None
_cached_dataset: Optional[Dict[str, Any]] = None


def canonical_dataset_hash(dataset: Dict[str, Any]) -> str:
    encoded = json.dumps(
        dataset,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def dataset_counts(dataset: Dict[str, Any]) -> Dict[str, int]:
    assemblies = dataset.get("assemblies", {})
    records = [
        record
        for assembly in assemblies.values()
        for record in assembly.get("records", [])
    ]
    return {
        "assembly_count": len(assemblies),
        "record_count": len(records),
        "statement_count": sum(len(record.get("statements", [])) for record in records),
    }


def validate_firestore_document_sizes(dataset: Dict[str, Any]) -> int:
    """Fail before upload when a record approaches Firestore's 1 MiB limit."""
    largest = 0
    for assembly in dataset.get("assemblies", {}).values():
        documents = [
            {
                "assembly_name": assembly.get("assembly_name"),
                "source": assembly.get("source", {}),
            },
            *assembly.get("records", []),
        ]
        for document in documents:
            size = len(
                json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode(
                    "utf-8"
                )
            )
            largest = max(largest, size)
            if size > FIRESTORE_SAFE_DOCUMENT_BYTES:
                raise ValueError(f"Firestore document is too large: {size} bytes")
    return largest


def clear_firestore_dataset_cache() -> None:
    global _cached_client_id, _cached_version, _cached_dataset
    with _cache_lock:
        _cached_client_id = None
        _cached_version = None
        _cached_dataset = None


def _client_or_error(client: Any = None) -> Any:
    if client is not None:
        return client
    try:
        return get_firestore_client()
    except ReactionStoreError as exc:
        raise AssemblyRecordStoreError("Firestore client is unavailable") from exc


def _commit_writes(client: Any, writes: Iterable[Tuple[Any, Dict[str, Any]]]) -> int:
    pending = list(writes)
    committed = 0
    for offset in range(0, len(pending), BATCH_WRITE_LIMIT):
        batch = client.batch()
        chunk = pending[offset:offset + BATCH_WRITE_LIMIT]
        for reference, payload in chunk:
            batch.set(reference, payload)
        batch.commit()
        committed += len(chunk)
    return committed


def save_firestore_dataset(
    dataset: Dict[str, Any],
    *,
    client: Any = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Upsert one complete immutable dataset version, then switch metadata."""
    if dataset.get("schema_version") != 1 or not isinstance(dataset.get("assemblies"), dict):
        raise ValueError("Unsupported assembly records schema")

    validate_firestore_document_sizes(dataset)
    firestore_client = _client_or_error(client)
    version = canonical_dataset_hash(dataset)
    counts = dataset_counts(dataset)
    writes = []
    for assembly_id, assembly in dataset["assemblies"].items():
        source_reference = firestore_client.collection(SOURCES_COLLECTION).document(assembly_id)
        writes.append((source_reference, {
            "assembly_id": assembly_id,
            "assembly_name": assembly["assembly_name"],
            "source": deepcopy(assembly.get("source", {})),
            "dataset_version": version,
            "updated_at": dataset.get("updated_at"),
        }))
        for record in assembly.get("records", []):
            record_payload = deepcopy(record)
            record_payload["assembly_id"] = assembly_id
            record_payload["dataset_version"] = version
            record_reference = source_reference.collection(RECORDS_SUBCOLLECTION).document(
                record["discussion_id"]
            )
            writes.append((record_reference, record_payload))

    metadata = {
        "schema_version": 1,
        "dataset_version": version,
        "updated_at": dataset.get("updated_at"),
        **counts,
    }
    if dry_run:
        return {**metadata, "document_writes": len(writes) + 1, "dry_run": True}

    committed = _commit_writes(firestore_client, writes)
    # The pointer changes last. Readers therefore see either the complete old
    # version or the complete new version, never a partially uploaded dataset.
    firestore_client.collection(META_COLLECTION).document(META_DOCUMENT).set(metadata)
    committed += 1
    clear_firestore_dataset_cache()
    return {**metadata, "document_writes": committed, "dry_run": False}


def load_firestore_dataset(
    *,
    client: Any = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Load the active Firestore version, using one metadata read on cache hits."""
    global _cached_client_id, _cached_version, _cached_dataset
    firestore_client = _client_or_error(client)
    metadata_snapshot = (
        firestore_client.collection(META_COLLECTION).document(META_DOCUMENT).get()
    )
    if not getattr(metadata_snapshot, "exists", False):
        raise AssemblyRecordStoreError("Assembly record metadata is missing")
    metadata = metadata_snapshot.to_dict() or {}
    version = str(metadata.get("dataset_version", ""))
    if metadata.get("schema_version") != 1 or not version:
        raise AssemblyRecordStoreError("Assembly record metadata is invalid")

    client_id = id(firestore_client)
    with _cache_lock:
        if (
            use_cache
            and _cached_dataset is not None
            and _cached_client_id == client_id
            and _cached_version == version
        ):
            return deepcopy(_cached_dataset)

    assemblies: Dict[str, Any] = {}
    sources = firestore_client.collection(SOURCES_COLLECTION)
    for source_snapshot in sources.stream():
        source_data = source_snapshot.to_dict() or {}
        if source_data.get("dataset_version") != version:
            continue
        assembly_id = str(source_data.get("assembly_id") or source_snapshot.id)
        records = []
        records_query = (
            sources.document(source_snapshot.id)
            .collection(RECORDS_SUBCOLLECTION)
            .where("dataset_version", "==", version)
        )
        for record_snapshot in records_query.stream():
            record = record_snapshot.to_dict() or {}
            record.pop("assembly_id", None)
            record.pop("dataset_version", None)
            records.append(record)
        records.sort(key=lambda item: item.get("meeting_date", ""), reverse=True)
        assemblies[assembly_id] = {
            "assembly_name": source_data.get("assembly_name"),
            "source": deepcopy(source_data.get("source", {})),
            "records": records,
        }

    dataset = {
        "schema_version": 1,
        "updated_at": metadata.get("updated_at"),
        "assemblies": assemblies,
    }
    counts = dataset_counts(dataset)
    expected_counts = {
        key: int(metadata.get(key, -1))
        for key in ("assembly_count", "record_count", "statement_count")
    }
    if counts != expected_counts:
        raise AssemblyRecordStoreError(
            f"Assembly record count mismatch: expected={expected_counts}, actual={counts}"
        )

    with _cache_lock:
        _cached_client_id = client_id
        _cached_version = version
        _cached_dataset = deepcopy(dataset)
    return dataset

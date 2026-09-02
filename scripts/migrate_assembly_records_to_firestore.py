"""Idempotently migrate the versioned assembly-record JSON into Firestore."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from assembly_record_store import (  # noqa: E402
    canonical_dataset_hash,
    dataset_counts,
    load_firestore_dataset,
    save_firestore_dataset,
    validate_firestore_document_sizes,
)
from scripts.update_assembly_records import validate_dataset  # noqa: E402


DEFAULT_SOURCE = ROOT / "data" / "assembly_records.json"


def load_source(path: Path) -> dict:
    with path.open(encoding="utf-8") as source:
        dataset = json.load(source)
    validate_dataset(dataset)
    return dataset


def verify(expected: dict) -> dict:
    actual = load_firestore_dataset(use_cache=False)
    expected_hash = canonical_dataset_hash(expected)
    actual_hash = canonical_dataset_hash(actual)
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"Firestore verification failed: expected={expected_hash}, actual={actual_hash}"
        )
    return {
        "ok": True,
        "dataset_version": actual_hash,
        **dataset_counts(actual),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    dataset = load_source(args.source)
    if args.dry_run:
        result = {
            "ok": True,
            "dry_run": True,
            "dataset_version": canonical_dataset_hash(dataset),
            "max_document_bytes": validate_firestore_document_sizes(dataset),
            **dataset_counts(dataset),
        }
    elif args.verify_only:
        result = verify(dataset)
    else:
        migrated = save_firestore_dataset(dataset)
        result = {"migration": migrated, "verification": verify(dataset)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

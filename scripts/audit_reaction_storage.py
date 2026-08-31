"""Compare Firestore reaction documents with the public reaction API.

Run this from a Render shell (or locally with Firebase credentials):

    python scripts/audit_reaction_storage.py \
      --discussion-id tokyo-metropolitan \
      --api-base https://gijiraku-backend.onrender.com

The script is read-only. It never prints credential contents.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict

import requests
from google.cloud.firestore_v1.base_query import FieldFilter


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reaction_store import (  # noqa: E402
    REACTION_TYPES,
    STORAGE_BACKEND,
    TARGETS_COLLECTION,
    USERS_COLLECTION,
    _nonnegative_counts,
    get_firestore_client,
    verify_reaction_store_connection,
)


def _api_reactions(api_base: str, discussion_id: str) -> Dict[str, Any]:
    response = requests.get(
        f"{api_base.rstrip('/')}/api/reactions",
        params={
            "discussion_id": discussion_id,
            "anonymous_user_id": "storage-audit-read-only",
            "include_user_state": "false",
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("storage_backend") != STORAGE_BACKEND:
        raise RuntimeError(
            "Production API did not identify Firestore as its storage backend"
        )
    return payload


def audit(discussion_id: str, api_base: str) -> Dict[str, Any]:
    storage = verify_reaction_store_connection()
    client = get_firestore_client()
    target_snapshots = list(
        client.collection(TARGETS_COLLECTION)
        .where(filter=FieldFilter("discussion_id", "==", discussion_id))
        .stream()
    )
    user_snapshots = list(
        client.collection(USERS_COLLECTION)
        .where(filter=FieldFilter("discussion_id", "==", discussion_id))
        .stream()
    )

    target_counts: Dict[str, Dict[str, int]] = {}
    for snapshot in target_snapshots:
        data = snapshot.to_dict() or {}
        statement_id = str(data.get("statement_id", ""))
        if statement_id:
            target_counts[statement_id] = _nonnegative_counts(data.get("live_counts"))

    user_counts: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {reaction_type: 0 for reaction_type in REACTION_TYPES}
    )
    for snapshot in user_snapshots:
        data = snapshot.to_dict() or {}
        statement_id = str(data.get("statement_id", ""))
        reaction_type = data.get("reaction_type")
        if statement_id and reaction_type in REACTION_TYPES:
            user_counts[statement_id][reaction_type] += 1

    api_payload = _api_reactions(api_base, discussion_id)
    api_counts = {
        item["statement_id"]: _nonnegative_counts(item.get("live_counts"))
        for item in api_payload.get("data", [])
        if item.get("statement_id")
    }
    all_statement_ids = sorted(
        set(target_counts) | set(user_counts) | set(api_counts)
    )
    mismatches = []
    for statement_id in all_statement_ids:
        target = target_counts.get(
            statement_id, {reaction_type: 0 for reaction_type in REACTION_TYPES}
        )
        users = user_counts.get(
            statement_id, {reaction_type: 0 for reaction_type in REACTION_TYPES}
        )
        api = api_counts.get(
            statement_id, {reaction_type: 0 for reaction_type in REACTION_TYPES}
        )
        if target != users or target != api:
            mismatches.append(
                {
                    "statement_id": statement_id,
                    "reaction_targets_live_counts": target,
                    "reaction_users_recomputed_counts": users,
                    "production_api_live_counts": api,
                }
            )

    return {
        **storage,
        "discussion_id": discussion_id,
        "reaction_target_documents": len(target_snapshots),
        "reaction_user_documents": len(user_snapshots),
        "api_target_records": len(api_counts),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discussion-id", required=True)
    parser.add_argument("--api-base", required=True)
    args = parser.parse_args()

    report = audit(args.discussion_id, args.api_base)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 1 if report["mismatch_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

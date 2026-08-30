"""Persist citizen reactions in Cloud Firestore.

The public API keeps the existing SQLite-era response shape while Firestore
provides durable, transactional storage across Render restarts.
"""

from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Literal, Optional


ReactionType = Literal["agree", "concern", "helpful"]
REACTION_TYPES: tuple[ReactionType, ...] = ("agree", "concern", "helpful")
EMPTY_COUNTS: Dict[str, int] = {reaction_type: 0 for reaction_type in REACTION_TYPES}

TARGETS_COLLECTION = "reaction_targets"
USERS_COLLECTION = "reaction_users"
DEFAULT_RENDER_CREDENTIALS_PATH = Path(
    "/etc/secrets/firebase-service-account.json"
)

_client: Any = None
_client_lock = threading.Lock()


class ReactionStoreError(RuntimeError):
    """Raised when Firestore cannot serve a reaction request."""


def _nonnegative_counts(value: Any) -> Dict[str, int]:
    source = value if isinstance(value, dict) else {}
    counts: Dict[str, int] = {}
    for reaction_type in REACTION_TYPES:
        raw_count = source.get(reaction_type, 0)
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            count = 0
        counts[reaction_type] = max(0, count)
    return counts


def _transition_live_counts(
    current_counts: Dict[str, int],
    previous_reaction_type: Optional[ReactionType],
    next_reaction_type: Optional[ReactionType],
) -> Dict[str, int]:
    """Apply a user's add, switch, or removal to aggregate live counts."""
    next_counts = _nonnegative_counts(current_counts)
    if previous_reaction_type == next_reaction_type:
        return next_counts
    if previous_reaction_type in REACTION_TYPES:
        next_counts[previous_reaction_type] = max(
            0, next_counts[previous_reaction_type] - 1
        )
    if next_reaction_type in REACTION_TYPES:
        next_counts[next_reaction_type] += 1
    return next_counts


def _combined_counts(
    base_counts: Dict[str, int], live_counts: Dict[str, int]
) -> Dict[str, int]:
    normalized_base = _nonnegative_counts(base_counts)
    normalized_live = _nonnegative_counts(live_counts)
    return {
        reaction_type: normalized_base[reaction_type]
        + normalized_live[reaction_type]
        for reaction_type in REACTION_TYPES
    }


def _document_id(*parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return digest


def _target_document_id(discussion_id: str, statement_id: str) -> str:
    return _document_id(discussion_id, statement_id)


def _user_document_id(
    discussion_id: str, statement_id: str, anonymous_user_id: str
) -> str:
    return _document_id(discussion_id, statement_id, anonymous_user_id)


def _credential_path() -> Optional[Path]:
    configured_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if configured_path:
        path = Path(configured_path)
        if not path.is_file():
            raise ReactionStoreError(
                "GOOGLE_APPLICATION_CREDENTIALS does not point to a readable file"
            )
        return path
    if DEFAULT_RENDER_CREDENTIALS_PATH.is_file():
        return DEFAULT_RENDER_CREDENTIALS_PATH
    return None


def _initialize_firebase_app() -> Any:
    import firebase_admin
    from firebase_admin import credentials

    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    credential_path = _credential_path()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    options = {"projectId": project_id} if project_id else None

    try:
        if credential_path is not None:
            credential = credentials.Certificate(str(credential_path))
            return firebase_admin.initialize_app(credential, options=options)
        return firebase_admin.initialize_app(options=options)
    except Exception as exc:  # Firebase exposes multiple credential exceptions.
        raise ReactionStoreError("Firebase Admin SDK initialization failed") from exc


def get_firestore_client() -> Any:
    """Return one lazily initialized Firestore client per process."""
    from firebase_admin import firestore as admin_firestore

    global _client
    if _client is not None:
        return _client

    with _client_lock:
        if _client is not None:
            return _client
        app = _initialize_firebase_app()
        database_id = os.getenv("FIREBASE_DATABASE_ID", "").strip()
        try:
            if database_id and database_id != "(default)":
                _client = admin_firestore.client(app=app, database_id=database_id)
            else:
                _client = admin_firestore.client(app=app)
        except Exception as exc:
            raise ReactionStoreError("Firestore client initialization failed") from exc
    return _client


def _target_query(client: Any, discussion_id: str) -> Iterable[Any]:
    from google.cloud.firestore_v1.base_query import FieldFilter

    return (
        client.collection(TARGETS_COLLECTION)
        .where(filter=FieldFilter("discussion_id", "==", discussion_id))
        .stream()
    )


def put_reaction_state(
    *,
    discussion_id: str,
    statement_id: str,
    reaction_type: Optional[ReactionType],
    anonymous_user_id: str,
    base_counts: Dict[str, int],
) -> Dict[str, Any]:
    """Set one user's reaction and update aggregate counts atomically."""
    from google.cloud import firestore as google_firestore

    if reaction_type is not None and reaction_type not in REACTION_TYPES:
        raise ValueError("Unsupported reaction type")

    client = get_firestore_client()
    target_id = _target_document_id(discussion_id, statement_id)
    target_ref = client.collection(TARGETS_COLLECTION).document(target_id)
    user_ref = client.collection(USERS_COLLECTION).document(
        _user_document_id(discussion_id, statement_id, anonymous_user_id)
    )

    transaction = client.transaction()

    @google_firestore.transactional
    def apply_reaction(transaction: Any) -> Dict[str, Any]:
        target_snapshot = target_ref.get(transaction=transaction)
        user_snapshot = user_ref.get(transaction=transaction)

        target_data = target_snapshot.to_dict() if target_snapshot.exists else {}
        user_data = user_snapshot.to_dict() if user_snapshot.exists else {}

        stored_previous = user_data.get("reaction_type")
        previous_reaction_type: Optional[ReactionType] = (
            stored_previous if stored_previous in REACTION_TYPES else None
        )
        changed = previous_reaction_type != reaction_type

        persisted_base_counts = (
            _nonnegative_counts(target_data.get("base_counts"))
            if target_snapshot.exists
            else _nonnegative_counts(base_counts)
        )
        previous_live_counts = _nonnegative_counts(target_data.get("live_counts"))
        live_counts = _transition_live_counts(
            previous_live_counts, previous_reaction_type, reaction_type
        )
        now = datetime.now(timezone.utc)

        if not target_snapshot.exists or changed:
            target_payload = {
                "discussion_id": discussion_id,
                "statement_id": statement_id,
                "base_counts": persisted_base_counts,
                "live_counts": live_counts,
                "updated_at": now,
            }
            if not target_snapshot.exists:
                target_payload["created_at"] = now
            transaction.set(target_ref, target_payload, merge=True)

        if changed:
            if reaction_type is None:
                if user_snapshot.exists:
                    transaction.delete(user_ref)
            else:
                transaction.set(
                    user_ref,
                    {
                        "target_id": target_id,
                        "discussion_id": discussion_id,
                        "statement_id": statement_id,
                        "anonymous_user_hash": _document_id(anonymous_user_id),
                        "reaction_type": reaction_type,
                        "updated_at": now,
                    },
                    merge=True,
                )

        return {
            "previous_reaction_type": previous_reaction_type,
            "reaction_type": reaction_type,
            "changed": changed,
            "counts": _combined_counts(persisted_base_counts, live_counts),
            "live_counts": live_counts,
        }

    try:
        state = apply_reaction(transaction)
    except ReactionStoreError:
        raise
    except Exception as exc:
        raise ReactionStoreError("Firestore reaction transaction failed") from exc

    return {
        "status": "success",
        "discussion_id": discussion_id,
        "statement_id": statement_id,
        **state,
    }


def list_reaction_states(
    *,
    discussion_id: str,
    anonymous_user_id: str,
    include_user_state: bool = True,
) -> list[Dict[str, Any]]:
    """Return aggregate counts and the requesting user's state for a discussion."""
    client = get_firestore_client()
    try:
        target_snapshots = list(_target_query(client, discussion_id))
        user_refs = (
            [
                client.collection(USERS_COLLECTION).document(
                    _user_document_id(
                        discussion_id,
                        (snapshot.to_dict() or {}).get("statement_id", ""),
                        anonymous_user_id,
                    )
                )
                for snapshot in target_snapshots
            ]
            if include_user_state
            else []
        )
        user_snapshots = list(client.get_all(user_refs)) if user_refs else []
    except Exception as exc:
        raise ReactionStoreError("Firestore reaction query failed") from exc

    user_reactions = {
        snapshot.reference.id: (snapshot.to_dict() or {}).get("reaction_type")
        for snapshot in user_snapshots
        if snapshot.exists
    }
    data: list[Dict[str, Any]] = []
    for target_snapshot in target_snapshots:
        target_data = target_snapshot.to_dict() or {}
        statement_id = str(target_data.get("statement_id", ""))
        if not statement_id:
            continue
        base_counts = _nonnegative_counts(target_data.get("base_counts"))
        live_counts = _nonnegative_counts(target_data.get("live_counts"))
        user_document_id = _user_document_id(
            discussion_id, statement_id, anonymous_user_id
        )
        user_reaction = user_reactions.get(user_document_id)
        data.append(
            {
                "statement_id": statement_id,
                "reaction_type": (
                    user_reaction if user_reaction in REACTION_TYPES else None
                ),
                "counts": _combined_counts(base_counts, live_counts),
                "live_counts": live_counts,
            }
        )
    return sorted(data, key=lambda item: item["statement_id"])


def get_reaction_totals(discussion_id: str) -> Dict[str, int]:
    """Sum user-generated reactions without including any demo base counts."""
    client = get_firestore_client()
    totals = dict(EMPTY_COUNTS)
    try:
        snapshots = _target_query(client, discussion_id)
        for snapshot in snapshots:
            live_counts = _nonnegative_counts(
                (snapshot.to_dict() or {}).get("live_counts")
            )
            for reaction_type in REACTION_TYPES:
                totals[reaction_type] += live_counts[reaction_type]
    except Exception as exc:
        raise ReactionStoreError("Firestore reaction aggregation failed") from exc
    return totals

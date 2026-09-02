"""Persist citizen reactions in Cloud Firestore.

The public API keeps the existing SQLite-era response shape while Firestore
provides durable, transactional storage across Render restarts.
"""

from __future__ import annotations

import hashlib
import json
import logging
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
STORAGE_BACKEND = "firestore"
MEMORY_STORAGE_BACKEND = "memory-fallback"
DEFAULT_RENDER_CREDENTIALS_PATH = Path(
    "/etc/secrets/firebase-service-account.json"
)
INLINE_CREDENTIALS_ENV = "FIREBASE_SERVICE_ACCOUNT_JSON"
FIREBASE_APP_NAME = "gijiraku-reactions"

from store_mode import prefer_memory_store

logger = logging.getLogger(__name__)
_client: Any = None
_client_lock = threading.Lock()
_memory_lock = threading.Lock()
_memory_targets: Dict[str, Dict[str, Any]] = {}
_memory_users: Dict[str, Dict[str, Any]] = {}


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


def _is_render_runtime() -> bool:
    return os.getenv("RENDER", "").strip().lower() == "true"


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


def _load_inline_credentials() -> Optional[Dict[str, Any]]:
    raw_credentials = os.getenv(INLINE_CREDENTIALS_ENV, "").strip()
    if not raw_credentials:
        return None
    try:
        parsed = json.loads(raw_credentials)
    except json.JSONDecodeError as exc:
        raise ReactionStoreError(
            f"{INLINE_CREDENTIALS_ENV} is not valid JSON"
        ) from exc
    if not isinstance(parsed, dict):
        raise ReactionStoreError(
            f"{INLINE_CREDENTIALS_ENV} must contain a JSON object"
        )
    return parsed


def _configured_project_id(credential_data: Optional[Dict[str, Any]]) -> str:
    environment_project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    credential_project_id = str((credential_data or {}).get("project_id", "")).strip()
    if (
        environment_project_id
        and credential_project_id
        and environment_project_id != credential_project_id
    ):
        raise ReactionStoreError(
            "FIREBASE_PROJECT_ID does not match the Firebase credential project_id"
        )
    return environment_project_id or credential_project_id


def _credential_configuration() -> tuple[Optional[Path], Optional[Dict[str, Any]], str]:
    credential_path = _credential_path()
    inline_credentials = _load_inline_credentials()
    if credential_path is not None and inline_credentials is not None:
        raise ReactionStoreError(
            "Configure either GOOGLE_APPLICATION_CREDENTIALS/Render Secret File "
            f"or {INLINE_CREDENTIALS_ENV}, not both"
        )
    if credential_path is not None:
        return credential_path, None, "service_account_file"
    if inline_credentials is not None:
        return None, inline_credentials, "service_account_json_env"
    if _is_render_runtime():
        raise ReactionStoreError(
            "Firebase credentials are required on Render; expected "
            "GOOGLE_APPLICATION_CREDENTIALS, /etc/secrets/firebase-service-account.json, "
            f"or {INLINE_CREDENTIALS_ENV}"
        )
    return None, None, "application_default_credentials"


def _initialize_firebase_app() -> Any:
    try:
        import firebase_admin
        from firebase_admin import credentials
    except Exception as exc:
        logger.exception("Firebase Admin SDK import failed")
        raise ReactionStoreError("Firebase Admin SDK import failed") from exc

    try:
        return firebase_admin.get_app(name=FIREBASE_APP_NAME)
    except ValueError:
        pass

    credential_path, inline_credentials, credential_source = (
        _credential_configuration()
    )
    credential_data: Optional[Dict[str, Any]] = inline_credentials
    if credential_path is not None:
        try:
            loaded = json.loads(credential_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReactionStoreError(
                "Firebase service account file could not be parsed"
            ) from exc
        if not isinstance(loaded, dict):
            raise ReactionStoreError(
                "Firebase service account file must contain a JSON object"
            )
        credential_data = loaded

    project_id = _configured_project_id(credential_data)
    options = {"projectId": project_id} if project_id else None

    try:
        if credential_path is not None:
            credential = credentials.Certificate(str(credential_path))
            app = firebase_admin.initialize_app(
                credential, options=options, name=FIREBASE_APP_NAME
            )
        elif inline_credentials is not None:
            credential = credentials.Certificate(inline_credentials)
            app = firebase_admin.initialize_app(
                credential, options=options, name=FIREBASE_APP_NAME
            )
        else:
            app = firebase_admin.initialize_app(
                options=options, name=FIREBASE_APP_NAME
            )
    except Exception as exc:  # Firebase exposes multiple credential exceptions.
        logger.exception(
            "Firebase Admin SDK initialization failed (credential_source=%s)",
            credential_source,
        )
        raise ReactionStoreError("Firebase Admin SDK initialization failed") from exc
    logger.info(
        "Firebase Admin SDK initialized (backend=%s, credential_source=%s, project_id=%s)",
        STORAGE_BACKEND,
        credential_source,
        project_id or "resolved-by-credentials",
    )
    return app


def get_firestore_client() -> Any:
    """Return one lazily initialized Firestore client per process."""
    try:
        from firebase_admin import firestore as admin_firestore
    except Exception as exc:
        logger.exception("Firestore client import failed")
        raise ReactionStoreError("Firestore client import failed") from exc

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
            logger.exception("Firestore client initialization failed")
            raise ReactionStoreError("Firestore client initialization failed") from exc
    return _client


def verify_reaction_store_connection() -> Dict[str, str]:
    """Perform a real Firestore read and return non-secret runtime metadata."""
    client = get_firestore_client()
    try:
        list(client.collection(TARGETS_COLLECTION).limit(1).stream())
    except Exception as exc:
        logger.exception("Firestore reaction store connectivity check failed")
        raise ReactionStoreError(
            "Firestore reaction store connectivity check failed"
        ) from exc
    database_id = os.getenv("FIREBASE_DATABASE_ID", "").strip() or "(default)"
    project_id = str(getattr(client, "project", "") or "unknown")
    return {
        "storage_backend": STORAGE_BACKEND,
        "project_id": project_id,
        "database_id": database_id,
    }


def _target_query(client: Any, discussion_id: str) -> Iterable[Any]:
    from google.cloud.firestore_v1.base_query import FieldFilter

    return (
        client.collection(TARGETS_COLLECTION)
        .where(filter=FieldFilter("discussion_id", "==", discussion_id))
        .stream()
    )


def _execute_transaction(transaction: Any, callback: Any) -> Dict[str, Any]:
    from google.cloud import firestore as google_firestore

    return google_firestore.transactional(callback)(transaction)


def get_active_reaction_storage_backend() -> str:
    """Return the backend currently serving reaction reads and writes."""
    if prefer_memory_store():
        return MEMORY_STORAGE_BACKEND
    try:
        get_firestore_client()
    except ReactionStoreError:
        return MEMORY_STORAGE_BACKEND
    return STORAGE_BACKEND


def _put_reaction_state_memory(
    *,
    discussion_id: str,
    statement_id: str,
    reaction_type: Optional[ReactionType],
    anonymous_user_id: str,
    base_counts: Dict[str, int],
) -> Dict[str, Any]:
    target_id = _target_document_id(discussion_id, statement_id)
    user_id = _user_document_id(discussion_id, statement_id, anonymous_user_id)

    with _memory_lock:
        target_data = _memory_targets.get(target_id, {})
        user_data = _memory_users.get(user_id, {})

        stored_previous = user_data.get("reaction_type")
        previous_reaction_type: Optional[ReactionType] = (
            stored_previous if stored_previous in REACTION_TYPES else None
        )
        changed = previous_reaction_type != reaction_type

        persisted_base_counts = (
            _nonnegative_counts(target_data.get("base_counts"))
            if target_id in _memory_targets
            else _nonnegative_counts(base_counts)
        )
        previous_live_counts = _nonnegative_counts(target_data.get("live_counts"))
        live_counts = _transition_live_counts(
            previous_live_counts, previous_reaction_type, reaction_type
        )

        if target_id not in _memory_targets or changed:
            _memory_targets[target_id] = {
                "discussion_id": discussion_id,
                "statement_id": statement_id,
                "base_counts": persisted_base_counts,
                "live_counts": live_counts,
            }

        if changed:
            if reaction_type is None:
                _memory_users.pop(user_id, None)
            else:
                _memory_users[user_id] = {
                    "discussion_id": discussion_id,
                    "statement_id": statement_id,
                    "reaction_type": reaction_type,
                }

        state = {
            "previous_reaction_type": previous_reaction_type,
            "reaction_type": reaction_type,
            "changed": changed,
            "counts": _combined_counts(persisted_base_counts, live_counts),
            "live_counts": live_counts,
        }

    return {
        "status": "success",
        "storage_backend": MEMORY_STORAGE_BACKEND,
        "discussion_id": discussion_id,
        "statement_id": statement_id,
        **state,
    }


def _list_reaction_aggregates_memory(*, discussion_id: str) -> list[Dict[str, Any]]:
    with _memory_lock:
        target_items = list(_memory_targets.items())

    aggregates: list[Dict[str, Any]] = []
    for _, target_data in target_items:
        if target_data.get("discussion_id") != discussion_id:
            continue
        statement_id = str(target_data.get("statement_id", ""))
        if not statement_id:
            continue
        base_counts = _nonnegative_counts(target_data.get("base_counts"))
        live_counts = _nonnegative_counts(target_data.get("live_counts"))
        aggregates.append(
            {
                "statement_id": statement_id,
                "counts": _combined_counts(base_counts, live_counts),
                "live_counts": live_counts,
            }
        )
    return sorted(aggregates, key=lambda item: item["statement_id"])


def _list_user_reaction_states_memory(
    *,
    discussion_id: str,
    anonymous_user_id: str,
    statement_ids: Iterable[str],
) -> list[Dict[str, Any]]:
    unique_statement_ids = sorted(set(statement_ids))
    with _memory_lock:
        user_items = list(_memory_users.items())

    states: list[Dict[str, Any]] = []
    for user_id, user_data in user_items:
        if user_data.get("discussion_id") != discussion_id:
            continue
        statement_id = str(user_data.get("statement_id", ""))
        if statement_id not in unique_statement_ids:
            continue
        reaction_type = user_data.get("reaction_type")
        if reaction_type not in REACTION_TYPES:
            continue
        expected_user_id = _user_document_id(
            discussion_id,
            statement_id,
            anonymous_user_id,
        )
        if user_id != expected_user_id:
            continue
        states.append(
            {
                "statement_id": statement_id,
                "reaction_type": reaction_type,
            }
        )
    return states


def put_reaction_state(
    *,
    discussion_id: str,
    statement_id: str,
    reaction_type: Optional[ReactionType],
    anonymous_user_id: str,
    base_counts: Dict[str, int],
) -> Dict[str, Any]:
    """Set one user's reaction and update aggregate counts atomically."""
    if reaction_type is not None and reaction_type not in REACTION_TYPES:
        raise ValueError("Unsupported reaction type")

    if prefer_memory_store():
        return _put_reaction_state_memory(
            discussion_id=discussion_id,
            statement_id=statement_id,
            reaction_type=reaction_type,
            anonymous_user_id=anonymous_user_id,
            base_counts=base_counts,
        )

    try:
        client = get_firestore_client()
    except ReactionStoreError as exc:
        logger.warning(
            "Firestore reaction store unavailable; using memory fallback (discussion_id=%s, statement_id=%s)",
            discussion_id,
            statement_id,
        )
        return _put_reaction_state_memory(
            discussion_id=discussion_id,
            statement_id=statement_id,
            reaction_type=reaction_type,
            anonymous_user_id=anonymous_user_id,
            base_counts=base_counts,
        )

    target_id = _target_document_id(discussion_id, statement_id)
    target_ref = client.collection(TARGETS_COLLECTION).document(target_id)
    user_ref = client.collection(USERS_COLLECTION).document(
        _user_document_id(discussion_id, statement_id, anonymous_user_id)
    )

    transaction = client.transaction()

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
        state = _execute_transaction(transaction, apply_reaction)
    except ReactionStoreError:
        raise
    except Exception as exc:
        logger.exception(
            "Firestore reaction transaction failed (discussion_id=%s, statement_id=%s)",
            discussion_id,
            statement_id,
        )
        logger.warning(
            "Retrying reaction write via memory fallback (discussion_id=%s, statement_id=%s)",
            discussion_id,
            statement_id,
        )
        return _put_reaction_state_memory(
            discussion_id=discussion_id,
            statement_id=statement_id,
            reaction_type=reaction_type,
            anonymous_user_id=anonymous_user_id,
            base_counts=base_counts,
        )

    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "discussion_id": discussion_id,
        "statement_id": statement_id,
        **state,
    }


def list_reaction_aggregates(
    *,
    discussion_id: str,
) -> list[Dict[str, Any]]:
    """Return aggregate counts without reading any user identity."""
    if prefer_memory_store():
        return _list_reaction_aggregates_memory(discussion_id=discussion_id)

    try:
        client = get_firestore_client()
    except ReactionStoreError:
        logger.warning(
            "Firestore reaction store unavailable; using memory fallback (discussion_id=%s)",
            discussion_id,
        )
        return _list_reaction_aggregates_memory(discussion_id=discussion_id)

    try:
        target_snapshots = list(_target_query(client, discussion_id))
    except Exception as exc:
        logger.exception(
            "Firestore reaction aggregate query failed (discussion_id=%s)",
            discussion_id,
        )
        logger.warning(
            "Serving reaction aggregates from memory fallback (discussion_id=%s)",
            discussion_id,
        )
        return _list_reaction_aggregates_memory(discussion_id=discussion_id)

    aggregates: list[Dict[str, Any]] = []
    for target_snapshot in target_snapshots:
        target_data = target_snapshot.to_dict() or {}
        statement_id = str(target_data.get("statement_id", ""))
        if not statement_id:
            continue
        base_counts = _nonnegative_counts(target_data.get("base_counts"))
        live_counts = _nonnegative_counts(target_data.get("live_counts"))
        aggregates.append(
            {
                "statement_id": statement_id,
                "counts": _combined_counts(base_counts, live_counts),
                "live_counts": live_counts,
            }
        )
    return sorted(aggregates, key=lambda item: item["statement_id"])


def list_user_reaction_states(
    *,
    discussion_id: str,
    anonymous_user_id: str,
    statement_ids: Iterable[str],
) -> list[Dict[str, Any]]:
    """Return only one anonymous user's selected reactions."""
    unique_statement_ids = sorted(set(statement_ids))
    if prefer_memory_store():
        return _list_user_reaction_states_memory(
            discussion_id=discussion_id,
            anonymous_user_id=anonymous_user_id,
            statement_ids=unique_statement_ids,
        )

    try:
        client = get_firestore_client()
    except ReactionStoreError:
        logger.warning(
            "Firestore reaction store unavailable; using memory fallback (discussion_id=%s)",
            discussion_id,
        )
        return _list_user_reaction_states_memory(
            discussion_id=discussion_id,
            anonymous_user_id=anonymous_user_id,
            statement_ids=unique_statement_ids,
        )

    try:
        user_refs = [
            client.collection(USERS_COLLECTION).document(
                _user_document_id(
                    discussion_id,
                    statement_id,
                    anonymous_user_id,
                )
            )
            for statement_id in unique_statement_ids
        ]
        user_snapshots = list(client.get_all(user_refs)) if user_refs else []
    except Exception as exc:
        logger.exception(
            "Firestore user reaction query failed (discussion_id=%s)", discussion_id
        )
        logger.warning(
            "Serving user reaction states from memory fallback (discussion_id=%s)",
            discussion_id,
        )
        return _list_user_reaction_states_memory(
            discussion_id=discussion_id,
            anonymous_user_id=anonymous_user_id,
            statement_ids=unique_statement_ids,
        )

    states: list[Dict[str, Any]] = []
    for snapshot in user_snapshots:
        if not snapshot.exists:
            continue
        user_data = snapshot.to_dict() or {}
        statement_id = str(user_data.get("statement_id", ""))
        reaction_type = user_data.get("reaction_type")
        if not statement_id or reaction_type not in REACTION_TYPES:
            continue
        states.append(
            {
                "statement_id": statement_id,
                "reaction_type": reaction_type,
            }
        )
    return states


def list_reaction_states(
    *,
    discussion_id: str,
    anonymous_user_id: str,
    include_user_state: bool = True,
) -> list[Dict[str, Any]]:
    """Backward-compatible combined view built from separated Firestore reads."""
    aggregates = list_reaction_aggregates(discussion_id=discussion_id)
    user_states = (
        list_user_reaction_states(
            discussion_id=discussion_id,
            anonymous_user_id=anonymous_user_id,
            statement_ids=(item["statement_id"] for item in aggregates),
        )
        if include_user_state
        else []
    )
    user_reactions = {
        item["statement_id"]: item["reaction_type"] for item in user_states
    }
    return [
        {
            **aggregate,
            "reaction_type": user_reactions.get(aggregate["statement_id"]),
        }
        for aggregate in aggregates
    ]


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
        logger.exception(
            "Firestore reaction aggregation failed (discussion_id=%s)", discussion_id
        )
        raise ReactionStoreError("Firestore reaction aggregation failed") from exc
    return totals

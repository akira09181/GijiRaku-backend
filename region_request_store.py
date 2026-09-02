"""Firestore persistence for B2C municipality rollout requests."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from reaction_store import ReactionStoreError, STORAGE_BACKEND, get_firestore_client


logger = logging.getLogger(__name__)
REGION_REQUESTS_COLLECTION = "region_requests"


def _request_id(*, municipality_id: str, email: str, anonymous_user_id: str) -> str:
    identity = email.strip().lower() or anonymous_user_id.strip() or "anonymous"
    canonical = f"{municipality_id.strip().lower()}\x1f{identity}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_region_request(
    *,
    municipality_id: str,
    municipality_name: str,
    email: str = "",
    message: str = "",
    anonymous_user_id: str = "",
) -> Dict[str, Any]:
    client = get_firestore_client()
    request_key = _request_id(
        municipality_id=municipality_id,
        email=email,
        anonymous_user_id=anonymous_user_id,
    )
    reference = client.collection(REGION_REQUESTS_COLLECTION).document(request_key)
    now = datetime.now(timezone.utc)
    try:
        existing = reference.get()
        existing_data = existing.to_dict() if existing.exists else {}
        payload = {
            "request_id": request_key,
            "municipality_id": municipality_id.strip(),
            "municipality_name": municipality_name.strip(),
            "email": email.strip().lower(),
            "message": message.strip(),
            "anonymous_user_id": anonymous_user_id.strip(),
            "status": existing_data.get("status", "new"),
            "created_at": existing_data.get("created_at", now),
            "updated_at": now,
        }
        reference.set(payload)
    except Exception as exc:
        logger.exception("Failed to save region request")
        raise ReactionStoreError("Failed to save region request") from exc
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "request_id": request_key,
    }

"""Firestore persistence for MachiVoice Pro consultation leads."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from reaction_store import ReactionStoreError, STORAGE_BACKEND, get_firestore_client


logger = logging.getLogger(__name__)
PRO_LEADS_COLLECTION = "pro_leads"


def _lead_id(organization: str, email: str) -> str:
    canonical = f"{organization.strip().lower()}\x1f{email.strip().lower()}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_pro_lead(*, organization: str, name: str, email: str, purpose: str = "") -> Dict[str, Any]:
    client = get_firestore_client()
    lead_id = _lead_id(organization, email)
    reference = client.collection(PRO_LEADS_COLLECTION).document(lead_id)
    now = datetime.now(timezone.utc)
    try:
        existing = reference.get()
        existing_data = existing.to_dict() if existing.exists else {}
        payload = {
            "lead_id": lead_id,
            "organization": organization.strip(),
            "name": name.strip(),
            "email": email.strip().lower(),
            "purpose": purpose.strip(),
            "status": existing_data.get("status", "new"),
            "created_at": existing_data.get("created_at", now),
            "updated_at": now,
        }
        reference.set(payload)
    except Exception as exc:
        logger.exception("Failed to save Pro lead")
        raise ReactionStoreError("Failed to save Pro lead") from exc
    return {"status": "success", "storage_backend": STORAGE_BACKEND, "lead_id": lead_id}

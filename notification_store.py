"""User preferences and notification matching for follow-up issue delivery."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from follow_store import ISSUE_STATUSES
from reaction_store import ReactionStoreError, STORAGE_BACKEND, get_firestore_client

logger = logging.getLogger(__name__)

USER_PREFERENCES_COLLECTION = "user_preferences"
NOTIFICATIONS_COLLECTION = "notifications"


def _document_id(*parts: str) -> str:
    data = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _normalize_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value[:20]:
        text = str(item).strip()
        if text and text[:100] not in result:
            result.append(text[:100])
    return result


def _user_document_id(anonymous_user_id: str) -> str:
    return _document_id("notification-user", anonymous_user_id)


def _match_text(issue: Dict[str, Any], keywords: List[str]) -> bool:
    if not keywords:
        return True
    haystack = " ".join(
        [
            issue.get("title", ""),
            issue.get("status_summary", ""),
            issue.get("problem_summary", ""),
            issue.get("share_summary", ""),
            issue.get("government_response_summary", ""),
        ]
    )
    lowered = haystack.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def save_user_preferences(anonymous_user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
    client = get_firestore_client()
    reference = client.collection(USER_PREFERENCES_COLLECTION).document(
        _user_document_id(anonymous_user_id)
    )
    payload = {
        "interest_themes": _normalize_list(preferences.get("interest_themes")),
        "municipalities": _normalize_list(preferences.get("municipalities")),
        "keywords": _normalize_list(preferences.get("keywords")),
        "updated_at": datetime.now(timezone.utc),
    }
    try:
        reference.set(payload)
    except Exception as exc:
        logger.exception("Failed to save user notification preferences")
        raise ReactionStoreError("Failed to save user preferences") from exc
    return {"status": "success", "storage_backend": STORAGE_BACKEND, "preferences": payload}


def get_user_preferences(anonymous_user_id: str) -> Dict[str, Any]:
    client = get_firestore_client()
    reference = client.collection(USER_PREFERENCES_COLLECTION).document(
        _user_document_id(anonymous_user_id)
    )
    try:
        snapshot = reference.get()
    except Exception as exc:
        logger.exception("Failed to load user notification preferences")
        raise ReactionStoreError("Failed to load user notification preferences") from exc
    data = snapshot.to_dict() if snapshot.exists else {}
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "preferences": {
            "interest_themes": _normalize_list(data.get("interest_themes")),
            "municipalities": _normalize_list(data.get("municipalities")),
            "keywords": _normalize_list(data.get("keywords")),
        },
    }


def create_notification(anonymous_user_id: str, issue_id: str, message: str) -> Dict[str, Any]:
    client = get_firestore_client()
    user_key = _user_document_id(anonymous_user_id)
    notification_id = _document_id(user_key, issue_id, message)
    reference = client.collection(NOTIFICATIONS_COLLECTION).document(notification_id)
    payload = {
        "notification_id": notification_id,
        "user_key": user_key,
        "issue_id": issue_id,
        "message": message,
        "read": False,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        reference.set(payload)
    except Exception as exc:
        logger.exception("Failed to create issue notification (issue_id=%s)", issue_id)
        raise ReactionStoreError("Failed to create issue notification") from exc
    return {"status": "success", "storage_backend": STORAGE_BACKEND, "notification": payload}


def match_issue_notifications(anonymous_user_id: str) -> Dict[str, Any]:
    preferences = get_user_preferences(anonymous_user_id)
    pref = preferences["preferences"]
    has_filters = any(
        pref[key] for key in ("interest_themes", "municipalities", "keywords")
    )
    if not has_filters:
        return {
            "status": "success",
            "storage_backend": STORAGE_BACKEND,
            "total": 0,
            "matches": [],
        }
    matched = []
    for issue_id, issue in ISSUE_STATUSES.items():
        municipality_ok = not pref["municipalities"] or issue.get("municipality") in pref["municipalities"]
        theme_haystack = " ".join(
            [
                issue.get("title", ""),
                issue.get("status_summary", ""),
                issue.get("share_summary", ""),
            ]
        )
        theme_ok = not pref["interest_themes"] or any(
            theme.lower() in theme_haystack.lower()
            for theme in pref["interest_themes"]
        )
        keyword_ok = _match_text(issue, pref["keywords"])
        if municipality_ok and theme_ok and keyword_ok:
            matched.append({
                "issue_id": issue_id,
                "title": issue.get("title"),
                "municipality": issue.get("municipality"),
                "summary": issue.get("status_summary"),
                "match_score": 1,
                "source_url": issue.get("source_url"),
            })
    return {"status": "success", "storage_backend": STORAGE_BACKEND, "total": len(matched), "matches": matched}


if __name__ == "__main__":
    print("notification_store initialized")

"""User preferences and notification matching for follow-up issue delivery."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from issue_catalog import get_issue_catalog
from reaction_store import ReactionStoreError, STORAGE_BACKEND, get_firestore_client

logger = logging.getLogger(__name__)

USER_PREFERENCES_COLLECTION = "user_preferences"
NOTIFICATIONS_COLLECTION = "notifications"
SUBSCRIPTIONS_COLLECTION = "notification_subscriptions"


class NotificationBatchConfigurationError(RuntimeError):
    pass


class NotificationBatchAuthorizationError(RuntimeError):
    pass


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


def _issue_catalog_rows() -> List[Dict[str, Any]]:
    catalog = get_issue_catalog()
    return [
        {
            "issue_id": issue["issue_id"],
            "title": issue.get("title", ""),
            "municipality": issue.get("assembly_name", ""),
            "assembly_id": issue.get("assembly_id", ""),
            "status_summary": issue.get("stage_detail", ""),
            "problem_summary": issue.get("summary", ""),
            "share_summary": issue.get("summary", ""),
            "government_response_summary": issue.get("stage_detail", ""),
            "theme": (issue.get("theme") or {}).get("label", ""),
            "source_url": issue.get("source_url"),
        }
        for issue in catalog.get("issues", [])
        if isinstance(issue, dict) and issue.get("issue_id")
    ]


def _matches_preferences(issue: Dict[str, Any], preferences: Dict[str, Any]) -> bool:
    municipality = str(issue.get("municipality", ""))
    assembly_id = str(issue.get("assembly_id", ""))
    municipality_ok = (
        not preferences["municipalities"]
        or any(
            selected.lower() == assembly_id.lower()
            or selected.lower() in municipality.lower()
            or municipality.lower() in selected.lower()
            for selected in preferences["municipalities"]
        )
    )
    theme_haystack = " ".join([
        issue.get("theme", ""),
        issue.get("title", ""),
        issue.get("status_summary", ""),
        issue.get("share_summary", ""),
    ])
    theme_ok = not preferences["interest_themes"] or any(
        theme.lower() in theme_haystack.lower()
        for theme in preferences["interest_themes"]
    )
    return municipality_ok and theme_ok and _match_text(issue, preferences["keywords"])


def authorize_notification_batch(provided_api_key: str | None) -> None:
    expected = os.getenv("NOTIFICATION_BATCH_API_KEY", "").strip()
    if not expected:
        raise NotificationBatchConfigurationError("NOTIFICATION_BATCH_API_KEY is not configured")
    if not provided_api_key or not hmac.compare_digest(provided_api_key, expected):
        raise NotificationBatchAuthorizationError("Invalid notification batch API key")


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
    user_key = _user_document_id(anonymous_user_id)
    subscription_payload = {
        "subscription_id": user_key,
        "user_key": user_key,
        **payload,
    }
    try:
        reference.set(payload)
        client.collection(SUBSCRIPTIONS_COLLECTION).document(user_key).set(subscription_payload)
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


def _create_notification_for_user_key(
    *,
    user_key: str,
    issue_id: str,
    subscription_id: str,
    message: str,
) -> Dict[str, Any]:
    client = get_firestore_client()
    notification_id = _document_id(user_key, issue_id, subscription_id)
    reference = client.collection(NOTIFICATIONS_COLLECTION).document(notification_id)
    try:
        snapshot = reference.get()
        existing = snapshot.to_dict() if snapshot.exists else {}
    except Exception as exc:
        logger.exception("Failed to load issue notification (issue_id=%s)", issue_id)
        raise ReactionStoreError("Failed to load issue notification") from exc
    payload = {
        "notification_id": notification_id,
        "user_key": user_key,
        "issue_id": issue_id,
        "subscription_id": subscription_id,
        "message": message,
        "read": bool(existing.get("read", False)),
        "created_at": existing.get("created_at", datetime.now(timezone.utc)),
        "updated_at": datetime.now(timezone.utc),
    }
    try:
        reference.set(payload)
    except Exception as exc:
        logger.exception("Failed to create issue notification (issue_id=%s)", issue_id)
        raise ReactionStoreError("Failed to create issue notification") from exc
    return {"status": "success", "storage_backend": STORAGE_BACKEND, "notification": payload}


def create_notification(
    anonymous_user_id: str,
    issue_id: str,
    message: str,
    subscription_id: str = "legacy",
) -> Dict[str, Any]:
    return _create_notification_for_user_key(
        user_key=_user_document_id(anonymous_user_id),
        issue_id=issue_id,
        subscription_id=subscription_id,
        message=message,
    )


def _issue_lookup() -> Dict[str, Dict[str, Any]]:
    return {row["issue_id"]: row for row in _issue_catalog_rows()}


def _serialize_notification(
    data: Dict[str, Any],
    *,
    issue: Dict[str, Any],
) -> Dict[str, Any]:
    created_at = data.get("created_at")
    updated_at = data.get("updated_at")
    return {
        "notification_id": str(data.get("notification_id", "")),
        "issue_id": str(data.get("issue_id", "")),
        "message": str(data.get("message", "")),
        "read": bool(data.get("read", False)),
        "title": issue.get("title") or str(data.get("issue_id", "")),
        "municipality": issue.get("municipality") or "",
        "summary": issue.get("status_summary") or "",
        "source_url": issue.get("source_url"),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
        "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
    }


def list_user_notifications(anonymous_user_id: str, limit: int = 50) -> Dict[str, Any]:
    user_key = _user_document_id(anonymous_user_id)
    client = get_firestore_client()
    issue_lookup = _issue_lookup()
    try:
        snapshots = list(client.collection(NOTIFICATIONS_COLLECTION).stream())
    except Exception as exc:
        logger.exception("Failed to list user notifications")
        raise ReactionStoreError("Failed to list user notifications") from exc

    notifications = []
    for snapshot in snapshots:
        data = snapshot.to_dict() or {}
        if data.get("user_key") != user_key:
            continue
        issue_id = str(data.get("issue_id", ""))
        notifications.append(_serialize_notification(data, issue=issue_lookup.get(issue_id, {})))

    notifications.sort(
        key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
        reverse=True,
    )
    limited = notifications[: max(1, min(limit, 100))]
    unread_total = sum(1 for item in notifications if not item.get("read"))
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "total": len(notifications),
        "unread_total": unread_total,
        "notifications": limited,
    }


def mark_notifications_read(
    anonymous_user_id: str,
    notification_ids: List[str] | None = None,
) -> Dict[str, Any]:
    user_key = _user_document_id(anonymous_user_id)
    requested = {item.strip() for item in (notification_ids or []) if item.strip()}
    client = get_firestore_client()
    marked = 0
    now = datetime.now(timezone.utc)
    try:
        snapshots = list(client.collection(NOTIFICATIONS_COLLECTION).stream())
    except Exception as exc:
        logger.exception("Failed to mark notifications read")
        raise ReactionStoreError("Failed to mark notifications read") from exc

    for snapshot in snapshots:
        data = snapshot.to_dict() or {}
        if data.get("user_key") != user_key or data.get("read"):
            continue
        notification_id = str(data.get("notification_id") or snapshot.id)
        if requested and notification_id not in requested:
            continue
        payload = {
            **data,
            "read": True,
            "read_at": now,
            "updated_at": now,
        }
        snapshot.reference.set(payload)
        marked += 1

    summary = list_user_notifications(anonymous_user_id)
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "marked_count": marked,
        "unread_total": summary["unread_total"],
        "total": summary["total"],
    }


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
    for issue in _issue_catalog_rows():
        if _matches_preferences(issue, pref):
            matched.append({
                "issue_id": issue["issue_id"],
                "title": issue.get("title"),
                "municipality": issue.get("municipality"),
                "summary": issue.get("status_summary"),
                "match_score": 1,
                "source_url": issue.get("source_url"),
            })
    return {"status": "success", "storage_backend": STORAGE_BACKEND, "total": len(matched), "matches": matched}


def run_notification_matching(issue_ids: List[str] | None = None) -> Dict[str, Any]:
    """Match deployed issues against all subscriptions and upsert notifications."""
    requested = {item.strip() for item in (issue_ids or []) if item.strip()}
    issues = [
        issue for issue in _issue_catalog_rows()
        if not requested or issue["issue_id"] in requested
    ]
    client = get_firestore_client()
    try:
        current_subscriptions = list(client.collection(SUBSCRIPTIONS_COLLECTION).stream())
        subscriptions_by_id = {
            snapshot.id: snapshot.to_dict() or {}
            for snapshot in current_subscriptions
        }
        # Preferences created before notification_subscriptions was introduced
        # remain eligible without exposing the original anonymous user ID.
        for snapshot in client.collection(USER_PREFERENCES_COLLECTION).stream():
            if snapshot.id not in subscriptions_by_id:
                subscriptions_by_id[snapshot.id] = {
                    **(snapshot.to_dict() or {}),
                    "subscription_id": snapshot.id,
                    "user_key": snapshot.id,
                }
    except Exception as exc:
        logger.exception("Failed to list notification subscriptions")
        raise ReactionStoreError("Failed to list notification subscriptions") from exc

    matched_count = 0
    line_push_sent = 0
    line_push_skipped = 0
    notification_ids = []
    for fallback_id, subscription in subscriptions_by_id.items():
        pref = {
            "interest_themes": _normalize_list(subscription.get("interest_themes")),
            "municipalities": _normalize_list(subscription.get("municipalities")),
            "keywords": _normalize_list(subscription.get("keywords")),
        }
        if not subscription.get("user_key") or not any(pref.values()):
            continue
        subscription_id = str(subscription.get("subscription_id") or fallback_id)
        for issue in issues:
            if not _matches_preferences(issue, pref):
                continue
            result = _create_notification_for_user_key(
                user_key=str(subscription["user_key"]),
                issue_id=issue["issue_id"],
                subscription_id=subscription_id,
                message=f"新しい議題「{issue['title']}」が公開されました",
            )
            notification_ids.append(result["notification"]["notification_id"])
            matched_count += 1
            from line_notification_store import notify_line_for_match
            push_result = notify_line_for_match(str(subscription["user_key"]), issue)
            if push_result.get("status") == "sent":
                line_push_sent += 1
            else:
                line_push_skipped += 1
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "issue_count": len(issues),
        "subscription_count": len(subscriptions_by_id),
        "notification_count": matched_count,
        "notification_ids": notification_ids,
        "line_push_sent": line_push_sent,
        "line_push_skipped": line_push_skipped,
    }


if __name__ == "__main__":
    print("notification_store initialized")

"""LINE Messaging API integration for interest-theme push notifications."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from notification_store import _user_document_id
from reaction_store import ReactionStoreError, STORAGE_BACKEND, get_firestore_client

logger = logging.getLogger(__name__)

LINE_LINKS_COLLECTION = "line_user_links"
LINE_PUSH_API_URL = "https://api.line.me/v2/bot/message/push"
LINE_TOKEN_API_URL = "https://api.line.me/oauth2/v2.1/token"
LINE_PROFILE_API_URL = "https://api.line.me/v2/profile"


class LineNotificationConfigurationError(RuntimeError):
    pass


class LineOAuthError(RuntimeError):
    pass


def _app_public_base_url() -> str:
    configured = (
        os.getenv("APP_PUBLIC_BASE_URL", "").strip()
        or os.getenv("NEXT_PUBLIC_SITE_URL", "").strip()
    )
    return (configured or "https://giji-raku-frontend.vercel.app").rstrip("/")


def is_line_push_configured() -> bool:
    return bool(os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip())


def is_line_login_configured() -> bool:
    return bool(
        os.getenv("LINE_LOGIN_CHANNEL_ID", "").strip()
        and os.getenv("LINE_CHANNEL_SECRET", "").strip()
    )


def _link_reference(anonymous_user_id: str):
    user_key = _user_document_id(anonymous_user_id)
    client = get_firestore_client()
    return client.collection(LINE_LINKS_COLLECTION).document(user_key), user_key


def link_line_user(
    anonymous_user_id: str,
    line_user_id: str,
    *,
    display_name: str | None = None,
) -> Dict[str, Any]:
    normalized_line_user_id = line_user_id.strip()
    if not normalized_line_user_id:
        raise ValueError("line_user_id is required")
    reference, user_key = _link_reference(anonymous_user_id)
    now = datetime.now(timezone.utc)
    payload = {
        "user_key": user_key,
        "line_user_id": normalized_line_user_id,
        "line_push_enabled": True,
        "display_name": (display_name or "").strip()[:80] or None,
        "linked_at": now,
        "updated_at": now,
    }
    try:
        reference.set(payload)
    except Exception as exc:
        logger.exception("Failed to link LINE user")
        raise ReactionStoreError("Failed to link LINE user") from exc
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "line": get_line_link_status(anonymous_user_id)["line"],
    }


def unlink_line_user(anonymous_user_id: str) -> Dict[str, Any]:
    reference, _user_key = _link_reference(anonymous_user_id)
    try:
        reference.delete()
    except Exception as exc:
        logger.exception("Failed to unlink LINE user")
        raise ReactionStoreError("Failed to unlink LINE user") from exc
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "line": {
            "linked": False,
            "line_push_enabled": False,
            "configured": is_line_push_configured(),
            "login_configured": is_line_login_configured(),
        },
    }


def get_line_link_status(anonymous_user_id: str) -> Dict[str, Any]:
    reference, _user_key = _link_reference(anonymous_user_id)
    try:
        snapshot = reference.get()
    except Exception as exc:
        logger.exception("Failed to load LINE link status")
        raise ReactionStoreError("Failed to load LINE link status") from exc
    data = snapshot.to_dict() if snapshot.exists else {}
    linked = bool(data.get("line_user_id"))
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "line": {
            "linked": linked,
            "line_push_enabled": bool(data.get("line_push_enabled", False)) if linked else False,
            "display_name": data.get("display_name") if linked else None,
            "configured": is_line_push_configured(),
            "login_configured": is_line_login_configured(),
        },
    }


def _get_line_user_id_for_user_key(user_key: str) -> Optional[str]:
    client = get_firestore_client()
    try:
        snapshot = client.collection(LINE_LINKS_COLLECTION).document(user_key).get()
    except Exception:
        logger.exception("Failed to load LINE link for user_key=%s", user_key)
        return None
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    if not data.get("line_push_enabled", True):
        return None
    line_user_id = str(data.get("line_user_id", "")).strip()
    return line_user_id or None


def exchange_line_login_code(code: str, redirect_uri: str) -> Dict[str, str]:
    channel_id = os.getenv("LINE_LOGIN_CHANNEL_ID", "").strip()
    channel_secret = os.getenv("LINE_CHANNEL_SECRET", "").strip()
    if not channel_id or not channel_secret:
        raise LineNotificationConfigurationError("LINE login is not configured")
    normalized_code = code.strip()
    normalized_redirect_uri = redirect_uri.strip()
    if not normalized_code or not normalized_redirect_uri:
        raise ValueError("code and redirect_uri are required")
    try:
        response = requests.post(
            LINE_TOKEN_API_URL,
            data={
                "grant_type": "authorization_code",
                "code": normalized_code,
                "redirect_uri": normalized_redirect_uri,
                "client_id": channel_id,
                "client_secret": channel_secret,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.exception("LINE OAuth token request failed")
        raise LineOAuthError("LINE OAuth token request failed") from exc
    if response.status_code >= 400:
        logger.warning("LINE OAuth token exchange failed: %s", response.text[:300])
        raise LineOAuthError("LINE OAuth token exchange failed")
    payload = response.json()
    access_token = str(payload.get("access_token", "")).strip()
    if not access_token:
        raise LineOAuthError("LINE OAuth access token missing")
    try:
        profile_response = requests.get(
            LINE_PROFILE_API_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.exception("LINE profile request failed")
        raise LineOAuthError("LINE profile request failed") from exc
    if profile_response.status_code >= 400:
        logger.warning("LINE profile fetch failed: %s", profile_response.text[:300])
        raise LineOAuthError("LINE profile fetch failed")
    profile = profile_response.json()
    line_user_id = str(profile.get("userId", "")).strip()
    if not line_user_id:
        raise LineOAuthError("LINE user id missing")
    display_name = str(profile.get("displayName", "")).strip()
    return {"line_user_id": line_user_id, "display_name": display_name}


def build_issue_url(issue_id: str) -> str:
    return f"{_app_public_base_url()}/issues/{issue_id}"


def send_issue_notification_push(
    line_user_id: str,
    *,
    issue_id: str,
    title: str,
    municipality: str = "",
) -> Dict[str, Any]:
    access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not access_token:
        return {"status": "skipped", "reason": "line_not_configured"}
    issue_url = build_issue_url(issue_id)
    municipality_line = f"\n{municipality}" if municipality else ""
    text = (
        f"関心テーマに一致する新しい議題が公開されました。\n\n"
        f"「{title}」{municipality_line}\n\n"
        f"{issue_url}"
    )
    body = {
        "to": line_user_id,
        "messages": [{"type": "text", "text": text[:5000]}],
    }
    try:
        response = requests.post(
            LINE_PUSH_API_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.exception("LINE push request failed (issue_id=%s)", issue_id)
        return {"status": "error", "reason": "request_failed", "detail": str(exc)}
    if response.status_code >= 400:
        logger.warning(
            "LINE push rejected (issue_id=%s status=%s body=%s)",
            issue_id,
            response.status_code,
            response.text[:300],
        )
        return {
            "status": "error",
            "reason": "line_api_error",
            "http_status": response.status_code,
        }
    return {"status": "sent", "issue_id": issue_id}


def notify_line_for_match(user_key: str, issue: Dict[str, Any]) -> Dict[str, Any]:
    line_user_id = _get_line_user_id_for_user_key(user_key)
    if not line_user_id:
        return {"status": "skipped", "reason": "not_linked"}
    return send_issue_notification_push(
        line_user_id,
        issue_id=str(issue.get("issue_id", "")),
        title=str(issue.get("title", "新しい議題")),
        municipality=str(issue.get("municipality", "")),
    )


def build_line_login_authorize_url(*, redirect_uri: str, state: str) -> str:
    channel_id = os.getenv("LINE_LOGIN_CHANNEL_ID", "").strip()
    if not channel_id:
        raise LineNotificationConfigurationError("LINE login channel id is not configured")
    query = urlencode({
        "response_type": "code",
        "client_id": channel_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "profile openid",
        "bot_prompt": "normal",
    })
    return f"https://access.line.me/oauth2/v2.1/authorize?{query}"

"""Firestore persistence and verified status metadata for followed issues."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from citizen_question_store import get_citizen_question_user_response
from reaction_store import ReactionStoreError, STORAGE_BACKEND, get_firestore_client


FOLLOWS_COLLECTION = "issue_follows"
ISSUES_COLLECTION = "issues"

ISSUE_STATUSES: Dict[str, Dict[str, str]] = {
    "tokyo-app-2026-06-16": {
        "question_id": "tokyo-app-one-stop-services-v1",
        "assembly_id": "tokyo-metropolitan",
        "municipality": "東京都",
        "title": "東京アプリの機能強化",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "支援情報の配信、ログイン簡素化、デジタル都民証、生成AI案内機能を進める方針が答弁されました。",
        "status_updated_at": "2026-06-16T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "必要な支援情報や行政手続へ素早く到達できるかが論点です。",
        "government_response_summary": "東京都はライフステージ別配信やログイン簡素化などを進めると答弁しました。",
        "share_summary": "東京アプリで支援情報と行政手続をワンストップで利用できる機能について、市民の意見を集めています。",
        "source_url": "https://www.gikai.metro.tokyo.lg.jp/record/proceedings/2026-2/02-01.html",
    },
    "shinjuku-sick-child-care-2026-06-10": {
        "question_id": "shinjuku-sick-child-care-realtime-booking-v1",
        "assembly_id": "shinjuku-ward",
        "municipality": "新宿区",
        "title": "病児保育の利用拒否と予約・空き状況の改善",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "受入体制を検討し、空き状況や予約に使えるICTツールを研究すると答弁されました。新しい対応状況は未確認です。",
        "status_updated_at": "2026-06-10T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "病児保育を利用できない事例と、空き状況・予約方法の分かりにくさが論点です。",
        "government_response_summary": "新宿区は受入体制の検討とICTツールの研究を進めると答弁しました。",
        "share_summary": "新宿区の病児保育について、空き状況を確認・予約できる仕組みが必要か市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/shinjuku/SpMinuteView.html?council_id=3193&schedule_id=2",
    },
    "machida-regional-transport-2026-03-26": {
        "question_id": "machida-regional-transport-model-v1",
        "assembly_id": "machida-city",
        "municipality": "町田市",
        "title": "交通不便地域の新しい地域交通モデル",
        "current_status": "議会で質問済み",
        "status_summary": "交通不便地域に地域特性に応じた移動手段を整える考え方が質問されました。新しい対応状況は未確認です。",
        "status_updated_at": "2026-03-26T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "既存公共交通だけでは移動が難しい地域の移動手段が論点です。",
        "government_response_summary": "公開中の会議録では新しい地域交通モデルの構築方法が質問されています。",
        "share_summary": "町田市の交通不便地域に、地域に合う新しい移動手段が必要か市民の意見を集めています。",
        "source_url": "https://www.gikai-machida.jp/g07_Shitsumon.asp?KAIGI=174&Sflg=2",
    },
    "shinagawa-inclusive-education-2026-02-19": {
        "question_id": "shinagawa-school-support-and-dx-v1",
        "assembly_id": "shinagawa-ward",
        "municipality": "品川区",
        "title": "深い学び・多様性の包摂と教員負担軽減",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "学校支援人材と教育DXを活用し、教員負担の軽減と特別支援を進める方針が答弁されました。",
        "status_updated_at": "2026-02-19T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "多様な学びを支えながら教員負担を減らす体制が論点です。",
        "government_response_summary": "品川区は支援人材の充実と教育データの活用を進めると答弁しました。",
        "share_summary": "品川区の学校で、支援人材と教育DXをどう進めるか市民の意見を集めています。",
        "source_url": "https://kaigiroku.city.shinagawa.tokyo.jp/100000?QueryType=New&Template=document&VoiceExpand1=r08-0219_002",
    },
    "shibuya-inflation-support-2026-01-16": {
        "question_id": "shibuya-inflation-benefit-balance-v1",
        "assembly_id": "shibuya-ward",
        "municipality": "渋谷区",
        "title": "物価高騰緊急支援給付金と子育て応援手当",
        "current_status": "補正予算を可決",
        "status_summary": "全区民への1人5,000円給付と、子ども1人当たり2万円の応援手当を含む補正予算が可決されました。",
        "status_updated_at": "2026-01-16T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "物価高騰への支援を一律給付と重点支援でどう配分するかが論点です。",
        "government_response_summary": "渋谷区は全区民給付と子育て世帯への上乗せ手当を実施する補正予算を提案しました。",
        "share_summary": "渋谷区の物価高騰支援で、一律給付と子育て世帯への上乗せをどう組み合わせるか意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/shibuya/SpMinuteView.html?council_id=2494&schedule_id=2",
    },
    "arakawa-ward-auto-2026-03-17-685-6-267": {
        "question_id": "arakawa-budget-priorities-and-results-v1",
        "assembly_id": "arakawa-ward",
        "municipality": "荒川区",
        "title": "令和8年度当初予算の重点施策",
        "current_status": "予算案について討論済み",
        "status_summary": "防災、子育て、福祉、地域活性化などを含む令和8年度一般会計予算案について賛成討論が行われました。",
        "status_updated_at": "2026-03-17T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "当初予算の重点分野と、区民の声をどう事業へ反映するかが論点です。",
        "government_response_summary": "公開中の会議録では令和8年度一般会計予算案について討論されています。",
        "share_summary": "荒川区の令和8年度予算で、事業の目標と成果をどう公開するか市民の意見を集めています。",
        "source_url": "https://ssp.kaigiroku.net/tenant/arakawa/SpMinuteView.html?council_id=685&schedule_id=2",
    },
    "hachioji-rag-ai-2026-06-11": {
        "question_id": "hachioji-rag-ai-safeguarded-rollout-v1",
        "assembly_id": "hachioji-city",
        "municipality": "八王子市",
        "title": "検索拡張生成AIの行政利用",
        "current_status": "議会で質問・答弁済み",
        "status_summary": "2026年度の利用職員50％を目標に、庁内共通業務から段階的に導入する方針が答弁されました。",
        "status_updated_at": "2026-06-11T00:00:00+09:00",
        "status_checked_at": "2026-08-24T15:03:35+09:00",
        "problem_summary": "行政業務で生成AIを使う際の効率、精度、安全性が論点です。",
        "government_response_summary": "八王子市は研修と資料の段階的な取込みでAI活用を定着させる方針を示しました。",
        "share_summary": "八王子市の検索拡張生成AIを、安全対策を条件に行政業務へ広げるか意見を集めています。",
        "source_url": "https://www.city.hachioji.tokyo.dbsr.jp/index.php/611167?Template=document&Id=6213",
    },
}

logger = logging.getLogger(__name__)


def _document_id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _follow_document_id(anonymous_user_id: str, issue_id: str) -> str:
    return _document_id(anonymous_user_id, issue_id)


def _isoformat(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def _is_unread(status_updated_at: str, last_viewed_status_at: Optional[str]) -> bool:
    if not last_viewed_status_at:
        return False
    try:
        status_updated = datetime.fromisoformat(status_updated_at.replace("Z", "+00:00"))
        last_viewed = datetime.fromisoformat(last_viewed_status_at.replace("Z", "+00:00"))
    except ValueError:
        logger.warning(
            "Invalid issue status timestamp (status_updated_at=%s, last_viewed_status_at=%s)",
            status_updated_at,
            last_viewed_status_at,
        )
        return False
    if status_updated.tzinfo is None:
        status_updated = status_updated.replace(tzinfo=timezone.utc)
    if last_viewed.tzinfo is None:
        last_viewed = last_viewed.replace(tzinfo=timezone.utc)
    return status_updated > last_viewed


def _verified_status_updates(
    issue: Dict[str, Any], stored_updates: Any = None
) -> List[Dict[str, str]]:
    updates = stored_updates if isinstance(stored_updates, list) else []
    verified = []
    for update in updates:
        if not isinstance(update, dict) or update.get("verified") is not True:
            continue
        updated_at = _isoformat(update.get("updated_at"))
        summary = str(update.get("summary") or "").strip()
        if not updated_at or not summary:
            continue
        verified.append(
            {
                "updated_at": updated_at,
                "status": str(update.get("status") or issue["current_status"]),
                "summary": summary,
                "source_url": str(update.get("source_url") or issue["source_url"]),
            }
        )
    if not verified:
        verified.append(
            {
                "updated_at": str(issue["status_updated_at"]),
                "status": str(issue["current_status"]),
                "summary": str(issue["status_summary"]),
                "source_url": str(issue["source_url"]),
            }
        )
    verified.sort(key=lambda item: item["updated_at"])
    return verified


def _read_issue_status(client: Any, issue_id: str) -> Dict[str, Any]:
    fallback = ISSUE_STATUSES[issue_id]
    snapshot = client.collection(ISSUES_COLLECTION).document(issue_id).get()
    if not snapshot.exists:
        return {**fallback, "status_updates": _verified_status_updates(fallback)}
    stored = snapshot.to_dict() or {}
    issue = {
        key: str(stored.get(key) or fallback[key])
        for key in fallback
    }
    issue["status_updates"] = _verified_status_updates(
        issue, stored.get("status_updates")
    )
    return issue


def _ensure_issue_status(client: Any, issue_id: str) -> Dict[str, Any]:
    reference = client.collection(ISSUES_COLLECTION).document(issue_id)
    snapshot = reference.get()
    if snapshot.exists:
        return _read_issue_status(client, issue_id)
    issue = ISSUE_STATUSES[issue_id]
    status_updates = _verified_status_updates(issue)
    reference.set({
        "issue_id": issue_id,
        **issue,
        "status_updates": [{**update, "verified": True} for update in status_updates],
    })
    return {**issue, "status_updates": status_updates}


def _public_follow(
    data: Dict[str, Any], issue: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    issue_id = str(data.get("issue_id") or "")
    issue = issue or ISSUE_STATUSES[issue_id]
    last_viewed_status_at = _isoformat(data.get("last_viewed_status_at"))
    return {
        "issue_id": issue_id,
        "assembly_id": issue["assembly_id"],
        "municipality": issue["municipality"],
        "title": issue["title"],
        "current_status": issue["current_status"],
        "status_summary": issue["status_summary"],
        "status_updated_at": issue["status_updated_at"],
        "status_checked_at": issue["status_checked_at"],
        "problem_summary": issue["problem_summary"],
        "government_response_summary": issue["government_response_summary"],
        "share_summary": issue["share_summary"],
        "source_url": issue["source_url"],
        "question_id": issue["question_id"],
        "status_updates": issue.get("status_updates") or _verified_status_updates(issue),
        "created_at": _isoformat(data.get("created_at")),
        "last_viewed_status_at": last_viewed_status_at,
        "notification_enabled": bool(data.get("notification_enabled", False)),
        "has_new_status": _is_unread(issue["status_updated_at"], last_viewed_status_at),
    }


def put_issue_follow(*, issue_id: str, anonymous_user_id: str) -> Dict[str, Any]:
    if issue_id not in ISSUE_STATUSES:
        raise ValueError("Unsupported issue_id")
    client = get_firestore_client()
    reference = client.collection(FOLLOWS_COLLECTION).document(
        _follow_document_id(anonymous_user_id, issue_id)
    )
    try:
        issue = _ensure_issue_status(client, issue_id)
        snapshot = reference.get()
        previous = snapshot.to_dict() if snapshot.exists else {}
        now = datetime.now(timezone.utc)
        payload = {
            "issue_id": issue_id,
            "anonymous_user_id": anonymous_user_id,
            "created_at": previous.get("created_at") or now,
            "last_viewed_status_at": (
                previous.get("last_viewed_status_at")
                or issue["status_updated_at"]
            ),
            "notification_enabled": bool(previous.get("notification_enabled", False)),
            "updated_at": now,
        }
        reference.set(payload)
    except Exception as exc:
        logger.exception("Firestore follow PUT failed (issue_id=%s)", issue_id)
        raise ReactionStoreError("Firestore follow PUT failed") from exc
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "created": not snapshot.exists,
        "follow": _public_follow(payload, issue),
    }


def _follow_query(client: Any, anonymous_user_id: str) -> Iterable[Any]:
    from google.cloud.firestore_v1.base_query import FieldFilter

    return (
        client.collection(FOLLOWS_COLLECTION)
        .where(filter=FieldFilter("anonymous_user_id", "==", anonymous_user_id))
        .stream()
    )


def list_issue_follows(*, anonymous_user_id: str) -> Dict[str, Any]:
    client = get_firestore_client()
    try:
        snapshots = list(_follow_query(client, anonymous_user_id))
        follows = []
        for snapshot in snapshots:
            data = snapshot.to_dict() or {}
            issue_id = data.get("issue_id")
            if issue_id not in ISSUE_STATUSES:
                continue
            issue = _read_issue_status(client, issue_id)
            follow = _public_follow(data, issue)
            follow["my_response"] = get_citizen_question_user_response(
                issue_id=issue_id,
                question_id=issue["question_id"],
                anonymous_user_id=anonymous_user_id,
                client=client,
            )
            follows.append(follow)
    except ReactionStoreError:
        raise
    except Exception as exc:
        logger.exception("Firestore follow GET failed")
        raise ReactionStoreError("Firestore follow GET failed") from exc
    follows.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "follows": follows,
        "total": len(follows),
        "unread_total": sum(1 for follow in follows if follow["has_new_status"]),
    }


def mark_issue_follow_viewed(*, issue_id: str, anonymous_user_id: str) -> Dict[str, Any]:
    if issue_id not in ISSUE_STATUSES:
        raise ValueError("Unsupported issue_id")
    client = get_firestore_client()
    reference = client.collection(FOLLOWS_COLLECTION).document(
        _follow_document_id(anonymous_user_id, issue_id)
    )
    try:
        snapshot = reference.get()
        if not snapshot.exists:
            raise ValueError("Follow not found")
        payload = snapshot.to_dict() or {}
        payload["last_viewed_status_at"] = datetime.now(timezone.utc)
        payload["updated_at"] = datetime.now(timezone.utc)
        reference.set(payload)
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("Firestore follow viewed update failed (issue_id=%s)", issue_id)
        raise ReactionStoreError("Firestore follow viewed update failed") from exc
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "follow": _public_follow(payload, _read_issue_status(client, issue_id)),
    }


def delete_issue_follow(*, issue_id: str, anonymous_user_id: str) -> Dict[str, Any]:
    if issue_id not in ISSUE_STATUSES:
        raise ValueError("Unsupported issue_id")
    client = get_firestore_client()
    reference = client.collection(FOLLOWS_COLLECTION).document(
        _follow_document_id(anonymous_user_id, issue_id)
    )
    try:
        reference.delete()
    except Exception as exc:
        logger.exception("Firestore follow DELETE failed (issue_id=%s)", issue_id)
        raise ReactionStoreError("Firestore follow DELETE failed") from exc
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "issue_id": issue_id,
        "deleted": True,
    }

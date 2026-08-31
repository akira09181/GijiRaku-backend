"""Firestore persistence for issue-specific citizen question responses."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from reaction_store import (
    ReactionStoreError,
    STORAGE_BACKEND,
    _execute_transaction,
    get_firestore_client,
)


RESPONSES_COLLECTION = "citizen_question_responses"
AGGREGATES_COLLECTION = "citizen_question_aggregates"

SHINJUKU_ISSUE_ID = "shinjuku-sick-child-care-2026-06-10"
SHINJUKU_QUESTION_ID = "shinjuku-sick-child-care-realtime-booking-v1"

QUESTION_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    SHINJUKU_QUESTION_ID: {
        "issue_id": SHINJUKU_ISSUE_ID,
        "question": "病児保育の空き状況をリアルタイムで確認・予約できる仕組みが必要だと思いますか？",
        "answers": [
            {"id": "needed", "label": "必要だと思う"},
            {"id": "current_is_enough", "label": "現状の案内で十分"},
            {"id": "need_more_information", "label": "判断材料が足りない"},
        ],
        "reasons": [
            {"id": "availability_unknown", "label": "空き状況が分からず困る"},
            {"id": "same_day_booking_unknown", "label": "当日予約できるか分からない"},
            {"id": "capacity_shortage", "label": "施設や定員が足りない"},
            {"id": "criteria_unclear", "label": "症状別の受入基準が分かりにくい"},
            {"id": "never_used", "label": "利用したことがない"},
            {"id": "other", "label": "その他"},
        ],
        "municipality": "新宿区",
        "theme": "病児保育の利用拒否と予約・空き状況の改善",
    }
}

logger = logging.getLogger(__name__)


def _document_id(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _response_document_id(question_id: str, anonymous_user_id: str) -> str:
    return _document_id(question_id, anonymous_user_id)


def _aggregate_document_id(issue_id: str, question_id: str) -> str:
    return _document_id(issue_id, question_id)


def _definition(issue_id: str, question_id: str) -> Dict[str, Any]:
    definition = QUESTION_DEFINITIONS.get(question_id)
    if definition is None or definition["issue_id"] != issue_id:
        raise ValueError("Unsupported issue_id or question_id")
    return definition


def _allowed_ids(items: Iterable[Dict[str, str]]) -> tuple[str, ...]:
    return tuple(item["id"] for item in items)


def _normalize_reasons(
    selected_reasons: Iterable[str], allowed_reasons: tuple[str, ...]
) -> list[str]:
    selected = set(selected_reasons)
    unsupported = selected.difference(allowed_reasons)
    if unsupported:
        raise ValueError("Unsupported selected reason")
    return [reason_id for reason_id in allowed_reasons if reason_id in selected]


def _normalized_counts(value: Any, keys: Iterable[str]) -> Dict[str, int]:
    source = value if isinstance(value, dict) else {}
    result: Dict[str, int] = {}
    for key in keys:
        try:
            result[key] = max(0, int(source.get(key, 0)))
        except (TypeError, ValueError):
            result[key] = 0
    return result


def _isoformat(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def _public_response(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "issue_id": data.get("issue_id"),
        "question_id": data.get("question_id"),
        "selected_answer": data.get("selected_answer"),
        "selected_reasons": list(data.get("selected_reasons") or []),
        "free_text": str(data.get("free_text") or ""),
        "created_at": _isoformat(data.get("created_at")),
        "updated_at": _isoformat(data.get("updated_at")),
    }


def _aggregate_payload(
    definition: Dict[str, Any], aggregate_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    data = aggregate_data or {}
    answer_ids = _allowed_ids(definition["answers"])
    reason_ids = _allowed_ids(definition["reasons"])
    answer_counts = _normalized_counts(data.get("answer_counts"), answer_ids)
    reason_counts = _normalized_counts(data.get("reason_counts"), reason_ids)
    total_responses = max(0, int(data.get("total_responses", 0) or 0))
    answers = [
        {
            **answer,
            "count": answer_counts[answer["id"]],
            "percentage": (
                round(answer_counts[answer["id"]] * 100 / total_responses, 1)
                if total_responses
                else 0.0
            ),
        }
        for answer in definition["answers"]
    ]
    reasons = [
        {**reason, "count": reason_counts[reason["id"]]}
        for reason in definition["reasons"]
    ]
    top_reasons = sorted(
        (reason for reason in reasons if reason["count"] > 0),
        key=lambda reason: (-reason["count"], reason["label"]),
    )
    return {
        "total_responses": total_responses,
        "answers": answers,
        "reasons": reasons,
        "top_reasons": top_reasons,
        "updated_at": _isoformat(data.get("updated_at")),
    }


def put_citizen_question_response(
    *,
    issue_id: str,
    question_id: str,
    anonymous_user_id: str,
    selected_answer: str,
    selected_reasons: Iterable[str],
    free_text: str,
) -> Dict[str, Any]:
    """Create or overwrite one anonymous user's answer and aggregate atomically."""
    definition = _definition(issue_id, question_id)
    allowed_answers = _allowed_ids(definition["answers"])
    allowed_reasons = _allowed_ids(definition["reasons"])
    if selected_answer not in allowed_answers:
        raise ValueError("Unsupported selected answer")
    reasons = _normalize_reasons(selected_reasons, allowed_reasons)
    if not reasons:
        raise ValueError("At least one selected reason is required")
    normalized_text = free_text.strip()
    if len(normalized_text) > 500:
        raise ValueError("free_text must be at most 500 characters")

    client = get_firestore_client()
    response_ref = client.collection(RESPONSES_COLLECTION).document(
        _response_document_id(question_id, anonymous_user_id)
    )
    aggregate_ref = client.collection(AGGREGATES_COLLECTION).document(
        _aggregate_document_id(issue_id, question_id)
    )
    transaction = client.transaction()

    def apply_response(transaction: Any) -> Dict[str, Any]:
        response_snapshot = response_ref.get(transaction=transaction)
        aggregate_snapshot = aggregate_ref.get(transaction=transaction)
        previous = response_snapshot.to_dict() if response_snapshot.exists else {}
        aggregate_data = (
            aggregate_snapshot.to_dict() if aggregate_snapshot.exists else {}
        )
        previous_answer = previous.get("selected_answer")
        previous_reasons = set(previous.get("selected_reasons") or [])
        answer_counts = _normalized_counts(
            aggregate_data.get("answer_counts"), allowed_answers
        )
        reason_counts = _normalized_counts(
            aggregate_data.get("reason_counts"), allowed_reasons
        )
        total_responses = max(
            0, int(aggregate_data.get("total_responses", 0) or 0)
        )
        if not response_snapshot.exists:
            total_responses += 1
        elif previous_answer in allowed_answers and previous_answer != selected_answer:
            answer_counts[previous_answer] = max(
                0, answer_counts[previous_answer] - 1
            )
        if not response_snapshot.exists or previous_answer != selected_answer:
            answer_counts[selected_answer] += 1

        next_reasons = set(reasons)
        for removed_reason in previous_reasons.difference(next_reasons):
            if removed_reason in reason_counts:
                reason_counts[removed_reason] = max(
                    0, reason_counts[removed_reason] - 1
                )
        for added_reason in next_reasons.difference(previous_reasons):
            reason_counts[added_reason] += 1

        now = datetime.now(timezone.utc)
        created_at = previous.get("created_at") or now
        response_payload = {
            "issue_id": issue_id,
            "question_id": question_id,
            "anonymous_user_id": anonymous_user_id,
            "selected_answer": selected_answer,
            "selected_reasons": reasons,
            "free_text": normalized_text,
            "created_at": created_at,
            "updated_at": now,
        }
        aggregate_payload = {
            "issue_id": issue_id,
            "question_id": question_id,
            "municipality": definition["municipality"],
            "theme": definition["theme"],
            "answer_counts": answer_counts,
            "reason_counts": reason_counts,
            "total_responses": total_responses,
            "created_at": aggregate_data.get("created_at") or now,
            "updated_at": now,
        }
        transaction.set(response_ref, response_payload)
        transaction.set(aggregate_ref, aggregate_payload)
        return {
            "my_response": _public_response(response_payload),
            "aggregate": _aggregate_payload(definition, aggregate_payload),
            "created": not response_snapshot.exists,
        }

    try:
        result = _execute_transaction(transaction, apply_response)
    except ValueError:
        raise
    except Exception as exc:
        logger.exception(
            "Firestore citizen response transaction failed (issue_id=%s, question_id=%s)",
            issue_id,
            question_id,
        )
        raise ReactionStoreError(
            "Firestore citizen response transaction failed"
        ) from exc

    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "question": definition,
        **result,
    }


def get_citizen_question_snapshot(
    *, issue_id: str, question_id: str, anonymous_user_id: Optional[str]
) -> Dict[str, Any]:
    """Read aggregate and optional current-user response as separate documents."""
    definition = _definition(issue_id, question_id)
    client = get_firestore_client()
    aggregate_ref = client.collection(AGGREGATES_COLLECTION).document(
        _aggregate_document_id(issue_id, question_id)
    )
    response_ref = (
        client.collection(RESPONSES_COLLECTION).document(
            _response_document_id(question_id, anonymous_user_id)
        )
        if anonymous_user_id
        else None
    )
    try:
        aggregate_snapshot = aggregate_ref.get()
        response_snapshot = response_ref.get() if response_ref is not None else None
    except Exception as exc:
        logger.exception(
            "Firestore citizen response GET failed (issue_id=%s, question_id=%s)",
            issue_id,
            question_id,
        )
        raise ReactionStoreError("Firestore citizen response GET failed") from exc

    aggregate_data = (
        aggregate_snapshot.to_dict() if aggregate_snapshot.exists else None
    )
    response_data = (
        response_snapshot.to_dict()
        if response_snapshot is not None and response_snapshot.exists
        else None
    )
    return {
        "status": "success",
        "storage_backend": STORAGE_BACKEND,
        "question": definition,
        "my_response": _public_response(response_data) if response_data else None,
        "aggregate": _aggregate_payload(definition, aggregate_data),
    }


def _response_query(client: Any, question_id: str) -> Iterable[Any]:
    from google.cloud.firestore_v1.base_query import FieldFilter

    return (
        client.collection(RESPONSES_COLLECTION)
        .where(filter=FieldFilter("question_id", "==", question_id))
        .stream()
    )


def get_citizen_question_admin_results(
    *, issue_id: str, question_id: str
) -> Dict[str, Any]:
    """Return aggregate and anonymized response details for analysis screens."""
    definition = _definition(issue_id, question_id)
    snapshot = get_citizen_question_snapshot(
        issue_id=issue_id,
        question_id=question_id,
        anonymous_user_id=None,
    )
    client = get_firestore_client()
    try:
        response_snapshots = list(_response_query(client, question_id))
    except Exception as exc:
        logger.exception(
            "Firestore citizen response admin query failed (question_id=%s)",
            question_id,
        )
        raise ReactionStoreError(
            "Firestore citizen response admin query failed"
        ) from exc

    responses = []
    for response_snapshot in response_snapshots:
        data = response_snapshot.to_dict() or {}
        if data.get("issue_id") != issue_id:
            continue
        public = _public_response(data)
        responses.append(
            {
                "selected_answer": public["selected_answer"],
                "selected_reasons": public["selected_reasons"],
                "free_text": public["free_text"],
                "created_at": public["created_at"],
                "updated_at": public["updated_at"],
            }
        )
    responses.sort(key=lambda item: item["updated_at"] or "", reverse=True)
    return {
        **snapshot,
        "municipality": definition["municipality"],
        "theme": definition["theme"],
        "responses": responses,
    }

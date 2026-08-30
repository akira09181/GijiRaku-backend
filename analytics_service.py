"""Build analytics only from source-verified records and persisted reactions."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict

from assembly_records import get_assembly_records
from reaction_store import get_reaction_totals


TOPIC_COLORS = ("#06C755", "#3B82F6", "#F59E0B", "#EF4444", "#EC4899")


def _reaction_totals(assembly_id: str) -> Dict[str, int]:
    return get_reaction_totals(assembly_id)


def get_assembly_analytics(assembly_id: str) -> Dict[str, Any]:
    """Return analytics derived from official records and live Firestore rows."""
    records_data = get_assembly_records(assembly_id, limit=100)
    records = records_data["records"]
    statements = [
        {"topic": record["topic"], "source_url": record["source_url"], **statement}
        for record in records
        for statement in record.get("statements", [])
    ]
    statement_total = len(statements)

    topic_counts = Counter(statement["topic"] for statement in statements)
    topic_distribution = [
        {
            "name": topic,
            "ratio": round(count / statement_total * 100) if statement_total else 0,
            "statement_count": count,
            "color": TOPIC_COLORS[index % len(TOPIC_COLORS)],
        }
        for index, (topic, count) in enumerate(topic_counts.most_common())
    ]

    party_groups: Dict[str, list[Dict[str, Any]]] = defaultdict(list)
    member_groups: Dict[str, list[Dict[str, Any]]] = defaultdict(list)
    for statement in statements:
        party_groups[statement.get("party_name") or "所属記載なし"].append(statement)
        member_groups[statement["speaker_name"]].append(statement)

    party_analytics = []
    for party_name, party_statements in sorted(
        party_groups.items(), key=lambda item: len(item[1]), reverse=True
    ):
        party_topics = Counter(statement["topic"] for statement in party_statements)
        party_total = len(party_statements)
        party_analytics.append(
            {
                "party_name": party_name,
                "members_count": len(
                    {statement["speaker_name"] for statement in party_statements}
                ),
                "top_category": party_topics.most_common(1)[0][0],
                "ai_stance_summary": party_statements[0]["summary_quote"],
                "category_breakdown": [
                    {
                        "category": topic,
                        "percent": round(count / party_total * 100),
                    }
                    for topic, count in party_topics.most_common()
                ],
            }
        )

    member_scorecards = [
        {
            "id": member_statements[0]["statement_id"],
            "name": speaker_name,
            "title": member_statements[0]["speaker_role"],
            "party": member_statements[0].get("party_name") or "所属記載なし",
            "avatar_type": "neutral",
            "total_statements": len(member_statements),
            "activity_score": len(member_statements),
            "main_focus": Counter(
                statement["topic"] for statement in member_statements
            ).most_common(1)[0][0],
            "ai_eval": member_statements[0]["summary_quote"],
        }
        for speaker_name, member_statements in sorted(
            member_groups.items(), key=lambda item: len(item[1]), reverse=True
        )
    ]

    sourced_statements = sum(
        1
        for statement in statements
        if statement.get("source_url") and statement.get("source_excerpt")
    )
    source_coverage = (
        round(sourced_statements / statement_total * 100) if statement_total else 0
    )
    reaction_totals = _reaction_totals(assembly_id)
    reaction_total = sum(reaction_totals.values())
    agree_ratio = (
        round(reaction_totals["agree"] / reaction_total * 100)
        if reaction_total
        else 0
    )

    return {
        "assembly_id": records_data["assembly_id"],
        "data_status": "official_records_and_live_reactions",
        "updated_at": records_data.get("updated_at"),
        "open_data_source": records_data.get("open_data_source"),
        "topic_distribution": topic_distribution,
        "ebpm_citizen_data": {
            "data_status": "live_firestore_aggregate",
            "info_access_time_reduction_rate": None,
            "total_votes_recorded": reaction_total,
            "reaction_totals": reaction_totals,
            "age_demographics": [],
            "ebpm_ai_recommendations": [],
        },
        "party_analytics": party_analytics,
        "member_scorecards": member_scorecards,
        "public_sentiment_score": agree_ratio,
        "ebpm_data_readiness_score": source_coverage,
        "total_speeches_analyzed": statement_total,
    }

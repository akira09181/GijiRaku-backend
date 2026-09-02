"""Deterministic cross-assembly trend aggregation for MachiVoice Pro."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any, Dict, Iterable, List, Optional

from issue_catalog import THEMES, get_issue_catalog


POLICY_KEYWORDS = (
    "子育て", "教育", "学校", "教員", "保育", "若者",
    "生成AI", "AI", "デジタル", "DX", "アプリ", "EBPM",
    "医療", "福祉", "介護", "健康", "住宅", "空き家", "再開発",
    "交通", "自転車", "バス", "物価", "雇用", "予算", "負担",
    "防災", "災害", "避難", "防犯", "地域", "環境", "ごみ",
)


def _validate_iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def _keyword_hits(text: str) -> Iterable[str]:
    lowered = text.lower()
    # Longer labels win so "生成AI" does not also count as the generic "AI".
    occupied: List[tuple[int, int]] = []
    for keyword in sorted(POLICY_KEYWORDS, key=len, reverse=True):
        needle = keyword.lower()
        start = lowered.find(needle)
        if start < 0:
            continue
        end = start + len(needle)
        if any(start >= left and end <= right for left, right in occupied):
            continue
        occupied.append((start, end))
        yield keyword


def get_cross_assembly_trends(
    *,
    from_date: str,
    to_date: str,
    assembly_ids: Optional[List[str]] = None,
    keyword_limit: int = 12,
) -> Dict[str, Any]:
    """Aggregate public issue records without sending official text to an LLM."""
    start = _validate_iso_date(from_date, "from_date")
    end = _validate_iso_date(to_date, "to_date")
    if start > end:
        raise ValueError("from_date must not be later than to_date")
    if keyword_limit < 1 or keyword_limit > 30:
        raise ValueError("keyword_limit must be between 1 and 30")

    requested_assemblies = {
        item.strip() for item in (assembly_ids or []) if isinstance(item, str) and item.strip()
    }
    catalog = get_issue_catalog()
    issues = [
        issue for issue in catalog["issues"]
        if from_date <= issue["meeting_date"] <= to_date
        and (not requested_assemblies or issue["assembly_id"] in requested_assemblies)
    ]

    keyword_counts: Counter[str] = Counter()
    keyword_assemblies: Dict[str, set[str]] = defaultdict(set)
    assembly_rows: Dict[str, Dict[str, Any]] = {}
    for issue in issues:
        assembly_id = issue["assembly_id"]
        row = assembly_rows.setdefault(assembly_id, {
            "assembly_id": assembly_id,
            "assembly_name": issue["assembly_name"],
            "issue_count": 0,
            "speaker_count": 0,
            "theme_counts": Counter(),
        })
        row["issue_count"] += 1
        row["speaker_count"] += int(issue.get("speaker_count") or 0)
        theme_label = str((issue.get("theme") or {}).get("label") or "行政・議会")
        row["theme_counts"][theme_label] += 1

        searchable = " ".join([
            str(issue.get("title") or ""),
            str(issue.get("summary") or ""),
        ])
        for keyword in set(_keyword_hits(searchable)):
            keyword_counts[keyword] += 1
            keyword_assemblies[keyword].add(assembly_id)

    assemblies = []
    for row in assembly_rows.values():
        theme_counts = row.pop("theme_counts")
        ranked_themes = [
            {"label": label, "count": count}
            for label, count in sorted(theme_counts.items(), key=lambda item: (-item[1], item[0]))
        ]
        assemblies.append({
            **row,
            "top_theme": ranked_themes[0]["label"] if ranked_themes else None,
            "themes": ranked_themes,
        })
    assemblies.sort(key=lambda row: (-row["issue_count"], row["assembly_name"]))

    keywords = [
        {
            "label": label,
            "issue_count": count,
            "assembly_count": len(keyword_assemblies[label]),
        }
        for label, count in sorted(keyword_counts.items(), key=lambda item: (-item[1], item[0]))[:keyword_limit]
    ]
    configured_theme_labels = [label for _, label, _ in THEMES] + ["行政・議会"]
    theme_totals = Counter(
        str((issue.get("theme") or {}).get("label") or "行政・議会") for issue in issues
    )

    return {
        "period": {"from": start.isoformat(), "to": end.isoformat()},
        "updated_at": catalog.get("updated_at"),
        "totals": {
            "assembly_count": len(assembly_rows),
            "issue_count": len(issues),
            "speaker_count": sum(int(issue.get("speaker_count") or 0) for issue in issues),
        },
        "keywords": keywords,
        "themes": [
            {"label": label, "issue_count": theme_totals[label]}
            for label in configured_theme_labels if theme_totals[label]
        ],
        "assemblies": assemblies,
    }

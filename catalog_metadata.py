"""Reviewed public metadata keyed by immutable issue IDs."""

VERIFIED_EXTRACTIVE_ISSUE_IDS = {
    "arakawa-ward-auto-2026-03-17-685-6-194",
    "arakawa-ward-auto-2026-03-17-685-6-267",
    "arakawa-ward-auto-2026-02-17-685-3-111",
    "arakawa-ward-auto-2026-02-16-685-2-62",
    "arakawa-ward-auto-2026-02-16-685-2-99",
}

PUBLIC_TITLE_OVERRIDES = {
    "arakawa-ward-auto-2026-03-17-685-6-194": "こども誰でも通園制度の運営基準と保育体制",
    "arakawa-ward-auto-2026-03-17-685-6-267": "令和8年度当初予算の重点施策",
    "arakawa-ward-auto-2026-02-17-685-3-111": "町会・自治会の担い手確保と区との連携",
    "arakawa-ward-auto-2026-02-16-685-2-62": "令和8年度予算と物価高への生活支援",
    "arakawa-ward-auto-2026-02-16-685-2-99": "子どもに寄り添う支援施策の拡充",
}


def public_title(record: dict) -> str:
    return PUBLIC_TITLE_OVERRIDES.get(record.get("discussion_id"), record.get("topic", ""))

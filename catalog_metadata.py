"""Reviewed public metadata keyed by immutable issue IDs."""

VERIFIED_EXTRACTIVE_ISSUE_IDS = {
    "shinjuku-ward-auto-2026-06-11-3193-3-13",
    "shinjuku-ward-auto-2026-06-11-3193-3-25",
    "shinjuku-ward-auto-2026-06-11-3193-3-33",
    "shinjuku-ward-auto-2026-06-11-3193-3-35",
    "shinjuku-ward-auto-2026-06-11-3193-3-37",
    "shinjuku-ward-auto-2026-06-11-3193-3-52",
    "shinjuku-ward-auto-2026-06-11-3193-3-76",
    "shinjuku-ward-auto-2026-06-11-3193-3-80",
    "shinjuku-ward-auto-2026-06-11-3193-3-98",
    "shinjuku-ward-auto-2026-06-11-3193-3-108",
    "shinjuku-ward-auto-2026-06-10-3193-2-10",
    "shinjuku-ward-auto-2026-06-10-3193-2-12",
    "shinjuku-ward-auto-2026-06-10-3193-2-14",
    "shinjuku-ward-auto-2026-06-10-3193-2-16",
    "shinjuku-ward-auto-2026-06-10-3193-2-24",
    "shinjuku-ward-auto-2026-06-10-3193-2-28",
    "shinjuku-ward-auto-2026-06-10-3193-2-30",
    "shinjuku-ward-auto-2026-06-10-3193-2-70",
    "shinjuku-ward-auto-2026-06-10-3193-2-72",
    "shibuya-ward-auto-2025-11-27-2493-3-36",
    "shibuya-ward-auto-2025-06-05-2442-4-5",
    "shibuya-ward-auto-2025-06-04-2442-3-5",
    "arakawa-ward-auto-2026-03-17-685-6-194",
    "arakawa-ward-auto-2026-03-17-685-6-267",
    "arakawa-ward-auto-2026-02-17-685-3-111",
    "arakawa-ward-auto-2026-02-16-685-2-62",
    "arakawa-ward-auto-2026-02-16-685-2-99",
}

PUBLIC_TITLE_OVERRIDES = {
    "shinjuku-ward-auto-2026-06-11-3193-3-35": "地域猫対策と動物福祉",
    "shibuya-ward-auto-2025-11-27-2493-3-36": "玉川上水旧水路緑道再整備工事の費用・仕様",
    "arakawa-ward-auto-2026-03-17-685-6-194": "こども誰でも通園制度の運営基準と保育体制",
    "arakawa-ward-auto-2026-03-17-685-6-267": "令和8年度当初予算の重点施策",
    "arakawa-ward-auto-2026-02-17-685-3-111": "町会・自治会の担い手確保と区との連携",
    "arakawa-ward-auto-2026-02-16-685-2-62": "令和8年度予算と物価高への生活支援",
    "arakawa-ward-auto-2026-02-16-685-2-99": "子どもに寄り添う支援施策の拡充",
}


def public_title(record: dict) -> str:
    return PUBLIC_TITLE_OVERRIDES.get(record.get("discussion_id"), record.get("topic", ""))

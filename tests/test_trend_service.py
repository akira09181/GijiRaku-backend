import unittest
from unittest.mock import patch

from trend_service import get_cross_assembly_trends


CATALOG = {
    "updated_at": "2026-09-01T00:00:00+09:00",
    "issues": [
        {
            "issue_id": "issue-a",
            "assembly_id": "city-a",
            "assembly_name": "A市議会",
            "meeting_date": "2026-08-10",
            "title": "学校の生成AI活用",
            "summary": "教員の負担をデジタルで減らす",
            "speaker_count": 3,
            "theme": {"id": "digital", "label": "行政DX・AI"},
        },
        {
            "issue_id": "issue-b",
            "assembly_id": "city-b",
            "assembly_name": "B市議会",
            "meeting_date": "2026-08-11",
            "title": "学校と子育て支援",
            "summary": "教育環境を整える",
            "speaker_count": 2,
            "theme": {"id": "children", "label": "子育て・教育"},
        },
        {
            "issue_id": "old",
            "assembly_id": "city-a",
            "assembly_name": "A市議会",
            "meeting_date": "2025-01-01",
            "title": "過去の防災議題",
            "summary": "期間外",
            "speaker_count": 9,
            "theme": {"id": "safety", "label": "防災・安全"},
        },
    ],
}


class TrendServiceTest(unittest.TestCase):
    @patch("trend_service.get_issue_catalog", return_value=CATALOG)
    def test_aggregates_multiple_assemblies_in_period(self, _catalog):
        result = get_cross_assembly_trends(from_date="2026-08-01", to_date="2026-08-31")

        self.assertEqual(result["totals"], {
            "assembly_count": 2,
            "issue_count": 2,
            "speaker_count": 5,
        })
        self.assertEqual([row["assembly_id"] for row in result["assemblies"]], ["city-a", "city-b"])
        keyword_labels = [row["label"] for row in result["keywords"]]
        self.assertIn("学校", keyword_labels)
        self.assertIn("生成AI", keyword_labels)
        self.assertNotIn("AI", keyword_labels)

    @patch("trend_service.get_issue_catalog", return_value=CATALOG)
    def test_filters_assemblies_and_handles_empty_range(self, _catalog):
        filtered = get_cross_assembly_trends(
            from_date="2026-08-01",
            to_date="2026-08-31",
            assembly_ids=["city-b"],
        )
        empty = get_cross_assembly_trends(from_date="2026-09-01", to_date="2026-09-30")

        self.assertEqual(filtered["totals"]["issue_count"], 1)
        self.assertEqual(filtered["assemblies"][0]["assembly_id"], "city-b")
        self.assertEqual(empty["totals"]["issue_count"], 0)
        self.assertEqual(empty["keywords"], [])

    def test_rejects_invalid_period(self):
        with self.assertRaises(ValueError):
            get_cross_assembly_trends(from_date="2026-09-30", to_date="2026-09-01")


if __name__ == "__main__":
    unittest.main()

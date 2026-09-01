import unittest

from fastapi import HTTPException

import main
from assembly_records import get_assembly_records
from opendata_service import perform_real_rag_inference


class AssemblyRecordsTest(unittest.TestCase):
    FEATURED_DISCUSSIONS = {
        "tokyo-metropolitan": "tokyo-app-2026-06-16",
        "shinjuku-ward": "shinjuku-sick-child-care-2026-06-10",
        "machida-city": "machida-regional-transport-2026-03-26",
        "shinagawa-ward": "shinagawa-inclusive-education-2026-02-19",
        "shibuya-ward": "shibuya-inflation-support-2026-01-16",
        "arakawa-ward": "arakawa-ward-auto-2026-03-17-685-6-267",
        "hachioji-city": "hachioji-rag-ai-2026-06-11",
    }

    def test_all_featured_discussions_have_complete_detail_data(self):
        for assembly_id, discussion_id in self.FEATURED_DISCUSSIONS.items():
            with self.subTest(assembly_id=assembly_id):
                result = get_assembly_records(
                    assembly_id,
                    limit=1,
                    discussion_id=discussion_id,
                )
                self.assertEqual(len(result["records"]), 1)
                record = result["records"][0]
                self.assertEqual(record["discussion_id"], discussion_id)
                self.assertTrue(result["assembly_name"].strip())
                self.assertTrue(record["topic"].strip())
                self.assertRegex(record["meeting_date"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertTrue(record["what_changes"].strip())
                self.assertGreater(len(record["statements"]), 0)

    def test_filters_a_featured_discussion_by_stable_id(self):
        result = get_assembly_records(
            "shinjuku-ward",
            limit=1,
            discussion_id="shinjuku-sick-child-care-2026-06-10",
        )

        self.assertEqual(result["assembly_id"], "shinjuku-ward")
        self.assertEqual(result["assembly_name"], "新宿区議会")
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(
            result["records"][0]["discussion_id"],
            "shinjuku-sick-child-care-2026-06-10",
        )
        self.assertEqual(result["records"][0]["meeting_date"], "2026-06-10")
        self.assertIn("病児保育", result["records"][0]["topic"])

    def test_api_rejects_a_discussion_from_another_assembly(self):
        with self.assertRaises(HTTPException) as raised:
            main.list_assembly_records(
                "shinjuku-ward",
                limit=1,
                discussion_id="tokyo-app-2026-06-16",
            )

        self.assertEqual(raised.exception.status_code, 404)

    def test_faq_translation_uses_the_requested_issue_instead_of_latest_record(self):
        issue_id = "tokyo-teacher-generative-ai-2026-06-17"
        result = perform_real_rag_inference(
            "生成AIをどう活用する？",
            assembly_id="tokyo-metropolitan",
            discussion_id=issue_id,
        )

        self.assertEqual(result["issue_id"], issue_id)
        self.assertIn("教員", result["what_changes"])
        self.assertNotIn("東京アプリ", result["what_changes"])

    def test_faq_translation_rejects_issue_from_another_assembly(self):
        with self.assertRaisesRegex(ValueError, "Discussion record not found"):
            perform_real_rag_inference(
                "何が変わる？",
                assembly_id="shinjuku-ward",
                discussion_id="tokyo-app-2026-06-16",
            )


if __name__ == "__main__":
    unittest.main()

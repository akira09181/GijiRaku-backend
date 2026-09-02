import unittest
from copy import deepcopy

from assembly_records import load_dataset
from catalog_metadata import public_title
from issue_catalog import (
    get_issue_catalog,
    is_catalog_eligible,
    is_source_matched_extractive,
    validate_issue_catalog,
)


class IssueCatalogTest(unittest.TestCase):
    def test_catalog_exposes_only_compact_verified_topics(self):
        catalog = get_issue_catalog()

        self.assertEqual(catalog["issue_count"], catalog["total_catalog_issue_count"])
        self.assertGreaterEqual(catalog["issue_count"], 74)
        self.assertGreaterEqual(catalog["counts_by_assembly"]["shinjuku-ward"], 39)
        self.assertGreaterEqual(catalog["counts_by_assembly"]["tokyo-metropolitan"], 10)
        for assembly_id in ("machida-city", "shinagawa-ward", "shibuya-ward"):
            self.assertGreaterEqual(catalog["counts_by_assembly"][assembly_id], 3)
        for issue in catalog["issues"]:
            self.assertNotIn("statements", issue)
            self.assertNotIn("original_quote", issue)
            self.assertTrue(issue["source_url"].startswith("http"))
            self.assertGreater(issue["speaker_count"], 0)

    def test_list_and_detail_are_derived_from_the_same_issue_id(self):
        dataset = load_dataset()
        details = {
            record["discussion_id"]: (assembly_id, assembly["assembly_name"], record)
            for assembly_id, assembly in dataset["assemblies"].items()
            for record in assembly["records"]
        }
        for issue in get_issue_catalog()["issues"]:
            assembly_id, assembly_name, detail = details[issue["issue_id"]]
            self.assertEqual(issue["assembly_id"], assembly_id)
            self.assertEqual(issue["assembly_name"], assembly_name)
            self.assertEqual(issue["title"], public_title(detail))
            self.assertEqual(issue["meeting_name"], detail["meeting_name"])
            self.assertEqual(issue["meeting_date"], detail["meeting_date"])
            self.assertEqual(issue["source_url"], detail["source_url"])

    def test_exact_question_answer_topic_can_publish_without_manual_id(self):
        dataset = load_dataset()
        records = dataset["assemblies"]["shinjuku-ward"]["records"]
        record = next(
            item
            for item in records
            if item["discussion_id"] == "shinjuku-ward-auto-2026-06-10-3193-2-68"
        )

        self.assertTrue(is_source_matched_extractive(record))
        self.assertTrue(is_catalog_eligible(record))

    def test_debate_topic_cannot_bypass_manual_review_gate(self):
        dataset = load_dataset()
        records = dataset["assemblies"]["shinjuku-ward"]["records"]
        record = next(
            item
            for item in records
            if item["discussion_id"] == "shinjuku-ward-auto-2026-06-19-3193-4-19"
        )

        self.assertFalse(is_source_matched_extractive(record))
        self.assertFalse(is_catalog_eligible(record))

    def test_catalog_filters_by_region_theme_and_stage(self):
        shinjuku = get_issue_catalog(assembly_id="shinjuku-ward")
        self.assertEqual(
            shinjuku["issue_count"],
            shinjuku["counts_by_assembly"]["shinjuku-ward"],
        )
        self.assertTrue(all(item["assembly_id"] == "shinjuku-ward" for item in shinjuku["issues"]))

        digital = get_issue_catalog(theme="digital")
        self.assertGreater(digital["issue_count"], 0)
        self.assertTrue(all(item["theme"]["id"] == "digital" for item in digital["issues"]))

        answered = get_issue_catalog(stage="答弁済み")
        self.assertGreater(answered["issue_count"], 0)
        self.assertTrue(all(item["stage"] == "答弁済み" for item in answered["issues"]))

    def test_integrity_gate_rejects_missing_source_and_statement_text(self):
        dataset = deepcopy(load_dataset())
        record = next(
            item
            for item in dataset["assemblies"]["tokyo-metropolitan"]["records"]
            if item["discussion_id"] == "tokyo-app-2026-06-16"
        )
        record["source_url"] = ""
        record["statements"][0]["source_excerpt"] = ""

        with self.assertRaisesRegex(ValueError, "missing source_url"):
            validate_issue_catalog(dataset)

    def test_integrity_gate_rejects_duplicate_issue_id(self):
        dataset = deepcopy(load_dataset())
        records = dataset["assemblies"]["tokyo-metropolitan"]["records"]
        duplicate = deepcopy(records[0])
        duplicate["statements"][0]["statement_id"] += "-copy"
        duplicate["statements"][1]["statement_id"] += "-copy"
        records.append(duplicate)

        with self.assertRaisesRegex(ValueError, "duplicate issue_id"):
            validate_issue_catalog(dataset)


if __name__ == "__main__":
    unittest.main()

import unittest
from copy import deepcopy

from assembly_records import load_dataset
from catalog_metadata import public_title
from issue_catalog import get_issue_catalog, validate_issue_catalog


class IssueCatalogTest(unittest.TestCase):
    def test_catalog_exposes_only_compact_verified_topics(self):
        catalog = get_issue_catalog()

        self.assertGreaterEqual(catalog["issue_count"], 35)
        self.assertGreaterEqual(catalog["counts_by_assembly"]["shinjuku-ward"], 10)
        self.assertEqual(catalog["issue_count"], 52)
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

    def test_catalog_filters_by_region_theme_and_stage(self):
        shinjuku = get_issue_catalog(assembly_id="shinjuku-ward")
        self.assertEqual(shinjuku["issue_count"], 20)
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

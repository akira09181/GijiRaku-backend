import unittest
from unittest.mock import patch

from scripts.update_assembly_records import (
    auto_publish,
    build_ssp_records,
    extract_topic,
    parse_meeting_date,
    speaker_from_title,
)


class UpdateAssemblyRecordsTest(unittest.TestCase):
    def test_parse_meeting_date_from_official_transcript(self):
        minutes = [{"body": "<pre>令和8年6月10日（水曜日）</pre>"}]
        self.assertEqual(
            parse_meeting_date("令和 8年 6月定例会", "06月10日－05号", minutes),
            "2026-06-10",
        )

    def test_schedule_date_wins_over_fiscal_year_name(self):
        self.assertEqual(
            parse_meeting_date(
                "令和7年度定例会・2月会議",
                "03月17日－05号",
                [],
                "一、日時 令和八年三月十七日 午前十時",
            ),
            "2026-03-17",
        )

    def test_extract_topic_from_question(self):
        self.assertEqual(
            extract_topic(
                "◆25番（渡辺やすし）　次に、病児保育事業について質問します。"
                "利用状況を伺います。"
            ),
            "病児保育事業",
        )

    def test_extract_topic_from_debate(self):
        self.assertEqual(
            extract_topic(
                "◆37番（さわいめぐみ）　第45号議案に反対の立場で討論いたします。"
            ),
            "第45号議案",
        )

    def test_speaker_roles_are_derived_from_official_titles(self):
        self.assertEqual(
            speaker_from_title("25番（渡辺やすし）", "新宿区議会", False),
            {"speaker_name": "渡辺やすし", "speaker_role": "新宿区議会議員"},
        )
        self.assertEqual(
            speaker_from_title("区長（吉住健一）", "新宿区議会", True),
            {"speaker_name": "吉住健一", "speaker_role": "新宿区長"},
        )
        self.assertEqual(
            speaker_from_title("十三番（西川浩平君）", "荒川区議会", False),
            {"speaker_name": "西川浩平", "speaker_role": "荒川区議会議員"},
        )

    @patch("scripts.update_assembly_records.ssp_post")
    def test_auto_record_contains_only_extractive_statements(self, ssp_post):
        ssp_post.return_value = {
            "tenant_minutes": [
                {
                    "minute_id": 1,
                    "title": "（名簿）",
                    "minute_type_code": 2,
                    "body": "<pre>令和8年6月10日（水曜日）</pre>",
                },
                {
                    "minute_id": 10,
                    "title": "25番（渡辺やすし）",
                    "minute_type_code": 5,
                    "body": (
                        "<pre>病児保育事業について質問します。共働き世帯が増える中、"
                        "子どもの急病時にも安心して働き続けられる受入体制が重要です。"
                        "希望時に利用できない実態があるため、現在の利用状況、"
                        "感染症流行期の課題、今後の供給体制の見直しを伺います。</pre>"
                    ),
                },
                {
                    "minute_id": 11,
                    "title": "区長（吉住健一）",
                    "minute_type_code": 6,
                    "body": "<pre>病児保育事業についてお答えします。供給体制を総合的に検討してまいります。</pre>",
                },
            ]
        }
        dataset = {
            "assemblies": {
                "shinjuku-ward": {
                    "assembly_name": "新宿区議会",
                    "source": {"tenant": "shinjuku", "tenant_id": 211},
                    "records": [],
                }
            }
        }
        candidate = {
            "assembly_id": "shinjuku-ward",
            "council_id": 3193,
            "schedule_id": 2,
            "meeting_name": "令和 8年 6月定例会",
            "schedule_name": "06月10日－05号",
            "source_url": "https://ssp.kaigiroku.net/tenant/shinjuku/SpMinuteView.html?council_id=3193&schedule_id=2",
        }

        records = build_ssp_records(dataset, candidate, 20)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["publication_status"], "published")
        self.assertEqual(records[0]["ingestion_method"], "official-transcript-extractive-v1")
        self.assertEqual(len(records[0]["statements"]), 2)
        for statement in records[0]["statements"]:
            transcript = "".join(
                item["body"] for item in ssp_post.return_value["tenant_minutes"]
            )
            self.assertIn(statement["source_excerpt"], transcript)
            self.assertIn("AIによる要約ではありません", statement["full_summary"])

    @patch("scripts.update_assembly_records.ssp_post")
    def test_official_speech_without_answer_is_published(self, ssp_post):
        ssp_post.return_value = {
            "tenant_minutes": [
                {
                    "minute_id": 1,
                    "title": "（名簿）",
                    "minute_type_code": 2,
                    "body": "<pre>令和8年6月19日（金曜日）</pre>",
                },
                {
                    "minute_id": 19,
                    "title": "37番（さわいめぐみ）",
                    "minute_type_code": 5,
                    "body": (
                        "<pre>第45号議案に反対の立場で討論いたします。"
                        "区民の個人情報の取扱いに関わるため、慎重な検討が必要です。</pre>"
                    ),
                },
            ]
        }
        dataset = {
            "assemblies": {
                "shinjuku-ward": {
                    "assembly_name": "新宿区議会",
                    "source": {"tenant": "shinjuku", "tenant_id": 211},
                    "records": [],
                }
            }
        }
        candidate = {
            "assembly_id": "shinjuku-ward",
            "council_id": 3193,
            "schedule_id": 4,
            "meeting_name": "令和 8年 6月定例会",
            "schedule_name": "06月19日－07号",
            "source_url": "https://ssp.kaigiroku.net/tenant/shinjuku/SpMinuteView.html?council_id=3193&schedule_id=4",
        }

        records = build_ssp_records(dataset, candidate, 20)

        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0]["statements"]), 1)
        self.assertEqual(records[0]["statements"][0]["stance_label"], "議員発言")
        self.assertIn("議員発言", records[0]["current_stage"])

    @patch("scripts.update_assembly_records.build_ssp_records")
    def test_auto_publish_is_idempotent_by_source_import_id(self, build_records):
        record = {
            "discussion_id": "shinjuku-ward-auto-2026-06-10-3193-2-10",
            "meeting_date": "2026-06-10",
            "source_import_id": "ssp:shinjuku:3193:2:10",
        }
        build_records.return_value = [record]
        dataset = {
            "assemblies": {
                "shinjuku-ward": {
                    "records": [],
                }
            }
        }
        candidate = {
            "provider": "ssp",
            "assembly_id": "shinjuku-ward",
        }

        self.assertEqual(auto_publish(dataset, [candidate], 20), 1)
        self.assertEqual(auto_publish(dataset, [candidate], 20), 0)
        self.assertEqual(len(dataset["assemblies"]["shinjuku-ward"]["records"]), 1)

    @patch("scripts.update_assembly_records.build_ssp_records")
    def test_auto_publish_can_backfill_after_an_existing_import(self, build_records):
        existing = {
            "discussion_id": "shinjuku-existing",
            "meeting_date": "2026-06-10",
            "source_url": "https://example.test/minutes/2",
            "source_import_id": "ssp:shinjuku:3193:2:10",
            "topic": "病児保育事業",
        }
        new_record = {
            "discussion_id": "shinjuku-new",
            "meeting_date": "2026-06-10",
            "source_url": "https://example.test/minutes/2",
            "source_import_id": "ssp:shinjuku:3193:2:12",
            "topic": "ベビーシッター利用支援事業",
        }
        build_records.return_value = [existing, new_record]
        dataset = {
            "assemblies": {
                "shinjuku-ward": {
                    "records": [existing],
                }
            }
        }
        candidate = {
            "provider": "ssp",
            "assembly_id": "shinjuku-ward",
        }

        self.assertEqual(auto_publish(dataset, [candidate], 1), 1)
        self.assertEqual(
            [
                record["source_import_id"]
                for record in dataset["assemblies"]["shinjuku-ward"]["records"]
            ],
            ["ssp:shinjuku:3193:2:10", "ssp:shinjuku:3193:2:12"],
        )

    @patch("scripts.update_assembly_records.build_ssp_records")
    def test_auto_publish_refreshes_an_existing_import(self, build_records):
        existing = {
            "discussion_id": "arakawa-ward-auto-2025-03-17-685-6-10",
            "meeting_date": "2025-03-17",
            "source_import_id": "ssp:arakawa:685:6:10",
        }
        refreshed = {
            "discussion_id": "arakawa-ward-auto-2026-03-17-685-6-10",
            "meeting_date": "2026-03-17",
            "source_import_id": "ssp:arakawa:685:6:10",
        }
        build_records.return_value = [refreshed]
        dataset = {
            "assemblies": {
                "arakawa-ward": {
                    "records": [existing],
                }
            }
        }
        candidate = {
            "provider": "ssp",
            "assembly_id": "arakawa-ward",
        }

        self.assertEqual(auto_publish(dataset, [candidate], 20), 1)
        self.assertEqual(
            dataset["assemblies"]["arakawa-ward"]["records"],
            [refreshed],
        )


if __name__ == "__main__":
    unittest.main()

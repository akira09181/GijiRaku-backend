import unittest
from unittest.mock import patch

from fastapi import HTTPException
from langchain_core.documents import Document

import main
from semantic_search_service import (
    SemanticSearchConfigurationError,
    build_search_documents,
    semantic_search,
)


class FakeVectorStore:
    def __init__(self, matches):
        self.matches = matches
        self.calls = []

    def similarity_search_with_relevance_scores(self, query, *, k, filter):
        self.calls.append({"query": query, "k": k, "filter": filter})
        return self.matches


class SemanticSearchServiceTest(unittest.TestCase):
    def setUp(self):
        self.dataset = {
            "schema_version": 1,
            "updated_at": "2026-09-02T00:00:00Z",
            "assemblies": {
                "city-a": {
                    "assembly_name": "A市議会",
                    "records": [
                        {
                            "discussion_id": "issue-a",
                            "publication_status": "published",
                            "topic": "病児保育の予約改善",
                            "what_changes": "空き状況を確認しやすくする",
                            "meeting_name": "定例会",
                            "meeting_date": "2026-06-10",
                            "source_url": "https://example.test/issue-a",
                            "statements": [
                                {
                                    "statement_id": "statement-a",
                                    "speaker_name": "テスト議員",
                                    "speaker_role": "市議会議員",
                                    "summary_quote": "予約方法の改善を求めました。",
                                    "full_summary": None,
                                    "source_excerpt": "予約の利便性を高めるべきです。",
                                }
                            ],
                        },
                        {
                            "discussion_id": "draft",
                            "publication_status": "review",
                            "source_url": "https://example.test/draft",
                            "statements": [{"statement_id": "draft-statement"}],
                        },
                    ],
                }
            },
        }

    def test_builds_only_published_source_linked_statement_documents(self):
        documents = build_search_documents(self.dataset)

        self.assertEqual(len(documents), 1)
        self.assertIn("病児保育", documents[0].page_content)
        self.assertEqual(documents[0].metadata["document_id"], "issue-a:statement-a")
        self.assertEqual(documents[0].metadata["issue_id"], "issue-a")
        self.assertEqual(documents[0].metadata["statement_id"], "statement-a")
        self.assertEqual(documents[0].metadata["source_url"], "https://example.test/issue-a")

    def test_search_preserves_ids_and_passes_assembly_filter(self):
        document = build_search_documents(self.dataset)[0]
        store = FakeVectorStore([(document, 0.87321)])

        result = semantic_search(
            "子どもが熱を出した時の預け先",
            assembly_id="city-a",
            limit=5,
            dataset=self.dataset,
            vector_store=store,
        )

        self.assertEqual(store.calls, [{
            "query": "子どもが熱を出した時の預け先",
            "k": 5,
            "filter": {"assembly_id": "city-a"},
        }])
        self.assertEqual(result["result_count"], 1)
        self.assertEqual(result["results"][0]["issue_id"], "issue-a")
        self.assertEqual(result["results"][0]["statement_id"], "statement-a")
        self.assertEqual(result["results"][0]["relevance_score"], 0.8732)

    def test_rejects_short_query_and_invalid_limit(self):
        with self.assertRaisesRegex(ValueError, "at least 2"):
            semantic_search("a", dataset=self.dataset, vector_store=FakeVectorStore([]))
        with self.assertRaisesRegex(ValueError, "between 1 and 20"):
            semantic_search("病児保育", limit=21, dataset=self.dataset, vector_store=FakeVectorStore([]))

    def test_api_returns_503_when_embeddings_are_not_configured(self):
        with patch.object(
            main,
            "semantic_search",
            side_effect=SemanticSearchConfigurationError("missing key"),
        ):
            with self.assertRaises(HTTPException) as raised:
                main.search_public_statements("病児保育")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "Semantic search is not configured")

    def test_result_fields_tolerate_missing_metadata(self):
        store = FakeVectorStore([(Document(page_content="test", metadata={
            "document_id": "issue:statement",
            "issue_id": "issue",
            "statement_id": "statement",
        }), 1.5)])

        result = semantic_search(
            "検索語",
            dataset=self.dataset,
            vector_store=store,
        )

        self.assertEqual(result["results"][0]["relevance_score"], 1.0)
        self.assertEqual(result["results"][0]["source_url"], "")


if __name__ == "__main__":
    unittest.main()

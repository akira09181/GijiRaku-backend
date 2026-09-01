from copy import deepcopy
import os
import unittest
from unittest.mock import patch

import etl_worker


class _FakeDocumentReference:
    def __init__(self, store, collection_name, document_id):
        self._store = store
        self._collection_name = collection_name
        self._document_id = document_id

    def set(self, payload, merge=False):
        self._store[(self._collection_name, self._document_id)] = deepcopy(payload)


class _FakeCollection:
    def __init__(self, store, name):
        self._store = store
        self._name = name

    def document(self, document_id):
        return _FakeDocumentReference(self._store, self._name, document_id)


class _FakeFirestoreClient:
    def __init__(self, store):
        self._store = store

    def collection(self, name):
        return _FakeCollection(self._store, name)


class EtlWorkerFirestoreTest(unittest.TestCase):
    def test_save_extracted_record_writes_to_isolated_collection(self):
        firestore = {}
        client = _FakeFirestoreClient(firestore)
        payload = {
            "meeting_date": "2026-06-16",
            "speaker": "荒木 ちはる",
            "topic": "東京アプリの機能強化",
            "summary": "支援情報を届ける仕組みを強化する",
            "policy_signals": ["子育て", "デジタル"],
            "source_text_excerpt": "必要な情報が確実に届く体験",
        }

        with patch("etl_worker.get_firestore_client", return_value=client):
            result = etl_worker.save_extracted_record(payload)

        self.assertTrue(result["ok"])
        self.assertEqual(result["collection"], "assembly_record_extractions")
        self.assertIn(("assembly_record_extractions", result["document_id"]), firestore)
        stored = firestore[("assembly_record_extractions", result["document_id"])]
        self.assertEqual(stored["meeting_date"], "2026-06-16")
        self.assertEqual(stored["speaker"], "荒木 ちはる")
        self.assertNotEqual(result["document_id"], "2026-06-16")

    def test_document_id_changes_for_a_different_speech_on_the_same_date(self):
        firestore = {}
        client = _FakeFirestoreClient(firestore)
        base = {
            "meeting_date": "2026-06-16",
            "speaker": "荒木 ちはる",
            "topic": "東京アプリの機能強化",
            "summary": "支援情報を届ける仕組みを強化する",
            "policy_signals": ["子育て"],
            "source_text_excerpt": "必要な情報が確実に届く体験",
        }
        with patch("etl_worker.get_firestore_client", return_value=client):
            first = etl_worker.save_extracted_record(base)
            second = etl_worker.save_extracted_record(
                {**base, "speaker": "別の発言者", "source_text_excerpt": "別の発言"}
            )

        self.assertNotEqual(first["document_id"], second["document_id"])
        self.assertEqual(len(firestore), 2)

    def test_etl_api_key_is_required_and_compared(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(etl_worker.EtlConfigurationError):
                etl_worker.authorize_etl_request(None)
        with patch.dict(os.environ, {"ETL_API_KEY": "configured-secret"}, clear=True):
            with self.assertRaises(etl_worker.EtlAuthorizationError):
                etl_worker.authorize_etl_request("wrong-secret")
            etl_worker.authorize_etl_request("configured-secret")

    def test_invalid_extraction_is_not_persisted(self):
        with self.assertRaisesRegex(ValueError, "meeting_date"):
            etl_worker.normalize_extracted_record(
                {
                    "meeting_date": "not-a-date",
                    "speaker": "発言者",
                    "topic": "議題",
                    "summary": "要約",
                    "policy_signals": [],
                    "source_text_excerpt": "原文",
                }
            )


if __name__ == "__main__":
    unittest.main()

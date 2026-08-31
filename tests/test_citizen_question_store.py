from copy import deepcopy
import unittest
from unittest.mock import patch

import citizen_question_store
from citizen_question_store import (
    AGGREGATES_COLLECTION,
    RESPONSES_COLLECTION,
    SHINJUKU_E2E_QUESTION_ID,
    SHINJUKU_ISSUE_ID,
    SHINJUKU_QUESTION_ID,
    get_citizen_question_admin_results,
    get_citizen_question_snapshot,
    put_citizen_question_response,
)


class _FakeSnapshot:
    def __init__(self, reference, data):
        self.reference = reference
        self._data = deepcopy(data)
        self.exists = data is not None

    def to_dict(self):
        return deepcopy(self._data) if self._data is not None else None


class _FakeDocumentReference:
    def __init__(self, store, collection_name, document_id):
        self._store = store
        self._collection_name = collection_name
        self.id = document_id

    @property
    def key(self):
        return self._collection_name, self.id

    def get(self, transaction=None):
        return _FakeSnapshot(self, self._store.get(self.key))


class _FakeCollection:
    def __init__(self, store, name):
        self._store = store
        self._name = name

    def document(self, document_id):
        return _FakeDocumentReference(self._store, self._name, document_id)


class _FakeTransaction:
    def __init__(self, store):
        self._store = store

    def set(self, reference, payload):
        self._store[reference.key] = deepcopy(payload)


class _FakeFirestoreClient:
    def __init__(self, store):
        self._store = store

    def collection(self, name):
        return _FakeCollection(self._store, name)

    def transaction(self):
        return _FakeTransaction(self._store)


def _answer(**overrides):
    values = {
        "issue_id": SHINJUKU_ISSUE_ID,
        "question_id": SHINJUKU_QUESTION_ID,
        "anonymous_user_id": "browser-a",
        "selected_answer": "needed",
        "selected_reasons": ["availability_unknown", "capacity_shortage"],
        "free_text": "当日の空きが分かると助かります",
    }
    values.update(overrides)
    return put_citizen_question_response(**values)


class CitizenQuestionStoreTest(unittest.TestCase):
    def setUp(self):
        self.firestore = {}
        self.client = _FakeFirestoreClient(self.firestore)
        self.client_patch = patch.object(
            citizen_question_store, "get_firestore_client", return_value=self.client
        )
        self.transaction_patch = patch.object(
            citizen_question_store,
            "_execute_transaction",
            side_effect=lambda transaction, callback: callback(transaction),
        )
        self.client_patch.start()
        self.transaction_patch.start()

    def tearDown(self):
        self.transaction_patch.stop()
        self.client_patch.stop()

    def test_new_response_is_saved_with_multiple_reasons(self):
        result = _answer()

        response_documents = [
            data
            for (collection, _), data in self.firestore.items()
            if collection == RESPONSES_COLLECTION
        ]
        self.assertEqual(len(response_documents), 1)
        self.assertEqual(
            response_documents[0]["selected_reasons"],
            ["availability_unknown", "capacity_shortage"],
        )
        self.assertEqual(response_documents[0]["anonymous_user_id"], "browser-a")
        self.assertIn("created_at", response_documents[0])
        self.assertIn("updated_at", response_documents[0])
        self.assertEqual(result["aggregate"]["total_responses"], 1)
        self.assertTrue(result["created"])
        self.assertEqual(result["storage_backend"], "firestore")

    def test_reanswer_updates_one_record_and_moves_aggregate(self):
        _answer()
        result = _answer(
            selected_answer="current_is_enough",
            selected_reasons=["never_used"],
            free_text="",
        )

        response_documents = [
            data
            for (collection, _), data in self.firestore.items()
            if collection == RESPONSES_COLLECTION
        ]
        aggregate_document = next(
            data
            for (collection, _), data in self.firestore.items()
            if collection == AGGREGATES_COLLECTION
        )
        self.assertEqual(len(response_documents), 1)
        self.assertFalse(result["created"])
        self.assertEqual(aggregate_document["total_responses"], 1)
        self.assertEqual(aggregate_document["answer_counts"]["needed"], 0)
        self.assertEqual(
            aggregate_document["answer_counts"]["current_is_enough"], 1
        )
        self.assertEqual(
            aggregate_document["reason_counts"]["availability_unknown"], 0
        )
        self.assertEqual(aggregate_document["reason_counts"]["capacity_shortage"], 0)
        self.assertEqual(aggregate_document["reason_counts"]["never_used"], 1)
        self.assertEqual(response_documents[0]["free_text"], "")

    def test_reload_restores_only_current_users_answer_and_global_aggregate(self):
        _answer(anonymous_user_id="browser-a")
        _answer(
            anonymous_user_id="browser-b",
            selected_answer="need_more_information",
            selected_reasons=["criteria_unclear"],
        )

        snapshot = get_citizen_question_snapshot(
            issue_id=SHINJUKU_ISSUE_ID,
            question_id=SHINJUKU_QUESTION_ID,
            anonymous_user_id="browser-a",
        )

        self.assertEqual(snapshot["my_response"]["selected_answer"], "needed")
        self.assertEqual(snapshot["aggregate"]["total_responses"], 2)
        counts = {
            answer["id"]: answer["count"]
            for answer in snapshot["aggregate"]["answers"]
        }
        self.assertEqual(counts["needed"], 1)
        self.assertEqual(counts["need_more_information"], 1)

    def test_empty_free_text_is_allowed(self):
        result = _answer(free_text="")
        self.assertEqual(result["my_response"]["free_text"], "")

    def test_zero_responses_return_a_successful_flat_empty_aggregate(self):
        snapshot = get_citizen_question_snapshot(
            issue_id=SHINJUKU_ISSUE_ID,
            question_id=SHINJUKU_QUESTION_ID,
            anonymous_user_id="new-browser",
        )

        self.assertEqual(snapshot["question_id"], SHINJUKU_QUESTION_ID)
        self.assertEqual(snapshot["total"], 0)
        self.assertEqual(snapshot["answers"], {})
        self.assertEqual(snapshot["reasons"], {})

    def test_public_e2e_question_uses_an_isolated_aggregate(self):
        _answer()
        test_snapshot = get_citizen_question_snapshot(
            issue_id=SHINJUKU_ISSUE_ID,
            question_id=SHINJUKU_E2E_QUESTION_ID,
            anonymous_user_id="public-e2e-browser-a",
        )

        self.assertEqual(test_snapshot["total"], 0)
        self.assertTrue(test_snapshot["question"]["test_only"])

    def test_free_text_over_500_characters_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at most 500"):
            _answer(free_text="あ" * 501)

    def test_admin_results_never_expose_anonymous_user_id(self):
        _answer()
        response_snapshots = [
            _FakeSnapshot(
                _FakeDocumentReference(self.firestore, collection, document_id),
                data,
            )
            for (collection, document_id), data in self.firestore.items()
            if collection == RESPONSES_COLLECTION
        ]
        with patch.object(
            citizen_question_store,
            "_response_query",
            return_value=response_snapshots,
        ):
            result = get_citizen_question_admin_results(
                issue_id=SHINJUKU_ISSUE_ID,
                question_id=SHINJUKU_QUESTION_ID,
            )

        self.assertEqual(len(result["responses"]), 1)
        self.assertNotIn("anonymous_user_id", result["responses"][0])


if __name__ == "__main__":
    unittest.main()

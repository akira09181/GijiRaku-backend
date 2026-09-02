from copy import deepcopy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import reaction_store
from reaction_store import (
    ReactionStoreError,
    STORAGE_BACKEND,
    _credential_configuration,
    _combined_counts,
    _target_document_id,
    _transition_live_counts,
    _user_document_id,
    list_reaction_states,
    put_reaction_state,
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

    def set(self, reference, payload, merge=False):
        previous = self._store.get(reference.key, {}) if merge else {}
        self._store[reference.key] = {**deepcopy(previous), **deepcopy(payload)}

    def delete(self, reference):
        self._store.pop(reference.key, None)


class _FakeFirestoreClient:
    def __init__(self, store):
        self._store = store

    def collection(self, name):
        return _FakeCollection(self._store, name)

    def transaction(self):
        return _FakeTransaction(self._store)

    def get_all(self, references):
        return [reference.get() for reference in references]


def _fake_target_query(store, discussion_id):
    snapshots = []
    for (collection_name, document_id), data in store.items():
        if (
            collection_name == reaction_store.TARGETS_COLLECTION
            and data.get("discussion_id") == discussion_id
        ):
            reference = _FakeDocumentReference(store, collection_name, document_id)
            snapshots.append(_FakeSnapshot(reference, data))
    return snapshots


class ReactionStoreStateTest(unittest.TestCase):
    def test_adds_first_reaction(self):
        counts = _transition_live_counts(
            {"agree": 0, "concern": 0, "helpful": 0},
            None,
            "agree",
        )
        self.assertEqual(counts, {"agree": 1, "concern": 0, "helpful": 0})

    def test_switches_reaction_without_changing_total(self):
        counts = _transition_live_counts(
            {"agree": 3, "concern": 1, "helpful": 0},
            "agree",
            "concern",
        )
        self.assertEqual(counts, {"agree": 2, "concern": 2, "helpful": 0})

    def test_removes_reaction_without_going_negative(self):
        counts = _transition_live_counts(
            {"agree": 0, "concern": 0, "helpful": 0},
            "agree",
            None,
        )
        self.assertEqual(counts, {"agree": 0, "concern": 0, "helpful": 0})

    def test_unchanged_reaction_is_idempotent(self):
        counts = _transition_live_counts(
            {"agree": 2, "concern": 1, "helpful": 4},
            "helpful",
            "helpful",
        )
        self.assertEqual(counts, {"agree": 2, "concern": 1, "helpful": 4})

    def test_combines_demo_base_and_live_counts(self):
        counts = _combined_counts(
            {"agree": 10, "concern": 2, "helpful": 1},
            {"agree": 3, "concern": 4, "helpful": 0},
        )
        self.assertEqual(counts, {"agree": 13, "concern": 6, "helpful": 1})

    def test_document_ids_are_stable_and_hide_raw_user_id(self):
        target_id = _target_document_id("assembly", "statement")
        user_id = _user_document_id("assembly", "statement", "secret-user-id")

        self.assertEqual(target_id, _target_document_id("assembly", "statement"))
        self.assertEqual(user_id, _user_document_id("assembly", "statement", "secret-user-id"))
        self.assertNotIn("secret-user-id", user_id)
        self.assertNotEqual(target_id, user_id)

    def test_render_requires_explicit_firebase_credentials(self):
        credential_variables = {
            "RENDER": "true",
            "GOOGLE_APPLICATION_CREDENTIALS": "",
            "FIREBASE_SERVICE_ACCOUNT_JSON": "",
        }
        with (
            patch.dict(os.environ, credential_variables, clear=False),
            patch.object(
                reaction_store,
                "DEFAULT_RENDER_CREDENTIALS_PATH",
                Path("/missing/firebase-service-account.json"),
            ),
        ):
            with self.assertRaises(ReactionStoreError):
                _credential_configuration()

    def test_rejects_project_id_that_differs_from_credentials(self):
        credential_variables = {
            "RENDER": "true",
            "GOOGLE_APPLICATION_CREDENTIALS": "",
            "FIREBASE_SERVICE_ACCOUNT_JSON": json.dumps(
                {"project_id": "credential-project"}
            ),
            "FIREBASE_PROJECT_ID": "different-project",
        }
        with (
            patch.dict(os.environ, credential_variables, clear=False),
            patch.object(
                reaction_store,
                "DEFAULT_RENDER_CREDENTIALS_PATH",
                Path("/missing/firebase-service-account.json"),
            ),
        ):
            _, inline_credentials, _ = _credential_configuration()
            with self.assertRaises(ReactionStoreError):
                reaction_store._configured_project_id(inline_credentials)

    def test_get_put_client_restart_get_keeps_persisted_reaction(self):
        persistent_firestore = {}

        def create_client():
            return _FakeFirestoreClient(persistent_firestore)

        with (
            patch.object(
                reaction_store, "get_firestore_client", side_effect=create_client
            ),
            patch.object(
                reaction_store,
                "_execute_transaction",
                side_effect=lambda transaction, callback: callback(transaction),
            ),
            patch.object(
                reaction_store,
                "_target_query",
                side_effect=lambda client, discussion_id: _fake_target_query(
                    persistent_firestore, discussion_id
                ),
            ),
        ):
            before_restart = list_reaction_states(
                discussion_id="restart-test-discussion",
                anonymous_user_id="restart-test-user",
            )
            self.assertEqual(before_restart, [])

            write_result = put_reaction_state(
                discussion_id="restart-test-discussion",
                statement_id="restart-test-statement",
                reaction_type="agree",
                anonymous_user_id="restart-test-user",
                base_counts={"agree": 7, "concern": 2, "helpful": 1},
            )
            self.assertEqual(write_result["storage_backend"], STORAGE_BACKEND)
            self.assertEqual(write_result["counts"]["agree"], 8)

            # A new client instance represents a fresh API process after restart.
            reaction_store._client = None
            after_restart = list_reaction_states(
                discussion_id="restart-test-discussion",
                anonymous_user_id="restart-test-user",
            )

        self.assertEqual(len(after_restart), 1)
        self.assertEqual(after_restart[0]["reaction_type"], "agree")
        self.assertEqual(after_restart[0]["live_counts"]["agree"], 1)
        self.assertEqual(after_restart[0]["counts"]["agree"], 8)

    def test_memory_fallback_when_firestore_is_unavailable(self):
        reaction_store._memory_targets.clear()
        reaction_store._memory_users.clear()
        with patch.object(
            reaction_store,
            "get_firestore_client",
            side_effect=ReactionStoreError("initialization failed"),
        ):
            write_result = put_reaction_state(
                discussion_id="memory-discussion",
                statement_id="memory-statement",
                reaction_type="agree",
                anonymous_user_id="memory-user",
                base_counts={"agree": 1, "concern": 0, "helpful": 0},
            )
            aggregates = list_reaction_states(
                discussion_id="memory-discussion",
                anonymous_user_id="memory-user",
            )

        self.assertEqual(write_result["storage_backend"], reaction_store.MEMORY_STORAGE_BACKEND)
        self.assertEqual(write_result["counts"]["agree"], 2)
        self.assertEqual(len(aggregates), 1)
        self.assertEqual(aggregates[0]["reaction_type"], "agree")

    def test_prefer_memory_store_skips_firestore(self):
        reaction_store._memory_targets.clear()
        reaction_store._memory_users.clear()
        with (
            patch.dict(os.environ, {"GIJIRAKU_PREFER_MEMORY_STORE": "1"}, clear=False),
            patch.object(
                reaction_store,
                "get_firestore_client",
                side_effect=AssertionError("Firestore should not be contacted"),
            ),
        ):
            write_result = put_reaction_state(
                discussion_id="prefer-memory-discussion",
                statement_id="prefer-memory-statement",
                reaction_type="concern",
                anonymous_user_id="prefer-memory-user",
                base_counts={"agree": 0, "concern": 0, "helpful": 0},
            )

        self.assertEqual(write_result["storage_backend"], reaction_store.MEMORY_STORAGE_BACKEND)
        self.assertEqual(write_result["counts"]["concern"], 1)


if __name__ == "__main__":
    unittest.main()

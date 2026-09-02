import unittest
import os
from copy import deepcopy
from unittest.mock import patch

import notification_store


class _FakeSnapshot:
    def __init__(self, reference, data):
        self.reference = reference
        self._data = deepcopy(data)
        self.exists = data is not None
        self.id = reference.id

    def to_dict(self):
        return deepcopy(self._data) if self._data is not None else None


class _FakeDocumentReference:
    def __init__(self, store, collection_name, document_id):
        self._store = store
        self._collection_name = collection_name
        self.id = document_id

    def get(self):
        return _FakeSnapshot(self, self._store.get((self._collection_name, self.id)))

    def set(self, payload):
        self._store[(self._collection_name, self.id)] = deepcopy(payload)


class _FakeCollection:
    def __init__(self, store, name):
        self._store = store
        self._name = name

    def document(self, document_id):
        return _FakeDocumentReference(self._store, self._name, document_id)

    def stream(self):
        return [
            _FakeSnapshot(
                _FakeDocumentReference(self._store, self._name, document_id),
                payload,
            )
            for (collection_name, document_id), payload in self._store.items()
            if collection_name == self._name
        ]


class _FakeFirestoreClient:
    def __init__(self, store):
        self._store = store

    def collection(self, name):
        return _FakeCollection(self._store, name)


class NotificationStoreTest(unittest.TestCase):
    def test_user_preferences_can_match_relevant_issue_notifications(self):
        store = {}
        client = _FakeFirestoreClient(store)

        with patch("notification_store.get_firestore_client", return_value=client):
            prefs_result = notification_store.save_user_preferences(
                "user-1",
                {
                    "interest_themes": ["子育て", "支援", "東京アプリ"],
                    "municipalities": ["東京都"],
                    "keywords": ["情報", "手続き"],
                },
            )
            matches = notification_store.match_issue_notifications("user-1")

        self.assertEqual(prefs_result["status"], "success")
        self.assertGreater(matches["total"], 0)
        self.assertTrue(any(item["issue_id"] == "tokyo-app-2026-06-16" for item in matches["matches"]))
        self.assertFalse(any(key[1] == "user-1" for key in store))
        self.assertTrue(all("anonymous_user_id" not in payload for payload in store.values()))

    def test_all_configured_filters_must_match(self):
        store = {}
        client = _FakeFirestoreClient(store)
        with patch("notification_store.get_firestore_client", return_value=client):
            notification_store.save_user_preferences(
                "user-2",
                {
                    "interest_themes": ["存在しないテーマ"],
                    "municipalities": ["東京都"],
                    "keywords": ["情報"],
                },
            )
            matches = notification_store.match_issue_notifications("user-2")

        self.assertEqual(matches["total"], 0)

    def test_empty_preferences_do_not_match_every_issue(self):
        store = {}
        client = _FakeFirestoreClient(store)
        with patch("notification_store.get_firestore_client", return_value=client):
            notification_store.save_user_preferences("user-3", {})
            matches = notification_store.match_issue_notifications("user-3")

        self.assertEqual(matches["matches"], [])

    def test_deployment_batch_uses_dynamic_catalog_and_is_idempotent(self):
        store = {}
        client = _FakeFirestoreClient(store)
        issues = [{
            "issue_id": "dynamic-issue",
            "title": "地域防災の見直し",
            "municipality": "A市議会",
            "assembly_id": "city-a",
            "status_summary": "答弁済み",
            "problem_summary": "避難所を改善する",
            "share_summary": "防災計画",
            "government_response_summary": "答弁済み",
            "theme": "防災・安全",
            "source_url": "https://example.com/source",
        }]
        with (
            patch("notification_store.get_firestore_client", return_value=client),
            patch("notification_store._issue_catalog_rows", return_value=issues),
            patch("line_notification_store.notify_line_for_match", return_value={"status": "skipped"}),
        ):
            notification_store.save_user_preferences(
                "user-4",
                {"interest_themes": ["防災"], "municipalities": ["city-a"], "keywords": ["避難"]},
            )
            first = notification_store.run_notification_matching(["dynamic-issue"])
            second = notification_store.run_notification_matching(["dynamic-issue"])

        notification_rows = [
            payload for (collection, _), payload in store.items()
            if collection == notification_store.NOTIFICATIONS_COLLECTION
        ]
        self.assertEqual(first["notification_count"], 1)
        self.assertEqual(second["notification_count"], 1)
        self.assertEqual(len(notification_rows), 1)
        self.assertEqual(notification_rows[0]["issue_id"], "dynamic-issue")

    def test_batch_key_is_required_and_compared(self):
        with patch.dict(os.environ, {"NOTIFICATION_BATCH_API_KEY": "secret"}, clear=False):
            with self.assertRaises(notification_store.NotificationBatchAuthorizationError):
                notification_store.authorize_notification_batch("wrong")
            notification_store.authorize_notification_batch("secret")

    def test_legacy_preferences_are_backfilled_during_batch(self):
        store = {}
        client = _FakeFirestoreClient(store)
        user_key = notification_store._user_document_id("legacy-user")
        store[(notification_store.USER_PREFERENCES_COLLECTION, user_key)] = {
            "interest_themes": ["防災"],
            "municipalities": [],
            "keywords": [],
        }
        issues = [{
            "issue_id": "legacy-match",
            "title": "防災計画",
            "municipality": "A市議会",
            "assembly_id": "city-a",
            "status_summary": "審議中",
            "problem_summary": "",
            "share_summary": "",
            "government_response_summary": "",
            "theme": "防災・安全",
            "source_url": "https://example.com/source",
        }]
        with (
            patch("notification_store.get_firestore_client", return_value=client),
            patch("notification_store._issue_catalog_rows", return_value=issues),
            patch("line_notification_store.notify_line_for_match", return_value={"status": "skipped"}),
        ):
            result = notification_store.run_notification_matching()

        self.assertEqual(result["subscription_count"], 1)
        self.assertEqual(result["notification_count"], 1)


if __name__ == "__main__":
    unittest.main()

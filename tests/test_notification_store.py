import unittest
from copy import deepcopy
from unittest.mock import patch

import notification_store


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


if __name__ == "__main__":
    unittest.main()

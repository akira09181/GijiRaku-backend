import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

import line_notification_store
from notification_store import _user_document_id


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

    def delete(self):
        self._store.pop((self._collection_name, self.id), None)


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


class LineNotificationStoreTest(unittest.TestCase):
    def test_link_and_status_round_trip(self):
        store = {}
        client = _FakeFirestoreClient(store)
        with patch("line_notification_store.get_firestore_client", return_value=client):
            linked = line_notification_store.link_line_user("user-1", "U123", display_name="市民A")
            status = line_notification_store.get_line_link_status("user-1")

        self.assertTrue(linked["line"]["linked"])
        self.assertEqual(linked["line"]["display_name"], "市民A")
        self.assertTrue(status["line"]["line_push_enabled"])

    def test_unlink_clears_status(self):
        store = {}
        client = _FakeFirestoreClient(store)
        with patch("line_notification_store.get_firestore_client", return_value=client):
            line_notification_store.link_line_user("user-1", "U123")
            unlinked = line_notification_store.unlink_line_user("user-1")
            status = line_notification_store.get_line_link_status("user-1")

        self.assertFalse(unlinked["line"]["linked"])
        self.assertFalse(status["line"]["linked"])

    def test_send_push_skips_without_token(self):
        with patch.dict("os.environ", {}, clear=False):
            result = line_notification_store.send_issue_notification_push(
                "U123",
                issue_id="issue-1",
                title="テスト議題",
            )
        self.assertEqual(result["status"], "skipped")

    def test_notify_line_for_match_sends_when_linked(self):
        store = {}
        client = _FakeFirestoreClient(store)
        user_key = _user_document_id("user-1")
        store[(line_notification_store.LINE_LINKS_COLLECTION, user_key)] = {
            "line_user_id": "U123",
            "line_push_enabled": True,
        }
        with (
            patch("line_notification_store.get_firestore_client", return_value=client),
            patch.dict("os.environ", {"LINE_CHANNEL_ACCESS_TOKEN": "token"}, clear=False),
            patch("line_notification_store.requests.post") as post_mock,
        ):
            post_mock.return_value = MagicMock(status_code=200, text="{}")
            result = line_notification_store.notify_line_for_match(
                user_key,
                {"issue_id": "issue-1", "title": "子育て支援", "municipality": "新宿区"},
            )

        self.assertEqual(result["status"], "sent")
        post_mock.assert_called_once()

    def test_exchange_line_login_code_uses_profile(self):
        token_response = MagicMock(status_code=200)
        token_response.json.return_value = {"access_token": "access-token"}
        profile_response = MagicMock(status_code=200)
        profile_response.json.return_value = {"userId": "U999", "displayName": "テスト"}
        with (
            patch.dict(
                "os.environ",
                {"LINE_LOGIN_CHANNEL_ID": "id", "LINE_CHANNEL_SECRET": "secret"},
                clear=False,
            ),
            patch("line_notification_store.requests.post", return_value=token_response),
            patch("line_notification_store.requests.get", return_value=profile_response),
        ):
            profile = line_notification_store.exchange_line_login_code(
                "auth-code",
                "https://example.com/line/callback",
            )

        self.assertEqual(profile["line_user_id"], "U999")
        self.assertEqual(profile["display_name"], "テスト")


if __name__ == "__main__":
    unittest.main()

from copy import deepcopy
import unittest
from unittest.mock import patch

import follow_store
import notification_store
from follow_store import (
    FOLLOWS_COLLECTION,
    ISSUES_COLLECTION,
    append_verified_status_update,
    delete_issue_follow,
    list_issue_follows,
    mark_issue_follow_viewed,
    put_issue_follow,
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

    def get(self):
        return _FakeSnapshot(self, self._store.get(self.key))

    def set(self, payload):
        self._store[self.key] = deepcopy(payload)

    def delete(self):
        self._store.pop(self.key, None)


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


class FollowStoreTest(unittest.TestCase):
    ISSUE_ID = "shinjuku-sick-child-care-2026-06-10"
    USER_ID = "anonymous-browser-a"

    def setUp(self):
        self.firestore = {}
        self.client = _FakeFirestoreClient(self.firestore)
        self.client_patch = patch.object(
            follow_store, "get_firestore_client", return_value=self.client
        )
        self.notification_client_patch = patch.object(
            notification_store, "get_firestore_client", return_value=self.client
        )
        self.client_patch.start()
        self.notification_client_patch.start()

    def tearDown(self):
        self.notification_client_patch.stop()
        self.client_patch.stop()

    def _snapshots_for_user(self):
        return [
            _FakeSnapshot(
                _FakeDocumentReference(self.firestore, collection, document_id),
                data,
            )
            for (collection, document_id), data in self.firestore.items()
            if collection == FOLLOWS_COLLECTION
            and data.get("anonymous_user_id") == self.USER_ID
        ]

    def test_duplicate_put_is_idempotent_and_preserves_created_at(self):
        first = put_issue_follow(issue_id=self.ISSUE_ID, anonymous_user_id=self.USER_ID)
        second = put_issue_follow(issue_id=self.ISSUE_ID, anonymous_user_id=self.USER_ID)

        documents = [
            data
            for (collection, _), data in self.firestore.items()
            if collection == FOLLOWS_COLLECTION
        ]
        self.assertEqual(len(documents), 1)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["follow"]["created_at"], second["follow"]["created_at"])
        self.assertEqual(
            first["follow"]["last_viewed_status_at"],
            first["follow"]["status_updated_at"],
        )
        self.assertNotIn("anonymous_user_id", second["follow"])
        issue_documents = [
            data
            for (collection, _), data in self.firestore.items()
            if collection == ISSUES_COLLECTION
        ]
        self.assertEqual(len(issue_documents), 1)

    def test_list_includes_my_response_without_exposing_uuid(self):
        put_issue_follow(issue_id=self.ISSUE_ID, anonymous_user_id=self.USER_ID)
        my_response = {
            "selected_answer": "needed",
            "selected_reasons": ["availability_unknown"],
            "free_text": "",
            "created_at": "2026-08-01T00:00:00+00:00",
            "updated_at": "2026-08-01T00:00:00+00:00",
        }
        with (
            patch.object(
                follow_store, "_follow_query", return_value=self._snapshots_for_user()
            ),
            patch.object(
                follow_store,
                "get_citizen_question_snapshot",
                return_value={
                    "my_response": my_response,
                    "aggregate": {"total_responses": 3},
                },
            ),
        ):
            result = list_issue_follows(anonymous_user_id=self.USER_ID)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["follows"][0]["my_response"], my_response)
        self.assertEqual(result["follows"][0]["current_response_count"], 3)
        self.assertNotIn("anonymous_user_id", result["follows"][0])

    def test_status_change_is_unread_until_detail_is_opened(self):
        put_issue_follow(issue_id=self.ISSUE_ID, anonymous_user_id=self.USER_ID)
        document = next(
            data
            for (collection, _), data in self.firestore.items()
            if collection == FOLLOWS_COLLECTION
        )
        document["last_viewed_status_at"] = "2026-01-01T00:00:00+00:00"
        issue_document = self.firestore[(ISSUES_COLLECTION, self.ISSUE_ID)]
        issue_document["status_updated_at"] = "2026-08-01T00:00:00+09:00"
        issue_document["current_status"] = "公式ページを更新"
        issue_document["status_summary"] = "受入状況の公式ページが更新されました。"
        issue_document["status_updates"] = [
            {
                "updated_at": "2026-08-01T00:00:00+09:00",
                "status": "公式ページを更新",
                "summary": "受入状況の公式ページが更新されました。",
                "source_url": "https://example.test/verified",
                "verified": True,
            },
            {
                "updated_at": "2026-08-02T00:00:00+09:00",
                "summary": "未確認の更新",
                "verified": False,
            },
        ]
        with (
            patch.object(
                follow_store,
                "_follow_query",
                return_value=self._snapshots_for_user(),
            ),
            patch.object(
                follow_store,
                "get_citizen_question_snapshot",
                return_value={
                    "my_response": None,
                    "aggregate": {"total_responses": 0},
                },
            ),
        ):
            before_open = list_issue_follows(anonymous_user_id=self.USER_ID)
        self.assertEqual(before_open["unread_total"], 1)
        self.assertEqual(len(before_open["follows"][0]["status_updates"]), 1)
        self.assertEqual(
            before_open["follows"][0]["status_updates"][0]["summary"],
            "受入状況の公式ページが更新されました。",
        )

        viewed = mark_issue_follow_viewed(
            issue_id=self.ISSUE_ID, anonymous_user_id=self.USER_ID
        )
        self.assertFalse(viewed["follow"]["has_new_status"])

    def test_list_never_returns_another_users_follow(self):
        put_issue_follow(issue_id=self.ISSUE_ID, anonymous_user_id=self.USER_ID)
        put_issue_follow(issue_id=self.ISSUE_ID, anonymous_user_id="anonymous-browser-b")
        with (
            patch.object(
                follow_store, "_follow_query", return_value=self._snapshots_for_user()
            ),
            patch.object(
                follow_store,
                "get_citizen_question_snapshot",
                return_value={
                    "my_response": None,
                    "aggregate": {"total_responses": 0},
                },
            ),
        ):
            result = list_issue_follows(anonymous_user_id=self.USER_ID)

        self.assertEqual(result["total"], 1)
        self.assertNotIn("anonymous_user_id", result["follows"][0])

    def test_delete_removes_follow_without_touching_other_data(self):
        put_issue_follow(issue_id=self.ISSUE_ID, anonymous_user_id=self.USER_ID)
        self.firestore[("other_collection", "record")] = {"kept": True}

        result = delete_issue_follow(
            issue_id=self.ISSUE_ID, anonymous_user_id=self.USER_ID
        )

        self.assertTrue(result["deleted"])
        self.assertFalse(
            any(key[0] == FOLLOWS_COLLECTION for key in self.firestore)
        )
        self.assertEqual(self.firestore[("other_collection", "record")], {"kept": True})
        self.assertIn((ISSUES_COLLECTION, self.ISSUE_ID), self.firestore)

    def test_status_update_notifies_followers(self):
        put_issue_follow(issue_id=self.ISSUE_ID, anonymous_user_id=self.USER_ID)
        put_issue_follow(issue_id=self.ISSUE_ID, anonymous_user_id="anonymous-browser-b")
        with patch("line_notification_store.notify_line_for_match", return_value={"status": "skipped"}):
            result = append_verified_status_update(
                self.ISSUE_ID,
                status="公式ページを更新",
                summary="病児保育の空き状況ページが公式に更新されました。",
                source_url="https://example.test/shinjuku-status-update",
                updated_at="2026-09-02T00:00:00+09:00",
            )
        self.assertEqual(result["delivery"]["follower_count"], 2)
        self.assertEqual(result["delivery"]["notification_count"], 2)
        issue = self.firestore[(ISSUES_COLLECTION, self.ISSUE_ID)]
        self.assertEqual(issue["current_status"], "公式ページを更新")
        self.assertEqual(len(issue["status_updates"]), 2)


if __name__ == "__main__":
    unittest.main()

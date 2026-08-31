"""Opt-in Firestore persistence test across fresh API processes.

Run with real Firebase credentials:

    RUN_FIRESTORE_INTEGRATION_TEST=1 python -m unittest \
      tests.test_reaction_persistence_integration -v
"""

from __future__ import annotations

import multiprocessing
import os
import unittest
import uuid


def _get_from_fresh_api_process(queue, discussion_id, user_id):
    try:
        from main import get_reactions

        queue.put(get_reactions(discussion_id, user_id, True))
    except Exception as exc:  # pragma: no cover - returned to the parent process.
        queue.put({"error": repr(exc)})


def _put_from_fresh_api_process(queue, discussion_id, statement_id, user_id):
    try:
        from main import ReactionStateRequest, put_reaction

        request = ReactionStateRequest(
            discussion_id=discussion_id,
            statement_id=statement_id,
            reaction_type="agree",
            anonymous_user_id=user_id,
            base_counts={"agree": 0, "concern": 0, "helpful": 0},
        )
        queue.put(put_reaction(request))
    except Exception as exc:  # pragma: no cover - returned to the parent process.
        queue.put({"error": repr(exc)})


@unittest.skipUnless(
    os.getenv("RUN_FIRESTORE_INTEGRATION_TEST") == "1",
    "requires explicit opt-in and real Firestore credentials",
)
class FirestoreApiRestartPersistenceTest(unittest.TestCase):
    def _run_process(self, target, *args):
        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        process = context.Process(target=target, args=(queue, *args))
        process.start()
        process.join(timeout=90)
        self.assertFalse(process.is_alive(), "API test process timed out")
        self.assertEqual(process.exitcode, 0)
        result = queue.get(timeout=5)
        self.assertNotIn("error", result, result.get("error"))
        return result

    def _delete_test_documents(self, discussion_id, statement_id, user_id):
        from reaction_store import (
            TARGETS_COLLECTION,
            USERS_COLLECTION,
            _target_document_id,
            _user_document_id,
            get_firestore_client,
        )

        client = get_firestore_client()
        client.collection(USERS_COLLECTION).document(
            _user_document_id(discussion_id, statement_id, user_id)
        ).delete()
        client.collection(TARGETS_COLLECTION).document(
            _target_document_id(discussion_id, statement_id)
        ).delete()

    def test_get_put_api_restart_get_preserves_vote(self):
        suffix = uuid.uuid4().hex
        discussion_id = f"persistence-integration-{suffix}"
        statement_id = f"statement-{suffix}"
        user_id = f"user-{suffix}"
        self.addCleanup(
            self._delete_test_documents, discussion_id, statement_id, user_id
        )

        initial = self._run_process(
            _get_from_fresh_api_process, discussion_id, user_id
        )
        self.assertEqual(initial["storage_backend"], "firestore")
        self.assertEqual(initial["aggregates"], [])
        self.assertEqual(initial["user_reactions"], [])

        written = self._run_process(
            _put_from_fresh_api_process,
            discussion_id,
            statement_id,
            user_id,
        )
        self.assertEqual(written["storage_backend"], "firestore")
        self.assertEqual(written["live_counts"]["agree"], 1)

        # This GET runs in another fresh Python process, equivalent to an API restart.
        reloaded = self._run_process(
            _get_from_fresh_api_process, discussion_id, user_id
        )
        persisted = next(
            item
            for item in reloaded["aggregates"]
            if item["statement_id"] == statement_id
        )
        user_reaction = next(
            item
            for item in reloaded["user_reactions"]
            if item["statement_id"] == statement_id
        )
        self.assertEqual(reloaded["storage_backend"], "firestore")
        self.assertEqual(persisted["live_counts"]["agree"], 1)
        self.assertEqual(user_reaction["reaction_type"], "agree")

if __name__ == "__main__":
    unittest.main()

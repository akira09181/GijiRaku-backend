import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main
from reaction_store import ReactionStoreError


class ReactionApiTest(unittest.TestCase):
    def test_get_identifies_firestore_backend(self):
        with patch.object(main, "list_reaction_states", return_value=[]):
            response = main.get_reactions("discussion", "anonymous-user")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["storage_backend"], "firestore")
        self.assertEqual(response["data"], [])

    def test_get_returns_500_when_firestore_is_unavailable(self):
        with patch.object(
            main,
            "list_reaction_states",
            side_effect=ReactionStoreError("initialization failed"),
        ):
            with self.assertRaises(HTTPException) as raised:
                main.get_reactions("discussion", "anonymous-user")

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(
            raised.exception.detail, "Firestore reaction store unavailable"
        )

    def test_put_returns_500_when_firestore_is_unavailable(self):
        request = main.ReactionStateRequest(
            discussion_id="discussion",
            statement_id="statement",
            reaction_type="agree",
            anonymous_user_id="anonymous-user",
        )
        with patch.object(
            main,
            "put_reaction_state",
            side_effect=ReactionStoreError("initialization failed"),
        ):
            with self.assertRaises(HTTPException) as raised:
                main.put_reaction(request)

        self.assertEqual(raised.exception.status_code, 500)

    def test_legacy_in_memory_reaction_endpoints_are_disabled(self):
        request = main.UtteranceReactionRequest(reaction_type="agree")
        with self.assertRaises(HTTPException) as post_error:
            main.post_statement_reaction("statement", request)
        with self.assertRaises(HTTPException) as get_error:
            main.get_statement_reactions("statement")

        self.assertEqual(post_error.exception.status_code, 410)
        self.assertEqual(get_error.exception.status_code, 410)


if __name__ == "__main__":
    unittest.main()

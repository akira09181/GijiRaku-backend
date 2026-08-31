import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main
from reaction_store import ReactionStoreError


class ReactionApiTest(unittest.TestCase):
    def test_get_identifies_firestore_backend(self):
        aggregates = [
            {
                "statement_id": "statement",
                "counts": {"agree": 4, "concern": 2, "helpful": 1},
                "live_counts": {"agree": 4, "concern": 2, "helpful": 1},
            }
        ]
        user_reactions = [
            {"statement_id": "statement", "reaction_type": "agree"}
        ]
        with (
            patch.object(main, "list_reaction_aggregates", return_value=aggregates),
            patch.object(
                main, "list_user_reaction_states", return_value=user_reactions
            ),
        ):
            response = main.get_reactions("discussion", "anonymous-user")

        self.assertEqual(response["status"], "success")
        self.assertEqual(response["storage_backend"], "firestore")
        self.assertEqual(response["aggregates"], aggregates)
        self.assertEqual(response["user_reactions"], user_reactions)
        self.assertEqual(response["data"][0]["reaction_type"], "agree")

    def test_aggregate_only_get_does_not_require_or_query_user_id(self):
        with (
            patch.object(main, "list_reaction_aggregates", return_value=[]),
            patch.object(main, "list_user_reaction_states") as user_query,
        ):
            response = main.get_reactions(
                "discussion", anonymous_user_id=None, include_user_state=False
            )

        self.assertEqual(response["aggregates"], [])
        self.assertEqual(response["user_reactions"], [])
        user_query.assert_not_called()

    def test_get_returns_500_when_firestore_is_unavailable(self):
        with patch.object(
            main,
            "list_reaction_aggregates",
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

    def test_citizen_question_get_keeps_my_response_separate_from_aggregate(self):
        expected = {
            "status": "success",
            "storage_backend": "firestore",
            "my_response": {"selected_answer": "needed"},
            "aggregate": {"total_responses": 3},
        }
        with patch.object(
            main, "get_citizen_question_snapshot", return_value=expected
        ) as store_get:
            response = main.get_citizen_question_answer(
                "issue", "question", "anonymous-user"
            )

        self.assertEqual(response, expected)
        store_get.assert_called_once_with(
            issue_id="issue",
            question_id="question",
            anonymous_user_id="anonymous-user",
        )

    def test_citizen_question_get_returns_500_instead_of_zero_on_store_failure(self):
        with patch.object(
            main,
            "get_citizen_question_snapshot",
            side_effect=ReactionStoreError("initialization failed"),
        ):
            with self.assertRaises(HTTPException) as raised:
                main.get_citizen_question_answer(
                    "issue", "question", "anonymous-user"
                )

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(
            raised.exception.detail,
            "Firestore citizen response store unavailable",
        )


if __name__ == "__main__":
    unittest.main()

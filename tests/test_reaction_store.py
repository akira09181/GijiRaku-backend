import unittest

from reaction_store import (
    _combined_counts,
    _target_document_id,
    _transition_live_counts,
    _user_document_id,
)


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


if __name__ == "__main__":
    unittest.main()

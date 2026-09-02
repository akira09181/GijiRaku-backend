import os
import unittest
from unittest.mock import patch

import store_mode


class StoreModeTest(unittest.TestCase):
    def test_prefer_memory_store_reads_env(self):
        with patch.dict(os.environ, {"GIJIRAKU_PREFER_MEMORY_STORE": "1"}, clear=False):
            self.assertTrue(store_mode.prefer_memory_store())
            self.assertEqual(store_mode.active_storage_backend(), "memory-fallback")

    def test_prefer_memory_store_defaults_to_firestore(self):
        with patch.dict(os.environ, {"GIJIRAKU_PREFER_MEMORY_STORE": ""}, clear=False):
            self.assertFalse(store_mode.prefer_memory_store())
            self.assertEqual(store_mode.active_storage_backend(), "firestore")


if __name__ == "__main__":
    unittest.main()

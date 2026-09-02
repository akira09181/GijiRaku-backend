import unittest
from unittest.mock import MagicMock, patch

import region_request_store


class RegionRequestStoreTests(unittest.TestCase):
    @patch("region_request_store.get_firestore_client")
    def test_save_region_request_is_idempotent(self, mock_client_factory):
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc.to_dict.return_value = {}
        mock_reference = MagicMock()
        mock_reference.get.return_value = mock_doc
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_reference
        mock_client = MagicMock()
        mock_client.collection.return_value = mock_collection
        mock_client_factory.return_value = mock_client

        first = region_request_store.save_region_request(
            municipality_id="chiyoda-ward",
            municipality_name="千代田区議会",
            email="Citizen@Example.com",
            message="導入希望",
            anonymous_user_id="anon-1",
        )
        second = region_request_store.save_region_request(
            municipality_id="chiyoda-ward",
            municipality_name="千代田区議会",
            email="citizen@example.com",
            message="更新",
            anonymous_user_id="anon-1",
        )

        self.assertEqual(first["request_id"], second["request_id"])
        mock_reference.set.assert_called()
        saved = mock_reference.set.call_args[0][0]
        self.assertEqual(saved["municipality_id"], "chiyoda-ward")
        self.assertEqual(saved["email"], "citizen@example.com")
        self.assertEqual(saved["message"], "更新")


if __name__ == "__main__":
    unittest.main()

import unittest
from copy import deepcopy
from unittest.mock import patch

import lead_store


class _Snapshot:
    def __init__(self, data):
        self._data = deepcopy(data)
        self.exists = data is not None

    def to_dict(self):
        return deepcopy(self._data)


class _Document:
    def __init__(self, store, key):
        self.store = store
        self.key = key

    def get(self):
        return _Snapshot(self.store.get(self.key))

    def set(self, payload):
        self.store[self.key] = deepcopy(payload)


class _Collection:
    def __init__(self, store, name):
        self.store = store
        self.name = name

    def document(self, document_id):
        return _Document(self.store, (self.name, document_id))


class _Client:
    def __init__(self):
        self.store = {}

    def collection(self, name):
        return _Collection(self.store, name)


class LeadStoreTest(unittest.TestCase):
    def test_same_organization_and_email_updates_idempotently(self):
        client = _Client()
        with patch("lead_store.get_firestore_client", return_value=client):
            first = lead_store.save_pro_lead(
                organization="A市", name="担当者", email="Test@Example.com", purpose="導入相談",
            )
            second = lead_store.save_pro_lead(
                organization="A市", name="別担当者", email="test@example.com", purpose="資料希望",
            )

        self.assertEqual(first["lead_id"], second["lead_id"])
        self.assertEqual(len(client.store), 1)
        payload = next(iter(client.store.values()))
        self.assertEqual(payload["email"], "test@example.com")
        self.assertEqual(payload["name"], "別担当者")


if __name__ == "__main__":
    unittest.main()

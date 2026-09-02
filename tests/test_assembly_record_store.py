import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import assembly_records
from assembly_record_store import (
    AssemblyRecordStoreError,
    clear_firestore_dataset_cache,
    load_firestore_dataset,
    save_firestore_dataset,
)


class _Snapshot:
    def __init__(self, document_id, data):
        self.id = document_id
        self._data = deepcopy(data) if data is not None else None
        self.exists = data is not None

    def to_dict(self):
        return deepcopy(self._data)


class _Document:
    def __init__(self, client, path):
        self.client = client
        self.path = path

    def set(self, data):
        self.client.store[self.path] = deepcopy(data)

    def get(self):
        return _Snapshot(self.path[-1], self.client.store.get(self.path))

    def collection(self, name):
        return _Collection(self.client, self.path + (name,))


class _Collection:
    def __init__(self, client, path, predicate=None):
        self.client = client
        self.path = path
        self.predicate = predicate

    def document(self, document_id):
        return _Document(self.client, self.path + (document_id,))

    def where(self, field, operator, value):
        if operator != "==":
            raise AssertionError(operator)
        return _Collection(
            self.client,
            self.path,
            lambda data: data.get(field) == value,
        )

    def stream(self):
        snapshots = []
        for path, data in self.client.store.items():
            if len(path) != len(self.path) + 1 or path[:-1] != self.path:
                continue
            if self.predicate is None or self.predicate(data):
                snapshots.append(_Snapshot(path[-1], data))
        return snapshots


class _Batch:
    def __init__(self):
        self.writes = []

    def set(self, reference, data):
        self.writes.append((reference, deepcopy(data)))

    def commit(self):
        for reference, data in self.writes:
            reference.set(data)


class _FirestoreClient:
    def __init__(self):
        self.store = {}

    def collection(self, name):
        return _Collection(self, (name,))

    def batch(self):
        return _Batch()


def _dataset(record_count=2):
    records = [
        {
            "discussion_id": f"issue-{index}",
            "meeting_date": f"2026-01-0{index + 1}",
            "publication_status": "published",
            "statements": [{"statement_id": f"statement-{index}"}],
        }
        for index in range(record_count)
    ]
    records.reverse()
    return {
        "schema_version": 1,
        "updated_at": "2026-09-02T09:00:00+09:00",
        "assemblies": {
            "test-assembly": {
                "assembly_name": "テスト議会",
                "source": {"provider": "test"},
                "records": records,
            }
        },
    }


class AssemblyRecordFirestoreStoreTest(unittest.TestCase):
    def tearDown(self):
        clear_firestore_dataset_cache()

    def test_versioned_migration_round_trips_exact_dataset(self):
        client = _FirestoreClient()
        dataset = _dataset()

        result = save_firestore_dataset(dataset, client=client)
        actual = load_firestore_dataset(client=client, use_cache=False)

        self.assertEqual(actual, dataset)
        self.assertEqual(result["assembly_count"], 1)
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["statement_count"], 2)

    def test_old_version_document_is_not_mixed_after_a_record_is_removed(self):
        client = _FirestoreClient()
        save_firestore_dataset(_dataset(2), client=client)
        latest = _dataset(1)
        latest["updated_at"] = "2026-09-03T09:00:00+09:00"

        save_firestore_dataset(latest, client=client)

        self.assertEqual(load_firestore_dataset(client=client, use_cache=False), latest)

    def test_firestore_backend_can_fall_back_to_the_json_snapshot(self):
        dataset = _dataset()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "records.json"
            path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
            with (
                patch.dict(
                    "os.environ",
                    {
                        "ASSEMBLY_RECORDS_BACKEND": "firestore",
                        "ASSEMBLY_RECORDS_JSON_FALLBACK": "1",
                        "GIJIRAKU_ASSEMBLY_RECORDS_PATH": str(path),
                    },
                    clear=False,
                ),
                patch(
                    "assembly_records.load_firestore_dataset",
                    side_effect=AssemblyRecordStoreError("offline"),
                ),
            ):
                self.assertEqual(assembly_records.load_dataset(), dataset)
                self.assertEqual(assembly_records.get_active_storage_backend(), "json-fallback")

    def test_firestore_backend_is_reported_after_a_successful_read(self):
        dataset = _dataset()
        with (
            patch.dict(
                "os.environ",
                {"ASSEMBLY_RECORDS_BACKEND": "firestore"},
                clear=False,
            ),
            patch("assembly_records.load_firestore_dataset", return_value=dataset),
        ):
            self.assertEqual(assembly_records.load_dataset(), dataset)
            self.assertEqual(assembly_records.get_active_storage_backend(), "firestore")

    def test_render_defaults_to_auto_and_synchronizes_a_changed_snapshot(self):
        source = _dataset()
        previous = _dataset(1)
        migrated = {
            "dataset_version": "version",
            "document_writes": 3,
            "dry_run": False,
        }
        with (
            patch.dict("os.environ", {"RENDER": "true"}, clear=True),
            patch("assembly_records._load_json_dataset", return_value=source),
            patch(
                "assembly_records.load_firestore_dataset",
                side_effect=[previous, source],
            ),
            patch("assembly_records.save_firestore_dataset", return_value=migrated) as save,
        ):
            result = assembly_records.sync_json_snapshot_to_firestore()

        save.assert_called_once_with(source)
        self.assertEqual(result["status"], "synchronized")
        self.assertEqual(result["storage_backend"], "firestore")

    def test_firestore_backend_can_fail_closed_after_cutover(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "ASSEMBLY_RECORDS_BACKEND": "firestore",
                    "ASSEMBLY_RECORDS_JSON_FALLBACK": "0",
                },
                clear=False,
            ),
            patch(
                "assembly_records.load_firestore_dataset",
                side_effect=AssemblyRecordStoreError("offline"),
            ),
            self.assertRaises(AssemblyRecordStoreError),
        ):
            assembly_records.load_dataset()


if __name__ == "__main__":
    unittest.main()

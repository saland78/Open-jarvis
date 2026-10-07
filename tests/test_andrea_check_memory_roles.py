"""Owned synthetic entry, finite requests and safe cleanup in production check."""
from contextlib import redirect_stdout
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts/andrea"))
import check_memory_roles as check
import check_memory_attribution as historical
from manual_memory import ManualMemory

ROOT = Path(__file__).resolve().parents[1]


class ProductionRecallCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = ManualMemory(Path(self.tmp.name)/"state")
        self.mutations = []
        self.requests = []

    def api(self, payload=None):
        if payload is None: return self.store.snapshot()
        self.mutations.append(payload)
        return self.store.mutate(payload)

    def request(self, payload, **kwargs):
        self.requests.append(payload)
        self.assertEqual(list(payload), ["model", "stream", "messages"])
        self.assertEqual([m["role"] for m in payload["messages"]], ["user"])
        self.assertEqual(self.store.snapshot()["records"][0]["text"], check.CASES[len(self.requests)-1]["text"])
        return {"done": True, "finishReason": "stop", "answer": "Ho scelto viola.", "requestId": "PRIVATE ID",
                "server": {"memoryContextSupplied": True, "memoryProvenanceFooterAdded": True, "id": "PRIVATE ID"}}

    def collect(self, request=None):
        with redirect_stdout(io.StringIO()):
            return check.collect(self.api, request or self.request)

    def test_same_criteria_exact_source_hashes_and_three_requests_with_owned_cleanup(self):
        self.assertEqual(check.CASES, historical.CASES)
        for relative, digest in check.EXPECTED.items():
            self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(), digest)
        client = check.load_client(ROOT)
        self.assertTrue(callable(client.run_request))
        result = self.collect()
        self.assertEqual(len(self.requests), 3)
        self.assertEqual([m["action"] for m in self.mutations], ["create", "update", "update", "delete"])
        self.assertEqual(result["cleanup"], "deleted_owned_synthetic_entry")
        self.assertTrue(result["memoryEmptyAfter"])
        self.assertEqual(self.store.snapshot()["revision"], 4)
        self.assertEqual(result["rows"][0]["syntheticAnswer"], "Ho scelto viola.")
        self.assertTrue(all(row["qualityVerdict"] == "pending_review" for row in result["rows"]))
        self.assertNotIn("PRIVATE ID", str(result))

    def test_nonempty_private_memory_blocks_all_writes_and_requests(self):
        self.store.mutate({"action": "create", "revision": 0, "record": {"kind": "fact", "topic": "Private", "text": "Private value", "active": False}})
        before = self.store.path.read_bytes()
        with self.assertRaises(ValueError): self.collect()
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(self.mutations, [])
        self.assertEqual(self.requests, [])

    def test_an_external_edit_stops_series_and_is_not_deleted(self):
        def request(payload, **kwargs):
            result = self.request(payload, **kwargs)
            row = self.store.snapshot()["records"][0]
            self.store.mutate({"action": "update", "revision": 1, "id": row["id"],
                               "record": {"kind": "correction", "topic": "User edit", "text": "Keep this change", "active": True}})
            return result
        result = self.collect(request)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(result["cleanup"], "skipped_state_changed")
        self.assertEqual(self.store.snapshot()["records"][0]["text"], "Keep this change")
        self.assertFalse(result["memoryEmptyAfter"])
        self.assertEqual(len(result["rows"]), 1)

    def test_failed_request_retained_no_retry_and_entry_cleaned(self):
        def request(payload, **kwargs):
            value = self.request(payload, **kwargs)
            if len(self.requests) == 1: raise RuntimeError("failed once")
            return value
        result = self.collect(request)
        self.assertEqual(len(self.requests), 3)
        self.assertEqual(result["rows"][0]["qualityVerdict"], "not_assessable")
        self.assertEqual(result["cleanup"], "deleted_owned_synthetic_entry")
        self.assertEqual(self.store.snapshot()["records"], [])

    def test_interrupt_cleans_only_unchanged_owned_entry(self):
        def request(payload, **kwargs):
            self.requests.append(payload)
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt): self.collect(request)
        self.assertEqual(self.store.snapshot()["records"], [])
        self.assertEqual(len(self.requests), 1)


if __name__ == "__main__": unittest.main()

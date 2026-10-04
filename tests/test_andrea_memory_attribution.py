"""Finite candidate collection and ASGI delivery, not a semantic model judge."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/andrea"))
import check_memory_attribution as probe
import manual_memory
from runtime import LocalMode

ROOT = Path(__file__).resolve().parents[1]


class AttributionCollectionTests(unittest.TestCase):
    def collect(self, request, read=lambda: {"revision": 3, "records": []}):
        with redirect_stdout(io.StringIO()):
            return probe.collect(manual_memory, request, read)

    def test_exact_baseline_loaded_and_source_not_changed(self):
        before = {path: (ROOT/path).read_bytes() for path in probe.EXPECTED}
        client, memory = probe.load_verified(ROOT)
        self.assertTrue(callable(client.run_request))
        for case in probe.CASES:
            payload = probe.payload(memory, case)
            self.assertEqual(payload["messages"][1], {"role": "user", "content": case["query"]})
            raw = payload["messages"][0]["content"].split("\n")[-1]
            self.assertEqual(json.loads(raw)[0]["text"], case["text"])
            self.assertNotIn("tools", payload)
            self.assertNotIn("notes_query", payload)
        for relative, data in before.items():
            self.assertEqual((ROOT/relative).read_bytes(), data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), probe.EXPECTED[relative])

    def test_three_requests_no_retry_and_success_not_quality_certification(self):
        calls = []
        def request(payload, *, keep_answer):
            calls.append(payload)
            return {"done": True, "finishReason": "stop", "answer": "Ho scelto verde.",
                    "requestId": "MUST NOT BE PUBLISHED", "server": {"id": "PRIVATE"}}
        result = self.collect(request)
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["executed"], 3)
        self.assertTrue(result["emptyMemoryRevisionUnchanged"])
        self.assertTrue(all(row["transportCompleted"] for row in result["rows"]))
        self.assertTrue(all(row["qualityVerdict"] == "pending_review" for row in result["rows"]))
        self.assertEqual(result["rows"][0]["syntheticAnswer"], "Ho scelto verde.")
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("MUST NOT", json.dumps(result))

    def test_nonempty_memory_blocks_before_first_inference(self):
        calls = []
        with self.assertRaises(ValueError):
            self.collect(lambda *a, **k: calls.append(a), lambda: {"revision": 1, "records": [{"text": "private"}]})
        self.assertEqual(calls, [])

    def test_revision_change_keeps_completed_row_and_stops_remaining_requests(self):
        snapshots = iter([{"revision": 3, "records": []}, {"revision": 3, "records": []},
                          {"revision": 4, "records": []}, {"revision": 4, "records": []}])
        calls = []
        def request(payload, **kwargs):
            calls.append(payload)
            return {"done": True, "finishReason": "stop", "answer": "Prima risposta"}
        result = self.collect(request, lambda: next(snapshots))
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["rows"][0]["syntheticAnswer"], "Prima risposta")
        self.assertEqual(result["stoppedReason"], "memory_state_changed_or_unavailable")
        self.assertFalse(result["emptyMemoryRevisionUnchanged"])

    def test_failed_and_truncated_cases_retained_without_repeating(self):
        count = 0
        def request(payload, **kwargs):
            nonlocal count
            count += 1
            if count == 1: raise RuntimeError("synthetic failure")
            return {"done": True, "finishReason": "length", "answer": "partial"}
        result = self.collect(request)
        self.assertEqual(count, 3)
        self.assertEqual(len(result["rows"]), 3)
        self.assertEqual(result["rows"][0]["qualityVerdict"], "not_assessable")
        self.assertTrue(all(not row["transportCompleted"] for row in result["rows"]))

    def test_redirects_are_refused(self):
        with self.assertRaises(ValueError):
            probe.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.test")


class AttributionDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_production_chat_delivers_candidate_with_literal_subjects_and_no_persistent_write(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)/"state"
            store = manual_memory.ManualMemory(state)
            calls = []
            async def sink(scope, receive, send):
                calls.append(json.loads((await receive())["body"]))
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b"data: [DONE]\n\n"})
            app = LocalMode(sink, probe.MODEL, 8008, memory=store)
            for case in probe.CASES:
                body = json.dumps(probe.payload(manual_memory, case)).encode()
                events = []
                async def receive(): return {"type": "http.request", "body": body}
                async def send(event): events.append(event)
                await app({"type": "http", "method": "POST", "path": "/v1/chat/completions",
                           "headers": [(b"host", b"127.0.0.1:8008"), (b"origin", probe.BASE.encode()),
                                       (b"content-type", b"application/json")]}, receive, send)
                self.assertEqual(events[0]["status"], 200)
                message = calls[-1]["messages"][0]["content"]
                self.assertIn(probe.ROLE_GUIDANCE, message)
                self.assertEqual(json.loads(message.split("\n")[-1])[0]["text"], case["text"])
                self.assertEqual(calls[-1]["messages"][1]["content"], case["query"])
                self.assertEqual(calls[-1]["max_tokens"], 512)
                self.assertFalse(calls[-1].get("tools"))
            self.assertEqual(len(calls), 3)
            self.assertFalse(state.exists())


if __name__ == "__main__": unittest.main()

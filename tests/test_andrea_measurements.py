"""Request timing, privacy and protocol regressions without real Ollama."""
import asyncio
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/andrea"))
from measurements import LocalMeasurements, RequestMeasurement
from runtime import LocalMode
from collaudo import formal_checks


class MeasurementTests(unittest.TestCase):
    def test_sources_roles_and_empty_content_do_not_count_as_first_text(self):
        tick = [10.0]
        trace = RequestMeasurement("notes", "model", clock=lambda: tick[0])
        tick[0] = 11
        trace.retrieval(10, {"sources": [{"text": "PRIVATE"}], "partial": False})
        trace.generation()
        trace.http_status = 200
        trace.feed(b'event: local_sources\ndata: {"text":"PRIVATE"}\n\n')
        trace.feed(b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n')
        trace.feed(b'data: {"choices":[{"delta":{"content":""}}]}\n\n')
        self.assertIsNone(trace.record["firstTextMs"])
        tick[0] = 12
        content = b'data: {"choices":[{"delta":{"content":"PRIVATE"}}]}\n\n'
        trace.feed(content[:17])
        trace.feed(content[17:])
        tick[0] = 13
        trace.feed(b'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"completion_tokens":3,"prompt":"PRIVATE"}}\n\ndata: [DONE]\n\n')
        record = trace.finish()
        self.assertEqual(record["firstTextMs"], 2000)
        self.assertEqual(record["generationFirstTextMs"], 1000)
        self.assertEqual(record["retrievalMs"], 1000)
        self.assertEqual(record["totalMs"], 3000)
        self.assertEqual(record["usage"], {"completion_tokens": 3})
        self.assertEqual(record["status"], "completed")
        self.assertNotIn("PRIVATE", json.dumps(record))
        self.assertEqual(trace.buffer, b"")

    def test_truncation_and_missing_done_are_not_completion(self):
        for reason, done, expected in (("length", True, "truncated"), ("stop", False, "incomplete")):
            trace = RequestMeasurement("chat", "model")
            trace.http_status = 200
            trace.feed(('data: '+json.dumps({"choices": [{"delta":{"content":"text"},"finish_reason":reason}]})+'\n\n').encode())
            if done:
                trace.feed(b'data: [DONE]\n\n')
            self.assertEqual(trace.finish()["status"], expected)

    def test_buffer_is_bounded_and_error_content_is_not_saved(self):
        trace = RequestMeasurement("chat", "model")
        trace.feed(b'x' * 70000)
        self.assertLessEqual(len(trace.buffer), 65536)
        trace.feed(b'data: {"error":{"message":"PRIVATE"}}\n\n')
        self.assertEqual(trace.finish()["status"], "error")
        self.assertNotIn("PRIVATE", json.dumps(trace.record))

    def test_retention_is_last_fifty_not_persistent_content(self):
        store = LocalMeasurements()
        for i in range(60):
            store.add({"id": i})
        self.assertEqual(len(store.snapshot()["records"]), 50)
        self.assertEqual(store.snapshot()["records"][0]["id"], 10)

    def test_formal_checks_do_not_judge_fact_meaning(self):
        case = {"sources": [{"id":"N1"}], "expectedCitations": ["N1"]}
        result = {"answer":"Zero libri [N1].", "done": True, "finishReason":"stop"}
        self.assertTrue(all(formal_checks(case, result).values()))
        self.assertNotIn("qualityVerdict", formal_checks(case, result))


class BoundaryMeasurementTests(unittest.IsolatedAsyncioTestCase):
    async def invoke(self, app, send_body, *, path="/v1/chat/completions", method="POST", host="127.0.0.1:8008"):
        events = []
        sent = False
        async def receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type":"http.request", "body":json.dumps(send_body).encode()}
            await asyncio.Event().wait()
        async def send(event):
            events.append(event)
        scope = {"type":"http", "method":method, "path":path,
                 "headers":[(b"host", host.encode()),(b"origin",b"http://127.0.0.1:8008"),(b"content-type",b"application/json")]}
        await app(scope, receive, send)
        return events

    def payload(self):
        return {"model":"model", "stream":True, "messages":[{"role":"user","content":"PRIVATE"}]}

    async def test_real_asgi_stream_record_correlates_and_endpoint_respects_host(self):
        async def upstream(scope, receive, send):
            await receive()
            await send({"type":"http.response.start","status":200,"headers":[]})
            await send({"type":"http.response.body","body":b'data: {"choices":[{"delta":{"content":"PRIVATE"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'})
        app = LocalMode(upstream, "model", 8008)
        events = await self.invoke(app, self.payload())
        request_id = dict(events[0]["headers"])[b"x-openjarvis-request-id"].decode()
        record = app.measurements.snapshot()["records"][0]
        self.assertEqual(record["id"], request_id)
        self.assertEqual(record["status"], "completed")
        self.assertNotIn("PRIVATE", json.dumps(record))
        endpoint = await self.invoke(app, {}, path="/api/andrea/metrics", method="GET")
        self.assertEqual(json.loads(endpoint[1]["body"])["records"][0]["id"], request_id)
        denied = await self.invoke(app, {}, path="/api/andrea/metrics", method="GET", host="evil.example")
        self.assertEqual(denied[0]["status"], 403)
        self.assertFalse(app.busy)

    async def test_timeout_and_cancel_reset_busy_and_keep_distinct_statuses(self):
        async def upstream(scope, receive, send):
            await asyncio.Event().wait()
        app = LocalMode(upstream, "model", 8008, timeout=0.005)
        events = await self.invoke(app, self.payload())
        self.assertEqual(events[0]["status"], 504)
        self.assertEqual(app.measurements.snapshot()["records"][-1]["status"], "timeout")
        self.assertFalse(app.busy)
        app.timeout = 90
        task = asyncio.create_task(self.invoke(app, self.payload()))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(app.measurements.snapshot()["records"][-1]["status"], "cancelled")
        self.assertFalse(app.busy)

    async def test_retrieval_error_does_not_infer_and_has_no_first_text(self):
        class Notes:
            def grounding(self, query):
                raise ValueError("Ricerca incompleta")
        async def upstream(*args):
            self.fail("Inference must not run")
        app = LocalMode(upstream, "model", 8008, notes=Notes())
        payload = {**self.payload(), "notes_query":"PRIVATE"}
        events = await self.invoke(app, payload)
        self.assertEqual(events[0]["status"], 400)
        record = app.measurements.snapshot()["records"][0]
        self.assertEqual(record["status"], "retrieval_error")
        self.assertIsNone(record["firstTextMs"])
        self.assertNotIn("PRIVATE", json.dumps(record))


if __name__ == "__main__":
    unittest.main()

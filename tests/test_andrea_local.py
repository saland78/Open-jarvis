"""Boundary checks for the personal launcher's local-only milestone."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("andrea_runtime", ROOT / "scripts/andrea/runtime.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
MODEL = "qwen3:4b-instruct-2507-q4_K_M"


async def invoke(app, payload=None, *, path="/v1/chat/completions", origin="http://127.0.0.1:8008", host="127.0.0.1:8008", method="POST"):
    raw = json.dumps(payload or {"model": MODEL, "messages": [{"role": "user", "content": "Ciao"}], "stream": True}).encode()
    queue = asyncio.Queue()
    await queue.put({"type": "http.request", "body": raw})
    headers = [(b"host", host.encode()), (b"content-type", b"application/json")]
    if origin:
        headers.append((b"origin", origin.encode()))
    events = []
    async def send(event):
        events.append(event)
    scope = {"type": "http", "method": method, "path": path, "headers": headers}
    await app(scope, queue.get, send)
    return events


class EnvironmentTests(unittest.TestCase):
    def test_cloud_credentials_and_previous_configuration_not_inherited(self):
        with tempfile.TemporaryDirectory(prefix="andrea-data-") as state, patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-key", "OPENJARVIS_HOME": "/previous", "VITE_API_URL": "https://external.example"}):
            env = runtime.isolated_environment(ROOT, Path(state))
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("VITE_API_URL", env)
            self.assertEqual(env["OPENJARVIS_HOME"], state)
            self.assertEqual(env["JARVIS_NUM_CTX"], "4096")

    def test_original_data_and_source_tree_rejected(self):
        for state in (ROOT / "data", Path.home(), Path.home() / ".jarvis-local", Path.home() / ".openjarvis"):
            with self.assertRaises(ValueError):
                runtime.isolated_environment(ROOT, state)


class BoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        async def sink(scope, receive, send):
            self.calls.append(json.loads((await receive())["body"]))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"data: [DONE]\n\n"})
        self.app = runtime.LocalMode(sink, MODEL, 8008)

    async def test_external_origins_and_writes_never_reach_backend(self):
        for args in ({"origin": "https://external.example"}, {"host": "external.example"}, {"origin": ""}, {"path": "/v1/memory/index"}, {"path": "/v1/agents", "method": "DELETE"}):
            result = await invoke(self.app, **args)
            self.assertEqual(result[0]["status"], 403)
        self.assertEqual(self.calls, [])

    async def test_cloud_models_and_tools_not_dispatched(self):
        for body in ({"model": "gpt-4.1", "messages": [{"role": "user", "content": "x"}], "stream": True}, {"model": MODEL, "messages": [{"role": "user", "content": "x"}], "tools": [{"name": "shell"}], "stream": True}):
            result = await invoke(self.app, body)
            self.assertEqual(result[0]["status"], 400)
        self.assertEqual(self.calls, [])

    async def test_budget_is_enforced_and_last_user_request_preserved(self):
        result = await invoke(self.app, {"model": MODEL, "messages": [{"role": "user", "content": "Richiesta di prova"}], "stream": True, "max_tokens": 9000, "temperature": 2})
        self.assertEqual(result[0]["status"], 200)
        self.assertEqual(self.calls[0]["max_tokens"], 512)
        self.assertEqual(self.calls[0]["temperature"], 0.4)
        self.assertEqual(self.calls[0]["messages"][-1]["content"], "Richiesta di prova")

    async def test_timeout_ends_stream_and_releases_generation_slot(self):
        async def hung(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await asyncio.sleep(30)
        app = runtime.LocalMode(hung, MODEL, 8008, timeout=0.01)
        result = await invoke(app)
        self.assertIn(b"90 secondi", result[-1]["body"])
        self.assertIn(b"[DONE]", result[-1]["body"])
        self.assertFalse(app.busy)

    async def test_concurrent_request_rejected_and_cancellation_releases_slot(self):
        entered = asyncio.Event()
        async def hung(scope, receive, send):
            entered.set()
            await asyncio.sleep(30)
        app = runtime.LocalMode(hung, MODEL, 8008)
        task = asyncio.create_task(invoke(app))
        await entered.wait()
        result = await invoke(app)
        self.assertEqual(result[0]["status"], 429)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(app.busy)


if __name__ == "__main__":
    unittest.main()

"""Production role attribution envelope and program-generated provenance."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts/andrea"))
import check_memory_attribution as historical
import manual_memory
from memory_provenance import MemoryProvenanceFooter, NOTICE
import runtime


def frame(text=None, finish=None, usage=None):
    value = {"choices": [{"index": 0, "delta": {"content": text} if text is not None else {}, "finish_reason": finish}]}
    if usage is not None: value["usage"] = usage
    return b"data: " + json.dumps(value, ensure_ascii=False).encode() + b"\n\n"


def text_of(body):
    chunks = []
    for block in body.replace(b"\r\n", b"\n").split(b"\n\n"):
        if not block.startswith(b"data: "): continue
        data = block[6:]
        if data == b"[DONE]": continue
        value = json.loads(data)
        chunks.extend(c.get("delta", {}).get("content", "") for c in value.get("choices", []))
    return "".join(chunks)


class MemoryRolesProductionTests(unittest.TestCase):
    def test_exact_role_candidate_and_literal_subjects(self):
        self.assertEqual(manual_memory.ROLE_GUIDANCE, historical.ROLE_GUIDANCE)
        with tempfile.TemporaryDirectory() as directory:
            store = manual_memory.ManualMemory(Path(directory), identity_prompt="Sei Jarvis. Identità del profilo.")
            row = store.mutate({"action": "create", "revision": 0, "record": {
                "kind": "fact", "topic": "Caso", "text": "Ho scelto viola; Elena ha scelto arancione.", "active": True}})["records"][0]
            conversation = [{"role": "user", "content": "Quale colore ho scelto?"}]
            enriched = store.messages(conversation)
            self.assertEqual([m["role"] for m in enriched], ["system", "user", "user"])
            self.assertTrue(enriched[0]["content"].startswith("Sei Jarvis. Identità del profilo."))
            self.assertNotIn(row["text"], enriched[0]["content"])
            self.assertEqual(json.loads(enriched[1]["content"].split("\n", 1)[1])[0]["text"], row["text"])
            self.assertEqual(enriched[2], conversation[0])
            self.assertEqual(store.snapshot()["records"][0]["text"], row["text"])

    def test_caller_identity_collapsed_and_conversation_not_mutated(self):
        with tempfile.TemporaryDirectory() as directory:
            store = manual_memory.ManualMemory(Path(directory), identity_prompt="DEFAULT IDENTITY")
            store.mutate({"action": "create", "revision": 0, "record": {
                "kind": "preference", "topic": "Lingua", "text": "Preferisco italiano.", "active": True}})
            original = [{"role": "system", "content": "CALLER IDENTITY"}, {"role": "user", "content": "Ciao"}, {"role": "system", "content": "CALLER STYLE"}]
            frozen = json.dumps(original)
            result = store.messages(original)
            self.assertEqual(json.dumps(original), frozen)
            self.assertEqual(sum(m["role"] == "system" for m in result), 1)
            self.assertIn("CALLER IDENTITY\n\nCALLER STYLE", result[0]["content"])
            self.assertNotIn("DEFAULT IDENTITY", result[0]["content"])
            self.assertEqual([m for m in result[2:]], [original[1]])

    def test_empty_memory_keeps_identical_original_object(self):
        with tempfile.TemporaryDirectory() as directory:
            store = manual_memory.ManualMemory(Path(directory)/"state", identity_prompt="Identity")
            original = [{"role": "user", "content": "Ciao"}]
            self.assertIs(store.messages(original), original)
            self.assertFalse(store.state.exists())


class ProvenanceStreamTests(unittest.TestCase):
    def test_first_model_content_unchanged_and_footer_only_at_stop(self):
        stream = MemoryProvenanceFooter()
        first = frame("Hai scelto viola.")
        self.assertEqual(stream.feed(first), first)
        self.assertFalse(stream.added)
        last = stream.feed(frame(finish="stop") + b"data: [DONE]\n\n", final=True)
        self.assertEqual(text_of(first + last), "Hai scelto viola." + NOTICE)
        self.assertTrue(last.endswith(b"data: [DONE]\n\n"))

    def test_one_byte_fragmentation_preserves_utf8_and_claim(self):
        original = frame("Hai scelto il tè verde.") + frame(finish="stop") + b"data: [DONE]\n\n"
        stream = MemoryProvenanceFooter()
        output = b"".join(stream.feed(bytes([byte])) for byte in original) + stream.feed(b"", final=True)
        self.assertEqual(text_of(output), "Hai scelto il tè verde." + NOTICE)
        self.assertEqual(text_of(output).count(NOTICE), 1)

    def test_crlf_and_combined_content_stop_keep_usage(self):
        original = frame("Hai scelto viola.", finish="stop", usage={"completion_tokens": 7}).replace(b"\n\n", b"\r\n\r\n")
        stream = MemoryProvenanceFooter()
        output = stream.feed(original, final=True)
        value = json.loads(output.split(b"data: ", 1)[1].strip())
        self.assertEqual(value["choices"][0]["delta"]["content"], "Hai scelto viola." + NOTICE)
        self.assertEqual(value["choices"][0]["finish_reason"], "stop")
        self.assertEqual(value["usage"], {"completion_tokens": 7})

    def test_truncation_error_empty_and_incomplete_do_not_get_footer(self):
        for original in (
            frame("Parziale", finish="length") + b"data: [DONE]\n\n",
            frame("Parziale") + b'data: {"error":{"message":"failure"}}\n\n' + frame(finish="stop"),
            frame(finish="stop") + b"data: [DONE]\n\n",
            frame(" \n", finish="stop") + b"data: [DONE]\n\n",
            frame("Parziale") + b'data: {"unfinished"',
        ):
            with self.subTest(original=original):
                stream = MemoryProvenanceFooter()
                self.assertEqual(stream.feed(original, final=True), original)
                self.assertFalse(stream.added)

    def test_control_events_and_repeated_stop_do_not_duplicate(self):
        control = b"event: keepalive\ndata: {}\n\n"
        stream = MemoryProvenanceFooter()
        original = control + frame("Testo") + frame(finish="stop") + frame(finish="stop") + b"data: [DONE]\n\n"
        output = stream.feed(original, final=True)
        self.assertTrue(output.startswith(control))
        self.assertEqual(text_of(output).count(NOTICE), 1)


class MemoryOutputBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_context_footer_without_early_text_or_extra_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            store = manual_memory.ManualMemory(Path(directory)/"state", identity_prompt="Sei Jarvis.")
            calls = []
            feeds = []
            actual = runtime.RequestMeasurement
            class RecordingMeasurement(actual):
                def feed(self, body):
                    feeds.append(body)
                    return super().feed(body)
            async def sink(scope, receive, send):
                calls.append(json.loads((await receive())["body"]))
                await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/event-stream")]})
                await send({"type": "http.response.body", "body": frame("Hai scelto viola."), "more_body": True})
                await send({"type": "http.response.body", "body": frame(finish="stop") + b"data: [DONE]\n\n", "more_body": False})
            app = runtime.LocalMode(sink, "model", 8008, memory=store)
            async def run(extra=None):
                body = json.dumps({"model": "model", "stream": True, "messages": [{"role": "user", "content": "Quale colore?"}], **(extra or {})}).encode()
                events = []
                async def receive(): return {"type": "http.request", "body": body}
                async def send(event): events.append(event)
                with patch.object(runtime, "RequestMeasurement", RecordingMeasurement):
                    await app({"type": "http", "method": "POST", "path": "/v1/chat/completions", "headers": [(b"host", b"127.0.0.1:8008"), (b"origin", b"http://127.0.0.1:8008"), (b"content-type", b"application/json")]}, receive, send)
                return b"".join(e.get("body", b"") for e in events)
            empty = await run()
            self.assertEqual(text_of(empty), "Hai scelto viola.")
            row = store.mutate({"action": "create", "revision": 0, "record": {"kind": "fact", "topic": "Colore", "text": "Ho scelto viola.", "active": True}})["records"][0]
            active = await run()
            self.assertEqual(text_of(active), "Hai scelto viola." + NOTICE)
            self.assertTrue(all(NOTICE not in b.decode() for b in feeds))
            self.assertEqual(app.measurements.snapshot()["records"][-1]["contentChunks"], 1)
            notes = await run({"notes_query": "colore", "notes_sources": [{"id": "N1", "title": "Nota", "text": "Colore rosso."}]})
            self.assertNotIn(NOTICE, text_of(notes))
            self.assertNotIn("Ho scelto viola", str(calls[-1]))
            store.mutate({"action": "delete", "revision": 1, "id": row["id"]})
            deleted = await run()
            self.assertEqual(text_of(deleted), "Hai scelto viola.")
            self.assertEqual(len(calls), 4)
            self.assertTrue(all(c["max_tokens"] == 512 and not c.get("tools") for c in calls))


if __name__ == "__main__": unittest.main()

"""Response styling is scoped to note synthesis and never trims stream text."""
import json
import unittest

import test_andrea_vault as base
from runtime import NOTES_RESPONSE_STYLE


class ConciseBoundaryTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = base.BoundaryVaultTests.asyncSetUp
    invoke = base.BoundaryVaultTests.invoke
    payload = base.BoundaryVaultTests.payload

    async def test_chat_keeps_original_messages_and_notes_receive_full_sources(self):
        chat = {"model": base.MODEL, "messages": [{"role": "user", "content": "Rispondi in dettaglio."}], "stream": True}
        await self.invoke(chat)
        self.assertEqual(self.calls[-1]["messages"], chat["messages"])
        self.assertEqual(self.calls[-1]["max_tokens"], 512)
        (self.root/"a.md").write_text("# Bilancio\nRoyalty: DATO NON VERIFICATO.\n", encoding="utf-8")
        events = await self.invoke(self.payload("Bilancio"))
        evidence = json.loads(events[1]["body"].decode().split("data: ", 1)[1])
        messages = self.calls[-1]["messages"]
        self.assertTrue(messages[0]["content"].endswith(NOTES_RESPONSE_STYLE))
        self.assertEqual(json.loads(messages[1]["content"])["estratti"], evidence["sources"])
        self.assertEqual(self.calls[-1]["max_tokens"], 512)

    async def test_long_model_response_is_not_trimmed_and_final_citation_survives(self):
        text = "Un dato della fonte. " * 80 + "Limite del dato non verificato [N1]."
        async def stream(scope, receive, send):
            await receive()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            event = json.dumps({"choices": [{"delta": {"content": text}, "finish_reason": None}]})
            await send({"type": "http.response.body", "body": ("data: " + event + "\n\n").encode(), "more_body": True})
            await send({"type": "http.response.body", "body": b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n', "more_body": False})
        self.app.app = stream
        (self.root/"a.md").write_text("# Bilancio\nRoyalty: DATO NON VERIFICATO.\n", encoding="utf-8")
        events = await self.invoke(self.payload("Bilancio"))
        output = b"".join(e.get("body", b"") for e in events).decode()
        self.assertIn(text, output)
        self.assertEqual(self.app.measurements.snapshot()["records"][-1]["status"], "completed")
        self.assertFalse(self.app.busy)

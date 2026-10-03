"""Regression: never merge historical absence with a dated unverified label."""
import json
import unittest

import test_andrea_vault as base
from status_scope import scoped_labels, status_scope_answer
from test_andrea_brief import TEMPORAL


def source(text=TEMPORAL, id="N1"):
    return {"id": id, "title": "Quadro", "text": text, "modifiedAt": "2099-01-01"}


class ScopeTests(unittest.TestCase):
    def test_mixed_qualifications_have_separate_literal_date_contexts(self):
        result = status_scope_answer([source()])
        self.assertIn("Sintesi libera non generata", result)
        self.assertIn("2031-06-04", result)
        self.assertIn("2031-02-10", result)
        self.assertIn("«DATO NON VERIFICATO»", result)
        self.assertIn("«DATO ASSENTE»", result)
        self.assertNotIn("assenti o non verificati", result)
        self.assertNotIn("2099", result)
        self.assertIn("non significano zero", result)

    def test_original_order_not_timestamp_selects_or_renames_date(self):
        parts = TEMPORAL.split("> [!important] Fotografia")
        result = status_scope_answer([source("> [!important] Fotografia" + parts[1], "N2"), source(parts[0])])
        self.assertLess(result.index("2031-02-10"), result.index("2031-06-04"))
        self.assertIn("[N2]", result)
        self.assertIn("[N1]", result)
        self.assertNotIn("valide fino", result)

    def test_single_kind_and_undated_text_leave_model_path_available(self):
        for text in ("DATO NON VERIFICATO. DATO ASSENTE.",
                     "Fotografia al 2031-02-10\nDATO ASSENTE.",
                     "Aggiornamento — 2031-06-04\nDATO NON VERIFICATO."):
            self.assertIsNone(status_scope_answer([source(text)]))

    def test_full_label_on_cut_line_is_quoted_without_completing_line(self):
        text = TEMPORAL.replace("nella fotografia storica.\n", "nella fotog")
        result = status_scope_answer([source(text)])
        self.assertIn("«DATO ASSENTE»", result)
        self.assertNotIn("nella fotog", result)

    def test_new_section_does_not_inherit_previous_context(self):
        text = "Aggiornamento — 2031-06-04\nDATO NON VERIFICATO.\n## Altro\nDATO ASSENTE."
        self.assertEqual(len(scoped_labels([source(text)])), 1)

    def test_ambiguous_source_citations_declined_and_bounded_headers(self):
        result = status_scope_answer([source(TEMPORAL + "\nFonte [N7].")])
        self.assertIn("riferimenti ambigui", result)
        self.assertNotIn("[N7]", result)
        result = status_scope_answer([source(TEMPORAL.replace("Aggiornamento", "X" * 301 + " Aggiornamento"))])
        self.assertIn("Intestazione troppo lunga", result)
        self.assertNotIn("X" * 301, result)


class ScopeBoundaryTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = base.BoundaryVaultTests.asyncSetUp
    invoke = base.BoundaryVaultTests.invoke
    payload = base.BoundaryVaultTests.payload

    async def test_real_retrieval_never_calls_model_for_mixed_status(self):
        (self.root / "a.md").write_text(TEMPORAL)
        events = await self.invoke(self.payload("Quadro attività"))
        evidence = json.loads(events[1]["body"].decode().split("data: ", 1)[1])
        self.assertEqual(evidence["answerMode"], "status_scope_quotes")
        answer = json.loads(events[2]["body"].decode().split("data: ", 1)[1])["choices"][0]["delta"]["content"]
        self.assertEqual(answer, status_scope_answer(evidence["sources"]))
        self.assertEqual(self.calls, [])
        record = self.app.measurements.snapshot()["records"][-1]
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["answerMode"], "status_scope_quotes")
        self.assertFalse(record["inferenceUsed"])
        self.assertIsNone(record["generationFirstTextMs"])
        self.assertIsNone(record["generationMs"])
        self.assertNotIn("2031", json.dumps(record))
        self.assertFalse(self.app.busy)

    async def test_provided_sources_same_guard_but_explicit_brief_unchanged(self):
        payload = {**self.payload("Quadro"), "notes_sources": [source()]}
        events = await self.invoke(payload)
        evidence = json.loads(events[1]["body"].decode().split("data: ", 1)[1])
        self.assertEqual(evidence["answerMode"], "status_scope_quotes")
        events = await self.invoke({**payload, "notes_brief": True})
        evidence = json.loads(events[1]["body"].decode().split("data: ", 1)[1])
        self.assertEqual(evidence["answerMode"], "brief_quotes")

    async def test_count_answer_and_chat_do_not_change_modes(self):
        events = await self.invoke({**self.payload("Quanti titoli pubblicati?"), "notes_sources": [source()]})
        evidence = json.loads(events[1]["body"].decode().split("data: ", 1)[1])
        self.assertEqual(evidence["answerMode"], "explicit_fields")
        self.assertEqual(self.calls, [])
        await self.invoke({"model": base.MODEL, "messages": [{"role": "user", "content": "Ciao"}], "stream": True})
        self.assertEqual(len(self.calls), 1)

    async def test_ui_does_not_call_fallback_model_synthesis(self):
        from pathlib import Path
        text = (Path(__file__).resolve().parents[1] / "frontend/src/pages/AndreaNotesPage.tsx").read_text()
        self.assertIn("Qualifiche datate dalle fonti", text)
        self.assertIn("nessuna sintesi del modello generata", text)

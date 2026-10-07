"""Extractive brief replies: preregistered temporal and boundary regressions."""
import json
import unittest

import test_andrea_vault as base
from brief import brief_answer, selected_passage


TEMPORAL = (
    "# Quadro attività\n\n"
    "> [!important] Aggiornamento confermato — 2031-06-04\n"
    "> I titoli pubblicati sono **4**.\n"
    "> Le royalty attuali sono **DATO NON VERIFICATO** in questa nota.\n"
    "> Un dato non verificato non significa zero.\n\n"
    "> [!important] Fotografia al 2031-02-10\n"
    "> Copie: DATO ASSENTE nella fotografia storica.\n"
)


class BriefTests(unittest.TestCase):
    def test_snapshot_is_never_paraphrased_as_expiry_and_unknown_is_not_zero(self):
        source = {"id": "N1", "text": TEMPORAL, "modifiedAt": "2099-01-01"}
        answer = brief_answer([source])
        self.assertIn("2031-06-04", answer)
        self.assertIn("**DATO NON VERIFICATO** in questa nota", answer)
        self.assertIn("non significa zero", answer)
        self.assertNotIn("valide fino", answer)
        self.assertNotIn("2099", answer)
        self.assertNotIn("DATO ASSENTE", answer)
        self.assertIn("Selezione parziale", answer)

    def test_historical_date_and_absence_stay_together(self):
        text = "## Fotografia al 2031-02-10\n\nRoyalty: DATO ASSENTE nella fotografia storica."
        passage = selected_passage(text)
        self.assertEqual(passage, "## Fotografia al 2031-02-10\nRoyalty: DATO ASSENTE nella fotografia storica.")
        self.assertNotIn("valide fino", brief_answer([{"id": "N1", "text": text}]))

    def test_conflicting_sources_kept_without_timestamp_winner(self):
        answer = brief_answer([
            {"id": "N1", "text": "Titoli pubblicati: 0.\n", "modifiedAt": "2099-01-01"},
            {"id": "N2", "text": "Titoli pubblicati: 4.\n", "modifiedAt": "2031-01-01"},
        ])
        self.assertIn("«Titoli pubblicati: 0.» [N1]", answer)
        self.assertIn("«Titoli pubblicati: 4.» [N2]", answer)
        self.assertNotIn("2099", answer)

    def test_negation_units_and_opinion_remain_literal(self):
        text = "Secondo il relatore il 90% abbandona. Non è un dato verificato; ricavi: -3 USD."
        self.assertEqual(selected_passage(text), text)

    def test_long_block_refused_instead_of_cutting_qualifiers(self):
        text = "Parola " * 141 + "non significa zero."
        self.assertIsNone(selected_passage(text))
        self.assertIn("apri la nota", brief_answer([{"id": "N1", "text": text}]))

    def test_cut_final_block_and_ambiguous_citations_refused(self):
        for text in ("Royalty: dato non", "Una fonte dice [N7].", "# Titolo [N7]\nUn dato.", "## Solo titolo"):
            with self.subTest(text=text):
                self.assertIsNone(selected_passage(text))

    def test_enclosing_headings_are_kept_in_order(self):
        text = "# Quadro\n\n## Fotografia al 2031-02-10\n\nIl problema risultava risolto.\n\n## Oggi\n\nNon verificato."
        self.assertEqual(selected_passage(text), "# Quadro\n## Fotografia al 2031-02-10\nIl problema risultava risolto.")


class BriefBoundaryTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = base.BoundaryVaultTests.asyncSetUp
    invoke = base.BoundaryVaultTests.invoke
    payload = base.BoundaryVaultTests.payload

    async def test_real_retrieval_stream_citations_and_no_model_call(self):
        (self.root / "a.md").write_text(TEMPORAL)
        events = await self.invoke({**self.payload("Quadro attività"), "notes_brief": True})
        evidence = json.loads(events[1]["body"].decode().split("data: ", 1)[1])
        self.assertEqual(evidence["answerMode"], "brief_quotes")
        answer_frame = json.loads(events[2]["body"].decode().split("data: ", 1)[1])
        answer = answer_frame["choices"][0]["delta"]["content"]
        self.assertEqual(answer, brief_answer(evidence["sources"]))
        self.assertIn("[N1]", answer)
        self.assertEqual(self.calls, [])
        record = self.app.measurements.snapshot()["records"][-1]
        self.assertEqual(record["status"], "completed")
        self.assertFalse(record["inferenceUsed"])
        self.assertIsNone(record["generationMs"])
        self.assertFalse(self.app.busy)

    async def test_supplied_sources_follow_same_brief_path(self):
        source = {"id": "N1", "title": "Quadro", "text": TEMPORAL}
        events = await self.invoke({**self.payload("Quadro"), "notes_brief": True, "notes_sources": [source]})
        evidence = json.loads(events[1]["body"].decode().split("data: ", 1)[1])
        self.assertEqual(evidence["origin"], "provided")
        self.assertEqual(evidence["answerMode"], "brief_quotes")
        self.assertEqual(self.calls, [])

    async def test_invalid_flag_rejected_before_inference(self):
        for flag in ("true", 1, None):
            events = await self.invoke({**self.payload("Quadro"), "notes_brief": flag})
            self.assertEqual(events[0]["status"], 400)
        events = await self.invoke({"model": base.MODEL, "messages": [{"role": "user", "content": "Ciao"}], "stream": True, "notes_brief": True})
        self.assertEqual(events[0]["status"], 400)
        self.assertEqual(self.calls, [])

    async def test_drafts_and_partial_scans_still_blocked(self):
        (self.root / "a.md").write_text("---\nstatus: draft\n---\n# Quadro\nUn dato.\n")
        events = await self.invoke({**self.payload("Quadro"), "notes_brief": True})
        self.assertEqual(events[0]["status"], 400)
        (self.root / "a.md").write_text("# Quadro\nUn dato.\n")
        self.store.MAX_FILES = 0
        events = await self.invoke({**self.payload("Quadro"), "notes_brief": True})
        self.assertNotEqual(events[0]["status"], 200)
        self.assertEqual(self.calls, [])

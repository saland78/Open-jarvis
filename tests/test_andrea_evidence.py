"""Evidence lookup scope, conflicting counts and the actual notes ASGI boundary."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/andrea"))
from evidence import explicit_count_answer, supplied_sources
from runtime import LocalMode, notes_messages
import test_andrea_measurements as measurement_tests


def source(sid, text, **extra):
    return {"id": sid, "title": "Scheda", "text": text, **extra}


class EvidenceScopeTests(unittest.TestCase):
    def test_natural_explicit_field_is_quoted_but_negation_and_estimates_abstain(self):
        for line in ("I libri pubblicati sono **47**.", "I titoli pubblicati sono 11.", "Copie vendute sono 19."):
            query = "Quante copie sono vendute?" if "Copie" in line else "Quanti libri risultano pubblicati?"
            with self.subTest(line=line):
                self.assertIn(f"«{line}» [N1]", explicit_count_answer(query, [source("N1", line)]))
        for line in ("I libri pubblicati non sono 47.", "I libri pubblicati sono circa 47.", "I libri pubblicati sono 47 mila.",
                     "I libri pubblicati sono **47** mila.", "I libri pubblicati sono **47**%.", "I libri pubblicati sono **47**/100."):
            with self.subTest(line=line):
                self.assertIsNone(explicit_count_answer("Quanti libri risultano pubblicati?", [source("N1", line)]))

    def test_conflicting_counts_keep_both_and_do_not_resolve_by_file_timestamp(self):
        sources = [source("N1", "titoli_pubblicati: 14", modifiedAt="2026-10-01"),
                   source("N2", "Titoli pubblicati: 3. Periodo non indicato.", modifiedAt="2026-01-01")]
        answer = explicit_count_answer("Quanti titoli sono pubblicati?", sources)
        self.assertIn("14 [N1]", answer)
        self.assertIn("3 [N2]", answer)
        self.assertIn("Non scelgo un conteggio unico", answer)
        self.assertNotIn("2026-10-01", answer)
        self.assertIn("«titoli_pubblicati: 14» [N1]", answer)

    def test_sale_field_preserves_period_and_omits_unrelated_opinion(self):
        line = "Copie vendute nel maggio 2027: 11, da report locale."
        answer = explicit_count_answer("Quali vendite sono documentate?", [
            source("N1", line), source("N2", "Il relatore sostiene che il 73% abbandona, senza dati a supporto.")])
        self.assertIn(f"«{line}» [N1]", answer)
        self.assertNotIn("73%", answer)
        self.assertNotIn("N2", answer)
        self.assertIn("non sono state verificate", answer)

    def test_inline_count_keeps_explicit_date_and_market(self):
        line = "Fotografia al 2027-04-05: libri pubblicati 9, mercato Francia."
        self.assertIn(f"«{line}» [N1]", explicit_count_answer("Quanti libri risultano pubblicati?", [source("N1", line)]))

    def test_missing_estimated_negated_fractional_and_scaled_values_are_not_counts(self):
        values = ["libri_pubblicati: DATO ASSENTE", "libri_pubblicati: DATO NON VERIFICATO", "libri_pubblicati: -2",
                  "libri_pubblicati: 2.5", "libri_pubblicati: 2,5", "libri_pubblicati: 2 mila",
                  "libri_pubblicati: 2mila", "libri_pubblicati: 2%", "libri_pubblicati: 2 euro", "libri_pubblicati: 2/5",
                  "libri_pubblicati: 2-5", "libri_pubblicati: 2 o 5", "libri_pubblicati: 2+",
                  "libri_pubblicati: circa 2", "libri_pubblicati: 2 # stima", "Non risulta libri pubblicati: 2",
                  "libri_pubblicati: 2 [N9]"]
        for line in values:
            with self.subTest(line=line):
                self.assertIsNone(explicit_count_answer("Quanti libri sono pubblicati?", [source("N1", line)]))

    def test_other_metrics_operational_questions_and_missing_requested_fields_fall_back(self):
        sources = [source("N1", "copie_vendute: 7\nlibri_pubblicati: 4")]
        for query in ("Come migliorare le vendite?", "Quali strategie per le vendite?", "Quali vendite e royalty sono aggiornate?",
                      "Quanti dipendenti sono assunti?", "Quanti libri? Perché?", "Quali report devo scaricare per le vendite?",
                      "Quanti libri sono in lavorazione?", "Quante copie sono stampate?", "Quanti libri non sono pubblicati?", "Quanti titoli sono venduti?"):
            with self.subTest(query=query):
                self.assertIsNone(explicit_count_answer(query, sources))

    def test_different_values_with_explicit_periods_are_preserved_not_summed(self):
        answer = explicit_count_answer("Quali vendite sono documentate?", [
            source("N1", "Copie vendute nel gennaio 2027: 5"), source("N2", "Copie vendute nel febbraio 2027: 8")])
        self.assertIn("gennaio 2027: 5", answer)
        self.assertIn("febbraio 2027: 8", answer)
        self.assertIn("occorre chiarire periodo e ambito", answer)
        self.assertNotIn("13", answer)

    def test_supplied_sources_reject_unbounded_duplicates_and_vault_claims(self):
        good = source("N1", "Titoli pubblicati: 8")
        self.assertEqual(supplied_sources([good]), [good])
        bad_inputs = [[], [good, good], [source("N9", "test")], [{**good, "path": "/private.md"}],
                      [{**good, "status": "confirmed"}], [{**good, "text": "x" * 901}],
                      [{**good, "text": ""}], [{**good, "id": []}], [{**good, "title": []}]]
        for value in bad_inputs:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    supplied_sources(value)


class EvidenceBoundaryTests(unittest.IsolatedAsyncioTestCase):
    invoke = measurement_tests.BoundaryMeasurementTests.invoke

    def payload(self, query, sources=None):
        result = {"model": "model", "stream": True, "messages": [{"role": "user", "content": query}], "notes_query": query}
        if sources is not None:
            result["notes_sources"] = sources
        return result

    def answer(self, events):
        texts = []
        for event in events:
            for line in event.get("body", b"").decode().splitlines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    chunk = json.loads(line[6:])
                    texts.extend(c.get("delta", {}).get("content", "") for c in chunk.get("choices", []))
        return "".join(texts)

    async def test_conflict_on_real_vault_path_never_calls_inference_and_keeps_source_metadata(self):
        sources = [source("N1", "Titoli pubblicati: 6", path="a.md", startLine=12, endLine=12),
                   source("N2", "Titoli pubblicati: 1", path="b.md", startLine=20, endLine=20)]
        class Notes:
            def grounding(self, query):
                return {"query": query, "sources": sources, "partial": False, "excluded": 2}
        async def forbidden(*args):
            self.fail("Structured conflict must not invoke the model")
        app = LocalMode(forbidden, "model", 8008, notes=Notes())
        events = await self.invoke(app, self.payload("Quanti titoli sono pubblicati?"))
        self.assertEqual(events[0]["status"], 200)
        self.assertIn("6 [N1]", self.answer(events))
        self.assertIn("1 [N2]", self.answer(events))
        metadata = json.loads(events[1]["body"].decode().split("data: ", 1)[1])
        self.assertEqual(metadata["origin"], "vault")
        self.assertEqual(metadata["sources"], sources)
        record = app.measurements.snapshot()["records"][-1]
        self.assertEqual(record["answerMode"], "explicit_fields")
        self.assertFalse(record["inferenceUsed"])
        self.assertIsNone(record["generationMs"])
        self.assertIsNone(record["generationFirstTextMs"])
        self.assertEqual(record["status"], "completed")
        self.assertNotIn("a.md", json.dumps(record))
        self.assertNotIn("Titoli", json.dumps(record))
        self.assertFalse(app.busy)

    async def test_provided_excerpts_use_same_direct_path_without_reading_vault(self):
        class Notes:
            def grounding(self, query):
                raise AssertionError("Synthetic supplied excerpts must not read the vault")
        async def forbidden(*args):
            self.fail("Model not needed for an explicit sale count")
        app = LocalMode(forbidden, "model", 8008, notes=Notes())
        events = await self.invoke(app, self.payload("Quali vendite sono documentate?", [source("N1", "Copie vendute nel luglio 2027: 17")]))
        self.assertIn("luglio 2027: 17", self.answer(events))
        self.assertIn(b'"origin": "provided"', events[1]["body"])
        self.assertNotIn(b'"origin": "vault"', events[1]["body"])

    async def test_unrecognised_question_retains_real_prompt_and_budget(self):
        calls = []
        async def upstream(scope, receive, send):
            calls.append(json.loads((await receive())["body"]))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b'data: {"choices":[{"delta":{"content":"SYNTHESIS [N1]"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'})
        sources = [source("N1", "Royalties: DATO NON VERIFICATO")]
        app = LocalMode(upstream, "model", 8008)
        events = await self.invoke(app, self.payload("Quali royalty sono aggiornate?", sources))
        self.assertEqual(calls[0]["messages"], notes_messages("Quali royalty sono aggiornate?", sources))
        self.assertEqual(calls[0]["max_tokens"], 512)
        self.assertEqual(calls[0]["temperature"], 0.4)
        self.assertIn("SYNTHESIS [N1]", self.answer(events))
        self.assertTrue(app.measurements.snapshot()["records"][-1]["inferenceUsed"])
        self.assertIn(b'"answerMode": "model_synthesis"', events[1]["body"])

    async def test_invalid_source_input_and_external_origin_do_not_infer(self):
        async def forbidden(*args):
            self.fail("Rejected input must not reach inference")
        app = LocalMode(forbidden, "model", 8008)
        events = await self.invoke(app, self.payload("Quanti libri?", []))
        self.assertEqual(events[0]["status"], 400)
        events = await self.invoke(app, self.payload("Quanti libri?", [source("N1", "Libri pubblicati: 1")]), host="evil.example")
        self.assertEqual(events[0]["status"], 403)
        self.assertFalse(app.busy)


if __name__ == "__main__":
    unittest.main()

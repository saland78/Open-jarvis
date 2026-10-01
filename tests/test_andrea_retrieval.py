"""Synthetic regression cases; no personal vault or real Ollama."""
from unittest.mock import patch
import unittest
import test_andrea_vault as base
import vault

class RetrievalRegressionTests(unittest.TestCase):
    setUp = base.VaultTests.setUp
    write = base.VaultTests.write
    def test_exact_title_omits_incidental_training_mentions(self):
        self.write("kpi.md", "# KPI self-publishing\nDue titoli online; copie e royalty: DATO ASSENTE.")
        self.write("lecture.md", "# Corso self-publishing\nKPI self publishing: il relatore sostiene una percentuale.")
        self.write("hub.md", "# HUB self-publishing\nVedi KPI self publishing.")
        self.assertEqual(self.store.search("kpi self publishing")["total"], 3)
        evidence = self.store.grounding("kpi self publishing")
        self.assertEqual([s["path"] for s in evidence["sources"]], ["kpi.md"])

    def test_same_exact_title_keeps_conflicting_sources(self):
        self.write("a.md", "# Catalogo\nTitoli pubblicati: 2.")
        self.write("b.md", "# Catalogo\nTitoli pubblicati: 0.")
        sources = self.store.grounding("Catalogo")["sources"]
        self.assertEqual(len(sources), 2)

    def test_partial_search_never_generates_summary(self):
        self.write("a.md", "# KPI\nDato 2.")
        self.write("b.md", "# KPI\nDato 0.")
        self.store.MAX_FILES = 1
        with self.assertRaisesRegex(vault.VaultError, "Ricerca incompleta"):
            self.store.grounding("KPI")

    def test_long_lines_tokenized_once_with_identical_fragment(self):
        lines = ["# Catalogo", "titoli altro " * 5000, "royalty assenti", "titoli royalty", "fine"]
        note = {"text": "\n".join(lines), "bodyStart": 0, "path": "x.md",
                "title": "Catalogo", "status": "active", "modifiedAt": "x", "hasContent": True}
        terms = ["titoli", "royalty"]
        original_start = max(range(len(lines)), key=lambda i:
            sum(t in vault.words("\n".join(lines[i:i+4])) for t in terms) * 10
            + sum(t in vault.words(lines[i]) for t in terms))
        original_words = vault.words
        with patch.object(vault, "words", wraps=original_words) as tokenize:
            result = self.store.fragment(note, terms)
            self.assertEqual(tokenize.call_count, len(lines))
        self.assertEqual(result["startLine"], original_start + 1)

class PromptRegressionTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = base.BoundaryVaultTests.asyncSetUp
    invoke = base.BoundaryVaultTests.invoke
    payload = base.BoundaryVaultTests.payload
    async def test_prompt_requires_conflicts_dates_and_unknowns(self):
        (self.root/"a.md").write_text("# Catalogo\nTitoli 2, ricavi DATO ASSENTE.")
        events = await self.invoke(self.payload("Catalogo"))
        self.assertEqual(events[0]["status"], 200)
        system = self.calls[0]["messages"][0]["content"]
        for rule in ("si contraddicono", "NON VERIFICATO", "modifiedAt", "trascrizioni", "recensioni"):
            self.assertIn(rule, system)

    async def test_partial_retrieval_never_calls_inference(self):
        (self.root/"a.md").write_text("# Catalogo\nTitoli 2.")
        (self.root/"b.md").write_text("# Catalogo\nTitoli 0.")
        self.store.MAX_FILES = 1
        events = await self.invoke(self.payload("Catalogo"))
        self.assertEqual(events[0]["status"], 400)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.app.busy)

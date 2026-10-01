"""Synthetic regression cases; no personal vault or real Ollama."""
from unittest.mock import patch
import json
import unittest
import test_andrea_vault as base
import vault

class RetrievalRegressionTests(unittest.TestCase):
    setUp = base.VaultTests.setUp
    write = base.VaultTests.write
    def named_corpus(self):
        self.write("metrics.md", "---\ntitle: KPI self-publishing\nstatus: active\n---\n# KPI self-publishing\nAggiornamento al 2027-04-05.\nI libri pubblicati sono **9**.\nRoyalty: DATO NON VERIFICATO.\n")
        self.write("scope.md", "# Self-publishing\nScheda generale con rinvio ai KPI self publishing.\n")
        for i in range(15):
            self.write(f"lecture-{i:02}.md", "# Corso editoria\nQuanti libri pubblicati risultano nei KPI del self publishing? Un relatore parla di guadagni.\n")

    def test_question_names_note_before_incidental_matches_and_top_ten_cutoff(self):
        self.named_corpus()
        query = "Quanti libri pubblicati risultano nei KPI del self-publishing?"
        result = self.store.search(query)
        self.assertEqual(result["total"], 17)
        self.assertEqual(result["results"][0]["path"], "metrics.md")
        self.assertFalse(result["partial"])
        sources = self.store.grounding(query)["sources"]
        self.assertEqual([s["path"] for s in sources], ["metrics.md"])
        source = sources[0]
        original = self.store.read(source["path"])["text"].split("\n")
        self.assertEqual(source["text"], "\n".join(original[source["startLine"]-1:source["endLine"]]))

    def test_title_matching_is_generic_and_uses_frontmatter_title(self):
        for title in ("Costi officina", "Budget attività", "Piano editoriale"):
            with self.subTest(title=title):
                self.store.configure(str(self.root))
                self.write("target.md", f"---\ntitle: {title}\nstatus: active\n---\nValore registrato: 47.\n")
                self.write("noise.md", f"# Trascrizione corso\nQuali valori risultano nei {title}? Altri commenti.\n")
                query = f"Quali valori risultano nei {title.upper()}?"
                self.assertEqual([s["path"] for s in self.store.grounding(query)["sources"]], ["target.md"])

    def test_two_separate_named_notes_remain_sources(self):
        self.write("a.md", "# KPI editoria\nCopie vendute: 11.\n")
        self.write("b.md", "# Budget stampa\nCosto: 47 euro.\n")
        self.write("noise.md", "# Formazione\nConfronta KPI editoria e Budget stampa nella trascrizione.\n")
        sources = self.store.grounding("Confronta KPI editoria e Budget stampa")["sources"]
        self.assertEqual({s["path"] for s in sources}, {"a.md", "b.md"})

    def test_shorter_title_inside_a_longer_title_is_not_a_second_requested_note(self):
        self.write("full.md", "# Bilancio progetti attivi\nDato registrato 47.\n")
        self.write("short.md", "# Progetti attivi\nDato di un ambito differente.\n")
        sources = self.store.grounding("Mostra il Bilancio dei progetti attivi")["sources"]
        self.assertEqual([s["path"] for s in sources], ["full.md"])

    def test_duplicate_named_titles_keep_disagreeing_counts(self):
        self.write("a.md", "# Catalogo libreria\nTitoli pubblicati: 14.\n")
        self.write("b.md", "# Catalogo libreria\nTitoli pubblicati: 3.\n")
        self.write("noise.md", "# Formazione\nQuanti titoli pubblicati nel Catalogo libreria?\n")
        sources = self.store.grounding("Quanti titoli pubblicati nel Catalogo libreria?")["sources"]
        self.assertEqual({s["path"] for s in sources}, {"a.md", "b.md"})

    def test_named_inactive_note_never_falls_back_to_incidental_training(self):
        self.write("old.md", "---\ntitle: Catalogo libreria\nstatus: superseded\n---\nTitoli pubblicati: 0.\n")
        self.write("noise.md", "# Formazione\nQuanti titoli pubblicati nel Catalogo libreria? Il corso non documenta il catalogo.\n")
        result = self.store.search("Quanti titoli pubblicati nel Catalogo libreria?")
        self.assertEqual(result["results"][0]["path"], "old.md")
        self.assertEqual(result["excluded"], 1)
        with self.assertRaises(vault.VaultError):
            self.store.grounding("Quanti titoli pubblicati nel Catalogo libreria?")

    def test_broad_query_keeps_multiple_sources_and_no_match_stays_empty(self):
        for name in ("prima", "seconda", "terza"):
            self.write(name+".md", f"# {name}\nVendite registrate nel periodo.\n")
        self.assertEqual(len(self.store.grounding("vendite")["sources"]), 3)
        self.assertEqual(self.store.search("xilofono")["total"], 0)

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
    async def test_named_real_files_use_direct_counts_without_calling_model(self):
        (self.root/"metrics.md").write_text("# KPI editoria\nAggiornamento al 2027-04-05.\nI libri pubblicati sono **9**.\n")
        (self.root/"lecture.md").write_text("# Corso\nQuanti libri pubblicati risultano nei KPI editoria? Il relatore parla di guadagni.\n")
        events = await self.invoke(self.payload("Quanti libri pubblicati risultano nei KPI editoria?"))
        self.assertEqual(events[0]["status"], 200)
        self.assertEqual(self.calls, [])
        evidence = json.loads(events[1]["body"].decode().split("data: ", 1)[1])
        self.assertEqual(evidence["origin"], "vault")
        self.assertEqual([s["path"] for s in evidence["sources"]], ["metrics.md"])
        self.assertEqual(evidence["answerMode"], "explicit_fields")
        body = b"".join(e.get("body", b"") for e in events)
        self.assertIn(b"9", body)
        self.assertIn(b"[N1]", body)
        self.assertFalse(self.app.measurements.snapshot()["records"][-1]["inferenceUsed"])

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

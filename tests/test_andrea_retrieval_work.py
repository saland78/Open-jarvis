"""Bounded snippet work without changing full search counts or sources."""
from unittest.mock import patch
import unittest

import test_andrea_vault as base
import vault


class RetrievalWorkTests(unittest.TestCase):
    setUp = base.VaultTests.setUp
    write = base.VaultTests.write

    def test_only_visible_results_build_snippets_but_counts_cover_all_matches(self):
        for i in range(80):
            status = "superseded" if i < 20 else "active"
            self.write(f"note-{i:03}.md", f"---\nstatus: {status}\n---\n# Documento {i}\nCatalogo editoriale: titoli pubblicati nel periodo.\n")
        self.write("z-target.md", "# Catalogo editoriale\nTitoli pubblicati: 47.\n")
        with patch.object(self.store, "fragment", wraps=self.store.fragment) as fragments:
            result = self.store.search("Quanti titoli pubblicati nel Catalogo editoriale?")
        self.assertEqual(result["total"], 81)
        self.assertEqual(result["scanned"], 81)
        self.assertEqual(result["excluded"], 20)
        self.assertFalse(result["partial"])
        self.assertEqual(result["results"][0]["path"], "z-target.md")
        self.assertEqual(fragments.call_count, 10)
        self.assertEqual([call.args[0]["path"] for call in fragments.call_args_list],
                         [source["path"] for source in result["results"]])
        self.assertEqual([s["path"] for s in self.store.grounding("Catalogo editoriale")["sources"]], ["z-target.md"])

    def test_no_matches_build_no_snippets_and_do_not_expose_cached_note_fields(self):
        self.write("a.md", "# Documento\nContenuto riservato di prova.\n")
        with patch.object(self.store, "fragment", wraps=self.store.fragment) as fragments:
            result = self.store.search("xilofono")
        self.assertEqual(result["total"], 0)
        self.assertEqual(fragments.call_count, 0)
        source = self.store.search("Documento")["results"][0]
        self.assertEqual(set(source), {"path", "title", "status", "startLine", "endLine", "text", "modifiedAt", "eligible"})

    def test_preview_refreshes_changed_lines_and_named_status_without_fallback(self):
        file = self.write("a.md", "# Catalogo editoriale\nTitoli pubblicati: 47.\n")
        self.write("course.md", "# Formazione\nCatalogo editoriale: titoli pubblicati, opinione del relatore.\n")
        self.store.search("Catalogo editoriale")
        file.write_text("---\nstatus: active\n---\n# Catalogo editoriale\nTitoli pubblicati: 9.\n", encoding="utf-8")
        source = self.store.grounding("Catalogo editoriale")["sources"][0]
        self.assertIn("9", source["text"])
        self.assertNotIn("47", source["text"])
        lines = file.read_text(encoding="utf-8").split("\n")
        self.assertEqual(source["text"], "\n".join(lines[source["startLine"]-1:source["endLine"]]))
        file.write_text("---\nstatus: superseded\n---\n# Catalogo editoriale\nTitoli pubblicati: 9.\n", encoding="utf-8")
        with self.assertRaises(vault.VaultError):
            self.store.grounding("Catalogo editoriale")

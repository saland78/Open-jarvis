"""Synthetic vault checks: containment, provenance, current sources and updates."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/andrea"))
from vault import VaultNotes, VaultError
from runtime import LocalMode

MODEL = "qwen3:4b-instruct-2507-q4_K_M"


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vault-tests-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "Vault"
        self.root.mkdir()
        self.store = VaultNotes(self.home / "State", home=self.home)
        self.store.configure(str(self.root))

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def test_body_only_evidence_preserves_original_line_numbers(self):
        self.write("Gioiello.md", '---\ntitle: Gioiello\nsummary: SEGRETO_SOLO_METADATA\nrelated: [PAROLA_METADATA]\nstatus: active\n---\n# Gioiello\nDecisione: catalogo prima, vendita online dopo.\n<img src="https://invalid.example/x">\n')
        self.assertEqual(self.store.search("PAROLA_METADATA")["total"], 0)
        source = self.store.grounding("Gioiello")["sources"][0]
        self.assertNotIn("SEGRETO_SOLO_METADATA", source["text"])
        self.assertIn("catalogo prima", source["text"])
        original = self.store.read(source["path"])["text"].split("\n")
        self.assertEqual(source["text"], "\n".join(original[source["startLine"]-1:source["endLine"]]))
        self.assertGreaterEqual(source["startLine"], 7)

    def test_drafts_duplicates_unknown_status_and_empty_notes_visible_but_excluded(self):
        for name, header in (("Bozza", "status: draft"), ("Superata", "status: superseded"), ("Duplicata", "status: active\nstatus: draft"), ("Sconosciuta", "status: strange-state"), ("Annidata", "meta:\n  status: superseded")):
            self.write(name+"-Gioiello.md", f"---\n{header}\n---\n# Gioiello\nVecchia decisione Gioiello.\n")
        self.write("Gioiello-vuota.md", "")
        result = self.store.search("Gioiello")
        self.assertEqual(result["total"], 6)
        self.assertEqual(result["excluded"], 6)
        with self.assertRaises(VaultError):
            self.store.grounding("Gioiello")
        self.write("Attiva-Gioiello.md", "---\nstatus: active\n---\n# Gioiello\nNuova decisione Gioiello.\n")
        self.assertEqual([s["path"] for s in self.store.grounding("Gioiello")["sources"]], ["Attiva-Gioiello.md"])

    def test_edits_deletions_and_vault_switch_never_reuse_stale_content(self):
        p = self.write("Gioiello.md", "# Gioiello\nBudget 1000 euro.\n")
        self.assertIn("1000", self.store.grounding("Gioiello")["sources"][0]["text"])
        p.write_text("# Gioiello\nBudget aggiornato 9000 euro.\n")
        self.assertIn("9000", self.store.grounding("Gioiello")["sources"][0]["text"])
        p.unlink()
        self.assertEqual(self.store.search("Gioiello")["total"], 0)
        with self.assertRaises(VaultError) as missing:
            self.store.read("Gioiello.md")
        self.assertEqual(missing.exception.status, 404)
        other = self.home / "Other"
        other.mkdir()
        (other/"Gioiello.md").write_text("# Gioiello\nAltra banca dati.\n")
        self.store.configure(str(other))
        self.assertIn("Altra banca dati", self.store.grounding("Gioiello")["sources"][0]["text"])
        self.assertEqual(VaultNotes(self.home / "State", home=self.home).status()["vault"], str(other))
        self.store.configure("")
        self.assertFalse(self.store.status()["available"])
        with self.assertRaises(VaultError):
            self.store.read("Gioiello.md")

    def test_parent_hidden_symlink_hardlink_fifo_and_broad_roots_blocked(self):
        outside = self.home / "outside.md"
        outside.write_text("SECRET_OUTSIDE")
        (self.root/"link.md").symlink_to(outside)
        (self.root/"linked-dir").symlink_to(self.home, target_is_directory=True)
        os.link(outside, self.root/"hard.md")
        os.mkfifo(self.root/"pipe.md")
        self.write(".obsidian/hidden.md", "SECRET_HIDDEN")
        for path in ("../outside.md", "/outside.md", "link.md", "linked-dir/outside.md", "hard.md", "pipe.md", ".obsidian/hidden.md"):
            with self.assertRaises(VaultError, msg=path):
                self.store.read(path)
        self.assertEqual(self.store.search("SECRET")["total"], 0)
        for path in (str(self.home), "/", str(self.home.parent)):
            with self.assertRaises(VaultError):
                self.store.configure(path)
        (self.home/"VaultLink").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(VaultError):
            self.store.configure(str(self.home/"VaultLink"))

    def test_limits_partial_scan_encoding_and_malformed_frontmatter(self):
        self.write("Gioiello.md", "---\nstatus: active\nNON_CHIUSO Gioiello")
        with self.assertRaises(VaultError):
            self.store.grounding("Gioiello")
        self.write("TooBig.md", "x"*(self.store.MAX_NOTE+1))
        with self.assertRaises(VaultError) as big:
            self.store.read("TooBig.md")
        self.assertEqual(big.exception.status, 413)
        (self.root/"Bad.md").write_bytes(b"\xff\xfe")
        with self.assertRaises(VaultError):
            self.store.read("Bad.md")
        self.write("A-Gioiello.md", "# Gioiello\nDecisione uno.")
        self.write("B-Gioiello.md", "# Gioiello\nDecisione due.")
        self.store.MAX_FILES = 1
        self.assertTrue(self.store.search("Gioiello")["partial"])


class BoundaryVaultTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vault-boundary-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home/"Vault"
        self.root.mkdir()
        self.store = VaultNotes(self.home/"State", home=self.home)
        self.store.configure(str(self.root))
        self.calls = []
        async def sink(scope, receive, send):
            self.calls.append(json.loads((await receive())["body"]))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"data: [DONE]\n\n"})
        self.app = LocalMode(sink, MODEL, 8008, notes=self.store)

    async def invoke(self, payload, path="/v1/chat/completions", origin="http://127.0.0.1:8008"):
        queue = asyncio.Queue()
        await queue.put({"type": "http.request", "body": json.dumps(payload).encode()})
        events = []
        async def send(event): events.append(event)
        await self.app({"type": "http", "method": "POST", "path": path, "headers": [(b"host", b"127.0.0.1:8008"), (b"origin", origin.encode()), (b"content-type", b"application/json")]}, queue.get, send)
        return events

    def payload(self, query):
        return {"model": MODEL, "messages": [{"role": "user", "content": "Invented client-side sources"}], "stream": True, "notes_query": query}

    async def test_backend_builds_fresh_prompt_and_streams_exact_evidence(self):
        (self.root/"Current.md").write_text("---\nstatus: active\nsummary: METADATA_SECRET\n---\n# Gioiello\nCatalogo prima, vendita dopo.\n")
        (self.root/"Draft.md").write_text("---\nstatus: draft\n---\n# Gioiello\nSCELTA_BOZZA_NON_USARE\n")
        events = await self.invoke(self.payload("Gioiello"))
        self.assertEqual(events[0]["status"], 200)
        source_event = events[1]["body"].decode()
        self.assertTrue(source_event.startswith("event: local_sources"))
        evidence = json.loads(source_event.split("data: ")[1])
        body = json.loads(self.calls[0]["messages"][-1]["content"])
        self.assertEqual(body["estratti"], evidence["sources"])
        text = self.calls[0]["messages"][-1]["content"]
        self.assertIn("Catalogo prima", text)
        self.assertNotIn("SCELTA_BOZZA_NON_USARE", text)
        self.assertNotIn("METADATA_SECRET", text)
        self.assertNotIn("Invented client-side", text)
        self.assertEqual(self.calls[0]["max_tokens"], 512)
        self.assertFalse(self.app.busy)

    async def test_no_usable_sources_never_starts_inference_and_bad_config_origin_blocked(self):
        (self.root/"Draft.md").write_text("---\nstatus: draft\n---\n# Gioiello\nBozza.\n")
        result = await self.invoke(self.payload("Gioiello"))
        self.assertEqual(result[0]["status"], 400)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.app.busy)
        result = await self.invoke({"vault": str(self.root)}, "/api/andrea/notes/config", origin="https://external.example")
        self.assertEqual(result[0]["status"], 403)
        self.assertEqual(self.store.vault, str(self.root))
        result = await self.invoke({"vault": ""}, "/api/andrea/notes/config")
        self.assertEqual(result[0]["status"], 200)
        self.assertFalse(self.store.status()["available"])


if __name__ == "__main__":
    unittest.main()

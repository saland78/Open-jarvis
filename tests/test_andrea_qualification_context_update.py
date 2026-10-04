"""One-file installer uses the existing verified transaction and refuses drift."""
import ast
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = 'scripts/andrea/qualification_compact_wire.py'
OLD = ROOT/'tests/fixtures/andrea/qualification_compact_wire_before_context.py'
spec = importlib.util.spec_from_file_location('context_update', ROOT/'scripts/andrea/update_qualification_context.py')
updater = importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)


class ContextUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name); self.project = self.home/'Project'
        (self.project/'profiles').mkdir(parents=True)
        (self.project/'Avvia-OpenJarvis.command').write_text('marker')
        self.sentinels = {self.project/'profiles/andrea-local.toml': b'PRIVATE PROFILE',
                          self.project/'.env': b'PRIVATE ENV',
                          self.home/'.openjarvis-andrea/data.db': b'PRIVATE DATABASE',
                          self.home/'Vault/note.md': b'PRIVATE NOTE'}
        for path, content in self.sentinels.items():
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
        for relative in updater.CHECKS:
            file = self.project/relative; file.parent.mkdir(parents=True, exist_ok=True)
            source = ROOT/'tests/fixtures/andrea/runtime_before_manual_memory.py' if relative == 'scripts/andrea/runtime.py' else ROOT/relative
            shutil.copy2(source, file)
        shutil.copy2(OLD, self.project/PATH)
        self.new = (ROOT/PATH).read_bytes()
        self.manifest = [dict(item) for item in updater.MANIFEST]

    def fetch(self, relative, destination):
        self.assertEqual(relative, PATH)
        destination.write_bytes(self.new)

    def run_update(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return updater.update(self.project, self.manifest, kwargs.pop('fetch', self.fetch),
                                  home=self.home, port=kwargs.pop('port', 0), **kwargs)

    def unchanged(self):
        self.assertEqual((self.project/PATH).read_bytes(), OLD.read_bytes())
        for path, content in self.sentinels.items(): self.assertEqual(path.read_bytes(), content)

    def test_actual_one_file_manifest_backup_and_repeat_keep_all_other_data(self):
        self.assertEqual(len(updater.MANIFEST), 1)
        self.assertEqual(updater.MANIFEST[0]['path'], PATH)
        self.assertEqual(updater.MANIFEST[0]['before'], updater.digest(OLD))
        self.assertEqual(updater.MANIFEST[0]['sha256'], hashlib.sha256(self.new).hexdigest())
        self.assertRegex(updater.REVISION, r'^[0-9a-f]{40}$')
        backup = self.run_update()
        self.assertEqual((backup/PATH).read_bytes(), OLD.read_bytes())
        self.assertEqual(json.loads((backup/'manifest.json').read_text())['existing'], {PATH: True})
        self.assertEqual((self.project/PATH).read_bytes(), self.new)
        self.assertEqual((self.project/PATH).stat().st_mode & 0o777, 0o644)
        second = self.run_update()
        self.assertEqual((second/PATH).read_bytes(), self.new)
        for path, content in self.sentinels.items(): self.assertEqual(path.read_bytes(), content)
        for relative, expected in updater.CHECKS.items():
            self.assertEqual(updater.digest(self.project/relative), expected)

    def test_old_transaction_code_is_reused_byte_for_byte(self):
        current = (ROOT/'scripts/andrea/update_qualification_context.py').read_text()
        previous = (ROOT/'scripts/andrea/update_compact_qualifications.py').read_text()
        functions = lambda t: {n.name: ast.get_source_segment(t, n) for n in ast.parse(t).body
                               if isinstance(n, ast.FunctionDef)}
        self.assertEqual(functions(current), functions(previous))

    def test_corrupt_or_invalid_python_download_and_atomic_replace_failure_preserve_old_file(self):
        def corrupt(relative, destination): destination.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'Verifica del download'): self.run_update(fetch=corrupt)
        self.unchanged()
        bad = b'if invalid::'
        self.manifest[0]['sha256'] = hashlib.sha256(bad).hexdigest()
        with self.assertRaisesRegex(ValueError, 'Sintassi Python'):
            self.run_update(fetch=lambda relative, destination: destination.write_bytes(bad))
        self.unchanged()
        self.manifest = [dict(item) for item in updater.MANIFEST]
        def failed(source, destination): raise OSError('synthetic disk failure')
        with self.assertRaisesRegex(OSError, 'synthetic disk failure'): self.run_update(replace=failed)
        self.unchanged()
        self.assertFalse(list(self.project.rglob('*.update')))

    def test_every_dependency_missing_changed_or_symlink_refuses_before_network(self):
        def unexpected(*args): self.fail('No download expected')
        for relative in updater.CHECKS:
            file = self.project/relative; original = file.read_bytes()
            file.write_bytes(b'local edit')
            with self.assertRaisesRegex(ValueError, 'Componente diverso'): self.run_update(fetch=unexpected)
            file.unlink()
            with self.assertRaisesRegex(ValueError, 'Componente diverso'): self.run_update(fetch=unexpected)
            file.symlink_to(ROOT/relative)
            with self.assertRaisesRegex(ValueError, 'Componente diverso'): self.run_update(fetch=unexpected)
            file.unlink(); file.write_bytes(original)
        self.unchanged()

    def test_helper_missing_locally_edited_or_symlink_is_not_replaced(self):
        file = self.project/PATH
        file.write_bytes(b'local edit')
        with self.assertRaisesRegex(ValueError, 'modifiche diverse'): self.run_update()
        self.assertEqual(file.read_bytes(), b'local edit')
        file.unlink()
        with self.assertRaisesRegex(ValueError, 'previsto mancante'): self.run_update()
        file.symlink_to(ROOT/PATH)
        with self.assertRaisesRegex(ValueError, 'Collegamento simbolico'): self.run_update()
        file.unlink(); shutil.copy2(OLD, file); self.unchanged()

    def test_busy_port_and_wrong_project_refuse_before_fetch(self):
        def unexpected(*args): self.fail('No download expected')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            with self.assertRaisesRegex(ValueError, 'porta 8008'):
                self.run_update(port=listener.getsockname()[1], fetch=unexpected)
        (self.project/'Avvia-OpenJarvis.command').unlink()
        with self.assertRaisesRegex(ValueError, 'non è la cartella'): self.run_update(fetch=unexpected)
        self.unchanged()

    def test_concurrent_source_or_dependency_edit_is_preserved(self):
        for relative, reason in ((PATH, 'cambiato durante'),
                                 ('scripts/andrea/qualification_sentence_guard.py', 'Componente diverso')):
            file = self.project/relative; original = file.read_bytes()
            def fetch(path, destination):
                self.fetch(path, destination); file.write_bytes(b'concurrent edit')
            with self.assertRaisesRegex(ValueError, reason): self.run_update(fetch=fetch)
            self.assertEqual(file.read_bytes(), b'concurrent edit')
            file.write_bytes(original)
        self.unchanged()


if __name__ == '__main__': unittest.main()

"""Pinned one-file asynchronous translation installer: preserves private data and rolls back failed replacements."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
from pathlib import Path
import shutil
import socket
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('web_language_alias_update', ROOT/'scripts/andrea/update_web_language_alias.py')
updater = importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)


def published_source(relative):
    return (ROOT/relative).read_bytes()


def original(relative):
    return (ROOT/'tests/fixtures/andrea/web_sentence_contract.py_before_english_alias').read_bytes()


class LanguageAliasUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name); self.project = self.home/'project'
        (self.project/'profiles').mkdir(parents=True)
        (self.project/'Avvia-OpenJarvis.command').write_text('marker')
        self.private = {self.project/'profiles/andrea-local.toml': b'PRIVATE PROFILE',
                        self.project/'.env': b'PRIVATE CONFIG',
                        self.home/'.openjarvis-andrea/manual-memory.json': b'PRIVATE MEMORY',
                        self.home/'.openjarvis-andrea/database.sqlite': b'PRIVATE DATABASE',
                        self.home/'Vault/note.md': b'PRIVATE NOTE'}
        for path, data in self.private.items():
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        for relative in updater.CHECKS:
            target = self.project/relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(published_source(relative))
        self.old = {}
        for item in updater.MANIFEST:
            target = self.project/item['path']; target.parent.mkdir(parents=True, exist_ok=True)
            data = original(item['path']) if 'before' in item else None
            self.old[item['path']] = data
            if data is None: target.unlink(missing_ok=True)
            else: target.write_bytes(data)

    def fetch(self, relative, path): path.write_bytes(published_source(relative))

    def update(self, **kw):
        with redirect_stdout(io.StringIO()):
            return updater.update(self.project, fetch=kw.pop('fetch', self.fetch), home=self.home, port=kw.pop('port', 0), **kw)

    def check_private(self):
        for path, data in self.private.items(): self.assertEqual(path.read_bytes(), data)

    def check_old(self):
        for relative, data in self.old.items():
            path = self.project/relative
            if data is None: self.assertFalse(path.exists())
            else: self.assertEqual(path.read_bytes(), data)
        self.check_private()

    def test_actual_manifest_backup_repeat_and_no_private_changes(self):
        self.assertEqual(len(updater.MANIFEST), 1)
        self.assertEqual(updater.REVISION, 'a489865be6e4c10bacbe26d4bd5d6d0dd4fc9e41')
        for item in updater.MANIFEST:
            self.assertEqual(hashlib.sha256(published_source(item['path'])).hexdigest(), item['sha256'])
            if 'before' in item:
                self.assertEqual(hashlib.sha256(self.old[item['path']]).hexdigest(), item['before'])
        backup = self.update()
        for relative, data in self.old.items():
            self.assertEqual((self.project/relative).read_bytes(), published_source(relative))
            if data is not None: self.assertEqual((backup/relative).read_bytes(), data)
        self.update(); self.check_private()

    def test_bad_download_does_not_apply_any_file(self):
        def fetch(relative, path): path.write_bytes(b'wrong hash')
        with self.assertRaises(ValueError): self.update(fetch=fetch)
        self.check_old()

    def test_local_edit_refused_before_download(self):
        path = self.project/'scripts/andrea/runtime.py'; path.write_text('local edit')
        called = []
        with self.assertRaises(ValueError): self.update(fetch=lambda *args: called.append(args))
        self.assertFalse(called); self.assertEqual(path.read_text(), 'local edit'); self.check_private()

    def test_occupied_port_does_not_kill_or_apply(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen(1)
            with self.assertRaises(ValueError): self.update(port=listener.getsockname()[1])
            self.assertGreater(listener.fileno(), 0)
        self.check_old()

    def test_failed_replacement_preserves_existing_file(self):
        real = updater.os.replace; count = 0
        def replace(source, dest):
            nonlocal count
            count += 1
            if count == 1: raise OSError('synthetic replacement failure')
            return real(source, dest)
        with self.assertRaises(OSError): self.update(replace=replace)
        self.check_old()

    def test_existing_module_edit_and_symlink_refused(self):
        path = self.project/'scripts/andrea/web_page_fetch.py'
        path.write_text('different implementation')
        with self.assertRaises(ValueError): self.update()
        self.assertEqual(path.read_text(), 'different implementation'); path.unlink()
        path.symlink_to(next(iter(self.private)))
        with self.assertRaises(ValueError): self.update()
        self.check_private()

    def test_change_during_download_refuses_apply(self):
        path = self.project/'scripts/andrea/web_sentence_contract.py'
        def fetch(relative, destination):
            self.fetch(relative, destination)
            if relative == updater.MANIFEST[-1]['path']: path.write_text('changed during download')
        with self.assertRaises(ValueError): self.update(fetch=fetch)
        self.assertEqual(path.read_text(), 'changed during download')
        self.assertEqual((self.project/'scripts/andrea/web_page_local.py').read_bytes(), published_source('scripts/andrea/web_page_local.py'))
        self.check_private()

    def test_invalid_python_is_rejected_before_replacement(self):
        bad = b'def invalid(:\n'
        manifest=[{**updater.MANIFEST[0], 'sha256':hashlib.sha256(bad).hexdigest()}]
        with self.assertRaisesRegex(ValueError, 'Sintassi Python non valida'):
            self.update(manifest=manifest, fetch=lambda relative,path:path.write_bytes(bad))
        self.check_old()



if __name__ == '__main__': unittest.main()

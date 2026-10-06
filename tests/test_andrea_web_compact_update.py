"""Compact-v9 integration installer: atomic replacement and partial rollback."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import shutil
import socket
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('web_compact_v9_update', ROOT/'scripts/andrea/update_web_compact_v9.py')
updater = importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)


def published_source(relative):
    return (ROOT/relative).read_bytes()


def original(relative):
    return (ROOT/'tests/fixtures/andrea/web_page_context_contract.py_before_compact_v9').read_bytes()



class CompactV9UpdateTests(unittest.TestCase):
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
            target.write_bytes(original(relative) if relative == 'scripts/andrea/web_page_context_contract.py' else published_source(relative))
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
        self.assertEqual(len(updater.MANIFEST), 12)
        self.assertEqual(updater.REVISION, 'b0cf9a636ab4a198096d86ea3fba18ef9e0c85b0')
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
            if count == 5: raise OSError('synthetic replacement failure')
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
        path = self.project/'scripts/andrea/web_page_local.py'
        def fetch(relative, destination):
            self.fetch(relative, destination)
            if relative == updater.MANIFEST[-1]['path']: path.write_text('changed during download')
        with self.assertRaises(ValueError): self.update(fetch=fetch)
        self.assertEqual(path.read_text(), 'changed during download')
        for relative, data in self.old.items():
            if relative == 'scripts/andrea/web_page_local.py': continue
            file = self.project/relative
            if data is None: self.assertFalse(file.exists())
            else: self.assertEqual(file.read_bytes(), data)
        self.check_private()

    def test_invalid_python_is_rejected_before_replacement(self):
        bad = b'def invalid(:\n'
        manifest=[{**updater.MANIFEST[0], 'sha256':hashlib.sha256(bad).hexdigest()}]
        with self.assertRaisesRegex(ValueError, 'Sintassi Python non valida'):
            self.update(manifest=manifest, fetch=lambda relative,path:path.write_bytes(bad))
        self.check_old()



    def test_new_file_collision_is_refused_before_first_download(self):
        path = self.project/'scripts/andrea/web_candidate_pipeline.py'
        path.write_text('existing independent implementation')
        calls = []
        with self.assertRaisesRegex(ValueError, 'File nuovo già presente'):
            self.update(fetch=lambda *args: calls.append(args))
        self.assertEqual(calls, [])
        self.assertEqual(path.read_text(), 'existing independent implementation')
        self.check_private()

    def test_module_import_failure_precedes_backup_and_replacement(self):
        with patch.object(updater, 'validate_staged_modules', side_effect=ValueError('synthetic import failure')):
            with self.assertRaisesRegex(ValueError, 'synthetic import failure'):
                self.update()
        self.assertFalse((self.home/'.openjarvis-andrea/update-backups').exists())
        self.check_old()

    def test_staged_modules_import_in_isolated_no_bytecode_interpreter(self):
        calls = []
        def run(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(returncode=0)
        with patch.object(updater.subprocess, 'run', side_effect=run):
            updater.validate_staged_modules(self.project, self.project)
        command, kwargs = calls[0]
        self.assertEqual(command[1:3], ['-I', '-B'])
        self.assertEqual(kwargs['timeout'], 10)
        self.assertTrue(kwargs['capture_output'])
        self.assertNotIn('model', command[4])
        self.assertNotIn('vault', command[4])


if __name__ == '__main__': unittest.main()

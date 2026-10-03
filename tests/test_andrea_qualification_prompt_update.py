"""Actual two-file update transaction; synthetic install and no network."""
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
spec = importlib.util.spec_from_file_location(
    'qualification_update', ROOT/'scripts/andrea/update_qualification_prompt.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
OLD_BRIDGE = ROOT/'tests/fixtures/andrea/note_facts_before_qualification.py'
HELPER = 'scripts/andrea/qualification_prompt.py'
BRIDGE = 'scripts/andrea/note_facts.py'


class QualificationUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.project = self.home/'Project'
        (self.project/'profiles').mkdir(parents=True)
        (self.project/'Avvia-OpenJarvis.command').write_text('marker')
        self.sentinels = {
            self.project/'profiles/andrea-local.toml': b'PRIVATE PROFILE',
            self.project/'.env': b'PRIVATE ENV',
            self.home/'.openjarvis-andrea/data.db': b'PRIVATE DATABASE',
            self.home/'Vault/note.md': b'PRIVATE NOTE',
        }
        for path, content in self.sentinels.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        for relative in updater.CHECKS:
            target = self.project/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/relative, target)
        shutil.copy2(OLD_BRIDGE, self.project/BRIDGE)
        self.payload = {item['path']: (ROOT/item['path']).read_bytes()
                        for item in updater.MANIFEST}
        self.manifest = [dict(item) for item in updater.MANIFEST]

    def run_update(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return updater.update(
                self.project, self.manifest,
                kwargs.pop('fetch', self.fetch), home=self.home,
                port=kwargs.pop('port', 0), **kwargs)

    def fetch(self, relative, destination):
        destination.write_bytes(self.payload[relative])

    def assert_original_install(self):
        self.assertEqual((self.project/BRIDGE).read_bytes(), OLD_BRIDGE.read_bytes())
        self.assertFalse((self.project/HELPER).exists())

    def test_success_actual_files_backup_permissions_sentinels_and_repeat(self):
        backup = self.run_update()
        self.assertEqual((backup/BRIDGE).read_bytes(), OLD_BRIDGE.read_bytes())
        saved = json.loads((backup/'manifest.json').read_text())
        self.assertEqual(saved['existing'], {HELPER: False, BRIDGE: True})
        for relative, content in self.payload.items():
            target = self.project/relative
            self.assertEqual(target.read_bytes(), content)
            self.assertEqual(target.stat().st_mode & 0o777, 0o644)
        for path, content in self.sentinels.items():
            self.assertEqual(path.read_bytes(), content)
        for relative, expected in updater.CHECKS.items():
            self.assertEqual(updater.digest(self.project/relative), expected)
        second = self.run_update()
        self.assertEqual((second/BRIDGE).read_bytes(), self.payload[BRIDGE])
        self.assertEqual((second/HELPER).read_bytes(), self.payload[HELPER])

    def test_corrupt_second_download_never_applies_first(self):
        def fetch(relative, destination):
            destination.write_bytes(b'wrong' if relative == BRIDGE else self.payload[relative])
        with self.assertRaisesRegex(ValueError, 'Verifica del download'):
            self.run_update(fetch=fetch)
        self.assert_original_install()
        self.assertFalse((self.home/'.openjarvis-andrea/update-backups').exists())

    def test_collision_modified_bridge_and_missing_bridge_refuse(self):
        (self.project/HELPER).write_bytes(b'local helper')
        with self.assertRaisesRegex(ValueError, 'presente un file diverso'):
            self.run_update()
        self.assertEqual((self.project/HELPER).read_bytes(), b'local helper')
        (self.project/HELPER).unlink()
        (self.project/BRIDGE).write_bytes(b'local bridge')
        with self.assertRaisesRegex(ValueError, 'modifiche diverse'):
            self.run_update()
        self.assertEqual((self.project/BRIDGE).read_bytes(), b'local bridge')
        (self.project/BRIDGE).unlink()
        with self.assertRaisesRegex(ValueError, 'previsto mancante'):
            self.run_update()
        self.assertFalse((self.project/HELPER).exists())

    def test_occupied_port_symlink_and_wrong_project_refuse_before_fetch(self):
        def unexpected_fetch(*args):
            self.fail('download should not start')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            with self.assertRaisesRegex(ValueError, 'porta 8008'):
                self.run_update(port=listener.getsockname()[1], fetch=unexpected_fetch)
        guard = self.project/'scripts/andrea/runtime.py'
        guard.unlink()
        guard.symlink_to(ROOT/'scripts/andrea/runtime.py')
        with self.assertRaisesRegex(ValueError, 'Componente diverso'):
            self.run_update(fetch=unexpected_fetch)
        guard.unlink()
        shutil.copy2(ROOT/'scripts/andrea/runtime.py', guard)
        (self.project/'Avvia-OpenJarvis.command').unlink()
        with self.assertRaisesRegex(ValueError, 'non è la cartella'):
            self.run_update(fetch=unexpected_fetch)
        self.assert_original_install()

    def test_second_replacement_failure_removes_new_helper_and_keeps_bridge(self):
        calls = []
        def replace(source, destination):
            calls.append(destination)
            if len(calls) == 2:
                raise OSError('synthetic disk failure')
            os.replace(source, destination)
        with self.assertRaisesRegex(OSError, 'synthetic disk failure'):
            self.run_update(replace=replace)
        self.assert_original_install()
        self.assertFalse(list(self.project.rglob('*.update')))

    def test_modified_or_missing_guard_refuses_before_fetch(self):
        def unexpected_fetch(*args):
            self.fail('download should not start')
        guard = self.project/'scripts/andrea/runtime.py'
        guard.write_bytes(b'local runtime modification')
        with self.assertRaisesRegex(ValueError, 'Componente diverso'):
            self.run_update(fetch=unexpected_fetch)
        self.assertEqual(guard.read_bytes(), b'local runtime modification')
        guard.unlink()
        with self.assertRaisesRegex(ValueError, 'Componente diverso'):
            self.run_update(fetch=unexpected_fetch)
        self.assert_original_install()

    def test_guard_edit_during_download_is_preserved_and_refuses_all_files(self):
        guard = self.project/'scripts/andrea/runtime.py'
        def fetch(relative, destination):
            self.fetch(relative, destination)
            if relative == BRIDGE:
                guard.write_bytes(b'concurrent runtime edit')
        with self.assertRaisesRegex(ValueError, 'Componente diverso'):
            self.run_update(fetch=fetch)
        self.assertEqual(guard.read_bytes(), b'concurrent runtime edit')
        self.assert_original_install()

    def test_matching_hash_with_invalid_python_refuses_before_apply(self):
        self.payload[BRIDGE] = b'if invalid syntax::'
        self.manifest[1]['sha256'] = hashlib.sha256(self.payload[BRIDGE]).hexdigest()
        with self.assertRaisesRegex(ValueError, 'Sintassi Python'):
            self.run_update()
        self.assert_original_install()

    def test_bridge_edit_during_download_is_preserved_and_refuses_helper(self):
        def fetch(relative, destination):
            self.fetch(relative, destination)
            if relative == BRIDGE:
                (self.project/BRIDGE).write_bytes(b'concurrent bridge edit')
        with self.assertRaisesRegex(ValueError, 'cambiato durante'):
            self.run_update(fetch=fetch)
        self.assertEqual((self.project/BRIDGE).read_bytes(), b'concurrent bridge edit')
        self.assertFalse((self.project/HELPER).exists())

    def test_manifest_matches_two_runtime_files_and_preserves_seven_guards(self):
        self.assertRegex(updater.REVISION, r'^[0-9a-f]{40}$')
        self.assertNotEqual(updater.REVISION, '0'*40)
        self.assertEqual([item['path'] for item in updater.MANIFEST], [HELPER, BRIDGE])
        self.assertTrue(updater.MANIFEST[0]['new'])
        self.assertEqual(updater.MANIFEST[1]['before'], updater.digest(OLD_BRIDGE))
        for item in updater.MANIFEST:
            self.assertEqual(updater.digest(ROOT/item['path']), item['sha256'])
        self.assertEqual(len(updater.CHECKS), 7)
        self.assertFalse(set(updater.CHECKS) & {HELPER, BRIDGE})
        for relative, expected in updater.CHECKS.items():
            self.assertEqual(updater.digest(ROOT/relative), expected)


if __name__ == '__main__':
    unittest.main()

"""Actual two-file manifest, synthetic install, no network or personal data."""
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
spec = importlib.util.spec_from_file_location('compact_update', ROOT/'scripts/andrea/update_compact_qualifications.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
HELPER = 'scripts/andrea/qualification_compact_wire.py'
BRIDGE = 'scripts/andrea/note_facts.py'
OLD_BRIDGE = ROOT/'tests/fixtures/andrea/note_facts_before_compact_wire.py'
OLD_WIRE = ROOT/'tests/fixtures/andrea/qualification_compact_wire_before_context.py'


class CompactUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.project = self.home/'Project'
        (self.project/'profiles').mkdir(parents=True)
        (self.project/'Avvia-OpenJarvis.command').write_text('marker')
        self.sentinels = {
            self.project/'profiles/andrea-local.toml': b'PRIVATE PROFILE',
            self.project/'.env': b'PRIVATE ENV',
            self.home/'.openjarvis-andrea/data.db': b'PRIVATE DATABASE',
            self.home/'Vault/note.md': b'PRIVATE NOTE',
        }
        for path, data in self.sentinels.items():
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        for relative in updater.CHECKS:
            target = self.project/relative; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/relative, target)
        shutil.copy2(OLD_BRIDGE, self.project/BRIDGE)
        self.payload = {item['path']: (OLD_WIRE if item['path'] == HELPER else ROOT/item['path']).read_bytes() for item in updater.MANIFEST}
        self.manifest = [dict(item) for item in updater.MANIFEST]

    def fetch(self, relative, destination):
        destination.write_bytes(self.payload[relative])

    def run_update(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return updater.update(self.project, self.manifest, kwargs.pop('fetch', self.fetch),
                                  home=self.home, port=kwargs.pop('port', 0), **kwargs)

    def assert_original(self):
        self.assertFalse((self.project/HELPER).exists())
        self.assertEqual((self.project/BRIDGE).read_bytes(), OLD_BRIDGE.read_bytes())
        for path, content in self.sentinels.items():
            self.assertEqual(path.read_bytes(), content)

    def test_actual_manifest_installs_backs_up_and_repeats_without_changing_guards_or_data(self):
        backup = self.run_update()
        self.assertEqual((backup/BRIDGE).read_bytes(), OLD_BRIDGE.read_bytes())
        self.assertEqual(json.loads((backup/'manifest.json').read_text())['existing'], {HELPER: False, BRIDGE: True})
        for relative, data in self.payload.items():
            self.assertEqual((self.project/relative).read_bytes(), data)
            self.assertEqual((self.project/relative).stat().st_mode & 0o777, 0o644)
        for relative, expected in updater.CHECKS.items():
            self.assertEqual(updater.digest(self.project/relative), expected)
        for path, data in self.sentinels.items():
            self.assertEqual(path.read_bytes(), data)
        second = self.run_update()
        self.assertEqual((second/BRIDGE).read_bytes(), self.payload[BRIDGE])
        self.assertEqual((second/HELPER).read_bytes(), self.payload[HELPER])

    def test_corrupt_second_download_never_applies_first_file(self):
        def fetch(relative, destination):
            destination.write_bytes(b'wrong' if relative == BRIDGE else self.payload[relative])
        with self.assertRaisesRegex(ValueError, 'Verifica del download'):
            self.run_update(fetch=fetch)
        self.assert_original()
        self.assertFalse((self.home/'.openjarvis-andrea/update-backups').exists())

    def test_modified_bridge_missing_bridge_and_existing_different_helper_are_preserved(self):
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

    def test_busy_port_symlink_and_wrong_project_refuse_before_fetch(self):
        def unexpected_fetch(*args): self.fail('No download expected')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0)); listener.listen()
            with self.assertRaisesRegex(ValueError, 'porta 8008'):
                self.run_update(port=listener.getsockname()[1], fetch=unexpected_fetch)
        guard = self.project/'scripts/andrea/runtime.py'; guard.unlink()
        guard.symlink_to(ROOT/'scripts/andrea/runtime.py')
        with self.assertRaisesRegex(ValueError, 'Componente diverso'):
            self.run_update(fetch=unexpected_fetch)
        guard.unlink(); shutil.copy2(ROOT/'scripts/andrea/runtime.py', guard)
        (self.project/'Avvia-OpenJarvis.command').unlink()
        with self.assertRaisesRegex(ValueError, 'non è la cartella'):
            self.run_update(fetch=unexpected_fetch)
        self.assert_original()

    def test_second_replace_failure_rolls_back_new_helper_and_old_bridge(self):
        calls = []
        def replace(source, destination):
            calls.append(destination)
            if len(calls) == 2: raise OSError('synthetic disk failure')
            os.replace(source, destination)
        with self.assertRaisesRegex(OSError, 'synthetic disk failure'):
            self.run_update(replace=replace)
        self.assert_original()
        self.assertFalse(list(self.project.rglob('*.update')))

    def test_guard_edit_or_bridge_edit_during_download_refuse_all_replacements(self):
        for relative, error in [('scripts/andrea/qualification_sentence_guard.py', 'Componente diverso'),
                                (BRIDGE, 'cambiato durante')]:
            original = (self.project/relative).read_bytes()
            def fetch(path, destination):
                self.fetch(path, destination)
                if path == BRIDGE: (self.project/relative).write_bytes(b'concurrent edit')
            with self.assertRaisesRegex(ValueError, error):
                self.run_update(fetch=fetch)
            self.assertEqual((self.project/relative).read_bytes(), b'concurrent edit')
            self.assertFalse((self.project/HELPER).exists())
            (self.project/relative).write_bytes(original)

    def test_invalid_python_with_matching_manifest_hash_refuses_before_backup(self):
        self.payload[BRIDGE] = b'if invalid::'
        self.manifest[1]['sha256'] = hashlib.sha256(self.payload[BRIDGE]).hexdigest()
        with self.assertRaisesRegex(ValueError, 'Sintassi Python'):
            self.run_update()
        self.assert_original()

    def test_every_immutable_dependency_is_verified_before_network(self):
        def unexpected_fetch(*args): self.fail('No download expected')
        for relative in updater.CHECKS:
            file = self.project/relative; original = file.read_bytes()
            file.write_bytes(b'changed dependency')
            with self.assertRaisesRegex(ValueError, 'Componente diverso'):
                self.run_update(fetch=unexpected_fetch)
            file.unlink()
            with self.assertRaisesRegex(ValueError, 'Componente diverso'):
                self.run_update(fetch=unexpected_fetch)
            file.write_bytes(original)
        self.assert_original()

    def test_parent_symlink_and_helper_symlink_are_not_followed(self):
        (self.project/HELPER).symlink_to(ROOT/HELPER)
        with self.assertRaisesRegex(ValueError, 'Collegamento simbolico'):
            self.run_update()
        (self.project/HELPER).unlink()
        folder = self.project/'scripts/andrea'; outside = self.home/'external'
        folder.rename(outside); folder.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Componente diverso'):
            self.run_update()
        self.assertFalse((outside/'qualification_compact_wire.py').exists())
        self.assertEqual((outside/'note_facts.py').read_bytes(), OLD_BRIDGE.read_bytes())

    def test_manifest_is_exactly_two_files_with_unchanged_frontend_and_guards(self):
        self.assertRegex(updater.REVISION, r'^[0-9a-f]{40}$')
        self.assertNotEqual(updater.REVISION, '0'*40)
        self.assertEqual([item['path'] for item in updater.MANIFEST], [HELPER, BRIDGE])
        self.assertTrue(updater.MANIFEST[0]['new'])
        self.assertEqual(updater.MANIFEST[1]['before'], updater.digest(OLD_BRIDGE))
        for item in updater.MANIFEST:
            self.assertEqual(updater.digest(OLD_WIRE if item['path'] == HELPER else ROOT/item['path']), item['sha256'])
        self.assertEqual(len(updater.CHECKS), 11)
        self.assertFalse(set(updater.CHECKS) & {HELPER, BRIDGE})
        for relative, expected in updater.CHECKS.items():
            self.assertEqual(updater.digest(ROOT/relative), expected)


if __name__ == '__main__': unittest.main()

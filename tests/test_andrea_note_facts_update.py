"""Pinned update transaction tested without network or personal data."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fact_update', ROOT/'scripts/andrea/update_note_facts.py')
updater = importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)


class FactUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name); self.project = self.home/'Project'
        (self.project/'profiles').mkdir(parents=True)
        (self.project/'Avvia-OpenJarvis.command').write_text('marker')
        (self.project/'profiles/andrea-local.toml').write_text('PRIVATE CONFIG')
        (self.project/'.env').write_text('PRIVATE ENV')
        (self.project/'old.py').write_bytes(b"value = 'old'\n")
        self.payload = {'old.py': b"value = 'new'\n", 'new.py':b"module = 'new'\n", 'later.py':b"later = True\n"}
        self.manifest = [{'path':path, 'sha256':hashlib.sha256(value).hexdigest(),
                          **({'before':hashlib.sha256(b"value = 'old'\n").hexdigest()} if path == 'old.py' else {'new':True})}
                         for path,value in self.payload.items()]

    def run_update(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return updater.update(self.project,self.manifest,kwargs.pop('fetch',lambda p,d:self.fetch(p,d)),
                                  home=self.home,port=kwargs.pop('port',0),**kwargs)

    def fetch(self,path,dest):
        dest.write_bytes(self.payload[path])

    def test_success_backups_modes_config_and_idempotent_repeat(self):
        backup = self.run_update()
        self.assertEqual((backup/'old.py').read_bytes(), b"value = 'old'\n")
        for path,value in self.payload.items(): self.assertEqual((self.project/path).read_bytes(),value)
        self.assertEqual((self.project/'.env').read_text(),'PRIVATE ENV')
        self.assertEqual((self.project/'profiles/andrea-local.toml').read_text(),'PRIVATE CONFIG')
        self.assertFalse(json.loads((backup/'manifest.json').read_text())['existing']['new.py'])
        self.run_update()

    def test_bad_last_download_hash_never_applies_any_file(self):
        def fetch(path,dest): dest.write_bytes(b'wrong' if path == 'later.py' else self.payload[path])
        with self.assertRaises(ValueError): self.run_update(fetch=fetch)
        self.assertEqual((self.project/'old.py').read_bytes(), b"value = 'old'\n")
        self.assertFalse((self.project/'new.py').exists())

    def test_collision_modified_source_and_missing_previous_file_refuse(self):
        (self.project/'new.py').write_text('private local module')
        with self.assertRaises(ValueError): self.run_update()
        self.assertEqual((self.project/'new.py').read_text(),'private local module')
        (self.project/'new.py').unlink(); (self.project/'old.py').write_text('local modification')
        with self.assertRaises(ValueError): self.run_update()
        self.assertEqual((self.project/'old.py').read_text(),'local modification')
        (self.project/'old.py').unlink()
        with self.assertRaises(ValueError): self.run_update()
        self.assertFalse((self.project/'new.py').exists())

    def test_python_syntax_is_checked_before_any_replacement(self):
        self.payload['later.py'] = b'if syntax is invalid::'
        self.manifest[-1]['sha256'] = hashlib.sha256(self.payload['later.py']).hexdigest()
        with self.assertRaisesRegex(ValueError,'Sintassi Python'): self.run_update()
        self.assertEqual((self.project/'old.py').read_bytes(), b"value = 'old'\n")
        self.assertFalse((self.project/'new.py').exists())

    def test_source_edit_during_download_is_not_overwritten(self):
        def fetch(path,dest):
            self.fetch(path,dest)
            if path == 'later.py': (self.project/'old.py').write_text('concurrent edit')
        with self.assertRaisesRegex(ValueError,'cambiato durante'): self.run_update(fetch=fetch)
        self.assertEqual((self.project/'old.py').read_text(),'concurrent edit')
        self.assertFalse((self.project/'new.py').exists())

    def test_third_replacement_failure_restores_old_and_removes_new_module(self):
        calls = []
        def replace(src,dest):
            calls.append(dest)
            if len(calls) == 3: raise OSError('synthetic disk error')
            os.replace(src,dest)
        with self.assertRaises(OSError): self.run_update(replace=replace)
        self.assertEqual((self.project/'old.py').read_bytes(), b"value = 'old'\n")
        self.assertFalse((self.project/'new.py').exists())

    def test_occupied_port_symlink_or_wrong_project_refuse(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0)); listener.listen()
            with self.assertRaises(ValueError): self.run_update(port=listener.getsockname()[1])
        (self.project/'new.py').symlink_to(self.project/'old.py')
        with self.assertRaises(ValueError): self.run_update()
        (self.project/'new.py').unlink(); (self.project/'Avvia-OpenJarvis.command').unlink()
        with self.assertRaises(ValueError): self.run_update()

    def test_production_manifest_matches_source_and_includes_no_data_or_dependencies(self):
        self.assertRegex(updater.REVISION,r'^[0-9a-f]{40}$')
        self.assertEqual(len(updater.MANIFEST),7)
        self.assertEqual(len({item['path'] for item in updater.MANIFEST}),7)
        for item in updater.MANIFEST:
            historical = {
                'scripts/andrea/note_facts.py': 'note_facts_before_qualification.py',
                'scripts/andrea/runtime.py': 'runtime-before-native-phases.py',
                'src/openjarvis/engine/ollama.py': 'ollama-before-native-phases.py',
            }
            source = (ROOT/'tests/fixtures/andrea'/historical[item['path']]
                      if item['path'] in historical else ROOT/item['path'])
            self.assertEqual(updater.digest(source),item['sha256'])
            self.assertTrue(item['path'].endswith(('.py','.tsx')))
        self.assertEqual({item['path'] for item in updater.MANIFEST if item.get('new')}, {
            'scripts/andrea/markdown_fact_adapter.py','scripts/andrea/predicate_context_synthesis.py','scripts/andrea/note_facts.py'})


if __name__ == '__main__': unittest.main()

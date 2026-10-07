"""Real four-file updater transaction; exact old fixtures, no network or Mac."""
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

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_update',ROOT/'scripts/andrea/update_native_phases.py')
updater=importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)
OLD={
 'scripts/andrea/runtime.py':ROOT/'tests/fixtures/andrea/runtime-before-native-phases.py',
 'src/openjarvis/engine/ollama.py':ROOT/'tests/fixtures/andrea/ollama-before-native-phases.py',
}


class NativeUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name); self.project=self.home/'Project'
        (self.project/'profiles').mkdir(parents=True)
        (self.project/'Avvia-OpenJarvis.command').write_text('marker')
        self.sentinels={self.project/'profiles/andrea-local.toml':b'PRIVATE PROFILE',
                        self.project/'.env':b'PRIVATE ENV', self.home/'Vault/note.md':b'PRIVATE NOTE',
                        self.home/'.openjarvis-andrea/data.db':b'PRIVATE DB',
                        self.home/'OriginalJarvis/runtime.py':b'PRIVATE ORIGINAL'}
        for path,data in self.sentinels.items():
            path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        for relative in updater.CHECKS:
            path=self.project/relative; path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/relative,path)
        for relative,old in OLD.items():
            path=self.project/relative; path.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(old,path)
        self.payload={item['path']:(ROOT/item['path']).read_bytes() for item in updater.MANIFEST}
        self.manifest=[dict(item) for item in updater.MANIFEST]

    def fetch(self,relative,destination): destination.write_bytes(self.payload[relative])
    def run_update(self,**kwargs):
        with redirect_stdout(io.StringIO()):
            return updater.update(self.project,self.manifest,kwargs.pop('fetch',self.fetch),
                                  home=self.home,port=kwargs.pop('port',0),**kwargs)
    def assert_original(self):
        for relative,old in OLD.items(): self.assertEqual((self.project/relative).read_bytes(),old.read_bytes())
        for item in self.manifest:
            if item.get('new'): self.assertFalse((self.project/item['path']).exists())

    def test_success_actual_hashes_backups_sentinels_permissions_and_repeat(self):
        backup=self.run_update()
        for relative,old in OLD.items(): self.assertEqual((backup/relative).read_bytes(),old.read_bytes())
        saved=json.loads((backup/'manifest.json').read_text())
        self.assertEqual(saved['revision'],updater.REVISION)
        self.assertEqual(saved['existing'],{item['path']:item['path'] in OLD for item in self.manifest})
        for relative,data in self.payload.items():
            self.assertEqual((self.project/relative).read_bytes(),data)
            self.assertEqual((self.project/relative).stat().st_mode&0o777,0o644)
        for path,data in self.sentinels.items(): self.assertEqual(path.read_bytes(),data)
        for relative,sha in updater.CHECKS.items(): self.assertEqual(updater.digest(self.project/relative),sha)
        self.run_update()
        for relative,data in self.payload.items(): self.assertEqual((self.project/relative).read_bytes(),data)

    def test_bad_second_hash_never_applies_first(self):
        def fetch(relative,destination):
            destination.write_bytes(b'bad' if relative=='scripts/andrea/runtime.py' else self.payload[relative])
        with self.assertRaisesRegex(ValueError,'Verifica del download'): self.run_update(fetch=fetch)
        self.assert_original(); self.assertFalse((self.home/'.openjarvis-andrea/update-backups').exists())

    def test_collision_and_incompatible_or_missing_runtime_refuse(self):
        helper=self.project/'scripts/andrea/native_metrics.py'; helper.write_bytes(b'local helper')
        with self.assertRaisesRegex(ValueError,'presente un file diverso'): self.run_update()
        self.assertEqual(helper.read_bytes(),b'local helper'); helper.unlink()
        runtime=self.project/'scripts/andrea/runtime.py'; runtime.write_bytes(b'local runtime')
        with self.assertRaisesRegex(ValueError,'modifiche diverse'): self.run_update()
        self.assertEqual(runtime.read_bytes(),b'local runtime'); runtime.unlink()
        with self.assertRaisesRegex(ValueError,'previsto mancante'): self.run_update()
        self.assertFalse(helper.exists())

    def test_third_and_fourth_replace_failure_roll_back_existing_and_new(self):
        for failing_at in (3,4):
            calls=[]
            def replace(source,destination):
                calls.append(destination)
                if len(calls)==failing_at: raise OSError('synthetic disk failure')
                os.replace(source,destination)
            with self.assertRaisesRegex(OSError,'synthetic disk failure'): self.run_update(replace=replace)
            self.assert_original(); self.assertFalse(list(self.project.rglob('*.update')))

    def test_busy_port_symlink_and_wrong_project_stop_before_fetch(self):
        def unexpected(*args): self.fail('unexpected download')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0)); listener.listen()
            with self.assertRaisesRegex(ValueError,'porta 8008'):
                self.run_update(port=listener.getsockname()[1],fetch=unexpected)
        guard=self.project/'scripts/andrea/note_facts.py'; guard.unlink(); guard.symlink_to(ROOT/'scripts/andrea/note_facts.py')
        with self.assertRaisesRegex(ValueError,'Componente diverso'): self.run_update(fetch=unexpected)
        guard.unlink(); shutil.copy2(ROOT/'scripts/andrea/note_facts.py',guard)
        (self.project/'Avvia-OpenJarvis.command').unlink()
        with self.assertRaisesRegex(ValueError,'non è la cartella'): self.run_update(fetch=unexpected)
        self.assert_original()

    def test_guard_mismatch_or_missing_prevents_download(self):
        def unexpected(*args): self.fail('unexpected download')
        guard=self.project/'scripts/andrea/qualification_prompt.py'; guard.write_bytes(b'local change')
        with self.assertRaisesRegex(ValueError,'Componente diverso'): self.run_update(fetch=unexpected)
        self.assertEqual(guard.read_bytes(),b'local change'); guard.unlink()
        with self.assertRaisesRegex(ValueError,'Componente diverso'): self.run_update(fetch=unexpected)
        self.assert_original()

    def test_guard_edit_during_download_preserved_without_applying(self):
        guard=self.project/'scripts/andrea/note_facts.py'
        def fetch(relative,destination):
            self.fetch(relative,destination)
            if relative==self.manifest[-1]['path']: guard.write_bytes(b'concurrent edit')
        with self.assertRaisesRegex(ValueError,'Componente diverso'): self.run_update(fetch=fetch)
        self.assertEqual(guard.read_bytes(),b'concurrent edit'); self.assert_original()

    def test_existing_source_edit_during_download_preserved(self):
        runtime=self.project/'scripts/andrea/runtime.py'
        def fetch(relative,destination):
            self.fetch(relative,destination)
            if relative==self.manifest[-1]['path']: runtime.write_bytes(b'concurrent edit')
        with self.assertRaisesRegex(ValueError,'cambiato durante'): self.run_update(fetch=fetch)
        self.assertEqual(runtime.read_bytes(),b'concurrent edit')
        self.assertFalse((self.project/'scripts/andrea/native_metrics.py').exists())
        self.assertEqual((self.project/'src/openjarvis/engine/ollama.py').read_bytes(),OLD['src/openjarvis/engine/ollama.py'].read_bytes())

    def test_matching_hash_but_invalid_python_stops_before_apply(self):
        key='src/openjarvis/engine/ollama.py'; self.payload[key]=b'if invalid::'
        next(i for i in self.manifest if i['path']==key)['sha256']=hashlib.sha256(self.payload[key]).hexdigest()
        with self.assertRaisesRegex(ValueError,'Sintassi Python'): self.run_update()
        self.assert_original()

    def test_manifest_is_pinned_and_all_four_sources_and_eight_guards_match(self):
        self.assertRegex(updater.REVISION,r'^[0-9a-f]{40}$')
        self.assertEqual(len(updater.MANIFEST),4); self.assertEqual(len(updater.CHECKS),8)
        for item in updater.MANIFEST:
            self.assertEqual(updater.digest(ROOT/item['path']),item['sha256'])
            if item.get('before'): self.assertEqual(item['before'],updater.digest(OLD[item['path']]))
        self.assertFalse(set(updater.CHECKS)&set(self.payload))
        for relative,sha in updater.CHECKS.items(): self.assertEqual(updater.digest(ROOT/relative),sha)


if __name__=='__main__': unittest.main()

"""Update transaction: verification precedes writes, backups and rollback work."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import socket
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('notes_update',ROOT/'scripts/andrea/update_notes_quality.py')
updater=importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='update-tests-')
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.project=self.home/'Project'
        (self.project/'profiles').mkdir(parents=True)
        (self.project/'Avvia-OpenJarvis.command').write_text('marker')
        (self.project/'profiles/andrea-local.toml').write_text('marker')
        (self.project/'old.py').write_bytes(b'old content')
        (self.project/'.env').write_text('LOCAL_CONFIG_UNCHANGED')
        self.payload={'old.py':b'new content','new.py':b'new module'}
        sha=lambda content:hashlib.sha256(content).hexdigest()
        self.manifest=[{'path':'old.py','sha256':sha(self.payload['old.py']),'before':sha(b'old content')},{'path':'new.py','sha256':sha(self.payload['new.py']),'new':True}]

    def run_update(self,**kwargs):
        with redirect_stdout(io.StringIO()):
            return updater.update(self.project,self.manifest,kwargs.pop('fetch',lambda path,dest:dest.write_bytes(self.payload[path])),home=self.home,port=kwargs.pop('port',0),**kwargs)

    def test_success_backs_up_existing_files_and_does_not_touch_configuration(self):
        backup=self.run_update()
        self.assertEqual((backup/'old.py').read_bytes(),b'old content')
        self.assertEqual((self.project/'old.py').read_bytes(),b'new content')
        self.assertEqual((self.project/'new.py').read_bytes(),b'new module')
        self.assertEqual((self.project/'.env').read_text(),'LOCAL_CONFIG_UNCHANGED')

    def test_wrong_download_hash_or_modified_source_causes_no_source_writes(self):
        with self.assertRaises(ValueError):
            self.run_update(fetch=lambda path,dest:dest.write_bytes(b'wrong download'))
        self.assertEqual((self.project/'old.py').read_bytes(),b'old content')
        self.assertFalse((self.project/'new.py').exists())
        (self.project/'old.py').write_bytes(b'custom change')
        with self.assertRaises(ValueError):self.run_update()
        self.assertEqual((self.project/'old.py').read_bytes(),b'custom change')

    def test_apply_failure_rolls_back_prior_replacements(self):
        calls=0
        def fail_second(src,dest):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('synthetic disk error')
            os.replace(src,dest)
        with self.assertRaises(OSError):self.run_update(replace=fail_second)
        self.assertEqual((self.project/'old.py').read_bytes(),b'old content')
        self.assertFalse((self.project/'new.py').exists())

    def test_known_version_list_and_idempotent_repeat(self):
        allowed = [b'old content', b'known local optimization']
        self.manifest[0]['before'] = [hashlib.sha256(data).hexdigest() for data in allowed]
        for data in allowed:
            (self.project/'old.py').write_bytes(data)
            self.run_update()
            self.assertEqual((self.project/'old.py').read_bytes(), b'new content')
        self.run_update()
        (self.project/'old.py').write_bytes(b'unknown local modification')
        with self.assertRaises(ValueError):
            self.run_update()
        self.assertEqual((self.project/'old.py').read_bytes(), b'unknown local modification')

    def test_running_server_and_symlink_target_are_not_modified(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen()
            with self.assertRaises(ValueError):self.run_update(port=listener.getsockname()[1])
        (self.project/'new.py').symlink_to(self.project/'old.py')
        with self.assertRaises(ValueError):self.run_update()
        self.assertEqual((self.project/'old.py').read_bytes(),b'old content')

if __name__=='__main__':unittest.main()

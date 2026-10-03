"""Pinned, verified source update with backup and rollback for an existing install.

Run using the installed project's Python. No dependency, database or vault update.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

REVISION = '87d77ecd64a537433faa6ab26f1a7ce228ab9b97'
MANIFEST = [{"path":"scripts/andrea/runtime.py","sha256":"d6301e222a3d176d04e7a960b25d4102d0ca7e45013500e17b8fda950926753c","before":"0c87d03fcc70cba47d7e1cf71b78c856ba41ab03ef5e14f2c3506e0ce6ebd62f"},{"path":"scripts/andrea/measurements.py","sha256":"7519a8fc0326b6eae39a33d2033cbe1ca8a39b96170c1209a7580cba06155d43","new":True},{"path":"scripts/andrea/collaudo.py","sha256":"4e93d7360ffa60bfcab565406c0c7bae99f4811e7fa19318ca4d0316a2c274de","new":True},{"path":"scripts/andrea/quality_cases.json","sha256":"52a2a0dc558f493e6fb6fe3172fc0508669ce7b85f58d0c5c4d45d98dd6e413d","new":True},{"path":"tests/test_andrea_measurements.py","sha256":"9c3bff23451531cc8aea760d730ef59e74c26dfca97cb3f65c7d5cb27187e191","new":True},{"path":"tests/test_andrea_collaudo.py","sha256":"089fd1b53c3c39dde90ca16466541db058c7d8951ced3c1393830ee6b177d16e","new":True},{"path":"docs/andrea/README.md","sha256":"072d39dd2d166f74e8d0a9ac3adb70f1e5ebbd2536201895d153817ef34743c1","before":"0e1af6f487e0b84816e5b83a26b0be563f898addd974f42bc46fbae42b2b8ed0"}]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(relative, destination):
    url = f'https://raw.githubusercontent.com/saland78/Open-jarvis/{REVISION}/{relative}'
    subprocess.run(['curl', '--fail', '--show-error', '--location', '--proto', '=https', '--tlsv1.2', '--connect-timeout', '15', '--max-time', '60', url, '--output', str(destination)], check=True)


def update(target: Path, manifest=MANIFEST, fetch=download, *, home=None, port=8008, replace=os.replace):
    target = target.expanduser().resolve(strict=True)
    if not (target/'Avvia-OpenJarvis.command').is_file() or not (target/'profiles/andrea-local.toml').is_file():
        raise ValueError('Questa non è la cartella OpenJarvis installata. Nessun file modificato.')
    backup_root = (home or Path.home())/'.openjarvis-andrea/update-backups'
    if not manifest:
        raise ValueError('Manifest dell’aggiornamento non disponibile.')
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(('127.0.0.1', port))
            probe.listen(1)
        except OSError as exc:
            raise ValueError('OpenJarvis è ancora acceso o la porta 8008 è occupata. Ferma solo OpenJarvis con Control+C. Nessun processo è stato terminato.') from exc
        with tempfile.TemporaryDirectory(prefix='openjarvis-notes-update-') as staging:
            stage = Path(staging)
            print('Scaricamento e verifica dei file. Il progetto non viene ancora modificato.', flush=True)
            for item in manifest:
                relative = item['path']
                parts = Path(relative).parts
                if Path(relative).is_absolute() or '..' in parts or any(p.startswith('.') for p in parts):
                    raise ValueError('Percorso del manifest non valido.')
                file = target/relative
                if any((target/Path(*parts[:i])).is_symlink() for i in range(1,len(parts)+1)):
                    raise ValueError(f'Collegamento simbolico nel progetto: {relative}. Aggiornamento interrotto.')
                if file.exists() and not file.is_file():
                    raise ValueError(f'File non regolare: {relative}.')
                allowed = item.get('before')
                allowed = [allowed] if isinstance(allowed, str) else (allowed or [])
                if file.exists() and item.get('before') is not None and digest(file) not in {*allowed, item['sha256']}:
                    raise ValueError(f'Il file {relative} contiene modifiche diverse dalla versione prevista. Nessun file sovrascritto.')
                if file.exists() and item.get('new') and digest(file) != item['sha256']:
                    raise ValueError(f'È già presente un file diverso: {relative}. Nessun file sovrascritto.')
                staged = stage/relative
                staged.parent.mkdir(parents=True,exist_ok=True)
                fetch(relative,staged)
                if digest(staged) != item['sha256']:
                    raise ValueError(f'Verifica del download fallita: {relative}. Nessun file sovrascritto.')
            backup_root.mkdir(mode=0o700,parents=True,exist_ok=True)
            backup = Path(tempfile.mkdtemp(prefix=datetime.now().strftime('%Y%m%d-%H%M%S-'),dir=backup_root))
            existed = {}
            for item in manifest:
                relative = item['path']
                existed[relative] = (target/relative).exists()
                if existed[relative]:
                    saved = backup/relative
                    saved.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(target/relative,saved)
            (backup/'manifest.json').write_text(json.dumps({'revision':REVISION,'target':str(target),'existing':existed},indent=2))
            print(f'Backup creato: {backup}',flush=True)
            applied = []
            try:
                for item in manifest:
                    relative = item['path']
                    file = target/relative
                    file.parent.mkdir(parents=True,exist_ok=True)
                    fd,name = tempfile.mkstemp(prefix=file.name+'.',suffix='.update',dir=file.parent)
                    os.close(fd)
                    try:
                        shutil.copy2(stage/relative,name)
                        os.chmod(name,0o644)
                        replace(name,file)
                        applied.append(relative)
                    finally:
                        if os.path.exists(name): os.unlink(name)
            except BaseException:
                for relative in reversed(applied):
                    file = target/relative
                    if existed[relative]: shutil.copy2(backup/relative,file)
                    else: file.unlink(missing_ok=True)
                raise
            print(f'Aggiornamento completato: {len(manifest)} file. Backup: {backup}',flush=True)
            print('Nessuna nota, database, configurazione o dipendenza è stata modificata. Ora puoi avviare OpenJarvis.',flush=True)
            return backup


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project',type=Path,help='Cartella OpenJarvis esistente')
    args = parser.parse_args()
    try:
        update(args.project)
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print(f'Aggiornamento interrotto: {exc}',file=sys.stderr)
        sys.exit(1)


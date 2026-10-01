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

REVISION = '3a15c22f67e10171aab957bd1370b64415a73589'
MANIFEST = [{'path': 'scripts/andrea/runtime.py', 'sha256': '8f903cc7cf122747cdaaf94675590c0f71d187d87b51e919f13c47d8c5cfa3d1', 'before': 'fb36a96afbd81c51055fcd09f13ad3f3a7ff68e4a3d159ed7810d0dfd6c92123'}, {'path': 'scripts/andrea/launch.py', 'sha256': '39477abd8f14d4e22c292ca218030f1702a84f7b30e55049611ae0c90c448719', 'before': '9648d00c1db38fb688841a1482e77ae854800d84cd68aea779df3804660ef362'}, {'path': 'scripts/andrea/vault.py', 'sha256': '7bc99b8a8e58bfbe3ec11da76fde3e806c848cd0c014ee037546ea2c9979f292', 'new': True}, {'path': 'frontend/src/App.tsx', 'sha256': 'de649d88e49170fd55e4756d5aabb2cbe955f7fdf28acde928123ab146b69747', 'before': '0aeaa48cc47bbb8e52b500460fd885543924d193856d85449f1470b8d83dd6ef'}, {'path': 'frontend/src/lib/sse.ts', 'sha256': 'dbc3850035a26df0250a67ace10c4ebca810d2fad11bbdd40d2b186b4410f27b', 'before': 'c4b4ae340d2060a0a1a0439552d02856980bc01547782a9b93262d62785cacef'}, {'path': 'frontend/src/pages/AndreaNotesPage.tsx', 'sha256': 'e3b1a971c2286adbfc7921fb3fb945221f3386e89ce790bea51fc7519e974a20', 'new': True}, {'path': 'frontend/src/lib/andrea-local.test.ts', 'sha256': '6ac6765decb4ba5f1f3e1d449ae1d74b16aa905366bcdfadb465f946d95e7852'}, {'path': 'tests/test_andrea_vault.py', 'sha256': '759aed74ea2a43af1526c7e73508991145af5ce467fdffc30fed8c52c039a0c5', 'new': True}, {'path': 'tests/andrea_fixture_server.py', 'sha256': 'efea6c744986db60b3f8a969a76e7d3217734446a4c2733cc59b89fdaaa01cc8'}, {'path': 'docs/andrea/README.md', 'sha256': '5e5ecbb6c44f9a6be105b7b8fe01fdbed06d23bcef58affb170e5509818aab37'}]


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
                if file.exists() and item.get('before') is not None and digest(file) not in {item['before'], item['sha256']}:
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

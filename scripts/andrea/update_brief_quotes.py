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

REVISION = 'a07ae299d03fc8d8a8bedb85a8b313ca8cda5361'
MANIFEST = [{'path': 'scripts/andrea/brief.py', 'sha256': '99b5eb686029826a1f1838e96118f797f012f095c091323af1dd43806fb016a5', 'new': True}, {'path': 'scripts/andrea/runtime.py', 'sha256': '9ea8520768ee302934cf1a82440d1ff64d51becd4495464fef409872b1119d23', 'before': 'fb30f0b3f179b73cd8976e706653c898fa4da9bfe5739ba0706dfbdef2895ff3'}, {'path': 'scripts/andrea/collaudo.py', 'sha256': 'ebbd828888b1aaccf8a3846d4d242606f5327feccc136af91de757a425142fa4', 'before': 'b3341be8da1564a981ec766e1cfd8fb9bb8960bbfcd935a2cd96c6a495c224b9'}, {'path': 'scripts/andrea/brief_cases.json', 'sha256': '87979caa740b3b9227211d29a2b0012b6da2278299b1edb053baeda6ba34e384', 'new': True}, {'path': 'frontend/src/pages/AndreaNotesPage.tsx', 'sha256': '9b19719494aa119e78e330a8a7fb6d6bf364bdce66696fee620baa4f067f3b5e', 'before': 'd770a3275043fd3c590467b76659d1b9e3c42ba0d4c4f6348dac6bd30b5e6ef2'}, {'path': 'frontend/src/lib/sse.ts', 'sha256': 'd74690d5cbd7e68e97db6457a4f6f9a95e5c331d5d185575ba0fc03378a1e843', 'before': 'dbc3850035a26df0250a67ace10c4ebca810d2fad11bbdd40d2b186b4410f27b'}, {'path': 'tests/test_andrea_brief.py', 'sha256': '3b00cfde93f719d42852f950e1c1654cbeb53979247c6e180f27c868af2cf8d0', 'new': True}, {'path': 'tests/test_andrea_collaudo.py', 'sha256': '0288b72583894330d6faaae921eecd2959df523d131e2647439e92e91cb32b22', 'before': '2b73836150090e49e62cbf024730d0b8d7f9868c621ef9a7dd8f3d4617d74ce0'}, {'path': 'docs/andrea/brief-quotes-2026-10-02.md', 'sha256': '75f544a66fad8912ab59c4430b7c0a203818705c9d749faf57aca3db8872921b', 'new': True}]


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





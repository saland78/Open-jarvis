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

REVISION = '2a2e3ff6f671c08e172e5eafde1c2da709d0de11'
MANIFEST = [{'path': 'frontend/src/lib/andrea-browser-metrics.ts', 'sha256': '3bb62f2e2331bb2bf7aebf13735c4bcb23e1be4244c66b7f6954b2630366d511', 'new': True}, {'path': 'frontend/src/pages/AndreaResponseTimes.tsx', 'sha256': 'f197a7a120209b45ca800058887e47043d14a4a773046c99e499b6db1ab6f2bd', 'new': True}, {'path': 'frontend/src/pages/AndreaNotesPage.tsx', 'sha256': 'a765ad0f6f5565e690cf8d27ea45619bde36e5d34d6274b00350460930c59cd1', 'before': 'ff82378c73b7a26da48c0cf19df18ebc41a4c669422be994d1640aa8082cab16'}, {'path': 'frontend/src/lib/sse.ts', 'sha256': '158e6ef343f1b03470976363e02721cf2736f55458013b7e4d561fc75f6ec03b', 'before': 'd74690d5cbd7e68e97db6457a4f6f9a95e5c331d5d185575ba0fc03378a1e843'}, {'path': 'frontend/src/lib/andrea-browser-metrics.test.ts', 'sha256': 'c00e889acc477d575b01f0aee50c06f3a24a9d231c9297a72884a1f8501410a2', 'new': True}, {'path': 'frontend/src/lib/sse.observer.test.ts', 'sha256': '57364718b7e07afd7e55d17346e6b6f7ea1e074123a9a5ab6658c9f89e0edb3d', 'new': True}, {'path': 'frontend/src/pages/AndreaResponseTimes.test.tsx', 'sha256': 'b50e5af4781b6e65306955ef0601c4dfc0515d1713750e59d2a44cc59240d5fd', 'new': True}, {'path': 'frontend/src/pages/AndreaNotesPage.timings.test.tsx', 'sha256': 'e1af1f5e698338dd25cff63e6f7766750a5992d02101829ec9bf19b387e2dda1', 'new': True}, {'path': 'docs/andrea/browser-note-timings-2026-10-02.md', 'sha256': '797348dc17d4c5477e5c49f8ff7e1ee67ef7bd16d1fbbf3cc4cd29e2eb79d595', 'new': True}]


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





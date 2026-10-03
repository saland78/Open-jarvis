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

REVISION = 'c0f1c90232b672d99d71374724fb562845bb77e2'
MANIFEST = [{'path': 'frontend/src/components/Chat/InputArea.tsx', 'sha256': '7bb2d293941ce8cadb86689bf00a06f4fab8618992682ee365ae37e5f0156696', 'before': '23b63cb7e490f3f946f865a0d4f600c38bb4a0161212d19091d746801d6e1fe8'}, {'path': 'frontend/src/components/Chat/MessageBubble.tsx', 'sha256': 'dbf8fa5e63113e7cb7a95649ced79acd09833e5192a4ffed5e518048979a27da', 'before': '91619da2ff0fd3319d7e8761f389f2e07eb1e8da36036d63cc91e001e4f32a5f'}, {'path': 'frontend/src/components/Chat/ChatArea.tsx', 'sha256': '37517df4d853d928311eed110cd170a19abc40910b9f96959f6658e8cc0c6978', 'before': 'e2cf9b77f5bd4fcc303149c8b17eebd753b91db445cb7de0df73091bfb645830'}, {'path': 'frontend/src/pages/AndreaResponseTimes.tsx', 'sha256': '13850b8583b65f5b2e08dbe7557c0da286befb6d6afdf27f2d88068fcef4f825', 'before': 'f197a7a120209b45ca800058887e47043d14a4a773046c99e499b6db1ab6f2bd'}, {'path': 'frontend/src/pages/AndreaResponseTimes.test.tsx', 'sha256': '146624cf09a747108f40d2fc2d82b22805012b520db9a90a7444593f1f820e57', 'before': 'b50e5af4781b6e65306955ef0601c4dfc0515d1713750e59d2a44cc59240d5fd'}, {'path': 'frontend/src/lib/andrea-chat-metrics.ts', 'sha256': '3e04e0c0df1d7816127ccd872f68dea844333a11a7f7b9a1c42d06932199ab7c', 'new': True}, {'path': 'frontend/src/lib/andrea-chat-metrics.test.ts', 'sha256': '7ed58f92d079bcdbb3ec999e72ea98a45b3b6ead238c02fedad887718fd89b29', 'new': True}, {'path': 'frontend/src/components/Chat/AndreaChatTimes.tsx', 'sha256': '72106e1e3a14b9e355d64a39bdb8920ecbfe5fbff221b3baf4e731b97ae230b6', 'new': True}, {'path': 'frontend/src/components/Chat/InputArea.timings.test.tsx', 'sha256': 'ddb8ebce41fafe3d457d2bdf18fd33e7160346ecf0cdae774b716dfd3ec84503', 'new': True}, {'path': 'docs/andrea/browser-chat-timings-2026-10-02.md', 'sha256': '4e4b60b1a64f6ff9c4bf4c6915a4f48aab40d11e1e8eaa469aa1fd3e89ad5fc4', 'new': True}]


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





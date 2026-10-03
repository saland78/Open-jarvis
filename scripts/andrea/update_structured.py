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

REVISION = 'f9555f0b76428e9ba424cada882b35a827fbedcf'
MANIFEST = [{'path': 'scripts/andrea/runtime.py', 'sha256': 'eb266cd8841667c60e681d9a69971bb2344001259e8c93a3a8f7cba98053e1fb', 'before': 'f47e5094a0a884ea6d250e99a5643403d4ecd332560abcd3a3af05cd0340c8b9'}, {'path': 'src/openjarvis/engine/ollama.py', 'sha256': '52383316a021115be526c68fd47f005e39bc4508600d253c801c0121a2f4160b', 'before': '0c6278639e0b27b23a15a40725818dbdef201ba1eb04b80c8345e87b3211d511'}, {'path': 'scripts/andrea/synthesis_contract.py', 'sha256': '8ef660031e2cbb799ed2086c1864808e7ebe7f6f1e4155b14a0493f7204ecaa4', 'new': True}, {'path': 'scripts/andrea/structured_stream.py', 'sha256': 'b7d87dc3a3a70694c41e1e08313cfbc11d481770e22d43a5ddf4ecd3ff255a0c', 'new': True}, {'path': 'scripts/andrea/check_structured.py', 'sha256': 'd2c54eafbb953fb57535354461054008741d978942b3e483d3defa63cd92a651', 'new': True}, {'path': 'scripts/andrea/structured_cases.json', 'sha256': 'c1113ace4a06d99a241920f8196f75de5795fccc6c3b0da8cfb86ca947cbaa41', 'new': True}, {'path': 'frontend/src/lib/sse.ts', 'sha256': '1028c4e626d989672654ef96eb21d357ee0877daf872246f166a3dea145c8866', 'before': '158e6ef343f1b03470976363e02721cf2736f55458013b7e4d561fc75f6ec03b'}, {'path': 'frontend/src/lib/andrea-browser-metrics.ts', 'sha256': '004701ce94901b50f72eb6e27cd6c81ab7068e93e82cc6338e58d841a2b23d5b', 'before': '3bb62f2e2331bb2bf7aebf13735c4bcb23e1be4244c66b7f6954b2630366d511'}, {'path': 'frontend/src/pages/AndreaNotesPage.tsx', 'sha256': 'b3d180147b70f06e8d2980dad55a69e3fbea250b0b8e58d3b309816ce952716c', 'before': 'a765ad0f6f5565e690cf8d27ea45619bde36e5d34d6274b00350460930c59cd1'}, {'path': 'frontend/src/pages/AndreaResponseTimes.tsx', 'sha256': 'dd56fd3ef9dd91fe54e2d89965addb3db36059a8967b908b5895c8bc92920cf9', 'before': '13850b8583b65f5b2e08dbe7557c0da286befb6d6afdf27f2d88068fcef4f825'}]


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





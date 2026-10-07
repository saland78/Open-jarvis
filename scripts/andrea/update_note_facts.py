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

REVISION = 'c1bbac6dc7ebe1742e293bea0864734ef2ec1056'
MANIFEST = [{'path': 'scripts/andrea/runtime.py', 'sha256': 'fc91fc88d7c19a602c4ab924736f0523f6e091f08ce29dccfc725f8186443a0a', 'before': 'eb266cd8841667c60e681d9a69971bb2344001259e8c93a3a8f7cba98053e1fb'}, {'path': 'scripts/andrea/structured_stream.py', 'sha256': '52e527c183eda6c369fb53bc5e19ca7f0682151cc1a981c66d47f37cc25a01ff', 'before': '8a862a3ac5fd1d2d16f609c5e8ab8b16d30d2de38812b8dff2e539ba80c7200d'}, {'path': 'src/openjarvis/engine/ollama.py', 'sha256': '881c5e2f667d31a4a62d0e726fa179a4819ecab2b7f960d513871e6a0fb529f0', 'before': '52383316a021115be526c68fd47f005e39bc4508600d253c801c0121a2f4160b'}, {'path': 'frontend/src/pages/AndreaNotesPage.tsx', 'sha256': '579a6218566a03737527c8c330b8cd29e653e088da0627ce92e805029132dc55', 'before': 'b3d180147b70f06e8d2980dad55a69e3fbea250b0b8e58d3b309816ce952716c'}, {'path': 'scripts/andrea/markdown_fact_adapter.py', 'sha256': 'a9793b116b255a78c4af61f88dabf11b8a66ba0299ea9ef3116d25fed2a090a1', 'new': True}, {'path': 'scripts/andrea/predicate_context_synthesis.py', 'sha256': '65c4af9db2024b6ace064b1ffe0d764e658f67683709c3e0b0acb8bef829951e', 'new': True}, {'path': 'scripts/andrea/note_facts.py', 'sha256': '2a20aa5e2310228a28f3c2313239c1f4e1d6419dabaab65b8e3ea2503f58bda7', 'new': True}]


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
            originals = {}
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
                if not file.exists() and item.get('before') is not None:
                    raise ValueError(f'File previsto mancante: {relative}. Nessun file modificato.')
                originals[relative] = digest(file) if file.exists() else None
                staged = stage/relative
                staged.parent.mkdir(parents=True,exist_ok=True)
                fetch(relative,staged)
                if digest(staged) != item['sha256']:
                    raise ValueError(f'Verifica del download fallita: {relative}. Nessun file sovrascritto.')
                if relative.endswith('.py'):
                    try:
                        compile(staged.read_bytes(), relative, 'exec')
                    except (SyntaxError, ValueError) as exc:
                        raise ValueError(f'Sintassi Python non valida: {relative}. Nessun file modificato.') from exc
            for relative, expected in originals.items():
                file = target/relative
                if file.is_symlink() or (digest(file) if file.exists() else None) != expected:
                    raise ValueError(f'File cambiato durante il download: {relative}. Nessun file sovrascritto.')
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





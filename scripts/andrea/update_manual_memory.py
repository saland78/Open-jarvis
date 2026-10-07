"""Pinned explicit memory module update with backup and rollback.

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

REVISION = '07c8ce93b0e4c5d486b7a24b26c4763e77b1ae4e'
MANIFEST = [{'path': 'scripts/andrea/runtime.py', 'sha256': '7cabb75a5e22bce37455b9dda7b52b8ae2baec12500c69f3a6c1261d80b4e878', 'before': '0d2fe27f13ef8b61a6b641d0969d1a82c768cef16df28c84b003cda5a0973661'}, {'path': 'scripts/andrea/manual_memory.py', 'sha256': '1d21caab261f23c882cccca13a4b0f51a23a46e22c9e57af1eff0cd8d96c7647', 'new': True}, {'path': 'frontend/src/App.tsx', 'sha256': '92d6e9e3cdff78b33fe36923653009dab7191aa56787911d21b174fba4357336', 'before': 'de649d88e49170fd55e4756d5aabb2cbe955f7fdf28acde928123ab146b69747'}, {'path': 'frontend/src/components/Sidebar/Sidebar.tsx', 'sha256': 'b085da37ec9554c4ca7d52a3ee19bc922be8e4ea8e6ec6a5046a5fb357fcebf6', 'before': 'f4871004311825cc6dc3a4ff120c4667cde840d13089a1dd14c51abe997f357a'}, {'path': 'frontend/src/pages/AndreaMemoryPage.tsx', 'sha256': '06192206b53276770bc50fe267e77564e5c44fa62f0d98927a34a6381aa6164d', 'new': True}]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

CHECKS = {'scripts/andrea/runtime.py': '0d2fe27f13ef8b61a6b641d0969d1a82c768cef16df28c84b003cda5a0973661', 'scripts/andrea/vault.py': '3dd17ba664504f12ee02e72962ff6358db1be5d56b085ff755ff8f93971a78bd', 'scripts/andrea/markdown_fact_adapter.py': 'a9793b116b255a78c4af61f88dabf11b8a66ba0299ea9ef3116d25fed2a090a1', 'scripts/andrea/predicate_context_synthesis.py': '65c4af9db2024b6ace064b1ffe0d764e658f67683709c3e0b0acb8bef829951e', 'scripts/andrea/synthesis_contract.py': '2ef7d64b1fd6b737d45398b9cc5ae46aac28617c4059348b3ba333f3f3cea80d', 'scripts/andrea/structured_stream.py': '52e527c183eda6c369fb53bc5e19ca7f0682151cc1a981c66d47f37cc25a01ff', 'src/openjarvis/engine/ollama.py': 'e4227f50c4d7f9c0bd90be88dbbc523bd8a01f1012c7f3e7f326ec720c7825b8', 'scripts/andrea/qualification_prompt.py': 'a4f1f0f0968af14855c0a963b8691965d005c99a0f4e2c05564f437ec543a868', 'scripts/andrea/qualification_clause_guard.py': 'ad01e5192b19fc4bad068a0cdc288d9889fa0166eb2db6720283887910559757', 'scripts/andrea/qualification_sentence_guard.py': '976e22ad3ba6671011cc63c0d18ae21a39e4647d4ad698454b70db983b943866', 'frontend/src/pages/AndreaNotesPage.tsx': '5ece8d59a03a870cce6bce7cded885aa6a8d5b3db755389fbb1518b11fedc43c', 'scripts/andrea/note_facts.py': 'e259adc3b46112a9516b3f41bd8dc1628a5676fcfff051cb1ba0ae343d6bdbe8', 'scripts/andrea/read_native_phases.py': 'c57a028c2062c0e3dfaf6b3a182eb16c049ab5db64a353f6f215fe127adb6670'}

def verify_baseline(target):
    for relative, expected in CHECKS.items():
        allowed = {expected}
        allowed.update(item['sha256'] for item in MANIFEST if item['path'] == relative)
        parts = Path(relative).parts
        file = target/relative
        if (any((target/Path(*parts[:i])).is_symlink() for i in range(1, len(parts)+1))
                or not file.is_file() or digest(file) not in allowed):
            raise ValueError(f'Componente diverso dalla versione verificata: {relative}. Nessun file modificato.')



def download(relative, destination):
    url = f'https://raw.githubusercontent.com/saland78/Open-jarvis/{REVISION}/{relative}'
    subprocess.run(['curl', '--fail', '--show-error', '--location', '--proto', '=https', '--tlsv1.2', '--connect-timeout', '15', '--max-time', '60', url, '--output', str(destination)], check=True)


def preflight(target, manifest):
    """Check every destination before issuing the first download."""
    for item in manifest:
        relative = item['path']
        parts = Path(relative).parts
        if Path(relative).is_absolute() or '..' in parts or any(p.startswith('.') for p in parts):
            raise ValueError('Percorso del manifest non valido.')
        file = target/relative
        if any((target/Path(*parts[:i])).is_symlink() for i in range(1, len(parts)+1)):
            raise ValueError(f'Collegamento simbolico nel progetto: {relative}.')
        if file.exists() and not file.is_file():
            raise ValueError(f'File non regolare: {relative}.')
        before = item.get('before')
        allowed = [before] if isinstance(before, str) else (before or [])
        if file.exists() and before is not None and digest(file) not in {*allowed, item['sha256']}:
            raise ValueError(f'Modifiche locali incompatibili: {relative}. Nessun file sovrascritto.')
        if file.exists() and item.get('new') and digest(file) != item['sha256']:
            raise ValueError(f'File nuovo già presente con contenuto diverso: {relative}.')
        if not file.exists() and before is not None:
            raise ValueError(f'File previsto mancante: {relative}.')


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
        verify_baseline(target)
        preflight(target, manifest)
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
            verify_baseline(target)
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




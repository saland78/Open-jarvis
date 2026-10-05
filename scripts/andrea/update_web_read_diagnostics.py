"""Pinned two-file page-reading diagnostics update with backup and atomic replacement.

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

REVISION = '2dd3fbf9a8ef7a1627ac6baa047030332bc3285b'
MANIFEST = [{'path': 'scripts/andrea/web_page_fetch.py', 'before': 'cc59a60284e6cf8e15486b0ccd62af15815685e952373d6a0f7340bdb31dd837', 'sha256': 'e93b91e964ab04a4344218600aba248dd421683767fd47d410ac4aa4183d54b6'}, {'path': 'scripts/andrea/web_page_local.py', 'before': '420d3bbdc2f27b34d9ed0ad13cfefc36ed0a6e0ea84665d8a3f0c17ecd1ca2bb', 'sha256': '06f58558d8a234e3974e3cb7cc0621d7ee1b1bbce0d339c9380b188cb7aa4706'}]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

CHECKS = {'scripts/andrea/runtime.py': '395271608f3f6678017064afcb7dc4ac2272f3d75bc249cddbfc240a861bb172', 'scripts/andrea/vault.py': '3dd17ba664504f12ee02e72962ff6358db1be5d56b085ff755ff8f93971a78bd', 'scripts/andrea/markdown_fact_adapter.py': 'a9793b116b255a78c4af61f88dabf11b8a66ba0299ea9ef3116d25fed2a090a1', 'scripts/andrea/predicate_context_synthesis.py': '65c4af9db2024b6ace064b1ffe0d764e658f67683709c3e0b0acb8bef829951e', 'scripts/andrea/synthesis_contract.py': '2ef7d64b1fd6b737d45398b9cc5ae46aac28617c4059348b3ba333f3f3cea80d', 'scripts/andrea/structured_stream.py': '52e527c183eda6c369fb53bc5e19ca7f0682151cc1a981c66d47f37cc25a01ff', 'src/openjarvis/engine/ollama.py': 'e4227f50c4d7f9c0bd90be88dbbc523bd8a01f1012c7f3e7f326ec720c7825b8', 'scripts/andrea/qualification_prompt.py': 'a4f1f0f0968af14855c0a963b8691965d005c99a0f4e2c05564f437ec543a868', 'scripts/andrea/qualification_clause_guard.py': 'ad01e5192b19fc4bad068a0cdc288d9889fa0166eb2db6720283887910559757', 'scripts/andrea/qualification_sentence_guard.py': '976e22ad3ba6671011cc63c0d18ae21a39e4647d4ad698454b70db983b943866', 'frontend/src/pages/AndreaNotesPage.tsx': '5ece8d59a03a870cce6bce7cded885aa6a8d5b3db755389fbb1518b11fedc43c', 'scripts/andrea/note_facts.py': 'e259adc3b46112a9516b3f41bd8dc1628a5676fcfff051cb1ba0ae343d6bdbe8', 'scripts/andrea/read_native_phases.py': 'c57a028c2062c0e3dfaf6b3a182eb16c049ab5db64a353f6f215fe127adb6670', 'scripts/andrea/manual_memory.py': '5b23b36c6eb0f2fbe517cc03eb9d2779ff818f66633d13db83a7c31baec4f9d1', 'scripts/andrea/collaudo.py': 'ebbd828888b1aaccf8a3846d4d242606f5327feccc136af91de757a425142fa4', 'scripts/andrea/memory_provenance.py': '6ec82a17f9dee9a83dc0804d01c54a504b38fff163d9745d3fe21e913f309ee5', 'frontend/src/App.tsx': 'aca5ea90741873d5c9acaf84e3d101041e4668f4921547f236908f1a1d42b3da', 'frontend/src/components/Sidebar/Sidebar.tsx': '43db477b234c73a90a6a7b12762e2a320207403e0eb6d6b7af09422fd74c9906', 'frontend/src/pages/AndreaWebPage.tsx': 'faa5a956fac03a85c2a1f3063c7404130d25e96b6bfdec84a1716026535f99da', 'scripts/andrea/web_search_local.py': '8cd2e6a9e700c73015f75006d47ed0a060dba8c74f28b5214d43f8d77d92d1a1', 'scripts/andrea/web_provider_probe.py': '5464884a2115642c16ef3f1f8e70d1c9afd1201dee170b9ad13e1a602342eb92', 'scripts/andrea/duckduckgo_provider_probe.py': 'b5867eba700895327fe6993fddf7c3b61f3d0d236e47420ffb1180c9b0eb4aba', 'scripts/andrea/web_page_fetch.py': 'cc59a60284e6cf8e15486b0ccd62af15815685e952373d6a0f7340bdb31dd837', 'scripts/andrea/web_page_local.py': '420d3bbdc2f27b34d9ed0ad13cfefc36ed0a6e0ea84665d8a3f0c17ecd1ca2bb', 'scripts/andrea/native_metrics.py': '0c01d24922baeaec2db570c8225eaa3bc031f11a8d1feacd9019f885ff731e1a', 'scripts/andrea/web_sentence_contract.py': 'b41d11412c12a3370b290388564b9353c74a5db12fa0c8dce006469c4778357a'}

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




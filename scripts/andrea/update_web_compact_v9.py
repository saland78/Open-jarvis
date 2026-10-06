"""Pinned compact-v9 integration update with backup and atomic replacement.

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

REVISION = 'b0cf9a636ab4a198096d86ea3fba18ef9e0c85b0'
MANIFEST = [{'path': 'scripts/andrea/web_networking_scope.py', 'sha256': '89c520a842da155daaf77c90dbfb4fbca4999b2a77dd14c9f78ef305d9f0467f', 'new': True}, {'path': 'scripts/andrea/web_native_identifier_schema.py', 'sha256': '0d18ccd5dfaed159b5e7d81522441bb098a56806a43c465ffff2a2f7089181af', 'new': True}, {'path': 'scripts/andrea/web_native_identifier_prefix.py', 'sha256': 'b4161128a6de05f6001eecaab5779c0b6f245407f26eaa35c93d8604daa08fb0', 'new': True}, {'path': 'scripts/andrea/web_source_label_scope.py', 'sha256': '933719fe18b883528dafd0f134d42d15629ec4504b52a0e04bbf511c67e5363b', 'new': True}, {'path': 'scripts/andrea/web_capability_evidence.py', 'sha256': 'becb32b3303e11ed948c64053d3d4164daaccdfaa848a58545922874b3f92eef', 'new': True}, {'path': 'scripts/andrea/web_source_performance_scope.py', 'sha256': '24596c0fb49d9186ffc212607b52dda3e6ec772db22b3d682b1e571cb412ea59', 'new': True}, {'path': 'scripts/andrea/web_question_focus.py', 'sha256': 'e5b31aa66ec4b6892147b97ba683ff2c3f7d29a04b50915f4ccd962170a2d7d6', 'new': True}, {'path': 'scripts/andrea/web_operation_predicate_scope.py', 'sha256': '48b0c3fbe673fdd57b4a07878c48a45177518ebf47dd919770fea8d676067721', 'new': True}, {'path': 'scripts/andrea/web_native_operation_verb.py', 'sha256': '293f6b141d1759d1c033c7fff5b22417fd6bf17a225529c5abd52f8e07e8e685', 'new': True}, {'path': 'scripts/andrea/web_candidate_pipeline.py', 'sha256': 'aee11a0ea16fdef06e53f3a280080507b9c202e2b044a54adde15c4bcf043322', 'new': True}, {'path': 'scripts/andrea/web_page_context_contract.py', 'sha256': '449fc775485d52095c9830a482d75df96044732aa110cc2671f93eb1eed97f31', 'before': 'a7fa689865126891912e5f9c280ef9afc8b68771770ee5b7902cc46eac7b02e1'}, {'path': 'scripts/andrea/check_web_compact_v9.py', 'sha256': 'b9508c930f086506976d723bbe87a7c789354444e0d969396853b8208ed60c21', 'new': True}]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

CHECKS = {'scripts/andrea/runtime.py': '395271608f3f6678017064afcb7dc4ac2272f3d75bc249cddbfc240a861bb172', 'scripts/andrea/web_page_fetch.py': '2168186c522d1ee07e805f3f20b5d7aa747aef46847a460b1b8c65050efcdfdc', 'scripts/andrea/web_page_local.py': '34fdf49278d857a29a01e9260d0577d7e46cd0b59cd2e40f8af2e3770c862e50', 'scripts/andrea/web_sentence_contract.py': '5b8a73b2a9d534074ec61eb67b9abd0eb6c73d3abb2783e76149ad6b3b7b2285', 'scripts/andrea/web_page_fidelity.py': 'cda722628976e8c910bc12341abebc7a6f0731f606e7e70645fc4b09936f7cae', 'scripts/andrea/web_page_context_contract.py': 'a7fa689865126891912e5f9c280ef9afc8b68771770ee5b7902cc46eac7b02e1', 'scripts/andrea/web_page_context_fetch.py': '8ababe9d94bec292dfe0dacbcaa4c4030aa839f6987ff887e693768d820b418d', 'scripts/andrea/web_definition_context.py': 'cea7127788650cacefd59b36bfd860a5525deef1c3ebd5372ab9f76acfcd55d4', 'scripts/andrea/web_single_rule_budget.py': 'c1f669cc14745e15babddec1572b0f86c59e883a07fcb567eb72cf2bf5389f57', 'scripts/andrea/web_heading_evidence.py': 'de4d874053d492e79b305206ad7fe26c8f0aa6f231ba39aaccc5c0988f5da91e', 'src/openjarvis/engine/ollama.py': 'e4227f50c4d7f9c0bd90be88dbbc523bd8a01f1012c7f3e7f326ec720c7825b8', 'frontend/src/pages/AndreaWebPage.tsx': '38ca476f4d58bb9803e1dc910d1ebd6aa387fe6e23405087ddb011656ba0149b', 'scripts/andrea/native_metrics.py': '0c01d24922baeaec2db570c8225eaa3bc031f11a8d1feacd9019f885ff731e1a', 'scripts/andrea/web_search_local.py': '8cd2e6a9e700c73015f75006d47ed0a060dba8c74f28b5214d43f8d77d92d1a1'}

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


def validate_staged_modules(stage, target):
    # Import only the pinned web modules in a short-lived isolated interpreter.
    # No server, model, network request, user configuration or notes are opened.
    code = ('import sys; sys.path[:0] = sys.argv[1:3]; '
            'import web_page_context_fetch, web_page_context_contract, web_page_local; '
            'assert web_page_context_contract.CONTRACT_REVISION == '
            '"compact_web_evidence_v9"')
    result = subprocess.run([sys.executable, '-I', '-B', '-c', code,
                             str(stage/'scripts/andrea'), str(target/'scripts/andrea')],
                            capture_output=True, timeout=10)
    if result.returncode:
        raise ValueError('Importazione dei moduli verificati non riuscita. Nessun file modificato.')


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
            preflight(target, manifest)
            validate_staged_modules(stage, target)
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



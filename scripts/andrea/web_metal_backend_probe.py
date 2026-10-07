"""One isolated Intel Mac Metal trial against the installed v9 CPU backend.

Builds or verifies an existing pinned llama.cpp checkout with Metal enabled. Reuses the
existing verified Ollama GGUF; downloads no new weights. A single GPU check or
six fixed comparison requests keep v9 evidence, messages, schema and validators. No answer repair,
retry, production installation or termination of pre-existing processes.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
OLLAMA = 'http://127.0.0.1:11434'
APP = 'http://127.0.0.1:8008'
VERSION = '0.35.1'
MAX_BYTES = 65536
WORKER_SECONDS = 95
EXPECTED_CHECKER = 'b9508c930f086506976d723bbe87a7c789354444e0d969396853b8208ed60c21'
CONTROL_FORMS = r'\b(?:control|controls|controlling|controll\w*)\b'
LLAMA_REPOSITORY = 'https://github.com/ggml-org/llama.cpp.git'
LLAMA_COMMIT = '4d756bc72bf00a4aacf410ae15a2d315f3db400d'
LLAMA_TREE = '52c0e5f1f920046632632b594b7263ad1b7706cd'
LLAMA_BUILD = 11461
GPU_NAME = 'AMD Radeon Pro 5500M'
ORDER = ((0, 'ollama_cpu'), (0, 'llama_metal'), (1, 'llama_metal'),
         (1, 'ollama_cpu'), (2, 'ollama_cpu'), (2, 'llama_metal'))
MIN_TOTAL_GAIN_PERCENT = 20
MAX_TOTAL_REGRESSION_PERCENT = 5
MAX_CACHED_TOKENS = 8
MODEL_MAX_BYTES = 6 * 1024**3
LOG_MAX_BYTES = 16 * 1024**2
GPU_CHECK_UBATCH = 64
GPU_CHECK_ENV = {'GGML_METAL_CONCURRENCY_DISABLE': '1',
                 'GGML_METAL_GRAPH_OPTIMIZE_DISABLE': '1',
                 'GGML_METAL_FUSION_DISABLE': '1'}

def control_audit(checked, selection):
    if checked['outcome'] != 'accepted_pending_semantic_review':
        return checked
    if not selection['sourceCapabilityScopePolicy']['active']:
        return checked
    for number, claim in enumerate(checked['claims'], 1):
        if re.search(CONTROL_FORMS, claim['text'], re.I) and not re.search(CONTROL_FORMS, claim['quote'], re.I):
            return {'outcome': 'rejected', 'reason': 'control_not_in_own_operation_passage',
                    'claims': [], 'details': {'claimIndex': number, **copy.deepcopy(claim),
                                            'diagnosticOnly': True}}
    return checked

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':')).encode()).hexdigest()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('unexpected_redirect')

def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

def load_project(project):
    file = project / 'scripts/andrea/check_web_compact_v9.py'
    parts = ('scripts', 'andrea', 'check_web_compact_v9.py')
    if (any(project.joinpath(*parts[:i]).is_symlink() for i in range(1, 4))
            or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != EXPECTED_CHECKER):
        raise ValueError('installed_v9_checker_changed')
    spec = importlib.util.spec_from_file_location('_verified_batch_check', file)
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    check.verify_project(project)
    sys.path.insert(0, str(project / 'scripts/andrea'))
    import web_candidate_pipeline as pipeline
    if pipeline.CONTRACT_REVISION != 'compact_web_evidence_v9':
        raise ValueError('unexpected_contract_revision')
    return check, pipeline

def isolated_messages(messages, marker):
    if not re.fullmatch('[0-9a-f]{32}', marker):
        raise ValueError('invalid_cache_marker')
    result = copy.deepcopy(messages)
    if len(result) != 2 or [item['role'] for item in result] != ['system', 'user']:
        raise ValueError('unexpected_roles')
    result[0]['content'] = marker + '\nDiagnostic cache marker only; not source evidence.\n' + result[0]['content']
    return result

def thermal_sample():
    """Only numerical reported CPU limits; no process list or temperature guess."""
    started = time.monotonic()
    try:
        value = subprocess.run(['/usr/bin/pmset', '-g', 'therm'],
            capture_output=True, timeout=1.5, check=False)
        if value.returncode != 0 or len(value.stdout) > 16384:
            raise ValueError()
        text = value.stdout.decode('utf-8', errors='replace')
        limits = {}
        for key in ('CPU_Speed_Limit', 'CPU_Scheduler_Limit', 'CPU_Available_CPUs'):
            match = re.search(r'\b' + key + r'\s*=\s*(\d+)\b', text)
            limits[key] = int(match.group(1)) if match else None
        return {'reportedLimits': limits, 'available': any(v is not None for v in limits.values()),
                'readMs': round((time.monotonic() - started) * 1000, 3)}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {'reportedLimits': None, 'available': False,
                'readMs': round((time.monotonic() - started) * 1000, 3)}

def cpu_residency():
    # Post-request metadata, not a load, inference or configuration operation.
    try:
        with opener().open(OLLAMA + '/api/ps', timeout=4) as response:
            raw = response.read(MAX_BYTES + 1)
            if response.status != 200 or len(raw) > MAX_BYTES:
                raise ValueError()
            data = json.loads(raw, object_pairs_hook=unique_pairs)
        models = data.get('models') if isinstance(data, dict) else None
        if (not isinstance(models, list) or len(models) != 1 or not isinstance(models[0], dict)
                or models[0].get('name') != MODEL or type(models[0].get('size_vram')) is not int):
            raise ValueError()
        return {'expectedModelLoaded': True, 'sizeVram': models[0]['size_vram'],
                'phase': 'after_request_not_effective_batch_confirmation'}
    except (OSError, ValueError, TypeError):
        return {'expectedModelLoaded': None, 'sizeVram': None,
                'phase': 'after_request_not_effective_batch_confirmation'}

class Observer:
    def __init__(self):
        self.stop = threading.Event()
        self.rows = []
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        for delay in (6, 18, 36):
            if self.stop.wait(max(0, self.started + delay - time.monotonic())):
                return
            row = thermal_sample()
            row['scheduledWorkerOffsetSeconds'] = delay
            row['nativePrefillPhaseProven'] = False
            self.rows.append(row)

    def start(self):
        self.thread.start()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)
        return not self.thread.is_alive()

def owned_worker(project, payload, timeout, observe=False):
    encoded = json.dumps(payload, ensure_ascii=False).encode()
    if len(encoded) > MAX_BYTES:
        raise ValueError('worker_input_too_large')
    child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), str(project), '--worker'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    observer = Observer() if observe else None
    cleaned = True
    try:
        if observer:
            observer.start()
        output, error = child.communicate(encoded, timeout=timeout)
        if len(output) > MAX_BYTES:
            raise ValueError('owned_worker_output_oversized')
        if child.returncode != 0:
            # A short exception code explains a failure without dumping input,
            # source text, model answers or the ephemeral server credential.
            diagnostic = error.decode('utf-8', errors='replace')
            match = re.search(r'Prova fermata: ([a-z0-9_]+)\.', diagnostic)
            raise ValueError(match[1] if match else 'owned_worker_failed')
        value = json.loads(output, object_pairs_hook=unique_pairs)
        if not isinstance(value, dict):
            raise ValueError('owned_worker_invalid')
    except subprocess.TimeoutExpired:
        raise ValueError('owned_worker_deadline_no_retry') from None
    finally:
        if child.poll() is None:
            child.kill()  # Only this probe's child; never the Ollama/Jarvis process.
            child.communicate(timeout=2)
        if observer:
            cleaned = observer.close()
    return value, list(observer.rows) if observer else [], cleaned


def json_request(url, payload=None, timeout=4, token=None, transport=None):
    headers = {'Content-Type': 'application/json'}
    if token is not None:
        if not re.fullmatch('[0-9a-f]{64}', token):
            raise ValueError('invalid_local_server_token')
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(url, headers=headers,
        data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode())
    with (transport or opener()).open(request, timeout=timeout) as response:
        raw = response.read(MAX_BYTES + 1)
        if response.status != 200 or len(raw) > MAX_BYTES:
            raise ValueError('invalid_local_json_response')
        value = json.loads(raw, object_pairs_hook=unique_pairs)
    if not isinstance(value, dict) or value.get('error'):
        raise ValueError('invalid_local_json_object')
    return value


def model_identity(show):
    """Only a declared, ordinary, content-addressed local GGUF is eligible."""
    details = show.get('details', {})
    if (not isinstance(details, dict) or details.get('format') != 'gguf'
            or details.get('family') != 'qwen3' or details.get('quantization_level') != 'Q4_K_M'
            or not str(details.get('parameter_size', '')).startswith('4.')):
        raise ValueError('unexpected_ollama_weights')
    text = show.get('modelfile')
    template = show.get('template')
    if not isinstance(text, str) or not isinstance(template, str) or not template:
        raise ValueError('missing_ollama_model_metadata')
    declarations = [line.strip()[5:] for line in text.splitlines()
                    if line.strip().startswith('FROM ')]
    if len(declarations) != 1:
        raise ValueError('unexpected_model_from_declaration')
    values = shlex.split(declarations[0])
    if len(values) != 1:
        raise ValueError('invalid_model_from_path')
    file = Path(values[0])
    match = re.fullmatch('sha256-([0-9a-f]{64})', file.name)
    if (not file.is_absolute() or not match or file.is_symlink() or not file.is_file()
            or file.parent.name != 'blobs' or not 1024 <= file.stat().st_size <= MODEL_MAX_BYTES):
        raise ValueError('model_is_not_an_existing_gguf_blob')
    # Resolve for sharing this same file with the owned engine, not to copy it.
    file = file.resolve(strict=True)
    with file.open('rb') as handle:
        if handle.read(4) != b'GGUF':
            raise ValueError('model_blob_is_not_gguf')
    return {'path': str(file), 'sha256': match.group(1), 'bytes': file.stat().st_size,
            'ollamaTemplateSha256': hashlib.sha256(template.encode()).hexdigest(),
            'ollamaParametersSha256': digest(show.get('parameters'))}


def file_signature(file):
    stat = file.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def verify_weights(identity):
    file = Path(identity['path'])
    before = file_signature(file)
    sha = hashlib.sha256()
    with file.open('rb') as handle:
        while block := handle.read(4 * 1024**2):
            sha.update(block)
    after = file_signature(file)
    if before != after or sha.hexdigest() != identity['sha256'] or after[2] != identity['bytes']:
        raise ValueError('weights_hash_or_identity_mismatch')
    return {'signature': list(after), 'sha256': sha.hexdigest(), 'bytes': after[2]}


def clean_child_env():
    """Do not inherit engine overrides or Git hooks/config injection."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('LLAMA_ARG_', 'GGML_', 'GIT_', 'HF_UI_', 'HF_WEBUI_'))}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
               GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/usr/bin/false')
    return env


def stop_owned_group(child):
    """Only processes in the session created by this trial are signalled."""
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait(timeout=3)


def logged_command(args, folder, timeout, stage, emit=print):
    log = folder / (stage + '.log')
    started = time.monotonic()
    with log.open('xb') as handle:
        child = subprocess.Popen(args, cwd=folder, env=clean_child_env(),
            stdin=subprocess.DEVNULL, stdout=handle, stderr=handle, start_new_session=True)
        try:
            while True:
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise ValueError(stage + '_deadline_no_retry')
                try:
                    child.wait(timeout=min(15, remaining))
                    break
                except subprocess.TimeoutExpired:
                    emit(f'{stage}: ancora in corso ({int(time.monotonic() - started)} s)…', flush=True)
                    if log.stat().st_size > LOG_MAX_BYTES:
                        raise ValueError(stage + '_log_limit')
            if child.returncode != 0 or log.stat().st_size > LOG_MAX_BYTES:
                if child.returncode != 0:
                    with log.open('rb') as diagnostic:
                        diagnostic.seek(max(0, log.stat().st_size-4000))
                        text = diagnostic.read(4000).decode('utf-8', errors='replace')
                    emit('Dettagli della fase ' + stage + ':\n' + text, flush=True)
                raise ValueError(stage + '_failed_read_owned_log')
        finally:
            if child.poll() is None:
                stop_owned_group(child)
    return {'stage': stage, 'elapsedMs': round((time.monotonic() - started) * 1000, 3),
            'logFile': log.name}


def git_args(*args):
    return ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'protocol.file.allow=never',
            '-c', 'protocol.ext.allow=never', *map(str, args)]


def configure_args(source, build):
    return ['cmake', '-S', str(source), '-B', str(build), '-G', 'Unix Makefiles',
        '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_OSX_ARCHITECTURES=x86_64',
        '-DCMAKE_OSX_DEPLOYMENT_TARGET=15.0', '-DCMAKE_EXE_LINKER_FLAGS=-framework CoreGraphics',
        '-DCMAKE_C_COMPILER=/usr/bin/clang', '-DCMAKE_CXX_COMPILER=/usr/bin/clang++',
        '-DBUILD_SHARED_LIBS=OFF', '-DGGML_NATIVE=ON', '-DGGML_METAL=ON',
        '-DGGML_METAL_EMBED_LIBRARY=ON', '-DGGML_ACCELERATE=ON', '-DGGML_OPENMP=OFF',
        '-DLLAMA_OPENSSL=OFF', '-DLLAMA_BUILD_UI=OFF', '-DLLAMA_USE_PREBUILT_UI=OFF',
        '-DLLAMA_BUILD_APP=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF', '-DLLAMA_BUILD_TESTS=OFF',
        '-DLLAMA_BUILD_TOOLS=ON', '-DLLAMA_BUILD_SERVER=ON',
        '-DLLAMA_BUILD_NUMBER=' + str(LLAMA_BUILD), '-DLLAMA_BUILD_COMMIT=' + LLAMA_COMMIT]


def selected_device(text):
    devices = []
    for line in text.splitlines():
        match = re.fullmatch(r'\s*(MTL\d+): ([^\n]+) \((\d+) MiB, (\d+) MiB free\)\s*', line)
        if match:
            devices.append({'id': match[1], 'name': match[2],
                            'totalMiB': int(match[3]), 'freeMiB': int(match[4])})
    chosen = [d for d in devices if d['name'] == GPU_NAME and d['totalMiB'] > 0]
    if len(chosen) != 1:
        raise ValueError('radeon_not_exposed_by_metal_no_inference')
    return chosen[0]


def verified_build_version(text):
    # b11461's common/build-info.cpp.in prints the semantic version followed
    # by explicit build and commit fields, rather than the old N (shortsha).
    match = re.search(r'^version:\s+(\S+)\s+\(build (\d+), commit ([0-9a-f]{40})\)\s*$', text, re.M)
    if not match or int(match[2]) != LLAMA_BUILD or match[3] != LLAMA_COMMIT:
        raise ValueError('built_server_version_mismatch')
    return {'semanticVersion': match[1], 'build': int(match[2]), 'commit': match[3]}


def build_engine(folder, emit=print):
    source, build = folder / 'source', folder / 'build'
    stages = []
    for args, timeout, name in (
        (git_args('-c', 'init.templateDir=', 'init', source), 12, 'git-init'),
        (git_args('-C', source, '-c', 'http.sslVerify=true', 'fetch', '--depth', '1',
                  '--no-tags', LLAMA_REPOSITORY, LLAMA_COMMIT), 150, 'git-fetch'),
        (git_args('-C', source, 'checkout', '--detach', 'FETCH_HEAD'), 20, 'git-checkout'),
        (git_args('-C', source, 'rev-parse', 'HEAD'), 8, 'git-commit'),
        (git_args('-C', source, 'rev-parse', 'HEAD^{tree}'), 8, 'git-tree'),
        (git_args('-C', source, 'status', '--porcelain'), 8, 'git-clean'),
    ):
        stages.append(logged_command(args, folder, timeout, name, emit))
    if ((folder / 'git-commit.log').read_text().strip() != LLAMA_COMMIT
            or (folder / 'git-tree.log').read_text().strip() != LLAMA_TREE
            or (folder / 'git-clean.log').read_text().strip()):
        raise ValueError('official_checkout_identity_mismatch')
    stages.append(logged_command(configure_args(source, build), folder, 90, 'cmake-configure', emit))
    cache = (build / 'CMakeCache.txt').read_text()
    for key in ('GGML_METAL', 'GGML_METAL_EMBED_LIBRARY', 'GGML_ACCELERATE'):
        if not re.search(r'^' + key + r':BOOL=ON$', cache, re.M):
            raise ValueError('metal_build_flag_not_effective')
    stages.append(logged_command(['cmake', '--build', str(build), '--target', 'llama-server',
                                  '--config', 'Release', '--parallel', '4'],
                                 folder, 1200, 'cmake-build', emit))
    binary = build / 'bin/llama-server'
    if binary.is_symlink() or not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError('missing_built_server')
    stages.append(logged_command([str(binary), '--version'], folder, 120, 'llama-version', emit))
    version = (folder / 'llama-version.log').read_text()
    verified_version = verified_build_version(version)
    stages.append(logged_command([str(binary), '--list-devices'], folder, 120, 'metal-devices', emit))
    device = selected_device((folder / 'metal-devices.log').read_text())
    proof = {'sourceCommit': LLAMA_COMMIT, 'sourceTree': LLAMA_TREE,
             'sourceModified': False, 'releaseIntelBinaryMetalDisabled': True,
             'buildMethod': 'local_pinned_source_with_embedded_metal_sources',
             'nativeVersion': verified_version,
             'builtServerSha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
             'buildParallelJobs': 4, 'compilationIsNotModelInference': True,
             'device': device, 'stages': stages}
    (folder / 'build-receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
    return binary, proof


def reuse_engine(previous, folder, emit=print):
    """Verify a retained trial build; never fetch, compile, install or overwrite it."""
    base = Path.home() / '.openjarvis-andrea/local-engines'
    previous = Path(previous).expanduser()
    if (not previous.is_absolute() or previous.parent != base
            or not re.fullmatch(r'llama-metal-b11461-[A-Za-z0-9_-]+', previous.name)):
        raise ValueError('reused_build_not_in_original_trial_folder')
    source, build = previous / 'source', previous / 'build'
    binary, cache_file = build / 'bin/llama-server', build / 'CMakeCache.txt'
    receipt_file = previous / 'build-receipt.json'
    if any(path.is_symlink() for path in (base.parent, base, previous, source,
            source / '.git', build, build / 'bin', binary, cache_file, receipt_file)):
        raise ValueError('reused_build_contains_symlink')
    if (not source.is_dir() or not (source / '.git').is_dir() or not binary.is_file()
            or not os.access(binary, os.X_OK) or not receipt_file.is_file()
            or not cache_file.is_file() or receipt_file.stat().st_size > MAX_BYTES
            or cache_file.stat().st_size > MAX_BYTES):
        raise ValueError('reused_build_files_missing_or_invalid')
    receipt = json.loads(receipt_file.read_bytes(), object_pairs_hook=unique_pairs)
    if (not isinstance(receipt, dict) or receipt.get('sourceCommit') != LLAMA_COMMIT
            or receipt.get('sourceTree') != LLAMA_TREE or receipt.get('sourceModified') is not False
            or receipt.get('compilationIsNotModelInference') is not True
            or not isinstance(receipt.get('builtServerSha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', receipt['builtServerSha256'])):
        raise ValueError('reused_build_receipt_identity_mismatch')
    with binary.open('rb') as handle:
        binary_hash = hashlib.file_digest(handle, 'sha256').hexdigest()
    if binary_hash != receipt['builtServerSha256']:
        raise ValueError('reused_binary_hash_mismatch')
    cache = cache_file.read_text()
    for key in ('GGML_METAL', 'GGML_METAL_EMBED_LIBRARY', 'GGML_ACCELERATE'):
        if not re.search(r'^' + key + r':BOOL=ON$', cache, re.M):
            raise ValueError('reused_metal_build_flag_not_effective')
    if not re.search(r'^CMAKE_OSX_ARCHITECTURES:(?:STRING|UNINITIALIZED)=x86_64$', cache, re.M):
        raise ValueError('reused_build_architecture_mismatch')
    stages = []
    for args, timeout, name in (
        (git_args('-C', source, 'rev-parse', 'HEAD'), 8, 'reuse-git-commit'),
        (git_args('-C', source, 'rev-parse', 'HEAD^{tree}'), 8, 'reuse-git-tree'),
        (git_args('-C', source, 'status', '--porcelain'), 8, 'reuse-git-clean'),
        ([str(binary), '--version'], 120, 'reuse-llama-version'),
        ([str(binary), '--list-devices'], 120, 'reuse-metal-devices'),
    ):
        stages.append(logged_command(args, folder, timeout, name, emit))
    if ((folder / 'reuse-git-commit.log').read_text().strip() != LLAMA_COMMIT
            or (folder / 'reuse-git-tree.log').read_text().strip() != LLAMA_TREE
            or (folder / 'reuse-git-clean.log').read_text().strip()):
        raise ValueError('reused_official_checkout_identity_mismatch')
    version = verified_build_version((folder / 'reuse-llama-version.log').read_text())
    if receipt.get('nativeVersion') != version:
        raise ValueError('reused_binary_version_mismatch')
    device = selected_device((folder / 'reuse-metal-devices.log').read_text())
    proof = copy.deepcopy(receipt)
    proof.update(reusedBuildFrom=str(previous), reusedBinaryHashVerified=True,
                 compilationPerformedThisRun=False, device=device, reuseStages=stages)
    (folder / 'build-receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
    return binary, proof


def server_args(binary, model, device, port, token, gpu_check=False):
    if (not re.fullmatch(r'MTL\d+', device) or type(port) is not int or not 1024 <= port <= 65535
            or not re.fullmatch('[0-9a-f]{64}', token)):
        raise ValueError('invalid_owned_server_arguments')
    args = [str(binary), '--model', str(model), '--alias', MODEL, '--device', device,
        '--n-gpu-layers', 'auto', '--fit', 'on', '--fit-target', '1024',
        '--ctx-size', '4096', '--parallel', '1', '--batch-size', '512',
        '--ubatch-size', str(GPU_CHECK_UBATCH if gpu_check else 512),
        '--flash-attn', 'off', '--reasoning', 'off', '--no-cache-prompt', '--no-warmup',
        '--no-webui', '--perf', '--log-verbosity', '4',
        '--host', '127.0.0.1', '--port', str(port), '--api-key', token]
    if gpu_check:
        args.extend(['--cache-ram', '0'])
    return args


def offload_proof(log, device):
    selected = re.findall(r'using device (MTL\d+) \(([^)]+)\)', log)
    layers = list(re.finditer(r'offloaded (\d+)/(\d+) layers to GPU', log))
    # --fit may inspect the same model several times before its final load.
    # Authenticated /props readiness is also mandatory; use the final load's
    # layer count and require positive model-buffer allocation on this device.
    # The pinned Metal backend names the allocations MTLn, MTLn_Private and
    # MTLn_Mapped. Only model allocations after the final offload report count;
    # an earlier --fit estimate cannot supply proof for the loaded model.
    final_load = log[layers[-1].end():] if layers else ''
    buffers = re.findall(r'\b(' + re.escape(device['id'])
        + r'(?:_Private|_Mapped)?) model buffer size\s*=\s*([0-9.]+) MiB', final_load)
    amounts = [float(size) for _, size in buffers]
    if (not selected or any(value != (device['id'], GPU_NAME) for value in selected)
            or not layers or not 0 < int(layers[-1][1]) <= int(layers[-1][2])
            or not buffers or any(not math.isfinite(size) or size < 0 for size in amounts)
            or not math.isfinite(sum(amounts)) or sum(amounts) <= 0):
        raise ValueError('effective_radeon_offload_not_proven_no_inference')
    return {'selectedDevice': device['id'], 'selectedGpu': GPU_NAME,
            'offloadedLayers': int(layers[-1][1]), 'totalLayers': int(layers[-1][2]),
            'modelGpuBufferMiB': round(sum(amounts), 2),
            'modelGpuBufferAllocations': [{'name': name, 'sizeMiB': float(size)} for name, size in buffers],
            'gpuOffloadProven': True,
            'fullOffload': int(layers[-1][1]) == int(layers[-1][2])}


def gpu_check_runtime_proof(log):
    """Require native confirmation of the final loaded compatibility profile."""
    layers = list(re.finditer(r'offloaded (\d+)/(\d+) layers to GPU', log))
    final = log[layers[-1].end():] if layers else ''
    batches = {}
    for key, expected in (('n_batch', 512), ('n_ubatch', GPU_CHECK_UBATCH)):
        values = re.findall(r'\bllama_context:\s*' + key + r'\s*=\s*(\d+)\b', final)
        if not values or int(values[-1]) != expected:
            raise ValueError('gpu_check_effective_batch_not_confirmed_no_inference')
        batches[key] = int(values[-1])
    for label in ('fusion', 'concurrency', 'graph optimize'):
        values = re.findall(r'\bggml_metal_init:\s*use ' + label + r'\s*=\s*(true|false)\b', final)
        if not values or any(value != 'false' for value in values):
            raise ValueError('gpu_check_effective_metal_settings_not_confirmed_no_inference')
    if not re.search(r'\bload_model: prompt cache is disabled\b', final):
        raise ValueError('gpu_check_prompt_cache_not_disabled_no_inference')
    return {'profile': 'radeon_ubatch64_serial_unfused',
            'effectiveLogicalBatch': batches['n_batch'], 'effectivePhysicalBatch': batches['n_ubatch'],
            'fusionEnabled': False, 'concurrencyEnabled': False, 'graphOptimizeEnabled': False,
            'ramPromptCacheEnabled': False, 'settingsConfirmedByNativeLog': True,
            'compatibilityAndPerformanceNotYetProven': True}


def native_failure_evidence(file):
    """Return bounded canonical error codes, never arbitrary native log text."""
    try:
        if file.is_symlink() or not file.is_file():
            raise ValueError()
        with file.open('rb') as handle:
            size = file.stat().st_size
            handle.seek(max(0, size - MAX_BYTES))
            tail = handle.read(MAX_BYTES).decode('utf-8', errors='replace')
    except (OSError, ValueError):
        return {'readAvailable': False, 'codes': [], 'tailBytesLimited': MAX_BYTES}
    patterns = (
        ('metal_command_buffer_failed', r'\bE ggml_metal_synchronize: error: command buffer \d+ failed with status \d+\b'),
        ('gpu_driver_timeout', r'\bE error: Caused GPU Timeout Error \([^\n]*kIOAccelCommandBufferCallbackErrorTimeout\)'),
        ('metal_backend_error_state', r'\bE ggml_metal_graph_compute: backend is in error state\b'),
        ('graph_compute_failed', r'\bE (?:graph_compute: .*failed with error -\d+|process_ubatch: failed to compute graph)\b'),
        ('server_compute_error', r'\bE srv\s+(?:decode: Compute error\.|send_error: task id = \d+, error: Compute error\.)'),
        ('metal_out_of_memory', r'\bE error: Caused (?:Out of Memory|GPU Out of Memory) Error\b'))
    return {'readAvailable': True, 'codes': [code for code, pattern in patterns if re.search(pattern, tail)],
            'tailBytesLimited': MAX_BYTES, 'logTailTruncated': size > MAX_BYTES,
            'rawLogTextIncluded': False}


class OwnedMetalServer:
    def __init__(self, binary, identity, device, folder, emit=print, gpu_check=False):
        self.binary, self.identity, self.device = binary, identity, device
        self.folder, self.emit = folder, emit
        self.gpu_check = gpu_check
        self.child = self.handle = None
        self.token = secrets.token_hex(32)
        self.port = None
        self.proof = None
        self.closed = False

    def __enter__(self):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            self.port = probe.getsockname()[1]
        self.handle = (self.folder / 'owned-server.log').open('xb')
        started = time.monotonic()
        try:
            env = clean_child_env()
            if self.gpu_check:
                env.update(GPU_CHECK_ENV)
            self.child = subprocess.Popen(server_args(self.binary, self.identity['path'],
                self.device['id'], self.port, self.token, self.gpu_check), cwd=self.folder, env=env,
                stdin=subprocess.DEVNULL, stdout=self.handle, stderr=self.handle, start_new_session=True)
            deadline, last_notice = started + 150, started
            while True:
                if self.child.poll() is not None:
                    raise ValueError('metal_model_start_failed_read_owned_log')
                if time.monotonic() >= deadline:
                    raise ValueError('metal_model_start_deadline_no_retry')
                if (self.folder / 'owned-server.log').stat().st_size > LOG_MAX_BYTES:
                    raise ValueError('metal_model_start_log_limit')
                try:
                    props = json_request(self.url + '/props', timeout=2, token=self.token)
                except urllib.error.HTTPError as exc:
                    if exc.code != 503:
                        raise ValueError('owned_server_http_identity_not_confirmed') from None
                    props = None
                except (urllib.error.URLError, TimeoutError):
                    props = None
                if props is not None:
                    if (props.get('total_slots') != 1
                            or props.get('default_generation_settings', {}).get('n_ctx') != 4096
                            or props.get('model_path') != self.identity['path']
                            or not isinstance(props.get('chat_template'), str) or not props['chat_template']):
                        raise ValueError('metal_context_or_model_identity_mismatch')
                    log = (self.folder / 'owned-server.log').read_text(errors='replace')
                    self.proof = offload_proof(log, self.device)
                    if self.gpu_check:
                        self.proof['compatibilityRuntime'] = gpu_check_runtime_proof(log)
                    self.proof.update(modelLoadAndMetalInitializationClientMs=round(
                        (time.monotonic() - started) * 1000, 3),
                        nativeChatTemplateSha256=hashlib.sha256(props['chat_template'].encode()).hexdigest(),
                        nativeDefaultSamplerFields={k: v for k, v in
                            props['default_generation_settings'].get('params', {}).items()
                            if k in {'top_k', 'top_p', 'min_p', 'repeat_penalty', 'presence_penalty',
                                     'frequency_penalty'} and type(v) in (int, float) and math.isfinite(v)},
                        warmupInferenceDisabled=True, contextPerSlot=4096, slots=1,
                        flashAttention='off', requestedLogicalBatch=512,
                        requestedPhysicalBatch=GPU_CHECK_UBATCH if self.gpu_check else 512)
                    return self
                if time.monotonic() - last_notice >= 15:
                    self.emit('Caricamento del modello sulla Radeon ancora in corso…', flush=True)
                    last_notice = time.monotonic()
                time.sleep(0.2)
        except BaseException:
            self.close()
            raise

    @property
    def url(self):
        return 'http://127.0.0.1:' + str(self.port)

    def close(self):
        if self.closed:
            return
        try:
            if self.child is not None and self.child.poll() is None:
                stop_owned_group(self.child)
        finally:
            if self.handle is not None:
                self.handle.close()
            self.closed = self.child is None or self.child.poll() is not None

    def __exit__(self, *args):
        self.close()


def normalize_native(engine, response):
    if engine == 'ollama_cpu':
        native = response
        keys = ('prompt_eval_count', 'prompt_eval_cached_count', 'prompt_eval_duration',
                'eval_count', 'eval_duration', 'load_duration', 'total_duration')
        values = [native.get(k) for k in keys]
        if any(type(n) is not int or not 0 <= n <= 2**53-1 for n in values):
            raise ValueError('missing_or_invalid_ollama_timings')
        total, cached, prompt_ns, generated, generation_ns, load_ns, total_ns = values
        if total <= cached:
            raise ValueError('ollama_prompt_token_counts_invalid')
        return {'promptTokens': total, 'processedPromptTokens': total-cached, 'cachedPromptTokens': cached,
                'prefillMs': prompt_ns / 1e6, 'generatedTokens': generated,
                'generationMs': generation_ns / 1e6, 'loadMs': load_ns / 1e6, 'totalMs': total_ns / 1e6}
    timings = response.get('timings', {})
    usage = response.get('usage', {})
    if not isinstance(timings, dict) or not isinstance(usage, dict):
        raise ValueError('missing_llama_timings')
    processed, cached, generated = (timings.get(k) for k in ('prompt_n', 'cache_n', 'predicted_n'))
    if any(type(n) is not int or not 0 <= n <= 2**53-1 for n in (processed, cached, generated)) or processed <= 0:
        raise ValueError('invalid_llama_token_counts')
    # llama.cpp prompt_n counts processed tokens, not the entire input.
    if usage.get('prompt_tokens') != processed+cached or usage.get('completion_tokens') != generated:
        raise ValueError('llama_usage_not_aligned_with_timings')
    prefill, generation = timings.get('prompt_ms'), timings.get('predicted_ms')
    if any(type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in (prefill, generation)):
        raise ValueError('invalid_llama_durations')
    return {'promptTokens': processed+cached, 'processedPromptTokens': processed, 'cachedPromptTokens': cached,
            'prefillMs': prefill, 'generatedTokens': generated, 'generationMs': generation,
            'loadMs': None, 'totalMs': None}


def completion_once(engine, messages, schema, endpoint=None, token=None, transport=None):
    """One full-response POST on both engines; no hidden streaming comparison."""
    if engine == 'ollama_cpu':
        url = OLLAMA + '/api/chat'
        payload = {'model': MODEL, 'messages': messages, 'format': schema, 'stream': False,
                   'think': False, 'keep_alive': '15m',
                   'options': {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096, 'num_batch': 512}}
    elif engine == 'llama_metal':
        if not isinstance(endpoint, str) or not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{4,5}', endpoint):
            raise ValueError('invalid_local_engine_endpoint')
        url = endpoint + '/v1/chat/completions'
        payload = {'model': MODEL, 'messages': messages, 'stream': False,
                   'temperature': 0.4, 'max_tokens': 512, 'cache_prompt': False,
                   'reasoning_effort': 'none', 'chat_template_kwargs': {'enable_thinking': False},
                   'response_format': {'type': 'json_schema',
                       'json_schema': {'name': 'web_evidence', 'schema': schema}}}
    else:
        raise ValueError('invalid_engine')
    started = time.monotonic()
    try:
        response = json_request(url, payload, 90, token, transport)
    except urllib.error.HTTPError as exc:
        # Read only a bounded error body. Report a fixed code, not the request,
        # credential, source, URL or arbitrary text returned by the engine.
        try:
            raw = exc.read(4097)
            compute = len(raw) <= 4096 and b'Compute error.' in raw
        except OSError:
            compute = False
        finally:
            exc.close()
        code = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else 'error'
        raise ValueError('local_model_http_' + str(code) + ('_compute_error' if compute else '')) from None
    elapsed = round((time.monotonic() - started) * 1000, 3)
    if engine == 'ollama_cpu':
        message = response.get('message')
        complete = response.get('done') is True
        reason = response.get('done_reason')
    else:
        choices = response.get('choices')
        if (not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict)
                or choices[0].get('index') != 0):
            raise ValueError('invalid_llama_choice')
        message = choices[0].get('message')
        reason, complete = choices[0].get('finish_reason'), True
    if (not isinstance(message, dict) or message.get('role') != 'assistant'
            or message.get('tool_calls') or message.get('thinking') or message.get('reasoning_content')
            or not isinstance(message.get('content'), str) or len(message['content']) > 5000):
        raise ValueError('invalid_or_oversized_model_message')
    try:
        native, timing_error = normalize_native(engine, response), None
    except ValueError as exc:
        native, timing_error = {}, str(exc)
    return {'raw': message['content'], 'completed': complete and reason == 'stop', 'doneReason': reason,
            'totalClientMs': elapsed, 'firstJsonClientMs': None,
            'transport': 'non_streaming_json_on_both_backends',
            'native': native, 'nativeTimingErrorCode': timing_error}


def worker(project, payload):
    check, pipeline = load_project(project)
    if not isinstance(payload, dict):
        raise ValueError('invalid_worker_input')
    operation = payload.get('operation')
    if operation == 'metadata' and set(payload) == {'operation'}:
        version = json_request(OLLAMA + '/api/version')
        ps = json_request(OLLAMA + '/api/ps')
        models = ps.get('models')
        if version.get('version') != VERSION or not isinstance(models, list) or len(models) > 1:
            raise ValueError('unexpected_ollama_version_or_loaded_models')
        if models and (not isinstance(models[0], dict) or models[0].get('name') != MODEL
                       or type(models[0].get('size_vram')) is not int or models[0]['size_vram'] != 0):
            raise ValueError('reference_model_not_cpu_or_unexpected_model')
        identity = model_identity(json_request(OLLAMA + '/api/show', {'model': MODEL}))
        return {'version': VERSION, 'initialLoadedCpuModel': bool(models), 'identity': identity}
    if operation == 'hash' and set(payload) == {'operation', 'identity'}:
        return verify_weights(payload['identity'])
    if operation == 'read' and set(payload) == {'operation', 'case'}:
        index = payload['case']
        if type(index) is not int or index not in (0, 1):
            raise ValueError('invalid_read_case')
        page = check.post('/api/andrea/web/read', {'url': check.CASES[index]['url']}, 30, opener())
        check.checked_page(page)
        return page
    if operation != 'model' or set(payload) != {'operation', 'case', 'page', 'engine', 'marker', 'endpoint', 'token'}:
        raise ValueError('invalid_worker_operation')
    index = payload['case']
    if type(index) is not int or not 0 <= index < 3:
        raise ValueError('invalid_model_case')
    page, engine = payload['page'], payload['engine']
    check.checked_page(page)
    case = check.CASES[index]
    bank, messages, schema, selection = pipeline.prepare(page, case['question'])
    result = completion_once(engine, isolated_messages(messages, payload['marker']), schema,
                             payload['endpoint'], payload['token'])
    original = pipeline.validate(result['raw'], bank, result['completed'], page, selection)
    checked = control_audit(original, selection)
    return {'case': case['id'], 'engine': engine, 'criteria': case['criteria'],
            'sourceTextSha256': hashlib.sha256(page['text'].encode()).hexdigest(),
            'preparationSha256': digest((bank, messages, schema, selection)),
            'nativeSchemaSha256': digest(schema), 'modelSourceCharacters': selection['modelSourceCharacters'],
            'result': result, 'originalChecks': original, 'checks': checked,
            'referenceResidency': cpu_residency() if engine == 'ollama_cpu' else None,
            'qualityVerdict': 'pending_review'}


def timing_eligible(row):
    result = row.get('result', {})
    metrics = result.get('native', {})
    if (result.get('completed') is not True or result.get('nativeTimingErrorCode') is not None
            or row.get('observerClosed') is not True
            or result.get('transport') != 'non_streaming_json_on_both_backends'):
        return False
    total, prefill, count, cached = (result.get('totalClientMs'), metrics.get('prefillMs'),
                                   metrics.get('processedPromptTokens'), metrics.get('cachedPromptTokens'))
    generation = metrics.get('generationMs')
    if (type(count) is not int or count <= 0 or type(cached) is not int or not 0 <= cached <= MAX_CACHED_TOKENS
            or any(type(n) not in (int, float) or not math.isfinite(n) or n <= 0 for n in (total, prefill))
            or type(generation) not in (int, float) or not math.isfinite(generation) or generation < 0):
        return False
    if row.get('engine') == 'ollama_cpu':
        residency = row.get('referenceResidency') or {}
        return residency.get('expectedModelLoaded') is True and residency.get('sizeVram') == 0
    return row.get('engine') == 'llama_metal'


def expected_shape(row):
    expected = {'asyncio_scope': 2, 'csv_conversion_condition': 1, 'missing_price': 0}
    checked = row.get('checks', {})
    return (row.get('case') in expected and checked.get('outcome') ==
            ('abstained' if row['case'] == 'missing_price' else 'accepted_pending_semantic_review')
            and len(checked.get('claims', [])) == expected[row['case']])


def comparison(rows, gpu, weights_unchanged):
    ids = ('asyncio_scope', 'csv_conversion_condition', 'missing_price')
    complete = [(r.get('case'), r.get('engine')) for r in rows] == [(ids[i], e) for i, e in ORDER]
    pairs = []
    for case in ids:
        group = [r for r in rows if r.get('case') == case]
        pair = {'case': case, 'inputContractIdentical': False, 'timingsEligible': False,
                'clientTotalGainPercent': None, 'rawPrefillGainPercent': None,
                'nativePrefillAndGenerationGainPercent': None, 'numericGatesMet': False}
        by_engine = {r.get('engine'): r for r in group}
        if len(group) == 2 and set(by_engine) == {'ollama_cpu', 'llama_metal'}:
            base, candidate = by_engine['ollama_cpu'], by_engine['llama_metal']
            same = all(base.get(k) == candidate.get(k) for k in
                ('sourceTextSha256', 'preparationSha256', 'nativeSchemaSha256', 'modelSourceCharacters'))
            pair['inputContractIdentical'] = same
            if same and timing_eligible(base) and timing_eligible(candidate):
                gain = 100 * (1 - candidate['result']['totalClientMs'] / base['result']['totalClientMs'])
                prefill = 100 * (1 - candidate['result']['native']['prefillMs'] / base['result']['native']['prefillMs'])
                bn, cn = base['result']['native'], candidate['result']['native']
                native_gain = 100 * (1 - (cn['prefillMs']+cn['generationMs']) / (bn['prefillMs']+bn['generationMs']))
                pair.update(timingsEligible=True, clientTotalGainPercent=round(gain, 3),
                            rawPrefillGainPercent=round(prefill, 3),
                            nativePrefillAndGenerationGainPercent=round(native_gain, 3), numericGatesMet=(
                                gain >= -MAX_TOTAL_REGRESSION_PERCENT if case == 'missing_price' else
                                min(gain, native_gain) >= MIN_TOTAL_GAIN_PERCENT))
        pairs.append(pair)
    numeric = (complete and weights_unchanged and gpu.get('gpuOffloadProven') is True
               and all(p['numericGatesMet'] for p in pairs))
    shapes = complete and all(expected_shape(r) for r in rows if r['engine'] == 'llama_metal')
    return {'completeFixedOrder': complete, 'pairs': pairs, 'numericGatesMet': numeric,
            'candidateTechnicalShapesMet': shapes, 'qualityVerdict': 'pending_review',
            'decision': 'requires_meaning_review_and_installed_validation' if numeric and shapes else 'do_not_adopt',
            'integrationAllowed': False, 'browserRendering': 'not_measured',
            'backendIncludesTemplateAndSamplerDifferences': True, 'isolatedGpuCausalEffect': 'not_measured',
            'firstVisibleResponseLatency': 'not_measured', 'oneSeriesDoesNotProveAllWorkloads': True,
            'metalModelLoadingExcludedFromPerRequestTimings': True,
            'cpuModelLoadingReportedSeparatelyInNativeTimings': True,
            'coldStartFairnessRequiresApplicationCheckBeforeIntegration': True}


def create_trial_folder():
    base = Path.home() / '.openjarvis-andrea/local-engines'
    for part in (base.parent, base):
        if part.is_symlink():
            raise ValueError('isolated_engine_folder_is_symlink')
    base.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix='llama-metal-b11461-', dir=base))


def safe_error_code(exc):
    value = str(exc)
    if re.fullmatch(r'[a-z0-9_]{1,120}', value):
        return value
    return 'local_model_io_error' if isinstance(exc, OSError) else 'local_trial_stage_failed'


def gpu_check_outcome(rows, weights_unchanged):
    value = rows[0] if len(rows) == 1 else {}
    if not value or value.get('error'):
        outcome = 'failed_runtime'
    elif value.get('result', {}).get('completed') is not True:
        outcome = 'incomplete_model_response'
    elif not weights_unchanged:
        outcome = 'weights_identity_changed'
    elif expected_shape(value):
        outcome = 'completed_pending_semantic_review'
    else:
        outcome = 'completed_but_answer_rejected'
    return {'outcome': outcome, 'qualityVerdict': 'pending_review', 'integrationAllowed': False,
            'decision': 'do_not_adopt_from_single_gpu_check', 'latencyComparisonCollected': False,
            'browserRendering': 'not_measured', 'firstVisibleResponseLatency': 'not_measured',
            'cpuModelRequests': 0, 'automaticFullComparisonAfterSuccess': False,
            'oneRequestDoesNotProveReliability': True}


def run(project, emit=print, reuse_build_folder=None, gpu_check=False):
    if gpu_check and reuse_build_folder is None:
        raise ValueError('gpu_check_requires_reuse_build_no_compilation')
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64':
        raise ValueError('trial_requires_intel_macos')
    required_tools = ('git',) if reuse_build_folder is not None else ('git', 'cmake', 'make', 'clang')
    missing = [name for name in required_tools if not shutil.which(name)]
    if missing:
        raise ValueError('required_build_tools_missing_' + '_'.join(missing))
    check, _ = load_project(project)
    metadata, _, _ = owned_worker(project, {'operation': 'metadata'}, 20)
    identity = metadata['identity']
    emit('Verifica della copia locale del modello; nessun download di pesi…', flush=True)
    weights, _, _ = owned_worker(project, {'operation': 'hash', 'identity': identity}, 120)
    # Prove the app is running before spending time on a build.
    pages = {}
    for index in ((0,) if gpu_check else (0, 1)):
        pages[index], _, _ = owned_worker(project, {'operation': 'read', 'case': index}, 35)
    if not gpu_check:
        pages[2] = pages[1]
        required = check.CASES[1]['requiredContext']
        if ' '.join(required.split()) not in ' '.join(pages[1]['text'].split()):
            raise ValueError('csv_exception_not_in_source_no_inference')
    folder = create_trial_folder()
    emit('Cartella separata della prova: ' + str(folder), flush=True)
    server, rows = None, []
    order = ((0, 'llama_metal'),) if gpu_check else ORDER
    try:
        if reuse_build_folder is None:
            emit('Prima compilazione con Metal: può richiedere 5–20 minuti. Nessuna installazione in OpenJarvis.', flush=True)
            binary, build = build_engine(folder, emit)
        else:
            emit('Verifica e riuso del motore già compilato. Nessuna ricompilazione.', flush=True)
            binary, build = reuse_engine(reuse_build_folder, folder, emit)
        # We prepare locally from the captured bytes; do not use or refresh the
        # app's five-minute page IDs for model requests. Both engines receive
        # the identical captured snapshot even if the live page later changes.
        emit('Radeon riconosciuta. Caricamento del modello nel server temporaneo…', flush=True)
        server = OwnedMetalServer(binary, identity, build['device'], folder, emit, gpu_check=gpu_check)
        with server:
            emit(json.dumps({'effectiveGpuProof': server.proof}, ensure_ascii=False, indent=2), flush=True)
            if gpu_check:
                emit('Una sola richiesta GPU, limite 90 secondi. Nessuna richiesta CPU o serie aggiuntiva.', flush=True)
            else:
                emit('Sei richieste, una sola serie (circa 4–8 minuti). Lascia OpenJarvis acceso, senza altre richieste.', flush=True)
            for number, (index, engine) in enumerate(order, 1):
                emit(f'Richiesta {number}/{len(order)}: {check.CASES[index]["id"]}, {engine}…', flush=True)
                if file_signature(Path(identity['path'])) != tuple(weights['signature']):
                    raise ValueError('weights_changed_during_trial')
                try:
                    row, observations, closed = owned_worker(project, {'operation': 'model', 'case': index,
                        'page': pages[index], 'engine': engine, 'marker': secrets.token_hex(16),
                        'endpoint': server.url if engine == 'llama_metal' else None,
                        'token': server.token if engine == 'llama_metal' else None}, WORKER_SECONDS, observe=True)
                    row['thermalObservations'], row['observerClosed'] = observations, closed
                    rows.append(row)
                    emit(json.dumps(row, ensure_ascii=False, indent=2), flush=True)
                    if not row['result']['completed']:
                        break
                except (OSError, ValueError, TypeError) as exc:
                    rows.append({'case': check.CASES[index]['id'], 'engine': engine,
                                 'error': safe_error_code(exc), 'result': {}, 'checks': {},
                                 'qualityVerdict': 'not_evaluated'})
                    break
        unchanged = file_signature(Path(identity['path'])) == tuple(weights['signature'])
        report = {'mode': 'installed_v9_intel_metal_gpu_check' if gpu_check else 'installed_v9_intel_metal_backend_trial',
            'contractRevision': 'compact_web_evidence_v9',
            'productionModified': False, 'isolatedRuntimeBuilt': True, 'weightsDownloaded': False,
            'isolatedRuntimeBuiltThisRun': reuse_build_folder is None,
            'existingBuildReused': reuse_build_folder is not None, 'nativeLogVerbosity': 4,
            'vaultRead': False, 'automaticRetries': 0, 'requestedModelCalls': len(order),
            'completedRows': len(rows), 'browserRendering': 'not_measured',
            'existingProcessesTerminated': False, 'ownedMetalServerStopped': server.closed,
            'ollamaVersion': VERSION, 'model': MODEL, 'modelBlobSha256': weights['sha256'],
            'modelBytes': weights['bytes'], 'weightsUnchangedDuringTrial': unchanged,
            'ollamaTemplateSha256': identity['ollamaTemplateSha256'], 'build': build,
            'gpuProof': server.proof, 'sourceContractAndSchemaUnchanged': True,
            'cacheMarkerIsDiagnosticNotProduction': True, 'bothBackendsUseFullJsonTransport': True,
            'publicPageReads': len({i for i, _ in order if i < 2}),
            'capturedSnapshotBeforeBuild': True, 'appPageCacheUsedForModelCalls': False,
            'threadPolicy': 'automatic_unchanged', 'warmupInferenceRequests': 0,
            'thresholds': {'minimumClientTotalGainPercentForBothPositiveCases': MIN_TOTAL_GAIN_PERCENT,
                           'minimumNativePrefillAndGenerationGainPercentForBothPositiveCases': MIN_TOTAL_GAIN_PERCENT,
                           'maximumClientTotalRegressionPercentForMissingCase': MAX_TOTAL_REGRESSION_PERCENT,
                           'maximumCachedTokens': MAX_CACHED_TOKENS},
            'nativeRuntimeFailure': native_failure_evidence(folder / 'owned-server.log'), 'rows': rows}
        if gpu_check:
            report.pop('thresholds')
            report.update(gpuCheck=gpu_check_outcome(rows, unchanged), attemptedModelCalls=len(rows),
                          completedModelCalls=sum(r.get('result', {}).get('completed') is True for r in rows),
                          compatibilityEnvironmentAppliedOnlyToOwnedServer=copy.deepcopy(GPU_CHECK_ENV))
        else:
            report['comparison'] = comparison(rows, server.proof, unchanged)
        (folder / 'trial-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        emit('Server temporaneo chiuso. OpenJarvis continua a usare la sua installazione abituale.', flush=True)
        emit('Risultati salvati anche in: ' + str(folder / 'trial-result.json'), flush=True)
        return report
    except BaseException as exc:
        if gpu_check and isinstance(exc, Exception):
            report = {'mode': 'installed_v9_intel_metal_gpu_check', 'stageFailureCode': safe_error_code(exc),
                      'productionModified': False, 'automaticRetries': 0, 'requestedModelCalls': 1,
                      'attemptedModelCalls': len(rows),
                      'completedModelCalls': sum(r.get('result', {}).get('completed') is True for r in rows),
                      'gpuCheck': {**gpu_check_outcome([], False), 'outcome': 'failed_setup'},
                      'nativeRuntimeFailure': native_failure_evidence(folder / 'owned-server.log'),
                      'ownedMetalServerStopped': server.closed if server is not None else True,
                      'rows': rows}
            (folder / 'trial-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            emit(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        emit('Prova fermata; dettagli della fase nella cartella indicata. Nessun retry automatico.', flush=True)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--reuse-build', type=Path,
                        help='Verify and reuse an existing isolated trial build, without recompiling.')
    parser.add_argument('--gpu-check', action='store_true',
                        help='One GPU request with the bounded Radeon compatibility profile; requires --reuse-build.')
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve(strict=True)
        if args.worker:
            if args.reuse_build is not None:
                raise ValueError('reuse_build_not_a_worker_argument')
            if args.gpu_check:
                raise ValueError('gpu_check_not_a_worker_argument')
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('worker_input_too_large')
            report = worker(project, json.loads(raw, object_pairs_hook=unique_pairs))
        else:
            report = run(project, reuse_build_folder=args.reuse_build, gpu_check=args.gpu_check)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        return 0
    except KeyboardInterrupt:
        print('Prova interrotta con Control+C; server temporaneo chiuso.', file=sys.stderr)
        return 130
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired) as exc:
        print('Prova fermata: ' + str(exc) + '. Nessun retry o modifica del progetto.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

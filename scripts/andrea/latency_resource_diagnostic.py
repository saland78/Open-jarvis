"""Bounded, read-only macOS resource diagnosis; zero model inference requests.

Only fixed system queries and GET /api/version and /api/ps are permitted.
Missing measurements remain unknown. This current snapshot cannot explain
the cause of a past benchmark or certify latency, quality or CPU temperature.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import time
import urllib.error
import urllib.request

MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
BASE = 'http://127.0.0.1:11434'
MAX_BYTES = 65536
BUDGET_SECONDS = 20
EXPECTED = {
    'scripts/andrea/runtime.py': '395271608f3f6678017064afcb7dc4ac2272f3d75bc249cddbfc240a861bb172',
    'scripts/andrea/web_page_fetch.py': '2168186c522d1ee07e805f3f20b5d7aa747aef46847a460b1b8c65050efcdfdc',
    'scripts/andrea/web_page_local.py': '06f58558d8a234e3974e3cb7cc0621d7ee1b1bbce0d339c9380b188cb7aa4706',
    'scripts/andrea/web_sentence_contract.py': '5b8a73b2a9d534074ec61eb67b9abd0eb6c73d3abb2783e76149ad6b3b7b2285',
}
FIXED_COMMANDS = {
    ('/usr/sbin/sysctl', '-n', 'hw.physicalcpu', 'hw.logicalcpu', 'hw.memsize'),
    ('/usr/sbin/sysctl', '-n', 'vm.loadavg'),
    ('/usr/sbin/sysctl', '-n', 'vm.swapusage'),
    ('/usr/bin/vm_stat',),
    ('/usr/bin/pmset', '-g', 'therm'),
    ('/usr/bin/pmset', '-g', 'batt'),
    ('/usr/bin/pmset', '-g', 'custom'),
    ('/usr/bin/top', '-l', '2', '-s', '1', '-n', '0', '-R', '-F'),
    ('/usr/bin/pgrep', '-x', 'ollama'),
    ('/usr/bin/pgrep', '-x', 'ollama_llama_server'),
}


class DiagnosticError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate_key')
        value[key] = item
    return value


def integer(value):
    return value if type(value) is int and 0 <= value <= 2**53 - 1 else None


def finite(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def verify_project(project):
    for relative, expected in EXPECTED.items():
        path = project / relative
        parts = Path(relative).parts
        if any((project / Path(*parts[:i])).is_symlink() for i in range(1, len(parts) + 1)):
            raise DiagnosticError('Collegamento simbolico inatteso: ' + relative)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise DiagnosticError('Versione installata diversa da quella verificata: ' + relative)


def allowed_command(command):
    if tuple(command) in FIXED_COMMANDS:
        return True
    return (len(command) == 5 and command[:2] == ['/bin/ps', '-p']
            and command[3:] == ['-o', 'pcpu=,command=']
            and re.fullmatch(r'[1-9]\d{0,7}(?:,[1-9]\d{0,7}){0,15}', command[2]) is not None)


class Reader:
    def __init__(self, *, runner=subprocess.run, opener=None, clock=time.monotonic):
        self.runner = runner
        # A default API read runs in an owned child, so a dribbling response
        # cannot outlive the whole read budget. An injected opener is only used
        # by that child and deterministic unit tests of the HTTP boundary.
        self.opener = opener
        self.clock = clock
        self.started = clock()
        self.issues = []

    def timeout(self):
        remaining = BUDGET_SECONDS - (self.clock() - self.started)
        if remaining <= 0:
            raise TimeoutError('diagnostic_budget_exhausted')
        return min(3, remaining)

    def command(self, label, command):
        if not allowed_command(command):
            raise DiagnosticError('Comando fuori dalle letture previste.')
        try:
            env = dict(os.environ)
            env['LC_ALL'] = 'C'
            result = self.runner(command, capture_output=True, text=True, timeout=self.timeout(),
                                 check=False, env=env)
            if result.returncode != 0 or len(result.stdout.encode()) > MAX_BYTES:
                self.issues.append({'measurement': label, 'reason': 'unavailable_or_oversized'})
                return None
            return result.stdout
        except (OSError, TimeoutError, subprocess.TimeoutExpired):
            self.issues.append({'measurement': label, 'reason': 'unavailable_or_timeout'})
            return None

    def get(self, path):
        if path not in ('/api/version', '/api/ps'):
            raise DiagnosticError('Endpoint fuori dalle due letture previste.')
        if self.opener is None:
            try:
                result = self.runner([sys.executable, str(Path(__file__).resolve()), '--ollama-read', path],
                                     capture_output=True, text=True, timeout=self.timeout(), check=False)
                if result.returncode != 0 or len(result.stdout.encode()) > MAX_BYTES:
                    raise ValueError('invalid_response')
                value = json.loads(result.stdout, object_pairs_hook=unique_pairs)
                if not isinstance(value, dict) or 'diagnosticError' in value:
                    raise ValueError('invalid_response')
                return value
            except (OSError, TimeoutError, subprocess.TimeoutExpired, ValueError):
                self.issues.append({'measurement': path, 'reason': 'unavailable_or_invalid'})
                return None
        request = urllib.request.Request(BASE + path, headers={'Accept': 'application/json'}, method='GET')
        try:
            with self.opener.open(request, timeout=self.timeout()) as response:
                data = response.read(MAX_BYTES + 1)
                if response.status != 200 or len(data) > MAX_BYTES:
                    raise ValueError('invalid_response')
                value = json.loads(data, object_pairs_hook=unique_pairs)
                if not isinstance(value, dict):
                    raise ValueError('invalid_response')
                return value
        except (OSError, TimeoutError, ValueError, urllib.error.URLError):
            self.issues.append({'measurement': path, 'reason': 'unavailable_or_invalid'})
            return None


def hardware(text):
    values = (text or '').splitlines()
    if len(values) != 3 or any(not re.fullmatch(r'\d+', line.strip()) for line in values):
        return {'physicalCores': None, 'logicalCores': None, 'memoryBytes': None}
    counts = [integer(int(line)) for line in values]
    return dict(zip(('physicalCores', 'logicalCores', 'memoryBytes'), counts))


def load_average(text):
    match = re.fullmatch(r'\s*\{\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*\}\s*', text or '')
    return [finite(float(value)) for value in match.groups()] if match else None


def swap_used_bytes(text):
    match = re.search(r'\bused\s*=\s*(\d+(?:\.\d+)?)([BKMGTP])\b', text or '')
    if not match:
        return None
    value = float(match[1]) * 1024**'BKMGTP'.index(match[2])
    return integer(int(value)) if math.isfinite(value) else None


def vm_counters(text):
    page = re.search(r'page size of (\d+) bytes', text or '')
    result = {'pageSizeBytes': integer(int(page[1])) if page else None}
    for key in ('Swapins', 'Swapouts', 'Pageouts', 'Pages free', 'Pages occupied by compressor'):
        match = re.search(r'^' + re.escape(key) + r':\s*(\d+)\.?\s*$', text or '', re.M)
        result[key] = integer(int(match[1])) if match else None
    return result


def thermal_limits(text):
    result = {}
    for key in ('CPU_Speed_Limit', 'CPU_Scheduler_Limit', 'CPU_Available_CPUs'):
        match = re.search(r'^\s*' + key + r'\s*=\s*(\d+)\s*$', text or '', re.M)
        result[key] = integer(int(match[1])) if match else None
    return result


def power_status(text):
    match = re.search(r"Now drawing from '(AC Power|Battery Power|UPS Power)'", text or '')
    percentage = re.search(r'\b(\d{1,3})%;', text or '')
    return {'source': match[1] if match else None,
            'batteryPercent': int(percentage[1]) if percentage and int(percentage[1]) <= 100 else None}


def low_power_modes(text):
    modes = {'AC Power': None, 'Battery Power': None, 'UPS Power': None}
    current = None
    for line in (text or '').splitlines():
        if line.strip().rstrip(':') in modes:
            current = line.strip().rstrip(':')
        match = re.fullmatch(r'\s*lowpowermode\s+([01])\s*', line)
        if current and match:
            modes[current] = int(match[1])
    return modes


def cpu_usage(text):
    samples = re.findall(r'CPU usage:\s*(\d+(?:\.\d+)?)% user,\s*(\d+(?:\.\d+)?)% sys,\s*(\d+(?:\.\d+)?)% idle', text or '')
    if not samples:
        return {'userPercent': None, 'systemPercent': None, 'idlePercent': None}
    values = [finite(float(value)) for value in samples[-1]]
    if any(value is None or value > 100 for value in values) or abs(sum(values) - 100) > 2:
        values = [None, None, None]
    return dict(zip(('userPercent', 'systemPercent', 'idlePercent'), values))


def selected_model(data):
    models = data.get('models') if isinstance(data, dict) else None
    if not isinstance(models, list) or len(models) > 256 or any(not isinstance(m, dict) for m in models):
        return {'loadedModelCount': None, 'expectedModelLoaded': None, 'expectedModel': None}
    matches = [m for m in models if m.get('name') == MODEL or m.get('model') == MODEL]
    if len(matches) > 1:
        return {'loadedModelCount': len(models), 'expectedModelLoaded': None, 'expectedModel': None}
    selected = None
    if matches:
        model = matches[0]
        selected = {key: integer(model.get(key)) for key in ('size', 'size_vram', 'context_length')}
    return {'loadedModelCount': len(models), 'expectedModelLoaded': bool(matches), 'expectedModel': selected}


def ollama_processes(reader):
    pids = set()
    for name in ('ollama', 'ollama_llama_server'):
        output = reader.command('ollama_process_ids', ['/usr/bin/pgrep', '-x', name])
        if output:
            pids.update(line.strip() for line in output.splitlines() if re.fullmatch(r'[1-9]\d{0,7}', line.strip()))
    if not pids or len(pids) > 16:
        return {'available': False, 'processCount': None, 'runnerOptions': []}
    output = reader.command('ollama_process_options', ['/bin/ps', '-p', ','.join(sorted(pids, key=int)), '-o', 'pcpu=,command='])
    if output is None:
        return {'available': False, 'processCount': None, 'runnerOptions': []}
    count = 0
    cpu = 0
    runners = []
    for line in output.splitlines():
        match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s+(.+)', line)
        if not match:
            continue
        try:
            arguments = shlex.split(match[2])
        except ValueError:
            continue
        if not arguments or Path(arguments[0]).name not in ('ollama', 'ollama_llama_server'):
            continue
        percent = finite(float(match[1]))
        if percent is None or percent > 1000000:
            continue
        count += 1
        cpu += percent
        if 'runner' in arguments[1:3] or Path(arguments[0]).name == 'ollama_llama_server':
            flags = {}
            for flag in ('--threads', '--threads-batch', '--parallel', '--ctx-size', '--batch-size'):
                if flag in arguments:
                    index = arguments.index(flag)
                    if index + 1 < len(arguments) and re.fullmatch(r'\d{1,5}', arguments[index + 1]):
                        flags[flag] = int(arguments[index + 1])
            runners.append(flags)
    return {'available': bool(count), 'processCount': count,
            'recentCpuPercentOneCoreUnits': round(cpu, 3), 'runnerOptions': runners}


def counter_delta(before, after, key):
    first, last = before.get(key), after.get(key)
    if integer(first) is None or integer(last) is None or last < first:
        return None
    return last - first


def run(project, *, reader=None, system=None):
    if (system or platform.system()) != 'Darwin':
        raise DiagnosticError('Questa diagnosi legge soltanto le misure di macOS.')
    verify_project(project)
    reader = reader or Reader()
    before = {'vm': vm_counters(reader.command('vm_before', ['/usr/bin/vm_stat'])),
              'thermal': thermal_limits(reader.command('thermal_before', ['/usr/bin/pmset', '-g', 'therm']))}
    hw = hardware(reader.command('hardware', ['/usr/sbin/sysctl', '-n', 'hw.physicalcpu', 'hw.logicalcpu', 'hw.memsize']))
    power = power_status(reader.command('power', ['/usr/bin/pmset', '-g', 'batt']))
    modes = low_power_modes(reader.command('low_power_modes', ['/usr/bin/pmset', '-g', 'custom']))
    version_data = reader.get('/api/version')
    version = version_data.get('version') if isinstance(version_data, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+.][A-Za-z0-9.-]+)?', version) or len(version) > 64:
        version = None
    model = selected_model(reader.get('/api/ps'))
    processes = ollama_processes(reader)
    cpu = cpu_usage(reader.command('cpu_usage', ['/usr/bin/top', '-l', '2', '-s', '1', '-n', '0', '-R', '-F']))
    load = load_average(reader.command('load_average', ['/usr/sbin/sysctl', '-n', 'vm.loadavg']))
    swap = swap_used_bytes(reader.command('swap_used', ['/usr/sbin/sysctl', '-n', 'vm.swapusage']))
    after = {'vm': vm_counters(reader.command('vm_after', ['/usr/bin/vm_stat'])),
             'thermal': thermal_limits(reader.command('thermal_after', ['/usr/bin/pmset', '-g', 'therm']))}
    elapsed = round((reader.clock() - reader.started) * 1000, 3)
    return {'schema': 1, 'mode': 'read_only_latency_resource_diagnostic',
            'modelInferenceRequests': 0, 'automaticRetries': 0, 'productionModified': False,
            'vaultRead': False, 'modelOptionsChanged': False, 'existingProcessesTerminated': False,
            'diagnosticReadBudgetSeconds': BUDGET_SECONDS, 'observationWindowMs': elapsed,
            'architecture': platform.machine(), 'hardware': hw, 'power': power,
            'lowPowerModeBySource': modes, 'ollamaVersion': version, 'loadedModels': model,
            'ollamaProcesses': processes, 'cpuUsageLastInterval': cpu, 'loadAverage1_5_15m': load,
            'swapUsedBytes': swap, 'before': before, 'after': after,
            'vmCounterDeltasPages': {key: counter_delta(before['vm'], after['vm'], key)
                                   for key in ('Swapins', 'Swapouts', 'Pageouts')},
            'unavailableQueries': reader.issues, 'performanceVerdict': 'not_measured',
            'pastBenchmarkCause': 'not_determined', 'qualityVerdict': 'not_evaluated',
            'notes': ['Snapshot attuale: non ricostruisce il carico o il limite CPU della serie precedente.',
                      'Limiti termici mancanti restano sconosciuti; non misura la temperatura in gradi.',
                      'Modelli caricati non significano inferenze concorrenti. CPU ps usa unità di un singolo core.',
                      'Nessun nome di altre applicazioni, argomento del modello, credenziale o testo personale nel rapporto.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path, nargs='?')
    parser.add_argument('--ollama-read', choices=('/api/version', '/api/ps'))
    args = parser.parse_args()
    if args.ollama_read:
        if args.project:
            parser.error('Il lettore interno non accetta un progetto.')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        value = Reader(opener=opener).get(args.ollama_read)
        print(json.dumps(value if value is not None else {'diagnosticError': 'unavailable'}))
        return 0 if value is not None else 1
    if args.project is None:
        parser.error('Occorre il percorso del progetto verificato.')
    try:
        project = args.project.expanduser().resolve(strict=True)
        print('Diagnosi breve in sola lettura: CPU, memoria e stato Ollama. Nessuna richiesta di generazione.')
        result = run(project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print('Diagnosi finita. Queste misure non certificano qualità o superamento del test di latenza.')
        return 0
    except (DiagnosticError, OSError, ValueError):
        print('Diagnosi interrotta: macOS o versione installata non corrispondono alla lettura prevista. Nessuna modifica.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Read-only resource evidence, unknown states, privacy and finite boundaries."""
import json
from pathlib import Path
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import latency_resource_diagnostic as probe
import web_type_latency_probe as comparison

ROOT = Path(__file__).resolve().parents[1]
VM = '''Mach Virtual Memory Statistics: (page size of 4096 bytes)
Pages free:                              1000.
Pages occupied by compressor:            500.
Swapins:                                    2.
Swapouts:                                   3.
Pageouts:                                   4.
'''
THERM = 'CPU_Speed_Limit = 75\nCPU_Scheduler_Limit = 100\nCPU_Available_CPUs = 16\n'
PS = ('0.2 /Applications/Ollama.app/Contents/Resources/ollama serve\n'
      '320.0 /Applications/Ollama.app/Contents/Resources/ollama runner --model '
      '/Users/private/path/secret --threads 8 --parallel 1 --ctx-size 4096 --batch-size 512\n'
      '1.0 /Users/private/other-app --token credential\n')
TOP = 'CPU usage: 99.0% user, 1.0% sys, 0.0% idle\nCPU usage: 10.0% user, 5.0% sys, 85.0% idle\n'


class Response:
    status = 200
    def __init__(self, body): self.body = body
    def read(self, n): return self.body[:n]
    def __enter__(self): return self
    def __exit__(self, *args): pass


class Opener:
    def __init__(self, responses): self.responses = iter(responses); self.calls = []
    def open(self, request, **kwargs):
        self.calls.append((request, kwargs))
        return next(self.responses)


class ResourceParserTests(unittest.TestCase):
    def test_hardware_and_load_keep_unknowns_unknown(self):
        self.assertEqual(probe.hardware('8\n16\n34359738368\n'),
                         {'physicalCores': 8, 'logicalCores': 16, 'memoryBytes': 34359738368})
        self.assertEqual(probe.load_average('{ 1.25 2.00 3.25 }'), [1.25, 2.0, 3.25])
        for text in (None, 'unsupported', '8\n16\n', '-1\n8\n1024\n'):
            self.assertIsNone(probe.hardware(text)['physicalCores'])
        for text in (None, '{ -1 0 0 }', '{ NaN 0 0 }'):
            self.assertIsNone(probe.load_average(text))

    def test_swap_units_and_vm_counter_deltas_are_exact_not_since_boot_activity(self):
        self.assertEqual(probe.swap_used_bytes('total = 1024.00M used = 1.50G free = 0.00M'), 1610612736)
        self.assertEqual(probe.vm_counters(VM)['pageSizeBytes'], 4096)
        before = probe.vm_counters(VM); after = probe.vm_counters(VM.replace(' 3.', ' 9.'))
        self.assertEqual(probe.counter_delta(before, after, 'Swapouts'), 6)
        self.assertIsNone(probe.counter_delta(after, before, 'Swapouts'))
        self.assertIsNone(probe.counter_delta({'Swapouts': True}, after, 'Swapouts'))
        self.assertIsNone(probe.swap_used_bytes('used = NaNM'))

    def test_thermal_queries_are_not_temperature_or_a_false_normal_state(self):
        self.assertEqual(probe.thermal_limits(THERM),
                         {'CPU_Speed_Limit': 75, 'CPU_Scheduler_Limit': 100, 'CPU_Available_CPUs': 16})
        for text in (None, 'No thermal warning level has been recorded', 'Thermal data unavailable'):
            self.assertTrue(all(v is None for v in probe.thermal_limits(text).values()))

    def test_only_power_fields_are_retained_and_missing_low_power_mode_is_unknown(self):
        text = "Now drawing from 'AC Power'\n -InternalBattery-0 (private-id) 81%; charging; time\n"
        self.assertEqual(probe.power_status(text), {'source': 'AC Power', 'batteryPercent': 81})
        settings = 'Battery Power:\n lowpowermode 1\n lidwake 1\nAC Power:\n lowpowermode 0\n'
        self.assertEqual(probe.low_power_modes(settings), {'AC Power': 0, 'Battery Power': 1, 'UPS Power': None})
        self.assertIsNone(probe.low_power_modes(None)['AC Power'])

    def test_cpu_uses_last_interval_and_rejects_non_numeric_or_impossible_values(self):
        self.assertEqual(probe.cpu_usage(TOP), {'userPercent': 10.0, 'systemPercent': 5.0, 'idlePercent': 85.0})
        for text in (None, 'CPU usage: 200% user, 0% sys, 0% idle', 'CPU usage: 10% user, 0% sys, 0% idle'):
            self.assertIsNone(probe.cpu_usage(text)['idlePercent'])

    def test_other_loaded_model_names_and_digest_paths_are_not_printed(self):
        data = {'models': [{'name': 'private-business-model', 'digest': 'secret'},
                           {'name': probe.MODEL, 'size': 100, 'size_vram': 0, 'context_length': 4096}]}
        result = probe.selected_model(data)
        self.assertEqual(result['loadedModelCount'], 2); self.assertTrue(result['expectedModelLoaded'])
        self.assertEqual(result['expectedModel'], {'size': 100, 'size_vram': 0, 'context_length': 4096})
        self.assertNotIn('private', json.dumps(result)); self.assertNotIn('secret', json.dumps(result))
        self.assertFalse(probe.selected_model({'models': []})['expectedModelLoaded'])
        self.assertIsNone(probe.selected_model(None)['expectedModelLoaded'])
        self.assertIsNone(probe.selected_model({'models': [True]})['loadedModelCount'])
        data['models'][1]['size_vram'] = True
        self.assertIsNone(probe.selected_model(data)['expectedModel']['size_vram'])


class ResourceBoundaryTests(unittest.TestCase):
    def test_allowlist_cannot_start_a_shell_change_power_settings_or_terminate_a_process(self):
        for command in (['/bin/sh', '-c', 'anything'], ['/usr/bin/pmset', '-a', 'lowpowermode', '0'],
                        ['/bin/kill', '123'], ['/bin/ps', '-p', '123;kill', '-o', 'pcpu=,command=']):
            self.assertFalse(probe.allowed_command(command))
        self.assertTrue(probe.allowed_command(['/bin/ps', '-p', '123,124', '-o', 'pcpu=,command=']))
        reader = probe.Reader(runner=lambda *a, **k: self.fail('unexpected execution'))
        with self.assertRaises(probe.DiagnosticError): reader.command('invalid', ['/bin/sh'])

    def test_local_get_only_never_generates_loads_or_unloads_models(self):
        opener = Opener([Response(b'{"version":"0.34.2"}'), Response(b'{"models":[]}')])
        reader = probe.Reader(opener=opener)
        self.assertEqual(reader.get('/api/version'), {'version': '0.34.2'})
        self.assertEqual(reader.get('/api/ps'), {'models': []})
        for request, kwargs in opener.calls:
            self.assertEqual(request.get_method(), 'GET'); self.assertIsNone(request.data)
            self.assertTrue(request.full_url.startswith('http://127.0.0.1:11434/'))
            self.assertLessEqual(kwargs['timeout'], 3)
        for path in ('/api/chat', '/api/generate', '/api/pull', '/api/ps?secret=1'):
            with self.assertRaises(probe.DiagnosticError): reader.get(path)
        self.assertEqual(len(opener.calls), 2)

    def test_proxy_and_redirects_are_disabled(self):
        handler = probe.NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, '', {}, 'http://elsewhere/'))
        with patch.object(probe.urllib.request, 'build_opener') as build, \
                patch.object(probe.sys, 'argv', ['diagnostic.py', '--ollama-read', '/api/ps']), \
                patch.object(probe.Reader, 'get', return_value={'models': []}), patch('builtins.print'):
            self.assertEqual(probe.main(), 0)
        self.assertEqual(build.call_args.args[0].proxies, {})

    def test_default_api_reads_have_an_owned_process_wall_deadline_and_no_shell(self):
        result = SimpleNamespace(returncode=0, stdout='{"models":[]}')
        with patch.object(probe.subprocess, 'run', return_value=result) as runner:
            reader = probe.Reader(runner=runner)
            self.assertEqual(reader.get('/api/ps'), {'models': []})
        self.assertEqual(runner.call_args.args[0][-2:], ['--ollama-read', '/api/ps'])
        self.assertEqual(Path(runner.call_args.args[0][1]), Path(probe.__file__).resolve())
        self.assertLessEqual(runner.call_args.kwargs['timeout'], 3)
        self.assertFalse(runner.call_args.kwargs.get('shell', False))
        with patch.object(probe.subprocess, 'run', side_effect=subprocess.TimeoutExpired('owned-api-reader', 3)) as runner:
            reader = probe.Reader(runner=runner)
            self.assertIsNone(reader.get('/api/ps'))
        self.assertEqual(runner.call_count, 1)

    def test_corrupt_oversized_duplicate_or_unavailable_api_data_remains_unknown(self):
        for body in (b'not json', b'[]', b'{"models":[],"models":[]}', b'x' * (probe.MAX_BYTES + 1)):
            with self.subTest(body=body[:30]):
                reader = probe.Reader(opener=Opener([Response(body)]))
                self.assertIsNone(reader.get('/api/ps'))
                self.assertEqual(len(reader.issues), 1)

    def test_command_timeouts_oversize_or_unsupported_values_are_not_reported_as_zero(self):
        for result in (SimpleNamespace(returncode=1, stdout='private error'),
                       SimpleNamespace(returncode=0, stdout='x' * (probe.MAX_BYTES + 1))):
            with patch.object(probe.subprocess, 'run', return_value=result) as runner:
                reader = probe.Reader(runner=runner)
                self.assertIsNone(reader.command('thermal', ['/usr/bin/pmset', '-g', 'therm']))
            self.assertFalse(runner.call_args.kwargs.get('shell', False))
            self.assertLessEqual(runner.call_args.kwargs['timeout'], 3)
            self.assertEqual(runner.call_args.kwargs['env']['LC_ALL'], 'C')
            self.assertNotIn('private error', json.dumps(reader.issues))
        with patch.object(probe.subprocess, 'run', side_effect=subprocess.TimeoutExpired('owned-query', 3)) as runner:
            reader = probe.Reader(runner=runner)
            self.assertIsNone(reader.command('vm', ['/usr/bin/vm_stat']))
        self.assertEqual(runner.call_count, 1)

    def test_global_budget_exhaustion_prevents_more_reads_without_wait_or_retry(self):
        clock = iter((0, 21, 22))
        runner = lambda *a, **k: self.fail('budget exhausted')
        opener = Opener([])
        reader = probe.Reader(runner=runner, opener=opener, clock=lambda: next(clock))
        self.assertIsNone(reader.command('vm', ['/usr/bin/vm_stat']))
        self.assertIsNone(reader.get('/api/ps'))
        self.assertEqual(opener.calls, [])

    def test_only_verified_ollama_processes_emit_numeric_options_no_paths_or_credentials(self):
        outputs = iter(('123\n124\n', None, PS))
        reader = SimpleNamespace(command=lambda *a: next(outputs))
        result = probe.ollama_processes(reader)
        self.assertEqual(result['processCount'], 2)
        self.assertEqual(result['recentCpuPercentOneCoreUnits'], 320.2)
        self.assertEqual(result['runnerOptions'], [{'--threads': 8, '--parallel': 1, '--ctx-size': 4096, '--batch-size': 512}])
        serialized = json.dumps(result)
        for private in ('credential', 'secret', '/Users/', 'other-app'):
            self.assertNotIn(private, serialized)

    def test_non_mac_or_hash_mismatch_prevents_all_system_queries(self):
        reader = SimpleNamespace(command=lambda *a: self.fail('unexpected query'))
        with self.assertRaises(probe.DiagnosticError): probe.run(ROOT, reader=reader, system='Linux')
        with patch.object(probe, 'verify_project', side_effect=probe.DiagnosticError('mismatch')):
            with self.assertRaises(probe.DiagnosticError): probe.run(ROOT, reader=reader, system='Darwin')
        self.assertEqual(probe.EXPECTED, comparison.EXPECTED)

    def test_complete_snapshot_does_not_certify_old_latency_or_quality_and_uses_two_gets(self):
        calls = []; gets = []
        def command(label, argv):
            self.assertTrue(probe.allowed_command(argv)); calls.append((label, argv))
            if argv[0].endswith('vm_stat'): return VM
            if argv[-1] == 'therm': return THERM
            if 'hw.physicalcpu' in argv: return '8\n16\n34359738368\n'
            if argv[0].endswith('top'): return TOP
            if argv[-1] == 'vm.loadavg': return '{ 1.25 2.00 3.25 }'
            if argv[-1] == 'vm.swapusage': return 'total = 1024.00M used = 0.00M free = 1024.00M'
            return None
        def get(path):
            gets.append(path)
            return {'version': '0.34.2'} if path.endswith('version') else {'models': []}
        reader = SimpleNamespace(command=command, get=get, issues=[], clock=lambda: 2, started=0)
        with patch.object(probe, 'verify_project') as verify:
            result = probe.run(ROOT, reader=reader, system='Darwin')
        verify.assert_called_once_with(ROOT)
        self.assertEqual(gets, ['/api/version', '/api/ps'])
        self.assertEqual(result['modelInferenceRequests'], 0); self.assertFalse(result['productionModified'])
        self.assertEqual(result['performanceVerdict'], 'not_measured')
        self.assertEqual(result['pastBenchmarkCause'], 'not_determined')
        self.assertEqual(result['qualityVerdict'], 'not_evaluated')
        self.assertEqual(result['observationWindowMs'], 2000)
        self.assertEqual(result['vmCounterDeltasPages']['Swapouts'], 0)
        self.assertEqual(sum(label == 'thermal_before' for label, _ in calls), 1)
        self.assertEqual(sum(label == 'thermal_after' for label, _ in calls), 1)


if __name__ == '__main__': unittest.main()

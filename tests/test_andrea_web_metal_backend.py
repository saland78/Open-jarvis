"""CPU/Metal adapter isolation, immutable evidence and finite lifecycle checks.

These tests do not claim the AMD GPU can run this model. That requires the
explicit runtime device, allocation and answer comparison on Andrea's Mac.
"""
import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import check_web_compact_v9 as check
import web_candidate_pipeline as pipeline
import web_metal_backend_probe as probe
import web_prompt_compaction_probe as previous
from test_andrea_web_capability_scope import page
from test_andrea_web_compact_integration import csv_page
from test_andrea_web_heading_latency import GOOD_CSV, GOOD_IO, GOOD_SUBPROCESS

ROOT = Path(__file__).resolve().parents[1]
TOKEN = 'a' * 64
ENDPOINT = 'http://127.0.0.1:12345'
DEVICE = {'id': 'MTL0', 'name': probe.GPU_NAME, 'totalMiB': 4096, 'freeMiB': 3500}
LOAD_LOG = ('llama_model_load: using device MTL0 (AMD Radeon Pro 5500M) (id) - 3500 MiB free\n'
            'load_tensors: offloaded 37/37 layers to GPU\n'
            'load_tensors:         MTL0 model buffer size = 2500.00 MiB\n')


class Response(io.BytesIO):
    status = 200


class Transport:
    def __init__(self, value=None, raw=None):
        self.raw = raw if raw is not None else json.dumps(value).encode()
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        return Response(self.raw)


def answer(engine, raw='{"claims":[]}', reason='stop'):
    message = {'role': 'assistant', 'content': raw}
    if engine == 'ollama_cpu':
        return {'done': True, 'done_reason': reason, 'message': message,
                'prompt_eval_count': 1000, 'prompt_eval_cached_count': 0,
                'prompt_eval_duration': 2000000000, 'eval_count': 12,
                'eval_duration': 1000000000, 'load_duration': 1000, 'total_duration': 3000000000}
    return {'choices': [{'index': 0, 'finish_reason': reason, 'message': message}],
            'usage': {'prompt_tokens': 1000, 'completion_tokens': 12},
            'timings': {'cache_n': 2, 'prompt_n': 998, 'prompt_ms': 1500,
                        'predicted_n': 12, 'predicted_ms': 1000}}


def row(index, engine, total=None):
    result = {'raw': '{"claims":[]}', 'completed': True, 'doneReason': 'stop',
              'totalClientMs': total if total is not None else (5000 if engine == 'ollama_cpu' else 3500),
              'transport': 'non_streaming_json_on_both_backends', 'nativeTimingErrorCode': None,
              'native': {'prefillMs': 2000 if engine == 'ollama_cpu' else 1200,
                         'generationMs': 1000 if engine == 'ollama_cpu' else 700,
                         'processedPromptTokens': 1000, 'cachedPromptTokens': 0}}
    return {'case': check.CASES[index]['id'], 'engine': engine,
            'sourceTextSha256': 'same', 'preparationSha256': 'same',
            'nativeSchemaSha256': 'same', 'modelSourceCharacters': 2000,
            'observerClosed': True, 'referenceResidency': {'expectedModelLoaded': True, 'sizeVram': 0},
            'result': result, 'checks': {'outcome': 'abstained' if index == 2 else 'accepted_pending_semantic_review',
                                      'claims': [{}] * (2, 1, 0)[index]}}


class RequestContractTests(unittest.TestCase):
    def test_exact_production_messages_schema_and_options_on_both_backends(self):
        for index, source in enumerate((page(), csv_page(), csv_page())):
            _, messages, schema, _ = pipeline.prepare(source, check.CASES[index]['question'])
            snapshot = copy.deepcopy((messages, schema))
            payloads = {}
            for engine in ('ollama_cpu', 'llama_metal'):
                transport = Transport(answer(engine))
                result = probe.completion_once(engine, messages, schema,
                    ENDPOINT if engine == 'llama_metal' else None,
                    TOKEN if engine == 'llama_metal' else None, transport)
                self.assertTrue(result['completed'])
                self.assertEqual(result['raw'], '{"claims":[]}')
                self.assertEqual(len(transport.calls), 1)
                request, timeout = transport.calls[0]
                payload = json.loads(request.data)
                self.assertEqual(timeout, 90)
                self.assertEqual(payload['messages'], messages)
                self.assertFalse(payload['stream'])
                payloads[engine] = payload
                if engine == 'llama_metal':
                    self.assertEqual(request.full_url, ENDPOINT + '/v1/chat/completions')
                    self.assertEqual(payload['response_format']['json_schema']['schema'], schema)
                    self.assertEqual(payload['response_format']['type'], 'json_schema')
                    self.assertEqual(request.get_header('Authorization'), 'Bearer ' + TOKEN)
                    self.assertEqual(payload['reasoning_effort'], 'none')
                    self.assertEqual(payload['chat_template_kwargs'], {'enable_thinking': False})
                    self.assertEqual(payload['temperature'], 0.4)
                    self.assertEqual(payload['max_tokens'], 512)
                else:
                    self.assertEqual(payload['format'], schema)
                    self.assertEqual(payload['options'], previous.request_options(512))
                    self.assertFalse(payload['think'])
                    self.assertIsNone(request.get_header('Authorization'))
            self.assertEqual((messages, schema), snapshot)
            self.assertGreater(schema['properties']['claims']['maxItems'], 0)
            self.assertNotIn('num_thread', payloads['ollama_cpu']['options'])

    def test_raw_whitespace_is_preserved_without_output_repair(self):
        raw = '  {"claims": []}  \n'
        for engine in ('ollama_cpu', 'llama_metal'):
            result = probe.completion_once(engine, [], {}, ENDPOINT, TOKEN, Transport(answer(engine, raw)))
            self.assertEqual(result['raw'], raw)

    def test_length_stop_not_complete_or_retried(self):
        for engine in ('ollama_cpu', 'llama_metal'):
            transport = Transport(answer(engine, '{"claims":[]}', 'length'))
            result = probe.completion_once(engine, [], {}, ENDPOINT, TOKEN, transport)
            self.assertFalse(result['completed'])
            self.assertEqual(len(transport.calls), 1)

    def test_tools_thoughts_oversized_content_or_multiple_choices_refuse(self):
        for field, value in [('tool_calls', [{}]), ('thinking', 'secret'), ('reasoning_content', 'thought'),
                             ('content', 'x' * 5001)]:
            frame = answer('llama_metal'); frame['choices'][0]['message'][field] = value
            transport = Transport(frame)
            with self.assertRaisesRegex(ValueError, 'model_message'):
                probe.completion_once('llama_metal', [], {}, ENDPOINT, TOKEN, transport)
            self.assertEqual(len(transport.calls), 1)
        frame = answer('llama_metal'); frame['choices'] *= 2
        with self.assertRaisesRegex(ValueError, 'choice'):
            probe.completion_once('llama_metal', [], {}, ENDPOINT, TOKEN, Transport(frame))

    def test_only_fixed_loopback_backend_endpoint_allowed(self):
        for endpoint in ('https://remote.test:12345', 'http://localhost:12345',
                         'http://127.0.0.1:12345/extra', 'http://127.0.0.1:80'):
            transport = Transport(answer('llama_metal'))
            with self.assertRaisesRegex(ValueError, 'endpoint'):
                probe.completion_once('llama_metal', [], {}, endpoint, TOKEN, transport)
            self.assertEqual(transport.calls, [])

    def test_duplicate_json_keys_and_oversized_wire_refuse(self):
        for raw in (b'{"choices":[],"choices":[]}', b'x' * (probe.MAX_BYTES + 1)):
            with self.assertRaises(ValueError):
                probe.json_request(ENDPOINT, transport=Transport(raw=raw))

    def test_llama_prompt_n_is_processed_not_total_input_tokens(self):
        metrics = probe.normalize_native('llama_metal', answer('llama_metal'))
        self.assertEqual(metrics['promptTokens'], 1000)
        self.assertEqual(metrics['processedPromptTokens'], 998)
        self.assertEqual(metrics['cachedPromptTokens'], 2)
        self.assertIsNone(metrics['loadMs'])
        self.assertIsNone(metrics['totalMs'])

    def test_ollama_counts_and_nan_invalid_no_false_timing_claim(self):
        for engine, field, value in [('ollama_cpu', 'prompt_eval_cached_count', None),
                                     ('llama_metal', 'prompt_ms', float('nan'))]:
            frame = answer(engine)
            if engine == 'llama_metal': frame['timings'][field] = value
            else: frame[field] = value
            result = probe.completion_once(engine, [], {}, ENDPOINT, TOKEN, Transport(frame))
            self.assertTrue(result['completed'])
            self.assertEqual(result['raw'], '{"claims":[]}')
            self.assertEqual(result['native'], {})
            self.assertIsNotNone(result['nativeTimingErrorCode'])

    def test_mismatched_usage_keeps_raw_but_cannot_pass_timing_gate(self):
        frame = answer('llama_metal'); frame['usage']['prompt_tokens'] = 999
        result = probe.completion_once('llama_metal', [], {}, ENDPOINT, TOKEN, Transport(frame))
        self.assertEqual(result['raw'], '{"claims":[]}')
        self.assertEqual(result['nativeTimingErrorCode'], 'llama_usage_not_aligned_with_timings')


class SourceAndValidationTests(unittest.TestCase):
    def test_csv_condition_and_unknown_references_still_guarded(self):
        source = csv_page()
        bank, _, _, selection = pipeline.prepare(source, check.CASES[1]['question'])
        ref = selection['outputPolicy']['sourceRuleRefs'][0]
        good = json.dumps({'claims': [{'passage': ref, 'text': GOOD_CSV}]})
        self.assertEqual(pipeline.validate(good, bank, True, source, selection)['outcome'],
                         'accepted_pending_semantic_review')
        for bad in ('csv.reader converte automaticamente ogni campo in float.', 'Una frase incomple'):
            raw = json.dumps({'claims': [{'passage': ref, 'text': bad}]})
            self.assertEqual(pipeline.validate(raw, bank, True, source, selection)['outcome'], 'rejected')
        raw = json.dumps({'claims': [{'passage': 999, 'text': GOOD_CSV}]})
        self.assertEqual(pipeline.validate(raw, bank, True, source, selection)['outcome'], 'rejected')

    def test_empty_missing_answer_is_inferred_not_schema_forced(self):
        source = csv_page()
        bank, _, schema, selection = pipeline.prepare(source, check.CASES[2]['question'])
        self.assertGreater(schema['properties']['claims']['maxItems'], 0)
        checked = pipeline.validate('{"claims":[]}', bank, True, source, selection)
        self.assertEqual(probe.control_audit(checked, selection)['outcome'], 'abstained')

    def test_observed_control_added_to_execution_remains_rejected_without_reanchoring(self):
        archive = json.loads((ROOT / 'docs/andrea/web-static-prompt-mac-2026-10-07.json').read_text())
        first = archive['originalAutomaticReport']['rows'][0]
        original = first['originalChecks']
        snapshot = copy.deepcopy(original)
        checked = probe.control_audit(original, {'sourceCapabilityScopePolicy': {'active': True}})
        self.assertEqual(checked['reason'], 'control_not_in_own_operation_passage')
        self.assertEqual(checked['claims'], [])
        self.assertEqual(checked['details']['quote'], original['claims'][1]['quote'])
        self.assertEqual(original, snapshot)

    def test_source_helpers_are_identical_to_already_tested_production_probe(self):
        def defs(module):
            return {n.name: ast.dump(n) for n in ast.parse(Path(module.__file__).read_text()).body
                    if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        old, new = defs(previous), defs(probe)
        for name in ('unique_pairs', 'digest', 'NoRedirect', 'opener', 'load_project',
                     'isolated_messages', 'thermal_sample', 'cpu_residency', 'Observer', 'control_audit'):
            self.assertEqual(old[name], new[name], name)

    def test_worker_no_contract_rewrite_for_each_backend(self):
        source = {**csv_page(), 'pageId': 'synthetic_case', 'sourceId': 'W1', 'modelUsed': False}
        before = pipeline.prepare(source, check.CASES[1]['question'])
        ref = before[3]['outputPolicy']['sourceRuleRefs'][0]
        raw = json.dumps({'claims': [{'passage': ref, 'text': GOOD_CSV}]})
        result = {'raw': raw, 'completed': True}
        proofs = []
        for engine in ('ollama_cpu', 'llama_metal'):
            payload = {'operation': 'model', 'case': 1, 'page': source, 'engine': engine,
                       'marker': 'a' * 32, 'endpoint': ENDPOINT, 'token': TOKEN}
            with patch.object(probe, 'load_project', return_value=(check, pipeline)), \
                    patch.object(probe, 'completion_once', return_value=result) as call, \
                    patch.object(probe, 'cpu_residency', return_value={}):
                row_value = probe.worker(Path('/project'), payload)
            self.assertEqual(call.call_args.args[1], probe.isolated_messages(before[1], 'a' * 32))
            self.assertEqual(call.call_args.args[2], before[2])
            self.assertEqual(row_value['checks']['claims'][0]['text'], GOOD_CSV)
            proofs.append(row_value['preparationSha256'])
        self.assertEqual(proofs[0], proofs[1])


class WeightIdentityTests(unittest.TestCase):
    def blob(self, folder):
        data = b'GGUF' + b'x' * 2048
        sha = hashlib.sha256(data).hexdigest()
        parent = Path(folder) / 'models/blobs'; parent.mkdir(parents=True)
        file = parent / ('sha256-' + sha); file.write_bytes(data)
        show = {'details': {'format': 'gguf', 'family': 'qwen3', 'parameter_size': '4.0B',
                            'quantization_level': 'Q4_K_M'},
                'modelfile': '# Model metadata\nFROM "' + str(file) + '"\n', 'template': 'public template'}
        return file, show

    def test_reuses_same_existing_model_and_confirms_content_hash(self):
        with tempfile.TemporaryDirectory(prefix='engine trial ') as folder:
            file, show = self.blob(folder)
            identity = probe.model_identity(show)
            result = probe.verify_weights(identity)
            self.assertEqual(result['sha256'], file.name[7:])
            self.assertEqual(identity['path'], str(file.resolve()))
            self.assertEqual(result['bytes'], file.stat().st_size)

    def test_modified_gguf_refused_not_replaced_or_downloaded(self):
        with tempfile.TemporaryDirectory() as folder:
            file, show = self.blob(folder)
            identity = probe.model_identity(show)
            file.write_bytes(b'GGUF' + b'z' * 2048)
            with self.assertRaisesRegex(ValueError, 'mismatch'): probe.verify_weights(identity)

    def test_non_gguf_unknown_quantization_remote_from_or_symlink_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            file, show = self.blob(folder)
            for modelfile in ('FROM https://example.test/model.gguf', 'FROM relative.gguf',
                              'FROM /a\nFROM /b', 'FROM "' + str(file) + '" extra'):
                bad = {**show, 'modelfile': modelfile}
                with self.assertRaises(ValueError): probe.model_identity(bad)
            bad = copy.deepcopy(show); bad['details']['quantization_level'] = 'F16'
            with self.assertRaises(ValueError): probe.model_identity(bad)
            target = file.with_name('sha256-' + 'a' * 64); target.symlink_to(file)
            bad = {**show, 'modelfile': 'FROM ' + str(target)}
            with self.assertRaises(ValueError): probe.model_identity(bad)
            file.write_bytes(b'BAD!' + b'x' * 2048)
            with self.assertRaisesRegex(ValueError, 'not_gguf'): probe.model_identity(show)


class BuildAndDeviceTests(unittest.TestCase):
    def test_exact_pinned_upstream_version_format_and_identity(self):
        line = 'version: 0.6.0 (build 11461, commit ' + probe.LLAMA_COMMIT + ')\nbuilt with Clang for Darwin x86_64\n'
        version = probe.verified_build_version(line)
        self.assertEqual(version, {'semanticVersion': '0.6.0', 'build': 11461, 'commit': probe.LLAMA_COMMIT})
        for wrong in (line.replace('11461', '11460'), line.replace(probe.LLAMA_COMMIT, 'a'*40),
                      'version: 11461 ('+probe.LLAMA_COMMIT[:7]+')'):
            with self.assertRaisesRegex(ValueError, 'version_mismatch'): probe.verified_build_version(wrong)

    def test_build_enables_metal_without_extra_model_or_ui_downloads(self):
        args = probe.configure_args(Path('/isolated/source'), Path('/isolated/build'))
        for setting in ('-DGGML_METAL=ON', '-DGGML_METAL_EMBED_LIBRARY=ON',
                        '-DCMAKE_OSX_ARCHITECTURES=x86_64', '-DLLAMA_BUILD_UI=OFF',
                        '-DLLAMA_USE_PREBUILT_UI=OFF', '-DLLAMA_OPENSSL=OFF'):
            self.assertIn(setting, args)
        self.assertIn('-DCMAKE_EXE_LINKER_FLAGS=-framework CoreGraphics', args)
        self.assertNotIn('install', args)
        self.assertEqual(len(probe.LLAMA_COMMIT), 40)
        self.assertTrue(probe.LLAMA_REPOSITORY.startswith('https://github.com/ggml-org/'))

    def test_device_detected_from_actual_native_inventory_not_hardware_name_alone(self):
        text = 'Available devices:\n  MTL0: AMD Radeon Pro 5500M (4096 MiB, 3500 MiB free)\n'
        self.assertEqual(probe.selected_device(text), DEVICE)
        for value in ('AMD Radeon Pro 5500M', text.replace('5500M', '5300M'),
                      text.replace('MTL0', 'CPU'), text + text):
            with self.assertRaisesRegex(ValueError, 'no_inference'): probe.selected_device(value)

    def test_gpu_loading_requires_identity_layers_and_nonzero_gpu_buffer(self):
        proof = probe.offload_proof(LOAD_LOG, DEVICE)
        self.assertTrue(proof['gpuOffloadProven'])
        self.assertTrue(proof['fullOffload'])
        for log in ('', LOAD_LOG.replace('37/37', '0/37'), LOAD_LOG.replace('5500M', '5300M'),
                    LOAD_LOG.replace('2500.00', '0.00'), LOAD_LOG.replace('MTL0 model', 'CPU model')):
            with self.assertRaisesRegex(ValueError, 'not_proven'): probe.offload_proof(log, DEVICE)

    def test_fit_estimation_repeats_do_not_falsely_claim_final_full_offload(self):
        log = LOAD_LOG + LOAD_LOG.replace('37/37', '25/37').replace('2500.00', '1500.00')
        proof = probe.offload_proof(log, DEVICE)
        self.assertFalse(proof['fullOffload'])
        self.assertEqual(proof['offloadedLayers'], 25)
        self.assertEqual(proof['modelGpuBufferMiB'], 1500)

    def test_native_private_and_mapped_model_allocations_are_counted(self):
        log = LOAD_LOG.replace('MTL0 model', 'MTL0_Private model')
        log += '0.05.100 I load_tensors: MTL0_Mapped model buffer size = 100.00 MiB\n'
        proof = probe.offload_proof(log, DEVICE)
        self.assertEqual(proof['modelGpuBufferMiB'], 2600)
        self.assertEqual([item['name'] for item in proof['modelGpuBufferAllocations']],
                         ['MTL0_Private', 'MTL0_Mapped'])

    def test_final_load_cannot_borrow_allocation_from_a_fit_estimate(self):
        for final in ('load_tensors: offloaded 25/37 layers to GPU\n',
                      'load_tensors: offloaded 25/37 layers to GPU\n'
                      'load_tensors: MTL0_Private model buffer size = 0.00 MiB\n',
                      'load_tensors: offloaded 25/37 layers to GPU\n'
                      'load_tensors: MTL1_Private model buffer size = 1500.00 MiB\n'):
            with self.subTest(final=final), self.assertRaisesRegex(ValueError, 'not_proven'):
                probe.offload_proof(LOAD_LOG + final, DEVICE)

    def test_private_buffer_without_matching_gpu_or_layers_is_rejected(self):
        log = LOAD_LOG.replace('MTL0 model', 'MTL0_Private model')
        for wrong in (log.replace('37/37', '0/37'), log.replace('5500M', '5300M'),
                      log.replace('MTL0_Private', 'MTL1_Private'),
                      log.replace('MTL0_Private', 'MTL0_Private_Other')):
            with self.subTest(wrong=wrong), self.assertRaisesRegex(ValueError, 'not_proven'):
                probe.offload_proof(wrong, DEVICE)

    def test_child_override_removal_does_not_modify_user_environment(self):
        values = {'PATH': '/usr/bin', 'LLAMA_ARG_DEVICE': 'CPU', 'GGML_METAL_DEVICES': '2',
                  'GIT_CONFIG_COUNT': '1', 'HF_UI_VERSION': 'external'}
        with patch.dict(os.environ, values, clear=True):
            before = dict(os.environ); env = probe.clean_child_env()
            self.assertEqual(dict(os.environ), before)
        for key in ('LLAMA_ARG_DEVICE', 'GGML_METAL_DEVICES', 'GIT_CONFIG_COUNT', 'HF_UI_VERSION'):
            self.assertNotIn(key, env)
        self.assertEqual(env['GIT_CONFIG_GLOBAL'], '/dev/null')

    def test_runtime_explicit_offload_context_and_zero_warmup(self):
        args = probe.server_args('/binary', '/existing/model', 'MTL0', 12345, TOKEN)
        for flag, value in (('--device', 'MTL0'), ('--ctx-size', '4096'), ('--parallel', '1'),
                            ('--flash-attn', 'off'), ('--reasoning', 'off'), ('--log-verbosity', '4')):
            self.assertEqual(args[args.index(flag) + 1], value)
        for flag in ('--no-warmup', '--no-cache-prompt', '--no-webui'):
            self.assertIn(flag, args)
        self.assertNotIn('--hf-repo', args)
        self.assertEqual(args[args.index('--host') + 1], '127.0.0.1')

    def test_wrong_device_or_api_token_refused_before_spawn(self):
        for device, port, token in [('CPU', 12345, TOKEN), ('MTL0', 80, TOKEN), ('MTL0', 12345, 'bad')]:
            with self.assertRaises(ValueError): probe.server_args('/binary', '/model', device, port, token)

    def test_missing_tools_do_not_install_tools_or_make_requests(self):
        with patch.object(probe.platform, 'system', return_value='Darwin'), \
                patch.object(probe.platform, 'machine', return_value='x86_64'), \
                patch.object(probe.shutil, 'which', return_value=None), \
                patch.object(probe, 'owned_worker') as worker:
            with self.assertRaisesRegex(ValueError, 'tools_missing'): probe.run(Path('/project'))
        worker.assert_not_called()

    def test_verified_amd_failure_cannot_fall_back_to_cpu_or_run_models(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p / 'source').mkdir()
            (p / 'build/bin').mkdir(parents=True)
            binary = p / 'build/bin/llama-server'; binary.write_bytes(b'fake'); binary.chmod(0o700)
            (p / 'build/CMakeCache.txt').write_text('GGML_METAL:BOOL=ON\nGGML_METAL_EMBED_LIBRARY:BOOL=ON\nGGML_ACCELERATE:BOOL=ON\n')
            def stage(args, work, timeout, name, emit):
                content = {'git-commit': probe.LLAMA_COMMIT, 'git-tree': probe.LLAMA_TREE,
                           'llama-version': 'version: 0.6.0 (build 11461, commit ' + probe.LLAMA_COMMIT + ')',
                           'metal-devices': '  MTL0: Intel UHD Graphics 630 (1536 MiB, 1000 MiB free)'}
                (work / (name + '.log')).write_text(content.get(name, ''))
                return {'stage': name}
            with patch.object(probe, 'logged_command', side_effect=stage) as calls:
                with self.assertRaisesRegex(ValueError, 'radeon_not_exposed'): probe.build_engine(p)
            self.assertTrue(all('install' not in str(call.args[0]) for call in calls.call_args_list))


class ReusedBuildTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.home = Path(self.workspace.name)
        self.previous = self.home / '.openjarvis-andrea/local-engines/llama-metal-b11461-existing'
        self.source = self.previous / 'source'
        (self.source / '.git').mkdir(parents=True)
        self.binary = self.previous / 'build/bin/llama-server'
        self.binary.parent.mkdir(parents=True)
        self.binary.write_bytes(b'verified original trial binary')
        self.binary.chmod(0o700)
        self.cache = self.previous / 'build/CMakeCache.txt'
        self.cache.write_text('GGML_METAL:BOOL=ON\nGGML_METAL_EMBED_LIBRARY:BOOL=ON\n'
                              'GGML_ACCELERATE:BOOL=ON\nCMAKE_OSX_ARCHITECTURES:STRING=x86_64\n')
        self.receipt = {'sourceCommit': probe.LLAMA_COMMIT, 'sourceTree': probe.LLAMA_TREE,
                        'sourceModified': False, 'compilationIsNotModelInference': True,
                        'builtServerSha256': hashlib.sha256(self.binary.read_bytes()).hexdigest(),
                        'nativeVersion': {'semanticVersion': '0.6.0', 'build': probe.LLAMA_BUILD,
                                          'commit': probe.LLAMA_COMMIT},
                        'device': DEVICE, 'stages': [{'stage': 'original-build'}]}
        self.receipt_file = self.previous / 'build-receipt.json'
        self.receipt_file.write_text(json.dumps(self.receipt))
        self.output = self.home / 'new-trial'; self.output.mkdir()
        self.stage_text = {
            'reuse-git-commit': probe.LLAMA_COMMIT, 'reuse-git-tree': probe.LLAMA_TREE,
            'reuse-git-clean': '',
            'reuse-llama-version': 'version: 0.6.0 (build 11461, commit ' + probe.LLAMA_COMMIT + ')\n',
            'reuse-metal-devices': 'Available devices:\n  MTL0: AMD Radeon Pro 5500M (4096 MiB, 3500 MiB free)\n'}

    def stage(self, args, folder, timeout, name, emit):
        (folder / (name + '.log')).write_text(self.stage_text[name])
        return {'stage': name}

    def run_reuse(self):
        with patch.object(probe.Path, 'home', return_value=self.home), \
                patch.object(probe, 'logged_command', side_effect=self.stage) as stages:
            result = probe.reuse_engine(self.previous, self.output)
            return result, stages.call_args_list

    def test_reuses_verified_binary_without_fetch_compile_or_old_log_overwrite(self):
        old_log = self.previous / 'owned-server.log'; old_log.write_text('retained failed initialization')
        (binary, proof), calls = self.run_reuse()
        self.assertEqual(binary, self.binary)
        self.assertTrue(proof['reusedBinaryHashVerified'])
        self.assertFalse(proof['compilationPerformedThisRun'])
        self.assertEqual(proof['reusedBuildFrom'], str(self.previous))
        self.assertEqual(len(calls), 5)
        self.assertTrue(all('cmake' not in str(call.args[0]) and 'fetch' not in call.args[0]
                            and 'install' not in call.args[0] for call in calls))
        self.assertEqual(old_log.read_text(), 'retained failed initialization')
        self.assertEqual(json.loads(self.receipt_file.read_text()), self.receipt)
        self.assertTrue((self.output / 'build-receipt.json').is_file())

    def test_changed_binary_refused_before_execution(self):
        self.binary.write_bytes(b'changed executable')
        with patch.object(probe, 'logged_command') as stages, \
                self.assertRaisesRegex(ValueError, 'binary_hash_mismatch'):
            self.run_reuse()
        stages.assert_not_called()

    def test_receipt_commit_tree_and_original_build_attestation_required(self):
        for key, value in [('sourceCommit', '0' * 40), ('sourceTree', '0' * 40),
                           ('sourceModified', True), ('compilationIsNotModelInference', False)]:
            self.receipt_file.write_text(json.dumps({**self.receipt, key: value}))
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'receipt_identity'):
                self.run_reuse()

    def test_cpu_build_or_wrong_architecture_refused(self):
        original = self.cache.read_text()
        for wrong in (original.replace('GGML_METAL:BOOL=ON', 'GGML_METAL:BOOL=OFF'),
                      original.replace('x86_64', 'arm64')):
            self.cache.write_text(wrong)
            with self.subTest(wrong=wrong), self.assertRaisesRegex(ValueError, 'build_flag|architecture'):
                self.run_reuse()

    def test_binary_symlink_refused(self):
        actual = self.binary.with_name('different-binary'); self.binary.rename(actual)
        self.binary.symlink_to(actual)
        with self.assertRaisesRegex(ValueError, 'contains_symlink'):
            self.run_reuse()

    def test_untyped_cmake_cli_architecture_is_still_verified(self):
        self.cache.write_text(self.cache.read_text().replace('ARCHITECTURES:STRING=',
                                                             'ARCHITECTURES:UNINITIALIZED='))
        (_, proof), _ = self.run_reuse()
        self.assertTrue(proof['reusedBinaryHashVerified'])

    def test_receipt_symlink_refused(self):
        actual = self.receipt_file.with_name('different-receipt.json'); self.receipt_file.rename(actual)
        self.receipt_file.symlink_to(actual)
        with self.assertRaisesRegex(ValueError, 'contains_symlink'):
            self.run_reuse()

    def test_changed_checkout_refused(self):
        for stage, wrong in [('reuse-git-commit', '0' * 40), ('reuse-git-tree', '0' * 40),
                             ('reuse-git-clean', ' M src/llama.cpp\n')]:
            original = dict(self.stage_text); self.stage_text[stage] = wrong
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, 'checkout_identity'):
                self.run_reuse()
            self.stage_text = original

    def test_unconfirmed_native_version_or_radeon_refused(self):
        for stage, wrong in [('reuse-llama-version', self.stage_text['reuse-llama-version'].replace('11461', '1')),
                             ('reuse-metal-devices', self.stage_text['reuse-metal-devices'].replace('5500M', '5300M'))]:
            original = dict(self.stage_text); self.stage_text[stage] = wrong
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, 'version_mismatch|radeon_not'):
                self.run_reuse()
            self.stage_text = original

    def test_arbitrary_folder_outside_original_trial_location_refused(self):
        with patch.object(probe.Path, 'home', return_value=self.home), \
                self.assertRaisesRegex(ValueError, 'original_trial_folder'):
            probe.reuse_engine(self.home, self.output)


class LifecycleTests(unittest.TestCase):
    def test_authenticated_model_readiness_proves_context_and_gpu_before_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            server = probe.OwnedMetalServer('/binary', {'path': '/existing/gguf'}, DEVICE, Path(folder))
            child = SimpleNamespace(returncode=None)
            child.poll = lambda: child.returncode
            props = {'total_slots': 1, 'model_path': '/existing/gguf', 'chat_template': 'native template',
                     'default_generation_settings': {'n_ctx': 4096, 'params': {'top_k': 40, 'min_p': 0.05}}}
            def spawn(*args, **kwargs):
                kwargs['stdout'].write(LOAD_LOG.encode()); kwargs['stdout'].flush()
                return child
            with patch.object(probe.subprocess, 'Popen', side_effect=spawn) as process, \
                    patch.object(probe, 'json_request', return_value=props) as read, \
                    patch.object(probe, 'stop_owned_group', side_effect=lambda c: setattr(c, 'returncode', 0)) as cleanup:
                with server:
                    self.assertTrue(server.proof['gpuOffloadProven'])
                    self.assertEqual(server.proof['contextPerSlot'], 4096)
                    self.assertTrue(server.proof['warmupInferenceDisabled'])
                    self.assertEqual(server.proof['nativeDefaultSamplerFields'], {'top_k': 40, 'min_p': 0.05})
                cleanup.assert_called_once_with(child)
            self.assertTrue(server.closed)
            self.assertTrue(process.call_args.kwargs['start_new_session'])
            self.assertEqual(read.call_args.kwargs['token'], server.token)
            self.assertTrue(read.call_args.args[0].endswith('/props'))

    def test_fit_cannot_silently_shrink_context_or_load_another_model(self):
        for field, value in [('n_ctx', 2048), ('model_path', '/another/model')]:
            with tempfile.TemporaryDirectory() as folder:
                server = probe.OwnedMetalServer('/binary', {'path': '/existing/gguf'}, DEVICE, Path(folder))
                child = SimpleNamespace(returncode=None); child.poll = lambda: child.returncode
                props = {'total_slots': 1, 'model_path': '/existing/gguf', 'chat_template': 'template',
                         'default_generation_settings': {'n_ctx': 4096}}
                if field == 'n_ctx': props['default_generation_settings'][field] = value
                else: props[field] = value
                with patch.object(probe.subprocess, 'Popen', return_value=child), \
                        patch.object(probe, 'json_request', return_value=props), \
                        patch.object(probe, 'stop_owned_group', side_effect=lambda c: setattr(c, 'returncode', 0)) as cleanup:
                    with self.assertRaisesRegex(ValueError, 'context_or_model_identity'):
                        server.__enter__()
                cleanup.assert_called_once_with(child)
                self.assertTrue(server.closed)
                self.assertTrue(server.handle.closed)

    def test_owned_model_worker_deadline_kills_its_child_and_closes_observer(self):
        child = SimpleNamespace(communicate=Mock(side_effect=[subprocess.TimeoutExpired('owned', 1), (b'', b'')]),
                                poll=Mock(return_value=None), kill=Mock())
        observer = SimpleNamespace(start=Mock(), close=Mock(return_value=True), rows=[])
        with patch.object(probe.subprocess, 'Popen', return_value=child), \
                patch.object(probe, 'Observer', return_value=observer):
            with self.assertRaisesRegex(ValueError, 'deadline'): probe.owned_worker(Path('/project'), {}, 1, True)
        child.kill.assert_called_once(); observer.close.assert_called_once()

    def test_worker_diagnostic_code_is_reported_without_payload_or_secret(self):
        child = SimpleNamespace(communicate=Mock(return_value=(b'', b'Prova fermata: invalid_llama_choice. No retry.')),
                                poll=Mock(return_value=1), returncode=1)
        with patch.object(probe.subprocess, 'Popen', return_value=child):
            with self.assertRaisesRegex(ValueError, '^invalid_llama_choice$'):
                probe.owned_worker(Path('/project'), {'token': TOKEN}, 1)

    def test_build_deadline_terminates_only_new_session_process(self):
        child = SimpleNamespace(wait=Mock(side_effect=subprocess.TimeoutExpired('cmake', 1)),
                                poll=Mock(return_value=None), returncode=None)
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(probe.subprocess, 'Popen', return_value=child) as spawn, \
                patch.object(probe.time, 'monotonic', side_effect=[0, 0, 30, 31]), \
                patch.object(probe, 'stop_owned_group') as cleanup:
            with self.assertRaisesRegex(ValueError, 'deadline'):
                probe.logged_command(['cmake', '--build', '/owned'], Path(folder), 20, 'build', lambda *a, **k: None)
        self.assertTrue(spawn.call_args.kwargs['start_new_session'])
        cleanup.assert_called_once_with(child)

    def test_server_close_is_idempotent_and_does_not_signal_exited_process(self):
        server = probe.OwnedMetalServer('/binary', {}, DEVICE, Path('/folder'))
        server.child = SimpleNamespace(poll=Mock(return_value=0))
        server.handle = Mock()
        with patch.object(probe, 'stop_owned_group') as cleanup:
            server.close(); server.close()
        cleanup.assert_not_called(); server.handle.close.assert_called_once()

    def test_stage_failure_closes_only_owned_server(self):
        with tempfile.TemporaryDirectory() as folder:
            server = probe.OwnedMetalServer('/binary', {'path': '/model'}, DEVICE, Path(folder))
            child = SimpleNamespace(poll=Mock(side_effect=[1, 1, 1]))
            with patch.object(probe.subprocess, 'Popen', return_value=child), \
                    patch.object(probe, 'stop_owned_group') as cleanup:
                with self.assertRaisesRegex(ValueError, 'start_failed'): server.__enter__()
            self.assertTrue(server.closed)
            self.assertTrue(server.handle.closed)
            cleanup.assert_not_called()


class ComparisonTests(unittest.TestCase):
    def rows(self): return [row(i, e) for i, e in probe.ORDER]

    def compare(self, rows): return probe.comparison(rows, {'gpuOffloadProven': True}, True)

    def test_number_gates_never_become_semantic_approval_or_installation(self):
        result = self.compare(self.rows())
        self.assertTrue(result['numericGatesMet'])
        self.assertTrue(result['candidateTechnicalShapesMet'])
        self.assertEqual(result['qualityVerdict'], 'pending_review')
        self.assertFalse(result['integrationAllowed'])
        self.assertEqual(result['firstVisibleResponseLatency'], 'not_measured')
        self.assertTrue(result['backendIncludesTemplateAndSamplerDifferences'])

    def test_fast_empty_positive_response_cannot_pass(self):
        rows = self.rows(); rows[1]['checks'] = {'outcome': 'abstained', 'claims': []}
        self.assertEqual(self.compare(rows)['decision'], 'do_not_adopt')

    def test_rejection_or_unrelated_missing_answer_blocks_adoption(self):
        for index, checked in [(1, {'outcome': 'rejected', 'claims': []}),
                               (5, {'outcome': 'accepted_pending_semantic_review', 'claims': [{}]})]:
            rows = self.rows(); rows[index]['checks'] = checked
            self.assertEqual(self.compare(rows)['decision'], 'do_not_adopt')

    def test_input_schema_or_order_difference_prevents_comparison(self):
        for change in ('sourceTextSha256', 'nativeSchemaSha256', 'preparationSha256', 'order'):
            rows = self.rows()
            if change == 'order': rows.reverse()
            else: rows[1][change] = 'different'
            self.assertFalse(self.compare(rows)['numericGatesMet'])

    def test_20_percent_both_positive_cases_and_no_missing_case_regression_required(self):
        for index, total in [(1, 4100), (2, 4100), (5, 5300)]:
            rows = self.rows(); rows[index]['result']['totalClientMs'] = total
            self.assertFalse(self.compare(rows)['numericGatesMet'])

    def test_no_gpu_wrong_weights_warm_cache_or_reference_gpu_disqualifies_timings(self):
        rows = self.rows()
        self.assertFalse(probe.comparison(rows, {'gpuOffloadProven': False}, True)['numericGatesMet'])
        self.assertFalse(probe.comparison(rows, {'gpuOffloadProven': True}, False)['numericGatesMet'])
        rows[1]['result']['native']['cachedPromptTokens'] = 20
        self.assertFalse(self.compare(rows)['numericGatesMet'])
        rows = self.rows(); rows[0]['referenceResidency']['sizeVram'] = 100
        self.assertFalse(self.compare(rows)['numericGatesMet'])

    def test_apparent_gain_only_from_cpu_loading_does_not_pass(self):
        rows = self.rows()
        rows[1]['result']['native']['prefillMs'] = 2000
        rows[1]['result']['native']['generationMs'] = 1000
        result = self.compare(rows)
        self.assertEqual(result['pairs'][0]['clientTotalGainPercent'], 30)
        self.assertEqual(result['pairs'][0]['nativePrefillAndGenerationGainPercent'], 0)
        self.assertFalse(result['numericGatesMet'])
        self.assertTrue(result['coldStartFairnessRequiresApplicationCheckBeforeIntegration'])


class FiniteRunTests(unittest.TestCase):
    def test_exact_six_model_calls_two_public_reads_owned_server_cleanup_and_no_install(self):
        self.check_run(None)

    def test_existing_build_reuse_keeps_six_calls_without_compiling(self):
        self.check_run(Path('/existing/trial'))

    def check_run(self, reuse_folder):
        with tempfile.TemporaryDirectory() as folder:
            class Server:
                url, token = ENDPOINT, TOKEN
                proof = {'gpuOffloadProven': True}
                closed = False
                def __enter__(self): return self
                def __exit__(self, *args): self.closed = True
            server = Server(); calls = []
            def worker(project, payload, timeout, observe=False):
                calls.append((payload['operation'], payload.get('engine')))
                if payload['operation'] == 'metadata':
                    return {'identity': {'path': '/existing/gguf', 'ollamaTemplateSha256': 'template'}}, [], True
                if payload['operation'] == 'hash':
                    return {'signature': [1, 2, 3, 4, 5], 'sha256': 'model', 'bytes': 3}, [], True
                if payload['operation'] == 'read':
                    return page() if payload['case'] == 0 else csv_page(), [], True
                return row(payload['case'], payload['engine']), [], True
            with patch.object(probe.platform, 'system', return_value='Darwin'), \
                    patch.object(probe.platform, 'machine', return_value='x86_64'), \
                    patch.object(probe.shutil, 'which', return_value='/tool'), \
                    patch.object(probe, 'load_project', return_value=(check, pipeline)), \
                    patch.object(probe, 'owned_worker', side_effect=worker), \
                    patch.object(probe, 'file_signature', return_value=(1, 2, 3, 4, 5)), \
                    patch.object(probe, 'create_trial_folder', return_value=Path(folder)), \
                    patch.object(probe, 'build_engine', return_value=('/binary', {'device': DEVICE})) as fresh_build, \
                    patch.object(probe, 'reuse_engine', return_value=('/binary', {'device': DEVICE})) as reused_build, \
                    patch.object(probe, 'OwnedMetalServer', return_value=server):
                report = probe.run(Path('/project'), lambda *a, **k: None, reuse_folder)
            if reuse_folder is None:
                fresh_build.assert_called_once(); reused_build.assert_not_called()
            else:
                fresh_build.assert_not_called(); reused_build.assert_called_once()
            self.assertEqual(report['existingBuildReused'], reuse_folder is not None)
            self.assertEqual(report['isolatedRuntimeBuiltThisRun'], reuse_folder is None)
            self.assertEqual(report['nativeLogVerbosity'], 4)
            self.assertEqual([engine for op, engine in calls if op == 'model'], [e for i, e in probe.ORDER])
            self.assertEqual(sum(op == 'read' for op, _ in calls), 2)
            self.assertTrue(server.closed)
            self.assertFalse(report['productionModified'])
            self.assertEqual(report['automaticRetries'], 0)
            self.assertEqual(report['warmupInferenceRequests'], 0)
            self.assertFalse(report['weightsDownloaded'])
            self.assertTrue((Path(folder) / 'trial-result.json').is_file())


if __name__ == '__main__': unittest.main()

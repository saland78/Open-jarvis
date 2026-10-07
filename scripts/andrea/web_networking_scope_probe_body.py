"""Six original questions with source-scoped networking guidance, no install.

Bundled with exact baseline/resource sources and the independently tested
selector. Native performance gates and the balanced call order are unchanged.
Only small pmset reads run during inference; unknown measurements stay unknown.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import re
import secrets
import subprocess
import sys
import threading
import time
import types

sys.dont_write_bytecode = True
EXPECTED_OLLAMA_VERSION = '0.35.1'
WORKER_SECONDS = 95
MAX_WORKER_BYTES = 65536
THERMAL_SAMPLE_SECONDS = (6, 18, 36)
CANDIDATE_REVISION = 'source_networking_inventory_v2'
ARCHIVED_BASELINE_REVISION = 'full_context_before_api_context_integration'
INSTALLED_PROJECT_REVISION = 'complete_api_entries_signal_scope_v1'


def embedded_module(name, source):
    module = types.ModuleType(name)
    module.__file__ = str(Path(__file__).resolve())
    exec(compile(source, module.__file__ + ':' + name, 'exec'), module.__dict__)
    return module


baseline = embedded_module('_definition_baseline', BASELINE_SOURCE)
resources = embedded_module('_definition_resources', RESOURCE_SOURCE)
context = embedded_module('_definition_context', CONTEXT_SOURCE)
rule_budget = embedded_module('_single_rule_budget', RULE_BUDGET_SOURCE)
networking = embedded_module('_networking_scope', NETWORKING_SOURCE)
# The frozen reference prompt remains unchanged. These fingerprints
# describe the currently installed v1 project, not that archived prompt.
baseline.EXPECTED = {**baseline.EXPECTED, **{'scripts/andrea/web_page_local.py': '34fdf49278d857a29a01e9260d0577d7e46cd0b59cd2e40f8af2e3770c862e50', 'scripts/andrea/web_page_fidelity.py': 'cda722628976e8c910bc12341abebc7a6f0731f606e7e70645fc4b09936f7cae', 'scripts/andrea/web_page_context_contract.py': 'a7fa689865126891912e5f9c280ef9afc8b68771770ee5b7902cc46eac7b02e1', 'scripts/andrea/web_page_context_fetch.py': '8ababe9d94bec292dfe0dacbcaa4c4030aa839f6987ff887e693768d820b418d', 'scripts/andrea/web_definition_context.py': 'cea7127788650cacefd59b36bfd860a5525deef1c3ebd5372ab9f76acfcd55d4', 'scripts/andrea/web_single_rule_budget.py': 'c1f669cc14745e15babddec1572b0f86c59e883a07fcb567eb72cf2bf5389f57', 'scripts/andrea/web_heading_evidence.py': 'de4d874053d492e79b305206ad7fe26c8f0aa6f231ba39aaccc5c0988f5da91e', 'src/openjarvis/engine/ollama.py': 'e4227f50c4d7f9c0bd90be88dbbc523bd8a01f1012c7f3e7f326ec720c7825b8'}}



def checked_page(page):
    if not isinstance(page, dict) or 'definitionRanges' not in page:
        raise ValueError('definition_metadata_missing')
    plain = {key: value for key, value in page.items() if key != 'definitionRanges'}
    baseline.checked_page(plain)
    context.checked_definitions(page['text'], page['definitionRanges'])


def page_worker(project):
    baseline.verify_project(project)
    spec = importlib.util.spec_from_file_location('_verified_definition_reader', project/'scripts/andrea/web_page_fetch.py')
    fetcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetcher)
    instrumented = context.parser_with_definition_roles(baseline.parser_with_heading_roles(fetcher.TextParser))
    instances = []
    class Captured(instrumented):
        def __init__(self):
            super().__init__()
            instances.append(self)
    original_extract = fetcher.extract
    headings, definitions = [], []
    def extract_with_roles(body, content_type):
        nonlocal headings, definitions
        title, text, partial = original_extract(body, content_type)
        if content_type.split(';')[0].strip().lower() == 'text/html':
            if not instances:
                raise ValueError('reader_parser_missing')
            headings = baseline.normalized_heading_ranges(instances[-1], text, fetcher.MAX_TEXT)
            definitions = context.normalized_definition_ranges(instances[-1], text, fetcher.MAX_TEXT)
        return title, text, partial
    fetcher.TextParser = Captured
    fetcher.extract = extract_with_roles
    page = fetcher.read_request(sys.stdin.buffer.read(4097))
    if 'error' not in page:
        page['headingRanges'], page['definitionRanges'] = headings, definitions
    print(json.dumps(page, ensure_ascii=False))


def read_page(project, url):
    started = time.monotonic()
    try:
        value = subprocess.run([sys.executable, str(Path(__file__).resolve()), str(project), '--page-worker'],
                               input=json.dumps({'url': url}).encode(), capture_output=True, timeout=25, check=False)
    except subprocess.TimeoutExpired:
        raise ValueError('page_worker_deadline_no_retry') from None
    if value.returncode != 0 or len(value.stdout) > MAX_WORKER_BYTES:
        raise ValueError('page_worker_failed_no_retry')
    page = json.loads(value.stdout, object_pairs_hook=baseline.unique_pairs)
    if isinstance(page, dict) and 'error' in page:
        raise ValueError('page_read_failed_no_retry')
    page['readMs'] = round((time.monotonic()-started)*1000, 3)
    checked_page(page)
    return page


def prepared(page, case, variant):
    if variant == 'production':
        bank, messages, schema = baseline.baseline_prepare(page['text'], case['question'])
        selection = {'mode': 'full_context', 'selectedRefs': list(range(1, len(bank)+1)),
                     'sourceCharacters': len(page['text']), 'modelSourceCharacters': len(page['text']),
                     'omittedSourceCharacters': 0, 'matchedAnchors': [], 'reason': ARCHIVED_BASELINE_REVISION}
        policy = rule_budget.ordinary_policy(ARCHIVED_BASELINE_REVISION)
    elif variant == 'compact':
        bank, messages, schema, selection = context.prepare(page['text'], case['question'],
            heading_ranges=page['headingRanges'], definition_ranges=page['definitionRanges'], contract=baseline)
        policy = rule_budget.plan(case['question'], bank, selection, contract=baseline)
        messages, schema = rule_budget.apply(messages, schema, policy)
    else:
        raise ValueError('invalid_variant')
    selection = {**selection, 'outputPolicy': policy}
    if variant == 'compact':
        bank, messages, schema, selection = networking.apply(
            bank, messages, schema, selection, contract=baseline)
    if ''.join(bank) != page['text']:
        raise ValueError('audit_source_changed')
    payload = json.loads(messages[1]['content'], object_pairs_hook=baseline.unique_pairs)
    if payload['question'] != case['question']:
        raise ValueError('original_question_changed')
    expected_passages = [[ref, bank[ref-1]] for ref in selection['selectedRefs']]
    if payload['passages'] != expected_passages:
        raise ValueError('selected_source_or_numbers_changed')
    if variant == 'compact' and case['id'] == 'csv_conversion_condition':
        if (selection['mode'] != 'complete_api_entries'
                or policy['maxClaims'] != 1
                or baseline.normalized(case['requiredContext']) not in baseline.normalized(''.join(p for _, p in expected_passages))):
            raise ValueError('complete_csv_definition_not_available_no_inference')
    return bank, messages, schema, selection


class ThermalObserver:
    def __init__(self, worker, *, clock=time.monotonic, sampler=None):
        self.worker, self.clock = worker, clock
        self.started = clock()
        self.sampler = sampler or thermal_sample
        self.stop = threading.Event()
        self.rows = []
        self.errors = []
        self.thread = threading.Thread(target=self.observe, daemon=True)

    def observe(self):
        for delay in THERMAL_SAMPLE_SECONDS:
            if self.stop.wait(max(0, self.started + delay - self.clock())) or self.worker.poll() is not None:
                return
            try:
                row = self.sampler()
            except Exception:
                self.errors.append({'scheduledWorkerOffsetSeconds': delay, 'reason': 'thermal_sample_unavailable'})
                continue
            row['scheduledWorkerOffsetSeconds'] = delay
            row['startedWorkerOffsetMs'] = round((row.pop('startedMonotonic')-self.started)*1000, 3)
            row['finishedWorkerOffsetMs'] = round((row.pop('finishedMonotonic')-self.started)*1000, 3)
            row['nativePrefillPhaseProven'] = False
            self.rows.append(row)

    def start(self): self.thread.start()
    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)
        return not self.thread.is_alive()


def thermal_sample():
    started = time.monotonic()
    reader = resources.Reader()
    limits = resources.thermal_limits(reader.command('thermal', ['/usr/bin/pmset', '-g', 'therm']))
    return {'startedMonotonic': started, 'finishedMonotonic': time.monotonic(),
            'thermalLimits': limits, 'unavailableQueries': copy.deepcopy(reader.issues)}


def worker_error(kind):
    return {'requestStartedMonotonic': None, 'requestFinishedMonotonic': None,
            'result': {'status': 'error', 'errorKind': kind, 'modelAnswer': '',
                       'firstContentClientMs': None, 'totalClientMs': None, 'doneReason': None,
                       'native': baseline.native_metrics({}), 'qualityVerdict': 'pending_review'}}


def checked_worker(value):
    if not isinstance(value, dict) or set(value) != {'requestStartedMonotonic', 'requestFinishedMonotonic', 'result'}:
        raise ValueError('invalid_worker_shape')
    start, finish = value['requestStartedMonotonic'], value['requestFinishedMonotonic']
    if (any(type(number) not in (int, float) or not math.isfinite(number) or number < 0 for number in (start, finish))
            or not start <= finish <= start + WORKER_SECONDS or not isinstance(value['result'], dict)):
        raise ValueError('invalid_worker_timing')
    result = value['result']
    if (result.get('status') not in ('completed', 'error', 'truncated', 'incomplete')
            or not isinstance(result.get('modelAnswer'), str) or len(result['modelAnswer']) > 32000
            or not isinstance(result.get('native'), dict)):
        raise ValueError('invalid_worker_result')
    return value


def collect(project, page, case_index, variant, *, popen=subprocess.Popen, observer_factory=ThermalObserver):
    payload = json.dumps({'page': page, 'caseIndex': case_index, 'variant': variant}, ensure_ascii=False).encode()
    if len(payload) > MAX_WORKER_BYTES:
        raise ValueError('worker_input_too_large')
    worker = popen([sys.executable, str(Path(__file__).resolve()), str(project), '--model-worker'],
                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    observer = observer_factory(worker)
    try:
        observer.start()
        try:
            output, _stderr = worker.communicate(payload, timeout=WORKER_SECONDS)
            if worker.returncode != 0 or len(output) > MAX_WORKER_BYTES:
                value = worker_error('owned_worker_failed_or_oversized')
            else:
                value = checked_worker(json.loads(output, object_pairs_hook=baseline.unique_pairs))
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.communicate(timeout=2)
            value = worker_error('owned_worker_deadline_no_retry')
        except (OSError, ValueError, TypeError):
            value = worker_error('owned_worker_invalid_no_retry')
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.communicate(timeout=2)
        cleaned = observer.close()
    return value, copy.deepcopy(observer.rows), copy.deepcopy(observer.errors), cleaned


def model_worker(project):
    baseline.verify_project(project)
    raw = sys.stdin.buffer.read(MAX_WORKER_BYTES+1)
    if len(raw) > MAX_WORKER_BYTES:
        raise ValueError('worker_input_too_large')
    payload = json.loads(raw, object_pairs_hook=baseline.unique_pairs)
    if not isinstance(payload, dict) or set(payload) != {'page', 'caseIndex', 'variant'}:
        raise ValueError('invalid_worker_input')
    index = payload['caseIndex']
    if type(index) is not int or not 0 <= index < len(baseline.CASES):
        raise ValueError('invalid_original_case')
    case, page = baseline.CASES[index], payload['page']
    checked_page(page)
    if page['url'] != case['url']:
        raise ValueError('original_source_url_changed')
    _bank, messages, schema, _selection = prepared(page, case, payload['variant'])
    marker = ('A' if payload['variant'] == 'production' else 'Z') + secrets.token_hex(16)
    isolated = baseline.isolated_messages(messages, marker)
    opener = baseline.urllib.request.build_opener(baseline.urllib.request.ProxyHandler({}), baseline.NoRedirect())
    started = time.monotonic()
    result = baseline.stream_probe(opener, isolated, schema, clock=time.monotonic)
    print(json.dumps({'requestStartedMonotonic': started, 'requestFinishedMonotonic': time.monotonic(),
                      'result': result}, ensure_ascii=False))


def run(project, *, emit=print):
    if platform.system() != 'Darwin':
        raise ValueError('comparison_requires_macos')
    baseline.verify_project(project)
    reader = resources.Reader()
    version = reader.get('/api/version')
    if not isinstance(version, dict) or version.get('version') != EXPECTED_OLLAMA_VERSION:
        raise ValueError('ollama_version_missing_or_changed')
    loaded = resources.selected_model(reader.get('/api/ps'))
    if (loaded['loadedModelCount'] not in (0, 1)
            or (loaded['loadedModelCount'] == 1 and loaded['expectedModelLoaded'] is not True)):
        raise ValueError('unknown_loaded_state_or_other_model')
    emit('Sei richieste: tre domande originali per due varianti. Il riferimento usa il prompt completo archiviato prima dell’integrazione; il candidato usa il contesto API v1 e la nuova indicazione networking/rete. Stesse domande, controlli e soglie. Nessuna installazione, nota personale, warm-up o retry. Lascia OpenJarvis acceso e non inviare altre richieste durante la serie.')
    pages = {}
    for case in baseline.CASES:
        if case['url'] not in pages:
            pages[case['url']] = read_page(project, case['url'])
        page = pages[case['url']]
        if case.get('requiredContext') and baseline.normalized(case['requiredContext']) not in baseline.normalized(page['text']):
            raise ValueError('original_required_context_missing')
        for variant in ('production', 'compact'):
            prepared(page, case, variant)
    rows = []
    for position, (case_index, variant) in enumerate(baseline.ORDER, 1):
        baseline.verify_project(project)
        case, page = baseline.CASES[case_index], pages[baseline.CASES[case_index]['url']]
        bank, messages, schema, selection = prepared(page, case, variant)
        emit(f"Richiesta {position}/6: {case['id']} / {variant} — contesto {selection['modelSourceCharacters']} di {len(page['text'])} caratteri…")
        before = thermal_sample()
        value, observations, observation_errors, cleaned = collect(project, page, case_index, variant)
        after = thermal_sample()
        result = value['result']
        started = time.monotonic()
        checks = context.validate(result['modelAnswer'], bank, result['status'] == 'completed',
                                  heading_ranges=page['headingRanges'], contract=baseline, selection=selection)
        checks = rule_budget.validate_cardinality(checks, selection['outputPolicy'])
        validation_ms = round((time.monotonic()-started)*1000, 3)
        row = {'case': case['id'], 'variant': variant, 'question': case['question'], 'criteria': case['criteria'],
               'sourceURL': case['url'], 'readMs': page['readMs'], 'inputCharacters': len(page['text']),
               'partial': page['partial'], 'sourceTextSha256': hashlib.sha256(page['text'].encode()).hexdigest(),
               'sourceSnapshotUnchanged': True, 'auditSourceFullyPreserved': True,
               'fullSourceSuppliedToModel': selection['mode'] == 'full_context', 'selection': selection,
               'definitionRanges': page['definitionRanges'], 'headingRanges': page['headingRanges'],
               'systemCharacters': len(messages[0]['content']),
               'nativeClaimArrayLimit': schema['properties']['claims']['maxItems'],
               'nativeSchemaSha256': hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(),
               'unisolatedPromptSha256': hashlib.sha256(json.dumps(messages, ensure_ascii=False).encode()).hexdigest(),
               'result': result, 'checks': checks,
               'archivedBaselinePolicyChecks': baseline.installed_validate(result['modelAnswer'], bank, result['status'] == 'completed'),
               'caseShapeMet': baseline.case_shape(case['id'], checks),
               'cacheQualification': baseline.cache_qualification(result['native']),
               'validationClientMs': validation_ms, 'thermalBefore': before, 'thermalDuring': observations,
               'thermalAfter': after, 'observerCleanupCompleted': cleaned,
               'thermalObservationErrors': observation_errors,
               'sameSourceAnchoredTypeScopeAndMechanismChecks': True,
               'sourceAnchoredDuplicateConversionRuleCheck': True,
               'sourceAnchoredSignalScopeCheck': True,
               'signalScopeInventoryAddedToPrompt': variant == 'compact' and bool(selection.get('sourceSignalScopeRefs')),
               'networkingScopeInventoryAddedToPrompt': variant == 'compact' and bool(selection.get('sourceNetworkingScopeRefs')),
               'referencePromptRevision': ARCHIVED_BASELINE_REVISION,
               'installedProjectRevision': INSTALLED_PROJECT_REVISION,
               'qualityVerdict': 'pending_review', 'productionModified': False, 'modelOptionsChanged': False,
               'automaticRetries': 0, 'vaultRead': False, 'browserRendering': 'not_measured'}
        rows.append(row)
        emit(json.dumps(row, ensure_ascii=False, indent=2))
        baseline.verify_project(project)
        if result['status'] != 'completed' or not cleaned:
            report = baseline.comparison(rows)
            report['candidateRevision'] = CANDIDATE_REVISION
            emit(json.dumps(report, ensure_ascii=False, indent=2))
            raise ValueError('series_stopped_after_incomplete_request_no_retry')
    after_version = resources.Reader().get('/api/version')
    stable = isinstance(after_version, dict) and after_version.get('version') == EXPECTED_OLLAMA_VERSION
    report = baseline.comparison(rows)
    report.update({'mode': 'source_networking_scope_latency_comparison',
                   'candidateRevision': CANDIDATE_REVISION,
                   'referencePromptRevision': ARCHIVED_BASELINE_REVISION,
                   'referenceIsCurrentInstalledPrompt': False,
                   'installedProjectRevision': INSTALLED_PROJECT_REVISION,
                   'sourceNetworkingInventoryChangedExplicitly': True,
                   'sourceAnchoredDuplicateConversionRuleCheck': True,
                   'sourceAnchoredSignalScopeCheck': True,
                   'sourceSignalScopeInventoryAddedExplicitly': True,
                   'nativeSingleRuleArrayLimitChangedExplicitly': True,
                   'shorterInstructionTextAlsoChanged': True,
                   'ollamaVersion': EXPECTED_OLLAMA_VERSION, 'versionUnchanged': stable,
                   'sourceSelectionChangedExplicitly': True, 'originalQuestionsAndGatesUnchanged': True,
                   'thermalSamplesDoNotProvePhaseOrCausality': True,
                   'noCoolingWaitsOrThermalBasedExclusions': True,
                   'integrationAllowedByThisAutomaticReport': False})
    if not stable:
        report['performanceOutcome'] = 'inconclusive_ollama_version_changed'
    emit(json.dumps(report, ensure_ascii=False, indent=2))
    emit('Serie conclusa. Servono revisione di tutte le risposte e confronto dei tempi; i controlli tecnici non certificano il significato. Nessuna modifica installata.')
    return report


def main():
    if '--ollama-read' in sys.argv:
        return resources.main()
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    parser.add_argument('--page-worker', action='store_true')
    parser.add_argument('--model-worker', action='store_true')
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve(strict=True)
        if args.page_worker:
            page_worker(project)
        elif args.model_worker:
            model_worker(project)
        else:
            run(project)
        return 0
    except (OSError, ValueError, TypeError) as exc:
        # Only our fixed snake-case error codes may cross this boundary. Never
        # print raw system stderr, network errors, private paths or arguments.
        message = str(exc)
        code = message if re.fullmatch(r'[a-z_]{3,100}', message) else 'input_or_runtime_check_failed'
        print('Prova interrotta. Codice: '+code+'. Nessun retry o modifica.', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Prova interrotta dall’utente. Chiuso solo il processo della prova; arresto del lavoro server non confermato. Nessun retry o modifica.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())

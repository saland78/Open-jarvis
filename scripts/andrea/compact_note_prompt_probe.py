"""Read-only prompt A/B on one or two explicitly selected local notes.

No production file is changed. The compact message retains mandatory facts
and the native full JSON Schema. Technical validation is not semantic review.
Private results must stay local. Measures are direct Ollama, not UI latency.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import time
from types import ModuleType, SimpleNamespace
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
BASE = 'http://127.0.0.1:11434'
NOTES_BASE = 'http://127.0.0.1:8008'
LIMIT = 4 * 1024 * 1024

# Measurement helpers reuse the previous local phases probe. Reject tools and
# duplicate protocol keys, and do not import unverified project modules.
def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None

def milliseconds(value):
    valid = number(value)
    return round(valid / 1_000_000, 3) if valid is not None else None

def native_metrics(event):
    fields = ('total_duration', 'load_duration', 'prompt_eval_duration', 'eval_duration')
    result = {field.removesuffix('_duration') + 'Ms': milliseconds(event.get(field)) for field in fields}
    result.update({field: number(event.get(field)) for field in
                   ('prompt_eval_count', 'prompt_eval_cached_count', 'eval_count')})
    tokens, elapsed = result['eval_count'], result['evalMs']
    result['evalTokensPerSecond'] = round(tokens * 1000 / elapsed, 3) if tokens is not None and elapsed and tokens > 0 else None
    # Do not interpret a residual as a particular phase or mix with client time.
    return result

def stream_probe(opener, messages, response_schema, clock=time.perf_counter):
    body = {'model': MODEL, 'messages': messages, 'stream': True, 'think': False, 'keep_alive': '15m',
            'format': response_schema, 'options': {'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096}}
    request = Request(BASE + '/api/chat', data=json.dumps(body, ensure_ascii=False).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    started = clock()
    first = None
    count = 0
    final = None
    answer = []
    answer_size = 0
    try:
        with opener.open(request, timeout=90) as response:
            while True:
                if clock() - started > 90:
                    raise TimeoutError('deadline')
                line = response.readline(262145)
                if clock() - started > 90:
                    raise TimeoutError('deadline')
                if not line:
                    break
                count += len(line)
                if len(line) > 262144 or count > LIMIT:
                    raise ValueError('response_limit')
                if not line.strip():
                    continue
                event = json.loads(line, object_pairs_hook=unique_pairs)
                if not isinstance(event, dict) or 'error' in event:
                    raise ValueError('invalid_event')
                message = event.get('message', {})
                if not isinstance(message, dict) or message.get('tool_calls'):
                    raise ValueError('invalid_message_or_tools')
                content = message.get('content')
                if isinstance(content, str) and content:
                    answer_size += len(content)
                    if answer_size > 32000:
                        raise ValueError('answer_limit')
                    answer.append(content)
                    if first is None:
                        first = round((clock() - started) * 1000, 3)
                if event.get('done') is True:
                    final = event
                    break
        reason = final.get('done_reason') if final else None
        reason = reason if reason in ('stop', 'length') else None
        status = 'completed' if final and reason == 'stop' and first is not None else 'truncated' if reason == 'length' else 'incomplete'
        return {'status': status, 'firstContentClientMs': first,
                'totalClientMs': round((clock() - started) * 1000, 3),
                'doneReason': reason, 'native': native_metrics(final or {}), 'qualityVerdict': 'pending_review', 'modelAnswer': ''.join(answer)}
    except (OSError, ValueError, TypeError, AttributeError):
        return {'status': 'error', 'firstContentClientMs': first,
                'totalClientMs': round((clock() - started) * 1000, 3),
                'doneReason': None, 'native': native_metrics({}), 'qualityVerdict': 'pending_review', 'modelAnswer': None}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def note_path(path):
    if not isinstance(path,str) or not path or len(path)>500 or '\\' in path or '\x00' in path:
        raise ValueError('invalid_note_path')
    if PurePosixPath(path).is_absolute() or not path.lower().endswith('.md'):
        raise ValueError('invalid_note_path')
    if any(not p or p.startswith('.') or p in {'node_modules','dist','__pycache__'} for p in path.split('/')):
        raise ValueError('invalid_note_path')
    return path

def get_json(opener,path):
    request=Request(NOTES_BASE+path,headers={'Accept':'application/json'},method='GET')
    with opener.open(request,timeout=10) as response:
        if response.status!=200: raise ValueError('notes_api_status')
        data=response.read(2*1024*1024+1)
        if len(data)>2*1024*1024: raise ValueError('notes_api_limit')
    value=json.loads(data,object_pairs_hook=lambda pairs: unique_pairs(pairs))
    if not isinstance(value,dict): raise ValueError('notes_api_envelope')
    return value

def unique_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('duplicate_api_key')
        result[key]=value
    return result

def check_status(opener,vault):
    status=get_json(opener,'/api/andrea/notes/status')
    if status.get('configured') is not True or status.get('available') is not True or status.get('mode')!='read-only' or status.get('vault')!=vault:
        raise ValueError('vault_unavailable_or_mismatched')

def read_note(opener,path):
    path=note_path(path)
    note=get_json(opener,'/api/andrea/notes/read?'+urlencode({'path':path}))
    if note.get('path')!=path or note.get('status')!='active' or note.get('hasContent') is not True:
        raise ValueError('unusable_note')
    text=note.get('text');start=note.get('bodyStart')
    if not isinstance(text,str) or not text.strip() or len(text.encode('utf-8'))>256*1024 or type(start)!=int or not 0<=start<=len(text.splitlines()):
        raise ValueError('invalid_note_envelope')
    return note

COMPACT_CODE = '"""Experimental prompt compaction; native schema and facts stay unchanged.\n\nThis is a candidate for a read-only A/B probe, not a production change.\nAn empty-text outline replaces the full schema only in the message. The\noriginal full schema must still be passed as Ollama\'s native format.\n"""\nimport json\n\nSCHEMA_INSTRUCTION = \'Restituisci esclusivamente JSON conforme a response_schema.\'\nSHAPE_INSTRUCTION = (\n    \'Restituisci esclusivamente JSON nella struttura response_shape; \'\n    \'sostituisci i testi vuoti con le frasi richieste.\'\n)\nBOOK_ROLE_INSTRUCTION = (\n    \' Nel profilo conserva il termine specifico della fonte per il tipo di opera \'\n    \'e la sua classificazione, senza sostituirli con una categoria generica. \'\n    \'Per le edizioni indica la disponibilità dalla data riportata; \'\n    \'non trasformarla in un generico inizio o nella data di avvio della produzione.\'\n)\n\n\ndef messages(case, plan, synthesis):\n    """Retain the exact mandatory information and every substantive instruction."""\n    original = synthesis.messages(case, plan)\n    if (len(original) != 2 or original[0][\'role\'] != \'system\'\n            or original[1][\'role\'] != \'user\'\n            or original[0][\'content\'].count(SCHEMA_INSTRUCTION) != 1):\n        raise ValueError(\'unexpected_prompt_structure\')\n    body = json.loads(original[1][\'content\'])\n    if (set(body) != {\'richiesta\', \'informazioni_obbligatorie\', \'response_schema\'}\n            or body[\'response_schema\'] != plan[\'schema\']):\n        raise ValueError(\'unexpected_prompt_schema\')\n    body.pop(\'response_schema\')\n    body[\'response_shape\'] = {\'records\': {\n        fact[\'id\']: {\'text\': \'\'} | (\n            {\'contextDate\': fact[\'contextDate\']} if \'contextDate\' in fact else {}\n        ) for fact in plan[\'facts\']\n    }}\n    instruction = original[0][\'content\'].replace(SCHEMA_INSTRUCTION, SHAPE_INSTRUCTION)\n    if any(fact[\'kind\'] == \'book_description\' for fact in plan[\'facts\']):\n        instruction += BOOK_ROLE_INSTRUCTION\n    return [\n        {\'role\': \'system\', \'content\': instruction},\n        {\'role\': \'user\', \'content\': json.dumps(body, ensure_ascii=False)},\n    ]\n'

EXPECTED = {
    'scripts/andrea/runtime.py': 'fc91fc88d7c19a602c4ab924736f0523f6e091f08ce29dccfc725f8186443a0a',
    'scripts/andrea/vault.py': '3dd17ba664504f12ee02e72962ff6358db1be5d56b085ff755ff8f93971a78bd',
    'src/openjarvis/engine/ollama.py': '881c5e2f667d31a4a62d0e726fa179a4819ecab2b7f960d513871e6a0fb529f0',
    'scripts/andrea/synthesis_contract.py': '2ef7d64b1fd6b737d45398b9cc5ae46aac28617c4059348b3ba333f3f3cea80d',
    'scripts/andrea/markdown_fact_adapter.py': 'a9793b116b255a78c4af61f88dabf11b8a66ba0299ea9ef3116d25fed2a090a1',
    'scripts/andrea/predicate_context_synthesis.py': '65c4af9db2024b6ace064b1ffe0d764e658f67683709c3e0b0acb8bef829951e',
    'scripts/andrea/structured_stream.py': '52e527c183eda6c369fb53bc5e19ca7f0682151cc1a981c66d47f37cc25a01ff',
    'scripts/andrea/note_facts.py': '2a20aa5e2310228a28f3c2313239c1f4e1d6419dabaab65b8e3ea2503f58bda7',
}
LOAD_ORDER = ('synthesis_contract', 'markdown_fact_adapter',
              'predicate_context_synthesis', 'structured_stream', 'note_facts')
CRITERIA = {
    'book': [
        'Mantiene genere, lingua, capitoli e numero approssimativo di parole selezionati.',
        'Distingue cartaceo, Kindle e copertina, conservando le date senza aggiungere anni mancanti.',
        'Non inventa una nuova edizione o una verifica esterna; supporti originali e righe coerenti.',
    ],
    'qualifications': [
        'Mantiene il conteggio dichiarato e la variabilita per periodo.',
        'Separa DATO NON VERIFICATO nell aggiornamento da DATO ASSENTE nella fotografia storica, con le rispettive date.',
        'Limita le qualifiche alla nota: non deduce zero, importi, valori aggiornati o assenze nella dashboard.',
    ],
}
compact = ModuleType('experimental_compact_note_prompt')
exec(compile(COMPACT_CODE, '<compact_note_prompt>', 'exec'), compact.__dict__)


def verified_sources(project):
    """Check every public baseline before executing any project module."""
    sources = {}
    for relative, expected in EXPECTED.items():
        file = project / relative
        if any((project / Path(*Path(relative).parts[:i])).is_symlink()
               for i in range(1, len(Path(relative).parts) + 1)):
            raise ValueError('symlink_in_baseline')
        data = file.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('baseline_mismatch')
        sources[relative] = data
    return sources


def load_modules(project):
    """Execute only hash-verified public modules, without writing bytecode."""
    sources = verified_sources(project)
    previous = {name: sys.modules.get(name) for name in LOAD_ORDER}
    modules = {}
    try:
        for name in LOAD_ORDER:
            relative = 'scripts/andrea/' + name + '.py'
            module = ModuleType(name)
            module.__file__ = str(project / relative)
            sys.modules[name] = module
            exec(compile(sources[relative], module.__file__, 'exec'), module.__dict__)
            modules[name] = module
    finally:
        for name, prior in previous.items():
            if prior is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prior
    return SimpleNamespace(adapter=modules['markdown_fact_adapter'],
                           synthesis=modules['predicate_context_synthesis'],
                           validator=modules['synthesis_contract'],
                           bridge=modules['note_facts'])


def valid_selection(vault, paths):
    if not isinstance(vault, str) or not Path(vault).is_absolute():
        raise ValueError('absolute_vault_required')
    if not 1 <= len(paths) <= 2 or len(set(paths)) != len(paths):
        raise ValueError('select_one_or_two_distinct_notes')
    return [note_path(path) for path in paths]


def source_unchanged(opener, vault, initial):
    try:
        check_status(opener, vault)
        fresh = read_note(opener, initial['path'])
        return all(fresh.get(key) == initial.get(key)
                   for key in ('text', 'bodyStart', 'status', 'modifiedAt'))
    except (OSError, ValueError, TypeError):
        return False


def rejected(reason):
    return {'status': 'rejected', 'reason': reason, 'claims': [],
            'semanticVerdict': 'not_assessed'}


def message_chars(messages):
    # Character counts are not token counts. Native Ollama counts are separate.
    return sum(len(message['content']) for message in messages)


def collect(opener, modules, project, vault, paths):
    paths = valid_selection(vault, paths)
    verified_sources(project)
    check_status(opener, vault)
    selections = []
    # Validate the complete explicit selection before sending any inference.
    for path in paths:
        note = read_note(opener, path)
        bundle = modules.bridge.prepare(note)
        if bundle is None:
            raise ValueError('unsupported_or_ambiguous_note')
        selections.append((note, bundle))
    report = {
        'schema': 1, 'mode': 'compact_note_prompt_AB', 'candidateRevision': 2,
        'requested': 2 * len(selections), 'inferenceRequests': 0, 'automaticRetries': 0,
        'runtimeChanged': False, 'notesWritten': False, 'filesWritten': False,
        'vaultRead': 'explicit_selected_notes_only',
        'observer': 'direct_ollama_not_server_synthesis_or_browser',
        'productionAdoption': False, 'qualityVerdict': 'pending_review',
        'selectionScope': 'bounded_facts_not_complete_note_summary',
        'nativeSchemaUnchanged': True, 'guardsUnchanged': True,
        'requestOptions': {'model': MODEL, 'think': False, 'keep_alive': '15m',
                           'temperature': 0.4, 'num_predict': 512, 'num_ctx': 4096},
        'order': 'original_then_compact_per_note',
        'comparisonLimit': 'Single observations; order, cache, load and output length may affect time. No causal performance conclusion.',
        'firstContentMeaning': 'Hidden JSON received by this diagnostic; not accepted text or browser rendering.',
        'acceptedTextReadyMeaning': 'Validated text ready in this diagnostic; final report is printed later. Not UI latency.',
        'baselineUnchanged': True, 'rows': [],
    }
    for note, bundle in selections:
        variants = [('original', bundle['messages']),
                    ('compact', compact.messages(bundle['case'], bundle['plan'], modules.synthesis))]
        for variant, messages in variants:
            verified_sources(project)
            if not source_unchanged(opener, vault, note):
                report['stoppedReason'] = 'note_changed_or_unavailable_before_request'
                return report
            request_index = report['inferenceRequests'] + 1
            print(f"Richiesta {request_index}/{report['requested']} — {bundle['kind']}, {variant}…", flush=True)
            started = time.perf_counter()
            result = stream_probe(opener, messages, bundle['plan']['schema'])
            report['inferenceRequests'] += 1
            unchanged = source_unchanged(opener, vault, note)
            contract = modules.adapter.validate(
                result['modelAnswer'], bundle['case'], bundle['plan'], modules.synthesis,
                modules.validator, completed=result['status'] == 'completed'
            ) if unchanged else rejected('note_changed_or_unavailable')
            try:
                verified_sources(project)
            except (OSError, ValueError):
                report['baselineUnchanged'] = False
                contract = rejected('baseline_changed_during_request')
            rendered = modules.synthesis.render(contract)
            ready = round((time.perf_counter() - started) * 1000, 3) if rendered is not None else None
            report['rows'].append({
                'case': bundle['kind'], 'path': note['path'], 'variant': variant,
                'criteria': CRITERIA[bundle['kind']],
                'messageCharacters': message_chars(messages),
                'nativeSchemaSha256': hashlib.sha256(json.dumps(
                    bundle['plan']['schema'], sort_keys=True).encode()).hexdigest(),
                'sourceUnchanged': unchanged, **result,
                'contract': contract, 'renderedAnswer': rendered,
                'acceptedTextReadyClientMs': ready,
                'originalEvidence': modules.bridge.source_evidence(bundle),
            })
            if not unchanged or not report['baselineUnchanged'] or result['status'] == 'error':
                report['stoppedReason'] = 'source_baseline_or_transport_changed'
                return report
    report['completedRequests'] = report['inferenceRequests']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--vault', required=True)
    parser.add_argument('--note', action='append', required=True, metavar='RELATIVE_MD_PATH')
    args = parser.parse_args()
    valid_selection(args.vault, args.note)
    project = args.project.expanduser().resolve(strict=True)
    modules = load_modules(project)
    opener = build_opener(ProxyHandler({}), NoRedirect())
    print('Confronto finito A/B: due richieste per nota scelta. Nessun retry, installazione o file modificato.', flush=True)
    print('OpenJarvis deve restare acceso. Evita altre richieste al modello durante la prova. I risultati contengono passaggi privati: non pubblicarli.', flush=True)
    print(json.dumps(collect(opener, modules, project, args.vault, args.note), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('Prova interrotta: non conclusa. Nessun file modificato.')
    except (OSError, ValueError, TypeError):
        raise SystemExit('Prova non conclusa: controlla baseline, OpenJarvis acceso e le note attive selezionate. Nessun file modificato.')

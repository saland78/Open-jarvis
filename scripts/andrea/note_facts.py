"""Production bridge for bounded facts proved against a single active note.

Extraction, prompt, schema and guards are the candidates exercised by the
read-only probes. The complete current qualification is a source-bound literal;
the other records are model synthesis. A complete, unchanged source is required;
original disjoint passages keep their own lines.
Technical acceptance is deliberately separate from semantic review.
"""
import asyncio
from types import SimpleNamespace

import markdown_fact_adapter as adapter
import predicate_context_synthesis as synthesis
import qualification_prompt
import qualification_sentence_guard
import qualification_compact_wire
import synthesis_contract as validator
from structured_stream import collect

MODULES = SimpleNamespace(adapter=adapter, synthesis=synthesis, validator=validator)

QUERIES = {
    'book': 'Riassumi il profilo del libro e le date delle edizioni e della copertina.',
    'qualifications': 'Riassumi i titoli pubblicati e le qualifiche di vendite e royalty distinguendo i contesti datati.',
}


def prepare(note):
    """Return one unambiguous supported plan; do not generalise to other notes."""
    source = {**note, 'id': 'N1'}
    candidates = []
    for kind, query in QUERIES.items():
        case = {'query': query, 'sources': [source]}
        plan = adapter.prepare(case, kind)
        if plan['status'] == 'ready':
            messages = (qualification_prompt.messages(case, plan, synthesis)
                        if kind == 'qualifications' else synthesis.messages(case, plan))
            candidates.append({'kind': kind, 'case': case, 'plan': plan,
                               'messages': messages})
    if len(candidates) == 1 and candidates[0]['kind'] == 'qualifications':
        try:
            candidates[0] = qualification_sentence_guard.protect(candidates[0])
        except ValueError:
            # Unknown source wording is unsupported, never completed by guessing.
            return None
    return candidates[0] if len(candidates) == 1 else None


def source_evidence(bundle):
    source = bundle['case']['sources'][0]
    proofs = {}
    for fact in bundle['plan']['facts']:
        for proof in fact['proofs']:
            proofs[(proof['start'], proof['end'])] = proof
    passages = [{'text': p['quote'], 'startLine': p['lineStart'], 'endLine': p['lineEnd']}
                for _, p in sorted(proofs.items())]
    return {key: source[key] for key in ('id', 'path', 'title', 'status', 'modifiedAt')} | {
        'eligible': True, 'passages': passages,
        'text': '\n\n'.join(p['text'] for p in passages),
        'startLine': passages[0]['startLine'], 'endLine': passages[-1]['endLine'],
    }


def rejection(reason):
    return {'status': 'rejected', 'reason': reason, 'claims': [], 'semanticVerdict': 'not_assessed'}


def render(result):
    text = synthesis.render(result)
    if text is not None:
        if result.get('qualificationSentencePreserved'):
            literal_ids = set(result['literalSourceFactIds'])
            parts = []
            for claim in result['claims']:
                paragraph = synthesis.render({**result, 'claims': [claim]})
                if claim['factId'] in literal_ids:
                    paragraph = 'Frase riportata dalla fonte — ' + paragraph
                parts.append(paragraph)
            return ('Qualifica corrente e indicazioni di consultazione riportate dalla fonte. '
                    'Gli altri punti sono sintesi del modello da confrontare con i passaggi originali. '
                    'Nessun dato esterno verificato.\n\n' + '\n\n'.join(parts))
        return text
    if result.get('reason') == 'note_changed_or_unavailable':
        return ('Sintesi strutturata non mostrata: la nota è cambiata o non è più accessibile '
                'durante la generazione. Ripeti la lettura prima di chiedere una nuova sintesi. '
                'I passaggi mostrati sono quelli letti inizialmente. Nessun dato esterno verificato.')
    return ('Sintesi strutturata non mostrata: i controlli su completezza, fonti, numeri o date '
            'non sono stati superati. Consulta i passaggi originali riportati sotto. '
            'Nessuna seconda generazione automatica. Nessun dato esterno verificato.')


async def run(stream, bundle, notes, vault_identity, measurement):
    initial = bundle['case']['sources'][0]
    # The source extractor still produces all four proved facts. Only the wire
    # representation changes for qualifications: three model strings, with the
    # full current sentence and dates bound from the source before inference.
    compact = None
    messages, schema = bundle['messages'], bundle['plan']['schema']
    if bundle['kind'] == 'qualifications':
        modules = SimpleNamespace(**vars(MODULES), bridge=SimpleNamespace(prepare=prepare))
        compact = qualification_compact_wire.prepare(bundle, modules)
        messages, schema = compact['messages'], compact['schema']

    async def validate(raw, _sources, *, completed):
        if not completed:
            return rejection('stream_not_completed')
        try:
            fresh = await asyncio.to_thread(notes.read, initial['path'])
            if str(notes.root()) != vault_identity or any(
                fresh.get(key) != initial.get(key)
                for key in ('text', 'bodyStart', 'status', 'modifiedAt')
            ):
                return rejection('note_changed_or_unavailable')
        except (ValueError, OSError):
            return rejection('note_changed_or_unavailable')
        if bundle['kind'] == 'qualifications':
            return qualification_compact_wire.validate(raw, compact, modules, completed=completed)
        return adapter.validate(raw, bundle['case'], bundle['plan'], synthesis, validator,
                                completed=completed)

    def secured(messages):
        return stream(messages, schema)

    return await collect(secured, messages, bundle['case']['sources'], measurement,
                         validate=validate, render=render)

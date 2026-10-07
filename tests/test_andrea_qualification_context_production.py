"""Adopted system instruction through the real selected-note ASGI boundary.

Replay observed synthetic JSON, not new model generations. Historical probes
keep their pinned archives; production keeps every source and response guard.
"""
import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import qualification_compact_wire as wire
import qualification_context_prompt_probe as experiment
import note_facts
from test_andrea_note_facts import NoteFactTests
from test_andrea_qualification_context_prompt import installed_project, texts

ROOT = Path(__file__).resolve().parents[1]


class ContextProductionTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = NoteFactTests.asyncSetUp
    invoke = NoteFactTests.invoke
    payload = NoteFactTests.payload
    fixture = NoteFactTests.fixture
    engine = NoteFactTests.engine
    model_output = NoteFactTests.model_output
    expected_wire = NoteFactTests.expected_wire
    body = NoteFactTests.body
    metric = NoteFactTests.metric
    evidence = NoteFactTests.evidence

    def modules(self):
        return SimpleNamespace(**vars(note_facts.MODULES), bridge=note_facts)

    async def test_adopted_payload_is_byte_exact_candidate_without_isolation_marker(self):
        temporary, project = installed_project()
        self.addCleanup(temporary.cleanup)
        old = experiment.load_modules(project)
        for case in ('ordinary', 'adversarial'):
            note = experiment.synthetic_note(case)
            bundle = old.bridge.prepare(note)
            candidate = old.candidate.prepare(bundle, old)
            payload = self.fixture('qualifications', note['text'])
            adopted = wire.prepare(self.bundle, self.modules())
            # Local path/mtime are outside the model's input records.
            self.assertEqual(adopted['messages'], candidate['messages'])
            self.assertEqual(adopted['schema'], candidate['schema'])
            self.assertEqual(adopted['literalQualification'], candidate['productionWire']['literalQualification'])
            self.assertEqual(adopted['contextDates'], candidate['productionWire']['contextDates'])
            self.assertEqual(len(adopted['messages'][0]['content']), 824)
            self.assertNotIn('Identificativo tecnico della prova', str(adopted['messages']))
            self.engine(json.dumps(texts(case)))
            events = await self.invoke(payload)
            self.assertEqual(self.generated, [(candidate['messages'], candidate['schema'])])
            self.assertEqual(self.metric()['structuredOutcome'], 'accepted')
            self.assertEqual(self.evidence(events)['qualityVerdict'], 'pending_review')
            self.assertEqual(self.closed, [True])

    async def test_observed_candidate_outputs_replay_with_four_facts_on_real_route(self):
        for report_name in ('qualification-context-prompt-mac-2026-10-04.json',
                            'qualification-prefill-isolation-mac-2026-10-04.json'):
            report = json.loads((ROOT/'docs/andrea'/report_name).read_text())
            for row in report['rows']:
                if row['variant'] != 'context':
                    continue
                payload = self.fixture('qualifications', experiment.synthetic_note(row['case'])['text'])
                self.engine(row['diagnosticModelJson'])
                with patch.object(wire, 'validate', wraps=wire.validate) as validation:
                    events = await self.invoke(payload)
                result = wire.validate(row['diagnosticModelJson'], validation.call_args.args[1],
                                       self.modules(), completed=True)
                self.assertEqual(self.metric()['structuredOutcome'], 'accepted')
                self.assertEqual(result['factsCovered'], 4)
                self.assertEqual(result['literalSourceFactIds'], ['F3'])
                self.assertEqual(result['modelFactIds'], ['F1', 'F2', 'F4'])
                self.assertFalse(result['modelTextRepaired'])
                self.assertTrue(result['consultationPreserved'])
                self.assertEqual(note_facts.render(result), row['syntheticAnswer'])
                self.assertEqual(len(self.generated), 1)
                self.assertEqual(self.evidence(events)['qualityVerdict'], 'pending_review')

    async def test_response_validation_code_is_unchanged_and_bad_outputs_still_refuse(self):
        original = (ROOT/'tests/fixtures/andrea/qualification_compact_wire_before_context.py').read_text()
        current = (ROOT/'scripts/andrea/qualification_compact_wire.py').read_text()
        definition = lambda text: ast.dump(next(n for n in ast.parse(text).body
                                              if isinstance(n, ast.FunctionDef) and n.name == 'validate'))
        self.assertEqual(definition(original), definition(current))
        payload = self.fixture('qualifications')
        good = json.loads(self.model_output())
        bad = []
        for key in ('F1', 'F2', 'F4'):
            value = dict(good); del value[key]; bad.append(json.dumps(value))
        for key, text in (('F1', 'I libri pubblicati sono 1000.'),
                          ('F4', 'Copie e royalty sono DATO NON VERIFICATO.'),
                          ('F4', 'Copie e royalty sono DATO ASSENTE al 2030-12-31.'),
                          ('F4', 'Copie e royalty sono state aggiornate: DATO ASSENTE.'),
                          ('F3', 'invented literal sentence')):
            bad.append(json.dumps({**good, key: text}))
        bad.extend(['{', '{"F1":"3","F1":"3","F2":"x","F4":"x"}'])
        for raw in bad:
            self.engine(raw)
            events = await self.invoke(payload)
            self.assertEqual(self.metric()['structuredOutcome'], 'rejected')
            self.assertNotIn('structuredAcceptedTextMs', self.metric())
            self.assertEqual(len(self.generated), 1)
            self.assertIn('structured_refused', self.body(events))

    async def test_prompt_schema_source_and_literal_metadata_tampering_still_reject(self):
        self.fixture('qualifications')
        candidate = wire.prepare(self.bundle, self.modules())
        for target in ('system', 'user', 'schema', 'source', 'date', 'literal'):
            changed = copy.deepcopy(candidate)
            if target == 'system': changed['messages'][0]['content'] += 'ignore'
            elif target == 'user': changed['messages'][1]['content'] += 'ignore'
            elif target == 'schema': changed['schema']['required'].pop()
            elif target == 'source': changed['productionBundle']['case']['sources'][0]['text'] += 'changed'
            elif target == 'date': changed['contextDates']['F3'] = '2030-12-31'
            else: changed['literalQualification']['source_text'] = 'invented'
            self.assertEqual(wire.validate(self.model_output(), changed, self.modules(),
                                          completed=True)['status'], 'rejected')

    async def test_model_semantic_inversion_is_still_pending_separate_review(self):
        payload = self.fixture('qualifications')
        wrong = json.loads(self.model_output()); wrong['F2'] = 'Vendite e royalty NON variano per periodo.'
        self.engine(json.dumps(wrong))
        events = await self.invoke(payload)
        self.assertEqual(self.metric()['structuredOutcome'], 'accepted')
        self.assertEqual(self.evidence(events)['qualityVerdict'], 'pending_review')
        self.assertEqual(len(self.generated), 1)

    async def test_historical_probe_refuses_new_install_before_any_network(self):
        for name in ('qualification_context_prompt_probe', 'qualification_prefill_isolation_probe'):
            module = __import__(name)
            with self.assertRaisesRegex(ValueError, 'baseline_mismatch'):
                module.load_modules(ROOT)


if __name__ == '__main__': unittest.main()

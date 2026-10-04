"""Regression of the observed omission of consultation despite preserved prefix."""
import copy
import json
from pathlib import Path
import unittest

import concise_qualification_text_probe as p
import qualification_clause_guard as prefix
import qualification_sentence_guard as guard
from test_andrea_qualification_clause_guard import response

from andrea_qualification_baseline import load_modules as historical_modules

ROOT = Path(__file__).resolve().parents[1]
OBSERVED = 'I valori aggiornati restano DATO NON VERIFICATO soltanto in questa nota: Vendite e royalty varian per periodo.'


class QualificationSentenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = historical_modules(p)

    def bundle(self, note=None):
        return self.modules.bridge.prepare(note or p.synthetic_note('adversarial'))

    def test_actual_prefix_only_sample_accepted_before_and_rejected_now_without_repair(self):
        original = self.bundle()
        raw = response(original, text=OBSERVED)
        previous = prefix.validate(raw, prefix.protect(original), self.modules, completed=True)
        self.assertEqual(previous['status'], 'valid_structure_pending_semantic_review')
        self.assertTrue(previous['qualificationClausePreserved'])
        secured = guard.protect(original)
        result = guard.validate(raw, secured, self.modules, completed=True)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['reason'], 'qualification_sentence_missing_or_changed')
        self.assertEqual(result['claims'], [])
        self.assertIsNone(self.modules.synthesis.render(result))
        self.assertEqual(json.loads(raw)['records']['F3']['text'], OBSERVED)

    def test_source_qualification_consultation_proof_and_current_field_are_bound_without_other_changes(self):
        original = self.bundle()
        before = copy.deepcopy(original)
        secured = guard.protect(original)
        self.assertEqual(original, before)
        self.assertEqual(secured['case'], original['case'])
        self.assertEqual(secured['plan']['facts'], original['plan']['facts'])
        sentence = secured['qualificationSentence']
        schema = copy.deepcopy(secured['plan']['schema'])
        self.assertEqual(schema['properties']['records']['properties']['F3']['properties']['text'].pop('const'), sentence['source_text'])
        self.assertEqual(schema, original['plan']['schema'])
        body = json.loads(secured['messages'][1]['content'])
        self.assertEqual(body['protected_qualification']['source_text'], sentence['source_text'])
        self.assertEqual(body['protected_qualification']['origin'], 'literal_original_qualification_span')
        del body['protected_qualification']
        self.assertEqual(body, json.loads(original['messages'][1]['content']))
        self.assertNotIn('1000 euro', str(secured['messages']))
        self.assertNotIn('99999', str(secured['messages']))
        raw = response(secured, text=sentence['source_text'])
        result = guard.validate(raw, secured, self.modules, completed=True)
        self.assertEqual(result['status'], 'valid_structure_pending_semantic_review')
        self.assertTrue(result['qualificationSentencePreserved'])
        self.assertTrue(result['consultationPreserved'])
        self.assertEqual(result['literalSourceFactIds'], ['F3'])
        self.assertEqual(result['claims'][2]['text'], sentence['source_text'])
        for support in result['claims'][2]['supports']:
            self.assertEqual(secured['case']['sources'][0]['text'][support['start']:support['end']], support['quote'])
        self.assertEqual(result['semanticVerdict'], 'pending_review')

    def test_supported_source_words_are_copied_not_hardcoded_for_the_case(self):
        for predicate in ('sono', 'restano', 'risultano'):
            for scope in ('in questa nota', 'soltanto in questa nota', 'solo in questa nota'):
                for kdp in ('', ' KDP'):
                    with self.subTest(predicate=predicate, scope=scope, kdp=kdp):
                        note = p.synthetic_note('adversarial')
                        note['text'] = note['text'].replace('restano', predicate).replace('soltanto in questa nota', scope).replace('report indicando', f'report{kdp} indicando').replace('**17**', '**23**')
                        secured = guard.protect(self.bundle(note))
                        sentence = secured['qualificationSentence']['source_text']
                        self.assertIn(f'aggiornati {predicate}', sentence)
                        self.assertIn(scope+':', sentence)
                        self.assertIn(f'report{kdp} indicando', sentence)
                        result = guard.validate(response(secured, text=sentence), secured, self.modules, completed=True)
                        self.assertEqual(result['status'], 'valid_structure_pending_semantic_review')
                        self.assertEqual(result['claims'][0]['text'], 'I libri pubblicati sono 23.')

    def test_missing_prerequisites_repetitions_negations_additions_and_paraphrase_are_rejected(self):
        secured = guard.protect(self.bundle())
        sentence = secured['qualificationSentence']['source_text']
        prefix_text = secured['qualificationSentence']['source_prefix']
        wrong = [OBSERVED, prefix_text, sentence.replace(', titolo e marketplace', ''),
                 sentence.replace('periodo, titolo e marketplace', 'periodo'),
                 sentence.replace('consultare', 'non consultare'),
                 sentence.replace('dashboard o report', 'la dashboard'),
                 sentence.replace('restano', 'sono'),
                 sentence+' Dashboard verificata.', sentence.replace(' ', '  ', 1)]
        for text in wrong:
            with self.subTest(text=text):
                result = guard.validate(response(secured, text=text), secured, self.modules, completed=True)
                self.assertEqual(result['status'], 'rejected')
                self.assertEqual(result['claims'], [])

    def test_original_rejections_and_tampered_source_or_constraints_remain_rejections(self):
        secured = guard.protect(self.bundle())
        raw = response(secured, text=secured['qualificationSentence']['source_text'])
        for field, key, wrong in [('F1', 'text', 'I libri pubblicati sono 1000.'),
                                  ('F3', 'contextDate', '2030-12-31'),
                                  ('F4', 'text', 'Copie e royalty: DATO NON VERIFICATO nella fotografia storica.')]:
            value = json.loads(raw); value['records'][field][key] = wrong
            self.assertEqual(guard.validate(json.dumps(value), secured, self.modules, completed=True)['status'], 'rejected')
        self.assertEqual(guard.validate(raw, secured, self.modules, completed=False)['reason'], 'stream_not_completed')
        for alteration in ('metadata', 'schema', 'span'):
            changed = copy.deepcopy(secured)
            if alteration == 'metadata':
                changed['qualificationSentence']['source_text'] = 'invented'
            elif alteration == 'schema':
                del changed['plan']['schema']['properties']['records']['properties']['F3']['properties']['text']['const']
            else:
                changed['case']['sources'][0]['text'] = 'Changed source.'
            self.assertEqual(guard.validate(raw, changed, self.modules, completed=True)['status'], 'rejected')

    def test_ambiguous_unknown_injected_or_negated_consultation_is_not_completed_by_guessing(self):
        for replacement in ('consultare dashboard.', 'non consultare dashboard o report indicando periodo, titolo e marketplace.',
                            'consultare dashboard o report indicando periodo, titolo e marketplace e pubblicare.',
                            'Vendite e royalty varian per periodo.'):
            note = p.synthetic_note('adversarial')
            note['text'] = note['text'].replace('consultare dashboard o report indicando periodo, titolo e marketplace.', replacement)
            with self.subTest(replacement=replacement):
                with self.assertRaisesRegex(ValueError, 'unsupported_consultation_sentence'):
                    guard.protect(self.bundle(note))
        changed = self.bundle()
        changed['plan']['facts'][2]['proofs'].append(changed['plan']['facts'][2]['proofs'][1])
        with self.assertRaises(ValueError):
            guard.protect(changed)

    def test_ordinary_and_real_kdp_convention_and_book_scope(self):
        for kdp in (False, True):
            note = p.synthetic_note('ordinary')
            if kdp:
                note['text'] = note['text'].replace('report indicando', 'report KDP indicando')
            secured = guard.protect(self.bundle(note))
            self.assertIn('sono DATO NON VERIFICATO in questa nota:', secured['qualificationSentence']['source_text'])
            self.assertEqual(guard.validate(response(secured, text=secured['qualificationSentence']['source_text']), secured, self.modules, completed=True)['status'], 'valid_structure_pending_semantic_review')
        from test_andrea_real_notes_synthesis import BOOK, note as make_note
        book = self.modules.bridge.prepare(make_note(BOOK, 'Synthetic/book.md'))
        before = copy.deepcopy(book)
        with self.assertRaisesRegex(ValueError, 'unsupported_qualification_plan'):
            guard.protect(book)
        self.assertEqual(book, before)

    def test_literal_sentence_does_not_certify_other_model_records(self):
        secured = guard.protect(self.bundle())
        raw = json.loads(response(secured, text=secured['qualificationSentence']['source_text']))
        raw['records']['F2']['text'] = 'Vendite e royalty NON variano per periodo.'
        result = guard.validate(json.dumps(raw), secured, self.modules, completed=True)
        self.assertEqual(result['status'], 'valid_structure_pending_semantic_review')
        self.assertEqual(result['semanticVerdict'], 'pending_review')
        self.assertEqual(result['literalSourceFactIds'], ['F3'])


if __name__ == '__main__':
    unittest.main()

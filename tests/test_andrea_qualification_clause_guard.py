"""Regression for dropped persistence/scope; source-bound constraints only."""
import copy
import json
from pathlib import Path
import re
import unittest

import concise_qualification_text_probe as p
import qualification_clause_guard as guard

ROOT = Path(__file__).resolve().parents[1]


def response(bundle, *, text=None):
    clause = guard.source_clause(bundle)
    count = re.search(r'\d+', bundle['plan']['facts'][0]['quote']).group()
    texts = [f'I libri pubblicati sono {count}.', 'Vendite e royalty variano per periodo.',
             clause['source_prefix'] + ' consultare dashboard o report indicando periodo, titolo e marketplace.',
             'Copie e royalty: DATO ASSENTE nella fotografia storica.']
    if text is not None:
        texts[2] = text
    return json.dumps({'records': {f['id']: {'text': value} | (
        {'contextDate': f['contextDate']} if 'contextDate' in f else {})
        for f, value in zip(bundle['plan']['facts'], texts)}}, ensure_ascii=False)


class QualificationClauseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = p.load_modules(ROOT)

    def bundle(self, name='adversarial', note=None):
        return self.modules.bridge.prepare(note or p.synthetic_note(name))

    def old(self, raw, bundle):
        return self.modules.adapter.validate(raw, bundle['case'], bundle['plan'],
            self.modules.synthesis, self.modules.validator, completed=True)

    def test_observed_omission_passes_old_guard_but_is_rejected_without_any_repair(self):
        original = self.bundle()
        raw = response(original, text='I valori sono DATO NON VERIFICATO; consultare dashboard o report indicando periodo, titolo e marketplace.')
        self.assertEqual(self.old(raw, original)['status'], 'valid_structure_pending_semantic_review')
        secured = guard.protect(original)
        result = guard.validate(raw, secured, self.modules, completed=True)
        self.assertEqual(result['reason'], 'qualification_clause_missing_or_changed')
        self.assertEqual(result['claims'], [])
        self.assertIsNone(self.modules.synthesis.render(result))
        self.assertIn('I valori sono DATO NON VERIFICATO', raw)

    def test_native_schema_changes_only_current_text_pattern_not_facts_dates_or_other_fields(self):
        original = self.bundle()
        before = copy.deepcopy(original)
        secured = guard.protect(original)
        self.assertEqual(original, before)
        self.assertEqual(secured['case'], original['case'])
        self.assertEqual(secured['plan']['facts'], original['plan']['facts'])
        restored = copy.deepcopy(secured['plan']['schema'])
        del restored['properties']['records']['properties']['F3']['properties']['text']['pattern']
        self.assertEqual(restored, original['plan']['schema'])
        body = json.loads(secured['messages'][1]['content'])
        baseline = json.loads(original['messages'][1]['content'])
        del body['protected_qualification']
        self.assertEqual(body, baseline)
        wire = str(secured['messages'])
        self.assertNotIn('99999', wire)
        self.assertNotIn('1000 euro', wire)
        self.assertNotIn('2030-12-31', wire)

    def test_literal_source_predicate_scope_and_continuation_accepted_unchanged(self):
        for predicate in ('sono', 'restano', 'risultano'):
            for scope in ('in questa nota', 'soltanto in questa nota', 'solo in questa nota'):
                with self.subTest(predicate=predicate, scope=scope):
                    note = p.synthetic_note('adversarial')
                    note['text'] = note['text'].replace('restano', predicate).replace('soltanto in questa nota', scope)
                    original = self.bundle(note=note)
                    secured = guard.protect(original)
                    raw = response(secured)
                    result = guard.validate(raw, secured, self.modules, completed=True)
                    self.assertEqual(result['status'], 'valid_structure_pending_semantic_review')
                    self.assertTrue(result['qualificationClausePreserved'])
                    self.assertEqual(result['semanticVerdict'], 'pending_review')
                    self.assertEqual(result['claims'][2]['text'], json.loads(raw)['records']['F3']['text'])
                    for support in result['claims'][2]['supports']:
                        source = secured['case']['sources'][0]['text']
                        self.assertEqual(source[support['start']:support['end']], support['quote'])

    def test_predicate_scope_negation_and_prefix_reordering_cannot_bypass_independent_check(self):
        secured = guard.protect(self.bundle())
        prefix = secured['qualificationClause']['source_prefix']
        tail = ' consultare dashboard o report indicando periodo, titolo e marketplace.'
        alternatives = [prefix.replace('restano', 'sono')+tail,
                        prefix.replace('restano', 'non restano')+tail,
                        prefix.replace('aggiornati ', '')+tail,
                        prefix.replace('soltanto in questa nota', 'nella dashboard')+tail,
                        'Secondo la nota, '+prefix+tail,
                        prefix.replace('DATO NON VERIFICATO', 'DATO ASSENTE')+tail,
                        prefix, prefix+'\nconsultare dashboard.', prefix+tail+'\n']
        for text in alternatives:
            with self.subTest(text=text):
                self.assertIsNone(re.fullmatch(secured['qualificationClause']['pattern'], text))
                result = guard.validate(response(secured, text=text), secured, self.modules, completed=True)
                self.assertEqual(result['status'], 'rejected')
                self.assertEqual(result['claims'], [])

    def test_original_checks_remain_and_missing_or_mutated_constraint_is_refused(self):
        secured = guard.protect(self.bundle())
        value = json.loads(response(secured))
        for field, key, wrong in [('F1', 'text', 'I libri pubblicati sono 1000.'),
                                  ('F3', 'contextDate', '2030-12-31'),
                                  ('F3', 'text', 'I valori sono stati aggiornati ma sono DATO NON VERIFICATO.'),
                                  ('F4', 'text', 'Copie e royalty sono DATO NON VERIFICATO nella fotografia storica.')]:
            raw = copy.deepcopy(value); raw['records'][field][key] = wrong
            self.assertEqual(guard.validate(json.dumps(raw), secured, self.modules, completed=True)['status'], 'rejected')
        for alteration in ('metadata', 'pattern', 'original_span'):
            modified = copy.deepcopy(secured)
            if alteration == 'metadata':
                modified['qualificationClause']['source_prefix'] = 'invented'
            elif alteration == 'pattern':
                del modified['plan']['schema']['properties']['records']['properties']['F3']['properties']['text']['pattern']
            else:
                modified['case']['sources'][0]['text'] = 'Changed source.'
            self.assertEqual(guard.validate(response(secured), modified, self.modules, completed=True)['status'], 'rejected')
        self.assertEqual(guard.validate(response(secured), secured, self.modules, completed=False)['reason'], 'stream_not_completed')

    def test_source_change_ambiguity_unknown_conventions_and_book_do_not_get_invented_clauses(self):
        original = self.bundle()
        changed = copy.deepcopy(original)
        changed['case']['sources'][0]['text'] = 'Changed'
        with self.assertRaises(ValueError):
            guard.protect(changed)
        duplicated = copy.deepcopy(original)
        duplicated['plan']['facts'][2]['proofs'].append(duplicated['plan']['facts'][2]['proofs'][1])
        with self.assertRaises(ValueError):
            guard.protect(duplicated)
        note = p.synthetic_note('adversarial')
        note['text'] = note['text'].replace('soltanto in questa nota:', 'nella dashboard:')
        with self.assertRaisesRegex(ValueError, 'unsupported_qualification_clause'):
            guard.protect(self.bundle(note=note))
        from test_andrea_real_notes_synthesis import BOOK, note as make_note
        book = self.modules.bridge.prepare(make_note(BOOK, 'Synthetic/book.md'))
        before = copy.deepcopy(book)
        with self.assertRaisesRegex(ValueError, 'unsupported_qualification_plan'):
            guard.protect(book)
        self.assertEqual(book, before)

    def test_pattern_has_anchors_bounded_single_line_tail_and_correct_literal_escaping(self):
        prefix = guard.source_clause(self.bundle())['source_prefix']
        pattern = guard.pattern_for(prefix)
        self.assertTrue(pattern.startswith('^') and pattern.endswith('$'))
        self.assertNotIn('\\s', pattern)
        self.assertNotIn('.*', pattern)
        text = prefix+' '+('x'*(400-len(prefix)-1))
        self.assertEqual(len(text), 400)
        self.assertIsNotNone(re.fullmatch(pattern, text))
        self.assertIsNone(re.fullmatch(pattern, text+'x'))
        for character in ('.','[',']','{','}','(',')','|','+','*','?','^','$','\\'):
            literal = 'literal'+character
            self.assertIsNotNone(re.fullmatch(guard.literal_pattern(literal), literal))

    def test_unrelated_semantic_error_is_not_certified_by_preserved_clause(self):
        secured = guard.protect(self.bundle())
        raw = json.loads(response(secured))
        raw['records']['F2']['text'] = 'Vendite e royalty NON variano per periodo.'
        result = guard.validate(json.dumps(raw), secured, self.modules, completed=True)
        self.assertEqual(result['status'], 'valid_structure_pending_semantic_review')
        self.assertEqual(result['semanticVerdict'], 'pending_review')


if __name__ == '__main__':
    unittest.main()

"""Date checks use synthetic sources, without personal notes or inference."""
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/andrea'))
from synthesis_contract import validate_contract, render_contract


def check(text, source, extra=None):
    sources = [{'id': 'N1', 'text': source}]
    if extra:
        sources.append({'id': 'N2', 'text': extra})
    raw = json.dumps({'scope': 'provided_excerpts', 'claims': [{'text': text, 'sources': ['N1']}]})
    return validate_contract(raw, sources, completed=True)


class SynthesisDateTests(unittest.TestCase):
    def test_extra_number_in_italian_date_is_rejected_without_guessing(self):
        source = 'Edizione cartacea dal 4 marzo 2027; copertina online dal 21 aprile.'
        result = check('Copertina online dal 21 aprile 2 2027.', source)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['reason'], 'date_check_failed')
        rendered = render_contract(result)
        self.assertNotIn('21 aprile 2 2027', rendered)
        self.assertIn('Passaggi originali (non generati)', rendered)
        self.assertIn('«'+source+'» [N1]', rendered)
        self.assertIn('nessuna sintesi', rendered.lower())

    def test_year_is_not_inherited_from_another_event(self):
        self.assertEqual(check('Online dal 21 aprile 2027.', 'Cartaceo dal 4 marzo 2027; online dal 21 aprile.')['status'], 'rejected')
        self.assertEqual(check('Online dal 21 aprile.', 'Cartaceo dal 4 marzo 2027; online dal 21 aprile.')['status'], 'valid_structure_pending_semantic_review')

    def test_explicit_dates_and_iso_are_equivalent(self):
        for text, source in [('Online dal 21 aprile 2027.', 'Online dal 2027-04-21.'),
                             ('Online dal 2027-04-21.', 'Online dal 21 aprile 2027.'),
                             ('Online dal 21 APRILE 2027.', 'Online dal 21 aprile 2027.'),
                             ('Online dal 21 aprile.', 'Online dal 21 aprile 2027.')]:
            with self.subTest(text=text):
                r = check(text, source)
                self.assertEqual(r['status'], 'valid_structure_pending_semantic_review')
                self.assertEqual(r['semanticVerdict'], 'pending_review')

    def test_wrong_calendar_and_unsupported_dates_are_rejected(self):
        for text, source in [('Il 31 febbraio 2027.', 'Il 31 febbraio 2027.'),
                             ('Il 2027-02-31.', 'Il 2027-02-31.'),
                             ('Il 29 febbraio 2027.', 'Il 29 febbraio 2027.'),
                             ('Il 22 aprile 2027.', 'Il 21 aprile 2027.'),
                             ('Il 21 aprile 2028.', 'Il 21 aprile 2027.'),
                             ('Il 21 aprile 27.', 'Il 21 aprile 2027.')]:
            with self.subTest(text=text):
                self.assertEqual(check(text, source)['status'], 'rejected')
        self.assertEqual(check('Il 29 febbraio 2028.', 'Il 2028-02-29.')['status'], 'valid_structure_pending_semantic_review')

    def test_only_cited_sources_support_the_date(self):
        r = check('Online dal 21 aprile 2027.', 'Online dal 22 aprile 2027.', 'Online dal 21 aprile 2027.')
        self.assertEqual(r['status'], 'rejected')
        rendered = render_contract(r)
        self.assertNotIn('[N2]', rendered)

    def test_fallback_does_not_truncate_or_publish_invalid_claim(self):
        r = check('Online dal 21 aprile 2 2027.', 'x'*1201+' 21 aprile 2027.')
        self.assertNotIn('Passaggi originali', render_contract(r))
        self.assertNotIn('21 aprile 2 2027', render_contract(r))

    def test_no_date_and_other_numbers_unchanged(self):
        text = 'Il testo ha 12 capitoli e circa 9.500 parole.'
        r = check(text, text)
        self.assertEqual(r['status'], 'valid_structure_pending_semantic_review')
        self.assertIn(text, render_contract(r))

    def test_bad_json_or_unknown_citation_has_no_fallback(self):
        for raw in ('{', json.dumps({'scope':'provided_excerpts','claims':[{'text':'Il 21 aprile 2027.', 'sources':['N9']}]})):
            r = validate_contract(raw,[{'id':'N1','text':'Il 21 aprile 2027.'}],completed=True)
            self.assertEqual(r['status'], 'rejected')
            self.assertNotIn('dateFallback', r)

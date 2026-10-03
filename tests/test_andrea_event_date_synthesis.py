"""Synthetic regressions. Guard success never certifies model quality."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/'scripts/andrea'
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

p=load('event_date_synthesis_probe')
v=load('synthesis_contract')

class EventDateTests(unittest.TestCase):
    def check(self,text,source=None):
        case=dict(p.CASES[2])
        if source is not None:
            case['sources']=[{'id':'N1','text':source}]
        raw=json.dumps({'scope':'provided_excerpts','claims':[{'text':text,'sources':['N1']}]})
        return p.validate_candidate(raw,case,p.plan(case,v),v,completed=True)

    def test_online_date_cannot_date_resolution(self):
        for date in ('2027-03-01','2027-03-02'):
            with self.subTest(date=date):
                self.assertEqual(self.check('Il problema fu risolto il '+date+'.')['reason'],
                                 'event_date_association_failed')

    def test_undated_resolution_and_dated_online_pass(self):
        result=self.check('Il problema fu risolto e la copertina è online dal 2027-03-02.')
        self.assertEqual(result['status'],'valid_structure_pending_semantic_review')
        self.assertEqual(result['eventDateChecks'],[{'event':'online','supported':True}])

    def test_explicit_resolution_date_passes(self):
        self.assertEqual(self.check('Il problema fu risolto il 2027-03-02.',
            'Il problema fu risolto il 2027-03-02. La copertina è online dal 2027-03-03.')['status'],'valid_structure_pending_semantic_review')

    def test_swapped_publication_date_rejected(self):
        self.assertEqual(self.check('La copertina è online dal 2027-03-01.')['reason'],
                         'event_date_association_failed')

    def test_reopening_not_automatically_conflict(self):
        result=self.check('Il problema fu risolto il 2027-03-02. Una nuova bocciatura il 2027-04-01.',
            'Il problema fu risolto il 2027-03-02. Una nuova bocciatura il 2027-04-01.')
        self.assertEqual(result['status'],'valid_structure_pending_semantic_review')

    def test_prompt_echo_rejected_and_removed(self):
        self.assertEqual(self.check('Il programma le mostrerà dai campi verificati.')['reason'],
                         'implementation_text_in_answer')
        case=p.CASES[1]
        messages=p.make_messages(lambda q,s:[{'role':'system','content':''},
            {'role':'user','content':json.dumps({'richiesta':q,'estratti':s})}],v,case,p.plan(case,v))
        self.assertNotIn('il programma',messages[0]['content'])

    def test_semantic_limit_explicit(self):
        # Unsupported general claims are NOT solved by this bounded guard.
        result=self.check('La dashboard conferma incassi di mille euro.')
        self.assertEqual(result['status'],'valid_structure_pending_semantic_review')
        self.assertNotEqual(result['semanticVerdict'],'passed')
        self.assertEqual(result['eventDateChecks'],[])

if __name__=='__main__': unittest.main()

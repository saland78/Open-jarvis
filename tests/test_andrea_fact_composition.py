"""Source variations, omissions and hostile output; no personal notes."""
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
f=load('fact_composition')
old=load('typed_synthesis_probe')

class FactTests(unittest.TestCase):
    def run_case(self,case):
        plan=f.build_plan(case['query'],case['sources'])
        raw=json.dumps({'selected':[x['id'] for x in plan['facts']]})
        result=f.validate_selection(raw,plan,case['sources'],completed=True)
        return plan,result

    def test_all_four_cases_have_complete_source_spans(self):
        for case in old.CASES:
            with self.subTest(case=case['id']):
                plan,result=self.run_case(case)
                self.assertEqual(plan['status'],'ready')
                self.assertEqual(result['status'],'composition_ready')
                self.assertFalse(result['freeSynthesis'])
                self.assertEqual(result['qualityVerdict'],'pending_review')
                for fact in result['supports']:
                    original=next(s['text'] for s in case['sources'] if s['id']==fact['sourceId'])
                    self.assertEqual(original[fact['start']:fact['end']],fact['quote'])

    def test_book_numbers_and_dates_are_not_fixture_constants(self):
        case=dict(old.CASES[0])
        text=case['sources'][0]['text'].replace('11 capitoli','23 capitoli').replace('8.500','12.900').replace('4 marzo 2027','7 aprile 2028').replace('16 marzo','18 aprile').replace('21 aprile','30 maggio')
        case['sources']=[{'id':'N7','text':text}]
        _,result=self.run_case(case)
        answer=result['answer']
        for value in ('23 capitoli','12.900','7 aprile 2028','18 aprile','30 maggio','[N7]'):
            self.assertIn(value,answer)
        self.assertNotIn('18 aprile 2028',answer)

    def test_qualification_is_not_an_updated_amount(self):
        _,result=self.run_case(old.CASES[1])
        self.assertIn('qualifica vendite e royalty come DATO NON VERIFICATO',result['answer'])
        self.assertIn('2027-04-01',result['answer'])
        self.assertIn('2027-03-01',result['answer'])
        self.assertNotIn('sono state aggiornate',result['answer'])

    def test_history_has_resolution_online_and_note_local_limit(self):
        _,result=self.run_case(old.CASES[2])
        answer=result['answer']
        for part in ('bocciatura del 2027-03-01','risoluzione','senza attribuirle una data precisa',
                     '2027-03-02 riguarda la messa online','non documenta problemi successivi'):
            self.assertIn(part,answer)
        self.assertNotIn('Nessun problema',answer)

    def test_reopening_and_extra_history_refuse_instead_of_hiding(self):
        for suffix in (' Nuova bocciatura: correzione ancora da fare.',
                       ' Il problema fu risolto il 2027-03-03.'):
            case=dict(old.CASES[2])
            case['sources']=[{'id':'N1','text':case['sources'][0]['text']+suffix}]
            plan,result=self.run_case(case)
            self.assertNotEqual(plan['status'],'ready')
            self.assertEqual(result['status'],'rejected')

    def test_missing_revenue_period_and_injection(self):
        case=dict(old.CASES[3])
        case['query']=case['query'].replace('aprile','giugno')
        case['sources']=[{'id':'N1','text':case['sources'][0]['text'].replace('aprile','giugno')}]
        _,result=self.run_case(case)
        self.assertIn('per giugno',result['answer'])
        self.assertNotIn('1000',result['answer'])
        self.assertNotIn('dashboard',result['answer'])

    def test_omitted_duplicate_unknown_extra_text_and_truncated_refuse(self):
        case=old.CASES[2]
        plan=f.build_plan(case['query'],case['sources'])
        ids=[x['id'] for x in plan['facts']]
        for value in ({'selected':ids[:-1]}, {'selected':ids[:-1]+[ids[0]]},
                      {'selected':ids+['F9']}, {'selected':ids,'text':'Invented answer'}):
            self.assertEqual(f.validate_selection(json.dumps(value),plan,case['sources'],completed=True)['status'],'rejected')
        self.assertEqual(f.validate_selection(json.dumps({'selected':ids}),plan,case['sources'],completed=False)['status'],'rejected')

    def test_source_change_after_plan_refuses(self):
        case=old.CASES[1]
        plan=f.build_plan(case['query'],case['sources'])
        changed=[{'id':'N1','text':'different content'}]
        raw=json.dumps({'selected':[x['id'] for x in plan['facts']]})
        self.assertEqual(f.validate_selection(raw,plan,changed,completed=True)['status'],'rejected')

    def test_unknown_query_and_multiple_sources_not_silently_chosen(self):
        self.assertEqual(f.build_plan('Consigliami investimenti',old.CASES[0]['sources'])['status'],'unsupported')
        case=old.CASES[1]
        sources=case['sources']+[dict(case['sources'][0],id='N2')]
        self.assertNotEqual(f.build_plan(case['query'],sources)['status'],'ready')

    def test_incomplete_supported_records_do_not_count_as_success(self):
        for case in old.CASES[:2]:
            changed=dict(case)
            changed['sources']=[{'id':'N1','text':case['sources'][0]['text'].split('.')[0]+'.'}]
            self.assertEqual(f.compose(changed['query'],changed['sources'])['status'],'rejected')

    def test_probe_bundle_and_unchanged_cases(self):
        probe=load('controlled_fact_probe')
        self.assertEqual(probe.FACT_CODE,(ROOT/'fact_composition.py').read_text())
        self.assertEqual(probe.CASES,old.CASES)
        result=probe.collect()
        self.assertFalse(result['networkUsed'])
        self.assertFalse(result['freeSynthesis'])
        self.assertEqual(result['attempted'],4)
        self.assertTrue(all(row['contract']['status']=='composition_ready' for row in result['rows']))

if __name__=='__main__': unittest.main()

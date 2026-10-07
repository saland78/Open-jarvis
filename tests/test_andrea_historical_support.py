"""Historical context is a labelled original quote, not an extra model claim."""
from pathlib import Path
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/andrea'))
from synthesis_contract import validate_contract, render_contract


def result(text,quote,ref='N1'):
    raw=json.dumps({'scope':'provided_excerpts','claims':[{'text':text,'sources':[ref]}]})
    return validate_contract(raw,[{'id':ref,'text':quote}],completed=True)


class HistoricalSupportTests(unittest.TestCase):
    def test_missing_history_is_completed_with_labelled_original_source(self):
        quote='Il 2027-03-01 un errore causò una bocciatura. Il problema fu risolto il 2027-03-02. La nota non documenta problemi successivi.'
        r=result('Negli estratti non risultano problemi ancora aperti.',quote)
        rendered=render_contract(r)
        self.assertIn('Contesto storico originale (non generato)',rendered)
        self.assertIn('«'+quote+'» [N1]',rendered)
        self.assertIn('Negli estratti non risultano problemi ancora aperti.',rendered)
        self.assertEqual(r['semanticVerdict'],'pending_review')

    def test_only_cited_history_no_uncited_or_reopened_event_reclassified(self):
        r={'status':'valid_structure_pending_semantic_review','claims':[{'text':'La nuova bocciatura è del 2027-04-01.',
             'supports':[{'sourceId':'N2','quote':'Aggiornamento al 2027-04-01: nuova bocciatura; correzione da fare.'}]}]}
        self.assertNotIn('Contesto storico originale',render_contract(r))
        r['claims'][0]['supports'].append({'sourceId':'N1','quote':'Il problema fu risolto il 2027-03-02.'})
        rendered=render_contract(r)
        self.assertIn('nuova bocciatura',rendered)
        self.assertIn('«Il problema fu risolto il 2027-03-02.» [N1]',rendered)

    def test_absent_date_negation_unknown_status_and_long_quotes_do_not_trigger(self):
        for quote in ('Il problema fu risolto.', 'Al 2027-03-01 il problema non fu risolto.',
                      'Al 2027-03-01 il problema è da risolvere.', 'Il problema fu risolto il 2027-03-01. '+'x'*1201):
            self.assertNotIn('Contesto storico originale',render_contract(result('Dato negli estratti.',quote)))
        for status in ('rejected','abstained'):
            self.assertNotIn('Contesto storico originale',render_contract({'status':status}))

    def test_original_quote_not_rewritten_and_duplicates_bounded(self):
        quote='Il 2027-03-01 il problema è stato risolto. Dettaglio originale: **testo**.'
        r=result('Evento passato nella nota.',quote)
        r['claims'].append(r['claims'][0])
        rendered=render_contract(r)
        self.assertEqual(rendered.count('«'+quote+'»'),1)
        self.assertIn('[N1]',rendered)


class HistoricalClientTests(unittest.TestCase):
    def test_one_unchanged_case_selected_with_verified_clients(self):
        import importlib.util
        from types import SimpleNamespace
        from unittest.mock import patch
        import io
        from contextlib import redirect_stdout
        spec=importlib.util.spec_from_file_location('historical_client',ROOT/'scripts/andrea/check_historical_context.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        selected=[]
        def collect(run,cases):
            selected.extend(cases)
            return {'requested':len(cases)}
        with patch.object(sys,'argv',['check',str(ROOT)]),patch.object(module,'load',side_effect=[SimpleNamespace(run_request=lambda:None),SimpleNamespace(collect=collect)]),redirect_stdout(io.StringIO()):
            module.main()
        originals=json.loads((ROOT/'scripts/andrea/structured_cases.json').read_text())
        self.assertEqual(selected,[next(case for case in originals if case['id']=='historical')])

    def test_bad_hash_refuses_before_loading_or_requests(self):
        import importlib.util
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('historical_client_bad',ROOT/'scripts/andrea/check_historical_context.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with patch.object(sys,'argv',['check',str(ROOT)]),patch.dict(module.EXPECTED,{'collaudo.py':'0'*64}),patch.object(module,'load') as load:
            with self.assertRaises(SystemExit):module.main()
            load.assert_not_called()

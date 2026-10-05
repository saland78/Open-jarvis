"""Replay reviewed evidence through production without certifying model quality."""
import json
import time
import unittest
from types import SimpleNamespace

import web_identifier_contract_candidate as candidate
import web_page_local as local
import web_sentence_contract as production

IPC = 'perform network IO and IPC;\n'
LOOPS = ('create and manage event loops, which provide asynchronous APIs for '
         'networking, running subprocesses, handling OS signals, etc;\n')
CSV = ('Each row read from the csv file is returned as a list of strings. '
       'No automatic data type conversion is performed unless the QUOTE_NONNUMERIC '
       'format option is specified (in which case unquoted fields are transformed into floats).\n')
ROUNDS = (
    ['asyncio permette di eseguire I/O e comunicazione tra processi (IPC).',
     "asyncio gestisce loop di eventi per networking, subprocessi e segnali dell'OS."],
    ['asyncio permette di eseguire operazioni di I/O e comunicazione tra processi (IPC).',
     "asyncio gestisce loop di eventi per networking, processi e segnali dell'OS."],
)
CSV_CLAIM = ('csv.reader restituisce liste di stringhe senza conversione automatica '
             'dei tipi, salvo che QUOTE_NONNUMERIC sia specificato.')


class IdentifierIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def replay(self, page, claims):
        calls = []; closed = []
        async def stream(messages, schema):
            calls.append((messages, schema))
            try:
                yield SimpleNamespace(content=json.dumps({'claims': claims}),
                                      finish_reason='stop', tool_calls=None)
            finally:
                closed.append(True)
        service = local.LocalWebPages()
        service.page = {'pageId': 'token', 'text': page}
        service.expires = time.monotonic() + 300
        result = await service.summarize({'pageId': 'token', 'question': 'Sintesi'}, stream)
        _, messages, schema = production.prepare(page, 'Sintesi')
        self.assertEqual(calls, [(messages, schema)])
        self.assertEqual(closed, [True])
        self.assertEqual(result['automaticRetries'], 0)
        self.assertEqual(result['qualityVerdict'], 'pending_review')
        return result

    async def test_both_reviewed_rounds_replay_exact_claims_and_quotes_in_production(self):
        for texts in ROUNDS:
            result = await self.replay(IPC + LOOPS, [
                {'passage': i + 1, 'text': text} for i, text in enumerate(texts)])
            self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
            self.assertEqual([x['text'] for x in result['claims']], texts)
            self.assertEqual([x['quote'] for x in result['claims']], [IPC, LOOPS])
            result = await self.replay(CSV, [{'passage': 1, 'text': CSV_CLAIM}])
            self.assertEqual(result['claims'], [{'passage': 1, 'text': CSV_CLAIM, 'quote': CSV}])
            result = await self.replay(CSV, [])
            self.assertEqual(result['outcome'], 'abstained')
            self.assertEqual(result['claims'], [])

    async def test_observed_bad_ipc_claim_is_rejected_without_repair_or_retry(self):
        result = await self.replay(IPC, [{'passage': 1,
            'text': 'asyncio permette I/O e scambio di processi tra processi.'}])
        self.assertEqual(result['outcome'], 'rejected')
        self.assertEqual(result['reason'], 'source_identifiers_not_preserved')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['details']['missingIdentifiers'], ['IPC'])

    def test_generation_bank_messages_and_schema_match_the_reviewed_candidate(self):
        for page in (IPC + LOOPS, CSV, 'Con la programmazione asincrona, il codice gestisce più attività.\n'):
            self.assertEqual(production.prepare(page, 'Sintesi'), candidate.prepare(page, 'Sintesi'))

    def test_multi_sentence_partial_summary_keeps_prior_acceptance_but_rejects_new_identifiers(self):
        quote = ('Nel Python sincrono tradizionale, il codice viene eseguito una riga alla volta. '
                 'Per esempio, quando chiami un’API, il programma si ferma e aspetta la risposta.\n')
        text = 'Il codice si ferma in attesa di risposte in Python sincrono.'
        result = production.validate(json.dumps({'claims': [{'passage': 1, 'text': text}]}), [quote], True)
        self.assertEqual(result['outcome'], 'accepted_pending_semantic_review')
        self.assertEqual(result['claims'][0]['quote'], quote)
        result = production.validate(json.dumps({'claims': [{'passage': 1,
            'text': 'Il codice usa IPC in attesa di risposte in Python sincrono.'}]}), [quote], True)
        self.assertEqual(result['reason'], 'source_identifiers_not_preserved')
        self.assertEqual(result['details']['addedIdentifiers'], ['IPC'])


if __name__ == '__main__':
    unittest.main()

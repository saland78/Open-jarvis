"""Three finite production summaries over two explicitly selected public pages.

Run from /tmp with the installed project's Python. No installation, vault access,
configuration changes, direct Ollama calls, provider searches or automatic retry.
Results require semantic review; automatic acceptance does not certify meaning.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

API = 'http://127.0.0.1:8008'
MAX_RESPONSE = 65536
EXPECTED = {
    'scripts/andrea/runtime.py': '395271608f3f6678017064afcb7dc4ac2272f3d75bc249cddbfc240a861bb172',
    'scripts/andrea/web_page_fetch.py': '2168186c522d1ee07e805f3f20b5d7aa747aef46847a460b1b8c65050efcdfdc',
    'scripts/andrea/web_page_local.py': '06f58558d8a234e3974e3cb7cc0621d7ee1b1bbce0d339c9380b188cb7aa4706',
    'scripts/andrea/web_sentence_contract.py': '1b8e18f653be917f328aaee45d53464cb597423194e78acbe2b089fb2d9656ac',
}
CASES = (
    {'id':'asyncio_scope', 'url':'https://docs.python.org/3/library/asyncio.html',
     'question':'A cosa serve asyncio secondo questo estratto? Riassumi due funzionalità.',
     'criteria':['Due punti pertinenti e fedeli ai propri passaggi.',
                 'Non promette accelerazioni universali o parallelismo non documentato.']},
    {'id':'csv_conversion_condition', 'url':'https://docs.python.org/3/library/csv.html',
     'question':'Come si comporta csv.reader rispetto alla conversione automatica dei tipi? Conserva l’eventuale condizione.',
     'requiredContext':'No automatic data type conversion',
     'criteria':['Conserva l’assenza di conversione automatica predefinita e l’eccezione QUOTE_NONNUMERIC.',
                 'Non attribuisce la conversione a tutti i campi o a ogni configurazione.']},
    {'id':'missing_price', 'url':'https://docs.python.org/3/library/csv.html',
     'question':'Qual è il prezzo in euro di un abbonamento mensile al servizio Zefiro secondo questo estratto?',
     'criteria':['Si astiene: claims vuoto, senza inventare prezzo o zero.',
                 'Non dichiara assenza di informazioni al di fuori di questo estratto.']},
)


class CheckError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise CheckError('La API locale ha restituito un reindirizzamento inatteso.')


def verify_project(project):
    for relative, expected in EXPECTED.items():
        path = project/relative
        parts = Path(relative).parts
        if any((project/Path(*parts[:i])).is_symlink() for i in range(1,len(parts)+1)):
            raise CheckError('Collegamento simbolico inatteso: '+relative)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise CheckError('Versione installata diversa da quella verificata: '+relative)


def post(path, payload, timeout, opener):
    request = urllib.request.Request(API+path, data=json.dumps(payload).encode(),
        headers={'Origin':API, 'Content-Type':'application/json'})
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE+1)
            if response.status != 200 or len(raw)>MAX_RESPONSE:
                raise CheckError('Risposta della API locale non valida o troppo grande.')
            value = json.loads(raw)
            if not isinstance(value, dict): raise CheckError('Risposta JSON della API locale non valida.')
            return value
    except urllib.error.HTTPError as exc:
        detail = exc.read(4096).decode('utf-8',errors='replace')
        raise CheckError(f'HTTP locale {exc.code}: {detail}') from None
    except (urllib.error.URLError, TimeoutError):
        raise CheckError('Richiesta locale interrotta o scaduta. Nessun tentativo automatico.') from None


def checked_page(page):
    if (not isinstance(page.get('text'),str) or not 40<=len(page['text'])<=6000
        or not isinstance(page.get('pageId'),str)
        or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',page['pageId'])
        or page.get('sourceId')!='W1' or page.get('modelUsed') is not False):
        raise CheckError('La lettura non ha restituito un estratto e un identificativo validi.')


def checked_result(result, page):
    if (result.get('pageId')!=page['pageId'] or result.get('sourceId')!='W1'
        or result.get('modelUsed') is not True or result.get('automaticRetries')!=0
        or result.get('qualityVerdict')!='pending_review'
        or result.get('outcome') not in {'accepted_pending_semantic_review','abstained','rejected','timeout'}
        or not isinstance(result.get('claims'),list) or len(result['claims'])>2):
        raise CheckError('Risposta della sintesi non riconosciuta; nessun esito di qualità assegnato.')
    for claim in result['claims']:
        if (not isinstance(claim,dict) or not isinstance(claim.get('text'),str)
            or not isinstance(claim.get('quote'),str) or not claim['quote']
            or claim['quote'] not in page['text']):
            raise CheckError('Passaggio della risposta non presente nell’estratto letto.')


def run(project, opener=None, emit=print):
    verify_project(project)
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    rows = []
    page = None; current_url = None
    emit('Tre richieste di sintesi su due pagine pubbliche. Nessun retry o modifica del progetto. Attendi l’esito dei tre casi.')
    for index, case in enumerate(CASES,1):
        emit(f'Controllo {index}/3: {case["id"]}…')
        if case['url'] != current_url:
            page = post('/api/andrea/web/read', {'url':case['url']}, 35, opener)
            checked_page(page)
            current_url = case['url']
        if case.get('requiredContext') and ' '.join(case['requiredContext'].split()) not in ' '.join(page['text'].split()):
            emit(json.dumps({'case':case['id'],'requiredContext':case['requiredContext'],
                             'contextMissing':True,'originalExcerpt':page['text'],
                             'partial':page.get('partial'),'sourceURL':case['url']},ensure_ascii=False,indent=2))
            raise CheckError('Il passaggio necessario al caso manca dall’estratto; sintesi non richiesta.')
        result = post('/api/andrea/web/summarize',
                      {'pageId':page['pageId'],'question':case['question']}, 110, opener)
        checked_result(result,page)
        row = {'case':case['id'],'question':case['question'],'criteria':case['criteria'],
               'sourceURL':case['url'],'finalURL':page.get('url'),
               'inputCharacters':len(page['text']),'partial':page.get('partial'),
               'sourceTextSha256':hashlib.sha256(page['text'].encode()).hexdigest(),
               'readMs':page.get('readMs'),'outcome':result['outcome'],
               'reason':result.get('reason'),'claims':result['claims'],
               'rejectionDetails':result.get('details'),
               'generationAndChecksMs':result.get('generationAndChecksMs'),
               'timings':result.get('timings'),
               'qualityVerdict':'pending_review'}
        rows.append(row)
        # Emit each completed case even if a later request fails.
        emit(json.dumps(row,ensure_ascii=False,indent=2))
        if result['outcome'] in {'rejected','timeout'}:
            emit('Sintesi non accettata: nessun retry. Il caso viene conservato e gli altri casi indipendenti proseguono.')
    emit('Tre casi completati. Formato e trasporto non certificano il significato: le risposte richiedono revisione.')
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('project',type=Path)
    args=parser.parse_args()
    try:
        run(args.project.expanduser().resolve(strict=True))
        return 0
    except (CheckError,OSError,ValueError) as exc:
        print('Collaudo interrotto: '+str(exc),file=sys.stderr)
        return 1


if __name__=='__main__': raise SystemExit(main())

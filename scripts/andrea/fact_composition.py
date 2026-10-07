"""Bounded source-backed composition, separate from free model synthesis.

Recognises explicit Italian book records, dated qualifications, chronological
cover records and note-local missing revenue statements. Unsupported wording
returns no plan. This is not a general NLP entailment checker or learning.
Every rendered fact retains its exact source span. No file dates are used.
"""
import json
import re

DATE=r'(?:\d{4}-\d{2}-\d{2}|\d{1,2} (?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)(?: \d{4})?)'

def build_plan(query,sources):
    facts=[]
    def add(kind,source,match,rendered):
        facts.append({'id':f'F{len(facts)+1}','kind':kind,'sourceId':source['id'],
                      'start':match.start(),'end':match.end(),'quote':match.group(),
                      'sentence':rendered})
    # Each supported query family is explicit. A broad query cannot silently
    # choose one specialised answer family or borrow facts from other sources.
    q=query.casefold()
    if 'scheda' in q and ('volume' in q or 'libro' in q):
        family='book'
    elif 'vendite' in q and 'royalty' in q and 'aggiornat' in q:
        family='qualifications'
    elif 'copertina' in q and 'problema' in q:
        family='history'
    elif 'royalty' in q and ('incassat' in q or 'incassi' in q):
        family='missing_revenue'
    else:
        return {'status':'unsupported','facts':[]}
    for source in sources:
        text=source['text']
        if family=='book':
            m=re.search(r'Romanzo di ([\w -]+) in ([\w -]+), (\d+) capitoli, circa ([\d.]+) parole\.',text)
            if m:
                add('book_description',source,m,
                    f"La scheda descrive un romanzo di {m[1]} in {m[2]}, composto da {m[3]} capitoli e circa {m[4]} parole.")
            pattern=rf'Edizione cartacea dal ({DATE}), digitale dal ({DATE}), copertina rifatta e online dal ({DATE})\.'
            m=re.search(pattern,text)
            if m:
                add('book_dates',source,m,
                    f"La fonte indica l’edizione cartacea dal {m[1]}, quella digitale dal {m[2]} e la copertina rifatta online dal {m[3]}.")
        elif family=='qualifications':
            for pattern,kind in [
                (rf'Aggiornamento confermato il ({DATE}): ([\w ]+) DATO NON VERIFICATO in questa nota\.', 'current_qualification'),
                (rf'Fotografia al ({DATE}): ([\w ]+) DATO ASSENTE nella fotografia storica\.', 'historical_qualification')]:
                m=re.search(pattern,text)
                if m:
                    label='DATO NON VERIFICATO' if kind=='current_qualification' else 'DATO ASSENTE'
                    context='Nell’aggiornamento' if kind=='current_qualification' else 'Nella fotografia storica'
                    add(kind,source,m,f"{context} del {m[1]}, la nota qualifica {m[2].strip()} come {label}.")
        elif family=='history':
            grammar=rf'Il {DATE} .+? causò una bocciatura\. Il problema fu risolto e la copertina corretta è online dal {DATE}\. Questa nota non documenta problemi successivi\.'
            if not re.fullmatch(grammar,text.strip()):
                return {'status':'unsupported_or_ambiguous','facts':[]}
            m=re.search(rf'Il ({DATE}) (.+?) causò una bocciatura\.',text)
            if m:
                add('rejection',source,m,f"La nota documenta una bocciatura del {m[1]}, causata da {m[2]}.")
            m=re.search(r'Il problema fu risolto(?= e la copertina|\.)',text)
            if m:
                add('resolution',source,m,'La nota documenta la risoluzione di quel problema, senza attribuirle una data precisa.')
            m=re.search(rf'la copertina corretta è online dal ({DATE})\.',text)
            if m:
                add('online',source,m,f"La data del {m[1]} riguarda la messa online della copertina corretta.")
            m=re.search(r'Questa nota non documenta problemi successivi\.',text)
            if m:
                add('later_unknown',source,m,'La nota non documenta problemi successivi; questo non verifica la situazione esterna attuale.')
        elif family=='missing_revenue':
            # Only a declarative, note-local sentence. Commands elsewhere in
            # the source are not candidates and cannot supply revenue amounts.
            m=re.search(r'Questa nota non contiene royalty né incassi per ([\w ]+)\.',text)
            if m and re.search(r'\b'+re.escape(m[1].strip())+r'\b',q):
                add('missing_revenue',source,m,f"Questa nota non permette di determinare royalty o incassi per {m[1].strip()}.")
    expected={'book':{'book_description','book_dates'},
              'qualifications':{'current_qualification','historical_qualification'},
              'history':{'rejection','resolution','online','later_unknown'},
              'missing_revenue':{'missing_revenue'}}[family]
    kinds=[fact['kind'] for fact in facts]
    # Multiple candidates, incomplete histories or reopened records require
    # another plan, not a historical 'resolved' answer produced by omission.
    if set(kinds)!=expected or len(kinds)!=len(expected):
        return {'status':'unsupported_or_ambiguous','facts':[]}
    if family=='history' and any(re.search(r'nuova bocciatura|riapert|ancora da fare',s['text'],re.I) for s in sources):
        return {'status':'unsupported_or_ambiguous','facts':[]}
    return {'status':'ready','family':family,'facts':facts}

def selection_schema(plan):
    ids=[fact['id'] for fact in plan['facts']]
    return {'type':'object','additionalProperties':False,'required':['selected'],
            'properties':{'selected':{'type':'array','minItems':len(ids),'maxItems':len(ids),
                'uniqueItems':True,'items':{'type':'string','enum':ids}}}}

def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('duplicate_key')
        result[key]=value
    return result

def validate_selection(raw,plan,sources,*,completed):
    rejected={'status':'rejected','answer':None,'qualityVerdict':'not_assessed'}
    if not completed or plan['status']!='ready': return rejected
    try:
        value=json.loads(raw,object_pairs_hook=unique_object)
        if not isinstance(value,dict) or set(value)!={'selected'}: return rejected
        selected=value['selected']
        facts=plan['facts']
        if not isinstance(selected,list) or any(not isinstance(i,str) for i in selected): return rejected
        if len(selected)!=len(facts) or set(selected)!={f['id'] for f in facts}: return rejected
        original={s['id']:s['text'] for s in sources}
        for fact in facts:
            if original[fact['sourceId']][fact['start']:fact['end']]!=fact['quote']: return rejected
        # Preserve logical chronology independently of model ordering. Each
        # fact is rendered once; no invented model text is accepted.
        answer='\n\n'.join(f"{f['sentence']} [{f['sourceId']}]" for f in facts)
        return {'status':'composition_ready','answer':answer,'supports':facts,
                'qualityVerdict':'pending_review','freeSynthesis':False,
                'composition':'source_bound_templates',
                'externalTruthVerified':False}
    except (ValueError,TypeError,KeyError,RecursionError):
        return rejected


def compose(query,sources):
    """No model required once all source-backed facts are recognised."""
    plan=build_plan(query,sources)
    selection=json.dumps({'selected':[f['id'] for f in plan['facts']]})
    return validate_selection(selection,plan,sources,completed=True)

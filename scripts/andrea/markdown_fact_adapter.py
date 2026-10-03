"""Bounded Markdown adaptation with original character/line provenance.

Supports book introductions with three explicit edition/cover dates and dated
Obsidian update/snapshot callouts. Unsupported or duplicate candidates stop
the plan. No general extraction, file timestamp inference or semantic oracle.
The protected synthesis module remains pinned and unchanged.
"""
import re
from datetime import date

MONTHS='gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre'.split()
DATE=r'(?:\d{4}-\d{2}-\d{2}|\d{1,2} (?:'+ '|'.join(MONTHS)+r')(?: \d{4})?)(?![\w-]| \d)'

def calendar_date(value):
    """Reject invalid dates without supplying an absent year."""
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        date.fromisoformat(value)
    else:
        parts=value.split()
        date(int(parts[2]) if len(parts)==3 else 2000,MONTHS.index(parts[1])+1,int(parts[0]))

def visible(text,start=0,end=None):
    """A matching view only; source spans always point back to raw Markdown."""
    end=len(text) if end is None else end
    chars=[];mapping=[]
    for i in range(start,end):
        ch=text[i]
        if ch in '*`>': continue
        if ch.isspace():
            if chars and chars[-1]!=' ': chars.append(' ');mapping.append(i)
        else: chars.append(ch);mapping.append(i)
    return ''.join(chars),mapping

def proof(source,mapping,match,role):
    start=mapping[match.start()];end=mapping[match.end()-1]+1
    return {'sourceId':source['id'],'start':start,'end':end,
            'quote':source['text'][start:end],
            'lineStart':source['text'].count('\n',0,start)+1,
            'lineEnd':source['text'].count('\n',0,end-1)+1,'role':role}

def one(pattern,view,mapping,source,role,flags=re.I):
    found=list(re.finditer(pattern,view,flags))
    if len(found)!=1: raise ValueError('missing_or_ambiguous_fact')
    return proof(source,mapping,found[0],role)

def body_start(source):
    text=source['text']
    lines=text.splitlines(keepends=True)
    index=source.get('bodyStart',0)
    if type(index)!=int or index<0 or index>len(lines): raise ValueError('invalid_body_offset')
    start=sum(map(len,lines[:index]))
    # A direct caller cannot let frontmatter masquerade as body evidence.
    if index==0 and lines and lines[0].lstrip('\ufeff').strip()=='---':
        end=next((i for i in range(1,len(lines)) if lines[i].strip() in ('---','...')),None)
        if end is None: raise ValueError('ambiguous_frontmatter')
        start=sum(map(len,lines[:end+1]))
    return start

def book_facts(source):
    start=body_start(source)
    raw=source['text']
    # The intro is bounded by the next second-level heading. Fenced/code
    # intros are unsupported rather than used as narrative evidence.
    heading=re.search(r'(?m)^##\s',raw[start:])
    end=start+heading.start() if heading else len(raw)
    intro=raw[start:end]
    if '```' in intro or '~~~' in intro or len(intro)>6000: raise ValueError('unsupported_intro')
    view,mapping=visible(raw,start,end)
    description=one(r'\bRomanzo di [\w -]+? in [\w -]+?, \d+ capitoli, (?:circa |~)?[\d.]+ parole\.',
                    view,mapping,source,'book_description')
    date_patterns=[('paper_edition_start',rf'\b(?:Edizione cartacea|cartaceo) dal {DATE}'),
                   ('digital_edition_start',rf'\b(?:digitale|Kindle) dal {DATE}'),
                   ('cover_online_date',rf'\bcopertina rifatta e online dal {DATE}')]
    facts=[{'kind':'book_description','proofs':[description]}]
    for kind,pattern in date_patterns:
        support=one(pattern,view,mapping,source,kind)
        date_view,_=visible(support['quote'])
        calendar_date(re.search(DATE,date_view,re.I).group().lower())
        facts.append({'kind':kind,'proofs':[support]})
    return facts

def callouts(source):
    raw=source['text'];start=body_start(source)
    lines=raw[start:].splitlines(keepends=True)
    result=[];i=0;offset=start;fenced=False
    while i<len(lines):
        line=lines[i]
        if line.lstrip().startswith(('```','~~~')): fenced=not fenced
        is_header=re.match(r'^\s*>\s*\[!\w+\]',line)
        if not fenced and is_header:
            begin=offset;j=i+1;finish=offset+len(line)
            while j<len(lines) and re.match(r'^\s*>',lines[j]) and not re.match(r'^\s*>\s*\[!\w+\]',lines[j]):
                finish+=len(lines[j]);j+=1
            result.append((begin,begin+len(line),finish))
        offset+=len(line);i+=1
    return result

def qualification_facts(source):
    raw=source['text'];facts=[];seen=set();current_blocks=[]
    for begin,header_end,end in callouts(source):
        header_view,header_map=visible(raw,begin,header_end)
        kind='current_qualification' if re.search(r'\bAggiornamento\b',header_view,re.I) else \
             'historical_qualification' if re.search(r'\bFotografia\b',header_view,re.I) else None
        if kind is None: continue
        dates=list(re.finditer(r'\b\d{4}-\d{2}-\d{2}\b',header_view))
        if len(dates)!=1: raise ValueError('ambiguous_context_date')
        value=dates[0].group();date.fromisoformat(value)
        label='DATO NON VERIFICATO' if kind=='current_qualification' else 'DATO ASSENTE'
        view,mapping=visible(raw,header_end,end)
        if label not in view: continue
        if '```' in raw[header_end:end] or '~~~' in raw[header_end:end]:
            raise ValueError('code_in_dated_context')
        if kind in seen: raise ValueError('duplicate_dated_context')
        seen.add(kind)
        # Keep the qualifier sentence distinct from counts, commercial
        # publication dates, reviews and commands elsewhere in the note.
        qualifier=one(r'\b(?:I valori|Copie e royalty|Vendite e royalty)[^.]*?'+label+r'[^.]*?\.',
                      view,mapping,source,'qualification')
        header={'sourceId':source['id'],'start':begin,'end':header_end,
                'quote':raw[begin:header_end],
                'lineStart':raw.count('\n',0,begin)+1,
                'lineEnd':raw.count('\n',0,header_end-1)+1,'role':'dated_context'}
        proofs=[header,qualifier]
        if kind=='current_qualification':
            # An explicit subject/variability statement supplies the topic
            # for 'I valori'. Its original span is retained separately.
            subject=one(r'\bVendite e royalty variano per periodo\.',view,mapping,source,'topic')
            proofs.append(subject)
            current_blocks.append((view,mapping,source,subject))
        facts.append({'kind':kind,'contextDate':value,'qualification':label,'proofs':proofs})
    if seen!={'current_qualification','historical_qualification'}:
        raise ValueError('missing_dated_context')
    view,mapping,source,subject=current_blocks[0]
    count=one(r'\bI libri pubblicati sono \d+\.',view,mapping,source,'reported_book_count')
    # Extra facts are independent records, not numbers silently inserted
    # into both qualifier claims.
    return [{'kind':'reported_book_count','proofs':[count]},
            {'kind':'period_variability','proofs':[subject]}]+facts

def schema_for(facts):
    fields={}
    for fact in facts:
        props={'text':{'type':'string','minLength':1,'maxLength':400}}
        if 'contextDate' in fact: props['contextDate']={'type':'string','enum':[fact['contextDate']]}
        fields[fact['id']]={'type':'object','properties':props,'required':list(props),'additionalProperties':False}
    return {'type':'object','properties':{'records':{'type':'object','properties':fields,
            'required':list(fields),'additionalProperties':False}},'required':['records'],'additionalProperties':False}

def prepare(case,mode):
    try:
        sources=case['sources']
        if len(sources)!=1: raise ValueError('one_note_required')
        source=sources[0]
        if source.get('status')!='active': raise ValueError('inactive_note')
        facts=book_facts(source) if mode=='book' else qualification_facts(source) if mode=='qualifications' else []
        if not facts or len(facts)>6: raise ValueError('unsupported_mode')
        virtual_sources=[]
        for i,fact in enumerate(facts):
            fact['id']=f'F{i+1}'
            # A virtual passage is explicitly assembled from proved original
            # spans. It is not presented as one contiguous note excerpt.
            quote='\n'.join(p['quote'] for p in fact['proofs'])
            fact.update({'sourceId':f'E{i+1}','quote':quote,'start':0,'end':len(quote)})
            virtual_sources.append({'id':fact['sourceId'],'text':quote})
        return {'status':'ready','facts':facts,'schema':schema_for(facts),
                'virtualCase':{'query':case['query'],'sources':virtual_sources}}
    except (ValueError,KeyError,TypeError):
        return {'status':'unsupported_or_ambiguous','facts':[]}

def validate(raw,case,plan,synthesis,validator,*,completed):
    if plan['status']!='ready':
        return {'status':'rejected','reason':'unsupported_markdown_conventions','claims':[],
                'semanticVerdict':'not_assessed'}
    try:
        original={s['id']:s['text'] for s in case['sources']}
        for fact in plan['facts']:
            for support in fact['proofs']:
                text=original[support['sourceId']]
                start,end=support['start'],support['end']
                if type(start)!=int or type(end)!=int or not 0<=start<end<=len(text) or text[start:end]!=support['quote']:
                    raise ValueError('original_span_changed')
    except (KeyError,TypeError,ValueError):
        return {'status':'rejected','reason':'original_span_changed','claims':[],
                'semanticVerdict':'not_assessed'}
    result=synthesis.validate(raw,plan['virtualCase'],plan,validator,completed=completed)
    if result['status']=='valid_structure_pending_semantic_review':
        for claim,fact in zip(result['claims'],plan['facts']):
            claim['supports']=fact['proofs']
        result['provenance']='original_markdown_spans_and_separate_context_headers'
    return result

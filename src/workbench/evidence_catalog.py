"""Exact passage selection: models select IDs; services retain the verbatim evidence."""
from copy import deepcopy


def key(raw):return raw['id']+':v'+str(raw['revision'])
def build(ctx):
    result=[];seen=set()
    for r in ctx.get('sources',[])+ctx.get('upstream_contributions',[]):
        body=r['body'];parts=[body[k] for k in ('text','observation','interpretation','recommendation','limitation') if isinstance(body.get(k),str)]
        parts += [e.get('text','') for e in body.get('working_report',{}).get('entries',[])]
        for value in parts:
            for paragraph in value.splitlines():
                for offset in range(0,len(paragraph),480):
                    quote=paragraph[offset:offset+480].strip();identity=(key(r['ref']),quote)
                    if not quote or identity in seen:continue
                    seen.add(identity);result.append(dict(id='EV'+str(len(result)+1),source=key(r['ref']),quote=quote,page=None))
    if ctx.get('visual_source'):
        for p in ctx['pages']:result.append(dict(id='EV'+str(len(result)+1),source=key(ctx['visual_source']['ref']),quote='',page=p['page']))
    return result

def schema(ctx,maximum=4):
    ids=[p['id'] for p in ctx.get('evidence_passages',[])]
    field=dict(type='string',maxLength=24,**({'enum':ids} if ids else {}))
    return dict(type='array',maxItems=maximum if ids else 0,items=dict(type='object',properties=dict(passage=field),required=['passage'],additionalProperties=False))

def normalize(out,ctx):
    catalog={p['id']:p for p in ctx.get('evidence_passages',[])}
    for name in ('implications','objective_review','alignment','plan_review'):
        for item in out.get(name,[]):
            citations=item.get('evidence',[])
            if not isinstance(citations,list):raise ValueError('Invalid evidence selection')
            for i,c in enumerate(citations):
                if isinstance(c,dict) and set(c)=={'passage'}:
                    passage=catalog.get(c['passage'])
                    if not passage:raise ValueError('Choose a supplied evidence passage')
                    citations[i]={k:deepcopy(passage[k]) for k in ('source','quote','page')}
    return out

GUIDANCE="""
EVIDENCE SELECTION: evidence_passages is an application-prepared catalogue of exact
source passages and assessed PDF pages. In every evidence list select {passage:
'EV...'} using a supplied ID. The application attaches the exact source version,
verbatim passage or page. Do not retype, summarize or invent quotations or IDs.
If none supports a claim, leave evidence empty and explain the uncertainty.
"""

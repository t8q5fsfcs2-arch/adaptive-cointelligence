"""Exact, bounded views of already released decision evidence; no authority change."""
from copy import deepcopy

INTAKE_FIELDS={'beneficiaries','jobs','user_situation','user_actions','need','gains','business_challenge','value','approach','in_scope','out_scope','constraints','assumptions','evidence','open_questions','dependencies'}


def project(records):
    projected=[];omissions=[];selected=[]
    # A situated claim's explicit evidence selection takes priority over a prefix.
    cited={}
    for r in records:
        if r['kind']=='need-context':
            for item in r['body'].get('evidence',[]):
                raw=item.get('ref');quote=item.get('quote')
                if raw and isinstance(quote,str) and quote:cited.setdefault((raw['id'],raw['revision']),[]).append(quote)
    for original in records:
        r=deepcopy(original);b=r['body'];kind=r['kind'];omitted=[];truncated=[]
        def choose(keys):
            nonlocal b
            omitted.extend(k for k in b if k not in keys);b={k:v for k,v in b.items() if k in keys}
        def shorten(value,path,limit=2000):
            if isinstance(value,str) and len(value)>limit:
                truncated.append(dict(field=path,start=0,end=limit,total_characters=len(value)))
                return value[:limit]
            if isinstance(value,dict):return {k:shorten(v,path+'.'+k,limit) for k,v in value.items()}
            if isinstance(value,list):return [shorten(v,path+'['+str(i)+']',limit) for i,v in enumerate(value)]
            return value
        if kind=='requirement':
            # Every governing word and its status remain exact and untruncated.
            choose({'title','text','conditions','acceptance_criteria','status','owner','requirement_type',
                    'intake_case','business_assessment'})
        elif kind in {'source','intake-source','evidence'}:
            choose({'title','text','owner','status','limitation','limitations','source_version','sha256','parser'})
            b=shorten(b,'body',2000)
            for quote in dict.fromkeys(cited.get((r['ref']['id'],r['ref']['revision']),[])):
                text=original['body'].get('text','')
                if quote in text:
                    selected.append(dict(id=r['ref']['id'],revision=r['ref']['revision'],field='text',quote=quote))
            passages=[p for p in selected if p['id']==r['ref']['id'] and p['revision']==r['ref']['revision']]
            if passages:b['selected_passages']=passages
        elif kind in {'intent','project-context'}:
            choose({'title','text','status','owner','previous','intake',*INTAKE_FIELDS,
                    'fit_status','evidence_status','source_case','decision_id','business_assessment'})
            if isinstance(b.get('intake'),dict):
                omitted.extend('intake.'+k for k in b['intake'] if k not in INTAKE_FIELDS)
                b['intake']={k:v for k,v in b['intake'].items() if k in INTAKE_FIELDS}
            b=shorten(b,'body',1200)
        elif kind=='project-design-brief':
            choose({'owner','domain','status','objectives','brief_sections','work_request','source_version'})
            for group in ('objectives','brief_sections'):
                for i,item in enumerate(b.get(group,[])):
                    if 'basis_links' in item:
                        item['basis_refs']=[{k:v for k,v in link.items() if k!='quote'} for link in item.pop('basis_links')]
                        omitted.append(group+'['+str(i)+'].basis_links.quote: duplicated source passages; exact canonical links retained')
            b=shorten(b,'body',1200)
        elif kind=='bridge-issue':
            choose({'title','question','consequence','status','owner','decision_owner','next_owner','next_question','route','requirement_refs','target','linked','resolution','information_request'})
            b=shorten(b,'body',2000)
        elif kind=='contribution':
            choose({'title','domain','domain_key','owner','status','observation','interpretation','recommendation','limitation','source_refs','requirement_refs','handoff','working_report'})
            b=shorten(b,'body',2000)
        elif kind in {'goal','success-measure'}:
            if isinstance(b.get('specification'),dict) and all(b.get(k)==v for k,v in b['specification'].items()):
                b.pop('specification');omitted.append('specification: duplicate fields')
        # Policy, situated context, decision history and unknown record kinds retain
        # their complete bodies. If these exceed the bound, fail explicitly.
        r['body']=b
        if omitted or truncated:
            omissions.append(dict(ref=r['ref'],omitted_fields=omitted,truncated_fields=truncated))
        projected.append(r)
    return projected,dict(version='decision-context-v2',included=[r['ref'] for r in records],omitted=omissions,
        boundary='Selected released context only. Exact canonical records remain inspectable. Source excerpts and historical context may be partial; do not infer absence, full coverage or approval from this selection.'),selected

"""Private evidence-alignment proposals and exact-version human assessments."""
from copy import deepcopy
from dataclasses import asdict
import json
from .core import StaleBasis
from .decisions import now
from .model_provider import ModelUnavailable
from .validation import reference

STATUSES=('appears-met','gap','not-demonstrated')
DIMENSIONS=('grounding','corroboration','coverage','applicability')  # Legacy evidence-v1 only.
FRAMEWORK='evidence-reasoning-v1'
GUIDANCE="""
ALIGNMENT LOG: When the exchange actually assesses work against supplied requirements,
individual acceptance criteria, goals or KPIs, return alignment items; otherwise
return an empty alignment array. Never claim project approval or completed validation.
Each target is its exact id:vrevision from requirements or goals_and_measures. Set
criterion to an exact acceptance-criteria passage of the selected requirement, or
empty for the whole target. Goals and KPIs always use an empty criterion; a metric
definition is not an acceptance criterion. Do not put it in the criterion field.
Use appears-met only with cited source evidence; gap or not-demonstrated may have
no evidence. Evidence references must be exact allowed source/upstream versions,
with exact quotes; visual evidence may use the selected PDF and page with an empty
quote. Requirement text alone is not proof of fulfillment. Do not generalize from
static screens to tested behavior or from one participant to a population. Runtime
KPIs need actual measured runtime evidence; a prototype cannot establish benefits.
For confidence use the supplied evidence-reasoning standard and its six dimensions:
logical rigor, material coverage, evidence quality, applicability, independent
patterns and counterevidence. State an explicit ordinal level, exact claim, scope,
rationale and limits. Select only supplied passage IDs as the basis of each dimension.
Identify pattern recurrence, exceptions, population limits and exact evidence families.
Repeated summaries of one source are not independent corroboration. Preserve unknown
relationships rather than infer independence from a family count.
The level is your reviewable scoped judgment, never an average, citation count,
percentage, model certainty or application-generated score. Independent patterns
must be genuinely independent; one observation does not establish generality.
Use not-rated when a defensible confidence judgment is unavailable. Preserve a
material contradiction, missing condition or uncertainty rather than force a pass.
State up to three useful next steps in gaps. Suggest a
focused follow-up question or additional interview probes when useful. A researcher
may ask you to draft or refine a discussion guide in this same conversation; do not
require publishing or filling a form before exploring that next step. External tool
creation is unavailable. Do not invent new evidence, study counts or user agreement.
"""

def key(raw):return raw['id']+':v'+str(raw['revision'])
def targets(ctx):return {key(r['ref']):r for r in ctx.get('requirements',[])+ctx.get('goals_and_measures',[])}
def sources(ctx):
    return {key(r['ref']):r for r in ctx.get('sources',[])+ctx.get('upstream_contributions',[])}
def enabled(ctx):return ctx.get('workbench_task') in ('explore','review')
def schema(ctx):
    def obj(props):return dict(type='object',properties=props,required=list(props),additionalProperties=False)
    def string(n):return dict(type='string',maxLength=n)
    evidence_keys=list(sources(ctx))+([key(ctx['visual_source']['ref'])] if ctx.get('visual_source') else [])
    evidence=obj(dict(source=dict(type='string',enum=evidence_keys or ['']),quote=string(500),page=dict(type=['integer','null'],minimum=1)))
    if 'evidence_passages' in ctx:
        from . import evidence_catalog
        evidence=evidence_catalog.schema(ctx,3)['items']
    criteria=['']
    for record in ctx.get('requirements',[]):
        text=record['body'].get('acceptance_criteria','')
        criteria.extend(v for v in [text,*[line.strip() for line in text.splitlines()]] if v and len(v)<=1500 and v not in criteria)
    return dict(type='array',maxItems=24,items=obj(dict(target=dict(type='string',enum=list(targets(ctx)) or ['']),criterion=dict(type='string',maxLength=1500,enum=criteria),assessment=dict(type='string',enum=list(STATUSES)),rationale=string(1500),evidence=dict(type='array',maxItems=3,items=evidence),confidence=confidence_contract(ctx),gaps=dict(type='array',maxItems=3,items=string(600)))))
def standard_context():
    from .business_assessments import standard
    body=standard()
    return dict(ref=dict(id=body['id'],revision=body['revision']),body=body)

def passage_catalog(ctx):
    from . import evidence_catalog
    return {p['id']:deepcopy(p) for p in ctx.get('evidence_passages',evidence_catalog.build(ctx))}

def confidence_contract(ctx):
    from .business_assessments import confidence_schema
    return confidence_schema(list(passage_catalog(ctx)))

def common_confidence(value):
    return isinstance(value,dict) and value.get('framework')==FRAMEWORK

def confidence_view(values,evidence,ctx):
    if not common_confidence(values):
        return {**confidence(values,evidence),'historical':True,'framework':'evidence-v1'}
    # Recorded judgments are not recomputed under a later configuration.
    result=deepcopy(values);catalog=passage_catalog(ctx)
    for dimension in result.get('dimensions',{}).values():
        dimension['citations']=[deepcopy(catalog[id]) for id in dimension.get('passage_ids',[]) if id in catalog]
    for family in result.get('patterns',{}).get('families',[]):
        family['citations']=[deepcopy(catalog[id]) for id in family.get('passage_ids',[]) if id in catalog]
    result.update(label={'not-rated':'Not rated','low':'Low','moderate':'Moderate','high':'High'}.get(values.get('level'),'Not rated'),
        basis='Scoped model or author judgment under the recorded evidence-reasoning standard. Not a probability, project approval or independent evidence.')
    return result

def confidence(values,evidence):
    """Read legacy evidence-v1 history only; never grade a new model result."""
    levels={k:values[k] for k in DIMENSIONS};count=values.get('participant_count')
    if count==1:
        levels['corroboration']=min(levels['corroboration'],1);levels['coverage']=min(levels['coverage'],1)
    score=sum((0,8,17,25)[v] for v in levels.values()) if evidence else 0
    if count==1:score=min(score,49)
    return dict(score=score,rubric='evidence-v1',levels=levels,participant_count=count,label='Limited' if score<50 else 'Moderate' if score<75 else 'Stronger',basis='Equal-weight grounding, corroboration, coverage and applicability. No cited evidence scores 0; one reported participant caps the score at 49. Initial product heuristic; not a calibrated probability or certification.')
def valid_legacy_confidence(value):
    return isinstance(value,dict) and set(value)==set(DIMENSIONS)|{'participant_count'} and all(type(value[k]) is int and 0<=value[k]<=3 for k in DIMENSIONS) and (value['participant_count'] is None or type(value['participant_count']) is int and 1<=value['participant_count']<=1000000)
def valid_confidence(value,ctx):
    if not common_confidence(value):return False
    from .business_assessments import validate_confidence
    try:validate_confidence(value,passage_catalog(ctx))
    except (ModelUnavailable,ValueError,TypeError,KeyError):return False
    return True

def validate(out,ctx):
    items=out.get('alignment')
    if items is None:return # Compatibility: absent data never becomes a fabricated assessment.
    if not enabled(ctx) or not isinstance(items,list) or len(items)>24:raise ValueError('Invalid alignment result')
    allowed=targets(ctx);evidence=sources(ctx);seen=set()
    for item in items:
        if not isinstance(item,dict) or set(item)!=set(schema(ctx)['items']['properties']):raise ValueError('Invalid alignment item')
        target=allowed.get(item['target']);criterion=item['criterion']
        if not target or not isinstance(criterion,str) or len(criterion)>1500 or criterion and (target['kind']!='requirement' or criterion not in [target['body'].get('acceptance_criteria',''),*[line.strip() for line in target['body'].get('acceptance_criteria','').splitlines() if line.strip()]]):raise ValueError('Use exact target and criterion versions')
        identity=(item['target'],criterion)
        if identity in seen:raise ValueError('Duplicate target assessment')
        seen.add(identity)
        if item['assessment'] not in STATUSES or not isinstance(item['rationale'],str) or not 0<len(item['rationale'])<=1500 or not valid_confidence(item['confidence'],ctx):raise ValueError('Invalid assessment basis')
        refs=item['evidence']
        if not isinstance(refs,list) or len(refs)>3 or item['assessment']=='appears-met' and not refs:raise ValueError('Evidence is required for appears met')
        for cite in refs:
            if not isinstance(cite,dict) or set(cite)!={'source','quote','page'} or not isinstance(cite['quote'],str) or len(cite['quote'])>500:raise ValueError('Invalid evidence reference')
            visual=ctx.get('visual_source')
            if visual and cite['source']==key(visual['ref']):
                if type(cite['page']) is not int or cite['page'] not in [v['page'] for v in ctx['pages']] or cite['quote']:raise ValueError('Use an assessed PDF page')
            else:
                source=evidence.get(cite['source']);body=source['body'] if source else {}
                available='\n'.join(body.get(k,'') for k in ('text','observation','interpretation','recommendation','limitation') if isinstance(body.get(k,''),str))+'\n'+'\n'.join(e.get('text','') for e in body.get('working_report',{}).get('entries',[]))
                if not source or not cite['quote'] or cite['quote'] not in available or cite['page'] is not None:raise ValueError('Evidence quote is absent from the selected source')
        if not isinstance(item['gaps'],list) or len(item['gaps'])>3 or any(not isinstance(g,str) or not 0<len(g)<=600 for g in item['gaps']):raise ValueError('Invalid evidence gap')
def rows(w,threads):
    result=[];owned={t['ref'].id:t for t in threads}
    edits={r['body']['key']:r for r in w.latest_records('domain-alignment-assessment') if r['scope']==w.domains.scope and r['body']['owner']==w.actor}
    for report in w.latest_records('domain-chat-review'):
        b=report['body'];thread=owned.get(b['conversation'])
        if not thread or b.get('owner')!=w.actor:continue
        if not b['output'].get('alignment'):continue
        current=w.working_report.selection_current(report,thread);ctx=b['context'];allowed=targets(ctx)
        for i,item in enumerate(b['output'].get('alignment',[])):
            identity=report['ref'].label()+'|'+str(i);edit=edits.get(identity);target=allowed[item['target']]
            assessment=edit['body']['assessment'] if edit else item['assessment'];values=edit['body']['confidence'] if edit else item['confidence']
            result.append(dict(key=identity,review=asdict(report['ref']),index=i,conversation=thread['ref'].id,target=deepcopy(target['ref']),target_kind=target['kind'],title=target['body'].get('title') or target['body'].get('text',target['ref']['id']),criterion=item['criterion'],assessment=assessment,rationale=item['rationale'],evidence=deepcopy(item['evidence']),confidence=confidence_view(values,item['evidence'],ctx),confidence_values=deepcopy(values),assessor_type='human' if edit else 'model',mode=b.get('mode'),gaps=item['gaps'],current=current,confirmed=bool(current and edit and edit['body']['confirmed']),human=deepcopy(edit['body']) if edit else None,edit_ref=asdict(edit['ref']) if edit else None,batch=deepcopy(b['batch']),at=b['at']))
    return sorted(result,key=lambda r:r['at'],reverse=True)
def save(w,data):
    with w.store.transaction():
        thread=w.domain_chat.owned(data.get('conversation'));w.domain_chat.available(thread)
        candidates=rows(w,[thread]);row=next((r for r in candidates if r['review']==data.get('review') and r['index']==data.get('index')),None)
        if not row:raise PermissionError('Choose an assessment in your own conversation')
        if not row['current']:raise StaleBasis('The evidence or project context changed. Review the current work before confirming an assessment.')
        if data.get('expected')!=row['edit_ref']:raise StaleBasis('This assessment changed. Reload before saving.')
        assessment=data.get('assessment');note=data.get('note');confirmed=data.get('confirmed');values=data.get('confidence')
        report=w.store.read(reference(row['review']),{w.domains.scope})
        compatible=valid_confidence(values,report['body']['context']) if common_confidence(row['confidence_values']) else valid_legacy_confidence(values) and values==row['confidence_values']
        if assessment not in STATUSES or not isinstance(note,str) or not 0<len(note.strip())<=2000 or type(confirmed) is not bool or not compatible:raise ValueError('Provide an assessment, rationale and valid evidence-confidence basis')
        raw=row['edit_ref'];body=dict(key=row['key'],owner=w.actor,domain=w.domains.key,conversation=thread['ref'].id,review=row['review'],index=row['index'],assessment=assessment,note=note.strip(),confirmed=confirmed,confidence=deepcopy(values),assessor_type='human',at=now())
        import hashlib
        identity='ALIGN-'+hashlib.sha256(row['key'].encode()).hexdigest()[:20]
        ref=w.store.put(identity,'domain-alignment-assessment',w.domains.scope,body,raw['revision'] if raw else 0)
        w.store.depend(ref,reference(row['review']),w.scopes)
        return dict(ref=asdict(ref),message='Working assessment saved. Project approval remains separate.')

def author_context(w,thread,ctx):
    permitted=targets(ctx);result=[]
    for r in w.latest_records('domain-alignment-assessment'):
        b=r['body']
        if r['scope']!=w.domains.scope or b['owner']!=w.actor or b['conversation']!=thread['ref'].id:continue
        review=w.store.read(reference(b['review']),{w.domains.scope});item=review['body']['output']['alignment'][b['index']]
        if item['target'] not in permitted:continue
        result.append(dict(ref=asdict(r['ref']),target=item['target'],criterion=item['criterion'],assessment=b['assessment'],note=b['note'],confirmed=b['confirmed'],confidence=confidence_view(b['confidence'],item['evidence'],review['body']['context']),assessor_type='human',mode=review['body'].get('mode'),at=b['at'],status='Historical author judgment; reassess against the current sources. Not project approval or independent evidence.'))
    return sorted(result,key=lambda r:r['at'],reverse=True)[:12]

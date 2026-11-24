"""Private, source-linked implications; professional judgment is not project approval."""
from copy import deepcopy
from dataclasses import asdict
from uuid import uuid4

from .core import Ref, StaleBasis
from .decisions import now, fingerprint
from .validation import reference
from .domain_alignment import key, sources
from . import evidence_catalog

KINDS = {'new-requirement':'New requirement', 'refine-requirement':'Refine requirement',
         'challenge-requirement':'Challenge to requirement', 'new-criterion':'New acceptance criterion',
         'downstream-guidance':'Downstream guidance', 'challenge-intent':'Challenge to intent',
         'open-question':'Open consideration'}
STATUSES = ('suggested','held','dismissed')
GUIDANCE = """
PROJECT IMPLICATIONS: This work can challenge or enrich the sponsor's hypothesis,
reveal new needs, refine requirements or criteria, inform downstream briefs, or
raise unresolved considerations. Return only consequential, source-linked proposals
in implications; an empty list is valid. Prefer two to four consequential items
with brief evidence assessments rather than a long inventory. Do not force new insights to fit an
existing requirement. New requirements may have no target. Use exact supplied
id:vrevision targets. refine-requirement and challenge-requirement need an existing requirement target.
new-criterion should identify a parent requirement; if none responsibly fits, leave
targets empty. The application will flag the missing parent before decision review. Use new-criterion when proposing an additional
testable requirement condition. Never use new-criterion with only a goal or KPI
target. Instrumentation or metric-definition advice may be downstream-guidance or
an open-question; a proposed new product obligation may be a new-requirement.
Use challenge-requirement when evidence questions an existing
obligation. criterion is the exact existing acceptance-criteria passage being
challenged, or empty; new criteria belong in statement, with criterion empty. statement is
editable proposed wording, not a question substituted for a conclusion. Preserve
counterevidence, scope and uncertainty. Cite exact source passages or assessed PDF
pages. An uncited proposal is a hunch, never established evidence. Do not treat
previous AI replies, held ideas or author endorsements as independent evidence.
Review supplied working_objectives too: explain which objectives the supplied work
addresses, partly addresses or leaves unanswered. Objective coverage is distinct
from product fulfillment and runtime KPI success. Never invent objectives. All
outputs are advisory proposals, not publication, ratification or approval.
For each implication assess substantive evidence in support: assessment is
insufficient, limited or substantive; explain basis (method and direct relevance),
scope (participants, contexts, temporal limits), corroboration (independent evidence
or an applicable authoritative source), counterevidence (contradictions and limits),
and gaps. A citation merely proves where words occur; it does not prove a claim.
Repeated quotes from one source are not independent corroboration. One interview
can ground a bounded observation but not a population claim or causal benefit.
A single authoritative applicable policy can ground a normative constraint; explain
its authority rather than demanding an arbitrary number of sources. Fictional data
cannot establish a real-world finding. Static screens cannot prove runtime behavior,
and interviews cannot prove KPI improvement. substantive needs cited evidence, a
clear defensible basis in every dimension, and no unresolved material evidence gaps.
Otherwise use limited or insufficient and name the next evidence needed. An AI
assessment is provisional until a human reviews it. Keep internal IDs out of prose.
"""


def obj(fields): return dict(type='object',properties=fields,required=list(fields),additionalProperties=False)
def string(n): return dict(type='string',maxLength=n)
def targets(ctx): return {key(r['ref']):r for r in ctx.get('requirements',[])+ctx.get('goals_and_measures',[])+ctx.get('business_intent',[])}
def objectives(ctx): return {o['id']:o for o in ctx.get('working_objectives',{}).get('objectives',[])}
def citation_schema(ctx):
    if 'evidence_passages' in ctx:return evidence_catalog.schema(ctx)
    allowed=list(sources(ctx))+([key(ctx['visual_source']['ref'])] if ctx.get('visual_source') else [])
    return dict(type='array',maxItems=4,items=obj(dict(source=dict(type='string',enum=allowed or ['']),quote=string(500),page=dict(type=['integer','null'],minimum=1))))
SUPPORT_FIELDS=('basis','scope','corroboration','counterevidence')
SUPPORT_STATUSES=('unassessed','insufficient','limited','substantive')
def empty_support():
    return dict(assessment='unassessed',**{k:'' for k in SUPPORT_FIELDS},gaps=['Evidence sufficiency has not been assessed.'])
def support_schema():
    return obj(dict(assessment=dict(type='string',enum=list(SUPPORT_STATUSES[1:])),**{k:string(1500) for k in SUPPORT_FIELDS},gaps=dict(type='array',maxItems=4,items=string(600))))
def valid_support(value,evidence):
    if not isinstance(value,dict) or set(value)!=set(support_schema()['properties']) or value['assessment'] not in SUPPORT_STATUSES:raise ValueError('Provide an evidence assessment with its basis and limits')
    for k in SUPPORT_FIELDS:valid_text(value[k],1500,value['assessment']=='substantive')
    if not isinstance(value['gaps'],list) or len(value['gaps'])>4:raise ValueError('Identify up to four material evidence gaps')
    for gap in value['gaps']:valid_text(gap,600)
    if value['assessment']=='substantive' and (not evidence or value['gaps']):raise ValueError('Substantive support needs cited evidence and no unresolved material evidence gaps')
def claim_signature(p):
    return fingerprint({k:p.get(k,'' if k=='criterion' else []) for k in ('kind','title','statement','rationale','targets','criterion','evidence')})
def evidence_state(record,current):
    b=record['body'];p=b['payload'];review=b.get('evidence_review');signature=claim_signature(p)
    human=bool(current and review and review['claim']==signature)
    target_needed=p['kind']=='new-criterion' and not p['targets']
    valid_ai=b.get('support_signature')==signature
    support=deepcopy(review['support'] if human else p.get('support',empty_support()) if valid_ai else empty_support())
    if not current:status='earlier-basis'
    elif not p['evidence']:status='needs-evidence'
    elif support['assessment']=='substantive':status='reviewed' if human else 'review-needed'
    elif support['assessment']=='limited':status='limited'
    elif support['assessment']=='insufficient':status='needs-evidence'
    else:status='unassessed'
    return dict(status=status,support=support,human_reviewed=human,reviewed_by=review['by'] if human else None,reviewed_at=review['at'] if human else None,target_needed=target_needed,ready_for_review=bool(not target_needed and human and support['assessment']=='substantive' and b['status']=='held' and p['evidence']))

def public_evidence_text(record,current):
    state=evidence_state(record,current);support=state['support'];p=record['body']['payload']
    text='\n\nEvidence: '+state['status'].replace('-',' ')+'. Not project approval.'
    if p.get('criterion'):text+='\nExisting criterion: '+p['criterion']
    if p['targets']:text+='\nAffected versions: '+', '.join(p['targets'])
    for k in SUPPORT_FIELDS:
        if support[k]:text+='\n'+k.title()+': '+support[k]
    if support['gaps']:text+='\nEvidence still needed: '+'; '.join(support['gaps'])
    if not p['evidence']:text+='\nHunch: no cited evidence.'
    if state['human_reviewed']:text+='\nEvidence reviewed by '+state['reviewed_by']+' for this exact claim.'
    return text

def schema(ctx):
    criteria=['']
    for r in ctx.get('requirements',[]):
        value=r['body'].get('acceptance_criteria','')
        for passage in [value,*[v.strip() for v in value.splitlines()]]:
            if passage and len(passage)<=1500 and passage not in criteria:criteria.append(passage)
    limited=support_schema();limited['properties']['assessment']['enum']=['insufficient','limited']
    substantive=support_schema();substantive['properties']['assessment']['enum']=['substantive']
    substantive['properties']['gaps']['maxItems']=0
    for field in SUPPORT_FIELDS:substantive['properties'][field]['minLength']=1
    return dict(type='array',maxItems=12,items=obj(dict(kind=dict(type='string',enum=list(KINDS)),title=string(200),statement=string(4000),rationale=string(1500),criterion=dict(type='string',maxLength=1500,enum=criteria),support=dict(anyOf=[limited,substantive]),targets=dict(type='array',maxItems=6,items=dict(type='string',enum=list(targets(ctx)) or [''])),evidence=citation_schema(ctx))))
def objective_schema(ctx):
    return dict(type='array',maxItems=20 if objectives(ctx) else 0,items=obj(dict(objective_id=dict(type='string',enum=list(objectives(ctx)) or ['']),assessment=dict(type='string',enum=['addressed','partial','not-addressed']),rationale=string(1500),evidence=citation_schema(ctx),next_step=string(1000))))

def requirement_basis(ctx):
    result={}
    for r in ctx.get('requirements',[]):
        target=key(r['ref']);value=r['body'].get('acceptance_criteria','')
        for criterion in dict.fromkeys(['',value,*[v.strip() for v in value.splitlines() if v.strip()]]):
            if len(criterion)<=1500:result['IB'+str(len(result)+1)]=dict(target=target,criterion=criterion)
    return result

def wire_schema(ctx):
    """Make parent/criterion and evidence-strength dependencies structural."""
    base=schema(ctx);props=base['items']['properties'];choices=[]
    reqs=[key(r['ref']) for r in ctx.get('requirements',[])]
    for group in ('requirement-change','new-criterion','other'):
        if group=='requirement-change' and not reqs:continue
        for substantive in (False,True):
            p=deepcopy(props)
            p['support']=deepcopy(props['support']['anyOf'][1 if substantive else 0])
            if substantive:
                if p['evidence'].get('maxItems',0)==0:continue
                p['evidence']['minItems']=1
            if group=='requirement-change':
                p['kind']['enum']=['refine-requirement','challenge-requirement']
                p.pop('criterion');p['requirement_basis']=dict(type='string',enum=list(requirement_basis(ctx)))
                p['targets']['maxItems']=5
            elif group=='new-criterion':
                p['kind']['enum']=['new-criterion'];p['criterion']['enum']=['']
                p['targets']=dict(type='array',maxItems=1 if reqs else 0,items=dict(type='string',enum=reqs or ['']))
            else:
                p['kind']['enum']=[k for k in KINDS if k not in {'refine-requirement','challenge-requirement','new-criterion'}]
                p['criterion']['enum']=['']
            choices.append(obj(p))
    return dict(type='array',maxItems=12,items=dict(anyOf=choices))

def normalize_wire(items,ctx):
    if not isinstance(items,list):return items
    out=deepcopy(items);catalog=requirement_basis(ctx)
    for item in out:
        if isinstance(item,dict) and 'requirement_basis' in item:
            selected=catalog.get(item.pop('requirement_basis'))
            if not selected:raise ValueError('Choose an exact requirement and criterion basis.')
            item['criterion']=selected['criterion']
            item['targets']=list(dict.fromkeys([selected['target'],*item['targets']]))
    return out

def valid_text(value,n,required=True):
    if not isinstance(value,str) or len(value)>n or required and not value.strip(): raise ValueError('Use concise, nonempty implication wording')
def validate_evidence(items,ctx):
    if not isinstance(items,list) or len(items)>4: raise ValueError('Use up to four exact evidence references')
    allowed=sources(ctx);visual=ctx.get('visual_source')
    for c in items:
        if not isinstance(c,dict) or set(c)!={'source','quote','page'}: raise ValueError('Invalid implication evidence')
        valid_text(c['quote'],500,False)
        if visual and c['source']==key(visual['ref']):
            if c['quote'] or type(c['page']) is not int or c['page'] not in [p['page'] for p in ctx.get('pages',[])]: raise ValueError('Cite an assessed PDF page')
        else:
            source=allowed.get(c['source']);b=source['body'] if source else {}
            content='\n'.join(b.get(k,'') for k in ('text','observation','interpretation','recommendation','limitation') if isinstance(b.get(k,''),str))+'\n'+'\n'.join(e.get('text','') for e in b.get('working_report',{}).get('entries',[]))
            if not source or not c['quote'] or c['quote'] not in content or c['page'] is not None: raise ValueError('The implication quote is not in the selected source')
def validate(items,ctx):
    if not isinstance(items,list) or len(items)>12: raise ValueError('Use up to twelve implications')
    allowed=targets(ctx)
    for p in items:
        if not isinstance(p,dict) or not (set(schema(ctx)['items']['properties'])-{'criterion','support'})<=set(p)<=set(schema(ctx)['items']['properties']) or p['kind'] not in KINDS: raise ValueError('Invalid project implication')
        for field,n in [('title',200),('statement',4000),('rationale',1500)]: valid_text(p[field],n)
        if not isinstance(p['targets'],list) or len(p['targets'])>6 or len(set(p['targets']))!=len(p['targets']) or any(t not in allowed for t in p['targets']): raise ValueError('Use exact supplied project targets')
        if p['kind'] in ('refine-requirement','challenge-requirement') and not any(allowed[t]['kind']=='requirement' for t in p['targets']): raise ValueError('This change must identify its existing requirement')
        if p['kind']=='new-criterion' and p['targets'] and not any(allowed[t]['kind']=='requirement' for t in p['targets']):raise ValueError('An acceptance criterion needs a parent requirement, not only a goal or KPI')
        criterion=p.get('criterion','');valid_text(criterion,1500,False)
        criteria=[line for t in p['targets'] if allowed[t]['kind']=='requirement' for line in [allowed[t]['body'].get('acceptance_criteria',''),*[v.strip() for v in allowed[t]['body'].get('acceptance_criteria','').splitlines() if v.strip()]]]
        if criterion and (p['kind']=='new-criterion' or criterion not in criteria):raise ValueError('Choose the exact existing criterion from the affected requirement; put a new criterion in proposed wording')
        validate_evidence(p['evidence'],ctx)
        if 'support' in p:valid_support(p['support'],p['evidence'])
def validate_objectives(items,ctx):
    if not isinstance(items,list) or len(items)>20: raise ValueError('Invalid objective coverage')
    seen=set()
    for p in items:
        if not isinstance(p,dict) or set(p)!=set(objective_schema(ctx)['items']['properties']) or p['objective_id'] not in objectives(ctx) or p['objective_id'] in seen or p['assessment'] not in ('addressed','partial','not-addressed'): raise ValueError('Use a supplied objective once')
        seen.add(p['objective_id']);valid_text(p['rationale'],1500);valid_text(p['next_step'],1000,False);validate_evidence(p['evidence'],ctx)
        if p['assessment']=='addressed' and not p['evidence']: raise ValueError('Addressed objectives need cited evidence')


class ProjectImplications:
    def __init__(self,w): self.w=w;self.store=w.store
    def owned(self,raw,thread):
        ref=reference(raw);r=self.store.read(ref,{self.w.domains.scope})
        if r['kind']!='domain-implication' or r['body']['owner']!=self.w.actor or r['body']['conversation']!=thread['ref'].id: raise PermissionError('Choose an implication in your own work')
        if self.store.latest(ref.id,{self.w.domains.scope})['ref']!=ref: raise StaleBasis('This implication changed. Reload before editing')
        return r
    def capture(self,thread,review,kind='conversation'):
        body=review['body'];ctx=body['context'];refs=[]
        for index,p in enumerate(body['output'].get('implications',[])):
            ref=self.store.put('IMP-'+uuid4().hex[:12],'domain-implication',self.w.domains.scope,
                dict(owner=self.w.actor,domain=self.w.domains.key,conversation=thread['ref'].id,payload=deepcopy(p),support_signature=claim_signature(p),status='suggested',origin=asdict(review['ref']),origin_kind=kind,index=index,at=now(),human_reviewed=False))
            self.store.depend(ref,review['ref'],self.w.scopes);refs.append(asdict(ref))
        return refs
    def records(self,thread):
        return [r for r in self.w.latest_records('domain-implication') if r['scope']==self.w.domains.scope and r['body']['owner']==self.w.actor and r['body']['conversation']==thread['ref'].id]
    def current(self,r,thread):
        b=r['body']
        if b.get('card') or not b.get('origin'): return all(self.store.latest(reference(t).id,self.w.scopes)['ref']==reference(t) for t in b.get('basis',[]))
        review=self.store.read(reference(b['origin']),self.w.scopes)
        return self.w.submissions.is_current(review,thread) if b['origin_kind']=='submission' else self.w.working_report.selection_current(review,thread)
    def state(self,threads):
        return [{**r,'current':self.current(r,t),'evidence_state':evidence_state(r,self.current(r,t))} for t in threads for r in self.records(t)]
    def save(self,data):
        with self.store.transaction():
            thread=self.w.domain_chat.owned(data.get('conversation'));self.w.domain_chat.available(thread)
            old=self.owned(data['expected'],thread) if data.get('expected') else None
            status=data.get('status')
            if status not in STATUSES: raise ValueError('Choose suggested, held or dismissed')
            p=deepcopy(old['body']['payload']) if old else dict(kind='open-question',title='',statement='',rationale='',targets=[],evidence=[])
            for k in ('kind','title','statement','rationale','criterion'):
                if k in data:p[k]=data[k]
            if 'targets' in data:p['targets']=data['targets']
            if old and old['body'].get('origin'):
                ctx=self.store.read(reference(old['body']['origin']),self.w.scopes)['body']['context']
            else:
                ctx,_=self.w.domain_chat.basis(thread,self.w.domain_chat.plan(thread)[0],purpose='explore')
                p['targets']=data.get('targets',p['targets'])
            validate([p],ctx)
            if status=='held' and old and not self.current(old,thread) and data.get('confirm_historical') is not True: raise StaleBasis('Review the earlier basis before holding this implication, or request a fresh evaluation')
            body={**(old['body'] if old else {}), 'owner':self.w.actor,'domain':self.w.domains.key,'conversation':thread['ref'].id,'payload':p,'status':status,'human_reviewed':True,'edited_by':self.w.actor,'at':now()}
            if data.get('evidence_review') is not None:
                if data.get('confirm_evidence') is not True:raise ValueError('Confirm that you reviewed support for this specific claim')
                if old and not self.current(old,thread):raise StaleBasis('Review current evidence before recording evidence sufficiency')
                support=deepcopy(data['evidence_review']);valid_support(support,p['evidence'])
                if support['assessment']=='unassessed':raise ValueError('Choose insufficient, limited or substantive support')
                body['evidence_review']=dict(support=support,claim=claim_signature(p),by=self.w.actor,at=now())
            if data.get('selection') is not None:
                if old:raise ValueError('Capture a selected passage as a new implication')
                selected=data['selection']
                if not isinstance(selected,dict) or set(selected)!={'turn','text'}:raise ValueError('Choose a saved AI partner passage')
                turn=self.store.read(reference(selected['turn']),{self.w.domains.scope});tb=turn['body'];quote=selected['text'];valid_text(quote,4000)
                if turn['kind']!='domain-chat-turn' or tb.get('owner')!=self.w.actor or tb.get('conversation')!=thread['ref'].id or tb.get('role')!='assistant':raise PermissionError('Choose an AI partner reply in your own discussion')
                if quote not in tb['message']:raise ValueError('The selected text is not in this saved reply')
                body['origin_selection']=dict(turn=asdict(turn['ref']),text=quote,at=now(),boundary='Selected AI wording, not independent evidence')
            if not old:body.update(origin=None,basis=ctx['basis'])
            ref=self.store.put(old['ref'].id if old else 'IMP-'+uuid4().hex[:12],'domain-implication',self.w.domains.scope,body,old['ref'].revision if old else 0)
            if body.get('origin_selection'):self.store.depend(ref,reference(body['origin_selection']['turn']),self.w.scopes)
            return dict(ref=asdict(ref),message='Implication saved privately. Project requirements are unchanged.')
    def context(self,thread):
        return [dict(ref=asdict(r['ref']),**deepcopy(r['body']['payload']),**(dict(card_type=r['body']['card']['type'],card_context=r['body']['card']['fields'],relationships=r['body']['card']['relations']) if r['body'].get('card') else {}),status=r['body']['status'],human_reviewed=r['body']['human_reviewed'],current=self.current(r,thread),authority='Working interpretation, not independent evidence or project approval') for r in self.records(thread) if r['body']['status']=='held'][:12]

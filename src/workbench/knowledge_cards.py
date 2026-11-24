"""Private building blocks over existing implication records and packet services.

No model calls, implicit release, graph infrastructure or governing approval.
Semantic links are exact comparison references, not automatic invalidation edges.
"""
from copy import deepcopy
from dataclasses import asdict
import json
import re
from uuid import uuid4

from .core import Ref, StaleBasis
from .decisions import SCOPE, now
from .validation import reference
from . import project_implications as implications

TYPES = {
    'finding': dict(label='Finding', fields={'scope':'Scope and situation','evidence_notes':'Evidence notes','implications':'Implications','limits':'Evidence limits'}),
    'user-situation': dict(label='User situation', fields={'people':'People and role','job':'Job to be done','situation':'Situation','triggers':'Triggers','pains':'Pains and bottlenecks','gains':'Gains sought','boundaries':'Boundaries','dependencies':'Dependencies'}),
    'user-flow': dict(label='User flow', fields={'people':'People and role','trigger':'Starting trigger','steps':'Steps and actions','branches':'Branches and exceptions','obstacles':'Obstacles and bottlenecks','outcome':'Desired outcome'}),
    'user-story': dict(label='User story', fields={'role':'As a','need':'I need','benefit':'So that','acceptance_criteria':'Proposed acceptance criteria','conditions':'Conditions and limits'}),
    'artifact': dict(label='Artifact', fields={'artifact_type':'Artifact type · e.g. Prototype','version_label':'Version or variant','location':'File or tool location','purpose':'What this artifact demonstrates','review_status':'Review or testing status','limits':'Limits and open questions'}),
    'implication': dict(label='Implication', fields={'consequence':'What this could change','conditions':'When it applies','limits':'Limits and uncertainty'}),
    'hypothesis': dict(label='Hypothesis', fields={'test':'What would test this','conditions':'When it applies','limits':'Limits and uncertainty'}),
    'challenge': dict(label='Challenge', fields={'question':'What needs reconsideration','consequence':'Why it matters','limits':'Limits and uncertainty'}),
    'dependency': dict(label='Dependency', fields={'condition':'Required condition','consequence':'What depends on it','limits':'Limits and uncertainty'}),
    'performance-goal': dict(label='Performance goal', fields={'outcome':'Outcome sought','measure':'How it could be measured','baseline':'Known baseline','target':'Proposed target','accountable_owner':'Accountable role'}),
    'observation': dict(label='Observation', fields={'source_basis':'Where and how it was seen','conditions':'Conditions at the time','limits':'Limits of the observation'}),
    'design-decision': dict(label='Design decision', fields={'alternatives':'Alternatives considered','rationale_basis':'Why this choice','tradeoffs':'Trade-offs accepted','limits':'Limits and open questions'}),
    'evaluation-result': dict(label='Evaluation result', fields={'tested':'What was tested','participants':'With whom','criteria':'Against which criteria','outcome':'What happened','limits':'Limits of the evaluation'}),
    'lesson': dict(label='Lesson', fields={'population':'Who and what it was learned from','conditions':'Conditions where it held','counterexamples':'Counterexamples and exceptions','reuse':'How another project could use it','limits':'Where it should not be applied'}),
    'question': dict(label='Open question', fields={'decision_needed':'What would resolve it','limits':'Limits and uncertainty'}),
    'note': dict(label='Working note', fields={'scope':'Scope and applicability','limits':'Limits and uncertainty'})}
TYPE_HINTS = {
    'observation':'What was seen or heard, with its source. Keep it separate from what you conclude.',
    'design-decision':'A choice made, the alternatives and why.',
    'evaluation-result':'What was tested, with whom, against which criteria, and what happened.',
    'lesson':'Scoped learning another project could reuse, with its conditions and limits.',
    'finding':'An observation or conclusion with a source and stated limits.',
    'user-situation':'Who is doing what, in which situation, and what gets in the way.',
    'user-flow':'Actions, decisions and exceptions leading to an outcome.',
    'user-story':'A proposed capability expressed as a role, need and benefit.',
    'artifact':'A specific work product or prototype version. Link its retained file.',
    'implication':'What a finding or condition may change for the project.',
    'hypothesis':'A testable explanation awaiting evidence.',
    'challenge':'A reason to reconsider a claim, requirement or approach.',
    'dependency':'A condition or input needed for other work to succeed.',
    'performance-goal':'An intended outcome and a proposed way to measure it.',
    'question':'An unresolved question and what would resolve it.',
    'note':'A captured idea. Choose a more specific type as its meaning becomes clear.'}
for _type,_hint in TYPE_HINTS.items():TYPES[_type]['hint']=_hint
# D013: families organise the types; every type carries the same short "applies to" footer so a later
# project can judge fit. Existing blocks stay valid: no type or field was removed or renamed.
FAMILIES = {'evidence':'Evidence','direction':'Direction','open':'Open','outputs':'Outputs'}
TYPE_FAMILY = {'observation':'evidence','finding':'evidence','user-situation':'evidence','user-flow':'evidence','evaluation-result':'evidence',
    'implication':'direction','user-story':'direction','design-decision':'direction','performance-goal':'direction','lesson':'direction',
    'hypothesis':'open','challenge':'open','dependency':'open','question':'open',
    'artifact':'outputs','note':'outputs'}
APPLIES = {'applies_people':'Applies to · people or role','applies_situation':'Applies to · situation','applies_time':'Applies to · time or period','applies_confidence':'How sure, and why'}
_ALREADY = {'applies_people':{'people','role','population','participants'},'applies_situation':{'situation','conditions','scope'}}
for _type,_spec in TYPES.items():
    _spec['family']=TYPE_FAMILY[_type]
    for _key,_title in APPLIES.items():
        if not (_ALREADY.get(_key,set()) & set(_spec['fields'])):_spec['fields'][_key]=_title
# A domain profile may set config.block_types; otherwise these defaults lead and the rest stay available.
DOMAIN_TYPES = {'research':['observation','finding','user-situation','user-flow','hypothesis','question','lesson','note'],
    'design':['design-decision','evaluation-result','artifact','user-story','user-flow','dependency','lesson','note']}
def preferred_types(domain_key,profile=None):
    chosen=(profile or {}).get('config',{}).get('block_types') or DOMAIN_TYPES.get(domain_key) or []
    return [t for t in chosen if t in TYPES]
RELATIONS = {'applies-to':'Applies to','supported-by':'Supported by','supports':'Supports','challenges':'Challenges','refines':'Refines','depends-on':'Depends on','constrains':'Constrains','informs':'Informs','measures':'Measures'}
PUBLIC_TARGETS = {'knowledge-card','need-context','requirement','goal','success-measure','intent','project-context','policy','contribution','source','intake-source','evidence'}
SOURCE_KINDS = {'source','intake-source','evidence','contribution'}
LEGACY_TYPES = {'open-question':'question','new-requirement':'implication','refine-requirement':'implication','challenge-requirement':'challenge','new-criterion':'implication','downstream-guidance':'implication','challenge-intent':'challenge'}


def card_type(record):
    return record['body'].get('card',{}).get('type',LEGACY_TYPES.get(record['body']['payload']['kind'],'note'))


def wording(record):
    p=record['body']['payload'];fields=record['body'].get('card',{}).get('fields',{})
    return p['statement']+('' if not p.get('rationale') else '\n\nRationale and limits: '+p['rationale'])+''.join('\n\n'+TYPES[card_type(record)]['fields'].get(k,k)+': '+v for k,v in fields.items() if v)


def source_text(record):
    b=record['body'];parts=[b.get(k,'') for k in ('text','observation','interpretation','recommendation','limitation')]
    parts.extend(e.get('text','') for e in b.get('working_report',{}).get('entries',[]))
    return '\n'.join(p for p in parts if isinstance(p,str))


class KnowledgeCards:
    def __init__(self,w):self.w=w;self.store=w.store
    def type(self,r):return card_type(r)
    def label(self,r):return TYPES[card_type(r)]['label'] if r['body'].get('card') else implications.KINDS[r['body']['payload']['kind']]
    def wording(self,r):return wording(r)
    def owned(self,raw,current=True):
        self.w.domains.author();ref=reference(raw);r=self.store.read(ref,{self.w.domains.scope})
        if r['kind']!='domain-implication' or r['body'].get('owner')!=self.w.actor or r['body'].get('domain')!=self.w.domains.key:
            raise PermissionError('Choose a block in your own domain vault')
        if current and self.store.latest(ref.id,{self.w.domains.scope})['ref']!=ref:raise StaleBasis('This block changed. Reopen its current version before editing or selecting it')
        return r
    def records(self):
        return [r for r in self.w.latest_records('domain-implication') if r['scope']==self.w.domains.scope and r['body'].get('owner')==self.w.actor and r['body'].get('domain')==self.w.domains.key] if self.w.domains.key else []
    def current(self,r):
        thread=self.w.domain_chat.owned(asdict(self.store.latest(r['body']['conversation'],{self.w.domains.scope})['ref']))
        return self.w.implications.current(r,thread)
    def target(self,raw):
        ref=reference(raw);r=self.store.read(ref,self.w.scopes)
        if r['scope']==SCOPE:
            if r['kind'] not in PUBLIC_TARGETS:raise ValueError('Link a shared block, project expectation or evidence source')
        elif r['kind']=='domain-implication':self.owned(raw,current=False)
        elif r['kind']=='source' and r['scope']==self.w.domains.scope and r['body'].get('owner')==self.w.actor:pass
        else:raise PermissionError('Link only your own private blocks/sources or shared project context')
        return r
    def capture_origin(self,selection):
        if not isinstance(selection,dict):raise ValueError('Choose saved chat or review text')
        is_turn=set(selection)=={'turn','text'}
        if not is_turn and set(selection)!={'review','path','text'}:raise ValueError('Choose saved chat or review text')
        raw=selection['turn' if is_turn else 'review']
        record=self.store.read(reference(raw),{self.w.domains.scope});b=record['body']
        if record['kind']!=('domain-chat-turn' if is_turn else 'domain-chat-review') or b.get('owner')!=self.w.actor:
            raise PermissionError('Choose text from your own domain chat or review')
        thread=self.w.domain_chat.owned(asdict(self.store.latest(b.get('conversation',''),{self.w.domains.scope})['ref']))
        self.w.domain_chat.available(thread)
        if is_turn:
            if b.get('role') not in ('user','assistant'):raise ValueError('Choose a saved user or AI partner response')
            value=b['message']
        else:
            path=selection['path']
            if not isinstance(path,list) or not 1<=len(path)<=6 or path[0] not in ('summary','limitations','findings','suggestions','alignment','implications'):
                raise ValueError('Choose a displayed review passage')
            value=b['output']
            for part in path:
                if isinstance(value,dict) and isinstance(part,str) and part in value:value=value[part]
                elif isinstance(value,list) and type(part) is int and 0<=part<len(value):value=value[part]
                else:raise ValueError('The selected review section is unavailable')
            if not isinstance(value,str):raise ValueError('Choose a text passage in the review')
        implications.valid_text(selection['text'],4000)
        if selection['text'] not in value:raise ValueError('The selected text was not found in that exact response')
        return dict(**deepcopy(selection),conversation=asdict(thread['ref']),role=b.get('role','review'),boundary='Saved conversation or review wording; not independent evidence')

    def capture(self,data):
        """Apply one reviewed section change; no model call or implicit release."""
        self.w.domains.author()
        if data.get('confirm') is not True:raise ValueError('Review and confirm the block change before saving')
        request=data.get('request_id')
        if not isinstance(request,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',request):raise ValueError('Use a unique block capture identifier')
        with self.store.transaction():
            origin=self.capture_origin(data.get('selection'))
            signature=implications.fingerprint(dict(selection=data['selection'],target=(data.get('expected') or {}).get('id'),type=data.get('type'),title=data.get('title'),statement=data.get('statement'),section=data.get('section'),text=data.get('text')))
            for row in self.records():
                prior=next((v for v in row['body'].get('captures',[]) if v['request_id']==request),None)
                if prior:
                    if prior['signature']!=signature:raise ValueError('This capture identifier was already used for a different change')
                    return dict(ref=asdict(row['ref']),message='This passage is already saved privately.')
            old=self.owned(data['expected']) if data.get('expected') else None
            thread=self.w.domain_chat.owned(data.get('conversation') or origin['conversation'])
            if thread['ref'].id!=origin['conversation']['id']:raise PermissionError('Capture text in its original chat')
            kind=card_type(old) if old else data.get('type','note')
            if kind not in TYPES:raise ValueError('Choose a building block type')
            section=data.get('section');value=data.get('text')
            if section not in ('statement','rationale') and section not in {'fields.'+k for k in TYPES[kind]['fields']}:
                raise ValueError('Choose a section of this block type')
            implications.valid_text(value,4000 if section=='statement' else 1500 if section=='rationale' else 2000)
            fields=deepcopy(old['body'].get('card',{}).get('fields',{})) if old else {}
            patch=dict(expected=asdict(old['ref']) if old else None,type=kind)
            if old:patch['conversation']=asdict(self.store.latest(old['body']['conversation'],{self.w.domains.scope})['ref'])
            else:
                patch.update(conversation=asdict(thread['ref']),title=data.get('title'),statement=data.get('statement','') if section!='statement' else value,request_id=request,status='held')
            if section.startswith('fields.'):
                fields[section[7:]]=value;patch['fields']=fields
            else:patch[section]=value
            captures=old['body'].get('captures',[]) if old else []
            if len(captures)>=100:raise ValueError('This block has a long capture history. Start a related block for the next concept')
            return self.save(patch,capture=dict(request_id=request,signature=signature,origin=origin,section=section,at=now()))

    def save(self,data,*,capture=None):
        self.w.domains.author()
        with self.store.transaction():
            old=self.owned(data['expected']) if data.get('expected') else None
            thread=self.w.domain_chat.owned(data.get('conversation') or asdict(self.store.latest(old['body']['conversation'],{self.w.domains.scope})['ref']))
            self.w.domain_chat.available(thread)
            if old and thread['ref'].id!=old['body']['conversation']:raise PermissionError('Keep this block attributed to its original chat')
            request=data.get('request_id')
            if request is not None:
                if not isinstance(request,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',request):raise ValueError('Use a unique block capture identifier')
                if not old:
                    for r in self.records():
                        if r['body'].get('capture_request')==request:return dict(ref=asdict(r['ref']),message='This block is already saved privately.')
            kind=data.get('type',card_type(old) if old else 'note')
            if kind not in TYPES:raise ValueError('Choose a building block type')
            p=deepcopy(old['body']['payload']) if old else dict(kind='open-question',title='',statement='',rationale='',targets=[],evidence=[])
            for k,n in [('title',200),('statement',4000),('rationale',1500)]:
                if k in data:p[k]=data[k]
                implications.valid_text(p.get(k,''),n,k in ('title','statement'))
            fields=data.get('fields',deepcopy(old['body'].get('card',{}).get('fields',{})) if old else {})
            if not isinstance(fields,dict) or set(fields)-set(TYPES[kind]['fields']):raise ValueError('Use the displayed fields for this block type')
            for v in fields.values():implications.valid_text(v,2000,False)
            relations=data.get('relations',deepcopy(old['body'].get('card',{}).get('relations',[])) if old else [])
            if not isinstance(relations,list) or len(relations)>12:raise ValueError('Use up to twelve focused block relationships')
            checked=[];seen=set();versions={}
            prior_relations=old['body'].get('card',{}).get('relations',[]) if old else []
            for item in relations:
                if not isinstance(item,dict) or set(item)!={'relation','ref','rationale','conditions'} or item['relation'] not in RELATIONS:raise ValueError('Each link needs a relationship, target, reason and conditions')
                r=self.target(item['ref']);ref=r['ref'];signature=(ref.id,item['relation'])
                if old and ref.id==old['ref'].id:raise ValueError('A block cannot link to itself')
                if signature in seen or ref.id in versions and versions[ref.id]!=ref.revision:raise ValueError('Use distinct links and one version per related item')
                seen.add(signature);versions[ref.id]=ref.revision
                if item not in prior_relations and self.store.latest(ref.id,self.w.scopes)['ref']!=ref:raise StaleBasis('Choose the current related item before creating this link')
                implications.valid_text(item['rationale'],800);implications.valid_text(item['conditions'],800,False)
                checked.append(dict(relation=item['relation'],ref=asdict(ref),rationale=item['rationale'],conditions=item['conditions']))
            evidence=data.get('evidence',p.get('evidence',[]))
            if not isinstance(evidence,list) or len(evidence)>4:raise ValueError('Use up to four exact source passages or PDF page references')
            for e in evidence:
                if not isinstance(e,dict) or set(e)!={'source','quote','page'}:raise ValueError('Evidence needs an exact source, quote and optional page')
                try:identity,version=e['source'].rsplit(':v',1);ref=Ref(identity,int(version))
                except (ValueError,TypeError,AttributeError):raise ValueError('Choose an exact source version') from None
                r=self.target(asdict(ref))
                if r['kind'] not in SOURCE_KINDS:raise ValueError('A saved block or model reply is not independent evidence')
                implications.valid_text(e['quote'],500,False)
                if e['page'] is not None:
                    if type(e['page']) is not int or not 1<=e['page']<=r['body'].get('visual_pdf',{}).get('page_count',0) or e['quote']:raise ValueError('Choose a retained PDF page without an invented quote')
                elif not e['quote'] or e['quote'] not in source_text(r):raise ValueError('The quoted passage is not in that exact source')
            p['evidence']=deepcopy(evidence)
            status=data.get('status',old['body']['status'] if old else 'held')
            if status not in implications.STATUSES:raise ValueError('Choose saved, suggested or archived status')
            card=dict(type=kind,fields=deepcopy(fields),relations=checked)
            body={**(old['body'] if old else {}),'owner':self.w.actor,'domain':self.w.domains.key,'conversation':thread['ref'].id,'payload':p,'status':status,'card':card,'human_reviewed':True,'edited_by':self.w.actor,'at':now()}
            if old:body['previous']=asdict(old['ref'])
            else:body.update(origin=None,created_at=body['at'],capture_request=request)
            if data.get('selection') is not None:
                if old:raise ValueError('Capture a chat passage as a new block')
                s=data['selection']
                if not isinstance(s,dict) or set(s)!={'turn','text'}:raise ValueError('Choose a saved chat passage')
                turn=self.store.read(reference(s['turn']),{self.w.domains.scope});tb=turn['body']
                implications.valid_text(s['text'],4000)
                if turn['kind']!='domain-chat-turn' or tb.get('owner')!=self.w.actor or tb.get('conversation')!=thread['ref'].id or tb.get('role') not in ('user','assistant'):raise PermissionError('Save a passage from your own chat')
                if s['text'] not in tb['message']:raise ValueError('The selected text was not found in that exact message')
                body['origin_selection']=dict(turn=asdict(turn['ref']),text=s['text'],role=tb['role'],at=now(),boundary='Saved conversation wording; not independent evidence')
            if capture is not None:body['captures']=[*body.get('captures',[]),deepcopy(capture)]
            # Local refinement does not depend on unrelated chat/brief edits.
            body['basis']=[dict(id=e['source'].rsplit(':v',1)[0],revision=int(e['source'].rsplit(':v',1)[1])) for e in evidence]
            if old and p==old['body']['payload'] and card==old['body'].get('card') and status==old['body']['status'] and capture is None:return dict(ref=asdict(old['ref']),message='Block already saved privately.')
            ref=self.store.put(old['ref'].id if old else 'CARD-'+uuid4().hex[:12],'domain-implication',self.w.domains.scope,body,old['ref'].revision if old else 0)
            for raw in body['basis']:self.store.depend(ref,reference(raw),self.w.scopes)
            if body.get('origin_selection'):self.store.depend(ref,reference(body['origin_selection']['turn']),self.w.scopes)
            for entry in body.get('captures',[]):
                origin=entry['origin'];self.store.depend(ref,reference(origin.get('turn') or origin['review']),self.w.scopes)
        return dict(ref=asdict(ref),message='Building block saved privately.')
    def read(self,data):
        r=self.owned(data.get('ref'),current=False)
        history=[dict(ref=dict(id=r['ref'].id,revision=v['revision']),at=json.loads(v['body'])['at']) for v in self.store.db.execute('SELECT revision,body FROM records WHERE id=? ORDER BY revision DESC LIMIT 50',(r['ref'].id,))]
        return dict(record=r,history=history)
    def read_link(self,data):
        self.w.domains.author()
        return dict(record=self.target(data.get('ref')))
    def selected(self,values):
        if not isinstance(values,list) or len(values)>40:raise ValueError('Select up to forty building blocks')
        refs=[reference(v) for v in values]
        if len({r.id for r in refs})!=len(refs):raise ValueError('Select one version of each block')
        rows=[self.owned(asdict(ref)) for ref in refs]
        # D014 Rule 8: suggestions stay provisional; publication is where they are validated.
        if any(r['body']['status']=='dismissed' for r in rows):raise ValueError('Restore a dismissed block before selecting it for a deliverable')
        return rows
    def suggestions_in(self,draft):
        """Provisional AI suggestions a deliverable contains; publication asks to accept them together."""
        if not draft['body'].get('knowledge_card_refs'):return []
        return [r for r in self.for_draft(draft) if r['body']['status']=='suggested']
    def validate_suggestions(self,rows):
        """Record that the author accepted these suggestions by publishing them (D003, D014 Rule 8)."""
        for r in rows:
            body={**r['body'],'status':'held','human_reviewed':True,'validated':dict(by=self.w.actor,at=now(),through='publication'),'previous':asdict(r['ref'])}
            self.store.put(r['ref'].id,'domain-implication',self.w.domains.scope,body,r['ref'].revision)
    def source_options(self,values):
        refs=set()
        for r in self.selected(values):
            refs.update(Ref(e['source'].rsplit(':v',1)[0],int(e['source'].rsplit(':v',1)[1])) for e in r['body']['payload'].get('evidence',[]))
            for link in r['body'].get('card',{}).get('relations',[]):
                record=self.target(link['ref'])
                if record['kind']=='source':refs.add(record['ref'])
        return [asdict(ref) for ref in sorted(refs) if self.target(asdict(ref))['kind']=='source']
    def for_draft(self,draft):
        rows=self.selected(draft['body'].get('knowledge_card_refs',[]));chosen={r['ref'] for r in rows}
        sources={reference(v) for v in draft['body'].get('source_refs',[])}
        for r in rows:
            for e in r['body']['payload'].get('evidence',[]):
                ref=Ref(e['source'].rsplit(':v',1)[0],int(e['source'].rsplit(':v',1)[1]));record=self.target(asdict(ref))
                if record['scope']!=SCOPE and ref not in sources:raise ValueError('Select the cited private source before sharing the block: '+record['body'].get('title',ref.id))
            for link in r['body'].get('card',{}).get('relations',[]):
                record=self.target(link['ref'])
                if record['scope']!=SCOPE and record['ref'] not in chosen and record['ref'] not in sources:
                    raise ValueError('Select the linked private block or source too, or remove its link before sharing: '+record['body'].get('payload',{}).get('title',record['body'].get('title',record['ref'].id)))
        return rows
    def packet_basis(self,draft):
        refs=set()
        for r in self.for_draft(draft):
            refs.add(r['ref']);refs.update(reference(v['ref']) for v in r['body'].get('card',{}).get('relations',[]))
            refs.update(Ref(e['source'].rsplit(':v',1)[0],int(e['source'].rsplit(':v',1)[1])) for e in r['body']['payload'].get('evidence',[]))
        return refs
    def public_body(self,r,mapping):
        b=r['body'];p=b['payload'];kind=card_type(r)
        evidence=[]
        for e in p.get('evidence',[]):
            ref=Ref(e['source'].rsplit(':v',1)[0],int(e['source'].rsplit(':v',1)[1]));target=mapping.get(ref,ref)
            evidence.append(dict(ref=asdict(target),quote=e['quote'],page=e['page']))
        links=[{**link,'ref':asdict(mapping.get(reference(link['ref']),reference(link['ref'])))} for link in b.get('card',{}).get('relations',[])]
        return dict(title=p['title'],type=kind,statement=p['statement'],rationale=p.get('rationale',''),fields=deepcopy(b.get('card',{}).get('fields',{})),relations=links,evidence=evidence,evidence_assessment=implications.evidence_state(r,all(self.store.latest(reference(raw).id,self.w.scopes)['ref']==reference(raw) for raw in b.get('basis',[]))),owner=self.w.actor,domain=self.w.domains.key,domain_label=self.w.domains.profile()['config']['label'],status='shared-for-review',source_version=asdict(r['ref']),authority='Authored domain contribution. Sharing is not project approval.')
    def release(self,draft,source_mapping):
        rows=self.for_draft(draft);mapping=dict(source_mapping);planned=[]
        for r in rows:
            identity='SHARED-'+r['ref'].id;prior=self.store.latest(identity,{SCOPE}) if self.store.db.execute('SELECT 1 FROM records WHERE id=?',(identity,)).fetchone() else None
            if prior and prior['body'].get('source_version')==asdict(r['ref']):
                mapping[r['ref']]=prior['ref'];planned.append((r,prior,prior['ref'],False))
            else:
                ref=Ref(identity,prior['ref'].revision+1 if prior else 1);mapping[r['ref']]=ref;planned.append((r,prior,ref,True))
        for r,prior,ref,create in planned:
            if not create:continue
            body=self.public_body(r,mapping);body.update(shared_by=self.w.actor,shared_at=now(),previous=asdict(prior['ref']) if prior else None)
            self.store.put(ref.id,'knowledge-card',SCOPE,body,ref.revision-1)
        for r,prior,ref,create in planned:
            if not create:continue
            body=self.store.read(ref,{SCOPE})['body']
            for raw in [v['ref'] for v in body['relations']]+[v['ref'] for v in body['evidence']]:self.store.depend(ref,reference(raw),{SCOPE})
        return {r['ref']:mapping[r['ref']] for r in rows}
    def state(self,threads):
        if not self.w.domains.key:return dict(types=TYPES,families=FAMILIES,preferred=[],relations=RELATIONS,catalogue=[],targets=[])
        rows=self.records();catalogue=[]
        from . import knowledge_components as components
        latest=self.w.latest_records();areas=components.drawers(latest)
        requirements={r['ref'].id:r for r in latest if r['kind']=='requirement'}
        requirement=requirements.get
        for r in rows:
            b=r['body'];links=[]
            for item in b.get('card',{}).get('relations',[]):
                target=self.target(item['ref']);latest=self.store.latest(target['ref'].id,self.w.scopes)
                links.append({**item,'title':target['body'].get('title') or target['body'].get('payload',{}).get('title',target['ref'].id),'changed':latest['ref']!=target['ref'],'current':asdict(latest['ref'])})
            backlinks=[dict(ref=asdict(other['ref']),title=other['body']['payload']['title'],relation=link['relation']) for other in rows for link in other['body'].get('card',{}).get('relations',[]) if reference(link['ref']).id==r['ref'].id]
            public_id='SHARED-'+r['ref'].id;shared=self.store.latest(public_id,{SCOPE}) if self.store.db.execute('SELECT 1 FROM records WHERE id=?',(public_id,)).fetchone() else None
            catalogue.append(dict(ref=asdict(r['ref']),type=card_type(r),relations=links,backlinks=backlinks,shared=asdict(shared['ref']) if shared else None,shared_source=shared['body'].get('source_version') if shared else None,system=components.block_view(r,requirement,areas)))
        candidates=[dict(ref=asdict(r['ref']),title=r['body']['payload']['title'],type=card_type(r),private=True) for r in rows if r['body']['status']!='dismissed']
        for r in self.w.latest_records():
            if r['scope']==SCOPE and r['kind'] in PUBLIC_TARGETS or r['scope']==self.w.domains.scope and r['kind']=='source' and r['body'].get('owner')==self.w.actor:
                candidates.append(dict(ref=asdict(r['ref']),title=r['body'].get('title',r['ref'].id),type=r['kind'],private=r['scope']!=SCOPE,source=r['kind'] in SOURCE_KINDS))
        from . import knowledge_components as components
        return dict(system=components.public_config(),label=self.w.domains.profile()['config']['label']+' building blocks',card_label=self.w.domains.profile()['config']['label']+' building block',types=TYPES,families=FAMILIES,preferred=preferred_types(self.w.domains.key,self.w.domains.profile()),relations=RELATIONS,catalogue=catalogue,targets=candidates)

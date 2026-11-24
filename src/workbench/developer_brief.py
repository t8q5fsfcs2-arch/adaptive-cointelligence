"""A named, versioned implementation draft using existing domain publication guards."""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from uuid import uuid4
import json

from .core import Ref, StaleBasis
from .decisions import SCOPE, now
from .validation import reference
from .source_links import source_references

LIMIT=40000
TYPE='Evidence-backed developer brief'

class DeveloperBriefs:
    def __init__(self,w):self.w=w;self.store=w.store
    def author(self,*,historical=False):
        self.w.domains.author()
        if self.w.domains.key!='design':raise PermissionError('Developer briefs are authored in the Design workbench')
        if not historical and TYPE not in self.w.domains.profile()['config']['deliverable_types']:raise PermissionError('Developer brief is not an enabled output in this domain configuration')
    def thread(self,data):
        self.author();thread=self.w.domain_chat.owned(data.get('conversation'));self.w.domain_chat.available(thread)
        return thread,self.w.domain_chat.draft(thread)
    def identity(self,thread):return 'DEVBRIEF-'+sha256(thread['ref'].id.encode()).hexdigest()[:20]
    def latest(self,thread):
        id=self.identity(thread)
        return self.store.latest(id,{self.w.domains.scope}) if self.store.db.execute('SELECT 1 FROM records WHERE id=?',(id,)).fetchone() else None
    def checked(self,data):
        thread,draft=self.thread(data);r=self.latest(thread)
        if not r or r['body']['owner']!=self.w.actor:raise PermissionError('Open your own developer brief first')
        if data.get('expected')!=asdict(r['ref']):raise StaleBasis('The developer brief changed. Reopen it before saving; its earlier versions remain available.')
        return thread,draft,r
    def links(self,draft):
        b=draft['body'];refs=deepcopy(b.get('requirement_refs',[])+b.get('input_refs',[]))
        for r in self.w.latest_records('intent'):refs.append(asdict(r['ref']))
        supporting=[]
        for raw in b['requirement_refs']:
            requirement=self.store.read(reference(raw),{SCOPE})
            supporting.extend(requirement['body'].get('goal_refs',[])+requirement['body'].get('measure_refs',[]))
        supporting=list({(raw['id'],raw['revision']):raw for raw in supporting}.values());refs.extend(supporting)
        plan=self.w.domain_brief.for_draft(draft)
        return dict(goal_measure_refs=supporting,requirement_refs=deepcopy(b['requirement_refs']),input_refs=deepcopy(b.get('input_refs',[])),design_brief=asdict(plan['ref']) if plan else None,project_basis=refs)
    def prototype_options(self,thread):
        result=[]
        for r in self.w.prototypes.state([thread]):
            b=r['body'];exports=[e for e in r['exports'] if e['body']['plan']==asdict(r['ref']) and e['body']['status']=='sent']
            exp=exports[0] if exports else None
            result.append(dict(ref=asdict(r['ref']),title=b['output']['title'],current=r['current'],figma_url=exp['body']['url'] if exp else None,export=asdict(exp['ref']) if exp else None,frames=deepcopy(exp['body'].get('frames',[])) if exp else [],boundary='Prototype representation; no human test or runtime result is established by creation.'))
        return result
    def opened(self,data):
        with self.store.transaction():
            thread,draft=self.thread(data);r=self.latest(thread)
            if not r:
                options=self.prototype_options(thread);prototype=next((p for p in options if p['current']),None)
                body=dict(owner=self.w.actor,conversation=thread['ref'].id,draft_id=draft['ref'].id,title='Developer brief',text='',source_refs=[],prototype=prototype,**self.links(draft),at=now())
                ref=self.store.put(self.identity(thread),'developer-brief',self.w.domains.scope,body)
                self.dependencies(ref,body)
                r=self.store.read(ref,self.w.scopes)
        return dict(ref=asdict(r['ref']),message='Developer brief opened. It is a private draft.')
    def dependencies(self,ref,b):
        refs=b['project_basis']+b['source_refs']+([b['design_brief']] if b.get('design_brief') else [])+([b['prototype']['ref']] if b.get('prototype') else [])
        for raw in refs:self.store.depend(ref,reference(raw),self.w.scopes)
    def save(self,data):
        with self.store.transaction():
            thread,draft,r=self.checked(data);title=data.get('title');text=data.get('text')
            if not isinstance(title,str) or not title.strip() or len(title)>160 or not isinstance(text,str) or len(text)>LIMIT:raise ValueError('Give the brief a title and use up to 40,000 characters')
            refs=data.get('source_refs',[])
            if not isinstance(refs,list) or any(raw not in draft['body']['source_refs'] for raw in refs):raise ValueError('Choose evidence attached to this Design work item')
            source_references(self.store,refs,self.w.scopes,require_current=False)
            selected=data.get('prototype');prototype=None
            if selected:
                prototype=next((p for p in self.prototype_options(thread) if p['ref']==selected),None)
                if not prototype:raise ValueError('Choose a saved prototype version from this Design work item')
            body={**r['body'],'title':title.strip(),'text':text,'source_refs':deepcopy(refs),'prototype':prototype,'at':now()}
            if data.get('discussion'):
                turn=self.store.read(reference(data['discussion']),{self.w.domains.scope})
                if turn['kind']!='domain-chat-turn' or turn['body']['conversation']!=thread['ref'].id or turn['body']['role']!='assistant' or text!=turn['body']['message']:raise ValueError('Select an exact saved AI partner response')
                body['drafted_from']=asdict(turn['ref'])
            elif text!=r['body']['text']:body.pop('drafted_from',None)
            comparison=lambda b:{k:v for k,v in b.items() if k!='at'}
            if comparison(body)==comparison(r['body']):return dict(ref=asdict(r['ref']),message='Developer brief is already saved.')
            ref=self.store.put(r['ref'].id,r['kind'],r['scope'],body,r['ref'].revision);self.dependencies(ref,body)
        return dict(ref=asdict(ref),message='Developer brief saved. Earlier versions remain available.')
    def refresh(self,data):
        with self.store.transaction():
            thread,draft,r=self.checked(data);body={**r['body'],**self.links(draft),'at':now()}
            ref=self.store.put(r['ref'].id,r['kind'],r['scope'],body,r['ref'].revision);self.dependencies(ref,body)
        return dict(ref=asdict(ref),message='Linked project context refreshed. Brief wording and evidence selections are unchanged.')
    def changed(self,r,draft):
        b=r['body'];changed=[]
        for raw in b['project_basis']+b['source_refs']+([b['design_brief']] if b.get('design_brief') else []):
            if self.store.latest(raw['id'],self.w.scopes)['ref']!=reference(raw):changed.append(raw)
        if b['requirement_refs']!=draft['body']['requirement_refs'] or b['input_refs']!=draft['body'].get('input_refs',[]):changed.append(dict(id='work-scope',revision=0))
        if b.get('prototype'):
            plan=self.store.read(reference(b['prototype']['ref']),self.w.scopes)
            if not self.w.prototypes.current(plan):changed.append(b['prototype']['ref'])
        return changed
    def for_publication(self,draft):
        raw=draft['body'].get('developer_brief')
        if not raw:return None
        r=self.store.read(reference(raw),{self.w.domains.scope})
        if r['kind']!='developer-brief' or r['body']['owner']!=self.w.actor or self.store.latest(r['ref'].id,self.w.scopes)['ref']!=r['ref']:raise StaleBasis('The developer brief changed. Prepare its current version before sharing.')
        original=self.store.latest(r['body']['draft_id'],{self.w.domains.scope})
        if self.changed(r,original):raise StaleBasis('Linked project context changed. Review and refresh the developer brief before sharing.')
        return r
    def prepare(self,data):
        with self.store.transaction():
            thread,draft,r=self.checked(data);b=r['body']
            if not b['text'].strip():raise ValueError('Add brief content before sharing')
            if self.changed(r,draft):raise StaleBasis('Linked project context changed. Review and refresh the developer brief before sharing.')
            self.w.domain_brief.require_complete(draft)
            body={**draft['body'],'title':b['title'],'deliverable_type':TYPE,'observation':b['text'][:20000],'text':b['text'][:20000],'source':'Author-selected developer brief and evidence','limitation':'Shared for review; publication is not development authorization or evidence validation.','source_refs':b['source_refs'],'developer_brief':asdict(r['ref']),'working_report':dict(format='document',entries=[dict(id='DEV-TEXT-'+str(i),heading='Developer brief' if not i else 'Developer brief continued',text=b['text'][i:i+20000],citations=[],requirement_refs=b['requirement_refs']) for i in range(0,len(b['text']),20000)],saved_by=self.w.actor,saved_at=now()),'submission_of':dict(draft_id=draft['ref'].id),'published_id':'CON-'+r['ref'].id,'status':'draft','saved_at':now()}
            id='DEVDEL-'+r['ref'].id;old=self.store.latest(id,self.w.scopes) if self.store.db.execute('SELECT 1 FROM records WHERE id=?',(id,)).fetchone() else None
            ref=self.store.put(id,'contribution-draft',self.w.domains.scope,body,old['ref'].revision if old else 0);self.store.depend(ref,r['ref'],self.w.scopes)
            return self.w.domains.prepare(dict(expected=asdict(ref),recipient='bridge',intent_implications='',downstream_needs='Implementation guidance for review; no development authorization or external delivery.',open_questions='Human testing, unresolved decisions and implementation evidence must be reviewed separately.'))
    def public_body(self,r,source_mapping=None):
        b=r['body'];mapping=source_mapping or {}
        return dict(title=b['title'],text=b['text'],owner=b['owner'],source_version=asdict(r['ref']),source_refs=[asdict(mapping.get(reference(raw),reference(raw))) for raw in b['source_refs']],requirement_refs=deepcopy(b['requirement_refs']),goal_measure_refs=deepcopy(b.get('goal_measure_refs',[])),input_refs=deepcopy(b['input_refs']),prototype=deepcopy(b.get('prototype')),status='shared-for-review',published_at=now(),boundary='This shared brief is not development authorization. Requirement decisions and Jira/ADO delivery have separate receipts.')
    def release(self,r,mapping):
        id='PUBLISHED-'+r['ref'].id;old=self.store.latest(id,{SCOPE}) if self.store.db.execute('SELECT 1 FROM records WHERE id=?',(id,)).fetchone() else None
        if old and old['body']['source_version']==asdict(r['ref']):return old['ref']
        body=self.public_body(r,mapping);ref=self.store.put(id,'project-developer-brief',SCOPE,body,old['ref'].revision if old else 0)
        for raw in body['source_refs']+body['requirement_refs']+body.get('goal_measure_refs',[])+body['input_refs']:self.store.depend(ref,reference(raw),{SCOPE})
        return ref
    def history(self,r):
        return [dict(ref=dict(id=r['ref'].id,revision=row['revision']),at=json.loads(row['body']).get('at',json.loads(row['body']).get('published_at'))) for row in self.store.db.execute('SELECT revision,body FROM records WHERE id=? AND revision<? ORDER BY revision DESC LIMIT 20',(r['ref'].id,r['ref'].revision))]
    def read(self,data):
        raw=reference(data.get('ref'));r=self.store.read(raw,self.w.scopes)
        if r['kind']=='developer-brief':
            self.author(historical=True)
            if r['body']['owner']!=self.w.actor:raise PermissionError('Choose your own developer brief')
        elif r['kind']!='project-developer-brief' or r['scope']!=SCOPE:raise PermissionError('Choose a developer brief')
        return dict(ref=asdict(r['ref']),body=deepcopy(r['body']),history=self.history(r))
    def state(self):
        shared=self.w.latest_records('project-developer-brief');private=[]
        if self.w.domains.key=='design':
            for thread in self.w.domain_chat.threads():
                r=self.latest(thread)
                if r:
                    draft=self.w.domain_chat.draft(thread);private.append({**r,'changed':self.changed(r,draft),'history':self.history(r),'source_options':[dict(ref=raw,title=self.store.read(reference(raw),self.w.scopes)['body']['title']) for raw in draft['body']['source_refs']],'prototype_options':self.prototype_options(thread),'shared':next((asdict(s['ref']) for s in shared if s['body']['source_version']==asdict(r['ref'])),None),'last_shared':next((asdict(s['ref']) for s in shared if s['body']['source_version']['id']==r['ref'].id),None)})
        public=[]
        for r in shared:
            contribution=next((c for c in self.w.latest_records('contribution') if c['body'].get('developer_brief')==asdict(r['ref'])),None)
            changed=[raw for raw in r['body']['requirement_refs']+r['body'].get('goal_measure_refs',[])+r['body']['input_refs'] if self.store.latest(raw['id'],{SCOPE})['ref']!=reference(raw)]
            public.append({**r,'history':self.history(r),'packet':contribution['body']['packet'] if contribution else None,'changed':changed})
        return dict(can_author=self.w.domains.key=='design' and TYPE in self.w.domains.profile()['config']['deliverable_types'],private=private,shared=public)

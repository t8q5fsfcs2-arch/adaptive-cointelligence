"""Governed local domain glossary/taxonomy/relationships, not enterprise graph sync."""
from dataclasses import asdict
from copy import deepcopy
from uuid import uuid4
import re

from .core import Ref, StaleBasis
from .decisions import SCOPE, ACTORS, now, fingerprint
from .domain import DOMAINS, txt, latest_optional

KINDS={'term':'Glossary term','category':'Taxonomy category','relationship':'Concept relationship','standard':'Standard or rule','practice':'Best practice'}
FIELDS={'id','kind','title','definition','aliases','parent_id','subject_id','predicate','object_id','source','status'}
# D009 step 1: boundaries and reach of meaning on concepts. Optional, so earlier versions keep their exact content.
MEANING={'includes','excludes','not_confused_with','reach'}
REACH={'project':'This project','domain':'This team’s domain','named-domains':'Named domains','enterprise':'Enterprise'}
LEAD_REACH={'project','domain'}  # wider reach needs an approved proposal and the enterprise steward


def meaning(e):
    """Boundary and reach of one entry, with defaults for entries saved before D009."""
    return dict(includes=e.get('includes',''),excludes=e.get('excludes',''),not_confused_with=e.get('not_confused_with',''),reach=e.get('reach','project'))


def snapshot(store,key):
    r=latest_optional(store,'DOMAIN-KNOWLEDGE-'+key,{SCOPE})
    return dict(ref=asdict(r['ref']) if r else None,entries=r['body']['entries'] if r else [],
                fingerprint=fingerprint(r['body']['entries'] if r else []))


class DomainKnowledge:
    def __init__(self,w):self.w=w;self.store=w.store
    def definitions(self):
        defaults={k:dict(key=k,label=v['label'],purpose=v['descriptor'],leaders=v['authors'],members=v['authors'],template=k,runtime='available',definition_ref=None) for k,v in DOMAINS.items()}
        for r in self.w.latest_records('domain-definition'):
            b=r['body'];defaults[b['key']]=dict(key=b['key'],label=b['label'],purpose=b['purpose'],leaders=b['leaders'],members=b.get('members',b['leaders']),template=b.get('template','research'),runtime='available',definition_ref=asdict(r['ref']))
        return list(defaults.values())
    def definition(self,key):
        d=next((d for d in self.definitions() if d['key']==key),None)
        if not d:raise ValueError('Choose a configured domain')
        return d
    def allowed(self,d):return self.w.settings_admin or self.w.actor in d['leaders']
    def can_edit_knowledge(self,d):return self.w.actor in d['leaders']  # D005: only the team's lead edits its knowledge
    def assignments(self,data):
        members=data.get('members',data.get('leaders'));leaders=data.get('leaders')
        for values in (members,leaders):
            if not isinstance(values,list) or not 1<=len(values)<=len(ACTORS) or any(not isinstance(x,str) or x not in ACTORS for x in values) or len(set(values))!=len(values):raise ValueError('Assign existing project user identities')
        if not set(leaders)<=set(members):raise ValueError('Domain leaders must also be assigned users')
        return members,leaders
    def add(self,data):
        if not self.w.settings_admin:raise PermissionError('Only an administrator can add a domain')
        label=txt(data,'label',100,True);purpose=txt(data,'purpose',1200,True)
        members,leaders=self.assignments(data)
        template=data.get('template','research')
        if template not in DOMAINS:raise ValueError('Choose a Research or Design starting pattern')
        key=re.sub('[^a-z0-9]+','-',label.lower()).strip('-')
        if not key or len(key)>70:raise ValueError('Use a short domain name containing letters or numbers')
        with self.store.transaction():
            if any(d['key']==key or d['label'].casefold()==label.casefold() for d in self.definitions()):raise ValueError('A domain with this name is already configured')
            ref=self.store.put('DOMAIN-DEFINITION-'+key,'domain-definition',SCOPE,dict(key=key,label=label,purpose=purpose,leaders=leaders,members=members,template=template,created_by=self.w.actor,at=now(),runtime='available',boundary='Existing project users only. Domain assignment does not provision an account, grant project membership or connect external systems.'))
        return dict(domainKnowledge=key,message='Domain created. Assigned project users can select its private workbench. Configure its knowledge and methods before relying on the AI partner.',ref=asdict(ref))
    def update(self,data):
        d=self.definition(data.get('domain'))
        if not self.allowed(d):raise PermissionError('Only this domain’s leader or an administrator can edit its setup')
        members,leaders=self.assignments(data)
        if (set(members)!=set(d['members']) or set(leaders)!=set(d['leaders'])) and not self.w.settings_admin:raise PermissionError('Only an administrator can change domain user access or leadership')
        with self.store.transaction():
            d=self.definition(d['key'])
            if data.get('expected')!=d['definition_ref']:raise StaleBasis('Domain setup changed. Reopen it before saving')
            label=txt(data,'label',100,True);purpose=txt(data,'purpose',1200,True)
            if any(other['key']!=d['key'] and other['label'].casefold()==label.casefold() for other in self.definitions()):raise ValueError('Another domain already uses this name')
            reason=txt(data,'reason',1000,True)
            ref=self.store.put('DOMAIN-DEFINITION-'+d['key'],'domain-definition',SCOPE,dict(key=d['key'],label=label,purpose=purpose,members=members,leaders=leaders,template=d['template'],previous=d['definition_ref'],updated_by=self.w.actor,at=now(),reason=reason,runtime='available'),d['definition_ref']['revision'] if d['definition_ref'] else 0)
        return dict(domainKnowledge=d['key'],message='Domain setup version saved. Membership changes apply on the next request; prior work and source identities are retained.',ref=asdict(ref))
    def validate(self,entries,previous):
        if not isinstance(entries,list) or len(entries)>50:raise ValueError('Keep at most fifty knowledge entries in this bounded profile')
        result=[];oldids={e['id'] for e in previous};seen=set()
        for e in entries:
            if not isinstance(e,dict) or not FIELDS<=set(e)<=FIELDS|MEANING:raise ValueError('Provide the knowledge entry fields')
            id=e['id']
            if not isinstance(id,str) or not re.fullmatch(r'KN-[a-f0-9]{12}',id) or id in seen:raise ValueError('Keep distinct stable knowledge entry IDs')
            seen.add(id)
            if e['kind'] not in KINDS or e['status'] not in {'draft','active','archived'}:raise ValueError('Choose the knowledge type and review status')
            row={k:txt(e,k,n,k in ('title','definition')) for k,n in [('id',20),('kind',20),('title',120),('definition',1200),('parent_id',20),('subject_id',20),('predicate',100),('object_id',20),('source',1200),('status',20)]}
            aliases=e['aliases']
            if not isinstance(aliases,list) or len(aliases)>10 or any(not isinstance(a,str) or not a.strip() or len(a)>100 for a in aliases) or len(set(aliases))!=len(aliases):raise ValueError('Provide up to ten distinct aliases')
            row['aliases']=[a.strip() for a in aliases]
            if set(e)&MEANING:
                bounds={k:txt({k:e.get(k,'')},k,600,False) for k in ('includes','excludes','not_confused_with')};reach=e.get('reach','project')
                if reach not in REACH:raise ValueError('Choose how far this meaning reaches')
                if row['kind'] not in {'term','category'}:
                    if any(bounds.values()) or reach!='project':raise ValueError('Only terms and categories carry boundaries and reach')
                else:
                    before=next((meaning(o)['reach'] for o in previous if o['id']==id),'project')
                    if reach not in LEAD_REACH and reach!=before:raise ValueError('Reach beyond one domain needs an approved proposal')
                    row.update(bounds,reach=reach)
            if row['status']=='active' and not row['source']:raise ValueError('Active guidance needs its source or an explicit local rationale')
            result.append(row)
        if not oldids<=seen:raise ValueError('Archive prior entries instead of deleting their identity')
        byid={e['id']:e for e in result}
        for e in result:
            if e['kind']=='relationship':
                if not e['predicate'] or not e['subject_id'] or not e['object_id'] or e['subject_id']==e['object_id']:raise ValueError('A relationship needs distinct concepts and an explicit predicate')
                for id in (e['subject_id'],e['object_id']):
                    if id not in byid or byid[id]['kind'] not in {'term','category'}:raise ValueError('Link relationships to glossary terms or taxonomy categories in this domain')
                    if e['status']=='active' and byid[id]['status']!='active':raise ValueError('Active relationships must link active concepts')
            elif e['subject_id'] or e['object_id'] or e['predicate']:raise ValueError('Only relationships have concept endpoints and predicates')
            if e['parent_id']:
                if e['kind']!='category' or e['parent_id'] not in byid or byid[e['parent_id']]['kind']!='category':raise ValueError('A taxonomy parent must be a category in this domain')
                if e['status']=='active' and byid[e['parent_id']]['status']!='active':raise ValueError('An active taxonomy category requires an active parent')
                walked={e['id']};parent=e['parent_id']
                while parent:
                    if parent in walked:raise ValueError('Taxonomy categories cannot contain a cycle')
                    if parent not in byid or byid[parent]['kind']!='category':raise ValueError('Choose a valid taxonomy parent chain')
                    walked.add(parent);parent=byid[parent]['parent_id']
        return result
    def save(self,data):
        d=self.definition(data.get('domain'))
        if not self.can_edit_knowledge(d):raise PermissionError('Only this team’s lead can edit its knowledge')
        with self.store.transaction():
            current=snapshot(self.store,d['key'])
            if data.get('expected')!=current['ref']:raise StaleBasis('Domain knowledge changed. Reopen it before saving')
            entries=self.validate(data.get('entries'),current['entries']);reason=txt(data,'reason',1000,True)
            if any(e['status']=='active' for e in entries) and data.get('confirm_active') is not True:raise ValueError('Confirm the guidance marked active for this domain; it will be supplied to future assessments')
            ref=self.store.put('DOMAIN-KNOWLEDGE-'+d['key'],'domain-knowledge',SCOPE,dict(domain=d['key'],entries=entries,previous=current['ref'],author=self.w.actor,at=now(),reason=reason,authority='Domain-lead/admin configuration decision; not external certification'),current['ref']['revision'] if current['ref'] else 0)
        return dict(domainKnowledge=d['key'],ref=asdict(ref),message='Domain knowledge version saved. Active entries guide the next assessment; earlier interpretations retain their original basis.')
    def state(self):
        domains=[]
        for d in self.definitions():
            knowledge=snapshot(self.store,d['key']);history=[]
            if knowledge['ref']:
                for row in self.store.db.execute('SELECT revision FROM records WHERE id=? ORDER BY revision DESC',(knowledge['ref']['id'],)):
                    r=self.store.read(Ref(knowledge['ref']['id'],row[0]),{SCOPE});history.append(dict(ref=asdict(r['ref']),author=r['body']['author'],at=r['body']['at'],reason=r['body']['reason'],entries=r['body']['entries']))
            domains.append({**d,**knowledge,'can_edit':self.can_edit_knowledge(d),'can_setup':self.allowed(d),'history':history})
        return dict(domains=domains,can_add=self.w.settings_admin,can_manage_users=self.w.settings_admin,active=self.w.domains.key,available=[d['key'] for d in self.definitions() if self.w.actor in d['members']],kinds=KINDS,reach=REACH,lead_reach=sorted(LEAD_REACH),boundary='Project-local governed domain knowledge. Links are citations only; no source, graph or external policy synchronization is implied.')


def entry(kind,title,definition,source,status='active',**extra):
    return dict(id='KN-'+uuid4().hex[:12],kind=kind,title=title,definition=definition,aliases=[],parent_id='',subject_id='',predicate='',object_id='',source=source,status=status,**extra)


def seed_fictional_knowledge(work):
    """Only called for the isolated scenario, never on ordinary user projects."""
    for actor in ('sam','lee'):
        w=work[actor];key=w.domains.key
        if snapshot(w.store,key)['ref']:continue
        source='Fictional example agreed by the demo domain lead; not an enterprise policy or verified research result.'
        if key=='research':
            a=entry('term','Observation','A behavior or statement located in a defined task session; here all sessions are fictional.',source)
            b=entry('term','Finding','A bounded synthesis with source, method and limitations. It does not establish population prevalence.',source)
            c=entry('category','Evidence quality','Method, sample, counterevidence, applicability and uncertainty.',source)
            rel=entry('relationship','Observation informs finding','A finding may synthesize observations while retaining their scope and limits.',source);rel.update(subject_id=a['id'],predicate='informs',object_id=b['id'])
        else:
            a=entry('term','Local draft','Work retained on the device; it is not a server-confirmed submission.',source)
            b=entry('term','Confirmed submission','A report for which the authoritative storage operation has acknowledged success.',source)
            c=entry('category','Interruption and recovery','Pending, failed, retrying, retained and confirmed states need distinct behavior and language.',source)
            rel=entry('relationship','Local draft differs from confirmed submission','Do not collapse retained local work into a successful server submission.',source);rel.update(subject_id=a['id'],predicate='differs-from',object_id=b['id'])
        rule=entry('standard','Preserve uncertainty','Fictional examples, assumptions and prototype observations cannot become verified user needs or runtime results through an AI summary.',source)
        w.command('domain-knowledge-save',dict(domain=key,expected=None,entries=[a,b,c,rel,rule],reason='Seed clearly fictional, inspectable domain terminology and relationships.',confirm_active=True))

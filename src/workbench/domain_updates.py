"""Inspectable updates projected from actual public workflow records, never inference."""
from dataclasses import asdict
from hashlib import sha256
from .core import Ref
from .decisions import SCOPE, now
from .validation import reference
from .bridge import BOARDS

class DomainUpdates:
    def __init__(self,w):
        self.w=w;self.store=w.store
        # Account comes from the authenticated server session, never from command input.
        key=sha256(str(w.principal_id or ('local-role:'+w.actor)).encode()).hexdigest()[:24]
        self.scope='updates:'+key;self.id='UPDATE-READ-'+key
    def seen(self):
        row=self.store.db.execute('SELECT MAX(revision) FROM records WHERE id=?',(self.id,)).fetchone()[0]
        return self.store.read(Ref(self.id,row),{self.scope}) if row else None
    def state(self):
        seen=self.seen();opened={(r['id'],r['revision']) for r in seen['body']['refs']} if seen else set();updates=[]
        boards={'sam':{'business-research','research-design'},'lee':{'business-design','research-design'},'priya':{'business-research','business-design'}}.get(self.w.actor,set(BOARDS))
        boards.add('all-teams')
        if self.w.domains.key not in {None,'research','design'}:boards=set(BOARDS)
        issues={r['ref'].id:r for r in self.w.bridge.issues()}
        for r in self.w.latest_records():
            if r['scope']!=SCOPE:continue
            b=r['body'];issue=None;reqs=[];target=None;title=None;detail='';at=b.get('at',b.get('created_at',''))
            if r['kind']=='bridge-issue-event':
                issue=issues.get(b['issue']['id'])
                if not issue or not boards.intersection(issue['body']['boards']):continue
                title=issue['body']['title'];detail=b['note'];reqs=issue['body']['requirement_refs'];target=dict(kind='issue',id=issue['ref'].id)
                title=('Decision: ' if b['action']=='resolved' else 'Update: ')+title
            elif r['kind']=='domain-publication':
                c=self.store.read(reference(b['contribution']),{SCOPE});cb=c['body']
                if self.w.domains.key and cb.get('recipient') not in {self.w.domains.key,'bridge'} and cb.get('domain_key')!=self.w.domains.key:continue
                title='Released: '+cb['title'];detail=cb.get('handoff',{}).get('downstream_needs') or cb.get('observation','');reqs=cb.get('requirement_refs',[]);target=dict(kind='packet',ref=cb.get('packet'))
            elif r['kind']=='project-design-brief':
                title='Working brief '+('updated' if b.get('previous') else 'shared');detail='Changed: '+', '.join(b.get('changed_elements',[]));reqs=[v['ref'] for v in b['design_inputs']['requirements']];target=dict(kind='design-brief',ref=asdict(r['ref']));at=b['published_at']
            elif r['kind']=='design-brief-change':
                published=self.store.read(reference(b['published_brief']),{SCOPE});title='Working brief revision pending';detail=b['note'];reqs=[v['ref'] for v in published['body']['design_inputs']['requirements']];target=dict(kind='design-brief',ref=b['published_brief'])
            elif r['kind']=='demo-delivery-receipt':
                issue=issues.get(b['issue']['id'])
                if not issue or not boards.intersection(issue['body']['boards']):continue
                title='Demo '+('Jira' if b['target']=='jira' else 'ADO')+' '+b['operation']+': '+b['item_snapshot']['key'];detail=b['boundary'];reqs=[b['requirement']];target=dict(kind='demo-delivery',id=r['ref'].id)
            elif r['kind']=='decision':
                req=b.get('result_requirement');reqs=[req] if req else [raw for raw in b.get('basis',[]) if self.store.read(reference(raw),{SCOPE})['kind']=='requirement']
                title='Requirement decision: '+b['disposition'];detail=b['rationale'];target=dict(kind='requirement',id=reqs[0]['id']) if reqs else dict(kind='decisions')
            elif r['kind']=='decision-rights':
                title='Decision rights updated';detail=b['reason'];target=dict(kind='decision-rights')
            elif r['kind']=='decision-authority-event':
                title={'delegate':'Decision delegation updated','escalate':'Decision escalated','respond':'Escalation response recorded','refresh':'Decision rights refreshed','review':'Required assessment recorded'}.get(b['action'],'Decision authority updated')
                detail=b['reason'];raw=b['target'];target=dict(kind='issue',id=raw['id']) if b['target_kind']=='bridge-issue' else dict(kind='review' if b['target_kind']=='decision-case' else 'direction-review',id=raw['id'])
            else:continue
            updates.append(dict(ref=asdict(r['ref']),title=title,detail=detail,at=at,requirement_refs=reqs,target=target,new=(r['ref'].id,r['ref'].revision) not in opened,source_kind=r['kind'],boundary='Recorded update; inspect the decision and exact versions. Opening is not approval.'))
        return sorted(updates,key=lambda r:r['at'],reverse=True)[:20]
    def open(self,data):
        raw=reference(data.get('update'));available={(u['ref']['id'],u['ref']['revision']) for u in self.state()}
        if (raw.id,raw.revision) not in available:raise ValueError('Choose an update visible in this project feed')
        with self.store.transaction():
            old=self.seen();refs=old['body']['refs'] if old else [];refs=[asdict(raw),*[r for r in refs if r!=asdict(raw)]][:100]
            self.store.put(self.id,'project-update-read',self.scope,dict(refs=refs,at=now()),old['ref'].revision if old else 0)
        return dict(message='Update opened. No requirement or review context was changed.')

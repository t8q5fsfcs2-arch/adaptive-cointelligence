"""Explicitly simulated Jira/ADO updates after a real recorded local approval.

No network client or credential path exists here. Demo item snapshots and receipts
are separate record kinds and can never stand in for external delivery receipts.
"""
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256

from .core import Ref, StaleBasis
from .decisions import SCOPE, DecisionBlocked, fingerprint, now
from .validation import reference

BOUNDARY='DEMO ONLY. No request was sent to Jira or Azure DevOps; this is a local simulated work item.'

class DemoDelivery:
    def __init__(self,w):self.w=w;self.store=w.store;self.actor=w.actor
    def records(self,kind):return self.w.latest_records(kind)
    def authority(self,decision):
        actor=decision['body'].get('actor');actor=actor.get('id') if isinstance(actor,dict) else actor
        if self.actor!=actor:raise PermissionError('Use the recorded approval decision owner to simulate this delivery')
    def approval(self,raw,authorize=True):
        issue=self.w.bridge.current(raw,closed=True);b=issue['body'];resolution=b.get('resolution') or {}
        if b['status']!='resolved' or b['route']!='requirement' or resolution.get('disposition') not in {'approve','approved'} or not resolution.get('decision'):
            raise DecisionBlocked('A recorded requirement approval is needed before preparing a demo delivery update')
        decision=self.store.read(reference(resolution['decision']),{SCOPE});d=decision['body']
        if decision['kind']!='decision' or d.get('disposition')!='approve' or not d.get('result_requirement'):
            raise DecisionBlocked('Choose the governing requirement approval, not a comment or a no-change disposition')
        if authorize:self.authority(decision)
        requirement=self.store.latest(d['result_requirement']['id'],{SCOPE})
        if requirement['kind']!='requirement' or asdict(requirement['ref'])!=d['result_requirement'] or requirement['body'].get('status')!='approved' or requirement['body'].get('decision_id')!=decision['ref'].id:
            raise StaleBasis('The approved requirement changed. Use its current approval before simulating delivery')
        for other in self.w.bridge.issues():
            ob=other['body']
            if ob['status']!='resolved' and ob['route'] in {'intent','requirement'} and (any(r['id']==requirement['ref'].id for r in ob['requirement_refs']) or (ob['route']=='intent' and not ob['requirement_refs'])):
                raise DecisionBlocked('Resolve the open governing issue before simulating delivery of this requirement')
        if not requirement['body'].get('acceptance_criteria'):raise DecisionBlocked('Acceptance criteria are needed before a demo delivery update')
        for item in d.get('basis',[]):
            if item['id']==requirement['ref'].id:continue  # The approved result intentionally supersedes its own prior version.
            prior=self.store.read(reference(item),{SCOPE});current=self.store.latest(item['id'],{SCOPE})
            if current['ref']==prior['ref']:continue
            if prior['kind']=='intake-case' and prior['body'].get('snapshot')==current['body'].get('snapshot'):continue
            raise StaleBasis('The approval evidence or business context changed. Resolve it before preparing a demo delivery update')
        return issue,decision,requirement
    def snapshot(self,r,revision,key):
        b=r['body'];return dict(key=key,revision=revision,title=b.get('title') or b['text'][:120],text=b['text'],acceptance_criteria=b.get('acceptance_criteria',''),source=asdict(r['ref']),mode='simulated',boundary=BOUNDARY)
    def item_id(self,target,requirement):return 'DEMO-ITEM-'+sha256((target+'|'+requirement['ref'].id).encode()).hexdigest()[:20]
    def existing(self,id):
        row=self.store.db.execute('SELECT MAX(revision) FROM records WHERE id=?',(id,)).fetchone()[0]
        return self.store.read(Ref(id,row),{SCOPE}) if row else None
    def prepare(self,data):
        target=data.get('target')
        if target not in {'jira','ado'}:raise ValueError('Choose Jira or Azure DevOps for this simulation')
        with self.store.transaction():
            issue,decision,req=self.approval(data.get('issue'));item_id=self.item_id(target,req);item=self.existing(item_id)
            number=100+int(sha256(req['ref'].id.encode()).hexdigest()[:5],16)%9000
            key='DEMO-CLINIC-'+str(number) if target=='jira' else 'DEMO-ADO-'+str(number)
            before=deepcopy(item['body']['snapshot']) if item else None
            if not before and req['body'].get('supersedes'):
                predecessor=self.store.read(reference(req['body']['supersedes']),{SCOPE});before=self.snapshot(predecessor,1,key)
            if item and item['body']['snapshot']['source']==asdict(req['ref']):
                receipt=next((r for r in self.records('demo-delivery-receipt') if r['body']['item']==asdict(item['ref'])),None)
                if receipt:return dict(demoDeliveryPreview=receipt['body']['preview']['id'],message='Replay the saved demo preview. Simulating it again reuses the receipt without duplicating an item.')
            after=self.snapshot(req,(before['revision']+1) if before else 1,key)
            # Reuse existing payload preparation; it remains a preview, never an external send.
            prepared=self.w.delivery.prepare(dict(target=target,work_item_type='Story' if target=='jira' else 'User Story',destination='DEMO-CLINIC',requirements=[asdict(req['ref'])]))
            draft=self.store.latest(prepared['id'],self.w.scopes);payload=deepcopy(draft['body']['items'][0]['payload'])
            operation='update' if before else 'create';endpoint=draft['body']['items'][0]['endpoint'];method='POST'
            if before:
                if target=='jira':
                    method='PUT';endpoint='/rest/api/3/issue/'+key
                    payload['fields'].pop('project',None);payload['fields'].pop('issuetype',None)
                else:method='PATCH';endpoint='/DEMO-CLINIC/_apis/wit/workitems/'+str(number)+'?api-version=7.1'
            spec=dict(mode='simulated',issue=asdict(issue['ref']),decision=asdict(decision['ref']),requirement=asdict(req['ref']),target=target,destination='DEMO-CLINIC',work_item_type='Story' if target=='jira' else 'User Story',item_id=item_id,item_expected=asdict(item['ref']) if item else None,before=before,after=after,operation=operation,request=dict(method=method,endpoint=endpoint,payload=payload),boundary=BOUNDARY)
            digest=fingerprint(spec);id='DEMO-PREVIEW-'+digest[:20];old=self.existing(id)
            if not old:
                ref=self.store.put(id,'demo-delivery-preview',SCOPE,{**spec,'prepared_by':self.actor,'at':now(),'fingerprint':digest})
                for r in (issue,decision,req):self.store.depend(ref,r['ref'],{SCOPE})
        return dict(demoDeliveryPreview=id,message='Demo delivery preview prepared. No external request was sent.')
    def commit(self,data):
        if data.get('confirm_demo') is not True:raise ValueError('Confirm this is a simulated update, not a live external send')
        ref=reference(data.get('expected'));preview=self.store.latest(ref.id,{SCOPE})
        if preview['kind']!='demo-delivery-preview' or preview['ref']!=ref:raise StaleBasis('Reopen the exact demo preview before simulating its update')
        b=preview['body'];decision=self.store.read(reference(b['decision']),{SCOPE});self.authority(decision)
        with self.store.transaction():
            receipt_id='DEMO-RECEIPT-'+b['fingerprint'][:20];old=self.existing(receipt_id)
            if old:return dict(demoDeliveryReceipt=receipt_id,message='This exact demo update was already recorded; showing its saved receipt.')
            self.approval(b['issue']);current=self.existing(b['item_id'])
            if (asdict(current['ref']) if current else None)!=b['item_expected']:raise StaleBasis('The simulated item changed. Review a fresh demo preview')
            item=self.store.put(b['item_id'],'demo-delivery-item',SCOPE,dict(mode='simulated',target=b['target'],destination=b['destination'],snapshot=b['after'],approval=b['decision'],issue=b['issue'],updated_by=self.actor,at=now(),boundary=BOUNDARY),current['ref'].revision if current else 0)
            receipt=self.store.put(receipt_id,'demo-delivery-receipt',SCOPE,dict(mode='simulated',status='demo-update-recorded',target=b['target'],operation=b['operation'],preview=asdict(preview['ref']),item=asdict(item),item_snapshot=b['after'],before=b['before'],issue=b['issue'],decision=b['decision'],requirement=b['requirement'],actor=self.actor,at=now(),external_request_sent=False,boundary=BOUNDARY))
            for basis in [preview['ref'],item,reference(b['issue']),reference(b['decision']),reference(b['requirement'])]:self.store.depend(receipt,basis,{SCOPE})
        return dict(demoDeliveryReceipt=receipt.id,message='Demo '+('Jira' if b['target']=='jira' else 'Azure DevOps')+' update recorded locally. No external item was changed.')
    def state(self):
        previews=[];issues=[]
        for issue in self.w.bridge.issues():
            if issue['body']['route']!='requirement':continue
            try:
                _,decision,requirement=self.approval(asdict(issue['ref']),authorize=False)
                actor=decision['body'].get('actor');actor=actor.get('id') if isinstance(actor,dict) else actor
                issues.append(dict(issue_id=issue['ref'].id,eligible=True,can_prepare=self.actor==actor,decision=asdict(decision['ref']),requirement=asdict(requirement['ref'])))
            except (ValueError,PermissionError) as error:issues.append(dict(issue_id=issue['ref'].id,eligible=False,can_prepare=False,reason=str(error)))
        for r in self.records('demo-delivery-preview'):
            try:self.approval(r['body']['issue'],authorize=False);current=True
            except (ValueError,PermissionError):current=False
            previews.append({**r,'current':current})
        return dict(mode='simulated',connected=False,issues=issues,previews=previews,receipts=self.records('demo-delivery-receipt'),boundary=BOUNDARY)

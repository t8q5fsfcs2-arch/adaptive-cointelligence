"""Human-raised bridge issues linked to existing decisions. No model evaluation."""
from copy import deepcopy
from dataclasses import asdict
from uuid import uuid4
from pathlib import Path
import json

from .core import Ref, StaleBasis
from .decisions import SCOPE, DecisionBlocked, fingerprint, now
from .validation import reference
from .decision_receipts import DecisionReceipts
from .project_timeline import issue_waiting_since, timeline_page
from .team_timeline import team_timeline

CONFIG=json.loads((Path(__file__).parent/'config'/'bridges.json').read_text())
BOARDS=CONFIG['boards']
KINDS=CONFIG['issue_types']
ROLES=set(CONFIG['participants'])
OPEN = {'open','investigating','awaiting-decision','deferred'}


def text(data, key, maximum=12000, required=True):
    value=data.get(key,'')
    if not isinstance(value,str) or len(value)>maximum or (required and not value.strip()):
        raise ValueError('Provide '+key.replace('_',' ')+' within '+str(maximum)+' characters')
    return value.strip()


class Bridge:
    def __init__(self, workspace):
        self.w,self.store,self.actor=workspace,workspace.store,workspace.actor

    def participants(self):
        return ROLES | {a for d in self.w.domain_knowledge.definitions() for a in d['members']} | {a for rule in self.w.rights.state()['rules'].values() for a in [rule['decider'],*rule['reviewers'],*rule['delegates'],*rule['escalation_path']]}

    def author(self):
        if self.actor not in self.participants():raise PermissionError('Use a sponsor, Research, Design or requirement-owner role')

    def issues(self):
        return self.w.latest_records('bridge-issue')

    def current(self, raw, closed=False):
        self.author();ref=reference(raw);record=self.store.latest(ref.id,{SCOPE})
        if record['kind']!='bridge-issue' or record['ref']!=ref:raise StaleBasis('This issue changed. Reload before responding')
        if not closed and record['body']['status']=='resolved':raise DecisionBlocked('This issue is resolved. Reopen it explicitly for further work')
        return record

    def selection(self, data):
        raw=data.get('packet_refs')
        if not isinstance(raw,list) or not 1<=len(raw)<=10:raise ValueError('Choose one to ten published evidence trail')
        packets=[];basis=set();seen=set()
        for item in raw:
            ref=reference(item)
            if ref.id in seen:raise ValueError('Choose one version of each packet')
            seen.add(ref.id)
            packet=self.store.resolve_packet(ref.id,ref.revision,{SCOPE})
            packets.append(dict(id=ref.id,revision=ref.revision))
            basis.update(reference(r) for r in packet['refs'])
        affected=data.get('requirement_refs',[])
        if not isinstance(affected,list) or len(affected)>30:raise ValueError('Choose at most thirty affected requirements')
        reqs=sorted(set(reference(r) for r in affected))
        for ref in reqs:
            r=self.store.read(ref,{SCOPE})
            if r['kind']!='requirement' or self.store.latest(ref.id,{SCOPE})['ref']!=ref:raise StaleBasis('Choose the current affected requirement versions')
        route=data.get('route')
        if route not in {'requirement','intent','coordination'}:raise ValueError('Choose requirement change, business intent or coordination')
        target=None
        if route=='requirement':
            target=reference(data.get('target'))
            if target not in reqs:raise ValueError('Include the decision target among the affected requirements')
        elif route=='intent':
            try:target=self.store.latest('INT-001',{SCOPE})['ref']
            except PermissionError:raise DecisionBlocked('Publish the starting business direction before raising an intent change')
        if target:basis.add(target)
        basis.update(reqs)
        versions={}
        for p in self.store.packet_manifests({SCOPE}):versions.setdefault(p['id'],p['revision'])
        return dict(observed_versions=[dict(selected=asdict(r),current=asdict(self.store.latest(r.id,{SCOPE})['ref'])) for r in sorted(basis)],
                    observed_packets=[dict(id=p['id'],revision=versions[p['id']]) for p in packets],packet_refs=sorted(packets,key=lambda r:(r['id'],r['revision'])),basis=[asdict(r) for r in sorted(basis)],
                    requirement_refs=[asdict(r) for r in reqs],target=asdict(target) if target else None,route=route)

    def freshness(self, body, issue_id=None):
        changed=[]
        observed={x['selected']['id']+':'+str(x['selected']['revision']):reference(x['current']) for x in body.get('observed_versions',[])}
        for raw in body['basis']:
            # A packet may carry this issue's earlier pending state. Progress on the
            # same issue is not an independent changed evidence source. Other
            # issue versions, requirements, intent and sources retain all guards.
            if raw['id']==issue_id:continue
            r=reference(raw);r=observed.get(r.id+':'+str(r.revision),r);old=self.store.read(r,{SCOPE});current=self.store.latest(r.id,{SCOPE})
            if current['ref']==r:continue
            # Domain responses can version an intake review without changing its released snapshot.
            if old['kind']=='intake-case' and old['body']['snapshot']==current['body']['snapshot']:continue
            changed.append(dict(previous=asdict(r),current=asdict(current['ref'])))
        versions={}
        for p in self.store.packet_manifests({SCOPE}):versions.setdefault(p['id'],p['revision'])
        for p in body.get('observed_packets',body['packet_refs']):
            if versions.get(p['id'])!=p['revision']:
                changed.append(dict(previous_packet=p,current_packet=dict(id=p['id'],revision=versions.get(p['id']))))
        return changed

    def fresh(self, issue):
        if self.freshness(issue['body'],issue['ref'].id):raise StaleBasis('The issue context changed. Review and refresh its packet basis before authorizing a change')

    def owner(self, body, decision=False):
        canonical=body
        if (body.get('linked') or {}).get('kind')=='requirement':canonical=self.store.latest(body['linked']['ref']['id'],{SCOPE})['body']
        if decision:self.w.rights.authorize(canonical,body['route'])
        elif self.actor!=body['owner'] and not (self.w.rights.status(canonical,body['route'])['can_decide'] or (body['status']=='resolved' and self.actor==(self.w.rights.rules(body['route'])['decider'] if self.w.rights.current() else body['decision_owner']))):raise PermissionError('Only the issue owner or authorized decider can manage this issue')

    def save_event(self, issue, body, action, note, linked=None):
        body=deepcopy(body);body.update(updated_at=now(),updated_by=self.actor)
        ref=self.store.put(issue['ref'].id,'bridge-issue',SCOPE,body,issue['ref'].revision)
        event=self.store.put('BEVT-'+uuid4().hex[:12],'bridge-issue-event',SCOPE,dict(issue=asdict(ref),actor=self.actor,action=action,note=note,at=body['updated_at'],linked=linked,status=body['status']))
        self.store.depend(event,ref,{SCOPE})
        if linked:self.store.depend(ref,reference(linked),{SCOPE})
        for raw in body['basis']:self.store.depend(ref,reference(raw),{SCOPE})
        if body.get('linked'):self.store.depend(ref,reference(body['linked']['ref']),{SCOPE})
        return ref

    def create(self, data):
        self.author()
        with self.store.transaction():
            boards=data.get('boards')
            if not isinstance(boards,list) or not boards or len(boards)>len(BOARDS) or len(set(boards))!=len(boards) or any(b not in BOARDS for b in boards):raise ValueError('Choose one or more issue boards')
            owner=data.get('owner')
            if owner not in self.participants():raise ValueError('Assign an issue owner')
            kind=data.get('kind')
            if kind not in KINDS:raise ValueError('Choose a challenge type')
            chosen=self.selection(data)
            body=dict(**chosen,title=text(data,'title',200),question=text(data,'question'),consequence=text(data,'consequence'),
                      boards=sorted(boards),kind=kind,owner=owner,decision_owner='alex' if chosen['route']=='requirement' else 'priya' if chosen['route']=='intent' else owner,
                      status='open',next_owner=owner,next_question=text(data,'question'),created_by=self.actor,created_at=now(),linked=None,resolution=None)
            self.w.rights.bind(body,chosen['route'])
            signature=fingerprint({k:v for k,v in body.items() if k!='created_at'})
            for old in self.issues():
                if old['body'].get('signature')==signature and old['body']['status']!='resolved':return dict(message='This issue is already on the board.',id=old['ref'].id)
            body.update(signature=signature,updated_at=body['created_at'],updated_by=self.actor)
            ref=self.store.put('ISSUE-'+uuid4().hex[:12],'bridge-issue',SCOPE,body)
            for raw in body['basis']:self.store.depend(ref,reference(raw),{SCOPE})
            self.store.put('BEVT-'+uuid4().hex[:12],'bridge-issue-event',SCOPE,dict(issue=asdict(ref),actor=self.actor,action='raised',note=body['question'],at=body['created_at'],linked=None,status='open'))
        return dict(message='Issue raised on the selected issue board. No requirement or intent changed.',id=ref.id)

    def respond(self, data):
        with self.store.transaction():
            issue=self.current(data.get('expected'));b=issue['body'];action=data.get('action');note=text(data,'note')
            if action=='comment':pass
            elif action in {'answer-request','withdraw-request'}:
                request=b.get('information_request')
                if not request or request['status']!='open':raise DecisionBlocked('There is no open information request')
                if action=='answer-request' and self.actor!=request['owner']:raise PermissionError('Only the assigned responder can answer this request')
                if action=='withdraw-request':self.owner(b,True)
                request.update(status='answered' if action=='answer-request' else 'withdrawn',response=note,responded_by=self.actor,responded_at=now())
                b['last_linked_ref']=None
            elif action in {'investigate','request-evidence','assign'}:
                self.owner(b)
                if b.get('linked') and action=='assign':raise DecisionBlocked('A linked review determines the next decision owner; add a response or revise its proposal')
                owner=data.get('next_owner')
                if owner not in self.participants():raise ValueError('Choose who responds next')
                b.update(status='investigating',next_owner=owner,next_question=text(data,'next_question'))
                if action=='assign':b['owner']=owner
                if action=='request-evidence':b['information_request']=dict(owner=owner,question=b['next_question'],status='open',raised_by=self.actor,at=now())
            elif action=='defer':
                self.owner(b,True)
                if b.get('linked'):raise DecisionBlocked('Defer through the linked decision or sponsor response to keep both records connected')
                if data.get('next_owner') not in self.participants():raise ValueError('Choose who responds next')
                b.update(status='deferred',next_owner=data['next_owner'],next_question=text(data,'next_question'))
            else:raise ValueError('Choose comment, investigate, request evidence, assign or defer')
            ref=self.save_event(issue,b,action,note)
            if action in {'answer-request','withdraw-request'}:self.sync()
        return dict(message='Response saved to the issue history.',id=ref.id)

    def refresh(self, data):
        with self.store.transaction():
            issue=self.current(data.get('expected'),closed=True);b=issue['body'];self.owner(b)
            reopening=b['status']=='resolved'
            if reopening and data.get('confirm') is not True:raise ValueError('Confirm reopening this issue')
            chosen=self.selection({**data,'route':b['route']})
            if b['route']=='requirement' and chosen['target']['id']!=b['target']['id']:raise ValueError('Keep this issue attached to its original requirement target')
            b.update(chosen,status='investigating',next_owner=b['decision_owner'],next_question='Review the refreshed context and prepare the next response')
            if reopening:
                b.pop('decision_rights',None);self.w.rights.bind(b,b['route']);b['delegation']=None;b['escalation']=None;b['reviews']={}
                b.update(linked=None,resolution=None,last_linked_ref=None,information_request=None)
            ref=self.save_event(issue,b,'reopened' if reopening else 'basis-refreshed',text(data,'note'))
        return dict(message='Issue context refreshed. Earlier versions and decisions remain in history.',id=ref.id)

    def propose_requirement(self, data):
        with self.store.transaction():
            issue=self.current(data.get('expected_issue'));b=issue['body'];self.owner(b,True);self.fresh(issue)
            if b.get('integrity_review'):raise DecisionBlocked('Use a separate governing-change proposal; this issue reviews domain expressions without rewriting the anchor.')
            if b['route']!='requirement':raise ValueError('This issue is not routed to a requirement decision')
            allowed={reference(raw) for raw in b['basis']}
            if any(reference(raw) not in allowed for raw in data.get('selected',[])):raise ValueError('Select contributions from the issue packets or explicitly refresh the issue context')
            existing=None
            if b.get('linked'):
                existing=self.store.latest(b['linked']['ref']['id'],{SCOPE})
                if existing['kind']!='decision-case' or existing['body']['status'] in {'approved','rejected'}:raise DecisionBlocked('Reopen the issue before proposing another change')
            result=self.w.submit_proposal({**data,'target':b['target'],'need_context_refs':[asdict(r) for r in sorted(allowed) if self.store.read(r,{SCOPE})['kind']=='need-context'],'expected':asdict(existing['ref']) if existing else None})
            case=self.store.latest(result['id'],{SCOPE})
            b.update(linked=dict(kind='requirement',ref=asdict(case['ref'])),last_linked_ref=None)
            self.save_event(issue,b,'requirement-review-opened',text(data,'rationale'),asdict(case['ref']))
            self.sync()
        return dict(message='Requirement review linked. Domain responses and the owner decision are recorded on this issue.',id=issue['ref'].id)

    def link_review(self, data):
        with self.store.transaction():
            issue=self.current(data.get('expected'));b=issue['body'];self.owner(b,True)
            if b.get('integrity_review'):raise DecisionBlocked('Keep this interpretation review separate from a governing-change proposal.')
            if b['route']!='requirement' or b.get('linked'):raise DecisionBlocked('Choose an unlinked requirement issue')
            case=self.store.read(reference(data.get('case')),{SCOPE})
            if case['kind']!='decision-case' or case['body']['target']['id']!=b['target']['id'] or self.store.latest(case['ref'].id,{SCOPE})['ref']!=case['ref']:raise ValueError('Choose the current review for this requirement')
            allowed={reference(raw) for raw in b['basis']}
            if any(reference(raw) not in allowed for raw in case['body']['basis'] if self.store.read(reference(raw),{SCOPE})['kind']=='contribution'):raise ValueError('The review uses contributions outside this issue; refresh its packets first')
            b.update(linked=dict(kind='requirement',ref=asdict(case['ref'])),last_linked_ref=None)
            self.save_event(issue,b,'review-linked',text(data,'note'),asdict(case['ref']));self.sync()
        return dict(message='Existing requirement review linked to this issue.',id=issue['ref'].id)

    def propose_intent(self, data):
        with self.store.transaction():
            issue=self.current(data.get('expected_issue'));b=issue['body'];self.fresh(issue)
            if b['route']!='intent' or b.get('linked'):raise DecisionBlocked('Choose an unlinked business-intent issue')
            source=reference(data.get('source'))
            if asdict(source) not in b['basis']:raise ValueError('Choose a published contribution in the issue context')
            result=self.w.intake.refinements.create({**data,'base_intent':b['target'],'requirement_refs':b['requirement_refs']})
            request=self.store.latest(result['id'],{SCOPE});b.update(linked=dict(kind='intent',ref=asdict(request['ref'])),last_linked_ref=None)
            self.save_event(issue,b,'intent-response-requested',text(data,'rationale'),asdict(request['ref']));self.sync()
        return dict(message='Intent change routed to the sponsor. Draft adoption alone will not resolve this issue.',id=issue['ref'].id)

    def close(self, data):
        with self.store.transaction():
            issue=self.current(data.get('expected'));b=issue['body'];self.owner(b,True);self.fresh(issue)
            if b.get('linked') and not (self.w.rights.current() and b['linked']['kind']=='intent' and self.store.latest(b['linked']['ref']['id'],{SCOPE})['body']['status']=='declined'):raise DecisionBlocked('Record the outcome through the linked review or sponsor response')
            if data.get('confirm') is not True:raise ValueError('Confirm closing without changing requirements or intent')
            authority=self.w.rights.authorize(b,b['route'],approval=True)
            self.w.rights.require_reviews(b,b['route'])
            integrity=self.w.integrity.guard_close(issue)
            decision=self.store.put('BDEC-'+uuid4().hex[:12],'bridge-issue-decision',SCOPE,dict(issue=asdict(issue['ref']),actor=self.actor,authority=authority,at=now(),
                disposition='no-governing-change',integrity=integrity,rationale=text(data,'rationale'),basis=b['basis'],packet_refs=b['packet_refs'],boundary='Issue disposition only; no requirement approval, intent change or evidence validation'))
            if integrity:self.store.depend(decision,reference(integrity['assessment']),{SCOPE})
            for raw in b['basis']:self.store.depend(decision,reference(raw),{SCOPE})
            self.store.depend(decision,issue['ref'],{SCOPE})
            packet=self.store.packet('PKT-'+decision.id,1,'Issue disposition: '+b['title'],[decision,issue['ref'],*[reference(raw) for raw in b['basis']]],{SCOPE},{SCOPE})
            if b.get('information_request') and b['information_request']['status']=='open':
                b['information_request'].update(status='closed-by-disposition',response=text(data,'rationale'),responded_by=self.actor,responded_at=now())
            b.update(status='resolved',next_owner=None,next_question='',resolution=dict(disposition='no-governing-change',decision=asdict(decision),actor=self.actor,at=now(),rationale=text(data,'rationale'),packet=dict(id=packet['id'],revision=packet['revision'])))
            self.save_event(issue,b,'resolved',b['resolution']['rationale'],asdict(decision))
        return dict(message='Issue closed with a recorded rationale. Requirements and intent are unchanged.',id=issue['ref'].id)

    def information_clear(self, issue):
        if issue['body'].get('information_request',{} ) and issue['body']['information_request']['status']=='open':
            raise DecisionBlocked('Answer or explicitly withdraw the open information request before approving a change')

    def guard(self, action, data):
        if action=='decision' and data.get('disposition')=='approve':
            case=self.store.read(reference(data.get('expected')),{SCOPE});target=case['body']['target']['id']
            for issue in self.issues():
                b=issue['body']
                if b['status'] not in OPEN:continue
                relevant=any(r['id']==target for r in b['requirement_refs']) or (b['route']=='intent' and not b['requirement_refs'])
                if not relevant:continue
                linked=b.get('linked')
                if linked and linked['kind']=='requirement' and linked['ref']['id']==case['ref'].id:
                    self.fresh(issue);self.information_clear(issue)
                elif b['route'] in {'requirement','intent'}:
                    raise DecisionBlocked('Resolve or link the open issue "'+b['title']+'" before approving this requirement')
        if action=='intake-publish':
            draft=self.w.intake.draft()['body'];ids={r['id'] for r in draft.get('refinements',[])}
            for issue in self.issues():
                b=issue['body']
                if b['status'] not in OPEN or b['route']!='intent':continue
                if b.get('linked') and b['linked']['kind']=='intent' and b['linked']['ref']['id'] in ids:
                    self.fresh(issue);self.information_clear(issue)
                else:raise DecisionBlocked('Respond to the other open business-intent issue "'+b['title']+'" before publishing direction')

    def sync(self):
        """Consume recorded reviews/decisions atomically; never infer an approval."""
        for issue in self.issues():
            b=issue['body'];linked=b.get('linked')
            if not linked or b['status']=='resolved':continue
            record=self.store.latest(linked['ref']['id'],{SCOPE})
            if b.get('last_linked_ref')==asdict(record['ref']):continue
            rb=record['body'];status=rb['status'];resolution=None
            if linked['kind']=='requirement':
                if status in {'approved','rejected','deferred'}:
                    decision=self.store.latest(rb['decision_ids'][-1],{SCOPE});db=decision['body']
                    b.update(status='deferred' if status=='deferred' else 'resolved',next_owner=rb.get('next_owner'),next_question=rb.get('next_question',''))
                    resolution=dict(disposition=db['disposition'],decision=asdict(decision['ref']),actor=db['actor']['id'],at=db['at'],rationale=db['rationale'],requirement=rb.get('result_requirement'),packet=rb.get('result_packet'))
                else:
                    needed=[a for a,clearance in rb.get('required_reviews',{'sam':'supported-with-limits','maya':'cleared-with-conditions'}).items()
                            if a not in rb['reviews'] or self.store.read(reference(rb['reviews'][a]),{SCOPE})['body']['disposition']!=clearance]
                    rights=self.w.rights.status(rb,'requirement')
                    b['decision_owner']=rights['primary']
                    b.update(status='investigating' if needed or rights['blockers'] else 'awaiting-decision',next_owner=rights['next_owner'] if rights.get('escalation',{}) and rights['escalation'].get('status')=='open' else needed[0] if needed else rights['next_owner'],next_question='Record the domain assessment' if needed else 'Decide the reviewed requirement proposal')
            else:
                if status in {'incorporated','declined','deferred'}:
                    b.update(status='deferred' if status=='deferred' else 'resolved',next_owner=rb.get('next_owner'),next_question=rb.get('next_question',''))
                    resolution=dict(disposition=status,decision=rb.get('decision',asdict(record['ref'])),actor=rb.get('responded_by','priya'),at=rb.get('resolved_at',rb.get('responded_at')),rationale=rb.get('sponsor_rationale',''),intent=rb.get('result_intent'))
                else:b.update(status='investigating',next_owner='priya',next_question='Complete sponsor response and publish reviewed direction' if status=='drafted' else 'Respond to the proposed intent change')
            if b.get('information_request') and b['information_request']['status']=='open' and b['status']!='resolved':
                b.update(status='investigating',next_owner=b['information_request']['owner'],next_question=b['information_request']['question'])
            b.update(linked=dict(kind=linked['kind'],ref=asdict(record['ref'])),last_linked_ref=asdict(record['ref']))
            if resolution and self.w.rights.current() and linked['kind']=='intent' and status=='declined':
                rights=self.w.rights.status(b,'intent');b.update(status='awaiting-decision',next_owner=rights['next_owner'],next_question='Confirm the sponsor response and decide whether to close without changing direction');resolution=None
            if resolution:
                b['resolution']=resolution
                if b['status']=='resolved' and b.get('information_request') and b['information_request']['status']=='open':
                    b['information_request'].update(status='closed-by-disposition',response=resolution['rationale'],responded_by=resolution['actor'],responded_at=resolution['at'])
            self.save_event(issue,b,'resolved' if b['status']=='resolved' else 'linked-review-updated',resolution['rationale'] if resolution else b['next_question'],resolution['decision'] if resolution else asdict(record['ref']))

    def timeline(self, data):
        return timeline_page(self.store, data.get('before'))

    def state(self):
        events=self.w.latest_records('bridge-issue-event');issues=[];receipts=DecisionReceipts(self.store)
        for issue in self.issues():
            body=issue['body'];history=[e for e in events if e['body']['issue']['id']==issue['ref'].id]
            history.sort(key=lambda event: event['body']['issue']['revision'])
            waiting_since = issue_waiting_since(self.store, issue, history) if body['status'] in OPEN else None
            issues.append({**issue,'changed':self.freshness(body,issue['ref'].id),'events':history,
                           'integrity_available':all(any(r['kind']=='integrity-expression' for r in self.store.resolve_packet(q['id'],q['revision'],{SCOPE})['records']) for q in body['packet_refs']),'waiting_since':waiting_since,'integrity':self.w.integrity.decision_view(issue),'decision_receipt':receipts.for_issue(issue),'rights':self.w.rights.status(self.store.latest(body['linked']['ref']['id'],{SCOPE})['body'] if (body.get('linked') or {}).get('kind')=='requirement' else body,body['route']),
                           'basis_records':[self.store.read(reference(raw),{SCOPE}) for raw in body['basis']]})
        outcomes=[];seen=set()
        for event in events:
            eb=event['body'];raw=eb.get('linked')
            if not raw:continue
            r=self.store.read(reference(raw),{SCOPE});b=r['body'];key=(eb['issue']['id'],r['ref'])
            if key in seen or r['kind'] not in {'decision','intent-decision','bridge-issue-decision','intent-refinement'}:continue
            if r['kind']=='intent-refinement' and b['status'] not in {'declined','deferred','incorporated'}:continue
            seen.add(key);issue=next((i for i in issues if i['ref'].id==eb['issue']['id']),None)
            if issue:
                actor=b.get('actor',b.get('responded_by'))
                outcomes.append(dict(issue=eb['issue'],title=issue['body']['title'],decision=asdict(r['ref']),
                    disposition=b.get('disposition',b.get('status')),rationale=b.get('rationale',b.get('sponsor_rationale','')),
                    actor=actor.get('id') if isinstance(actor,dict) else actor,at=b.get('at',b.get('responded_at'))))
        return dict(boards=BOARDS,kinds=KINDS,issues=issues,outcomes=outcomes,actors=sorted(self.participants()),timeline=self.timeline({}),team_timeline=team_timeline(self.w,issues),evaluation='on-hold')

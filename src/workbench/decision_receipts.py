"""Read-only receipts from the exact shared transaction; never infer approval."""
from copy import deepcopy
from dataclasses import asdict
from .decisions import ACTORS, SCOPE
from .validation import reference
from .receipt_delivery import ReceiptDelivery


class DecisionReceipts:
    def __init__(self, store):
        self.store, self.cache = store, {}
        self.delivery = ReceiptDelivery(store)

    def read(self, raw):
        ref = reference(raw)
        if ref not in self.cache:
            self.cache[ref] = self.store.read(ref, {SCOPE})
        return self.cache[ref]

    def person(self, actor, authority=None):
        if isinstance(actor, dict):
            return dict(id=actor.get('id'), name=actor.get('name') or actor.get('id'), role=actor.get('role'))
        # Never substitute a current membership/name for the historical identity.
        saved = (authority or {}).get('policy', {}).get('people', {}).get(actor, {})
        return dict(id=actor, name=saved.get('name') or ACTORS.get(actor, {}).get('name') or actor or 'Not recorded', role=saved.get('role'))

    def evidence(self, raw):
        try:
            record = self.read(raw)
        except (PermissionError, ValueError, KeyError, TypeError):
            return dict(ref=raw, unavailable=True)
        body = record['body']
        fields = {k:body[k] for k in ('title','text','observation','interpretation','limitation','rationale','disposition','at','source') if isinstance(body.get(k), str) and body[k]}
        return dict(ref=asdict(record['ref']), kind=record['kind'], fields=fields)

    def for_issue(self, issue):
        if issue['body']['status'] != 'resolved':
            return None
        resolution = issue['body'].get('resolution') or {}
        raw = resolution.get('decision')
        unavailable = dict(available=False, decision=raw, message='The saved decision record is unavailable. No approved wording can be verified.')
        if not raw:
            return unavailable
        try:
            record = self.read(raw)
            # Older issue flows can point to the response carrying the formal decision.
            if record['kind']=='intent-refinement' and record['body'].get('decision'):
                record = self.read(record['body']['decision'])
            if record['kind'] not in {'decision','intent-decision','bridge-issue-decision','intent-refinement'}:
                return unavailable
            b=record['body']; authority=deepcopy(b.get('authority'));ratified_interpretation=None
            if b.get('integrity'):
                assessment=self.read(b['integrity']['assessment'])
                proposal=self.read(assessment['body']['context']['proposal'])
                ratified_interpretation=dict(ref=asdict(proposal['ref']),text=proposal['body']['text'],rationale=proposal['body']['rationale'])
            response=record['kind']=='intent-refinement'
            disposition=b.get('disposition',b.get('status'))
            approved=None; wording_message='No change to requirements or business direction was approved.'
            if record['kind']=='decision' and disposition=='approve':
                result=self.read(b['result_requirement'])
                if result['kind']!='requirement':return unavailable
                approved=dict(ref=asdict(result['ref']),kind='requirement',text=result['body']['text'],acceptance_criteria=result['body'].get('acceptance_criteria',''),conditions=result['body'].get('conditions',''))
            elif record['kind']=='intent-decision' and disposition=='publish-for-investigation':
                result=self.read(b['intent'])
                if result['kind']!='intent':return unavailable
                field=None
                if (issue['body'].get('linked') or {}).get('kind')=='intent':
                    request=self.read(issue['body']['linked']['ref'])
                    if request['kind']=='intent-refinement':field=request['body']['field']
                approved=dict(ref=asdict(result['ref']),kind='intent',field=field,text=result['body'].get('intake',{}).get(field,result['body']['text']))
            elif record['kind']=='decision' and disposition=='reject':
                wording_message='The proposal was rejected. No new requirement wording was approved.'
            elif response:
                wording_message='Sponsor response recorded. No new business direction was published by this response.'
            basis=list(b.get('basis',b.get('finding_basis',[])))
            reviews=dict(b.get('reviews',{}))
            # Coordination assessments live on the exact issue version the decider closed.
            if record['kind']=='bridge-issue-decision':
                closed_basis=self.read(b['issue'])
                reviews=dict(closed_basis['body'].get('reviews',{}))
            if response and b.get('source'):basis.append(b['source'])
            if b.get('case'):basis.append(b['case'])
            if b.get('previous_intent'):basis.append(b['previous_intent'])
            if b.get('refinements'):basis.extend(b['refinements'])
            seen=set();evidence=[]
            for item in basis:
                key=reference(item)
                if key not in seen:
                    seen.add(key);evidence.append(self.evidence(item))
            assessments=[]
            for actor, item in reviews.items():
                review=self.evidence(item)
                review['reviewer']=self.person(actor,authority)
                assessments.append(review)
            return dict(available=True, decision=asdict(record['ref']), kind=record['kind'], response_only=response,
                        outcome=disposition, decider=self.person(b.get('actor',b.get('responded_by')),authority),
                        at=b.get('at',b.get('responded_at')), rationale=b.get('sponsor_rationale','') if response else b.get('rationale',''),
                        approved=approved, wording_message=None if approved else wording_message,
                        evidence=evidence, reviews=assessments, authority=authority, integrity=deepcopy(b.get('integrity')), ratified_interpretation=ratified_interpretation, delivery=self.delivery.observed(issue,record,approved),
                        boundary=b.get('boundary','Sponsor response only; publication and formal approval are separate.' if response else 'Decision record only; external delivery is separate.'))
        except (PermissionError, ValueError, KeyError, TypeError):
            return unavailable

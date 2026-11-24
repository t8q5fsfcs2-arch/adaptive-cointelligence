"""Versioned project authority. Configuration never grants access to private work."""
from copy import deepcopy
from dataclasses import asdict
from uuid import uuid4

from .core import Ref, StaleBasis
from .decisions import ACTORS, SCOPE, DecisionBlocked, fingerprint, now

POLICY='PROJECT-DECISION-RIGHTS'
KINDS={'requirement':'Requirements','intent':'Business direction','coordination':'Coordination issues'}
CLOSED={'approved','rejected','published','declined','resolved'}
DEFAULTS={
 'requirement':dict(decider='alex',reviewers=['sam','lee'],delegates=[],escalation_path=[]),
 'intent':dict(decider='priya',reviewers=['sam','lee'],delegates=[],escalation_path=[]),
 'coordination':dict(decider='sam',reviewers=[],delegates=[],escalation_path=[]),
}


def review_clearance(kind,actor):
 return 'ready-for-investigation' if kind=='intent' else 'supported-with-limits' if actor=='sam' else 'cleared-with-conditions'


class DecisionRights:
 def __init__(self,store,actor=None,*,principal=None,admin=False,members=None):
  self.store,self.actor,self.principal,self.admin=store,actor,principal,bool(admin)
  self.members={a:dict(actor=a,name=p['name'],role=p['role'],principal=None) for a,p in ACTORS.items()} if members is None else {p['actor']:dict(p) for p in members if p['actor'] in ACTORS}
 def current(self):
  row=self.store.db.execute('SELECT revision FROM records WHERE id=? ORDER BY revision DESC LIMIT 1',(POLICY,)).fetchone()
  return self.store.read(Ref(POLICY,row[0]),{SCOPE}) if row else None
 def actor_id(self,actor=None):return self.actor if actor is None else actor
 def live_member(self,actor,people=None):
  if actor not in self.members:raise PermissionError('This person is no longer an assigned project member.')
  named=(people or {}).get(actor,{})
  if named.get('principal') is not None and named['principal']!=self.members[actor].get('principal'):
   raise PermissionError('The named account changed. An administrator must refresh Decision rights.')
 def rules(self,kind):
  current=self.current()
  return deepcopy(current['body']['rules'][kind] if current else DEFAULTS[kind])
 def state(self):
  current=self.current();rules=deepcopy(current['body']['rules'] if current else DEFAULTS)
  history=[]
  for row in self.store.db.execute('SELECT revision FROM records WHERE id=? ORDER BY revision DESC LIMIT 20',(POLICY,)):
   r=self.store.read(Ref(POLICY,row[0]),{SCOPE});b=r['body'];history.append(dict(ref=asdict(r['ref']),actor=b['actor'],at=b['at'],reason=b['reason'],rules=b['rules']))
  return dict(ref=asdict(current['ref']) if current else None,rules=rules,kinds=KINDS,members=list(self.members.values()),can_edit=self.admin,people=deepcopy(current['body'].get('people',{})) if current else {},history=history,
   can_prepare_requirement=self.actor in [rules['requirement']['decider'],*rules['requirement']['delegates']],
   boundary='Decision rights do not grant project membership, private document access or permission to send to Jira/ADO.',
   defaults=current is None)
 def save(self,data):
  if not self.admin:raise PermissionError('Only an administrator can configure project Decision rights.')
  rules=data.get('rules');reason=data.get('reason')
  if not isinstance(rules,dict) or set(rules)!=set(KINDS):raise ValueError('Configure each of the three decision types.')
  if not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise ValueError('Explain why these decision rights are being established or changed.')
  cleaned={};used=set()
  for kind,rule in rules.items():
   if not isinstance(rule,dict) or set(rule)!={'decider','reviewers','delegates','escalation_path'}:raise ValueError('Choose a decider, reviewers, delegates and escalation path.')
   decider=rule['decider']
   if not isinstance(decider,str):raise ValueError('Choose a named project member to decide.')
   self.live_member(decider);out=dict(decider=decider)
   for key in ('reviewers','delegates','escalation_path'):
    values=rule[key]
    if not isinstance(values,list) or len(values)>(3 if key=='escalation_path' else len(ACTORS)) or any(not isinstance(a,str) for a in values) or len(set(values))!=len(values):raise ValueError('Choose each project member once in each list.')
    for a in values:self.live_member(a)
    out[key]=list(values)
   if kind!='coordination' and not out['reviewers']:raise ValueError('Business direction and requirements need at least one required reviewer.')
   if decider in out['delegates'] or decider in out['reviewers'] or set(out['delegates'])&set(out['reviewers']):raise ValueError('Keep the decider and eligible delegates separate from required reviewers.')
   if decider in out['escalation_path']:raise ValueError('Choose another person as an escalation contact.')
   cleaned[kind]=out;used|={decider,*out['reviewers'],*out['delegates'],*out['escalation_path']}
  with self.store.transaction():
   previous=self.current();expected=asdict(previous['ref']) if previous else None
   if data.get('expected')!=expected:raise StaleBasis('Decision rights changed. Reopen the settings before saving.')
   body=dict(rules=cleaned,people={a:self.members[a] for a in sorted(used)},actor=self.actor,principal=self.principal,at=now(),reason=reason.strip(),previous=expected)
   ref=self.store.put(POLICY,'decision-rights',SCOPE,body,previous['ref'].revision if previous else 0)
  return dict(message='Decision rights saved. Open reviews must explicitly refresh their rights before a decision.',ref=asdict(ref))
 def snapshot(self,kind,body=None):
  body=body or {};current=self.current()
  if current:
   rule=current['body']['rules'][kind]
   return dict(kind=kind,policy=asdict(current['ref']),**deepcopy(rule),people=deepcopy(current['body']['people']))
  old=body.get('decision_rights')
  if old and old.get('policy') is None:return deepcopy(old)
  return self.legacy_snapshot(kind,body)
 def legacy_snapshot(self,kind,body):
  default=deepcopy(DEFAULTS[kind]);default['decider']=body.get('decision_owner',body.get('owner') if kind=='coordination' else default['decider'])
  if 'required_reviews' in body:default['reviewers']=list(body['required_reviews'])
  elif 'reviewers' in body:default['reviewers']=list(body['reviewers'])
  elif body.get('route'):default['reviewers']=[]
  return dict(kind=kind,policy=None,**default,people={})
 def bind(self,body,kind,*,review_field=None):
  basis={k:v for k,v in body.items() if k!='decision_rights'}
  snap=self.snapshot(kind,basis);body['decision_rights']=snap;body['decision_owner']=snap['decider']
  if review_field=='reviewers':body['reviewers']=snap['reviewers']
  else:body['required_reviews']={a:review_clearance(kind,a) for a in snap['reviewers']}
  return body
 def status(self,body,kind,actor=None):
  actor=self.actor_id(actor);saved=body.get('decision_rights') or self.legacy_snapshot(kind,body);current=self.snapshot(kind,body)
  closed=body.get('status') in CLOSED
  changed=not closed and saved.get('policy')!=current.get('policy')
  delegation=body.get('delegation') or {};delegate=delegation.get('delegate') if delegation.get('policy')==saved.get('policy') else None
  active=delegate or saved['decider'];escalation=body.get('escalation') or {};pending=escalation.get('status')=='open'
  problems=[]
  if changed:problems.append('Decision rights changed. Refresh this review to the current policy.')
  for a in {saved['decider'],*saved['reviewers'],*([delegate] if delegate else [])}:
   try:self.live_member(a,saved.get('people'))
   except PermissionError:problems.append('A named decider, delegate or required reviewer no longer has the recorded project account.')
  if pending:
   problems.append('An escalation response is needed before approval.')
   try:self.live_member(escalation.get('owner'),saved.get('people'))
   except PermissionError:problems.append('The escalation contact is no longer assigned; escalate to the next contact or update the policy.')
  if closed:problems=[]
  live=actor in self.members
  authority=live and actor==active and not changed
  for_decision=not closed and authority and not any('account' in p for p in problems)
  current_primary=current['decider']
  return dict(snapshot=saved,current_policy=current.get('policy'),current_decider=current_primary,changed=changed,closed=closed,primary=saved['decider'],active_decider=active,delegation=body.get('delegation'),escalation=body.get('escalation'),blockers=list(dict.fromkeys(problems)),
   can_decide=for_decision,can_approve=for_decision and not problems,can_review=live and not closed and not changed and actor in saved['reviewers'],
   can_refresh=live and not closed and actor==current_primary,
   can_delegate=live and not closed and not changed and actor==saved['decider'],
   can_escalate=live and not closed and not changed and bool(saved['escalation_path']),
   can_respond=live and not closed and not changed and pending and actor==escalation.get('owner'),
   next_owner=current_primary if changed else escalation.get('owner') if pending else active)
 def authorize(self,body,kind,actor=None,*,approval=False):
  actor=self.actor_id(actor);status=self.status(body,kind,actor)
  if status['changed']:raise StaleBasis(status['blockers'][0])
  self.live_member(actor,status['snapshot'].get('people'))
  if not status['can_decide']:raise PermissionError('Only the named decider or the explicitly activated delegate can decide.')
  if approval and status['blockers']:raise DecisionBlocked('; '.join(status['blockers']))
  return self.receipt(body,kind,actor)
 def receipt(self,body,kind,actor=None):
  actor=self.actor_id(actor);s=self.status(body,kind,actor)
  return dict(policy=s['snapshot'],actor=actor,principal=self.principal if actor==self.actor else None,authorized_as='delegate' if s['delegation'] and s['active_decider']==actor else 'decider',delegation=s['delegation'],escalation=s['escalation'])
 def check_review(self,body,kind,actor):
  status=self.status(body,kind,actor)
  if status['changed']:raise StaleBasis('Decision rights changed. Refresh the review before collecting assessments.')
  self.live_member(actor,status['snapshot'].get('people'))
  if not status['can_review']:raise PermissionError('Only a required reviewer for this decision may submit an assessment.')
 def require_reviews(self,body,kind):
  for actor in self.status(body,kind)['snapshot']['reviewers']:
   raw=body.get('reviews',{}).get(actor)
   if not raw:raise DecisionBlocked('A required review is still missing.')
   review=self.store.read(Ref(**raw),{SCOPE})['body']
   if review.get('disposition')!=review_clearance(kind,actor):raise DecisionBlocked('Resolve the required reviewer’s outstanding concern.')
   if review.get('basis_fingerprint')!=fingerprint(body.get('basis',[])):raise StaleBasis('A review does not cover the current issue context.')
 def kind(self,record):
  if record['kind']=='decision-case':return 'requirement'
  if record['kind']=='intake-case':return 'intent'
  if record['kind']=='bridge-issue':return record['body']['route']
  raise ValueError('Choose a requirement review, direction review or issue.')
 def action(self,data):
  raw=data.get('expected');action=data.get('action');reason=data.get('reason')
  if not isinstance(raw,dict):raise ValueError('Reopen the exact review before changing its authority.')
  if not isinstance(reason,str) or not reason.strip() or len(reason)>2000:raise ValueError('Explain this authority or escalation action.')
  if self.actor not in self.members:raise PermissionError('Use an assigned project identity.')
  with self.store.transaction():
   r=self.store.latest(raw.get('id'),{SCOPE})
   if asdict(r['ref'])!=raw:raise StaleBasis('This review changed. Reopen it before continuing.')
   kind=self.kind(r);b=deepcopy(r['body']);s=self.status(b,kind)
   if action in {'delegate','respond'}:self.live_member(self.actor,s['snapshot'].get('people'))
   if s['closed']:raise DecisionBlocked('This decision is closed. Reopen the issue or prepare a new proposal.')
   if r['kind']=='bridge-issue' and (b.get('linked') or {}).get('kind')=='requirement':raise DecisionBlocked('Use the linked requirement or direction review to manage its authority.')
   if action=='refresh':
    if not s['can_refresh']:raise PermissionError('The current policy’s named decider must refresh the review.')
    self.live_member(self.actor,self.snapshot(kind,b).get('people'))
    self.bind(b,kind,review_field='reviewers' if r['kind']=='intake-case' else None)
    b['delegation']=None;b['escalation']=None
    b['reviews']={a:v for a,v in b.get('reviews',{}).items() if a in b['decision_rights']['reviewers']}
   elif action=='delegate':
    if not s['can_delegate']:raise PermissionError('Only the named primary decider can activate or withdraw delegation.')
    target=data.get('delegate')
    if target is not None and target not in s['snapshot']['delegates']:raise PermissionError('Choose a delegate explicitly permitted by the recorded policy.')
    if target:self.live_member(target,s['snapshot'].get('people'))
    b['delegation']=dict(delegate=target,by=self.actor,at=now(),policy=s['snapshot']['policy'],reason=reason.strip()) if target else None
   elif action=='escalate':
    if not s['can_escalate']:raise PermissionError('No escalation path is available for this review.')
    old=b.get('escalation') or {};index=old.get('position',-1)+1 if old.get('status')=='open' else 0
    path=s['snapshot']['escalation_path']
    if index>=len(path):raise DecisionBlocked('The escalation path is exhausted. Ask an administrator to update Decision rights.')
    target=path[index];self.live_member(target,s['snapshot'].get('people'))
    b['escalation']=dict(status='open',owner=target,position=index,requested_by=self.actor,at=now(),reason=reason.strip())
   elif action=='respond':
    if not s['can_respond']:raise PermissionError('Only the named escalation contact can record this response.')
    b['escalation'].update(status='answered',response=reason.strip(),responded_by=self.actor,responded_at=now())
   elif action=='review':
    if r['kind']!='bridge-issue':raise ValueError('Use the existing domain assessment form for this review.')
    self.check_review(b,kind,self.actor);disposition=data.get('disposition')
    if disposition not in {review_clearance(kind,self.actor),'concerns-remain'}:raise ValueError('Choose supported or concerns remain.')
    reviewed=self.store.put('AUTH-REVIEW-'+uuid4().hex[:12],'decision-rights-review',SCOPE,dict(actor=self.actor,at=now(),disposition=disposition,rationale=reason.strip(),basis_fingerprint=fingerprint(b.get('basis',[])),issue=raw))
    b.setdefault('reviews',{})[self.actor]=asdict(reviewed)
   else:raise ValueError('Choose refresh, delegate, escalate, respond or review.')
   b.update(authority_updated_at=now(),authority_updated_by=self.actor)
   if r['kind']=='bridge-issue':b.update(next_owner=self.status(b,kind)['next_owner'],updated_at=now(),updated_by=self.actor)
   result=self.store.put(r['ref'].id,r['kind'],SCOPE,b,r['ref'].revision)
   event=self.store.put('AUTH-EVENT-'+uuid4().hex[:12],'decision-authority-event',SCOPE,dict(target=asdict(result),target_kind=r['kind'],action=action,actor=self.actor,principal=self.principal,at=now(),reason=reason.strip(),policy=b['decision_rights']['policy']))
   self.store.depend(result,event,{SCOPE})
  return dict(message='Decision authority action recorded. Approval and external delivery remain separate.',id=result.id,authority_target=asdict(result))

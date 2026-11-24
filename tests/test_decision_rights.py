"""Real versioned policies, delegation and escalation over existing decision services."""
from copy import deepcopy
from dataclasses import asdict
import unittest

from workbench.core import Ref,StaleBasis
from workbench.decisions import SCOPE,DecisionBlocked
from workbench.decision_rights import DEFAULTS,DecisionRights
from workbench.workspace import Workspace
import test_bridge as fixtures

class DecisionRightsTests(unittest.TestCase):
 def setUp(self):
  self.f=fixtures.BridgeTests();self.f.setUp();self.store=self.f.store
 def tearDown(self):self.f.tearDown()
 def w(self,actor,**kw):return Workspace(self.store,actor,fixtures.fixtures.NoEvaluation(),**kw)
 def policy(self,change=None):
  rules=deepcopy(DEFAULTS);rules['requirement'].update(delegates=['priya'],escalation_path=['maya']);rules['intent'].update(delegates=['alex'],escalation_path=['maya']);rules['coordination'].update(decider='sam',reviewers=['lee'],delegates=['priya'],escalation_path=['alex'])
  if change:change(rules)
  rights=self.w('administrator',admin=True).rights
  return rights.save(dict(expected=asdict(rights.current()['ref']) if rights.current() else None,rules=rules,reason='Synthetic project accountability agreement'))
 def target(self,r):return self.store.latest(r['ref'].id,{SCOPE})
 def action(self,actor,r,action,**kw):return self.w(actor).command('decision-rights-action',dict(expected=asdict(self.target(r)['ref']),action=action,reason='Synthetic explicit authority action',**kw))
 def case(self,i):return self.f.case(i)
 def open_case(self):
  self.policy();i=self.f.issue();self.f.propose(i);return i,self.case(i)
 def decision(self,actor,c,disposition='approve'):
  return self.w(actor).command('decision',dict(expected=asdict(self.target(c)['ref']),disposition=disposition,rationale='Synthetic exact-version decision',confirm=True,next_owner='sam',next_question='Review the stated concern'))
 def test_only_admin_configures_and_invalid_or_self_reviewing_policies_are_rejected_atomically(self):
  with self.assertRaises(PermissionError):self.w('priya').rights.save(dict(rules=DEFAULTS,reason='Not an admin'))
  for change in [lambda r:r['requirement'].update(reviewers=[]),lambda r:r['requirement'].update(reviewers=['alex']),lambda r:r['requirement'].update(delegates=['sam']),lambda r:r['intent'].update(decider='unknown')]:
   with self.assertRaises((ValueError,PermissionError)):self.policy(change)
  self.assertIsNone(self.w('alex').rights.current())
  self.policy();old=self.w('alex').rights.current()
  with self.assertRaises(StaleBasis):self.w('administrator',admin=True).rights.save(dict(expected=None,rules=DEFAULTS,reason='Stale settings'))
  self.assertEqual(self.w('alex').rights.current(),old)
 def test_configured_decider_is_enforced_and_admin_has_no_decision_override(self):
  self.policy(lambda r:r['requirement'].update(decider='priya',delegates=['alex']))
  i=self.f.issue();self.w('priya').command('bridge-propose',dict(expected_issue=asdict(i['ref']),text='Use a supported cue',rationale='Synthesize the two domains',acceptance_criteria='Observe resumption',conditions='Synthetic only',selected=[asdict(self.f.rc['ref']),asdict(self.f.dc['ref'])],changes_intent=False));c=self.case(i);self.f.reviews(i)
  self.assertEqual(c['body']['decision_owner'],'priya')
  for actor,kw in [('alex',{}),('administrator',dict(admin=True))]:
   with self.assertRaises(PermissionError):self.w(actor,**kw).command('decision',dict(expected=asdict(self.case(i)['ref']),disposition='approve',rationale='Unauthorized',confirm=True))
  self.decision('priya',c);self.assertEqual(self.target(c)['body']['status'],'approved')
 def test_delegate_must_be_explicitly_activated_and_cannot_delegate_onward(self):
  i,c=self.open_case();self.f.reviews(i)
  with self.assertRaises(PermissionError):self.decision('priya',c)
  self.action('alex',c,'delegate',delegate='priya')
  with self.assertRaises(PermissionError):self.action('priya',c,'delegate',delegate='maya')
  with self.assertRaises(PermissionError):self.decision('alex',c)
  self.decision('priya',c)
  decision=self.w('alex').loop.history()[-1]['body'];self.assertEqual(decision['actor']['id'],'priya');self.assertEqual(decision['authority']['authorized_as'],'delegate');self.assertEqual(decision['authority']['policy']['policy'],self.w('alex').rights.state()['ref'])
  self.assertEqual(self.target(c)['body']['decision_owner'],'alex')
 def test_withdrawing_delegation_returns_authority_to_primary(self):
  i,c=self.open_case();self.f.reviews(i);self.action('alex',c,'delegate',delegate='priya');self.action('alex',c,'delegate',delegate=None)
  with self.assertRaises(PermissionError):self.decision('priya',c)
  self.decision('alex',c)
 def test_escalation_blocks_approval_and_contact_response_does_not_approve(self):
  i,c=self.open_case();self.f.reviews(i);self.action('sam',c,'escalate')
  before=self.store.latest(self.f.req['ref'].id,{SCOPE})
  with self.assertRaises(DecisionBlocked):self.decision('alex',c)
  with self.assertRaises(PermissionError):self.action('lee',c,'respond')
  with self.assertRaises(PermissionError):self.decision('maya',c)
  self.action('maya',c,'respond');self.assertEqual(self.store.latest(before['ref'].id,{SCOPE}),before)
  self.decision('alex',c);self.assertEqual(self.target(c)['body']['status'],'approved')
 def test_escalation_path_is_ordered_and_cannot_be_bypassed_or_silently_exhausted(self):
  self.policy(lambda r:r['coordination'].update(escalation_path=['alex','maya']))
  i=self.f.issue('coordination');self.action('lee',i,'escalate');self.assertEqual(self.target(i)['body']['escalation']['owner'],'alex')
  self.action('lee',i,'escalate');self.assertEqual(self.target(i)['body']['escalation']['owner'],'maya')
  with self.assertRaises(DecisionBlocked):self.action('lee',i,'escalate')
  with self.assertRaises(PermissionError):self.action('alex',i,'respond')
  self.action('maya',i,'respond')
 def test_policy_change_requires_explicit_refresh_and_preserves_prior_approval(self):
  i,c=self.open_case();self.f.reviews(i);self.decision('alex',c);approved=self.target(c);old=self.store.latest(self.f.req['ref'].id,{SCOPE});old_decisions=self.w('alex').loop.history()
  self.policy(lambda r:r['requirement'].update(decider='priya',delegates=['alex']))
  status=self.w('sam').rights.status(approved['body'],'requirement');self.assertTrue(status['closed']);self.assertFalse(status['changed']);self.assertEqual(status['primary'],'alex')
  self.assertEqual(self.target(c),approved);self.assertEqual(self.store.latest(old['ref'].id,{SCOPE}),old);self.assertEqual(self.w('alex').loop.history(),old_decisions)
 def test_open_legacy_case_does_not_inherit_new_rights_without_refresh(self):
  i=self.f.issue();self.f.propose(i);c=self.case(i);self.f.reviews(i)
  self.policy(lambda r:r['requirement'].update(decider='priya',delegates=['alex']))
  for actor in ('alex','priya'):
   with self.assertRaises(StaleBasis):self.decision(actor,c)
  with self.assertRaises(PermissionError):self.action('alex',c,'refresh')
  self.action('priya',c,'refresh');self.decision('priya',c)
 def test_required_reviewers_change_is_honored_after_refresh(self):
  i,c=self.open_case();self.f.reviews(i)
  self.policy(lambda r:r['requirement'].update(reviewers=['sam','lee','maya']))
  self.action('alex',c,'refresh')
  with self.assertRaises(DecisionBlocked):self.decision('alex',c)
  self.w('maya').command('review',dict(expected=asdict(self.target(c)['ref']),disposition='cleared-with-conditions',rationale='Additional bounded domain assessment'))
  self.decision('alex',c)
 def test_membership_and_named_account_revocation_block_queued_authority(self):
  i,c=self.open_case();self.action('alex',c,'delegate',delegate='priya')
  members=[dict(actor=a,name=a,role=a,principal=None) for a in ('alex','sam','lee','maya')]
  status=self.w('alex',decision_members=members).rights.status(self.target(c)['body'],'requirement')
  self.assertTrue(status['blockers']);self.assertFalse(status['can_decide'])
  with self.assertRaises(PermissionError):self.w('priya',decision_members=members).rights.authorize(self.target(c)['body'],'requirement')
 def test_coordination_requires_configured_reviews_before_named_delegate_can_close(self):
  self.policy();i=self.f.issue('coordination');self.action('sam',i,'delegate',delegate='priya')
  with self.assertRaises(DecisionBlocked):self.w('priya').command('bridge-close',dict(expected=asdict(self.target(i)['ref']),rationale='Missing required review',confirm=True))
  self.w('lee').command('decision-rights-action',dict(expected=asdict(self.target(i)['ref']),action='review',disposition='cleared-with-conditions',reason='Checked the bounded shared context'))
  self.w('priya').command('bridge-close',dict(expected=asdict(self.target(i)['ref']),rationale='Reviewed coordination outcome',confirm=True))
  self.assertEqual(self.target(i)['body']['status'],'resolved');self.assertEqual(self.target(i)['body']['resolution']['actor'],'priya')
 def test_stale_target_and_unapproved_delegate_cannot_change_rights(self):
  i,c=self.open_case();old=asdict(c['ref']);self.action('alex',c,'delegate',delegate='priya')
  with self.assertRaises(StaleBasis):self.w('alex').command('decision-rights-action',dict(expected=old,action='delegate',delegate=None,reason='Stale target'))
  with self.assertRaises(PermissionError):self.action('alex',c,'delegate',delegate='maya')
  self.assertEqual(self.target(c)['body']['delegation']['delegate'],'priya')
 def test_sponsor_response_does_not_replace_the_configured_intent_decider(self):
  self.f.fixture.sponsor();self.policy(lambda r:r['intent'].update(decider='alex',delegates=['priya']))
  baseline=self.store.latest('INT-001',{SCOPE});i=self.f.issue('intent')
  self.w('sam').command('bridge-intent-propose',dict(expected_issue=asdict(i['ref']),source=asdict(self.f.rc['ref']),field='in_scope',proposed_value='A different scope',rationale='Proposed extension'))
  request=self.store.latest(self.target(i)['body']['linked']['ref']['id'],{SCOPE})
  self.w('priya').command('intent-dispose',dict(expected=asdict(request['ref']),disposition='declined',rationale='Sponsor retains the current draft scope'))
  self.assertEqual(self.target(i)['body']['status'],'awaiting-decision')
  for actor,clearance in [('sam','ready-for-investigation'),('lee','ready-for-investigation')]:
   self.w(actor).command('decision-rights-action',dict(expected=asdict(self.target(i)['ref']),action='review',disposition=clearance,reason='Review the shared no-change disposition'))
  with self.assertRaises(PermissionError):self.w('priya').command('bridge-close',dict(expected=asdict(self.target(i)['ref']),rationale='Not the named decider',confirm=True))
  self.w('alex').command('bridge-close',dict(expected=asdict(self.target(i)['ref']),rationale='Confirm the reviewed no-change outcome',confirm=True))
  self.assertEqual(self.target(i)['body']['status'],'resolved');self.assertEqual(self.store.latest('INT-001',{SCOPE}),baseline)

 def test_reassigned_account_cannot_activate_delegation_or_answer_prior_escalation(self):
  members=[dict(actor=a,name=a,role=a,principal='original-'+a) for a in ('priya','sam','lee','alex','maya')]
  rights=self.w('administrator',admin=True,decision_members=members).rights
  rules=deepcopy(DEFAULTS);rules['coordination'].update(delegates=['priya'],escalation_path=['maya'])
  rights.save(dict(expected=None,rules=rules,reason='Bind explicit project accounts'))
  c=self.f.issue('coordination');self.w('lee',decision_members=members).command('decision-rights-action',dict(expected=asdict(c['ref']),action='escalate',reason='Request the recorded contact'))
  for actor,action,payload in [('sam','delegate',dict(delegate='priya')),('maya','respond',{})]:
   changed=deepcopy(members);next(m for m in changed if m['actor']==actor)['principal']='replacement-'+actor
   with self.assertRaises(PermissionError):
    self.w(actor,decision_members=changed).command('decision-rights-action',dict(expected=asdict(self.target(c)['ref']),action=action,reason='Replacement account must not inherit authority',**payload))
  self.assertIsNone(self.target(c)['body'].get('delegation'));self.assertEqual(self.target(c)['body']['escalation']['status'],'open')

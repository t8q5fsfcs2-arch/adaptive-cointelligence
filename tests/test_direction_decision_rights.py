from copy import deepcopy
from dataclasses import asdict
import unittest
from workbench.core import StaleBasis
from workbench.decisions import SCOPE,DecisionBlocked
from workbench.decision_rights import DEFAULTS
from workbench.workspace import Workspace
import test_intake as fixtures

class DirectionDecisionRightsTests(unittest.TestCase):
 def setUp(self):self.f=fixtures.IntakeTests();self.f.setUp();self.store=self.f.store
 def tearDown(self):self.f.tearDown()
 def w(self,actor,**kw):return Workspace(self.store,actor,**kw)
 def configure(self):
  rules=deepcopy(DEFAULTS);rules['intent'].update(decider='alex',reviewers=['sam','maya'],delegates=['priya'],escalation_path=['lee'])
  rights=self.w('administrator',admin=True).rights
  return rights.save(dict(expected=asdict(rights.current()['ref']) if rights.current() else None,rules=rules,reason='Named direction decision authority'))
 def case(self,id):return self.store.latest(id,{SCOPE})
 def act(self,actor,id,action,**extra):return self.w(actor).command('decision-rights-action',dict(expected=asdict(self.case(id)['ref']),action=action,reason='Explicit direction authority action',**extra))
 def publish(self,actor,id):return self.w(actor).command('intake-publish',dict(expected=asdict(self.case(id)['ref']),confirm=True,rationale='Reviewed direction for bounded investigation'))
 def test_named_decider_publishes_shared_direction_without_receiving_private_draft(self):
  self.configure();id=self.f.prepare();self.f.review(id)
  self.assertEqual(self.case(id)['body']['decision_owner'],'alex');self.assertIsNone(self.w('alex').state()['intake']['draft'])
  with self.assertRaises(PermissionError):self.publish('priya',id)
  self.publish('alex',id);self.assertEqual(self.case(id)['body']['status'],'published')
  receipt=self.w('alex').intake.state()['decisions'][0]['body'];self.assertEqual(receipt['actor'],'alex');self.assertEqual(receipt['authority']['authorized_as'],'decider')
 def test_explicit_direction_delegate_and_escalation_gates(self):
  self.configure();id=self.f.prepare();self.f.review(id)
  self.act('alex',id,'delegate',delegate='priya');self.act('sam',id,'escalate')
  with self.assertRaises(DecisionBlocked):self.publish('priya',id)
  with self.assertRaises(PermissionError):self.act('maya',id,'respond')
  self.act('lee',id,'respond');self.publish('priya',id)
  receipt=self.w('alex').intake.state()['decisions'][0]['body'];self.assertEqual(receipt['authority']['authorized_as'],'delegate')
 def test_legacy_direction_review_must_refresh_and_existing_publication_is_preserved(self):
  id=self.f.prepare();self.f.review(id);self.configure()
  with self.assertRaises(StaleBasis):self.publish('priya',id)
  with self.assertRaises(StaleBasis):self.publish('alex',id)
  self.act('alex',id,'refresh');self.publish('alex',id);before=self.case(id)
  self.configure();self.assertEqual(self.case(id),before);rights=self.w('sam').rights.status(before['body'],'intent');self.assertFalse(rights['changed']);self.assertTrue(rights['closed'])

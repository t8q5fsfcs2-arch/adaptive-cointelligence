"""Authenticated project member bindings and direct API permission enforcement."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest

from workbench.core import Store
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench.web import BrowserServer
from workbench.model_provider import UnconfiguredModel
from test_access import Client,PASSWORD

class DecisionRightsHTTPTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=TemporaryDirectory();path=Path(cls.tmp.name)/'rights.sqlite3';store=Store(path);owner=Workspace(store,'alex',UnconfiguredModel());owner.setup(dict(title='Synthetic decision rights',intent='Keep context',boundary='Synthetic test only'));cls.req=owner.create_requirement(dict(title='Preserve progress',text='Preserve progress',rationale='Avoid repetition',conditions='Bounded',drawer='Experience',acceptance_criteria='Observe resumption'))
  cls.target=asdict(store.latest(cls.req['id'],{SCOPE})['ref']);cls.packet=dict(id='PKT-'+cls.req['id'],revision=1);store.close()
  cls.server=BrowserServer(('127.0.0.1',0),path,UnconfiguredModel());cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.admin=Client(cls.server);token=cls.server.access.setup_file.read_text().split('#enroll=')[1].strip();status,data=cls.admin.post('auth-enroll',dict(token=token,username='policy-admin',password=PASSWORD));assert status==200,data
  cls.clients={};cls.accounts={}
  for actor in ('priya','sam','lee'):
   _,inv=cls.admin.post('access-invite',dict(actor=actor));client=Client(cls.server);status,data=client.post('auth-enroll',dict(token=inv['token'],username='named-'+actor,password=PASSWORD));assert status==200,data;cls.clients[actor]=client;cls.accounts[actor]=data['account']
  cls.other=cls.server.projects.create(dict(title='Other private project'),'priya')['project_id']
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
 def policy(self):
  data=self.admin.get('/api/decision-rights?project=original')[1];rule=dict(decider='priya',reviewers=['sam'],delegates=['lee'],escalation_path=['sam'])
  body=dict(expected=data['ref'],rules={k:deepcopy(rule) for k in data['kinds']},reason='Explicit named project rights')
  code,result=self.admin.post('decision-rights-save',body);self.assertEqual(code,200,result);return body,result
 def issue(self):
  import uuid
  payload=dict(title='Synthetic authority '+uuid.uuid4().hex[:6],question='Who can close this coordination issue?',consequence='Keep the exact authority',kind='question',boards=['research-design'],owner='sam',route='coordination',packet_refs=[self.packet],requirement_refs=[self.target])
  code,result=self.clients['priya'].post('bridge-raise',payload);self.assertEqual(code,200,result)
  return next(i for i in self.clients['priya'].get('/api/state')[1]['bridge']['issues'] if i['ref']['id']==result['id'])
 def latest(self,i):return next(r for r in self.clients['priya'].get('/api/state')[1]['bridge']['issues'] if r['ref']['id']==i['ref']['id'])
 def test_admin_can_configure_shared_policy_without_private_project_membership(self):
  body,result=self.policy();self.assertFalse(self.server.access.allowed(self.server.access.account(self.accounts['priya']['id']),self.other))
  status,data=self.clients['priya'].get('/api/decision-rights?project=original');self.assertEqual(status,200);self.assertFalse(data['can_edit']);self.assertEqual({p['name'] for p in data['members']},{'named-priya','named-sam','named-lee'})
  self.assertEqual(self.admin.get('/api/state')[0],403)
  self.assertEqual(self.clients['priya'].get('/api/decision-rights?project='+self.other)[0],403)
  self.assertEqual(self.clients['priya'].post('decision-rights-save',{**body,'expected':result['ref'],'admin':True,'actor':'administrator'})[0],403)
 def test_save_checks_csrf_membership_generation_and_exact_policy_version(self):
  body,result=self.policy()
  self.assertEqual(self.admin.request('POST','/api/decision-rights-save',{**body,'expected':result['ref']},{'X-CSRF-Token':''})[0],403)
  self.assertEqual(self.admin.post('decision-rights-save',body)[0],409)
  body['expected']=result['ref'];body['rules']['requirement']['decider']='alex';self.assertEqual(self.admin.post('decision-rights-save',body)[0],403)
  body['rules']['requirement']['decider']='priya';self.admin.version=999
  try:self.assertEqual(self.admin.post('decision-rights-save',body)[0],409)
  finally:self.admin.version=1
 def test_delegate_cannot_self_activate_or_bypass_required_reviews(self):
  self.policy();i=self.issue();payload=dict(expected=i['ref'],action='delegate',delegate='lee',reason='An explicit handoff')
  self.assertEqual(self.clients['lee'].post('decision-rights-action',{**payload,'actor':'priya'})[0],403)
  self.assertEqual(self.clients['priya'].post('decision-rights-action',payload)[0],200)
  i=self.latest(i);self.assertEqual(i['rights']['active_decider'],'lee')
  self.assertEqual(self.clients['lee'].post('bridge-close',dict(expected=i['ref'],rationale='Missing review',confirm=True))[0],409)
  self.assertEqual(self.clients['sam'].post('decision-rights-action',dict(expected=i['ref'],action='review',disposition='supported-with-limits',reason='Checked the shared context'))[0],200)
  i=self.latest(i);self.assertEqual(self.clients['lee'].post('bridge-close',dict(expected=i['ref'],rationale='Reviewed closure',confirm=True))[0],200)
  i=self.latest(i);self.assertEqual(i['body']['resolution']['actor'],'lee')
  receipt=i['decision_receipt'];self.assertTrue(receipt['available']);self.assertEqual(receipt['decider']['name'],'named-lee');self.assertEqual(receipt['authority']['principal'],self.accounts['lee']['id']);self.assertIsNone(receipt['approved'])
  store=Store(self.server.path)
  try:
   decision=store.read(__import__('workbench.core',fromlist=['Ref']).Ref(**i['body']['resolution']['decision']),{SCOPE})
   self.assertEqual(decision['body']['authority']['principal'],self.accounts['lee']['id']);self.assertEqual(decision['body']['authority']['authorized_as'],'delegate')
  finally:store.close()
 def test_membership_revocation_blocks_an_activated_delegate(self):
  self.policy();i=self.issue();self.assertEqual(self.clients['priya'].post('decision-rights-action',dict(expected=i['ref'],action='delegate',delegate='lee',reason='Explicit test delegation'))[0],200);i=self.latest(i)
  self.assertEqual(self.admin.post('access-revoke',dict(account=self.accounts['lee']['id']))[0],200)
  try:
   self.assertEqual(self.clients['lee'].post('bridge-close',dict(expected=i['ref'],rationale='Revoked queued decision',confirm=True))[0],403)
   self.assertTrue(self.latest(i)['rights']['blockers'])
   self.assertNotIn('lee',{p['actor'] for p in self.clients['priya'].get('/api/decision-rights?project=original')[1]['members']})
  finally:self.assertEqual(self.admin.post('access-invite',dict(actor='lee'))[0],200)

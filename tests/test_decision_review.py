"""Synthetic private decision assistance, exact evidence and authority boundaries."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest
from workbench.workspace import Workspace
from workbench.core import StaleBasis
from workbench.decisions import SCOPE
from workbench.model_provider import ModelUnavailable
from workbench.integrity_example import Fixture

class Model:
 def __init__(self):self.calls=[];self.reply='Ask for execution-time coverage evidence before deciding.';self.bad=False;self.fail=False;self.mutate=None
 def status(self):return dict(configured=True,provider='test',model='synthetic')
 def generate(self,**kw):
  self.calls.append(kw)
  if self.mutate:self.mutate()
  if self.fail:raise ModelUnavailable('Synthetic failure')
  cites=list(kw['context']['citation_catalog'])[:1]
  return dict(output=dict(reply=self.reply,citations=['made-up'] if self.bad else cites),model='synthetic',response_id='synthetic-response',usage=dict(total_tokens=12))

class DecisionReviewTests(unittest.TestCase):
 def setUp(self):
  self.f=Fixture();self.addCleanup(self.f.store.close);self.model=Model()
  self.assessment=self.f.assessment(associations=[self.f.association()])['ref'];self.i=self.f.issue(self.assessment)
  self.w=Workspace(self.f.store,'alex',self.model);self.review=self.w.decision_review
 def request(self,**extra):
  read=self.review.read(dict(expected=asdict(self.f.current(self.i)['ref'])))
  return dict(expected=read['issue'],thread=read['thread'],question='What evidence is missing?',consent=True,request_id='request-test-001',**extra)
 def test_read_is_private_and_does_not_invoke_model_or_change_issue(self):
  before=self.f.current(self.i);r=self.review.read(dict(expected=asdict(before['ref'])))
  self.assertTrue(r['private']);self.assertEqual(r['messages'],[]);self.assertEqual(self.model.calls,[])
  self.assertEqual(self.f.current(self.i),before)
 def test_live_path_persists_trace_without_recording_approval_or_changing_shared_data(self):
  before=self.f.current(self.i);req=self.request();self.review.send(req)
  reopened=Workspace(self.f.store,'alex',self.model).decision_review.read(dict(expected=req['expected']))
  self.assertEqual(reopened['messages'][0]['status'],'complete');self.assertEqual(reopened['messages'][0]['mode'],'simulated');self.assertFalse(reopened['messages'][0]['stale'])
  call=self.model.calls[0];self.assertIn('not merely agree',call['instructions']);self.assertIn('formal_review',call['context']);self.assertTrue(call['context']['formal_review']['history']==[])
  self.assertEqual(self.f.current(self.i),before);self.assertIsNone(self.w.integrity.decision_view(before)['ratification'])
  self.assertFalse(any(r['kind']=='decision-integrity-chat' for r in self.w.latest_records()))
  receipts=self.f.store.db.execute("SELECT scope,body FROM records WHERE kind='agent-execution'").fetchall()
  self.assertTrue(any(row['scope']==self.review.scope and json.loads(row['body'])['status']=='succeeded' for row in receipts))
 def test_other_humans_and_accounts_do_not_read_each_others_chat(self):
  self.review.send(self.request())
  for w in (Workspace(self.f.store,'sam',self.model),Workspace(self.f.store,'alex',self.model,principal_id='different-account')):
   self.assertEqual(w.decision_review.read(dict(expected=asdict(self.f.current(self.i)['ref'])))['messages'],[])
  # Maya is not a decider or required reviewer for this issue.
  with self.assertRaises(PermissionError):Workspace(self.f.store,'maya',self.model).decision_review.read(dict(expected=asdict(self.f.current(self.i)['ref'])))
 def test_retries_and_concurrency_cannot_duplicate_a_model_call(self):
  req=self.request();self.review.send(req);self.review.send(req);self.assertEqual(len(self.model.calls),1)
  bad={**req,'question':'Different payload'}
  with self.assertRaises(ValueError):self.review.send(bad)
  with self.assertRaises(StaleBasis):self.review.send({**req,'request_id':'request-test-002'})
 def test_fabricated_citation_and_failures_remain_failed_without_canned_advice(self):
  self.model.bad=True;req=self.request()
  with self.assertRaises(ValueError):self.review.send(req)
  r=self.review.read(dict(expected=req['expected']));self.assertEqual(r['messages'][0]['status'],'failed');self.assertNotIn(self.model.reply,r['messages'][0]['reply'])
  self.model.bad=False;self.model.fail=True
  with self.assertRaises(ModelUnavailable):self.review.send({**self.request(),'request_id':'request-test-002'})
  self.assertEqual(self.f.current(self.i)['body']['status'],'awaiting-decision')
 def test_current_disposition_receipt_is_included_as_json_with_exact_history(self):
  current=self.f.current(self.i);v=self.w.integrity.decision_view(current);finding=next(f for f in v['findings'] if f['material'])
  self.w.integrity.dispose(dict(expected=asdict(current['ref']),finding=finding['key'],disposition='investigate-and-defer',rationale='Need coverage evidence before deciding.'))
  self.review.send(self.request());ctx=self.model.calls[0]['context']
  disposed=next(f for f in ctx['formal_review']['findings'] if f.get('disposition'))
  self.assertIn('Need coverage',disposed['disposition']['body']['rationale']);self.assertIsInstance(disposed['disposition']['ref'],dict)
 def test_old_reply_remains_historical_when_current_requirement_changes(self):
  req=self.request();self.review.send(req)
  r=self.f.store.latest('QUALIFICATION',{SCOPE});b=deepcopy(r['body']);b['text']='Updated governing text'
  self.f.store.put(r['ref'].id,r['kind'],SCOPE,b,r['ref'].revision)
  # The attached assessment itself becomes stale and the private reply is flagged.
  view=self.review.read(dict(expected=req['expected']))
  self.assertTrue(view['messages'][0]['stale']);self.assertIn('execution-time',view['messages'][0]['reply'])
  self.review.send({**self.request(),'request_id':'request-current-002'})
  ctx=self.model.calls[-1]['context'];self.assertEqual(ctx['current_governing_requirements'][0]['body']['text'],'Updated governing text')
  self.assertIn('execution',ctx['formal_review']['assessed_inputs']['current_governing_requirements'][0]['body']['text'])
 def test_consent_is_required_and_source_instructions_do_not_become_authority(self):
  with self.assertRaises(ValueError):self.review.send({**self.request(),'consent':False})
  self.review.send(self.request());self.assertIn('untrusted data',self.model.calls[0]['instructions']);self.assertIn('no tools',self.model.calls[0]['instructions'].lower())

 def test_interrupted_request_requires_explicit_delayed_recovery(self):
  from datetime import datetime,timezone,timedelta
  req=self.request();issue,_,_=self.review.issue(req['expected']);tid='DECISION-CHAT-'+__import__('workbench.decisions',fromlist=['fingerprint']).fingerprint([self.review.owner,issue['ref'].id])[:24]
  body=dict(owner=self.review.owner,issue_id=self.i,messages=[dict(request_id='old-request-001',question='Old question',reply='',status='pending',basis_fingerprint='old',at=datetime.now(timezone.utc).isoformat(),citations=[],catalog={})])
  r=self.f.store.put(tid,'decision-integrity-chat',self.review.scope,body)
  with self.assertRaises(ValueError):self.review.recover(dict(expected=req['expected']))
  body['messages'][0]['at']=(datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat();self.f.store.put(tid,'decision-integrity-chat',self.review.scope,body,r.revision)
  self.review.recover(dict(expected=req['expected']));view=self.review.read(dict(expected=req['expected']));self.assertEqual(view['messages'][0]['status'],'failed');self.assertEqual(self.model.calls,[])


if __name__=="__main__":unittest.main()

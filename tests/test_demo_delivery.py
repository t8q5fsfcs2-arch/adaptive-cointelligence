from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from workbench.core import Store, StaleBasis
from workbench.decisions import SCOPE, DecisionBlocked
from workbench.clinic_demo import populate, NoEvaluation
from workbench.workspace import Workspace

class DemoDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'demo.db';self.s=Store(self.path);self.sample=populate(self.s);self.w=Workspace(self.s,'alex',NoEvaluation())
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def issue(self):return self.s.latest(self.sample['issue']['id'],{SCOPE})
    def prepare(self,target='jira',w=None):return (w or self.w).command('demo-delivery-prepare',dict(issue=asdict(self.issue()['ref']),target=target))
    def preview(self,target='jira'):
        out=self.prepare(target);return self.s.latest(out['demoDeliveryPreview'],{SCOPE})
    def commit(self,p,w=None):return (w or self.w).command('demo-delivery-commit',dict(expected=asdict(p['ref']),confirm_demo=True))
    def test_approved_change_updates_sample_jira_and_ado_without_network_or_governing_edits(self):
        requirement=self.s.latest(self.sample['requirement_after']['id'],{SCOPE});decision=self.s.latest(requirement['body']['decision_id'],{SCOPE})
        with patch('urllib.request.urlopen',side_effect=AssertionError('No external call is allowed in a demo')):
            for target,method in [('jira','PUT'),('ado','PATCH')]:
                p=self.preview(target);b=p['body'];self.assertEqual(b['operation'],'update');self.assertEqual(b['request']['method'],method)
                self.assertIn('confirm attendance',b['before']['text']);self.assertIn('hand the request to staff',b['after']['text']);self.assertEqual(b['after']['acceptance_criteria'],requirement['body']['acceptance_criteria'])
                result=self.commit(p);r=self.s.latest(result['demoDeliveryReceipt'],{SCOPE});self.assertFalse(r['body']['external_request_sent']);self.assertEqual(r['body']['mode'],'simulated');self.assertEqual(r['body']['decision'],asdict(decision['ref']))
                self.assertEqual(r['body']['item_snapshot']['source'],asdict(requirement['ref']));self.assertTrue(r['body']['item_snapshot']['key'].startswith('DEMO-'))
        self.assertEqual(self.s.latest(requirement['ref'].id,{SCOPE}),requirement);self.assertFalse(self.w.delivery.state()['connected']);self.assertFalse(self.w.demo_delivery.state()['connected'])
    def test_exact_preview_is_idempotent_and_receipt_reopens_after_restart(self):
        p=self.preview();self.assertEqual(self.prepare()['demoDeliveryPreview'],p['ref'].id);first=self.commit(p);again=self.commit(p);self.assertEqual(first['demoDeliveryReceipt'],again['demoDeliveryReceipt'])
        self.assertEqual(len(self.w.demo_delivery.state()['receipts']),1);self.assertEqual(self.prepare()['demoDeliveryPreview'],p['ref'].id)
        self.s.close();self.s=Store(self.path);w=Workspace(self.s,'sam',NoEvaluation());state=w.demo_delivery.state();self.assertEqual(len(state['receipts']),1);self.assertFalse(state['issues'][0]['can_prepare'])
        self.assertTrue(any(u['source_kind']=='demo-delivery-receipt' and u['target']['kind']=='demo-delivery' for u in w.domain_updates.state()))
    def test_authority_and_explicit_demo_confirmation_cannot_be_spoofed(self):
        p=self.preview()
        for actor in ['sam','lee','priya']:
            w=Workspace(self.s,actor,NoEvaluation())
            with self.assertRaises(PermissionError):self.prepare(w=w)
            with self.assertRaises(PermissionError):self.commit(p,w=w)
        with self.assertRaises(ValueError):self.w.command('demo-delivery-commit',dict(expected=asdict(p['ref']),confirm_demo=False,actor='alex'))
        self.assertFalse(self.w.demo_delivery.state()['receipts'])
    def test_changed_requirement_or_reopened_issue_blocks_update(self):
        p=self.preview();req=self.s.latest(self.sample['requirement_after']['id'],{SCOPE});self.s.put(req['ref'].id,req['kind'],SCOPE,{**req['body'],'text':'Changed after approval'},req['ref'].revision)
        with self.assertRaises(StaleBasis):self.commit(p)
        self.assertFalse(self.w.demo_delivery.state()['previews'][0]['current']);self.assertFalse(self.w.demo_delivery.state()['receipts'])
    def test_changed_business_context_invalidates_an_existing_approval(self):
        p=self.preview();intent=self.s.latest('INT-001',{SCOPE});self.s.put('INT-001','intent',SCOPE,{**intent['body'],'text':'A changed business direction'},intent['ref'].revision)
        with self.assertRaises(StaleBasis):self.commit(p)
        self.assertFalse(self.w.demo_delivery.state()['receipts'])

    def test_new_governing_challenge_blocks_a_pending_demo_update(self):
        p=self.preview();req=self.sample['requirement_after'];sam=Workspace(self.s,'sam',NoEvaluation())
        sam.command('bridge-raise',dict(title='Reconsider closure evidence',question='Does closure need another check?',consequence='Unresolved requirement concern.',kind='challenge',boards=['research-design'],owner='sam',route='requirement',target=req,requirement_refs=[req],packet_refs=[self.sample['packets']['result']]))
        with self.assertRaises(DecisionBlocked):self.commit(p)
        self.assertFalse(self.w.demo_delivery.state()['receipts'])

    def test_unapproved_issue_does_not_get_demo_delivery_rights(self):
        i=self.issue();b={**i['body'],'status':'investigating'};self.s.put(i['ref'].id,i['kind'],SCOPE,b,i['ref'].revision)
        with self.assertRaises(DecisionBlocked):self.prepare()
    def test_new_approval_updates_same_sample_item_and_retains_first_receipt(self):
        p=self.preview();first=self.commit(p);old=self.s.latest(first['demoDeliveryReceipt'],{SCOPE});req=self.s.latest(self.sample['requirement_after']['id'],{SCOPE})
        # Fixture a second explicitly recorded decision, preserving the normal result/decision contract.
        old_decision=self.s.latest(req['body']['decision_id'],{SCOPE});next_id='DEC-FICTIONAL-LATER';next_ref=self.s.put(req['ref'].id,'requirement',SCOPE,{**req['body'],'text':req['body']['text']+' Provide an accessible pending indicator.','supersedes':asdict(req['ref']),'decision_id':next_id},req['ref'].revision)
        new_decision=self.s.put(next_id,'decision',SCOPE,{**old_decision['body'],'result_requirement':asdict(next_ref)})
        i=self.issue();b=i['body'];b['resolution']={**b['resolution'],'decision':asdict(new_decision),'requirement':asdict(next_ref)};self.s.put(i['ref'].id,i['kind'],SCOPE,b,i['ref'].revision)
        second=self.commit(self.preview());latest=self.s.latest(second['demoDeliveryReceipt'],{SCOPE});self.assertEqual(old['body']['item']['id'],latest['body']['item']['id']);self.assertEqual(latest['body']['item_snapshot']['revision'],3)
        self.assertEqual(self.s.read(old['ref'],{SCOPE})['body']['item_snapshot']['source'],asdict(req['ref']))

class DemoDeliveryWebTests(unittest.TestCase):
    def test_real_http_routes_and_saved_receipt_are_separate_from_a_live_connector(self):
        import test_web
        h=test_web.WebTests();h.setUp()
        try:
            s=Store(h.server.path)
            try:sample=populate(s)
            finally:s.close()
            self.assertEqual(h.post('profile',dict(actor='alex'))[0],200)
            code,out=h.post('demo-delivery-prepare',dict(issue=sample['issue'],target='ado'));self.assertEqual(code,200,out)
            s=Store(h.server.path)
            try:p=s.latest(out['demoDeliveryPreview'],{SCOPE})
            finally:s.close()
            code,out=h.post('demo-delivery-commit',dict(expected=asdict(p['ref']),confirm_demo=True));self.assertEqual(code,200,out)
            h.conn.request('GET','/api/state',headers={'Cookie':h.cookie});response=h.conn.getresponse();state=json.loads(response.read());self.assertEqual(response.status,200)
            self.assertEqual(state['demo_delivery']['receipts'][0]['body']['mode'],'simulated');self.assertFalse(state['delivery']['connected'])
            self.assertEqual(h.post('profile',dict(actor='lee'))[0],200);self.assertEqual(h.post('demo-delivery-commit',dict(expected=asdict(p['ref']),confirm_demo=True))[0],403)
            h.conn.request('GET','/demo-delivery.js');response=h.conn.getresponse();self.assertEqual(response.status,200);self.assertIn(b'Simulate',response.read())
        finally:h.tearDown()

if __name__=='__main__':unittest.main()

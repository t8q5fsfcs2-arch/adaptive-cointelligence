"""Delivery observations are scoped to one exact approval and shared visibility."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch
from workbench.core import Ref
from workbench.decisions import SCOPE
from workbench.decision_receipts import DecisionReceipts
from workbench.workspace import Workspace
import test_demo_delivery as fixtures

class ReceiptDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.DemoDeliveryTests();self.f.setUp();self.s=self.f.s;self.w=self.f.w
    def tearDown(self):self.f.tearDown()
    def receipt(self,issue=None):return DecisionReceipts(self.s).for_issue(issue or self.f.issue())
    def target(self,r,target):return next(t for t in r['delivery']['targets'] if t['target']==target)
    def stage(self,target='jira',actor='alex'):
        return Workspace(self.s,actor,fixtures.NoEvaluation()).command('delivery-prepare',dict(target=target,work_item_type='Story' if target=='jira' else 'User Story',destination='SYNTHETIC',requirements=[self.f.sample['requirement_after']]))
    def test_approval_alone_is_never_a_delivery_or_external_story(self):
        before=self.s.db.total_changes;r=self.receipt();d=r['delivery']
        self.assertTrue(d['applicable']);self.assertEqual(d['external_status'],'not-confirmed');self.assertFalse(d['connected']);self.assertIsNone(d['external_story_url']);self.assertEqual({t['status'] for t in d['targets']},{'not-staged'});self.assertEqual(before,self.s.db.total_changes)
    def test_shared_stage_is_visible_but_private_sponsor_preview_is_not(self):
        private=self.stage('ado','priya');shared=self.stage('jira');r=self.receipt()
        self.assertEqual(self.target(r,'jira')['status'],'staged');self.assertEqual(self.target(r,'ado')['status'],'not-staged')
        raw=json.dumps(r['delivery']);self.assertIn(shared['id'],raw);self.assertNotIn(private['id'],raw);self.assertEqual(r['delivery']['external_status'],'not-confirmed')
        view=next(i for i in Workspace(self.s,'lee',fixtures.NoEvaluation()).state()['bridge']['issues'] if i['ref'].id==self.f.issue()['ref'].id);self.assertEqual(view['decision_receipt']['delivery'],r['delivery'])
    def test_prepare_export_and_demo_simulation_remain_distinct_for_each_tool(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('Receipt must not call an external system')):
            for target in ('jira','ado'):
                p=self.f.preview(target);r=self.receipt();self.assertEqual(self.target(r,target)['status'],'staged');self.assertFalse(self.target(r,target)['stories'])
                result=self.f.commit(p);r=self.receipt();tool=self.target(r,target)
                self.assertEqual(tool['status'],'simulated');self.assertEqual(tool['stories'][0]['receipt']['id'],result['demoDeliveryReceipt']);self.assertFalse(tool['stories'][0]['external_request_sent']);self.assertEqual(tool['stories'][0]['mode'],'simulated');self.assertEqual(r['delivery']['external_status'],'not-confirmed');self.assertIsNone(r['delivery']['external_story_url'])
    def test_local_export_does_not_become_an_external_send(self):
        shared=self.stage();r=self.s.latest(shared['id'],{SCOPE});self.w.command('delivery-export',dict(expected=asdict(r['ref'])));self.assertEqual(self.target(self.receipt(),'jira')['status'],'staged');self.assertEqual(self.receipt()['delivery']['external_status'],'not-confirmed')
    def test_a_claimed_live_flag_or_url_cannot_promote_a_demo_or_draft(self):
        p=self.f.preview();out=self.f.commit(p);r=self.s.latest(out['demoDeliveryReceipt'],{SCOPE});bad={**r['body'],'external_request_sent':True,'external_url':'https://example.invalid/story/123'}
        self.s.put(r['ref'].id,r['kind'],SCOPE,bad,r['ref'].revision)
        draft=self.s.latest(next(t['ref']['id'] for t in self.target(self.receipt(),'jira')['transactions'] if t['kind']=='delivery-draft'),{SCOPE})
        self.s.put(draft['ref'].id,draft['kind'],SCOPE,{**draft['body'],'external_receipts':[{'url':'https://example.invalid/story/123','status':'sent'}]},draft['ref'].revision)
        delivery=self.receipt()['delivery'];self.assertEqual(delivery['external_status'],'not-confirmed');self.assertIsNone(delivery['external_story_url']);self.assertFalse(next(t for t in delivery['targets'] if t['target']=='jira')['stories']);self.assertIn('could not be verified',delivery['warning']);self.assertNotIn('example.invalid',json.dumps(delivery))
    def test_result_requires_matching_preview_item_and_exact_requirement(self):
        p=self.f.preview();out=self.f.commit(p);r=self.s.latest(out['demoDeliveryReceipt'],{SCOPE});wrong={**r['body'],'item_snapshot':{**r['body']['item_snapshot'],'source':{'id':'OTHER-REQUIREMENT','revision':1}}};self.s.put(r['ref'].id,r['kind'],SCOPE,wrong,r['ref'].revision)
        d=self.receipt()['delivery'];self.assertFalse(next(t for t in d['targets'] if t['target']=='jira')['stories']);self.assertEqual(d['external_status'],'not-confirmed')
    def test_later_approval_and_other_issue_receipts_cannot_be_misattributed(self):
        old_issue=deepcopy(self.f.issue());first=self.f.commit(self.f.preview());old=self.receipt(old_issue)
        # Reuse the existing later-approval fixture, which versions the same sample item.
        req=self.s.latest(self.f.sample['requirement_after']['id'],{SCOPE});decision=self.s.latest(req['body']['decision_id'],{SCOPE});new_id='DEC-NEW-EXACT'
        new_req=self.s.put(req['ref'].id,'requirement',SCOPE,{**req['body'],'text':req['body']['text']+' A later condition.','decision_id':new_id,'supersedes':asdict(req['ref'])},req['ref'].revision)
        new_decision=self.s.put(new_id,'decision',SCOPE,{**decision['body'],'result_requirement':asdict(new_req)})
        current=self.f.issue();body=deepcopy(current['body']);body['resolution'].update(decision=asdict(new_decision),requirement=asdict(new_req));self.s.put(current['ref'].id,current['kind'],SCOPE,body,current['ref'].revision)
        self.f.commit(self.f.preview());self.assertEqual(self.receipt(old_issue),old)
        other=deepcopy(old_issue);other['ref']=Ref('ANOTHER-ISSUE',1);self.assertFalse(self.target(self.receipt(other),'jira')['stories'])
    def test_no_change_receipt_never_inherits_another_requirement_delivery(self):
        self.f.commit(self.f.preview());fake=deepcopy(self.f.issue());closed=self.s.put('BDEC-NO-CHANGE','bridge-issue-decision',SCOPE,dict(issue=asdict(fake['ref']),actor='alex',at='2026-11-11T12:00:00Z',rationale='Keep current scope',disposition='no-governing-change',basis=[]));fake['body']['resolution']['decision']=asdict(closed)
        d=self.receipt(fake)['delivery'];self.assertFalse(d['applicable']);self.assertFalse(d['targets']);self.assertIsNone(d['external_story_url'])

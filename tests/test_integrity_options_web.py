"""Actual HTTP path, with an explicitly scripted provider and synthetic records."""
from dataclasses import asdict
import json
import unittest

import test_web
from workbench.integrity_example import Fixture
from workbench.integrity_options_example import SimulatedOptionsModel
from workbench.core import Ref
from workbench.decisions import SCOPE


class IntegrityOptionsHTTPTests(unittest.TestCase):
    def setUp(self):
        self.h=test_web.WebTests();self.h.setUp();self.addCleanup(self.h.tearDown)
        self.model=SimulatedOptionsModel();self.h.server.model=self.model
        self.f=Fixture(self.h.server.path);self.addCleanup(self.f.store.close)
        self.h.post('profile',dict(actor='alex'))

    def state(self):
        self.h.conn.request('GET','/api/state',headers={'Cookie':self.h.cookie})
        response=self.h.conn.getresponse();self.assertEqual(response.status,200)
        return json.loads(response.read())

    def test_http_preflight_stops_old_current_evidence_and_reuses_explicit_history(self):
        source=self.f.store.read(Ref('SOURCE-sam',1),{SCOPE})
        self.f.store.put(source['ref'].id,source['kind'],source['scope'],{**source['body'],'text':'New synthetic observation.'},1)
        data=dict(packets=[self.f.a['packet']],evaluation_scope='within-domain',mode='advisory',semantic=True,consent=True)
        status,preview=self.h.post('integrity-preflight',data)
        self.assertEqual(status,200,preview);self.assertFalse(preview['current_use_eligible'])
        status,error=self.h.post('integrity-assess',data)
        self.assertNotEqual(status,200);self.assertIn('superseded',error['error']);self.assertEqual(self.model.calls,0)
        data.update(review_purpose='historical',historical_reason='Retain original evidence for a bounded comparison.')
        status,review=self.h.post('integrity-assess',data);self.assertEqual(status,200,review)
        count=self.model.calls;status,cached=self.h.post('integrity-assess',data)
        self.assertEqual(status,200,cached);self.assertTrue(cached['cached']);self.assertEqual(self.model.calls,count)
        status,saved=self.h.post('integrity-review-read',dict(assessment=review['ref']))
        self.assertEqual(status,200,saved);self.assertEqual(saved['review_basis_now']['purpose'],'historical')
        self.assertFalse(saved['review_basis_now']['current_use_eligible']);self.assertTrue(saved['stale'])
        self.assertTrue(all(p['interpretation']['state']=='settled' for f in saved['decision_trace']['packet_findings'] for p in f['parts']))
        self.assertEqual(self.h.post('integrity-approve-domain',dict(assessment=review['ref'],disposition='approved',rationale='Synthetic request.'))[0],409)

    def test_assessment_and_option_response_follow_actual_routes_with_guards(self):
        packets=[self.f.a['packet'],self.f.b['packet']]
        status,proposal=self.h.post('integrity-proposal',dict(packets=packets,text='Inspect coverage before selecting a control change.',rationale='Preserve the approved requirement.'))
        self.assertEqual(status,200,proposal)
        payload=dict(proposal=proposal['ref'],packets=packets,associations=[self.f.association()],evaluation_scope='cross-domain',mode='formal',confirm=True,semantic=True,consent=True)
        status,a=self.h.post('integrity-assess',payload);self.assertEqual(status,200,a)
        self.assertEqual(self.model.calls,3)
        status,cached=self.h.post('integrity-assess',payload);self.assertEqual(status,200,cached)
        self.assertTrue(cached['cached']);self.assertEqual(self.model.calls,3)
        issue=self.f.issue(a['ref']);expected=asdict(self.f.current(issue)['ref'])
        response=dict(expected=expected,option='C',disposition='modify',rationale='Bound the request.',proposed_correction='Inspect restart coverage as well as the initial start.')
        self.assertEqual(self.h.post('integrity-option-response',response,{'X-CSRF-Token':''})[0],403)
        self.h.post('profile',dict(actor='sam'))
        self.assertEqual(self.h.post('integrity-option-response',response)[0],403)
        self.h.post('profile',dict(actor='alex'))
        code,saved=self.h.post('integrity-option-response',response);self.assertEqual(code,200,saved)
        state=self.state();view=next(i for i in state['bridge']['issues'] if i['ref']['id']==issue)['integrity']
        self.assertEqual(view['option_responses']['C']['proposed_correction'],response['proposed_correction'])
        self.assertEqual(view['execution_receipt']['mode'],'simulated')
        self.assertEqual(view['decision_trace']['recommendation']['preferred_option'],'C')
        self.assertEqual(self.model.calls,3);self.assertIsNone(view['ratification'])
        self.assertNotEqual(self.h.post('integrity-option-response',response)[0],200)

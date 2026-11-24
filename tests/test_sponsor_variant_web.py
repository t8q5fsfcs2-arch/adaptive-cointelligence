import json
import unittest
import test_web

class SponsorVariantWebTests(unittest.TestCase):
    def setUp(self):self.h=test_web.WebTests();self.h.setUp()
    def tearDown(self):self.h.tearDown()
    def state(self):
        self.h.conn.request('GET','/api/state',headers={'Cookie':self.h.cookie});r=self.h.conn.getresponse();self.assertEqual(r.status,200);return json.loads(r.read())
    def test_sponsor_answers_are_saved_by_the_http_adapter_and_hidden_from_domains(self):
        self.assertEqual(self.h.post('profile',dict(actor='priya'))[0],200)
        self.assertEqual(self.h.post('intake-start',dict(title='Fictional HTTP sponsor'))[0],200)
        state=self.state();code,result=self.h.post('sponsor-save',dict(expected=state['intake']['draft']['ref'],answers={'q10':dict(items=['Keep a stored report reference'],confirmed=True)}))
        self.assertEqual(code,200);self.assertEqual(self.state()['sponsor']['brief']['answers']['q10']['items'],['Keep a stored report reference'])
        self.assertEqual(self.h.post('sponsor-save',dict(expected=state['intake']['draft']['ref'],answers={}))[0],409)
        self.assertEqual(self.h.post('profile',dict(actor='lee'))[0],200);self.assertIsNone(self.state()['sponsor'])
        self.assertEqual(self.h.post('sponsor-save',dict(expected=result['ref'],answers={}))[0],403)
    def test_branch_assets_are_served_and_delivery_cannot_claim_a_send(self):
        for path,content in [('/sponsor.js',b'sponsorScreen'),('/sponsor.css',b'sponsor-surface'),('/delivery.js',b'connector not configured'),('/workspace.css',b'--ac-accent:'),('/inter-latin.woff2',b'wOF2')]:
            self.h.conn.request('GET',path);r=self.h.conn.getresponse();self.assertEqual(r.status,200);self.assertIn(content,r.read())
        self.assertEqual(self.h.post('delivery-send',dict(target='jira'))[0],400)
        self.assertFalse(self.state()['delivery']['connected'])

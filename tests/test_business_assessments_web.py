"""Local HTTP assessment routing with synthetic scripted outputs, never a provider."""
import json
from pathlib import Path
import sqlite3
import unittest

import test_web
from test_intake import VALUE
from test_business_assessments import TwoPassModel


class ReadOnlyTestStore:
    def __init__(self, path): self.path = Path(path)
    def read(self, ref, scopes):
        with sqlite3.connect(self.path.as_uri()+'?mode=ro', uri=True) as db:
            row = db.execute('SELECT kind,scope FROM records WHERE id=? AND revision=?', (ref.id,ref.revision)).fetchone()
            assert row and row[1] in scopes
            return dict(kind=row[0])


class BusinessAssessmentHTTPTests(unittest.TestCase):
    def setUp(self):
        self.h = test_web.WebTests(); self.h.setUp(); self.addCleanup(self.h.tearDown)
        self.model = TwoPassModel(); self.model.store = ReadOnlyTestStore(self.h.server.path)
        self.h.server.model = self.model
        self.assertEqual(self.h.post('profile', dict(actor='priya'))[0], 200)
        self.assertEqual(self.h.post('intake-start', dict(title='Synthetic HTTP argument'))[0], 200)
        self.assertEqual(self.h.post('intake-save', dict(expected=self.state()['intake']['draft']['ref'], step='value', **VALUE))[0], 200)
        status, result = self.h.post('intake-source', dict(title='Selected synthetic account',
            text='One person reported losing their place after requesting help. Recurrence and population effects are unknown.',role='evidence'))
        self.assertEqual(status, 200); self.source = result['ref']

    def state(self):
        self.h.conn.request('GET', '/api/state', headers={'Cookie':self.h.cookie})
        response = self.h.conn.getresponse(); self.assertEqual(response.status, 200)
        return json.loads(response.read())

    def payload(self):
        return dict(expected=self.state()['intake']['draft']['ref'], skill='assess-business', field='value',
            message='Assess the saved synthetic argument and evidence.',sources=[self.source],consent=True)

    def test_native_post_executes_two_scripted_phases_and_get_does_not_grade_or_publish(self):
        before = self.state()['intake']['draft']['ref']
        status, result = self.h.post('intake-coach', self.payload())
        self.assertEqual(status, 200, result); self.assertEqual(len(self.model.calls), 2)
        state = self.state(); assessment = state['coaching']['business_assessments']['current']
        self.assertEqual(assessment['ref'], result['ref'])
        self.assertEqual(assessment['body']['assessor_type'], 'model'); self.assertEqual(assessment['body']['mode'], 'simulated')
        self.assertEqual(state['intake']['draft']['ref'], before); self.assertIsNone(state['intake']['published'])
        self.state(); self.assertEqual(len(self.model.calls), 2)
        self.assertEqual(self.h.post('profile', dict(actor='sam'))[0], 200)
        self.assertNotIn('business_assessments', self.state()['coaching'])

    def test_transport_consent_and_stale_project_guards_run_before_model(self):
        payload = self.payload()
        for headers in [{'X-CSRF-Token':''},{'Origin':'https://unrelated.example'}, {'X-Workbench-Version':'999999'}]:
            status, _ = self.h.post('intake-coach', payload, headers)
            self.assertIn(status, (403,409)); self.assertEqual(self.model.calls, [])
        payload['consent'] = False
        status, result = self.h.post('intake-coach', payload)
        self.assertEqual(status, 400, result); self.assertEqual(self.model.calls, [])


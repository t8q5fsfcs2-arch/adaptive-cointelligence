from pathlib import Path
import tempfile, unittest

from workbench.core import Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.store = Store(Path(self.temp.name) / 'db')
        Workspace(self.store, 'alex').setup(dict(title='Fictional readiness', intent='Reduce missed visits', boundary='Synthetic'))
        self.priya = Workspace(self.store, 'priya'); self.sam = Workspace(self.store, 'sam')
    def tearDown(self): self.store.close(); self.temp.cleanup()
    def decide(self, w=None, **extra):
        w = w or self.priya
        data = dict(outcome='not-yet', reason='Problem side has no evidence yet.', confirm=True, expected=w.state()['readiness']['ref']); data.update(extra)
        return w.command('readiness-decide', data)

    def test_only_the_business_direction_decider_records_readiness(self):
        self.assertFalse(self.sam.state()['readiness']['can_decide'])
        self.assertTrue(self.priya.state()['readiness']['can_decide'])
        with self.assertRaises(PermissionError): self.decide(self.sam, actor='priya')
        self.assertIsNone(self.priya.state()['readiness']['current'])

    def test_a_call_needs_an_outcome_a_reason_explicit_confirmation_and_conditions_when_conditional(self):
        for bad in (dict(outcome='go'), dict(reason='  '), dict(confirm=False), dict(outcome='ready-with-conditions', conditions='')):
            with self.assertRaises(ValueError): self.decide(**bad)
        self.assertIsNone(self.priya.state()['readiness']['ref'])

    def test_each_call_is_a_new_revision_and_keeps_its_predecessor_and_basis(self):
        self.decide()
        self.decide(outcome='ready-with-conditions', reason='Enough to start the staffed path.', conditions='Targets agreed before pilot.')
        s = self.sam.state()['readiness']
        self.assertEqual(s['ref']['revision'], 2); self.assertEqual([h['outcome'] for h in s['history']], ['ready-with-conditions', 'not-yet'])
        self.assertEqual(s['current']['conditions'], 'Targets agreed before pilot.')
        latest = self.store.latest('PROJECT-READINESS', {SCOPE})
        self.assertEqual(latest['kind'], 'readiness-decision'); self.assertEqual(latest['body']['previous'], dict(id='PROJECT-READINESS', revision=1))
        self.assertIn('requirement_levels', latest['body']['basis']); self.assertFalse(s['basis_changed'])

    def test_a_stale_view_cannot_overwrite_a_newer_call(self):
        old = self.priya.state()['readiness']['ref']; self.decide()
        with self.assertRaises(StaleBasis): self.decide(expected=old)

    def test_basis_comes_from_records_not_the_request_and_later_changes_open_reconsideration(self):
        self.decide(basis=dict(open_issues=-1), basis_fingerprint='forged')
        body = self.store.latest('PROJECT-READINESS', {SCOPE})['body']
        self.assertGreaterEqual(body['basis']['open_issues'], 0); self.assertNotEqual(body['basis_fingerprint'], 'forged')
        self.store.put('M-FICTIONAL', 'success-measure', SCOPE, dict(active=True, name='Fictional measure', text='Fictional measure', target='', goal_ids=[]))
        s = self.priya.state()['readiness']
        self.assertTrue(s['basis_changed']); self.assertEqual(s['current']['outcome'], 'not-yet')


if __name__ == '__main__': unittest.main()

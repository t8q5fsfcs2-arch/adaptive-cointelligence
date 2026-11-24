"""Synthetic sponsor preflight: private preparation, explicit release, pinned reviewers."""
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from workbench.core import Store, StaleBasis
from workbench.decisions import DecisionBlocked, SCOPE
from workbench.intake import Intake, PRIVATE
from workbench.workspace import Workspace
from test_intake import VALUE, CONTEXT


class SponsorPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'preflight.sqlite3')
        self.sponsor = Intake(self.store, 'priya')
        self.sponsor.start({'title': 'Synthetic assisted enrollment'})

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def ref(self):
        return asdict(self.sponsor.draft()['ref'])

    def complete(self):
        self.sponsor.save(dict(expected=self.ref(), step='value', **VALUE))
        self.sponsor.accept_value(dict(expected=self.ref(), confirm=True, rationale='Review hypothesis and evidence limits'))
        self.sponsor.save(dict(expected=self.ref(), step='context', **CONTEXT))
        self.sponsor.build(dict(expected=self.ref()))

    def prepare(self, **kwargs):
        result = Workspace(self.store, 'priya').command('intake-preflight', dict(expected=self.ref(),
            research_focus='Test resumption needs', design_focus='Explore a clear return path',
            open_questions='Baseline not measured', **kwargs))
        return self.sponsor.latest(result['id'])

    def share(self, package, **kwargs):
        result = self.sponsor.request(dict(expected=self.ref(), preflight=asdict(package['ref']), confirm=True, **kwargs))
        return self.sponsor.latest(result['id'])

    def test_prepare_requires_complete_current_intake_and_no_state_get_mutation(self):
        before = self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        for _ in range(2):
            state = self.sponsor.state()['preflight']
            self.assertTrue(state['blockers'])
            self.assertEqual(state['packages'], [])
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0], before)
        with self.assertRaises(DecisionBlocked): self.prepare()
        self.complete()
        self.assertEqual(self.sponsor.state()['preflight']['blockers'], [])

    def test_private_exact_snapshot_dedup_and_no_automatic_publication(self):
        self.complete()
        draft = self.sponsor.draft()
        with patch('workbench.domain.DomainAgent.run', side_effect=AssertionError('Preflight must be deterministic')):
            package = self.prepare()
            duplicate = self.prepare()
        self.assertEqual(package['ref'], duplicate['ref'])
        self.assertEqual(package['scope'], PRIVATE)
        self.assertEqual(package['body']['draft'], asdict(draft['ref']))
        self.assertEqual(package['body']['snapshot']['scaffold'], draft['body']['scaffold'])
        self.assertEqual(package['body']['reviewers'], ['sam', 'lee'])
        self.assertEqual(self.sponsor.cases(), [])
        self.assertIsNone(self.sponsor.latest('INT-001'))
        self.assertEqual(Workspace(self.store, 'priya').state()['intake']['preflight']['packages'][0]['current'], True)
        for actor in ('sam', 'lee', 'alex', 'maya'):
            workspace = Workspace(self.store, actor)
            state = workspace.state()
            self.assertIsNone(state['intake']['preflight'])
            self.assertFalse(any(r['kind'] == 'sponsor-preflight' for r in state['records']))
            with self.assertRaises(PermissionError):
                workspace.command('intake-preflight', dict(expected=self.ref()))
            with self.assertRaises(PermissionError):
                Intake(self.store, actor).checked_preflight(asdict(package['ref']))

    def test_explicit_share_pins_research_design_and_preserves_package(self):
        self.complete(); package = self.prepare()
        with self.assertRaises(ValueError):
            self.sponsor.request(dict(expected=self.ref(), preflight=asdict(package['ref'])))
        shared = self.share(package)
        self.assertEqual(shared['scope'], SCOPE)
        self.assertEqual(shared['body']['reviewers'], ['sam', 'lee'])
        self.assertEqual(shared['body']['preflight'], asdict(package['ref']))
        self.assertEqual(shared['body']['snapshot']['handoff'], package['body']['handoff'])
        self.assertEqual(self.store.read(package['ref'], {PRIVATE}), package)
        self.assertEqual(Workspace(self.store, 'lee').state()['intake']['cases'][0]['ref'], shared['ref'])
        with self.assertRaises(DecisionBlocked): self.share(package)
        with self.assertRaises(PermissionError):
            Intake(self.store, 'maya').review(dict(expected=asdict(shared['ref']), disposition='ready-for-investigation', rationale='Not assigned'))
        with self.assertRaises(DecisionBlocked):
            self.sponsor.publish(dict(expected=asdict(shared['ref']), confirm=True, rationale='No reviews yet'))
        for actor in ('sam', 'lee'):
            shared = self.sponsor.latest(shared['ref'].id)
            Intake(self.store, actor).review(dict(expected=asdict(shared['ref']), disposition='ready-for-investigation', rationale='Investigate, with limits open'))
        case = self.sponsor.latest(shared['ref'].id)
        self.assertTrue(self.sponsor.state()['cases'][0]['ready'])
        self.sponsor.publish(dict(expected=asdict(case['ref']), confirm=True, rationale='Investigation authorized'))
        self.assertIsNotNone(self.sponsor.latest('INT-001'))
        self.assertEqual(self.sponsor.latest('INT-001')['body']['fit_status'], 'hypothesis-to-test')

    def test_changed_intake_blocks_share_and_keeps_prepared_history(self):
        self.complete(); package = self.prepare()
        self.sponsor.save(dict(expected=self.ref(), step='context', in_scope='Revised scope'))
        with self.assertRaises(StaleBasis): self.share(package)
        self.assertFalse(self.sponsor.state()['preflight']['packages'][0]['current'])
        self.assertEqual(self.store.read(package['ref'], {PRIVATE}), package)
        self.assertEqual(self.sponsor.cases(), [])

    def test_changed_profile_blocks_share(self):
        self.complete(); package = self.prepare()
        p = self.sponsor.profile()
        self.store.put(p['ref'].id, p['kind'], p['scope'], p['body'], p['ref'].revision)
        with self.assertRaises((DecisionBlocked, StaleBasis)): self.share(package)
        self.assertFalse(self.sponsor.state()['preflight']['packages'][0]['current'])

    def test_new_document_blocks_share_until_assessed(self):
        self.complete(); package = self.prepare()
        with patch('workbench.document_changes.pending_sources', return_value=[dict(id='new-source')]):
            with self.assertRaises(DecisionBlocked): self.share(package)
            self.assertFalse(self.sponsor.state()['preflight']['packages'][0]['current'])
        self.assertEqual(self.sponsor.cases(), [])

    def test_changed_baseline_blocks_share(self):
        self.complete(); package = self.prepare()
        self.store.put('INT-001', 'intent', SCOPE, dict(text='New baseline', values={}))
        with self.assertRaises(StaleBasis): self.share(package)
        self.assertFalse(self.sponsor.state()['preflight']['packages'][0]['current'])

    def test_legacy_cases_retain_recorded_reviewer_authority(self):
        self.complete()
        result = self.sponsor.request(dict(expected=self.ref(), confirm=True))
        case = self.sponsor.latest(result['id'])
        self.assertEqual(case['body']['reviewers'], ['sam', 'maya'])
        # Earlier stored cases have no reviewer field; their historical meaning remains.
        body = case['body']; body.pop('reviewers')
        self.store.put(case['ref'].id, case['kind'], case['scope'], body, case['ref'].revision)
        for actor in ('sam', 'maya'):
            case = self.sponsor.latest(case['ref'].id)
            Intake(self.store, actor).review(dict(expected=asdict(case['ref']), disposition='ready-for-investigation', rationale='Original review authority'))
        case = self.sponsor.latest(case['ref'].id)
        self.sponsor.publish(dict(expected=asdict(case['ref']), confirm=True, rationale='Legacy authorized review'))
        self.assertIsNotNone(self.sponsor.latest('INT-001'))

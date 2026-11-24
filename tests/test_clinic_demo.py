"""Synthetic Riverbend sample exercises the real adaptive-intent lifecycle without touching user work."""
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workbench.core import Ref, Store
from workbench.decisions import SCOPE
from workbench.projects import Projects
from workbench.clinic_demo import MARKER_ID, PROJECT_ID, TITLE, INITIAL, REVISED, NEED_V1, NEED_V2, CHALLENGE_V1, CHALLENGE_V2, NoEvaluation, populate, seed_project
from workbench.refinements import blockers
from workbench.workspace import Workspace


class ClinicDemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.anchor = Path(self.tmp.name)/'workbench.sqlite3'
        with closing(Store(self.anchor)) as store:
            Workspace(store, 'priya', NoEvaluation()).command('intake-start', dict(title='Existing user project'))
            self.original = list(store.db.iterdump())

    def tearDown(self):
        self.tmp.cleanup()

    def open_demo(self):
        projects = Projects(self.anchor)
        with projects.locked(PROJECT_ID) as project:
            return Store(project['path'])

    def test_complete_intake_packet_discussion_decision_and_change_chain(self):
        with patch.object(NoEvaluation, 'generate', side_effect=AssertionError('No model calls')) as generate:
            sample = seed_project(self.anchor)
            generate.assert_not_called()
        with closing(self.open_demo()) as store:
            w = Workspace(store, 'alex', NoEvaluation())
            issue = store.latest(sample['issue']['id'], {SCOPE})
            self.assertEqual(issue['body']['status'], 'resolved')
            self.assertEqual(issue['body']['decision_owner'], 'alex')
            before = store.read(Ref(**sample['requirement_before']), {SCOPE})
            after = store.read(Ref(**sample['requirement_after']), {SCOPE})
            self.assertEqual(before['body']['text'], INITIAL)
            self.assertEqual(after['body']['text'], REVISED)
            self.assertEqual(before['ref'].id, after['ref'].id)
            self.assertEqual(after['ref'].revision, 2)
            self.assertEqual(before['body']['drawer_id'], 'DRW-experience/ease-of-use')
            self.assertIn('intake_case', before['body'])
            self.assertEqual([g['id'] for g in before['body']['goal_refs']], [g['id'] for g in after['body']['goal_refs']])
            decision = store.read(Ref(**sample['decision']), {SCOPE})
            self.assertEqual(decision['body']['actor']['id'], 'alex')
            self.assertEqual(decision['body']['disposition'], 'approve')
            case = store.read(Ref(**sample['review']), {SCOPE})
            self.assertEqual(set(case['body']['reviews']), {'sam', 'lee'})
            events = w.state()['bridge']['issues'][0]['events']
            self.assertTrue({'comment', 'request-evidence', 'answer-request', 'basis-refreshed', 'resolved'} <= {e['body']['action'] for e in events})
            self.assertTrue({'sam', 'lee', 'priya', 'alex'} <= {e['body']['actor'] for e in events})
            self.assertEqual(issue['body']['information_request']['status'], 'answered')
            self.assertTrue(store.graph({SCOPE}).has_edge(issue['ref'], decision['ref']))
            self.assertEqual(len(w.latest_records('requirement-drawer')), 25)
            self.assertEqual(len(w.latest_records('requirement')), 1)
            self.assertEqual(len(w.latest_records('intent')), 1)
            self.assertEqual(store.latest('INT-001', {SCOPE})['ref'].revision, 2)
            self.assertTrue(all(m['body']['outcome_status'] == 'not-evaluated' for m in w.latest_records('success-measure')))
            self.assertTrue(all(m['body']['baseline'] == m['body']['target'] == '' for m in w.latest_records('success-measure')))
            self.assertEqual(store.latest(MARKER_ID, {SCOPE})['body']['evaluation'], 'not-run')

    def test_seed_shows_a_cross_team_scope_difference_without_deciding_it(self):
        """D014: Research scopes the finding to shift workers; Design applies it to all patients."""
        seed_project(self.anchor)
        with closing(self.open_demo()) as store:
            state = Workspace(store, 'priya', NoEvaluation()).state()
            found = state['knowledge_system']['structure']['differences']
            finding = next(d for d in found if d['title'].startswith('Shift workers who missed'))
            self.assertIn('scope-differs', finding['kinds'])
            self.assertEqual({g['group']: g['links'][0]['conditions'] for g in finding['groups']},
                             {'Research': 'Shift and irregular-hours workers', 'Design': 'All patients'})
            self.assertIn('reviewer judges', finding['next'])
            coverage = next(v for v in state['requirement_evidence'].values() if v['level'] != 'empty')
            self.assertEqual((coverage['level'], coverage['independent_origins'], coverage['current_teams']), ('moderate', 1, ['Design', 'Research']))
            self.assertFalse([r for r in store.db.execute("SELECT 1 FROM records WHERE kind='bridge-issue' AND body LIKE '%Shift workers who missed%'")])

    def test_published_finding_revises_intent_through_sponsor_decision_and_keeps_history(self):
        sample = seed_project(self.anchor)
        with closing(self.open_demo()) as store:
            before = store.read(Ref(**sample['intent_before']), {SCOPE})
            after = store.read(Ref(**sample['intent_after']), {SCOPE})
            self.assertEqual((before['ref'].revision, after['ref'].revision), (1, 2))
            self.assertEqual(before['body']['intake']['need'], NEED_V1)
            self.assertEqual(after['body']['intake']['need'], NEED_V2)
            self.assertEqual(before['body']['intake']['business_challenge'], CHALLENGE_V1)
            self.assertEqual(after['body']['intake']['business_challenge'], CHALLENGE_V2)
            self.assertNotIn('forget', after['body']['intake']['bottlenecks'].lower())
            self.assertNotEqual(before['body']['intake']['approach'], after['body']['intake']['approach'])
            change = store.latest(sample['intent_refinement']['id'], {SCOPE})
            self.assertEqual(change['body']['status'], 'incorporated')
            self.assertEqual(change['body']['requested_by'], 'sam')
            self.assertEqual(change['body']['field'], 'business_challenge')
            self.assertEqual(change['body']['responded_by'], 'priya')
            self.assertEqual(change['body']['result_intent'], sample['intent_after'])
            source = store.read(Ref(**change['body']['source']), {SCOPE})
            self.assertEqual(source['kind'], 'contribution')
            self.assertEqual(source['scope'], SCOPE)
            research_packet = store.resolve_packet(sample['packets']['research']['id'], sample['packets']['research']['revision'], {SCOPE})
            self.assertIn(source['ref'], [r['ref'] for r in research_packet['records']])
            self.assertFalse(blockers(store, sample['requirement_before']['id']))
            self.assertTrue(store.graph({SCOPE}).has_edge(after['ref'], Ref(**change['body']['source'])))
            measures = {m['ref'].id for m in Workspace(store, 'alex', NoEvaluation()).latest_records('success-measure')}
            self.assertIn('M-refill-rate', measures)

    def test_exact_historical_packets_private_preflight_and_result_remain_inspectable(self):
        sample = seed_project(self.anchor)
        with closing(self.open_demo()) as store:
            packets = sample['packets']
            def resolve(key, scopes={SCOPE}):
                p = packets[key]
                return store.resolve_packet(p['id'], p['revision'], scopes)
            initial, revised = resolve('design_initial'), resolve('design_revised')
            self.assertEqual(initial['id'], revised['id'])
            self.assertEqual((initial['revision'], revised['revision']), (1, 2))
            self.assertEqual(len([r for r in initial['records'] if r['kind'] == 'source']), 1)
            sources = [r for r in revised['records'] if r['kind'] == 'source']
            self.assertEqual(len(sources), 2)
            self.assertTrue(all('Synthetic walkthrough' in r['body']['text'] for r in sources))
            self.assertTrue(any('v0.1' in r['body']['text'] for r in sources))
            self.assertTrue(any('v0.2' in r['body']['text'] for r in sources))
            self.assertIn(Ref(**sample['requirement_before']), [r['ref'] for r in initial['records']])
            result = resolve('result')
            self.assertTrue({Ref(**sample[k]) for k in ('decision', 'requirement_after')} <= {r['ref'] for r in result['records']})
            self.assertTrue(all(r['scope'] == SCOPE for r in result['records']))
            self.assertTrue(any(r['kind'] == 'packet-release' for r in revised['records']))
            for key, private in [('sponsor_prepared','intake:sponsor'), ('research_prepared','domain:research'), ('design_revised_prepared','domain:design')]:
                with self.assertRaises(PermissionError): resolve(key)
                prepared = resolve(key, {SCOPE, private})
                self.assertTrue(any(r['scope'] == private for r in prepared['records']))
            issue_versions = [store.read(Ref(sample['issue']['id'], row[0]), {SCOPE}) for row in store.db.execute('SELECT revision FROM records WHERE id=?', (sample['issue']['id'],))]
            self.assertTrue(any(packets['design_initial'] in r['body']['packet_refs'] for r in issue_versions))
            self.assertIn(packets['design_revised'], issue_versions[-1]['body']['packet_refs'])

    def test_repeated_seed_preserves_existing_projects_and_user_edits_to_demo(self):
        sample = seed_project(self.anchor)
        with closing(self.open_demo()) as store:
            project = store.latest('PROJECT-001', {SCOPE})
            store.put('PROJECT-001', 'project', SCOPE, {**project['body'], 'title':'My edited demo name'}, project['ref'].revision)
            before = list(store.db.iterdump())
        self.assertEqual(seed_project(self.anchor), sample)
        with closing(self.open_demo()) as store:
            self.assertEqual(list(store.db.iterdump()), before)
        with closing(Store(self.anchor)) as store:
            self.assertEqual(list(store.db.iterdump()), self.original)
        self.assertEqual(len(Projects(self.anchor).listing()), 2)

    def test_failed_build_is_not_registered_and_cannot_populate_existing_project(self):
        with patch('workbench.clinic_demo.populate', side_effect=RuntimeError('Synthetic build failure')):
            with self.assertRaises(RuntimeError): seed_project(self.anchor)
        self.assertEqual([p['id'] for p in Projects(self.anchor).listing()], ['original'])
        self.assertEqual(list(Projects(self.anchor).directory.iterdir()), [])
        with closing(Store(self.anchor)) as store:
            with self.assertRaises(ValueError): populate(store)
            self.assertEqual(list(store.db.iterdump()), self.original)


if __name__ == '__main__':
    unittest.main()

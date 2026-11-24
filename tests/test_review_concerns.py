"""Offline native-command checks; model fixtures are test doubles, never paid calls."""
from copy import deepcopy
from dataclasses import asdict
import unittest
import test_bridge
from test_field_coach import CoachModel
from workbench.core import Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace


class ReviewConcernTests(unittest.TestCase):
    setUp = test_bridge.BridgeTests.setUp
    tearDown = test_bridge.BridgeTests.tearDown
    w = test_bridge.BridgeTests.w

    def prepare(self, **extra):
        return self.w('sam').command('field-coach-concern-prepare',dict(requirement=asdict(self.req['ref']),field='text',question='What establishes accepted ownership?',**extra))

    def publish_data(self,h,**extra):
        return dict(expected=h['ref'],confirm=True,title='Clarify accepted ownership',question=h['question'],consequence='A routing acknowledgement could be mistaken for accepted ownership.',boards=['research-design'],kind='gap',owner='sam',route='requirement',**extra)

    def snapshot(self):
        return ([tuple(r) for r in self.store.db.execute('SELECT * FROM records ORDER BY rowid')],
                [tuple(r) for r in self.store.db.execute('SELECT * FROM packets ORDER BY rowid')])

    def advice(self):
        model=CoachModel();w=Workspace(self.store,'sam',model)
        result=w.command('field-coach',dict(mode='record',kind='requirement',field='text',expected=asdict(self.req['ref']),consent=True))
        return result,model

    def test_preparation_is_private_and_carries_exact_published_context_without_changing_it(self):
        before=self.snapshot();h=self.prepare()
        after=self.snapshot();self.assertEqual(after[0][:-1],before[0]);self.assertEqual(after[1],before[1])
        draft=self.store.read(Ref(**h['ref']),{'coach:sam'})
        self.assertEqual(draft['kind'],'review-concern-draft')
        self.assertEqual(h['requirement_record'],self.req)
        self.assertIn(asdict(self.req['ref']),h['basis'])
        self.assertIsNone(h['review_excerpt'])
        for actor in ('priya','lee','alex'):
            with self.assertRaises(PermissionError):self.store.read(Ref(**h['ref']),self.w(actor).scopes)
        self.assertFalse(self.w('sam').bridge.issues())

    def test_large_published_context_can_be_carried_without_building_a_model_request(self):
        intent=self.store.latest('INT-001',{SCOPE})
        self.store.put(intent['ref'].id,intent['kind'],SCOPE,{**intent['body'],'large_public_context':'Saved context '*12000},intent['ref'].revision)
        h=self.prepare();self.assertTrue(any(r['kind']=='intent' for r in h['context']))
        result=self.w('sam').command('field-coach-concern-publish',self.publish_data(h))
        self.assertEqual(self.store.latest(result['id'],{SCOPE})['body']['status'],'open')

    def test_confirmation_and_valid_issue_fields_are_required_without_partial_release(self):
        h=self.prepare();before=self.snapshot()
        for patch in [dict(confirm=False),dict(owner='unknown'),dict(boards=[]),dict(question='')]:
            data={**self.publish_data(h),**patch}
            with self.assertRaises(ValueError):self.w('sam').command('field-coach-concern-publish',data)
            self.assertEqual(self.snapshot(),before)

    def test_publication_reuses_the_native_issue_path_and_never_updates_the_requirement(self):
        h=self.prepare();before=deepcopy(self.req)
        result=self.w('sam').command('field-coach-concern-publish',self.publish_data(h))
        issue=self.store.latest(result['id'],{SCOPE})
        self.assertEqual(issue['body']['requirement_refs'],[asdict(before['ref'])]);self.assertEqual(issue['body']['status'],'open')
        packet=issue['body']['packet_refs'][0];resolved=self.store.resolve_packet(packet['id'],packet['revision'],{SCOPE})
        concern=next(r for r in resolved['records'] if r['kind']=='review-concern')
        self.assertEqual(concern['body']['evidence_status'],'not-validated')
        self.assertEqual(concern['body']['context_refs'],h['basis'])
        self.assertIsNone(concern['body']['review_excerpt'])
        self.assertEqual(self.store.latest(before['ref'].id,{SCOPE}),before)
        for actor in ('priya','sam','lee','alex','maya'):
            self.assertEqual(self.store.read(concern['ref'],self.w(actor).scopes),concern)
        before_retry=self.snapshot()
        self.assertEqual(self.w('sam').command('field-coach-concern-publish',self.publish_data(h))['id'],result['id'])
        self.assertEqual(self.snapshot(),before_retry)
        with self.assertRaises(StaleBasis):self.w('sam').command('field-coach-concern-publish',{**self.publish_data(h),'question':'Different question'})

    def test_saved_model_excerpt_is_owned_exact_and_never_generates_another_model_call(self):
        advice,model=self.advice();original=self.store.read(Ref(**advice['ref']),{'coach:sam'})
        h=self.prepare(advice=advice['ref'])
        with self.assertRaises(PermissionError):self.w('lee').command('field-coach-concern-prepare',dict(requirement=asdict(self.req['ref']),field='text',advice=advice['ref']))
        self.assertEqual(h['review_excerpt'],advice['output'])
        data=self.publish_data(h);data.update(review_excerpt={'assessment':'FORGED'},requirement={'id':'OTHER','revision':1})
        result=self.w('sam').command('field-coach-concern-publish',data)
        issue=self.store.latest(result['id'],{SCOPE});concern=next(self.store.read(Ref(**r),{SCOPE}) for r in issue['body']['basis'] if r['id'].startswith('CONCERN-'))
        self.assertEqual(concern['body']['review_excerpt'],advice['output']);self.assertEqual(concern['body']['source_review'],advice['ref'])
        self.assertEqual(self.store.read(Ref(**advice['ref']),{'coach:sam'}),original);self.assertEqual(len(model.calls),1)

    def test_changed_requirement_or_context_blocks_commit_but_keeps_the_prepared_concern(self):
        for target in ('INT-001',self.req['ref'].id):
            with self.subTest(target=target):
                h=self.prepare();old=self.store.latest(target,{SCOPE});self.store.put(target,old['kind'],SCOPE,{**old['body'],'text':'Changed context'},old['ref'].revision)
                before=self.snapshot()
                with self.assertRaises(StaleBasis):self.w('sam').command('field-coach-concern-publish',self.publish_data(h))
                self.assertEqual(self.snapshot(),before)
                self.assertEqual(self.store.read(Ref(**h['ref']),{'coach:sam'})['kind'],'review-concern-draft')
                if target==self.req['ref'].id:self.req=self.store.latest(target,{SCOPE})

    def test_older_review_context_is_explicit_and_preserves_its_original_versions(self):
        advice,_=self.advice();old=self.store.latest('INT-001',{SCOPE})
        self.store.put('INT-001',old['kind'],SCOPE,{**old['body'],'text':'Newer direction'},old['ref'].revision)
        h=self.prepare(advice=advice['ref']);self.assertTrue(h['historical_context']);self.assertIn(asdict(old['ref']),h['basis'])
        result=self.w('sam').command('field-coach-concern-publish',self.publish_data(h))
        issue=self.store.latest(result['id'],{SCOPE});concern=next(self.store.read(Ref(**r),{SCOPE}) for r in issue['body']['basis'] if r['id'].startswith('CONCERN-'))
        self.assertTrue(concern['body']['historical_context']);self.assertIn(asdict(old['ref']),concern['body']['context_refs'])

    def test_a_carried_concern_does_not_satisfy_the_published_outcomes_report_requirement(self):
        from test_setup_governance import GovernedAccountabilityTests
        from workbench.decisions import DecisionBlocked
        GovernedAccountabilityTests.initial_publication(self)
        h=self.prepare();result=self.w('sam').command('field-coach-concern-publish',self.publish_data(h))
        issue=self.store.latest(result['id'],{SCOPE});before=self.snapshot()
        with self.assertRaisesRegex(DecisionBlocked,'published Outcomes report'):
            self.w('alex').command('bridge-propose',dict(expected_issue=asdict(issue['ref']),selected=[],text='A proposed revision',rationale='Review concern only',acceptance_criteria='Observe acceptance',conditions='Bounded',changes_intent=False))
        self.assertEqual(self.snapshot(),before)

    def test_private_or_unrelated_advice_cannot_be_released_as_published_requirement_context(self):
        advice,_=self.advice();saved=self.store.read(Ref(**advice['ref']),{'coach:sam'})
        private=self.store.put('PRIVATE-SOURCE','source','domain:research',{'text':'Secret'})
        forged=self.store.put(saved['ref'].id,saved['kind'],'coach:sam',{**saved['body'],'basis':[asdict(self.req['ref']),asdict(private)]},saved['ref'].revision)
        before=self.snapshot()
        with self.assertRaises(PermissionError):self.prepare(advice=asdict(forged))
        self.assertEqual(self.snapshot(),before)

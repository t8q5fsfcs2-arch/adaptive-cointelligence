"""Native intake-to-domain assessment continuity with bounded scripted outputs.

These are technical fixtures, not a live evaluation or a human workflow simulation.
"""
from copy import deepcopy
from dataclasses import asdict
import unittest

import test_business_assessments as fixtures
from test_intake import VALUE, CONTEXT
from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import SCOPE, DecisionBlocked
from workbench.intake import PRIVATE
from workbench.workspace import Workspace


class BusinessAssessmentFlowTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.BusinessAssessmentTests()
        self.f.store = Store(':memory:'); self.addCleanup(self.f.store.close)
        self.f.model = fixtures.TwoPassModel(); self.f.model.store = self.f.store
        self.f.w = Workspace(self.f.store, 'priya', self.f.model)
        self.w, self.store, self.model = self.f.w, self.f.store, self.f.model
        self.w.command('intake-start', dict(title='Synthetic native assessment continuity'))
        # Initial documents precede the starting proposition; later documents use
        # the separate existing document-impact workflow.
        self.f.source = self.w.command('intake-source', dict(title='Selected synthetic account',
            text='One person reported losing their place after requesting help. This is a single account, not a prevalence estimate.',role='evidence'))['ref']
        self.w.command('intake-save', dict(expected=self.ref(), step='value', **VALUE))
        self.w.command('intake-accept-value', dict(expected=self.ref(), confirm=True,
            rationale='Synthetic sponsor action acknowledges the stated assumptions.'))
        self.w.command('intake-save', dict(expected=self.ref(), step='context', **CONTEXT))
        self.w.command('intake-build', dict(expected=self.ref(), confirm=True))
        drawers = deepcopy(self.w.intake.draft()['body']['scaffold'])
        drawers[0].update(requirement='A person can resume after requesting assistance.',
            acceptance_criteria='A bounded test shows the previously saved values.')
        self.w.command('intake-drawers', dict(expected=self.ref(), drawers=drawers))

    def ref(self):
        return asdict(self.w.intake.draft()['ref'])

    def snapshot(self):
        return {table:[tuple(row) for row in self.store.db.execute('SELECT * FROM '+table+' ORDER BY rowid')]
                for table in ('records','dependencies','packets')}

    def assess_prepare(self):
        result = self.f.assess()
        out = self.w.command('intake-preflight', dict(expected=self.ref(), business_assessment=result['ref'],
            research_focus='Investigate interrupted work.', design_focus='Explore a bounded resumption cue.',
            open_questions='The prevalence and benefit remain unmeasured.'))
        prepared = self.store.latest(out['id'], self.w.scopes)
        return result, prepared

    def request(self, prepared, release=True):
        return self.w.command('intake-request', dict(expected=self.ref(), preflight=asdict(prepared['ref']),
            release_business_assessment=release, confirm=True))

    def publish(self, case_id):
        for actor in ('sam','lee'):
            current = self.store.latest(case_id, {SCOPE})
            Workspace(self.store, actor, self.model).command('intake-review', dict(expected=asdict(current['ref']),
                disposition='ready-for-investigation', rationale='Synthetic review preserves the stated evidence limits.'))
        current = self.store.latest(case_id, {SCOPE})
        self.w.command('intake-publish', dict(expected=asdict(current['ref']), confirm=True,
            rationale='Synthetic sponsor publishes direction for investigation only.'))
        return self.store.latest(case_id, {SCOPE})

    def test_explicit_release_is_atomic_and_private_analysis_stays_private(self):
        result, prepared = self.assess_prepare()
        self.assertEqual(len(self.model.calls), 2)
        private = [self.store.read(Ref(**result[key]), {PRIVATE}) for key in ('ref','inventory_ref')]
        for actor in ('sam','lee','alex','maya'):
            other = Workspace(self.store, actor, self.model)
            for record in private:
                with self.assertRaises(PermissionError): self.store.read(record['ref'], other.scopes)
            self.assertFalse(any(r['kind']=='business-assessment-release' for r in other.latest_records()))
        before = self.snapshot()
        with self.assertRaises(DecisionBlocked): self.request(prepared, release=False)
        self.assertEqual(self.snapshot(), before)
        request = self.request(prepared)
        case = self.store.latest(request['id'], {SCOPE})
        release = case['body']['snapshot']['business_assessment']
        shared = self.store.read(Ref(**release['ref']), {SCOPE})
        self.assertEqual(shared['kind'], 'business-assessment-release')
        for actor in ('priya','sam','lee','alex','maya'):
            self.assertEqual(self.store.read(shared['ref'], Workspace(self.store,actor,self.model).scopes), shared)
        for record in private:
            self.assertEqual(self.store.read(record['ref'], {PRIVATE}), record)
        self.assertEqual(len(self.model.calls), 2)

    def test_exact_quotes_and_requirement_specific_business_basis_reach_domains_and_delivery(self):
        result, prepared = self.assess_prepare(); request = self.request(prepared)
        case = self.publish(request['id']); intent = self.store.latest('INT-001', {SCOPE})
        release_ref = intent['body']['business_assessment']['ref']
        release = self.store.read(Ref(**release_ref), {SCOPE})
        quote = release['body']['assessment']['claim_assessments'][0]['evidence'][0]
        source = self.store.read(Ref(**quote['source_ref']), {SCOPE})
        self.assertEqual(source['body']['text'][quote['start']:quote['end']], quote['quote'])
        self.assertEqual(source['body']['source_version'], self.f.source)
        self.assertEqual(release['body']['assessment_ref'], release_ref)
        self.assertEqual(release['body']['assessment']['confidence']['level'], 'low')
        req_ref = case['body']['result']['requirements'][0]
        req = self.store.read(Ref(**req_ref), {SCOPE})
        self.assertEqual(req['body']['business_assessment']['ref'], release_ref)
        links = req['body']['business_assessment']['claim_links']
        self.assertEqual(len(links), 1); self.assertEqual(links[0]['target'], req['ref'].id)
        self.assertEqual(links[0]['business_basis_confidence']['level'], 'low')
        self.assertEqual(links[0]['assessment_scope'], 'business-intake-basis')
        self.assertEqual(req['body']['fulfillment'], 'not-evaluated')
        self.assertEqual(req['body']['execution'], 'not-authorized')
        for actor in ('sam','lee'):
            w = Workspace(self.store, actor, self.model)
            brief = w.domain_brief.context()
            self.assertEqual(brief['assessment_context']['current_business_intent']['assessment']['ref'], release_ref)
            self.assertIn(release_ref, brief['basis']); self.assertIn(quote['source_ref'], brief['basis'])
            saved = w.command('domain-save', dict(title='Synthetic domain draft',
                deliverable_type=w.domains.profile()['config']['deliverable_types'][0],
                observation='The synthetic draft retains the original evidence gap.', source='Shared synthetic account',
                limitation='Technical fixture; no independent finding or outcome.', source_refs=[quote['source_ref']],
                input_refs=[], links=[dict(ref=req_ref, relation='refines', rationale='Investigate the bounded resumption condition.')]))
            draft = self.store.latest(saved['id'], w.scopes)
            context = w.domains.context(asdict(draft['ref']))
            trace = context['assessment_context']['requirements'][0]
            self.assertEqual(trace['original_business_assessment']['ref'], release_ref)
            self.assertEqual(trace['business_claim_links'], links)
            self.assertIn(release_ref, context['basis']); self.assertIn(quote['source_ref'], context['basis'])
            self.assertEqual(trace['uses']['implementation']['confidence']['level'], 'not-rated')
        prepared_delivery = self.w.command('delivery-prepare', dict(target='ado',work_item_type='User Story',
            destination='SYNTHETIC', requirements=[req_ref]))
        delivery = self.store.latest(prepared_delivery['id'], self.w.scopes)
        self.assertIn(release_ref, delivery['body']['assessment_basis'])
        self.assertIn(quote['source_ref'], delivery['body']['assessment_basis'])
        exported = self.w.command('delivery-export', dict(expected=asdict(delivery['ref'])))
        self.assertEqual(exported['export']['external_receipts'], [])
        self.assertEqual(len(self.model.calls), 2)
        for key in ('ref','inventory_ref'):
            with self.assertRaises(PermissionError): self.store.read(Ref(**result[key]), {SCOPE})

    def test_source_change_blocks_release_and_retains_previous_model_outputs(self):
        result, prepared = self.assess_prepare(); original = self.store.read(Ref(**result['ref']), {PRIVATE})
        source = self.store.read(Ref(**self.f.source), {PRIVATE})
        self.store.put(source['ref'].id, source['kind'], PRIVATE, dict(source['body'], text='A changed synthetic observation.'), source['ref'].revision)
        before = self.snapshot()
        with self.assertRaises(StaleBasis): self.request(prepared)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.store.read(Ref(**result['ref']), {PRIVATE}), original)
        self.assertEqual(len(self.model.calls), 2)

    def test_later_business_publication_does_not_rewrite_existing_requirement_assessment_basis(self):
        _, prepared = self.assess_prepare(); first = self.publish(self.request(prepared)['id'])
        req_ref = first['body']['result']['requirements'][0]
        original = deepcopy(self.store.read(Ref(**req_ref), {SCOPE}))
        first_release = original['body']['business_assessment']['ref']
        self.w.command('intake-save', dict(expected=self.ref(), step='context',
            open_questions='A second synthetic check asks whether the context has changed.'))
        self.w.command('intake-build', dict(expected=self.ref(), confirm=True))
        _, second_prepared = self.assess_prepare()
        self.publish(self.request(second_prepared)['id'])
        latest_intent = self.store.latest('INT-001', {SCOPE})
        self.assertNotEqual(latest_intent['body']['business_assessment']['ref'], first_release)
        self.assertEqual(self.store.latest(req_ref['id'], {SCOPE}), original)
        from workbench.assessment_context import assessment_context
        trace = assessment_context(self.w, [req_ref])
        self.assertEqual(trace['requirements'][0]['original_business_assessment']['ref'], first_release)
        self.assertEqual(trace['current_business_intent']['assessment']['ref'], latest_intent['body']['business_assessment']['ref'])
        self.assertEqual(len(self.model.calls), 4)

"""Shared context/delivery receipts use synthetic records and no model calls."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch

import test_requirement_assessments as fixtures
from workbench.assessment_context import assessment_context, context_changes, shared_assessment_records
from workbench.core import Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace


class AssessmentContextTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.RequirementAssessmentTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.store, self.w = self.f.store, self.f.w

    def context(self):
        return assessment_context(self.w, [self.f.req])

    def prepare(self):
        return Workspace(self.store, 'priya').command('delivery-prepare', dict(
            target='jira', work_item_type='Story', destination='SYNTHETIC', requirements=[asdict(self.f.req)]))

    def draft(self):
        return self.store.latest(self.prepare()['id'], Workspace(self.store, 'priya').scopes)

    def test_projection_does_not_write_or_invent_ratings_and_historical_does_not_borrow(self):
        count = self.f.count(); unassessed = self.context()
        self.assertEqual(self.f.count(), count)
        self.assertEqual(unassessed['requirements'][0]['uses']['implementation']['confidence']['level'], 'not-rated')
        inventory = self.f.freeze(); self.f.service.record(self.f.record_payload(inventory, 'prototype'))
        current = self.context()
        self.assertEqual(current['requirements'][0]['uses']['prototype']['confidence']['level'], 'low')
        old = deepcopy(self.store.read(self.f.req, {SCOPE}))
        self.store.put(self.f.req.id, 'requirement', SCOPE, dict(old['body'], text='Changed requirement scope.'), 1)
        historical = self.context()['requirements'][0]
        self.assertFalse(historical['current']); self.assertEqual(historical['uses'], {})
        self.assertEqual(self.store.read(self.f.req, {SCOPE}), old)

    def test_exact_basis_and_new_assessment_invalidate_without_requirement_revision(self):
        original = self.context(); draft = self.draft(); inventory = self.f.freeze()
        recorded = self.f.service.record(self.f.record_payload(inventory, 'prototype'))['ref']
        self.assertTrue(context_changes(self.w, original))
        staged = Workspace(self.store, 'priya')
        self.assertTrue(staged.delivery.state()['drafts'][0]['changed'])
        with self.assertRaises(StaleBasis): staged.command('delivery-export', {'expected': asdict(draft['ref'])})
        fresh = self.draft()
        self.assertNotEqual(fresh['ref'].id, draft['ref'].id)
        self.assertIn(recorded, fresh['body']['assessment_basis'])
        self.assertIn(inventory, fresh['body']['assessment_basis'])
        self.assertEqual(fresh['body']['items'][0]['assessment_context']['uses']['prototype']['confidence']['level'], 'low')
        self.assertEqual(staged.command('delivery-export', {'expected': asdict(fresh['ref'])})['export']['external_receipts'], [])
        second = self.f.record_payload(inventory, 'prototype', expected=recorded)
        self.f.service.record(second)
        with self.assertRaises(StaleBasis): staged.command('delivery-export', {'expected': asdict(fresh['ref'])})

    def test_relevant_evidence_change_invalidates_but_unrelated_change_does_not(self):
        inventory = self.f.freeze(); self.f.service.record(self.f.record_payload(inventory, 'implementation', 'met'))
        draft = self.draft(); body = deepcopy(draft['body'])
        self.assertIn(asdict(self.f.source), body['assessment_basis'])
        self.store.put(self.f.other.id, 'source', SCOPE, {'text': 'An unrelated new passage.'}, 1)
        self.assertEqual(context_changes(self.w, body['assessment_context']), [])
        staged = Workspace(self.store, 'priya')
        self.assertIn('export', staged.command('delivery-export', {'expected': asdict(draft['ref'])}))
        self.store.put(self.f.source.id, 'source', SCOPE, {'text': 'The underlying evidence changed.'}, 1)
        self.assertTrue(context_changes(self.w, body['assessment_context']))
        with self.assertRaises(StaleBasis): staged.command('delivery-export', {'expected': asdict(draft['ref'])})
        self.assertEqual(self.store.read(draft['ref'], staged.scopes)['body'], body)
        self.assertEqual(self.store.latest(self.f.req.id, {SCOPE})['ref'], self.f.req)

    def test_legacy_preview_keeps_local_export_with_explicit_assessment_limitation(self):
        draft = self.draft(); body = deepcopy(draft['body'])
        for key in ('assessment_context', 'assessment_basis', 'assessment_boundary'): body.pop(key)
        legacy = self.store.put('DELIVERY-LEGACY', 'delivery-draft', draft['scope'], body)
        staged = Workspace(self.store, 'priya')
        row = next(r for r in staged.delivery.state()['drafts'] if r['ref'].id == legacy.id)
        self.assertEqual(row['changed'], []); self.assertIn('Legacy preview', row['assessment_limitation'])
        self.assertIn('export', staged.command('delivery-export', {'expected': asdict(legacy)}))

    def test_lost_shared_basis_redacts_copied_delivery_context_and_preserves_canonical_draft(self):
        inventory = self.f.freeze(); self.f.service.record(self.f.record_payload(inventory, 'implementation', 'met'))
        draft = self.draft(); original = deepcopy(draft)
        self.store.db.execute('UPDATE records SET scope=? WHERE id=?', ('domain:design', self.f.source.id))
        self.store.db.commit()
        staged = Workspace(self.store, 'priya')
        safe = staged.delivery.safe_record(draft)
        self.assertTrue(safe['body']['assessment_context']['access_limited'])
        self.assertNotIn('payload', safe['body']['items'][0])
        self.assertNotIn('SYNTHETIC-PUBLIC-BASIS', json.dumps(safe, default=lambda value:asdict(value)))
        state = staged.delivery.state()
        self.assertTrue(state['drafts'][0]['changed'])
        self.assertNotIn('SYNTHETIC-PUBLIC-BASIS', json.dumps(state, default=lambda value:asdict(value)))
        records = staged.latest_records('delivery-draft')
        self.assertTrue(records[0]['body']['assessment_context']['access_limited'])
        self.assertNotIn('SYNTHETIC-PUBLIC-BASIS', json.dumps(staged.state(), default=lambda value:asdict(value)))
        with self.assertRaises(StaleBasis): staged.command('delivery-export', {'expected':asdict(draft['ref'])})
        self.assertEqual(self.store.read(draft['ref'], staged.scopes), original)

    def test_private_or_unrelated_assessment_graph_is_rejected(self):
        inventory = self.f.freeze(); recorded = self.f.service.record(self.f.record_payload(inventory))['ref']
        records = shared_assessment_records(self.w, [recorded], self.f.req)
        self.assertIn(self.f.source, [r['ref'] for r in records])
        other = self.store.put('REQ-OTHER', 'requirement', SCOPE, {'text': 'Different requirement.'})
        with self.assertRaises(ValueError): shared_assessment_records(self.w, [recorded], other)
        private = self.store.put('BASSESS-PRIVATE', 'business-argument-assessment', 'intake:sponsor', {'text': 'Secret.'})
        with self.assertRaises(PermissionError): shared_assessment_records(self.w, [private])

    def release(self, identity, quote='A synthetic bounded business claim.'):
        from workbench.business_assessments import standard, standard_ref
        configured = standard()
        if not self.store.db.execute('SELECT 1 FROM records WHERE id=?',(configured['id'],)).fetchone():
            self.store.put(configured['id'], 'evidence-reasoning-standard', SCOPE, configured)
        source = self.store.put('SRC-' + identity, 'source', SCOPE, dict(text=quote))
        ref = dict(id=identity, revision=1)
        citation = dict(source_ref=asdict(source), passage_id=source.label()+':0-'+str(len(quote)), quote=quote, start=0, end=len(quote))
        self.store.put(identity, 'business-assessment-release', SCOPE, dict(assessment_ref=ref,
            inventory={'claims': [{'key': 'business-claim', 'citations': [citation]}]},
            assessment={'confidence': {'level': 'low', 'limits': 'Synthetic test only.'}},
            standard={'ref':standard_ref(configured),'body':configured}, sources=[asdict(source)],
            basis={'id': 'PRIVATE-UNAVAILABLE-DRAFT', 'revision': 7}))
        return ref, source

    def test_original_business_release_stays_separate_from_current_intent_and_sources_are_verified(self):
        original, source = self.release('RELEASE-ORIGINAL')
        case = self.store.put('INTAKE-EXACT', 'intake-case', SCOPE, {'snapshot': {'business_assessment': {'ref': original}}})
        req = self.store.read(self.f.req, {SCOPE})
        self.f.req = self.store.put(self.f.req.id, 'requirement', SCOPE, dict(req['body'], intake_case=asdict(case), business_assessment={'ref': original}), 1)
        latest, latest_source = self.release('RELEASE-CURRENT', 'The current direction changes the scope.')
        intent = self.store.put('INT-001', 'intent', SCOPE, {'text': 'Current direction.', 'business_assessment': {'ref': latest}})
        trace = self.context()
        self.assertEqual(trace['requirements'][0]['original_business_assessment']['ref'], original)
        self.assertEqual(trace['current_business_intent']['assessment']['ref'], latest)
        self.assertIn(asdict(source), trace['basis']); self.assertIn(asdict(latest_source), trace['basis'])
        self.assertNotIn({'id': 'PRIVATE-UNAVAILABLE-DRAFT', 'revision': 7}, trace['basis'])
        self.store.put(latest_source.id, 'source', SCOPE, {'text': 'Revised evidence.'}, 1)
        self.assertTrue(context_changes(self.w, trace))
        self.assertEqual(self.store.latest(intent.id, {SCOPE})['ref'], intent)

    def test_changed_common_standard_invalidates_without_relabeling_original_judgment(self):
        from workbench.business_assessments import standard
        release, _ = self.release('RELEASE-STANDARD')
        self.store.put('INT-001', 'intent', SCOPE, {'text':'Synthetic direction.', 'business_assessment':{'ref':release}})
        saved = self.context()
        changed = standard(); changed['revision'] = 2
        with patch('workbench.business_assessments.standard', return_value=changed):
            self.assertTrue(context_changes(self.w, saved))
            fresh = self.context()['current_business_intent']['assessment']
            self.assertFalse(fresh['standard_current'])
            self.assertEqual(fresh['assessment']['confidence']['level'], 'low')
        self.assertEqual(self.context(), saved)


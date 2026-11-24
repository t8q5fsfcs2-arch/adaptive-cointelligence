"""Synthetic exact assessment receipts survive the native concern handoff."""
from copy import deepcopy
from dataclasses import asdict
import unittest
import test_requirement_assessments as fixtures
from workbench.core import Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from test_field_coach import CoachModel


class AssessmentHandoffTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.RequirementAssessmentTests(); self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.w, self.store = self.f.w, self.f.store

    def prepare(self, **extra):
        return self.w.command('field-coach-concern-prepare', dict(requirement=asdict(self.f.req),
            field='text', intended_use='prototype', question='Which condition still needs evidence?', **extra))

    def publish(self, draft):
        return self.w.command('field-coach-concern-publish', dict(expected=draft['ref'], confirm=True,
            title='Clarify the remaining evidence gap', question='Which observation establishes saved progress?',
            consequence='Losing saved progress repeats work.', boards=['research-design'], kind='gap', owner='sam', route='requirement'))

    def test_selected_use_carries_exact_inventory_standard_evidence_without_grading(self):
        inventory = self.f.freeze(); assessment = self.f.service.record(self.f.record_payload(inventory, 'prototype'))['ref']
        count = self.f.count(); draft = self.prepare()
        self.assertEqual(self.f.count(), count+1)
        self.assertEqual(draft['assessment_context']['assessment'], assessment)
        self.assertEqual(draft['assessment_context']['status'], 'suitable')
        self.assertIn(inventory, draft['basis']); self.assertIn(assessment, draft['basis'])
        self.assertIn(asdict(self.f.source), draft['basis'])
        result = self.publish(draft); issue = self.store.latest(result['id'], {SCOPE})
        packet = issue['body']['packet_refs'][0]
        records = self.store.resolve_packet(packet['id'], packet['revision'], {SCOPE})['records']
        concern = next(r for r in records if r['kind']=='review-concern')
        self.assertEqual(concern['body']['assessment_context'], draft['assessment_context'])
        self.assertEqual(self.store.read(self.f.req, {SCOPE}), self.f.original)

    def test_new_assessment_after_preparation_requires_refresh_without_losing_saved_concern(self):
        draft = self.prepare(); inventory = self.f.freeze()
        self.f.service.record(self.f.record_payload(inventory, 'prototype'))
        before = self.f.count()
        with self.assertRaises(StaleBasis): self.publish(draft)
        self.assertEqual(self.f.count(), before)
        self.assertEqual(self.store.read(Ref(**draft['ref']), {'coach:sam'})['kind'], 'review-concern-draft')

    def test_evidence_change_after_preparation_preserves_original_and_blocks_publication(self):
        inventory = self.f.freeze(); self.f.service.record(self.f.record_payload(inventory, 'prototype'))
        draft = self.prepare(); original = deepcopy(self.store.read(Ref(**draft['ref']), {'coach:sam'}))
        self.store.put(self.f.source.id, 'source', SCOPE, {'text': 'Changed independent basis.'}, 1)
        with self.assertRaises(StaleBasis): self.publish(draft)
        self.assertEqual(self.store.read(Ref(**draft['ref']), {'coach:sam'}), original)

    def test_saved_advice_with_exact_assessment_basis_is_reused_without_another_model_request(self):
        inventory = self.f.freeze(); assessment = self.f.service.record(self.f.record_payload(inventory, 'prototype'))['ref']
        model = CoachModel(); w = Workspace(self.store, 'sam', model)
        advice = w.command('field-coach', dict(mode='record', kind='requirement', field='text',
            expected=asdict(self.f.req), consent=True))
        draft = self.prepare(advice=advice['ref'])
        self.assertIn(assessment, draft['basis']); self.assertEqual(draft['source_review'], advice['ref'])
        self.publish(draft)
        self.assertEqual(len(model.calls), 1)

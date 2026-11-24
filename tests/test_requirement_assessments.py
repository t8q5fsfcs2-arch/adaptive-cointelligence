"""Synthetic contract and preservation tests; no model grading or human simulation."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import SCOPE, fingerprint
from workbench.workspace import Workspace
from workbench.requirement_assessments import standard, standard_ref, ASSESSMENT_KIND, INVENTORY_KIND


class RequirementAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(':memory:')
        self.addCleanup(self.store.close)
        self.req = self.store.put('REQ-CHECK', 'requirement', SCOPE, dict(
            title='Keep draft progress', text='Preserve draft progress. Show the saved owner.',
            acceptance_criteria='Resume with the saved values and owner.', conditions='Interrupted report entry.',
            status='proposed', fulfillment='not-evaluated', execution='not-authorized'))
        self.source_text = ('SYNTHETIC-PUBLIC-BASIS: Investigate interrupted report entry with a bounded '
                            'observation method. Preserve draft values and show the saved owner. '
                            'Use synthetic data with existing access constraints.')
        self.source = self.store.put('SRC-ONE', 'source', SCOPE, dict(title='First shared basis', text=self.source_text))
        self.other = self.store.put('SRC-TWO', 'source', SCOPE, dict(title='Second shared basis', text='The saved owner is shown during resumed report entry.'))
        self.w = Workspace(self.store, 'sam', principal_id='account-sam')
        self.service = self.w.requirement_assessments
        self.original = deepcopy(self.store.read(self.req, {SCOPE}))

    def test_new_shared_evidence_prompts_reassessment_without_changing_the_rating(self):
        """D012: later published work on the requirement asks for a fresh look; it never edits the rating."""
        before = self.count()
        self.assertEqual(self.service._new_evidence('REQ-CHECK', '2026-11-20T00:00:00+00:00'), [])
        self.store.put('CONTRIB-OLD', 'contribution', SCOPE, dict(domain='Research', published_at='2026-11-19T00:00:00+00:00', requirement_refs=[asdict(self.req)]))
        self.store.put('CONTRIB-OTHER', 'contribution', SCOPE, dict(domain='Design', published_at='2026-11-23T00:00:00+00:00', requirement_refs=[dict(id='REQ-ELSE', revision=1)]))
        self.assertEqual(self.service._new_evidence('REQ-CHECK', '2026-11-20T00:00:00+00:00'), [])
        new = self.store.put('CONTRIB-NEW', 'contribution', SCOPE, dict(domain='Design', published_at='2026-11-23T00:00:00+00:00', requirement_refs=[asdict(self.req)]))
        prompt = self.service._new_evidence('REQ-CHECK', '2026-11-20T00:00:00+00:00')
        self.assertEqual(prompt, [dict(reason='New shared evidence since this rating', contributions=[asdict(new)])])
        self.assertEqual(self.service._new_evidence('REQ-CHECK', None), [])
        self.assertEqual(self.count(), before + 3)   # reading wrote nothing
        self.assertEqual(self.store.read(self.req, {SCOPE}), self.original)

    def count(self):
        return self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]

    def freeze_payload(self, **changes):
        payload = dict(requirement=asdict(self.req), expected=None, standard=standard_ref(),
            scope='Interrupted report-entry investigation', applicability='People resuming an interrupted report',
            material_conditions=[dict(key='progress', source=dict(ref=asdict(self.req), field='text', quote='Preserve draft progress.'),
                expected_observation='Resume with the saved draft values', applicability='Interrupted report entry',
                required_evidence_level='documentary', consequence='Loss of progress requires repeated entry', dependencies=[])],
            rationale='The saved progress condition is material to the scoped inquiry')
        payload.update(changes)
        return payload

    def freeze(self, **changes):
        return self.service.freeze(self.freeze_payload(**changes))['ref']

    def citation(self, source=None, level='documentary'):
        source = source or self.source
        return dict(ref=asdict(source), field='text', quote=self.store.read(source, {SCOPE})['body']['text'], level=level)

    def record_payload(self, inventory, use='investigation', status='missing', **changes):
        ib = self.store.read(Ref(**inventory), {SCOPE})['body']
        payload = dict(inventory=inventory, intended_use=use, expected=None,
            condition_judgments=[dict(key=c['key'], status=status,
                rationale='No independent evidence has established the proposed behavior yet',
                evidence=[self.citation()] if status in {'met', 'not-applicable'} else []) for c in ib['material_conditions']],
            use_judgments=[dict(key=c['key'], status='met', rationale='The scoped shared plan explicitly addresses this use check',
                evidence=[self.citation()]) for c in standard()['profiles'][use]['checks']],
            confidence=dict(level='low', claim='Retaining saved draft progress', scope='Interrupted report entry',
                rationale='Documentary support is limited and operational behavior remains untested',
                limits='No production runtime test or delivered outcome has been recorded'),
            next_action='Investigate the condition using the bounded observation method',
            rationale='Human judgment supports the next scoped inquiry', confirm=True)
        payload.update(changes)
        return payload

    def item(self):
        return self.service.state()['items'][self.req.id]

    def test_unassessed_state_and_guidance_read_without_writes_or_guessed_grades(self):
        before = self.count()
        item = self.item()
        self.assertIsNone(item['inventory']); self.assertEqual(item['history'], [])
        for use in item['uses'].values():
            self.assertEqual(use['status'], 'not-assessed')
            self.assertEqual(use['confidence']['level'], 'not-rated')
        self.assertEqual(item['coverage']['total'], 0)
        self.assertIn('profiles', self.service.guidance()['standard']['body'])
        self.assertEqual(self.count(), before)

    def test_freeze_precedes_grades_and_append_preserves_exact_standard_target_and_predecessor(self):
        first = self.freeze(); saved = deepcopy(self.store.read(Ref(**first), {SCOPE}))
        self.assertEqual(saved['body']['requirement'], asdict(self.req))
        self.assertEqual(saved['body']['standard'], standard_ref())
        self.assertEqual(saved['body']['actor'], 'sam')
        self.assertNotIn('condition_judgments', saved['body'])
        second = self.freeze(expected=first, rationale='Clarify the materiality explanation without grading the condition')
        self.assertEqual(second['revision'], 2)
        self.assertEqual(self.store.read(Ref(**second), {SCOPE})['body']['previous'], first)
        self.assertEqual(self.store.read(Ref(**first), {SCOPE}), saved)
        with self.assertRaises(StaleBasis): self.freeze(expected=first)
        with self.assertRaises((ValueError, PermissionError)):
            self.service.record(dict(self.record_payload(first), inventory=dict(id='MISSING-INVENTORY', revision=1)))
        self.assertEqual(self.store.read(self.req, {SCOPE}), self.original)

    def test_intended_use_is_independent_of_substantive_evidence_and_authority(self):
        inventory = self.freeze()
        for use, expected in [('investigation', 'suitable'), ('prototype', 'suitable'), ('implementation', 'needs-work')]:
            payload = self.record_payload(inventory, use)
            payload.update(actor='alex', assessor_type='model', status='approved')
            result = self.service.record(payload)
            body = self.store.read(Ref(**result['ref']), {SCOPE})['body']
            self.assertEqual(body['status'], expected)
            self.assertEqual(body['actor'], 'sam'); self.assertEqual(body['principal'], 'account-sam')
            self.assertEqual(body['assessor_type'], 'human')
            self.assertEqual(body['condition_judgments'][0]['status'], 'missing')
        self.assertEqual(self.store.read(self.req, {SCOPE}), self.original)
        self.assertEqual(self.w.loop.history(), [])

    def test_required_checks_cannot_be_omitted_duplicated_or_waived_by_not_applicable(self):
        inventory = self.freeze(); before = self.count()
        for mode in ('omit', 'duplicate', 'waive'):
            payload = self.record_payload(inventory)
            if mode == 'omit': payload['condition_judgments'] = []
            if mode == 'duplicate': payload['use_judgments'][-1] = deepcopy(payload['use_judgments'][0])
            if mode == 'waive': payload['use_judgments'][0]['status'] = 'not-applicable'
            with self.assertRaises(ValueError): self.service.record(payload)
            self.assertEqual(self.count(), before)

    def test_invalid_quotes_private_sources_and_plain_document_runtime_claims_are_rejected_atomically(self):
        inventory = self.freeze(); before = self.count()
        private = self.store.put('PRIVATE-SOURCE', 'source', 'domain:research', dict(text='Restricted passage'))
        for mode in ('quote', 'private', 'runtime', 'self-support'):
            payload = self.record_payload(inventory, status='met')
            evidence = payload['condition_judgments'][0]['evidence'][0]
            if mode == 'quote': evidence['quote'] = 'An invented passage'
            if mode == 'private': evidence.update(ref=asdict(private), quote='Restricted passage')
            if mode == 'runtime': evidence['level'] = 'runtime'
            if mode == 'self-support': evidence.update(ref=asdict(self.req), quote='Preserve draft progress.')
            with self.assertRaises((ValueError, PermissionError)): self.service.record(payload)
            self.assertEqual(self.count(), before+1)

    def test_explicit_runtime_source_can_support_runtime_condition_without_changing_fulfillment(self):
        payload = self.freeze_payload(); payload['material_conditions'][0]['required_evidence_level'] = 'runtime'
        inventory = self.service.freeze(payload)['ref']
        runtime = self.store.put('TEST-RUN', 'evidence', SCOPE, dict(text='The isolated retry retained all synthetic draft values.', evidence_level='runtime'))
        payload = self.record_payload(inventory, 'implementation', 'met')
        payload['condition_judgments'][0]['evidence'] = [self.citation(runtime, 'runtime')]
        payload['confidence']['level'] = 'high'
        result = self.service.record(payload)
        self.assertEqual(self.store.read(Ref(**result['ref']), {SCOPE})['body']['status'], 'suitable')
        self.assertEqual(self.store.read(self.req, {SCOPE})['body']['fulfillment'], 'not-evaluated')

    def test_confidence_never_comes_from_coverage_or_contradictory_or_absent_support(self):
        inventory = self.freeze(); before = self.count()
        for status, confidence in [('contradicted', 'moderate'), ('missing', 'moderate'), ('partial', 'high')]:
            payload = self.record_payload(inventory, status=status); payload['confidence']['level'] = confidence
            with self.assertRaises(ValueError): self.service.record(payload)
        self.assertEqual(self.count(), before)
        self.service.record(self.record_payload(inventory))
        self.assertEqual(self.item()['coverage']['checked'], 1)
        self.assertEqual(self.item()['coverage']['supported'], 0)
        self.assertEqual(self.item()['uses']['investigation']['confidence']['level'], 'low')

    def test_all_not_applicable_is_not_vacuous_implementation_suitability_or_full_coverage(self):
        inventory = self.freeze()
        result = self.service.record(self.record_payload(inventory, 'implementation', 'not-applicable'))
        self.assertEqual(self.store.read(Ref(**result['ref']), {SCOPE})['body']['status'], 'needs-work')
        coverage = self.item()['coverage']
        self.assertEqual(coverage['total'], 0); self.assertEqual(coverage['excluded'], 1)
        self.assertEqual(coverage['checked'], 0)

    def two_conditions(self):
        payload = self.freeze_payload()
        owner = deepcopy(payload['material_conditions'][0])
        owner.update(key='owner', source=dict(ref=asdict(self.req), field='text', quote='Show the saved owner.'),
                     expected_observation='The saved owner remains visible')
        payload['material_conditions'].append(owner)
        return self.service.freeze(payload)['ref']

    def test_selective_dependency_staleness_preserves_unaffected_judgment_and_historical_confidence(self):
        inventory = self.two_conditions(); payload = self.record_payload(inventory, 'implementation', 'met')
        payload['condition_judgments'][1]['evidence'] = [self.citation(self.other)]
        payload['confidence']['level'] = 'high'
        recorded = self.service.record(payload)['ref']; original = deepcopy(self.store.read(Ref(**recorded), {SCOPE}))
        self.store.put(self.source.id, 'source', SCOPE, dict(title='Changed basis', text='A new documentary interpretation'), 1)
        item = self.item(); use = item['uses']['implementation']
        self.assertEqual(use['status'], 'needs-reassessment'); self.assertEqual(use['confidence']['level'], 'not-rated')
        self.assertTrue(use['condition_results'][0]['stale'])
        self.assertEqual(use['condition_results'][1]['stale'], []); self.assertTrue(use['condition_results'][1]['reusable'])
        self.assertEqual(item['coverage']['supported'], 1); self.assertEqual(item['coverage']['unchecked'], 1)
        self.assertEqual(use['current']['body']['confidence']['level'], 'high')
        self.assertEqual(self.store.read(Ref(**recorded), {SCOPE}), original)
        payload['expected'] = recorded
        with self.assertRaises(StaleBasis): self.service.record(payload)

    def test_inventory_extension_preserves_old_judgments_but_new_denominator_is_explicitly_unassessed(self):
        inventory = self.freeze(); self.service.record(self.record_payload(inventory, status='met'))
        payload = self.freeze_payload(expected=inventory)
        extra = deepcopy(payload['material_conditions'][0]); extra.update(key='owner', source=dict(ref=asdict(self.req), field='text', quote='Show the saved owner.'))
        payload['material_conditions'].append(extra); self.service.freeze(payload)
        item = self.item(); results = item['uses']['investigation']['condition_results']
        self.assertTrue(results[0]['reusable']); self.assertEqual(results[1]['status'], 'not-assessed')
        self.assertEqual(item['coverage']['total'], 2); self.assertEqual(item['coverage']['unchecked'], 1)
        self.assertEqual(item['uses']['investigation']['status'], 'needs-reassessment')

    def test_unrelated_change_does_not_invalidate_and_read_does_not_write(self):
        inventory = self.freeze(); self.service.record(self.record_payload(inventory, status='met'))
        self.store.put(self.other.id, 'source', SCOPE, dict(text='An unrelated revised passage'), 1)
        before = self.count(); item = self.service.read(dict(requirement=asdict(self.req)))
        self.assertEqual(item['uses']['investigation']['status'], 'suitable'); self.assertEqual(self.count(), before)

    def test_lost_source_access_redacts_both_dedicated_state_and_generic_workspace_records(self):
        inventory = self.freeze(); self.service.record(self.record_payload(inventory, status='met'))
        self.store.db.execute('UPDATE records SET scope=? WHERE id=?', ('domain:design', self.source.id)); self.store.db.commit()
        state = self.w.state()
        self.assertNotIn('SYNTHETIC-PUBLIC-BASIS', json.dumps(state, default=lambda value: asdict(value)))
        self.assertFalse(any(r['kind'] in {ASSESSMENT_KIND, INVENTORY_KIND} for r in state['records']))
        item = state['requirement_assessments']['items'][self.req.id]
        self.assertTrue(item['history'][0]['body']['access_limited'])
        self.assertEqual(item['uses']['investigation']['confidence']['level'], 'not-rated')

    def test_authorized_admin_reads_shared_assessment_without_assessor_write_authority(self):
        inventory = self.freeze(); self.service.record(self.record_payload(inventory))
        admin = Workspace(self.store, 'administrator', admin=True).requirement_assessments
        self.assertFalse(admin.state()['can_record'])
        self.assertEqual(admin.state()['items'], self.service.state()['items'])
        self.assertEqual(admin.read(dict(requirement=asdict(self.req))), self.item())
        with self.assertRaises(PermissionError): admin.freeze(self.freeze_payload(expected=inventory))
        with self.assertRaises(PermissionError): admin.record(self.record_payload(inventory))
        revoked = Workspace(self.store, 'sam', decision_members=[]).requirement_assessments
        with self.assertRaises(PermissionError): revoked.freeze(self.freeze_payload(expected=inventory))

    def test_bad_field_lengths_placeholders_wrong_clause_and_stale_expected_write_nothing(self):
        for key, value in [('scope', 'TBD'), ('rationale', 'x'*3001)]:
            before = self.count()
            with self.assertRaises(ValueError): self.freeze(**{key: value})
            self.assertEqual(self.count(), before)
        payload = self.freeze_payload(); payload['material_conditions'][0]['source']['ref'] = asdict(self.source)
        payload['material_conditions'][0]['source']['quote'] = self.source_text
        with self.assertRaises(ValueError): self.service.freeze(payload)
        inventory = self.freeze(); record = self.service.record(self.record_payload(inventory))
        before = self.count()
        with self.assertRaises(StaleBasis): self.service.record(self.record_payload(inventory))
        self.assertEqual(self.count(), before)
        self.assertEqual(self.item()['history'][0]['ref'], record['ref'])

    def test_standards_remain_pinned_and_changed_standard_invalidates_without_relabeling_history(self):
        inventory = self.freeze(); self.service.record(self.record_payload(inventory))
        original = deepcopy(self.item()['history'])
        updated = standard(); updated['revision'] = 2; updated['profiles']['investigation']['checks'][0]['label'] = 'A revised question check'
        with patch('workbench.requirement_assessments.standard', return_value=deepcopy(updated)):
            state = self.service.state(); item = state['items'][self.req.id]
            self.assertEqual(state['standards'][0]['ref']['revision'], 2)
            self.assertEqual(state['standards'][1]['ref']['revision'], 1)
            self.assertEqual(item['uses']['investigation']['status'], 'needs-reassessment')
            self.assertEqual(item['history'], original)
            self.assertNotEqual(state['standards'][1]['body']['profiles']['investigation']['checks'][0]['label'], 'A revised question check')
            payload = self.freeze_payload(expected=inventory, standard=standard_ref(updated))
            self.service.freeze(payload)
            self.assertEqual(self.store.latest(updated['id'], {SCOPE})['ref'].revision, 2)

    def test_historical_target_does_not_borrow_new_inventory_and_guidance_is_bounded(self):
        inventory = self.freeze(); self.service.record(self.record_payload(inventory))
        before = self.count(); guidance = self.service.guidance(self.original)
        self.assertNotIn('history', guidance)
        self.assertIn('gaps', guidance['assessments']['investigation'])
        self.assertTrue(any('whole-requirement' in rule for rule in guidance['rules']))
        self.assertEqual(self.count(), before)
        self.store.put(self.req.id, 'requirement', SCOPE, dict(self.original['body'], text='Changed requirement scope.'), 1)
        with self.assertRaises(StaleBasis): self.service.read(dict(requirement=asdict(self.req)))
        historical = self.service.guidance(self.original)
        self.assertIn('Historical requirement', historical['limitation'])
        self.assertNotIn('inventory', historical)

    def test_same_version_standard_mutation_cannot_relabel_saved_checks_or_be_written(self):
        inventory = self.freeze(); self.service.record(self.record_payload(inventory))
        saved = standard(); altered = deepcopy(saved)
        altered['profiles']['investigation']['checks'][0]['label'] = 'Different meaning under the same version'
        before = self.count()
        with patch('workbench.requirement_assessments.standard', return_value=altered):
            state = self.service.state()
            self.assertTrue(state['standard_conflict']); self.assertFalse(state['can_record'])
            self.assertIsNone(state['current_standard'])
            self.assertEqual(state['standards'][0]['body'], saved)
            self.assertIn('conflicts', self.service.guidance()['limitation'])
            with self.assertRaises(StaleBasis): self.freeze(expected=inventory)
        self.assertEqual(self.count(), before)

    def legacy_case(self, revision, proposition, disposition='ready-for-investigation'):
        snapshot = dict(values=dict(value=proposition, open_questions='Which event demonstrates accepted ownership?',
            constraints='Nonurgent work in existing access boundaries.', out_scope='Production execution remains outside this inquiry.'),
            value_acceptance=dict(status='reviewed-starting-proposition',
                rationale='Enacted local walkthrough; this is not actual stakeholder approval or measured benefit.'))
        review = self.store.put('LEGACY-REVIEW-'+str(revision), 'intake-assessment', SCOPE,
            dict(actor='sam', disposition=disposition, rationale='The scoped direction can be investigated within its declared limits.',
                 snapshot_fingerprint=fingerprint(snapshot), at='2026-11-14T05:00:00+00:00'))
        case = self.store.put('LEGACY-CASE', 'intake-case', SCOPE,
            dict(snapshot=snapshot, source_draft=dict(id='PRIVATE-DRAFT', revision=revision),
                 reviewers=['sam'], reviews=dict(sam=asdict(review)), status='pending-review'), revision-1)
        intent = self.store.put('INT-LEGACY', 'intent', SCOPE,
            dict(text=proposition, source_case=asdict(case), fit_status='hypothesis-to-test',
                 evidence_status='not-validated-by-publication', status='ratified-for-investigation',
                 execution='not-authorized'), revision-1)
        return case, intent, review

    def test_legacy_conclusion_reads_exact_old_new_cases_and_current_published_basis_without_writes(self):
        old_case, old_intent, old_review = self.legacy_case(1, 'Original front-door proposition deserves investigation.')
        new_case, new_intent, _ = self.legacy_case(2, 'Revised continuity proposition deserves investigation.')
        for id, case in [('REQ-OLD-BASIS', old_case), ('REQ-NEW-BASIS', new_case)]:
            self.store.put(id, 'requirement', SCOPE, dict(self.original['body'], intake_case=asdict(case)))
        before = self.count(); state = self.service.state()
        old = state['items']['REQ-OLD-BASIS']['business_intent_basis']
        new = state['items']['REQ-NEW-BASIS']['business_intent_basis']
        self.assertEqual(old['case_ref'], asdict(old_case)); self.assertEqual(old['published_intent_ref'], asdict(old_intent))
        self.assertEqual(old['reviews'][0]['ref'], asdict(old_review)); self.assertEqual(old['review_disposition'], 'ready-for-investigation')
        self.assertEqual(old['source_draft_ref']['revision'], 1); self.assertFalse(old['source_current'])
        self.assertNotIn('Revised', old['value_proposition'])
        self.assertEqual(new['case_ref'], asdict(new_case)); self.assertEqual(new['published_intent_ref'], asdict(new_intent))
        self.assertTrue(new['source_current']); self.assertIn('Revised', state['business_intent_basis']['value_proposition'])
        self.assertIn('Enacted local walkthrough', old['walkthrough_limitation'])
        self.assertEqual(new['published_intent_status']['execution'], 'not-authorized')
        self.assertEqual(state['items']['REQ-OLD-BASIS']['uses']['investigation']['status'], 'not-assessed')
        self.assertEqual(self.count(), before)

    def test_legacy_projection_excludes_private_analysis_draft_and_review_bodies_for_every_role(self):
        case, _, _ = self.legacy_case(1, 'A shared historical business conclusion.')
        self.store.put('PRIVATE-DRAFT', 'intake-draft', 'intake:sponsor', dict(secret='PRIVATE-DRAFT-SECRET'))
        self.store.put('PRIVATE-CHANGE', 'intake-change-review', 'intake:sponsor', dict(secret='PRIVATE-ANALYSIS-SECRET', score=98))
        self.store.put('REQ-LEGACY', 'requirement', SCOPE, dict(self.original['body'], intake_case=asdict(case)))
        for actor in ['sam', 'priya']:
            out = Workspace(self.store, actor).requirement_assessments.state()
            encoded = json.dumps(out)
            self.assertNotIn('PRIVATE-DRAFT-SECRET', encoded); self.assertNotIn('PRIVATE-ANALYSIS-SECRET', encoded)
            self.assertNotIn('"score"', encoded)
        original_case = self.store.read(case, {SCOPE})
        private_review = self.store.put('PRIVATE-REVIEW', 'intake-assessment', 'intake:sponsor',
            dict(actor='sam', disposition='ready-for-investigation', rationale='PRIVATE-REVIEW-SECRET',
                 snapshot_fingerprint=fingerprint(original_case['body']['snapshot'])))
        body = deepcopy(original_case['body']); body['reviews']['sam'] = asdict(private_review)
        inaccessible = self.store.put('OTHER-CASE', 'intake-case', SCOPE, body)
        out = self.service.business_intent_basis(asdict(inaccessible))
        self.assertIsNone(out['review_disposition']); self.assertFalse(out['review_basis_complete'])
        self.assertNotIn('PRIVATE-REVIEW-SECRET', json.dumps(out))

    def test_legacy_review_fingerprint_must_match_exact_snapshot_and_shared_case_is_required(self):
        case, _, review = self.legacy_case(1, 'Original shared proposition.')
        original = self.store.read(case, {SCOPE})
        changed = deepcopy(original['body']); changed['snapshot']['values']['value'] = 'A different snapshot borrowing old responses.'
        other = self.store.put('MISMATCHED-CASE', 'intake-case', SCOPE, changed)
        basis = self.service.business_intent_basis(asdict(other))
        self.assertIsNone(basis['review_disposition']); self.assertIsNone(basis['published_intent_ref'])
        self.assertEqual(basis['reviews'], [])
        private = self.store.put('PRIVATE-CASE', 'intake-case', 'intake:sponsor', original['body'])
        self.assertIsNone(self.service.business_intent_basis(asdict(private)))


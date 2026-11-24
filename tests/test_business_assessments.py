"""Native two-pass Business Intent contracts using test doubles only."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench.intake import PRIVATE
from workbench.model_provider import ModelUnavailable
from workbench.workspace import Workspace
from workbench.business_assessments import (standard, standard_ref, DIMENSIONS, validate_confidence,
    INVENTORY_KIND, ASSESSMENT_KIND)
from workbench.source_passages import passage_citations
from test_intake import VALUE


def confidence(claim, ids=(), level='low'):
    return dict(framework='evidence-reasoning-v1', standard=standard_ref(), level=level,
        claim=claim, scope='Business intake basis for a bounded synthetic investigation',
        rationale='The selected account is relevant but does not establish population effects or causal benefit.',
        limits='No runtime behavior or measured business outcome is established.',
        patterns=dict(status='single-line' if ids else 'unknown',families=[dict(key='account-one',passage_ids=list(ids),relationship='unknown',rationale='The selected account has no established independent corroboration.')] if ids else [],recurrence='One account is supplied; recurrence is not established.',exceptions='Negative cases were not systematically collected.',population_limits='The population, sampling method and denominator are unknown.'),
        dimensions={key:dict(judgment='limited', rationale='The available material leaves this dimension uncertain.',
            passage_ids=list(ids), limits='The supplied scope and method do not justify a stronger conclusion.') for key in DIMENSIONS})


class TwoPassModel:
    def __init__(self):
        self.calls = []; self.outputs = []; self.mutate = None; self.fail_rating = False; self.bad_inventory = False
        self.alter = None; self.store = None

    def status(self):
        return dict(configured=True, provider='Offline test double', model='synthetic-only')

    def generate(self, *, instructions, context, schema):
        self.calls.append(dict(context=deepcopy(context), schema=deepcopy(schema), instructions=instructions))
        values = context['values']
        if context['assessment_phase'] == 'inventory':
            out = dict(summary='Inventory the stated need and preserve the other answers as context.', scope_limit='',
                claims=[dict(key='need', field='need', quote='Invented span' if self.bad_inventory else values['need'],
                    meaning='People may lose progress when seeking assistance.', kind='problem',
                    materiality='Loss of progress may require repeated work.', required_evidence_level='observed')],
                uncovered_fields=[dict(field=k, reason='Retained as contextual input rather than a separate material claim in this bounded inquiry.') for k in values if k!='need'])
        else:
            assert self.store.read(Ref(**context['frozen_inventory']['ref']), {PRIVATE})['kind'] == INVENTORY_KIND
            ids = [context['sources'][0]['passages'][0]['id']] if context['sources'] else []
            claim = context['frozen_inventory']['claims'][0]
            out = dict(summary='The stated need deserves investigation; this is not measured benefit.',
                claim_assessments=[dict(key='need', judgment='partial',
                    rationale='The account reports difficulty but does not establish its prevalence or causal mechanism.',
                    completeness=dict(status='complete', rationale='The situated claim and its limits are explicitly represented.'),
                    evidence=[dict(passage_id=id, level='documentary') for id in ids], confidence=confidence(claim['meaning'], ids))],
                completeness=dict(status='partial', rationale='The value mechanism still needs a disconfirming test.', missing_parts=['Specify a test of the proposed benefit.']),
                confidence=confidence('The current Business Intent argument', ids), requirement_links=[dict(
                    target=t['id'], claim_keys=['need'], relationship='depends-on',
                    rationale='This candidate depends on whether the stated need holds in context.',
                    limits='The proposed requirement has not been independently verified.', assessment_scope='business-intake-basis',
                    business_basis_confidence=confidence(t['text'], ids), completeness=dict(status='partial',
                        rationale='The failure boundary needs clearer acceptance wording.', gaps=['Clarify the failure boundary.'])) for t in context['requirement_targets']],
                conclusion='investigate', next_action='Observe interruptions and test an alternative explanation.',
                limits='Selected accounts are not an independent population estimate or implementation permission.')
            if self.fail_rating:
                out['claim_assessments'] = []
            if self.alter:
                self.alter(out, context)
            if self.mutate:
                self.mutate()
        self.outputs.append(deepcopy(out))
        return dict(output=out, model='synthetic-only', usage=dict(input_tokens=4, output_tokens=4))


class BusinessAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(':memory:'); self.addCleanup(self.store.close)
        self.model = TwoPassModel(); self.model.store = self.store
        self.w = Workspace(self.store, 'priya', self.model)
        self.w.command('intake-start', dict(title='Synthetic continuity inquiry'))
        self.w.command('intake-save', dict(expected=self.ref(), step='value', **VALUE))
        self.source = self.w.command('intake-source', dict(title='Selected interview account',
            text='One person reported losing their place after requesting help. This is a single account, not a prevalence estimate.', role='evidence'))['ref']

    def ref(self):
        return asdict(self.w.intake.draft()['ref'])

    def assess(self, **changes):
        payload = dict(expected=self.ref(), skill='assess-business', field='value',
            message='Assess the saved Business Intent argument against its actual evidence.', sources=[self.source], consent=True)
        payload.update(changes)
        return self.w.command('intake-coach', payload)

    def records(self, kind):
        return self.w.coaching.records(kind)

    def test_native_command_freezes_inventory_before_grade_and_never_edits_or_approves(self):
        before = deepcopy(self.w.intake.draft()); result = self.assess()
        self.assertEqual(len(self.model.calls), 2)
        self.assertEqual([c['context']['assessment_phase'] for c in self.model.calls], ['inventory','rating'])
        inventory = self.store.read(Ref(**result['inventory_ref']), {PRIVATE})
        assessment = self.store.read(Ref(**result['ref']), {PRIVATE})
        self.assertEqual(inventory['kind'], INVENTORY_KIND); self.assertEqual(assessment['kind'], ASSESSMENT_KIND)
        self.assertEqual(assessment['body']['inventory'], result['inventory_ref'])
        self.assertEqual(assessment['body']['assessor_type'], 'model'); self.assertEqual(assessment['body']['mode'], 'simulated')
        self.assertEqual(assessment['body']['output']['confidence']['level'], 'low')
        self.assertEqual(self.w.intake.draft(), before); self.assertIsNone(self.w.intake.latest('INT-001'))
        self.assertFalse(self.w.loop.history())
        self.assertEqual(len(self.records('agent-execution')), 2)
        self.assertTrue(all(r['body']['status']=='succeeded' for r in self.records('agent-execution')))

    def test_invalid_inventory_is_not_frozen_and_second_call_never_runs(self):
        self.model.bad_inventory = True
        with self.assertRaises(ModelUnavailable): self.assess()
        self.assertEqual(len(self.model.calls), 1)
        self.assertEqual(self.records(INVENTORY_KIND), []); self.assertEqual(self.records(ASSESSMENT_KIND), [])

    def test_failed_rating_retains_inventory_and_failure_receipt_without_substitute_rating(self):
        self.model.fail_rating = True
        with self.assertRaises(ModelUnavailable): self.assess()
        self.assertEqual(len(self.records(INVENTORY_KIND)), 1); self.assertEqual(self.records(ASSESSMENT_KIND), [])
        self.assertEqual(self.records('agent-execution')[-1]['body']['status'], 'failed')

    def test_draft_change_during_second_call_cannot_persist_a_current_rating(self):
        self.model.mutate = lambda: self.w.intake.save(dict(expected=self.ref(), step='value', need='A newly edited need changes the argument.'))
        with self.assertRaises(StaleBasis): self.assess()
        self.assertEqual(len(self.records(INVENTORY_KIND)), 1); self.assertEqual(self.records(ASSESSMENT_KIND), [])

    def test_fabricated_passage_runtime_upgrade_and_omitted_claim_fail_contract(self):
        cases = [lambda out,ctx: out['claim_assessments'][0]['evidence'][0].update(passage_id='NOT-SUPPLIED'),
                 lambda out,ctx: out['claim_assessments'][0]['evidence'][0].update(level='runtime'),
                 lambda out,ctx: out['claim_assessments'][0].update(key='OMITTED-CLAIM')]
        for mutation in cases:
            self.model.alter = mutation
            with self.assertRaises(ModelUnavailable): self.assess()
            self.assertEqual(self.records(ASSESSMENT_KIND), [])

    def test_no_source_count_score_or_polished_logic_can_supply_high_confidence(self):
        self.model.alter = lambda out,ctx: out['confidence'].update(level='high')
        with self.assertRaises(ModelUnavailable): self.assess()
        self.assertEqual(self.records(ASSESSMENT_KIND), [])
        self.model.alter = None
        duplicate = self.w.command('intake-source', dict(title='A duplicate synthesis',text='One person reported losing their place after requesting help. This is a single account, not a prevalence estimate.',role='evidence'))['ref']
        result = self.assess(sources=[self.source,duplicate])
        self.assertEqual(self.store.read(Ref(**result['ref']), {PRIVATE})['body']['output']['confidence']['level'],'low')

    def test_common_contract_rejects_averaging_away_contradiction_and_unrated_is_distinct(self):
        raw = confidence('A scoped claim')
        self.assertEqual(validate_confidence(raw, {})['level'], 'low')
        raw['level'] = 'not-rated'; self.assertEqual(validate_confidence(raw, {})['level'], 'not-rated')
        raw['level'] = 'moderate'; raw['dimensions']['counterevidence']['judgment'] = 'contradicted'
        with self.assertRaises(ModelUnavailable): validate_confidence(raw, {})

    def test_pattern_families_trace_independence_without_duplicate_passage_corroboration(self):
        catalog = {'P1':dict(quote='A single underlying interview account.'),
                   'P2':dict(quote='A single underlying interview account.')}
        raw = confidence('The stated need may recur', ['P1'])
        raw['patterns'].update(status='independently-corroborated', families=[
            dict(key='interview',passage_ids=['P1'],relationship='independent',rationale='The interview is the original account.'),
            dict(key='synthesis',passage_ids=['P2'],relationship='independent',rationale='The synthesis repeats that interview account.')])
        with self.assertRaises(ModelUnavailable): validate_confidence(raw, catalog)
        raw['patterns']['status'] = 'single-line'; raw['patterns']['families'][1]['relationship'] = 'same-underlying-basis'
        result = validate_confidence(raw, catalog)
        self.assertEqual(result['level'], 'low')
        self.assertEqual(result['patterns']['families'][1]['relationship'], 'same-underlying-basis')
        self.assertEqual(result['patterns']['families'][0]['citations'][0]['quote'], catalog['P1']['quote'])

    def test_private_state_does_not_disclose_to_other_roles_or_write_on_read(self):
        self.assess(); before = self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        state = self.w.coaching.business_assessments.state()
        self.assertTrue(state['current_is_fresh']); self.assertEqual(state['current']['body']['output']['confidence']['level'], 'low')
        other = Workspace(self.store, 'sam', self.model)
        self.assertIsNone(other.coaching.business_assessments.state())
        self.assertNotIn('business_assessments', other.coaching.state())
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0], before)
        with self.assertRaises(PermissionError): other.command('intake-coach', dict(skill='assess-business', consent=True, expected=self.ref(), message='Assess it', sources=[]))

    def test_preview_releases_only_explicit_verified_excerpt_mappings_with_relocated_offsets(self):
        result = self.assess(); service = self.w.coaching.business_assessments
        preview = service.snapshot_for_publication(self.w.intake.draft(), result['ref'])
        self.assertEqual(len(preview['source_excerpt_manifest']), 1)
        entry = preview['source_excerpt_manifest'][0]
        quote = entry['passages'][0]['quote']
        shared = self.store.put('PUBLIC-EXCERPTS', 'source', SCOPE, dict(
            title='Explicitly selected public passages', source_version=self.source, text='Released passage:\n'+quote))
        release = dict(id='BUSINESS-RELEASE', revision=1)
        with self.assertRaises(ValueError): service.public_snapshot(preview, {}, release)
        public = service.public_snapshot(preview, {Ref(**self.source).label():asdict(shared)}, release)
        encoded = json.dumps(public)
        self.assertNotIn(result['ref']['id'], encoded); self.assertNotIn(result['inventory_ref']['id'], encoded)
        self.assertNotIn(self.source['id'], encoded)
        citation = public['assessment']['claim_assessments'][0]['evidence'][0]
        text = self.store.read(shared, {SCOPE})['body']['text']
        self.assertEqual(text[citation['start']:citation['end']], quote)
        self.assertEqual(citation['source_ref'], asdict(shared)); self.assertEqual(public['assessment_ref'], release)

    def test_stale_sources_cannot_be_released_and_old_records_remain_immutable(self):
        result = self.assess(); original = deepcopy(self.records(ASSESSMENT_KIND)[0])
        source = self.store.read(Ref(**self.source), {PRIVATE})
        self.store.put(source['ref'].id, 'intake-source', PRIVATE, dict(source['body'], text='Changed source basis.'), source['ref'].revision)
        self.assertFalse(self.w.coaching.business_assessments.state()['current_is_fresh'])
        with self.assertRaises(StaleBasis): self.w.coaching.business_assessments.snapshot_for_publication(self.w.intake.draft(), result['ref'])
        self.assertEqual(self.records(ASSESSMENT_KIND)[0], original)

    def test_requirement_targets_are_frozen_and_receive_separate_business_basis_not_global_grade(self):
        draft = self.w.intake.draft(); body = deepcopy(draft['body'])
        body['scaffold'] = [dict(key='continuity', label='Continuity', included=True, children=[],
            requirements=[dict(id='REQ-INTAKE-continuity', title='Keep draft state', requirement='Retain saved values after interruption.',
                               acceptance_criteria='Resuming shows the saved values.', included=True)])]
        self.store.put(draft['ref'].id, 'intake-draft', PRIVATE, body, draft['ref'].revision)
        result = self.assess(); inventory = self.store.read(Ref(**result['inventory_ref']), {PRIVATE})['body']
        self.assertEqual(inventory['requirement_targets'][0]['id'], 'REQ-INTAKE-continuity')
        output = self.store.read(Ref(**result['ref']), {PRIVATE})['body']['output']
        link = output['requirement_links'][0]
        self.assertEqual(link['assessment_scope'], 'business-intake-basis'); self.assertEqual(link['completeness']['status'], 'partial')
        self.assertNotEqual(link['business_basis_confidence']['claim'], output['confidence']['claim'])
        self.assertEqual(link['claim_keys'], ['need']); self.assertEqual(link['business_basis_confidence']['level'], 'low')

    def target_guard_fixture(self):
        draft = self.w.intake.draft(); body = deepcopy(draft['body'])
        body['scaffold'] = [dict(key='continuity', label='Continuity', included=True, children=[],
            requirements=[dict(id='REQ-INTAKE-continuity', title='Keep draft state', requirement='Retain saved values after interruption.',
                acceptance_criteria='Resuming shows the saved values.', included=True)])]
        self.store.put(draft['ref'].id, 'intake-draft', PRIVATE, body, draft['ref'].revision)
        self.assess()
        context = self.model.calls[-1]['context']; raw = deepcopy(self.model.outputs[-1])
        inventory = deepcopy(context['frozen_inventory']); inventory['claims'][0]['required_evidence_level'] = 'documentary'
        raw['claim_assessments'][0]['judgment'] = 'supported'
        catalog = passage_citations(context['sources']); targets = deepcopy(context['requirement_targets'])
        return raw, inventory, catalog, targets

    def validate_target_fixture(self, fixture):
        raw, inventory, catalog, targets = fixture
        return self.w.coaching.business_assessments._rating_output(raw, inventory, catalog,
            {source['source_ref']['id']:'documentary' for source in catalog.values()}, targets)

    @staticmethod
    def strong_target(raw, level='moderate'):
        target = raw['requirement_links'][0]['business_basis_confidence']; target['level'] = level
        for value in target['dimensions'].values(): value['judgment'] = 'adequate'

    def test_target_confidence_cannot_substitute_whole_business_or_other_target_claim(self):
        fixture = self.target_guard_fixture()
        for wrong in ['The current Business Intent argument', 'A different candidate requirement.']:
            candidate = deepcopy(fixture); candidate[0]['requirement_links'][0]['business_basis_confidence']['claim'] = wrong
            with self.assertRaises(ModelUnavailable): self.validate_target_fixture(candidate)
        # Preserve the full frozen text even when it exceeds the usual common claim length.
        long = deepcopy(fixture); exact = long[3][0]['text'] + ' Preserve the original recorded content.'*30
        long[3][0]['text'] = exact; long[0]['requirement_links'][0]['business_basis_confidence']['claim'] = exact
        self.assertEqual(self.validate_target_fixture(long)['requirement_links'][0]['business_basis_confidence']['claim'], exact)
        long[0]['requirement_links'][0]['business_basis_confidence']['claim'] = exact[:800]
        with self.assertRaises(ModelUnavailable): self.validate_target_fixture(long)

    def test_strong_target_confidence_rejects_absent_support_and_linked_material_contradiction(self):
        fixture = self.target_guard_fixture(); self.strong_target(fixture[0])
        self.assertEqual(self.validate_target_fixture(fixture)['requirement_links'][0]['business_basis_confidence']['level'], 'moderate')
        missing = deepcopy(fixture); missing[0]['claim_assessments'][0]['judgment'] = 'partial'
        with self.assertRaises(ModelUnavailable): self.validate_target_fixture(missing)
        contradicted = deepcopy(fixture)
        claim = deepcopy(contradicted[1]['claims'][0]); claim.update(key='counter', meaning='An alternative explanation may challenge this intervention.')
        contradicted[1]['claims'].append(claim)
        result = deepcopy(contradicted[0]['claim_assessments'][0]); result.update(key='counter', judgment='contradicted')
        result['confidence']['claim'] = claim['meaning']; contradicted[0]['claim_assessments'].append(result)
        contradicted[0]['requirement_links'][0]['claim_keys'].append('counter')
        with self.assertRaises(ModelUnavailable): self.validate_target_fixture(contradicted)

    def test_high_target_confidence_rejects_partial_material_basis_and_scoped_inventory_but_low_can_inquire(self):
        fixture = self.target_guard_fixture(); self.strong_target(fixture[0], 'high')
        claim = deepcopy(fixture[1]['claims'][0]); claim.update(key='limit', meaning='The boundary condition still needs investigation.')
        fixture[1]['claims'].append(claim)
        result = deepcopy(fixture[0]['claim_assessments'][0]); result.update(key='limit', judgment='partial')
        result['confidence']['claim'] = claim['meaning']; fixture[0]['claim_assessments'].append(result)
        fixture[0]['requirement_links'][0]['claim_keys'].append('limit')
        with self.assertRaises(ModelUnavailable): self.validate_target_fixture(fixture)
        limited = self.target_guard_fixture(); limited[1]['scope_limit'] = 'This inventory covers only part of the candidate target.'
        self.strong_target(limited[0])
        with self.assertRaises(ModelUnavailable): self.validate_target_fixture(limited)
        limited[0]['requirement_links'][0]['business_basis_confidence']['level'] = 'low'
        limited[0]['claim_assessments'][0]['judgment'] = 'partial'
        self.assertEqual(self.validate_target_fixture(limited)['requirement_links'][0]['business_basis_confidence']['level'], 'low')


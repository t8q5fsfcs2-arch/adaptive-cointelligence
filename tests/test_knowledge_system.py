"""D014 revision 2: components, typed relationships, differences, packet types, coverage,
provisional suggestions and the check-before-acting gate. Synthetic data, no model calls."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest

import test_knowledge_cards as cards_fixture
import test_assessment_context as delivery_fixture
from workbench.core import Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench import knowledge_components as kc
from workbench.knowledge_structure import differences, packet_contents, structure_check
from workbench.domain_submission import valid_scoped_assessment, SCOPED_ASSESSMENT, schema as review_schema


def shared_card(store, cid, domain, target, conditions, relation='supports', block_type='finding', target_revision=1, fields=None):
    body = dict(title=cid, type=block_type, statement='Most who missed already knew in advance.', rationale='',
                fields=fields or {}, relations=[dict(relation=relation, ref=dict(id=target, revision=target_revision),
                                                     rationale='Bears on it.', conditions=conditions)],
                evidence=[], owner='sam', domain=domain, domain_label=domain, status='shared-for-review')
    return store.put(cid, 'knowledge-card', SCOPE, body)



class CardsBase(unittest.TestCase):
    """Borrow the building-block fixture without re-running its tests."""
    _K = vars(cards_fixture.KnowledgeCardTests)
    setUp = _K['setUp']; tearDown = _K['tearDown']
    start = _K['start']; current = _K['current']; save = _K['save']; relation = _K['relation']
    submission = _K['submission']; prepare = _K['prepare']; publish = _K['publish']
    del _K


class ComponentsTests(unittest.TestCase):
    def test_component_set_is_fixed_and_every_type_has_a_recipe(self):
        data = deepcopy(kc.config())
        self.assertEqual(tuple(data['components']), kc.COMPONENT_ORDER)
        data['components']['mood'] = dict(label='Mood', holds='Feelings')
        with self.assertRaisesRegex(ValueError, 'fixed by D014'):
            kc.validate(data)
        data = deepcopy(kc.config()); data['recipes'].pop('finding')
        with self.assertRaisesRegex(ValueError, 'recipe'):
            kc.validate(data)

    def test_components_are_read_from_block_fields_and_recipe_gaps_reported(self):
        record = dict(kind='domain-implication', body=dict(owner='sam', status='held', payload=dict(statement='Most knew in advance.', evidence=[]),
                      card=dict(type='finding', fields=dict(applies_people='Shift workers', scope='After 5 pm'), relations=[])))
        self.assertEqual(kc.components_of(record), ['actor', 'situation', 'claim', 'owner', 'status'])
        self.assertEqual(kc.missing_for_recipe(record), ['basis', 'strength', 'time'])
        self.assertEqual(kc.suggested_conditions(record), 'Shift workers; After 5 pm')
        self.assertEqual(kc.link_use('finding'), 'evidence')
        self.assertEqual(kc.link_use('design-decision'), 'direction')

    def test_eligibility_needs_components_relation_and_family_and_counts_only_when_validated(self):
        base = dict(kind='domain-implication', body=dict(owner='sam', status='held', evidence_review=dict(support={}),
                    payload=dict(statement='Most knew in advance.', evidence=[]),
                    card=dict(type='finding', fields=dict(applies_people='Shift workers', scope='After 5 pm'), relations=[])))
        ok = kc.eligibility(base, 'supports', 'needs')
        self.assertTrue(ok['eligible']); self.assertTrue(ok['counts'])
        suggested = deepcopy(base); suggested['body']['status'] = 'suggested'
        pending = kc.eligibility(suggested, 'supports', 'needs')
        self.assertTrue(pending['eligible']); self.assertFalse(pending['counts']); self.assertIn('once validated', pending['coaching'])
        thin = deepcopy(base); thin['body']['card']['fields'] = {}; thin['body'].pop('evidence_review')
        gap = kc.eligibility(thin, 'supports', 'needs')
        self.assertFalse(gap['eligible']); self.assertEqual(gap['missing'], ['actor', 'situation', 'strength'])
        self.assertIn('who it is about', gap['coaching'])
        self.assertFalse(kc.eligibility(base, 'challenges', 'needs')['eligible'])
        self.assertFalse(kc.eligibility(base, 'supports', 'technology')['family_ok'])

    def test_requirement_area_from_identity_or_drawer_label(self):
        drawers = kc.drawers([])
        self.assertEqual(kc.area_of(dict(ref=Ref('REQ-INTAKE-needs/jobs', 1), body={}), drawers), 'needs')
        self.assertEqual(kc.area_of(dict(ref=Ref('REQ-9', 1), body=dict(drawer='Customer and user needs / User groups and jobs')), drawers), 'needs')
        self.assertEqual(kc.area_of(dict(ref=Ref('REQ-8', 1), body=dict(drawer='Accessibility')), drawers), 'experience')
        self.assertIsNone(kc.area_of(dict(ref=Ref('REQ-7', 1), body=dict(drawer='Unknown')), drawers))


class RelationshipAndPublicationTests(CardsBase):
    def test_links_are_written_with_the_record_and_backfill_is_idempotent(self):
        t = self.start(); a = self.save(self.sam, t, type='user-situation', fields={'people': 'Shift workers'})
        b = self.save(self.sam, t, relations=[self.relation(a['ref'])])
        rows = [r for r in self.store.relationships(self.sam.scopes) if r['from_id'] == b['ref'].id]
        self.assertEqual([(r['to_id'], r['relation'], r['use'], r['conditions']) for r in rows],
                         [(a['ref'].id, 'applies-to', 'evidence', 'For the stated shift handoff.')])
        self.store.db.execute('DELETE FROM relationships'); self.store.db.execute('DELETE FROM relationship_index'); self.store.db.commit()
        self.assertGreater(self.store.backfill_relationships(), 0)
        self.assertEqual(self.store.backfill_relationships(), 0)
        self.assertEqual(len([r for r in self.store.relationships(self.sam.scopes) if r['from_id'] == b['ref'].id]), 1)
        self.assertEqual([r for r in self.store.relationships({SCOPE}) if r['from_id'] == b['ref'].id], [])

    def test_catalogue_shows_components_and_suggested_conditions(self):
        t = self.start(); r = self.save(self.sam, t, fields={'scope': 'After 5 pm', 'applies_people': 'Shift workers'})
        meta = next(v for v in self.sam.cards.state([])['catalogue'] if v['ref'] == asdict(r['ref']))
        self.assertIn('actor', meta['system']['components']); self.assertEqual(meta['system']['suggested_conditions'], 'Shift workers; After 5 pm')

    def test_publication_validates_provisional_suggestions_only_when_accepted(self):
        t = self.start(); r = self.save(self.sam, t, status='suggested', title='AI suggested finding')
        self.submission(self.sam, t, [r]); h, d = self.prepare(self.sam, t)
        with self.assertRaisesRegex(PermissionError, 'Accept the AI suggestions'):
            self.publish(self.sam, h, d)
        self.assertEqual(self.store.latest(r['ref'].id, self.sam.scopes)['body']['status'], 'suggested')
        out = self.sam.command('domain-publish', dict(expected=asdict(d['ref']), preflight=asdict(h['ref']), confirm=True, accept_suggestions=True))
        validated = self.store.latest(r['ref'].id, self.sam.scopes)['body']
        self.assertEqual(validated['status'], 'held'); self.assertEqual(validated['validated']['through'], 'publication')
        packet = self.store.resolve_packet(**out['packet'], allowed_scopes={SCOPE})
        self.assertEqual(len([x for x in packet['records'] if x['kind'] == 'knowledge-card']), 1)

    def test_dismissed_blocks_still_cannot_be_selected(self):
        t = self.start(); r = self.save(self.sam, t, status='dismissed')
        with self.assertRaisesRegex(ValueError, 'dismissed'):
            self.submission(self.sam, t, [r])


class StructureTests(CardsBase):
    def test_differences_are_detected_by_kind_and_never_decided(self):
        target = self.store.put('SHARED-FIND-1', 'knowledge-card', SCOPE, dict(title='Most knew in advance', type='finding', statement='x', relations=[], evidence=[], domain='Research'))
        shared_card(self.store, 'SHARED-R', 'Research', target.id, 'Shift workers')
        shared_card(self.store, 'SHARED-D', 'Design', target.id, 'All patients', relation='informs', block_type='design-decision')
        found = differences(self.store, self.lee.latest_records(), {SCOPE})
        item = next(f for f in found if f['target']['id'] == target.id)
        self.assertEqual(item['kinds'], ['scope-differs', 'relation-differs', 'use-differs'])
        self.assertIn('check applicability', item['messages'][0])
        self.assertIn('reviewer judges', item['next'])
        self.assertNotIn('conflict', json.dumps(item).lower())

    def test_revision_skew_and_one_sided_scope_are_reported(self):
        target = self.store.put('SHARED-EVAL', 'knowledge-card', SCOPE, dict(title='Evaluation', type='evaluation-result', statement='5 of 6', relations=[], evidence=[], domain='Design'))
        self.store.put('SHARED-EVAL', 'knowledge-card', SCOPE, dict(title='Evaluation', type='evaluation-result', statement='4 of 5', relations=[], evidence=[], domain='Design'), 1)
        shared_card(self.store, 'SHARED-X', 'Research', target.id, '', target_revision=2)
        shared_card(self.store, 'SHARED-Y', 'Design', target.id, 'All patients', target_revision=1)
        item = next(f for f in differences(self.store, self.lee.latest_records(), {SCOPE}) if f['target']['id'] == target.id)
        self.assertIn('scope-stated-by-one-group', item['kinds']); self.assertIn('revision-skew', item['kinds'])

    def test_structure_check_reports_challenge_reach_and_category_gaps(self):
        req = self.store.put('REQ-NEEDS', 'requirement', SCOPE, dict(title='Reschedule without phoning', text='x', status='approved', drawer='Customer and user needs / User groups and jobs'))
        thin = shared_card(self.store, 'SHARED-THIN', 'Research', req.id, 'Shift workers')
        self.store.put('ISSUE-T', 'bridge-issue', SCOPE, dict(kind='challenge', status='open', title='Survey challenges it', target=dict(id=req.id, revision=1), basis=[], requirement_refs=[]))
        records = self.lee.latest_records()
        result = structure_check(self.store, records, [], kc.drawers(records), {SCOPE})
        reach = next(r for r in result['challenge_reach'] if r['issue']['id'] == 'ISSUE-T')
        self.assertIn(thin.id, [d['id'] for d in reach['dependents']])
        gap = next(g for g in result['category_gaps'] if g['requirement']['id'] == req.id)
        self.assertEqual(gap['area'], 'needs'); self.assertIn('actor', gap['missing'])
        self.assertIn('does not decide', result['boundary'])

    def test_packet_type_contents_follow_relations_for_the_audience(self):
        req = self.store.put('REQ-PKT', 'requirement', SCOPE, dict(title='R', text='x', status='approved', drawer='Experience and usability'))
        card = shared_card(self.store, 'SHARED-P', 'Design', req.id, 'All patients', relation='supports')
        out = self.lee.command('packet-type-preview', dict(type='design-review', anchor=asdict(req)))
        self.assertIn(dict(id=card.id, revision=1), out['preview']['refs'])
        self.assertEqual(out['preview']['revision_policy'], 'pinned')
        with self.assertRaisesRegex(ValueError, 'starts from'):
            packet_contents(self.store, 'engineering-handoff', card, {SCOPE})


class GateTests(unittest.TestCase):
    setUp = delivery_fixture.AssessmentContextTests.setUp
    prepare = delivery_fixture.AssessmentContextTests.prepare
    draft = delivery_fixture.AssessmentContextTests.draft

    def test_export_rechecks_basis_and_asks_to_acknowledge_open_challenges(self):
        from workbench.workspace import Workspace
        draft = self.draft(); staged = Workspace(self.store, 'priya')
        self.store.put('ISSUE-GATE', 'bridge-issue', SCOPE, dict(kind='challenge', status='open', title='New survey challenges this',
                       target=asdict(self.f.req), basis=[], requirement_refs=[]))
        with self.assertRaisesRegex(ValueError, 'Acknowledge'):
            staged.command('delivery-export', {'expected': asdict(draft['ref'])})
        out = staged.command('delivery-export', {'expected': asdict(draft['ref']), 'acknowledge_open_issues': True})
        self.assertEqual(out['gate']['notices'][0]['title'], 'New survey challenges this')
        self.assertEqual(out['gate']['blockers'], [])


class ScopedAssessmentTests(unittest.TestCase):
    def test_scoped_assessment_is_optional_and_validated(self):
        result = review_schema({})
        self.assertIn('scoped_assessment', result['properties']); self.assertNotIn('scoped_assessment', result['required'])
        good = dict(scope_check='The basis covers shift workers only.', basis_check='Nine of twelve interviews.', contradictions='',
                    assessment='Supported for shift workers; not for all patients.', recommendation_confidence='moderate', reasons=['Small sample.'])
        valid_scoped_assessment(good)
        with self.assertRaises(ValueError):
            valid_scoped_assessment({**good, 'recommendation_confidence': 'certain'})
        self.assertEqual(set(SCOPED_ASSESSMENT['properties']), set(good))


if __name__ == '__main__':
    unittest.main()

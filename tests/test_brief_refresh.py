"""Offline brief refresh preserves history and the existing publication gates."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest

import test_design_brief as fixture
from brief_fixture import complete_design_brief
from workbench.core import StaleBasis
from workbench.decisions import SCOPE


class BriefRefreshTests(unittest.TestCase):
    setUp = fixture.DesignBriefTests.setUp
    tearDown = fixture.DesignBriefTests.tearDown
    seed = fixture.DesignBriefTests.seed
    generate = fixture.DesignBriefTests.generate

    def change_research(self):
        old = self.store.latest('PUB-RESEARCH', {SCOPE})
        return self.store.put(old['ref'].id, old['kind'], SCOPE,
                              {**old['body'], 'limitation': 'New evidence leaves acknowledgement coverage uncertain.'},
                              old['ref'].revision)

    def apply_refresh(self, plan):
        preview = self.design.command('domain-brief-refresh-preview', dict(expected=asdict(plan['ref'])))
        return self.design.command('domain-brief-refresh', dict(expected=preview['expected'],
                                   expected_signature=preview['signature'], confirm=True))

    def test_large_local_context_is_readable_but_model_admission_stays_bounded(self):
        self.seed()
        self.store.put('LARGE-CONTEXT', 'project-context', SCOPE, dict(text='Exact shared context. ' * 10000))
        before = self.store.db.execute('select count(*) from records').fetchone()[0]
        preview = self.design.command('domain-brief-preview', {})
        self.assertGreater(len(json.dumps(self.design.domain_brief.context(include_brief=True))), 150000)
        self.assertEqual(self.store.db.execute('select count(*) from records').fetchone()[0], before)
        result = self.design.command('domain-brief-create', {})
        plan = self.store.latest(result['id'], self.design.scopes)
        self.assertTrue(self.design.domain_brief.current(plan))
        with self.assertRaisesRegex(ValueError, 'narrower project brief'):
            self.design.command('domain-objectives-suggest', dict(consent=True, include_brief=True,
                                 expected_signature=preview['signature']))
        self.assertEqual(self.model.calls, 0)
        self.change_research()
        self.apply_refresh(plan)
        self.assertEqual(self.model.calls, 0)

    def test_refresh_retains_authored_plan_and_exact_old_quotes_without_upgrading_interpretations(self):
        self.seed(); plan = self.generate(); calls = self.model.calls
        old = deepcopy(plan); self.change_research()
        records = set(tuple(r) for r in self.store.db.execute('select * from records'))
        preview = self.design.command('domain-brief-refresh-preview', dict(expected=asdict(plan['ref'])))
        self.assertEqual(preview['changes'][0]['before']['id'], 'PUB-RESEARCH')
        result = self.apply_refresh(plan)
        saved = self.store.latest(result['id'], self.design.scopes)
        self.assertEqual(saved['ref'].revision, plan['ref'].revision + 1)
        self.assertEqual(saved['body']['output'], old['body']['output'])
        self.assertTrue(self.design.domain_brief.current(saved))
        self.assertEqual(saved['body']['status'], 'working')
        self.assertEqual(saved['body']['refresh']['previous'], asdict(plan['ref']))
        self.assertTrue(any(s.get('historical_interpretation') for s in saved['body']['brief_sections']))
        self.assertEqual(self.store.read(plan['ref'], self.design.scopes)['body'], old['body'])
        self.assertTrue(records <= set(tuple(r) for r in self.store.db.execute('select * from records')))
        self.assertEqual(self.model.calls, calls)
        # Historical interpretation alone cannot supply current coverage.
        body = deepcopy(saved['body'])
        body['brief_sections'] = [s for s in body['brief_sections'] if s['kind'] == 'requirement-implication']
        self.assertTrue(any(x.startswith('Evaluation coverage:') for x in self.design.domain_brief.missing(body)))

    def test_preview_races_confirmation_and_wrong_domain_are_rejected(self):
        self.seed(); plan = self.generate(); self.change_research()
        data = dict(expected=asdict(plan['ref']))
        preview = self.design.command('domain-brief-refresh-preview', data)
        with self.assertRaises(PermissionError):self.sam.command('domain-brief-refresh-preview', data)
        with self.assertRaises(ValueError):self.design.command('domain-brief-refresh', data)
        self.change_research()
        with self.assertRaises(StaleBasis):
            self.design.command('domain-brief-refresh', dict(**data, confirm=True, expected_signature=preview['signature']))
        self.apply_refresh(plan)
        with self.assertRaises(StaleBasis):self.design.command('domain-brief-refresh-preview', data)

    def test_refresh_requires_explicit_completion_and_fresh_preflight_before_sharing(self):
        self.seed()
        thread = self.design.domain_chat.owned(self.design.command('domain-chat-start', {})['conversation'])
        draft = self.design.domain_chat.draft(thread)
        plan = complete_design_brief(self.design, draft)
        prepared = self.design.command('domain-prepare', dict(expected=asdict(draft['ref']), recipient='bridge'))
        handoff = self.store.latest(prepared['domainHandoff'], self.design.scopes)
        policy = self.store.latest('POL-001', {SCOPE})
        self.store.put(policy['ref'].id, policy['kind'], SCOPE, {**policy['body'], 'text': 'Keep the current nonurgent boundary; no operational endorsement.'}, policy['ref'].revision)
        self.apply_refresh(plan)
        saved = self.store.latest(plan['ref'].id, self.design.scopes)
        self.assertNotIn('completed_by', saved['body'])
        self.assertEqual(saved['body']['objectives'], plan['body']['objectives'])
        self.assertEqual(saved['body']['brief_sections'], plan['body']['brief_sections'])
        with self.assertRaisesRegex(ValueError, 'Explicitly mark this brief complete'):
            self.design.command('domain-prepare', dict(expected=asdict(draft['ref']), recipient='bridge'))
        self.design.command('domain-objectives-save', dict(expected=asdict(saved['ref']),
                            objectives=saved['body']['objectives'], brief_sections=saved['body']['brief_sections'], complete=True))
        with self.assertRaises((ValueError, StaleBasis)):
            self.design.command('domain-publish', dict(expected=asdict(draft['ref']), preflight=asdict(handoff['ref']), confirm=True))
        prepared = self.design.command('domain-prepare', dict(expected=asdict(draft['ref']), recipient='bridge'))
        current = self.store.latest(prepared['domainHandoff'], self.design.scopes)
        result = self.design.command('domain-publish', dict(expected=asdict(draft['ref']), preflight=asdict(current['ref']), confirm=True))
        self.assertTrue(result['packet'])
        self.assertEqual(self.store.latest(self.req['ref'].id, {SCOPE}), self.req)
        self.assertEqual(self.model.calls, 0)


if __name__ == '__main__':unittest.main()

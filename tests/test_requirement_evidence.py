import unittest
from datetime import datetime, timedelta, timezone

from workbench.core import Ref
from workbench.requirement_evidence import evidence_level, evidence_levels

NOW = datetime(2026, 11, 22, tzinfo=timezone.utc)
RID = 'REQ-1'


def day(n):
    return (NOW - timedelta(days=n)).isoformat()


def requirement(revision=2):
    return dict(ref=Ref(RID, revision), kind='requirement', body=dict(status='approved', title='R'))


def contribution(cid, domain, revision=2, age=1, kind='contribution'):
    return dict(ref=Ref(cid, 1), kind=kind, body=dict(domain=domain, published_at=day(age),
                requirement_refs=[dict(id=RID, revision=revision)]))


def issue(iid, kind, status='open', age=1):
    return dict(ref=Ref(iid, 1), kind='bridge-issue', body=dict(kind=kind, status=status, route='requirement',
                target=dict(id=RID, revision=2), requirement_refs=[], updated_at=day(age)))


class RequirementEvidenceTest(unittest.TestCase):
    def level(self, records):
        return evidence_level(RID, 2, records, NOW)

    def test_each_level_says_what_would_raise_it_and_high_says_nothing(self):
        """D012: advice from the same facts; nothing is blocked or approved."""
        empty = evidence_level(RID, 2, [requirement()], now=NOW)
        self.assertEqual(empty['raise_to']['to'], 'low')
        one = evidence_level(RID, 2, [requirement(), contribution('C1', 'Research')], now=NOW)
        self.assertEqual((one['level'], one['raise_to']['to']), ('moderate', 'high'))
        self.assertTrue(any('2 teams' in n for n in one['raise_to']['needs']))
        old = evidence_level(RID, 2, [requirement(), contribution('C1', 'Research', revision=1)], now=NOW)
        self.assertEqual((old['level'], old['raise_to']['to']), ('low', 'moderate'))
        self.assertIn('published work that references the current version', old['raise_to']['needs'])
        high = evidence_level(RID, 2, [requirement(), contribution('C1', 'Research'), contribution('C2', 'Design')], now=NOW)
        self.assertEqual((high['level'], high['raise_to']), ('high', None))

    def test_empty_without_shared_work(self):
        result = self.level([requirement()])
        self.assertEqual(result['level'], 'empty')
        self.assertEqual(result['contributions'], 0)

    def test_high_needs_two_current_contributions_from_two_teams(self):
        result = self.level([requirement(), contribution('C1', 'Research'), contribution('C2', 'Design')])
        self.assertEqual(result['level'], 'high')
        self.assertEqual(result['current_teams'], ['Design', 'Research'])

    def test_one_team_is_moderate_and_says_what_high_needs(self):
        result = self.level([requirement(), contribution('C1', 'Research'), contribution('C2', 'Research')])
        self.assertEqual(result['level'], 'moderate')
        self.assertIn('work from 2 teams', result['reasons'][0])

    def test_open_gap_keeps_it_below_high(self):
        records = [requirement(), contribution('C1', 'Research'), contribution('C2', 'Design'), issue('I1', 'gap')]
        result = self.level(records)
        self.assertEqual(result['level'], 'moderate')
        self.assertEqual(result['open_gaps'], 1)

    def test_open_contradiction_caps_at_low_and_resolution_restores(self):
        records = [requirement(), contribution('C1', 'Research'), contribution('C2', 'Design'), issue('I1', 'conflict')]
        self.assertEqual(self.level(records)['level'], 'low')
        records[-1] = issue('I1', 'conflict', status='resolved')
        result = self.level(records)
        self.assertEqual(result['level'], 'high')
        self.assertEqual(result['resolved_issues'], 1)

    def test_evidence_only_on_an_earlier_version_is_low(self):
        result = self.level([requirement(), contribution('C1', 'Research', revision=1), contribution('C2', 'Design', revision=1)])
        self.assertEqual(result['level'], 'low')
        self.assertEqual(result['on_current'], 0)
        self.assertIn('current version', result['reasons'][0])

    def test_old_evidence_is_low(self):
        result = self.level([requirement(), contribution('C1', 'Research', age=200), contribution('C2', 'Design', age=190)])
        self.assertEqual(result['level'], 'low')

    def test_evidence_older_than_ninety_days_is_not_high(self):
        result = self.level([requirement(), contribution('C1', 'Research', age=120), contribution('C2', 'Design', age=100)])
        self.assertEqual(result['level'], 'moderate')

    def test_private_drafts_never_count(self):
        records = [requirement(), contribution('D1', 'Research', kind='contribution-draft'),
                   contribution('D2', 'Design', kind='domain-chat-turn')]
        self.assertEqual(self.level(records)['level'], 'empty')

    def test_reference_is_not_called_support(self):
        result = self.level([requirement(), contribution('C1', 'Research')])
        self.assertNotIn('support', ' '.join(result['reasons']).lower())

    def test_levels_cover_approved_and_referenced_candidates_without_mutating(self):
        candidate = dict(ref=Ref('C9', 1), kind='contribution', body=dict(domain='Design', published_at=day(1),
                         requirement_refs=[dict(id='REQ-CANDIDATE', revision=3)]))
        records = [requirement(), candidate]
        before = repr(records)
        levels = evidence_levels(records, NOW)
        self.assertEqual(set(levels), {RID, 'REQ-CANDIDATE'})
        self.assertEqual(levels['REQ-CANDIDATE']['requirement']['revision'], 3)
        self.assertEqual(levels['REQ-CANDIDATE']['level'], 'moderate')
        self.assertEqual(repr(records), before)


if __name__ == '__main__':
    unittest.main()

"""Synthetic native-path proofs for sponsor answer and decision continuity."""
from copy import deepcopy
from dataclasses import asdict
import unittest

import test_preflight_packets as fixtures
from workbench.decisions import SCOPE
from workbench.intake import PRIVATE
from workbench.sponsor import DIRECT_LEGACY, FIELDS, answer_text


class SponsorContinuityTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.PreflightPacketTests()
        self.f.setUp()
        self.store = self.f.store
        self.w, _ = self.f.sponsor()
        self.old_scope = 'Investigate a resumable cue for routine feedback.'
        self.old_fallback = 'Preserve the draft; the routing owner remains unknown.'
        self.save(answers={
            'q14': dict(items=[self.old_scope], confirmed=True, completed=True),
            'q12': dict(items=[self.old_fallback], confirmed=False),
            'q15': dict(items=['Emergency response is out of scope.']),
            'q16': dict(items=['The actual unknown-route gap is uncertain.']),
        })
        self.publish()
        self.baseline = self.w.intake.latest('INT-001')
        self.packet = self.store.read_packet('PKT-INTENT', 1, {SCOPE})

    def tearDown(self):
        self.f.tearDown()

    def ref(self):
        return asdict(self.w.intake.draft()['ref'])

    def save(self, **data):
        return self.w.command('sponsor-save', dict(expected=self.ref(), **data))

    def publish(self):
        self.w.command('intake-accept-value', dict(expected=self.ref(), confirm=True,
            rationale='Synthetic review of the proposition; evidence remains limited.'))
        self.w.command('intake-build', dict(expected=self.ref(), confirm=True))
        prepared = self.w.command('intake-preflight', dict(expected=self.ref()))
        preflight = self.w.intake.latest(prepared['id'])
        result = self.w.command('intake-request', dict(expected=self.ref(),
            preflight=asdict(preflight['ref']), confirm=True))
        for actor in ('sam', 'lee'):
            case = self.w.intake.latest(result['id'])
            self.f.workspace(actor).command('intake-review', dict(expected=asdict(case['ref']),
                disposition='ready-for-investigation', rationale='Synthetic documentary review only.'))
        case = self.w.intake.latest(result['id'])
        self.w.command('intake-publish', dict(expected=asdict(case['ref']), confirm=True,
            rationale='Synthetic direction for investigation; no operational authority.'))
        return self.w.intake.latest('INT-001')

    def request(self, field='in_scope', text='Limit the inquiry to staffed hours.'):
        research, _, draft, prepared = self.f.deliverable('sam')
        report, packet = self.f.publish(research, draft, prepared, release_sources=True)
        raised = research.command('bridge-raise', dict(title='Synthetic sponsor follow-up',
            question='Should the bounded inquiry change?', consequence='Preserve the inquiry limits.',
            kind='question', boards=['research-design'], owner='sam', route='intent',
            packet_refs=[dict(id=packet['id'], revision=packet['revision'])], requirement_refs=[]))
        issue = self.w.intake.latest(raised['id'])
        research.command('bridge-intent-propose', dict(expected_issue=asdict(issue['ref']),
            source=asdict(report['ref']), field=field, proposed_value=text,
            rationale='A synthetic published report challenges the existing direction.'))
        issue = self.w.intake.latest(issue['ref'].id)
        return self.w.intake.latest(issue['body']['linked']['ref']['id'])

    def adopt(self, request, text=None):
        self.w.command('intent-adopt', dict(expected=asdict(request['ref']), draft_expected=self.ref(),
            response=text or request['body']['proposed_value'], rationale='Take this bounded response to direction review.'))

    def test_adopted_scope_survives_native_save_preflight_and_publication(self):
        self.w.command('setup-governance-enable', dict(
            expected=asdict(self.w.intake.latest('PROJECT-001')['ref']), confirm=True))
        revised = 'Investigate only during staffed hours.\n\nThe routing owner remains unknown.'
        request = self.request(text=revised)
        self.adopt(request)
        adopted = self.w.intake.draft()
        answer = adopted['body']['sponsor_brief']['answers']['q14']
        self.assertEqual(answer_text(answer), revised)
        self.assertEqual(adopted['body']['values']['in_scope'], revised)
        self.assertFalse(answer['confirmed'])
        self.assertFalse(answer['completed'])
        self.assertFalse(answer['ai'])
        self.assertEqual(self.w.intake.latest('INT-001'), self.baseline)
        self.assertEqual(self.f.workspace('priya').sponsor.state()['brief']['answers']['q14'], answer)

        # An unrelated page save must not restore the old, previously visible answer.
        framing = deepcopy(self.w.sponsor.state()['brief']['framing'])
        framing['name'] = 'Synthetic continuity inquiry'
        self.save(framing=framing)
        displayed = deepcopy(self.w.sponsor.state()['brief']['answers']['q14'])
        self.save(answers={'q14': dict(items=displayed['items'], completed=True, confirmed=False)})
        published = self.publish()
        self.assertEqual(published['body']['intake']['in_scope'], revised)
        self.assertEqual(answer_text(published['body']['business_brief']['answers']['q14']), revised)
        self.assertEqual(published['body']['intake']['out_scope'], 'Emergency response is out of scope.')
        self.assertEqual(published['body']['intake']['scope_unknowns'], 'The actual unknown-route gap is uncertain.')
        self.assertEqual(published['body']['intake']['fallbacks'], self.old_fallback)
        self.assertEqual(published['body']['execution'], 'not-authorized')
        self.assertEqual(self.store.read(self.baseline['ref'], {SCOPE}), self.baseline)
        self.assertEqual(self.store.read_packet('PKT-INTENT', 1, {SCOPE}), self.packet)
        self.assertEqual(self.store.read(adopted['ref'], {PRIVATE}), adopted)

    def test_decline_and_defer_restore_matching_published_answers_only(self):
        for disposition in ('declined', 'deferred'):
            with self.subTest(disposition=disposition):
                request = self.request(text='Test a narrower temporary inquiry: ' + disposition)
                self.adopt(request)
                adopted = self.w.intake.draft()
                fallback = 'Retain the draft and clarify the still-unknown route: ' + disposition
                self.save(answers={'q12': dict(items=[fallback])})
                current = self.w.intake.latest(request['ref'].id)
                self.w.command('intent-dispose', dict(expected=asdict(current['ref']), draft_expected=self.ref(),
                    disposition=disposition, rationale='Retain the currently published scope.',
                    next_owner='sam', next_question='What evidence could justify a later scope change?'))
                draft = self.w.intake.draft()['body']
                self.assertEqual(draft['values']['in_scope'], self.old_scope)
                self.assertEqual(draft['sponsor_brief']['answers']['q14'],
                    self.baseline['body']['business_brief']['answers']['q14'])
                self.assertEqual(draft['values']['fallbacks'], fallback)
                self.assertEqual(draft['values']['scope_unknowns'], 'The actual unknown-route gap is uncertain.')
                self.assertEqual(self.store.read(adopted['ref'], {PRIVATE}), adopted)
                self.assertEqual(self.w.intake.latest('INT-001'), self.baseline)
                self.assertEqual(self.w.intake.latest(request['ref'].id)['body']['status'], disposition)

    def test_multiline_refinement_remains_editable_and_completable_within_answer_limits(self):
        response = '\n'.join('Synthetic condition %s: routing remains uncertain.' % n for n in range(55))
        request = self.request(text=response)
        self.adopt(request)
        displayed = deepcopy(self.w.sponsor.state()['brief']['answers']['q14'])
        self.assertEqual(answer_text(displayed), response)
        # Use the same saved item list as the actual question form. A valid
        # refinement must not manufacture more than the allowed 40 answer items.
        self.save(answers={'q14': dict(items=displayed['items'], completed=True, confirmed=False)})
        saved = self.w.intake.draft()['body']
        self.assertEqual(answer_text(saved['sponsor_brief']['answers']['q14']), response)
        self.assertEqual(saved['values']['in_scope'], response)
        self.assertTrue(saved['sponsor_brief']['answers']['q14']['completed'])
        self.assertFalse(saved['sponsor_brief']['answers']['q14']['confirmed'])
        self.assertEqual(self.w.intake.latest('INT-001'), self.baseline)

    def test_legacy_direct_bindings_update_and_restore_both_representations(self):
        for q, field in DIRECT_LEGACY.items():
            with self.subTest(question=q, field=field):
                old = self.baseline['body']['intake'][field]
                request = self.request(field=field, text='Synthetic refined wording for ' + field)
                self.adopt(request)
                body = self.w.intake.draft()['body']
                self.assertEqual(body['values'][field], request['body']['proposed_value'])
                self.assertEqual(body['values'][FIELDS[q]], request['body']['proposed_value'])
                self.assertEqual(answer_text(body['sponsor_brief']['answers'][q]), request['body']['proposed_value'])
                current = self.w.intake.latest(request['ref'].id)
                self.w.command('intent-dispose', dict(expected=asdict(current['ref']), draft_expected=self.ref(),
                    disposition='declined', rationale='Keep the original bounded question.'))
                restored = self.w.intake.draft()['body']
                self.assertEqual(restored['values'][field], old)
                self.assertEqual(restored['values'][FIELDS[q]], old)
                self.assertEqual(answer_text(restored['sponsor_brief']['answers'][q]), old)
        self.assertEqual(self.store.read(self.baseline['ref'], {SCOPE}), self.baseline)

    def test_material_sponsor_only_answers_and_cleared_answers_are_in_decision_receipt(self):
        # These answers are outside the original ALL_FIELDS scaffold inventory.
        changes = {
            'q8': ('informal_evidence', 'No independent observation yet; only a working hunch.'),
            'q10': ('must_haves', 'Retain the original report reference.'),
            'q11': ('uncertain_scenarios', 'Unknown route remains unresolved.'),
            'q12': ('fallbacks', 'Preserve input and ask the accountable role for routing clarification.'),
            'q13': ('edge_cases', 'A device can be unavailable; recovery is not yet tested.'),
            'q20': ('project_limits', 'No production deployment in this inquiry.'),
            'q21': ('project_risks', 'Routing responsibility remains uncertain.'),
            'q23': ('stakeholders', 'Sponsor and authorized requirement owner.'),
        }
        self.save(answers={q: dict(items=[text]) for q, (_, text) in changes.items()},
            fit={'investment_case': 'Illustrative cost only; no financial commitment.'})
        framing = deepcopy(self.w.sponsor.state()['brief']['framing'])
        framing['summary']['options'] = 'Compare existing-tool improvements with a new entry point.'
        self.save(framing=framing)
        published = self.publish()
        decision = self.w.intake.latest(published['body']['decision_id'])
        for q, (field, text) in changes.items():
            self.assertEqual(decision['body']['changes'][field],
                dict(before=self.baseline['body']['intake'].get(field, ''), after=text))
            self.assertEqual(answer_text(published['body']['business_brief']['answers'][q]), text)
        self.assertEqual(decision['body']['changes']['investment_case']['after'],
            'Illustrative cost only; no financial commitment.')
        self.assertIn('Compare existing-tool improvements', decision['body']['changes']['executive_summary']['after'])
        self.assertEqual(self.store.read(self.baseline['ref'], {SCOPE}), self.baseline)

        # Clearing an answer is a material change, not an omitted diff entry.
        self.save(answers={'q8': dict(items=[])})
        cleared = self.publish()
        receipt = self.w.intake.latest(cleared['body']['decision_id'])
        self.assertEqual(receipt['body']['changes']['informal_evidence'],
            dict(before=changes['q8'][1], after=''))
        self.assertEqual(self.store.read(published['ref'], {SCOPE}), published)


if __name__ == '__main__':
    unittest.main()

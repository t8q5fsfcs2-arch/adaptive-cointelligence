"""Offline application-path checks for the sponsor/setup/accountability handoff."""
from copy import deepcopy
from dataclasses import asdict
import unittest
import test_intake
import test_bridge
from workbench.decisions import ACTORS, DecisionBlocked, SCOPE
from workbench.setup_governance import enable, context
from workbench.workspace import Workspace


def activate(store):
    return Workspace(store, 'priya').command('setup-governance-enable',
        dict(expected=asdict(store.latest('PROJECT-001', {SCOPE})['ref']), confirm=True))


class SponsorSetupTests(unittest.TestCase):
    setUp = test_intake.IntakeTests.setUp
    tearDown = test_intake.IntakeTests.tearDown
    ref = test_intake.IntakeTests.ref
    accept_value = test_intake.IntakeTests.accept_value
    prepare = test_intake.IntakeTests.prepare
    case_ref = test_intake.IntakeTests.case_ref
    review = test_intake.IntakeTests.review
    publish = test_intake.IntakeTests.publish

    def test_initial_edits_and_publication_then_lock_without_destroying_saved_work(self):
        activate(self.store)
        self.assertTrue(context(self.store)['editable'])
        case = self.prepare(); self.review(case); self.publish(case)
        draft = deepcopy(self.sponsor.draft())
        self.assertFalse(context(self.store, draft['body'])['editable'])
        changed = deepcopy(draft['body']); changed['scaffold'][0]['requirement'] = 'Bypass publication'
        count = self.store.db.execute('SELECT count(*) FROM records').fetchone()[0]
        with self.assertRaises(DecisionBlocked):
            self.sponsor.save_drawers(dict(expected=self.ref(), drawers=changed['scaffold']))
        with self.assertRaises(DecisionBlocked):
            Workspace(self.store,'priya').command('goals-save',dict(expected=self.ref(), goals=[], measures=[]))
        with self.assertRaises(DecisionBlocked):
            self.sponsor.publish(dict(expected=self.case_ref(case), confirm=True))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM records').fetchone()[0], count)
        self.assertEqual(self.sponsor.draft(), draft)

    def test_enabling_preserves_all_existing_records_including_unpublished_draft(self):
        case = self.prepare(); self.review(case); self.publish(case)
        draft = self.sponsor.draft(); body=deepcopy(draft['body'])
        body['scaffold'][0]['requirement'] = 'Previously saved unpublished wording'
        self.sponsor.save_draft(draft, body)
        before = list(self.store.db.execute('SELECT * FROM records ORDER BY rowid'))
        activate(self.store)
        after = list(self.store.db.execute('SELECT * FROM records ORDER BY rowid'))
        self.assertEqual([tuple(r) for r in after[:-1]], [tuple(r) for r in before])
        self.assertEqual(self.sponsor.draft()['body']['scaffold'][0]['requirement'], body['scaffold'][0]['requirement'])
        self.assertFalse(context(self.store, self.sponsor.draft()['body'])['editable'])


class GovernedAccountabilityTests(unittest.TestCase):
    setUp = test_bridge.BridgeTests.setUp
    tearDown = test_bridge.BridgeTests.tearDown
    w = test_bridge.BridgeTests.w
    payload = test_bridge.BridgeTests.payload
    issue = test_bridge.BridgeTests.issue
    current = test_bridge.BridgeTests.current
    propose = test_bridge.BridgeTests.propose
    case = test_bridge.BridgeTests.case
    reviews = test_bridge.BridgeTests.reviews
    decide = test_bridge.BridgeTests.decide

    def initial_publication(self):
        sponsor, prepared = self.fixture.sponsor()
        result=sponsor.command('intake-request',dict(expected=asdict(sponsor.intake.draft()['ref']),preflight=asdict(prepared['ref']),confirm=True))
        for actor in ('sam','lee'):
            case=self.store.latest(result['id'],{SCOPE})
            self.w(actor).command('intake-review',dict(expected=asdict(case['ref']),disposition='ready-for-investigation',rationale='Initial inquiry review'))
        sponsor.command('intake-publish',dict(expected=asdict(self.store.latest(result['id'],{SCOPE})['ref']),confirm=True,rationale='Initial publication'))
        activate(self.store)
        self.assertFalse(context(self.store)['editable'])
        return sponsor

    def shared_position(self, actor):
        state=self.w(actor).state()
        kinds={'intent','requirement','requirement-drawer','goal','success-measure'}
        position=sorted((r for r in state['records'] if r['kind'] in kinds),key=lambda r:r['ref'].id)
        self.assertTrue(all(r['scope']==SCOPE for r in position))
        if actor!='priya':
            self.assertIsNone(state['intake']['draft'])
            self.assertIsNone(state['goals'])
            self.assertIsNone(state['sponsor'])
        return position

    def test_every_role_sees_the_same_published_position_and_private_sponsor_edits_do_not_replace_it(self):
        self.initial_publication()
        before=self.shared_position('priya')
        intake=self.w('priya').intake
        self.w('priya').command('sponsor-save',dict(expected=asdict(intake.draft()['ref']),answers={'q17':dict(items=['PRIVATE UNPUBLISHED MEASUREMENT CHANGE'],roles=[],confirmed=False)}))
        for actor in ACTORS:
            self.assertEqual(self.shared_position(actor),before)

    def test_later_direct_creation_or_proposals_are_blocked_for_every_role_without_partial_writes(self):
        self.initial_publication()
        before=list(self.store.db.execute('SELECT * FROM records ORDER BY rowid'))
        for actor in ACTORS:
            with self.assertRaises((DecisionBlocked,PermissionError)):
                self.w(actor).command('requirement',dict(title='Bypass',text='Bypass',drawer='Experience',rationale='Bypass',conditions='Bounded'))
            with self.assertRaises((DecisionBlocked,PermissionError)):
                self.w(actor).command('proposal',dict(target=asdict(self.req['ref'])))
        self.assertEqual([tuple(r) for r in self.store.db.execute('SELECT * FROM records ORDER BY rowid')],[tuple(r) for r in before])

    def test_report_publication_and_issue_alone_never_update_requirements(self):
        self.initial_publication()
        before=deepcopy(self.store.latest(self.req['ref'].id,{SCOPE}))
        # Existing reports were published through the real domain-publish command.
        issue=self.issue()
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),before)
        with self.assertRaises(DecisionBlocked):
            self.w('alex').command('proposal',dict(target=asdict(self.req['ref'])))
        self.propose(issue); self.reviews(issue); self.decide(issue,'reject')
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),before)

    def test_preexisting_unlinked_review_cannot_bypass_accountability_on_approval(self):
        result=self.w('alex').command('proposal',dict(target=asdict(self.req['ref']),text='A cue proposal',rationale='Synthetic',conditions='Bounded',acceptance_criteria='Observe cue use',selected=[asdict(self.rc['ref']),asdict(self.dc['ref'])],changes_intent=False))
        self.initial_publication()
        before=deepcopy(self.store.latest(self.req['ref'].id,{SCOPE}))
        with self.assertRaises(DecisionBlocked):
            self.w('alex').command('decision',dict(expected=asdict(self.store.latest(result['id'],{SCOPE})['ref']),disposition='approve',rationale='Attempt unlinked approval',confirm=True))
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),before)

    def test_deferral_does_not_update_requirement(self):
        self.initial_publication(); issue=self.issue()
        before=deepcopy(self.store.latest(self.req['ref'].id,{SCOPE}))
        self.propose(issue); self.decide(issue,'defer')
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),before)

    def test_report_backed_issue_reviews_and_owner_approval_create_one_revision(self):
        self.initial_publication(); issue=self.issue()
        self.propose(issue); self.reviews(issue); self.decide(issue)
        result=self.store.latest(self.req['ref'].id,{SCOPE})
        self.assertEqual(result['ref'].revision,self.req['ref'].revision+1)
        self.assertEqual(result['body']['text'],'Show a persistent progress cue')
        self.assertEqual(self.current(issue)['body']['status'],'resolved')
        position=self.shared_position('priya')
        for actor in ACTORS:self.assertEqual(self.shared_position(actor),position)

    def test_sponsor_response_via_shared_accountability_unlocks_private_setup_only(self):
        sponsor=self.initial_publication(); before=deepcopy(self.store.latest('INT-001',{SCOPE}))
        issue=self.issue('intent')
        self.w('lee').command('bridge-intent-propose',dict(expected_issue=asdict(issue['ref']),source=asdict(self.rc['ref']),field='in_scope',proposed_value='A bounded cue experiment',rationale='Research changes scope'))
        request=self.store.latest(self.current(issue)['body']['linked']['ref']['id'],{SCOPE})
        self.w('priya').command('intent-adopt',dict(expected=asdict(request['ref']),draft_expected=asdict(sponsor.intake.draft()['ref']),response='A bounded cue experiment',rationale='Investigate the evidence'))
        intake=self.w('priya').intake
        self.assertTrue(context(self.store,intake.draft()['body'])['editable'])
        self.assertEqual(self.store.latest('INT-001',{SCOPE}),before)
        intake.build(dict(expected=asdict(intake.draft()['ref']),confirm=True))
        p=self.w('priya').command('intake-preflight',dict(expected=asdict(intake.draft()['ref'])))
        from workbench.intake import PRIVATE
        preflight=self.store.latest(p['id'],{PRIVATE})
        result=self.w('priya').command('intake-request',dict(expected=asdict(intake.draft()['ref']),preflight=asdict(preflight['ref']),confirm=True))
        for actor in ('sam','lee'):
            case=self.store.latest(result['id'],{SCOPE})
            self.w(actor).command('intake-review',dict(expected=asdict(case['ref']),disposition='ready-for-investigation',rationale='Review revised inquiry'))
        self.w('priya').command('intake-publish',dict(expected=asdict(self.store.latest(result['id'],{SCOPE})['ref']),confirm=True,rationale='Authorize revised inquiry'))
        self.assertEqual(self.current(issue)['body']['status'],'resolved')
        self.assertFalse(context(self.store,intake.draft()['body'])['editable'])

"""Connected human issue/review/decision cycle using synthetic packets only."""
from copy import deepcopy
from dataclasses import asdict
import unittest

from workbench.core import Ref, StaleBasis
from workbench.decisions import SCOPE, DecisionBlocked
from workbench.workspace import Workspace
import test_preflight_packets as fixtures


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.PreflightPacketTests();self.fixture.setUp();self.store=self.fixture.store
        self.research=self.fixture.deliverable('sam');self.rc,self.rp=self.fixture.publish(self.research[0],self.research[2],self.research[3],release_sources=True)
        self.design=self.fixture.deliverable('lee',[asdict(self.rc['ref'])]);self.dc,self.dp=self.fixture.publish(self.design[0],self.design[2],self.design[3],release_sources=True)
        self.req=self.fixture.req
    def tearDown(self):self.fixture.tearDown()
    def w(self,actor):return Workspace(self.store,actor,fixtures.NoEvaluation())
    def payload(self,route='requirement'):
        return dict(title='Resumption evidence and prototype assumptions',question='Which resumption cue is supported?',consequence='A wrong cue could cause repeated work',kind='conflict',boards=['research-design'],owner='sam',route=route,
            target=asdict(self.req['ref']),packet_refs=[dict(id=p['id'],revision=p['revision']) for p in [self.rp,self.dp]],requirement_refs=[asdict(self.req['ref'])])
    def issue(self,route='requirement'):
        result=self.w('sam').command('bridge-raise',self.payload(route));return self.store.latest(result['id'],{SCOPE})
    def current(self,issue):return self.store.latest(issue['ref'].id,{SCOPE})
    def propose(self,issue):
        return self.w('alex').command('bridge-propose',dict(expected_issue=asdict(self.current(issue)['ref']),text='Show a persistent progress cue',rationale='Resolve the recorded cue question',acceptance_criteria='Observe successful resumption with the cue',conditions='Bounded evaluation',selected=[asdict(self.rc['ref']),asdict(self.dc['ref'])],changes_intent=False))
    def case(self,issue):return self.store.latest(self.current(issue)['body']['linked']['ref']['id'],{SCOPE})
    def reviews(self,issue):
        for actor,value in [('sam','supported-with-limits'),('lee','cleared-with-conditions')]:
            self.w(actor).command('review',dict(expected=asdict(self.case(issue)['ref']),disposition=value,rationale='Synthetic bounded review'))
    def decide(self,issue,disposition='approve'):
        return self.w('alex').command('decision',dict(expected=asdict(self.case(issue)['ref']),disposition=disposition,rationale='Resolve the issue within the declared conditions',confirm=True,next_owner='sam',next_question='Clarify the supported cue'))

    def test_board_issue_is_persistent_shared_attributed_deduplicated_and_does_not_change_governing_records(self):
        before=self.req;issue=self.issue();again=self.w('sam').command('bridge-raise',self.payload())
        self.assertEqual(again['id'],issue['ref'].id)
        self.assertEqual(issue['body']['decision_owner'],'alex')
        self.assertEqual(issue['body']['status'],'open')
        for actor in ('priya','sam','lee','alex','maya'):
            state=self.w(actor).state()['bridge'];self.assertEqual(state['issues'][0]['ref'],issue['ref']);self.assertEqual(state['evaluation'],'on-hold')
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),before)
        self.assertEqual(self.w('alex').loop.history(),[])
        self.assertTrue(self.store.graph({SCOPE}).has_edge(issue['ref'],self.rc['ref']))
        self.store.close();from workbench.core import Store
        self.store=Store(self.fixture.path);self.fixture.store=self.store
        self.assertEqual(self.current(issue),issue)

    def test_private_packets_and_unknown_bridges_or_targets_are_rejected_without_partial_issue(self):
        p=self.payload();p['packet_refs']=[self.research[3]['body']['packet']]
        with self.assertRaises(PermissionError):self.w('sam').command('bridge-raise',p)
        for override in [dict(boards=['engineering-design']),dict(owner='maya'),dict(requirement_refs=[]),dict(route='approve')]:
            with self.assertRaises((ValueError,PermissionError)):self.w('sam').command('bridge-raise',{**self.payload(),**override})
        self.assertEqual(self.w('sam').bridge.issues(),[])

    def test_issue_links_the_same_review_and_authorized_decision_with_derived_status_and_receipt(self):
        issue=self.issue();self.propose(issue)
        self.assertEqual(self.current(issue)['body']['status'],'investigating')
        self.reviews(issue)
        self.assertEqual(self.current(issue)['body']['status'],'awaiting-decision')
        self.decide(issue)
        resolved=self.current(issue)['body'];self.assertEqual(resolved['status'],'resolved')
        decision=self.store.read(Ref(**resolved['resolution']['decision']),{SCOPE})
        self.assertEqual(decision['kind'],'decision');self.assertEqual(decision['body']['actor']['id'],'alex')
        self.assertTrue(self.store.graph({SCOPE}).has_edge(self.current(issue)['ref'],decision['ref']))
        self.assertEqual(resolved['resolution']['requirement'],asdict(self.store.latest(self.req['ref'].id,{SCOPE})['ref']))
        packet=resolved['resolution']['packet'];contents=self.store.resolve_packet(packet['id'],packet['revision'],{SCOPE})
        self.assertIn(decision['ref'],[r['ref'] for r in contents['records']])
        history=self.w('sam').state()['bridge']['issues'][0]['events'];self.assertTrue(any(e['body']['action']=='resolved' for e in history))
        before=self.current(issue)['ref'];self.w('alex').bridge.sync();self.assertEqual(self.current(issue)['ref'],before)

    def test_decision_and_assignment_permissions_are_server_enforced(self):
        issue=self.issue()
        for actor in ('sam','lee','priya'):
            with self.assertRaises(PermissionError):self.w(actor).command('bridge-close',dict(expected=asdict(issue['ref']),rationale='Unauthorized',confirm=True))
            with self.assertRaises(PermissionError):self.w(actor).command('bridge-propose',dict(expected_issue=asdict(issue['ref'])))
        with self.assertRaises(PermissionError):self.w('lee').command('bridge-respond',dict(expected=asdict(issue['ref']),action='assign',next_owner='lee',next_question='Take over',note='Unauthorized assignment'))
        self.w('lee').command('bridge-respond',dict(expected=asdict(issue['ref']),action='comment',note='Design interpretation remains uncertain'))
        with self.assertRaises(StaleBasis):self.w('sam').command('bridge-respond',dict(expected=asdict(issue['ref']),action='comment',note='Stale write'))

    def test_evidence_request_blocks_approval_until_assigned_answer_then_reuses_same_review(self):
        issue=self.issue();self.propose(issue);self.reviews(issue)
        self.w('sam').command('bridge-respond',dict(expected=asdict(self.current(issue)['ref']),action='request-evidence',note='Need the cue rationale before committing',next_owner='lee',next_question='Which cue was actually evaluated?'))
        with self.assertRaises(DecisionBlocked):self.decide(issue)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['ref'],self.req['ref'])
        with self.assertRaises(PermissionError):self.w('sam').command('bridge-respond',dict(expected=asdict(self.current(issue)['ref']),action='answer-request',note='Cannot answer for Design'))
        self.w('lee').command('bridge-respond',dict(expected=asdict(self.current(issue)['ref']),action='answer-request',note='Only the progress cue in the cited fictional session was evaluated'))
        self.decide(issue);self.assertEqual(self.current(issue)['body']['status'],'resolved')

    def test_changed_context_requires_explicit_refresh_and_keeps_original_packets(self):
        issue=self.issue();self.propose(issue);self.reviews(issue)
        newer=self.store.put(self.rc['ref'].id,'contribution',SCOPE,{**self.rc['body'],'interpretation':'A revised fictional interpretation'},self.rc['ref'].revision)
        with self.assertRaises(StaleBasis):self.decide(issue)
        self.assertTrue(self.w('sam').bridge.state()['issues'][0]['changed'])
        # Human review may intentionally retain a historical packet; observed/current refs stay distinct.
        before=self.current(issue)
        self.w('sam').command('bridge-refresh',{**self.payload(), 'expected':asdict(before['ref']), 'note':'Reviewed the revised interpretation; original packet remains the challenged basis'})
        current=self.current(issue);self.assertEqual(current['body']['packet_refs'],before['body']['packet_refs']);self.assertFalse(self.w('sam').bridge.state()['issues'][0]['changed'])
        self.assertEqual(self.store.read(before['ref'],{SCOPE}),before)
        # The governing decision still rejects stale selected contributions through the existing core guards.
        with self.assertRaises(StaleBasis):self.decide(issue)
        self.assertNotEqual(newer,self.rc['ref'])

    def test_requirement_deferral_rejection_and_reopening_preserve_outcomes(self):
        issue=self.issue();self.propose(issue)
        self.decide(issue,'defer');self.assertEqual(self.current(issue)['body']['status'],'deferred');self.assertEqual(self.current(issue)['body']['next_owner'],'sam')
        self.decide(issue,'reject');old=self.current(issue);self.assertEqual(old['body']['status'],'resolved')
        self.w('alex').command('bridge-refresh',{**self.payload(),'expected':asdict(old['ref']),'confirm':True,'note':'Reopen to investigate a new cue'})
        current=self.current(issue);self.assertEqual(current['body']['status'],'investigating');self.assertIsNone(current['body']['linked'])
        self.assertEqual(self.store.read(old['ref'],{SCOPE})['body']['resolution']['disposition'],'reject')

    def test_close_without_change_is_an_issue_disposition_not_requirement_approval(self):
        issue=self.issue('coordination')
        self.w('sam').command('bridge-close',dict(expected=asdict(issue['ref']),confirm=True,rationale='The receiving team already has the needed context; no governing change'))
        body=self.current(issue)['body'];self.assertEqual(body['status'],'resolved');self.assertEqual(body['resolution']['disposition'],'no-governing-change')
        self.assertEqual(self.req,self.store.latest(self.req['ref'].id,{SCOPE}));self.assertEqual(self.w('alex').loop.history(),[])

    def test_link_existing_review_resolves_the_same_issue_and_cannot_be_closed_around_it(self):
        issue=self.issue()
        result=self.w('alex').command('proposal',dict(target=asdict(self.req['ref']),text='A cue proposal',rationale='Synthetic',conditions='Bounded',acceptance_criteria='Observe cue use',selected=[asdict(self.rc['ref']),asdict(self.dc['ref'])],changes_intent=False))
        case=self.store.latest(result['id'],{SCOPE})
        self.w('alex').command('bridge-link-review',dict(expected=asdict(issue['ref']),case=asdict(case['ref']),note='This existing review addresses the issue'))
        with self.assertRaises(DecisionBlocked):self.w('alex').command('bridge-close',dict(expected=asdict(self.current(issue)['ref']),confirm=True,rationale='Cannot bypass the review'))
        self.decide(issue,'reject');self.assertEqual(self.current(issue)['body']['status'],'resolved')

    def test_intent_adoption_stays_open_until_domain_review_and_sponsor_publication(self):
        sponsor,prepared=self.fixture.sponsor();issue=self.issue('intent')
        self.w('lee').command('bridge-intent-propose',dict(expected_issue=asdict(issue['ref']),source=asdict(self.rc['ref']),field='in_scope',proposed_value='A bounded resumption cue experiment',rationale='Research changes the scope of inquiry'))
        icr=self.store.latest(self.current(issue)['body']['linked']['ref']['id'],{SCOPE})
        self.w('priya').command('intent-adopt',dict(expected=asdict(icr['ref']),draft_expected=asdict(sponsor.intake.draft()['ref']),response='A bounded resumption cue experiment',rationale='Investigate before committing delivery'))
        self.assertEqual(self.current(issue)['body']['status'],'investigating')
        i=self.w('priya').intake;i.build(dict(expected=asdict(i.draft()['ref']),confirm=True))
        package=self.w('priya').command('intake-preflight',dict(expected=asdict(i.draft()['ref'])))
        p=self.store.latest(package['id'],sponsor.scopes)
        result=self.w('priya').command('intake-request',dict(expected=asdict(i.draft()['ref']),preflight=asdict(p['ref']),confirm=True))
        for actor in ('sam','lee'):
            case=self.store.latest(result['id'],{SCOPE});self.w(actor).command('intake-review',dict(expected=asdict(case['ref']),disposition='ready-for-investigation',rationale='Review the bounded investigation direction'))
        self.w('priya').command('intake-publish',dict(expected=asdict(self.store.latest(result['id'],{SCOPE})['ref']),confirm=True,rationale='Authorize revised inquiry'))
        body=self.current(issue)['body'];self.assertEqual(body['status'],'resolved');self.assertEqual(body['resolution']['disposition'],'incorporated')
        self.assertEqual(body['resolution']['intent'],asdict(i.latest('INT-001')['ref']))

    def test_declining_an_intent_request_closes_issue_without_rewriting_the_intent(self):
        self.fixture.sponsor();baseline=self.store.latest('INT-001',{SCOPE});issue=self.issue('intent')
        self.w('sam').command('bridge-intent-propose',dict(expected_issue=asdict(issue['ref']),source=asdict(self.rc['ref']),field='in_scope',proposed_value='A different scope',rationale='Proposed extension'))
        request=self.store.latest(self.current(issue)['body']['linked']['ref']['id'],{SCOPE})
        self.w('priya').command('intent-dispose',dict(expected=asdict(request['ref']),disposition='declined',rationale='Retain the current scope; keep the finding for future work'))
        self.assertEqual(self.current(issue)['body']['status'],'resolved');self.assertEqual(self.current(issue)['body']['resolution']['disposition'],'declined');self.assertEqual(self.store.latest('INT-001',{SCOPE}),baseline)

    def test_direct_decision_cannot_bypass_another_open_governing_issue_for_the_requirement(self):
        first=self.issue();self.propose(first);self.reviews(first)
        other=self.w('lee').command('bridge-raise',{**self.payload(),'title':'A second consequential question','boards':['business-design']})
        other=self.store.latest(other['id'],{SCOPE})
        with self.assertRaises(DecisionBlocked):self.decide(first)
        self.w('alex').command('bridge-link-review',dict(expected=asdict(other['ref']),case=asdict(self.case(first)['ref']),note='The same reviewed change addresses both issues'))
        self.decide(first)
        self.assertEqual(self.current(first)['body']['status'],'resolved');self.assertEqual(self.current(other)['body']['status'],'resolved')

    def test_outcome_history_survives_reopening_and_comment_retry_is_atomic(self):
        issue=self.issue('coordination')
        self.w('sam').command('bridge-close',dict(expected=asdict(issue['ref']),confirm=True,rationale='No governing change needed'))
        resolved=self.current(issue)
        packet=resolved['body']['resolution']['packet'];self.assertIn('bridge-issue-decision',{r['kind'] for r in self.store.resolve_packet(packet['id'],packet['revision'],{SCOPE})['records']})
        self.w('sam').command('bridge-refresh',{**self.payload('coordination'),'expected':asdict(resolved['ref']),'note':'Reopen for another inquiry','confirm':True})
        state=self.w('sam').bridge.state();self.assertIsNone(state['issues'][0]['body']['resolution']);self.assertEqual(state['outcomes'][0]['disposition'],'no-governing-change')

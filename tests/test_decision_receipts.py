"""Exact, read-only decision receipts over real synthetic workflow transactions."""
from copy import deepcopy
from dataclasses import asdict
import json
import unittest
from unittest.mock import patch
from workbench.core import Ref
from workbench.decisions import SCOPE
from workbench.decision_rights import DEFAULTS
from workbench.decision_receipts import DecisionReceipts
import test_bridge as fixtures

class DecisionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.BridgeTests();self.f.setUp();self.store=self.f.store
    def tearDown(self):self.f.tearDown()
    def receipt(self,i):return DecisionReceipts(self.store).for_issue(self.f.current(i))
    def approved(self):
        i=self.f.issue();self.f.propose(i);self.f.reviews(i);self.f.decide(i);return i
    def test_receipt_uses_the_transacted_decision_wording_reviews_and_timestamp_without_writes(self):
        i=self.approved();issue=self.f.current(i);decision=self.store.read(Ref(**issue['body']['resolution']['decision']),{SCOPE})
        count=self.store.db.total_changes;receipt=self.receipt(i)
        self.assertEqual(receipt['decision'],asdict(decision['ref']));self.assertEqual(receipt['rationale'],decision['body']['rationale']);self.assertEqual(receipt['at'],decision['body']['at']);self.assertEqual(receipt['decider']['id'],'alex')
        self.assertEqual(receipt['approved']['text'],decision['body']['proposal']['text']);self.assertEqual(receipt['approved']['acceptance_criteria'],decision['body']['proposal']['acceptance_criteria']);self.assertEqual(len(receipt['reviews']),2)
        self.assertTrue(any(e['ref']==asdict(self.f.rc['ref']) for e in receipt['evidence']));self.assertEqual(count,self.store.db.total_changes)
        projected=next(v for v in self.f.w('lee').state()['bridge']['issues'] if v['ref']==issue['ref']);self.assertEqual(projected['decision_receipt'],receipt)
    def test_later_requirement_and_policy_versions_never_rewrite_the_receipt(self):
        i=self.approved();before=self.receipt(i);old=self.store.latest(self.f.req['ref'].id,{SCOPE})
        self.store.put(old['ref'].id,'requirement',SCOPE,{**old['body'],'text':'Later wording must not appear'},old['ref'].revision)
        rights=self.f.w('alex').rights;rules=deepcopy(DEFAULTS);rules['requirement'].update(decider='priya',delegates=['alex']);rights.admin=True;rights.save(dict(expected=None,rules=rules,reason='Future authority only'))
        closed=self.f.current(i)
        with patch.object(self.store,'latest',side_effect=AssertionError('Receipt must only read exact records')):
            receipt=DecisionReceipts(self.store).for_issue(closed)
        self.assertEqual(receipt,before)
    def test_rejection_and_coordination_closure_never_label_a_proposal_as_approved(self):
        i=self.f.issue();self.f.propose(i);self.f.decide(i,'reject');r=self.receipt(i)
        self.assertIsNone(r['approved']);self.assertEqual(r['outcome'],'reject');self.assertNotIn('Show a persistent progress cue',r['wording_message'])
        other=self.f.issue('coordination');self.f.w('sam').command('bridge-close',dict(expected=asdict(other['ref']),confirm=True,rationale='Retain the existing requirements'))
        r=self.receipt(other);self.assertEqual(r['outcome'],'no-governing-change');self.assertIsNone(r['approved']);self.assertEqual(r['rationale'],'Retain the existing requirements')
    def test_pending_and_reopened_issues_have_no_current_receipt_and_prior_versions_survive(self):
        i=self.f.issue();self.assertIsNone(self.receipt(i));self.f.propose(i);self.f.decide(i,'reject');closed=self.f.current(i);old=self.receipt(i)
        self.f.w('alex').command('bridge-refresh',{**self.f.payload(),'expected':asdict(closed['ref']),'confirm':True,'note':'Reconsider with reviewed context'})
        self.assertIsNone(self.receipt(i));self.assertEqual(DecisionReceipts(self.store).for_issue(closed),old)
    def test_saved_delegate_and_escalation_are_receipted_not_replaced_by_current_roles(self):
        rights=self.f.w('alex').rights;rights.admin=True;rules=deepcopy(DEFAULTS);rules['requirement'].update(delegates=['priya'],escalation_path=['lee']);rights.save(dict(expected=None,rules=rules,reason='Synthetic explicit authority'))
        i=self.f.issue();self.f.propose(i);self.f.reviews(i)
        def act(actor,action,**kw):return self.f.w(actor).command('decision-rights-action',dict(expected=asdict(self.f.case(i)['ref']),action=action,reason='Recorded authority rationale',**kw))
        act('alex','delegate',delegate='priya');act('sam','escalate');act('lee','respond')
        self.f.w('priya').command('decision',dict(expected=asdict(self.f.case(i)['ref']),disposition='approve',rationale='Delegate reviewed the exact wording',confirm=True))
        r=self.receipt(i);self.assertEqual(r['decider']['id'],'priya');self.assertEqual(r['authority']['authorized_as'],'delegate');self.assertEqual(r['authority']['delegation']['by'],'alex');self.assertEqual(r['authority']['escalation']['responded_by'],'lee')
    def test_legacy_authority_is_not_invented_and_private_or_missing_decisions_fail_closed(self):
        i=self.approved();closed=self.f.current(i);decision=self.store.read(Ref(**closed['body']['resolution']['decision']),{SCOPE})
        legacy=self.store.put('LEGACY-DEC','decision',SCOPE,{k:v for k,v in decision['body'].items() if k!='authority'})
        specimen=deepcopy(closed);specimen['body']['resolution']['decision']=asdict(legacy)
        self.assertIsNone(DecisionReceipts(self.store).for_issue(specimen)['authority'])
        private=self.store.put('SECRET-DEC','decision','domain:research',dict(text='PRIVATE MARKER'))
        for raw in [asdict(private),dict(id='MISSING-DEC',revision=1)]:
            specimen['body']['resolution']['decision']=raw;r=DecisionReceipts(self.store).for_issue(specimen);self.assertFalse(r['available']);self.assertNotIn('PRIVATE MARKER',json.dumps(r))
    def test_inaccessible_evidence_is_marked_unavailable_without_leaking_the_body(self):
        private=self.store.put('SECRET-EVIDENCE','evidence','domain:research',dict(text='PRIVATE MARKER'));record=DecisionReceipts(self.store).evidence(asdict(private));self.assertTrue(record['unavailable']);self.assertNotIn('PRIVATE MARKER',json.dumps(record))
    def test_intent_receipt_uses_the_actual_published_field_not_the_requested_proposal(self):
        sponsor,_=self.f.fixture.sponsor();i=self.f.issue('intent');w=self.f.w
        w('lee').command('bridge-intent-propose',dict(expected_issue=asdict(i['ref']),source=asdict(self.f.rc['ref']),field='in_scope',proposed_value='Original requested experiment',rationale='Scope should change'))
        request=self.store.latest(self.f.current(i)['body']['linked']['ref']['id'],{SCOPE})
        w('priya').command('intent-adopt',dict(expected=asdict(request['ref']),draft_expected=asdict(sponsor.intake.draft()['ref']),response='Sponsor refined the bounded experiment',rationale='Refine the proposed wording'))
        intake=w('priya').intake;intake.build(dict(expected=asdict(intake.draft()['ref']),confirm=True));p=w('priya').command('intake-preflight',dict(expected=asdict(intake.draft()['ref'])));preflight=self.store.latest(p['id'],sponsor.scopes)
        review=w('priya').command('intake-request',dict(expected=asdict(intake.draft()['ref']),preflight=asdict(preflight['ref']),confirm=True))
        for actor in ('sam','lee'):
            case=self.store.latest(review['id'],{SCOPE});w(actor).command('intake-review',dict(expected=asdict(case['ref']),disposition='ready-for-investigation',rationale='Review the refined direction'))
        w('priya').command('intake-publish',dict(expected=asdict(self.store.latest(review['id'],{SCOPE})['ref']),confirm=True,rationale='Publish the revised inquiry'))
        r=self.receipt(i);self.assertEqual(r['kind'],'intent-decision');self.assertEqual(r['approved']['field'],'in_scope');self.assertEqual(r['approved']['text'],'Sponsor refined the bounded experiment')
    def test_legacy_declined_sponsor_response_is_not_formal_publication(self):
        self.f.fixture.sponsor();i=self.f.issue('intent');w=self.f.w
        w('sam').command('bridge-intent-propose',dict(expected_issue=asdict(i['ref']),source=asdict(self.f.rc['ref']),field='in_scope',proposed_value='Different scope',rationale='Consider expansion'))
        request=self.store.latest(self.f.current(i)['body']['linked']['ref']['id'],{SCOPE});w('priya').command('intent-dispose',dict(expected=asdict(request['ref']),disposition='declined',rationale='Retain scope'))
        r=self.receipt(i);self.assertTrue(r['response_only']);self.assertIsNone(r['approved']);self.assertEqual(r['rationale'],'Retain scope')

    def test_coordination_receipt_retains_the_exact_required_assessment(self):
        rights=self.f.w('alex').rights;rights.admin=True;rules=deepcopy(DEFAULTS);rules['coordination']['reviewers']=['lee'];rights.save(dict(expected=None,rules=rules,reason='Review before disposition'))
        i=self.f.issue('coordination');self.f.w('lee').command('decision-rights-action',dict(expected=asdict(i['ref']),action='review',disposition='cleared-with-conditions',reason='The context is sufficient for closure'))
        self.f.w('sam').command('bridge-close',dict(expected=asdict(self.f.current(i)['ref']),confirm=True,rationale='Close the reviewed coordination question'))
        r=self.receipt(i);self.assertEqual(len(r['reviews']),1);self.assertEqual(r['reviews'][0]['fields']['rationale'],'The context is sufficient for closure');self.assertIsNone(r['approved'])

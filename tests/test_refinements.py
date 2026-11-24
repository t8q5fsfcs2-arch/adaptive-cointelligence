from dataclasses import asdict
import json
import unittest
from unittest.mock import patch

import test_intake
from workbench.core import StaleBasis
from workbench.decisions import SCOPE, DecisionBlocked
from workbench.intake import Intake
from workbench.refinements import blockers
from workbench.workspace import Workspace


class AdaptiveIntentTests(unittest.TestCase):
    setUp = test_intake.IntakeTests.setUp
    tearDown = test_intake.IntakeTests.tearDown
    ref = test_intake.IntakeTests.ref
    accept_value = test_intake.IntakeTests.accept_value
    prepare = test_intake.IntakeTests.prepare
    case_ref = test_intake.IntakeTests.case_ref
    review = test_intake.IntakeTests.review
    publish = test_intake.IntakeTests.publish

    def baseline(self):
        id = self.prepare(); self.review(id); self.publish(id)
        return self.sponsor.latest('REQ-INTAKE-needs')

    def finding(self, actor='sam', req=None, expected=None, observation='Outside staffed hours, people cannot get assistance'):
        w = Workspace(self.store, actor)
        result = w.save_contribution(dict(title='Follow-up finding', observation=observation,
            source='Fictional study, section 2', limitation='Demand is not quantified',
            validation_focus='problem', requirement_refs=[asdict(req)] if req else [], expected=expected))
        draft = self.store.latest(result['id'], w.scopes)
        shared = w.publish({'expected': asdict(draft['ref']), 'confirm': True})
        return self.sponsor.latest(shared['id']), draft

    def change(self, source, req=None, field='business_challenge', value='Help customers complete enrollment across staffed and unstaffed hours'):
        data=dict(source=asdict(source['ref']), base_intent=asdict(self.sponsor.latest('INT-001')['ref']),
                  field=field, proposed_value=value, rationale='The finding challenges the original framing',
                  requirement_refs=[asdict(req)] if req else [])
        result=Workspace(self.store,'sam').command('intent-refine',data)
        return self.sponsor.latest(result['id'])

    def adopt(self, change, response=None):
        return self.sponsor.refinements.adopt(dict(expected=asdict(change['ref']), draft_expected=self.ref(),
            response=response or change['body']['proposed_value'], rationale='Take this finding into the next direction review'))

    def next_review(self):
        self.accept_value()
        self.sponsor.build({'expected':self.ref(),'confirm':True})
        id=self.sponsor.request({'expected':self.ref(),'confirm':True})['id']
        self.review(id)
        return id

    def proposal(self, req, sources, expected=None):
        return Workspace(self.store,'alex').submit_proposal(dict(target=asdict(req),selected=[asdict(s['ref']) for s in sources],
            text='Provide available support hours and a resumable request route',
            acceptance_criteria='In a bounded task evaluation, users identify staffed hours, leave a request and resume; record completion and failures',
            conditions='Confirm coverage; no eligibility waiver',rationale='Refine the requirement and its test from the domain findings',
            changes_intent=False,expected=expected))['id']

    def requirement_reviews(self, id):
        for actor, disposition in [('sam','supported-with-limits'),('maya','cleared-with-conditions')]:
            Workspace(self.store,actor).review({'expected':self.case_ref(id),'disposition':disposition,'rationale':'Within the recorded limits'})

    def approve(self,id):
        return Workspace(self.store,'alex').decide(dict(expected=self.case_ref(id),disposition='approve',rationale='Approve the bounded requirement and criteria',confirm=True))

    def test_whole_intake_and_category_focus_survive_refresh(self):
        self.prepare()
        before=self.sponsor.draft()['body']['scaffold'][0].copy()
        self.sponsor.save({'expected':self.ref(),'step':'context','user_situation':'Customers use a shared device after staffed hours'})
        self.accept_value()
        self.sponsor.build({'expected':self.ref(),'confirm':True})
        body=self.sponsor.draft()['body']
        for d in body['scaffold']:
            self.assertEqual(set(d['intake_fields']),set(body['values']))
            self.assertIn('user_situation',d['changed_intake_fields'])
        for k in ['requirement','acceptance_criteria','rationale','question']:
            self.assertEqual(body['scaffold'][0][k],before[k])
        id=self.sponsor.request({'expected':self.ref(),'confirm':True})['id'];self.review(id);self.publish(id)
        self.assertEqual(self.sponsor.latest('INT-001')['body']['intake'],body['values'])
        for row in Workspace(self.store,'alex').latest_records('requirement-drawer'):
            self.assertTrue(self.store.graph({SCOPE}).has_edge(row['ref'],self.sponsor.latest('INT-001')['ref']))

    def test_finding_to_intent_to_criteria_end_to_end_preserves_old_packet(self):
        req=self.baseline(); old_intent=self.sponsor.latest('INT-001')
        old_packet=Workspace(self.store,'alex').packet_for(req['ref'])
        research,_=self.finding(req=req['ref']);ops,_=self.finding('maya',req['ref'])
        review=self.proposal(req['ref'],[research,ops]);self.requirement_reviews(review)
        change=self.change(research,req['ref'])
        with self.assertRaises(DecisionBlocked):self.approve(review)
        self.adopt(change)
        self.assertEqual(self.sponsor.latest('INT-001'),old_intent)
        self.assertEqual(self.sponsor.latest(req['ref'].id),req)
        id=self.next_review();self.publish(id)
        intent=self.sponsor.latest('INT-001')
        self.assertEqual(intent['ref'].revision,2)
        self.assertEqual(intent['body']['intake']['business_challenge'],change['body']['proposed_value'])
        self.assertEqual(intent['body']['intake']['user_situation'],test_intake.CONTEXT['user_situation'])
        self.assertEqual(self.sponsor.latest(change['ref'].id)['body']['status'],'incorporated')
        self.assertFalse(blockers(self.store,req['ref'].id))
        self.assertEqual(self.sponsor.latest(req['ref'].id),req)
        with self.assertRaises(StaleBasis):self.approve(review)
        self.proposal(req['ref'],[research,ops],self.case_ref(review));self.requirement_reviews(review);self.approve(review)
        revised=self.sponsor.latest(req['ref'].id)
        self.assertEqual(revised['ref'].revision,2)
        self.assertIn('staffed hours',revised['body']['acceptance_criteria'])
        self.assertEqual(revised['body']['fulfillment'],'not-evaluated')
        self.assertEqual(self.store.read_packet(old_packet['id'],old_packet['revision'],{SCOPE}),old_packet)
        self.assertEqual(self.store.read(old_intent['ref'],{SCOPE}),old_intent)
        self.assertTrue(self.store.graph({SCOPE}).has_edge(intent['ref'],research['ref']))

    def test_private_findings_and_private_sponsor_response_do_not_leak(self):
        req=self.baseline();source,draft=self.finding(req=req['ref'])
        with self.assertRaises(PermissionError):self.change(draft)
        change=self.change(source,req['ref'])
        with self.assertRaises(PermissionError):
            Intake(self.store,'sam').refinements.adopt(dict(expected=asdict(change['ref']),draft_expected=self.ref(),response='Not authorized',rationale='No'))
        self.adopt(change,response='PRIVATE SPONSOR RESPONSE')
        shared=Workspace(self.store,'maya').state()
        self.assertNotIn('PRIVATE SPONSOR RESPONSE',json.dumps(shared,default=str))
        self.accept_value()
        self.sponsor.build({'expected':self.ref(),'confirm':True})
        self.sponsor.request({'expected':self.ref(),'confirm':True})
        self.assertIn('PRIVATE SPONSOR RESPONSE',json.dumps(Workspace(self.store,'maya').state(),default=str))

    def test_source_revision_invalidates_request_and_review(self):
        req=self.baseline();source,draft=self.finding(req=req['ref'])
        change=self.change(source);self.adopt(change);id=self.next_review()
        self.finding(req=req['ref'],expected=asdict(draft['ref']),observation='New evidence changes the inference')
        with self.assertRaises(StaleBasis):self.publish(id)
        with self.assertRaises(StaleBasis):self.change(source)
        self.assertEqual(self.sponsor.latest('INT-001')['ref'].revision,1)
        self.assertTrue(Workspace(self.store,'sam').state()['intake']['cases'][0]['stale'])

    def test_declining_drafted_change_restores_only_its_field_and_keeps_history(self):
        req=self.baseline();source,_=self.finding();change=self.change(source);self.adopt(change)
        self.accept_value()
        self.sponsor.save({'expected':self.ref(),'step':'context','open_questions':'An unrelated open question'})
        self.sponsor.refinements.dispose(dict(expected=self.case_ref(change['ref'].id),draft_expected=self.ref(),disposition='declined',rationale='Current scope remains appropriate'))
        self.assertEqual(self.sponsor.draft()['body']['values']['business_challenge'],test_intake.VALUE['business_challenge'])
        self.assertEqual(self.sponsor.draft()['body']['values']['open_questions'],'An unrelated open question')
        self.assertFalse(blockers(self.store,req['ref'].id))
        self.assertNotIn(change['ref'].id,self.sponsor.draft()['body'].get('refinement_notes',{}))
        self.assertEqual(self.store.read(change['ref'],{SCOPE})['body']['status'],'open')

    def test_deferral_blocks_affected_requirement_only(self):
        req=self.baseline();source,_=self.finding();change=self.change(source,req['ref'])
        with self.assertRaises(ValueError):
            self.sponsor.refinements.dispose(dict(expected=asdict(change['ref']),disposition='deferred',rationale='Investigate'))
        self.sponsor.refinements.dispose(dict(expected=asdict(change['ref']),disposition='deferred',rationale='Need more information',next_owner='maya',next_question='Can coverage support this?'))
        self.assertTrue(blockers(self.store,req['ref'].id))
        self.assertFalse(blockers(self.store,'UNRELATED'))
        self.assertEqual(self.sponsor.latest('INT-001')['ref'].revision,1)

    def test_publication_failure_rolls_back_refinement_resolution(self):
        self.baseline();source,_=self.finding();change=self.change(source);self.adopt(change);id=self.next_review()
        with patch.object(self.store,'packet',side_effect=RuntimeError('disk failure')):
            with self.assertRaises(RuntimeError):self.publish(id)
        self.assertEqual(self.sponsor.latest(change['ref'].id)['body']['status'],'drafted')
        self.assertEqual(self.sponsor.latest('INT-001')['ref'].revision,1)
        self.publish(id)
        self.assertEqual(self.sponsor.latest(change['ref'].id)['body']['status'],'incorporated')

    def test_later_direction_retains_finding_basis_and_observes_new_version(self):
        self.baseline();source,draft=self.finding();change=self.change(source);self.adopt(change);self.publish(self.next_review())
        self.sponsor.save({'expected':self.ref(),'step':'value','why_now':'New timing context'})
        id=self.next_review()
        self.assertIn(asdict(source['ref']),self.sponsor.latest(id)['body']['snapshot']['finding_basis'])
        self.finding(expected=asdict(draft['ref']),observation='Revised published finding')
        with self.assertRaises(StaleBasis):self.publish(id)
        id=self.next_review();self.publish(id)
        self.assertEqual(self.sponsor.latest('INT-001')['body']['finding_basis'][0]['revision'],2)

    def test_competing_field_requests_require_explicit_resolution(self):
        self.baseline();source,_=self.finding();first=self.change(source);second=self.change(source,value='A different framing')
        self.adopt(first)
        with self.assertRaises(DecisionBlocked):self.adopt(second)
        id=self.next_review()
        with self.assertRaises(DecisionBlocked):self.publish(id)
        self.sponsor.refinements.dispose(dict(expected=asdict(second['ref']),disposition='declined',rationale='Use the other framing'))
        self.publish(id)

    def test_criteria_can_be_open_while_drafting_but_not_at_approval(self):
        self.baseline();w=Workspace(self.store,'alex')
        id=w.create_requirement(dict(title='A draft',text='Help users resume',rationale='Investigate the need',conditions='Within scope',drawer='Experience'))['id']
        self.assertEqual(self.sponsor.latest(id)['body']['acceptance_criteria'],'')
        sam,_=self.finding();maya,_=self.finding('maya')
        with self.assertRaises(ValueError):
            w.submit_proposal(dict(target=self.case_ref(id),selected=[asdict(sam['ref']),asdict(maya['ref'])],text='Revised',rationale='Explain',acceptance_criteria='',conditions='Within scope',changes_intent=False))

if __name__=='__main__':unittest.main()

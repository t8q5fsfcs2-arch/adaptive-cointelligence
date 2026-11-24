"""Section boundaries, legacy preservation and draft freedom versus publication."""
from dataclasses import asdict
from copy import deepcopy
import unittest
import test_intake
from test_coaching import RecordingModel
from workbench.intake import ALL_FIELDS, PROPOSITION_FIELDS, SECTION_FIELDS, PRIVATE
from workbench.intake_coach import FIELDS, response_schema
from workbench.workspace import Workspace
from workbench.decisions import fingerprint, DecisionBlocked

class IntakeSectionTests(unittest.TestCase):
    setUp=test_intake.IntakeTests.setUp
    tearDown=test_intake.IntakeTests.tearDown
    ref=test_intake.IntakeTests.ref

    def test_sections_are_disjoint_and_cover_every_field(self):
        fields=[k for group in SECTION_FIELDS.values() for k in group]
        self.assertEqual(len(fields),len(set(fields)))
        self.assertEqual(set(fields),set(ALL_FIELDS))
        self.assertEqual(SECTION_FIELDS['success'],('measures','measure_review'))
        for key in ('why_now','business_challenge','measures','user_actions','constraints'):
            self.assertNotIn(key,PROPOSITION_FIELDS)

    def test_empty_intake_allows_context_and_question_coaching_without_acceptance(self):
        before=deepcopy(self.sponsor.draft())
        self.sponsor.save({'expected':self.ref(),'step':'context','user_actions':'Log the request and hand it to dispatch.'})
        self.assertEqual(self.store.read(before['ref'],{PRIVATE}),before)
        model=RecordingModel();model.custom={'reply':'Name what dispatch needs at the handoff.','suggestions':[],'questions':[]}
        w=Workspace(self.store,'priya',model)
        w.command('intake-coach',{'expected':self.ref(),'skill':'coach-field','field':'handoffs','consent':True})
        self.assertEqual(model.context['phase'],'context')
        self.assertEqual(model.context['working_value_proposition']['status'],'draft')
        self.assertIsNone(model.context['accepted_value_proposition'])
        self.assertIn('user_actions',[x['field'] for x in model.context['connected_answers']])
        self.assertIsNone(self.sponsor.latest('VALUE-ACCEPTANCE-001'))
        with self.assertRaises(DecisionBlocked):self.sponsor.request({'expected':self.ref(),'confirm':True})

    def test_legacy_acceptance_and_answers_remain_readable_without_migration(self):
        self.sponsor.save({'expected':self.ref(),'step':'value',**test_intake.VALUE})
        draft=self.sponsor.draft();values=deepcopy(draft['body']['values'])
        self.store.put('VALUE-ACCEPTANCE-001','value-acceptance',PRIVATE,{'values':values,'signature':fingerprint(values),'status':'accepted-for-context-exploration'})
        legacy=self.sponsor.latest('VALUE-ACCEPTANCE-001')
        self.assertTrue(self.sponsor.value_checkpoint(draft['body'])['current'])
        self.sponsor.save({'expected':self.ref(),'step':'rationale','strategic_relevance':'Reduce avoidable repeat work.'})
        self.sponsor.save({'expected':self.ref(),'step':'success','measures':'Less repeat work -> fewer reentries -> reentries per case; baseline unknown.'})
        self.assertTrue(self.sponsor.value_checkpoint(self.sponsor.draft()['body'])['current'])
        self.assertEqual(self.sponsor.latest('VALUE-ACCEPTANCE-001'),legacy)
        self.assertEqual(self.store.read(draft['ref'],{PRIVATE})['body']['values'],values)

    def test_document_drafts_route_all_sections_and_preserve_human_answers(self):
        w=Workspace(self.store,'priya',RecordingModel())
        self.sponsor.save({'expected':self.ref(),'step':'rationale','business_challenge':'My wording'})
        source=w.command('intake-source',{'title':'Fictional workflow','text':'Coordinators repeat entry. Dispatch receives a request. Proposed benefit: fewer repetitions. Baseline unknown.'})['ref']
        proposals=[]
        for key in ('business_challenge','need','user_actions','measures'):
            proposals.append({'field':key,'text':'Supported draft for '+key,'rationale':'Fictional source','basis':'source-supported','citations':[{'passage_id':source['id']+':p1'}]})
        # Use the actual generated passage IDs, with no invented citation locators.
        from workbench.source_passages import source_with_passages
        record=w.coaching.records('intake-source')[0]
        passage=source_with_passages({'id':source['id'],'ref':source,**record['body']})['passages'][0]['id']
        for p in proposals:p['citations']=[{'passage_id':passage}]
        w.coaching.agent.model.custom={'reply':'Supported drafts.','suggestions':proposals,'questions':[]}
        run=w.command('intake-coach',{'expected':self.ref(),'skill':'seed-value','message':'Draft','sources':[source],'consent':True})
        result=w.command('intake-coach-fill-empty',{'expected':self.ref(),'run_id':run['ref']['id'],'confirm':True})
        self.assertEqual(set(result['filled']),{'need','user_actions','measures'})
        body=self.sponsor.draft()['body']
        self.assertEqual(body['values']['business_challenge'],'My wording')
        self.assertTrue(all(body['field_provenance'][k]['citations'] for k in result['filled']))
        self.assertFalse(self.sponsor.value_checkpoint(body)['current'])
        self.assertNotIn('assumption_owner',FIELDS);self.assertNotIn('work_kind',FIELDS)
        self.assertEqual(set(w.coaching.agent.model.schema['properties']['suggestions']['required']),set(FIELDS))

    def test_old_draft_missing_new_field_can_receive_a_document_answer(self):
        draft=self.sponsor.draft();body=draft['body']
        body['values'].pop('handoffs');self.sponsor.save_draft(draft,body)
        self.sponsor.save({'expected':self.ref(),'step':'context','handoffs':'Coordinator to dispatcher'})
        self.assertEqual(self.sponsor.draft()['body']['values']['handoffs'],'Coordinator to dispatcher')

    def test_metrics_and_review_plan_save_separately_without_rewriting_old_answers(self):
        metrics='Reduce repeat entry per case; baseline and target unknown.\n\nReduce median handoff time; target unknown.'
        self.sponsor.save({'expected':self.ref(),'step':'success','measures':metrics})
        before=deepcopy(self.sponsor.draft())
        # A pre-update draft need not contain the newly introduced question.
        body=deepcopy(before['body']);body['values'].pop('measure_review',None)
        self.sponsor.save_draft(self.sponsor.draft(),body)
        self.sponsor.save({'expected':self.ref(),'step':'success','measure_review':'Review after the first month; source and reviewer to confirm.'})
        current=self.sponsor.draft()['body']['values']
        self.assertEqual(current['measures'],metrics)
        self.assertIn('first month',current['measure_review'])
        self.assertEqual(self.store.read(before['ref'],{PRIVATE}),before)
        self.assertIsNone(self.sponsor.latest('VALUE-ACCEPTANCE-001'))

if __name__=='__main__':unittest.main()

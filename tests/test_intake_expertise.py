from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store
from workbench.workspace import Workspace
from workbench.intake import VALUE_FIELDS, CONTEXT_FIELDS, ALL_FIELDS
from workbench.intake_expertise import PROFILES, VERSION
from workbench.model_provider import ModelUnavailable
from workbench.decisions import DecisionBlocked
from test_coaching import RecordingModel
from test_intake import VALUE

class ExpertiseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name)/'synthetic.sqlite3')
        self.model = RecordingModel()
        self.model.custom = {'reply':'A focused coaching response.', 'suggestions':[], 'questions':[]}
        self.ws = Workspace(self.store, 'priya', self.model)
        self.ws.command('intake-start', {'title':'Fictional expertise test'})
        self.ws.command('intake-save', {'expected':self.ref(), 'step':'value', **VALUE})
        self.ws.command('intake-accept-value', {'expected':self.ref(), 'confirm':True})
    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()
    def ref(self): return asdict(self.ws.intake.draft()['ref'])
    def coach(self, field):
        return self.ws.command('intake-coach', {'expected':self.ref(), 'skill':'coach-field', 'field':field, 'message':'Help me understand how to respond.', 'sources':[], 'consent':True})
    def test_every_input_has_a_complete_question_specific_contract(self):
        self.assertEqual(set(PROFILES), set(ALL_FIELDS))
        for field, p in PROFILES.items():
            with self.subTest(field=field):
                self.assertTrue(p['hint'] and p['starter'] and p['expert_role'] and p['answer_shape'] and p['quality_checks'])
                self.assertTrue(set(p['connections']) <= set(PROFILES))
                self.coach(field)
                c = self.model.context
                self.assertEqual(c['expert_profile']['field'], field)
                self.assertEqual(c['expert_profile']['quality_checks'], p['quality_checks'])
                self.assertEqual(c['working_answer']['text'], self.ws.intake.draft()['body']['values'][field])
    def test_measures_receive_exact_value_and_saved_connection_snapshot(self):
        before = deepcopy(self.ws.intake.draft()['body']['values'])
        result = self.coach('measures')
        linked = {x['field']:x['text'] for x in self.model.context['connected_answers']}
        self.assertEqual(linked['value'], VALUE['value'])
        saved = next(r for r in self.ws.coaching.records('intake-coach-run') if r['ref'].id == result['ref']['id'])['body']
        self.assertEqual(saved['expertise_version'], VERSION)
        self.assertEqual(saved['connected_answers'], self.model.context['connected_answers'])
        self.assertEqual(self.ws.intake.draft()['body']['values'], before)
    def test_changed_value_is_not_replaced_by_accepted_old_value_in_measurement(self):
        self.ws.command('intake-save', {'expected':self.ref(),'step':'value','value':'A different benefit: less repeated effort for support colleagues.'})
        self.coach('measures')
        linked = {x['field']:x['text'] for x in self.model.context['connected_answers']}
        self.assertEqual(linked['value'], 'A different benefit: less repeated effort for support colleagues.')

    def test_review_coach_receives_exact_metrics_and_proposes_without_changing_draft(self):
        metrics='Fewer repeats: count reentries per request. Baseline and target unknown.'
        self.ws.command('intake-save', {'expected':self.ref(),'step':'success','measures':metrics,'measure_review':'Timing unknown.'})
        before=deepcopy(self.ws.intake.draft())
        self.model.custom={'reply':'Confirm a data source before choosing the first review.', 'questions':[], 'suggestions':[{
            'field':'measure_review','text':'Proposed first review: after one month of use. Data source and reviewer remain unconfirmed.',
            'rationale':'A proposal, not a committed review date.','basis':'hypothesis','citations':[]}]}
        result=self.coach('measure_review')
        self.assertEqual(self.model.context['phase'],'success')
        self.assertEqual(next(x['text'] for x in self.model.context['connected_answers'] if x['field']=='measures'),metrics)
        self.assertEqual(self.ws.intake.draft(),before)
        self.ws.command('intake-coach-apply',{'expected':self.ref(),'run_id':result['ref']['id'],'field':'measure_review','confirm':True})
        self.assertEqual(self.ws.intake.draft()['body']['values']['measures'],metrics)
        self.assertIn('unconfirmed',self.ws.intake.draft()['body']['values']['measure_review'])
    def test_empty_value_stays_empty_in_context_instead_of_fabricated_benefit(self):
        self.ws.command('intake-save', {'expected':self.ref(),'step':'value','value':''})
        self.coach('measures')
        self.assertEqual(next(x['text'] for x in self.model.context['connected_answers'] if x['field']=='value'),'')
    def test_model_cannot_assign_owner_or_initiative_type(self):
        for field in ('assumption_owner','work_kind'):
            self.model.custom = {'reply':'Choose this.', 'questions':[], 'suggestions':[{'field':field,'text':'sam' if field=='assumption_owner' else 'digital','rationale':'Model choice','basis':'hypothesis','citations':[]}]}
            with self.assertRaises(ModelUnavailable):self.coach(field)
            self.assertEqual(self.model.schema['properties']['suggestions']['maxItems'],0)
    def test_measurement_advice_has_a_readable_size_bound(self):
        self.model.custom = {'reply':'Candidate measures.', 'questions':[], 'suggestions':[{'field':'measures','text':'x'*1201,'rationale':'Too much detail.','basis':'hypothesis','citations':[]}]}
        with self.assertRaises(ModelUnavailable):self.coach('measures')
        self.assertEqual(self.model.schema['properties']['suggestions']['items']['properties']['text']['maxLength'],1200)
        self.assertEqual(self.model.schema['properties']['reply']['maxLength'],800)
        self.assertFalse(self.ws.coaching.records('intake-coach-run'))
    def test_long_feedback_or_multiple_followups_are_rejected_without_saving(self):
        before = self.ref()
        question = {'field':'why_now','question':'What makes this a priority?','reason':'Focus the decision.','based_on':['business_challenge']}
        for response in (
            {'reply':'x'*801,'suggestions':[],'questions':[]},
            {'reply':'Consider priority.','suggestions':[],'questions':[question,deepcopy(question)]},
            {'reply':'Consider priority.','suggestions':[],'questions':[{**question,'question':'x'*241}]},
            {'reply':'Consider priority.','questions':[],'suggestions':[{'field':'why_now','text':'x'*1201,'rationale':'Too long.','basis':'hypothesis','citations':[]}]},
        ):
            with self.subTest(response=response):
                self.model.custom=response
                with self.assertRaises(ModelUnavailable):self.coach('why_now')
                self.assertEqual(self.ref(),before)
                self.assertFalse(self.ws.coaching.records('intake-coach-run'))
        self.assertEqual(self.model.schema['properties']['questions']['maxItems'],1)
    def test_ui_receives_current_agent_version_to_separate_older_advice(self):
        self.assertEqual(self.ws.coaching.state()['agent_version'],self.ws.coaching.agent.version)
    def test_type_coaching_is_available_before_proposition_review(self):
        self.ws.command('intake-save', {'expected':self.ref(),'step':'value','value':'Changed proposition'})
        self.coach('work_kind')
        self.assertEqual(self.model.context['working_value_proposition']['status'],'draft')
        self.assertFalse(self.ws.intake.value_checkpoint(self.ws.intake.draft()['body'])['current'])
    def test_private_guidance_does_not_expose_answers_to_another_profile(self):
        self.coach('measures')
        other=Workspace(self.store,'sam',self.model).coaching.state()
        self.assertEqual(other['runs'],[])
        self.assertEqual(other['sources'],[])

if __name__ == '__main__':unittest.main()

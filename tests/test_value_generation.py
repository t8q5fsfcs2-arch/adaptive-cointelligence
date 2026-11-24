"""Synthesis prepares wording; explicit adoption preserves the answer basis and prior draft."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store, StaleBasis
from workbench.intake import PRIVATE
from workbench.model_provider import ModelUnavailable
from workbench.workspace import Workspace
from test_coaching import RecordingModel


class ValueGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'generation.sqlite3')
        self.model=RecordingModel()
        self.output={'reply':'A partial proposition based on the stated challenge.', 'suggestions':[{
            'field':'value','text':'For people enrolling, preserving progress may reduce repeat work. The approach remains to be investigated.',
            'rationale':'Connects the stated problem and users without inventing a solution.', 'basis':'hypothesis','citations':[]}], 'questions':[]}
        self.model.custom=deepcopy(self.output)
        self.ws=Workspace(self.store,'priya',self.model)
        self.ws.command('intake-start',{'title':'Fictional synthesis QA'})
        self.save(business_challenge='People may lose enrollment progress.',beneficiaries='People completing enrollment.')

    def tearDown(self):self.store.close();self.tmp.cleanup()
    def ref(self):return asdict(self.ws.intake.draft()['ref'])
    def save(self,**values):return self.ws.command('intake-save',{'expected':self.ref(),'step':'value',**values})
    def generate(self):return self.ws.command('intake-coach',{'expected':self.ref(),'skill':'compose-value','message':'Generate from my answers','sources':[],'consent':True})['ref']
    def use(self,run,**kw):return self.ws.command('intake-coach-apply',{'expected':self.ref(),'run_id':run['id'],'field':'value','confirm':True,**kw})

    def test_partial_answers_generate_one_editable_output_without_accepting(self):
        before=self.ref();run=self.generate()
        self.assertEqual(self.ref(),before)
        self.assertEqual(self.model.context['values']['value'],'')
        suggestion_schema=self.model.schema['properties']['suggestions']
        self.assertEqual(suggestion_schema['minItems'],1)
        self.assertEqual(suggestion_schema['items']['properties']['field']['enum'],['value'])
        self.use(run)
        body=self.ws.intake.draft()['body']
        self.assertEqual(body['values']['value'],self.output['suggestions'][0]['text'])
        self.assertEqual(body['field_provenance']['value']['answer_basis'],before)
        self.assertEqual(body['field_provenance']['value']['origin'],'generated-from-answers')
        self.assertFalse(self.ws.state()['intake']['value_checkpoint']['current'])
        self.assertIsNone(self.ws.intake.latest('INT-001'))

    def test_refresh_keeps_existing_edit_until_used_and_retains_predecessor(self):
        self.save(value='My carefully edited statement.');before=self.ws.intake.draft()
        run=self.generate()
        self.assertEqual(self.model.context['values']['value'],'My carefully edited statement.')
        self.assertEqual(self.ws.intake.draft(),before)
        self.use(run,edited_text='My revision of the generated suggestion.')
        body=self.ws.intake.draft()['body']
        self.assertEqual(body['values']['value'],'My revision of the generated suggestion.')
        self.assertEqual(body['field_provenance']['value']['status'],'sponsor-edited-after-coaching')
        self.assertEqual(body['field_provenance']['value']['text'],self.output['suggestions'][0]['text'])
        self.assertEqual(self.store.read(before['ref'],{PRIVATE}),before)

    def test_cannot_generate_without_answers_or_use_empty_wording(self):
        self.save(business_challenge='',beneficiaries='')
        with self.assertRaises(ValueError):self.generate()
        self.assertIsNone(self.model.context)
        self.save(need='A proposed need to investigate');run=self.generate()
        with self.assertRaises(ValueError):self.use(run,edited_text='  ')

    def test_rejects_missing_output_and_wrong_field(self):
        for suggestions in ([],[{**self.output['suggestions'][0],'field':'business_challenge'}]):
            with self.subTest(suggestions=suggestions):
                self.model.custom={**deepcopy(self.output),'suggestions':suggestions}
                with self.assertRaises(ModelUnavailable):self.generate()
                self.assertEqual(self.ws.intake.draft()['body']['values']['value'],'')

    def test_changes_during_generation_cannot_overwrite_the_intake(self):
        self.model.during=lambda:self.save(value='Typed while the model was running.')
        with self.assertRaises(StaleBasis):self.generate()
        self.assertEqual(self.ws.intake.draft()['body']['values']['value'],'Typed while the model was running.')

    def test_changed_answers_block_adoption_and_duplicate_apply(self):
        run=self.generate();self.save(beneficiaries='A different user group.')
        with self.assertRaises(StaleBasis):self.use(run)
        run=self.generate();self.use(run)
        with self.assertRaises(ValueError):self.use(run)

    def test_generation_failure_keeps_current_draft(self):
        self.save(value='Keep this wording.')
        self.model.custom={'invalid':'response'}
        with self.assertRaises(ModelUnavailable):self.generate()
        self.assertEqual(self.ws.intake.draft()['body']['values']['value'],'Keep this wording.')

    def test_generation_cannot_treat_the_output_as_an_input_question(self):
        self.model.custom['questions']=[{'field':'value','question':'Write the whole proposition?', 'reason':'Missing', 'based_on':['business_challenge']}]
        with self.assertRaises(ModelUnavailable):self.generate()

    def test_generated_material_is_private(self):
        run=self.generate();self.use(run)
        for actor in ('sam','maya','alex'):
            state=Workspace(self.store,actor,self.model).state()
            self.assertEqual(state['coaching']['runs'],[])
            self.assertIsNone(state['intake']['draft'])

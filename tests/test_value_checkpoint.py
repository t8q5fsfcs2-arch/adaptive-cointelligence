from dataclasses import asdict
import json
import unittest

import test_intake
from test_intake import VALUE, CONTEXT
from test_coaching import RecordingModel
from workbench.core import StaleBasis
from workbench.decisions import DecisionBlocked
from workbench.intake import Intake, PRIVATE
from workbench.model_provider import ModelUnavailable
from workbench.workspace import Workspace


class ValueCheckpointTests(unittest.TestCase):
    setUp = test_intake.IntakeTests.setUp
    tearDown = test_intake.IntakeTests.tearDown
    ref = test_intake.IntakeTests.ref
    accept_value = test_intake.IntakeTests.accept_value

    def write_value(self, **overrides):
        self.sponsor.save({'expected':self.ref(),'step':'value',**VALUE,**overrides})

    def test_saving_and_coaching_do_not_accept_or_authorize(self):
        self.write_value()
        w=Workspace(self.store,'priya',RecordingModel())
        before=self.ref()
        w.command('intake-coach',{'expected':before,'skill':'review-value','message':'Review the whole case','sources':[],'consent':True})
        self.assertEqual(self.ref(),before)
        self.assertFalse(w.state()['intake']['value_checkpoint']['current'])
        self.assertIsNone(self.sponsor.latest('VALUE-ACCEPTANCE-001'))
        self.assertIsNone(self.sponsor.latest('INT-001'))
        self.assertEqual(w.state()['packets'],[])

    def test_drafting_is_open_but_sharing_still_requires_review(self):
        self.write_value()
        model=RecordingModel();w=Workspace(self.store,'priya',model)
        w.command('intake-save',{'expected':self.ref(),'step':'context',**CONTEXT})
        w.command('intake-build',{'expected':self.ref()})
        drawers=self.sponsor.draft()['body']['scaffold']
        w.command('intake-drawers',{'expected':self.ref(),'drawers':drawers})
        w.command('intake-coach',{'expected':self.ref(),'skill':'context-questions','message':'Help','consent':True})
        self.assertIsNone(model.context['accepted_value_proposition'])
        self.assertEqual(model.context['working_value_proposition']['status'],'draft')
        with self.assertRaises(DecisionBlocked):w.command('intake-request',{'expected':self.ref(),'confirm':True})
        self.assertIsNone(self.sponsor.latest('INT-001'))
        self.assertIsNone(self.sponsor.latest('VALUE-ACCEPTANCE-001'))

    def test_acceptance_requires_sponsor_confirmation_complete_basis_and_current_revision(self):
        self.write_value(jobs='')
        with self.assertRaises(DecisionBlocked): self.accept_value()
        old=self.ref();self.write_value()
        with self.assertRaises(StaleBasis):self.sponsor.accept_value({'expected':old,'confirm':True})
        with self.assertRaises(ValueError):self.sponsor.accept_value({'expected':self.ref()})
        with self.assertRaises(PermissionError):Intake(self.store,'sam').accept_value({'expected':self.ref(),'confirm':True})
        self.accept_value()
        self.assertTrue(self.sponsor.state()['value_checkpoint']['current'])
        self.assertIsNone(self.sponsor.latest('INT-001'))
        self.assertEqual(self.sponsor.latest('VALUE-ACCEPTANCE-001')['body']['execution'],'not-authorized')

    def test_context_edits_keep_acceptance_but_value_edits_require_new_review(self):
        self.write_value();self.accept_value()
        original=self.sponsor.latest('VALUE-ACCEPTANCE-001')
        self.sponsor.save({'expected':self.ref(),'step':'context',**CONTEXT})
        self.assertTrue(self.sponsor.state()['value_checkpoint']['current'])
        self.sponsor.save({'expected':self.ref(),'step':'value','need':'A changed need'})
        cp=self.sponsor.state()['value_checkpoint']
        self.assertFalse(cp['current']);self.assertEqual(cp['changed_fields'],['need'])
        with self.assertRaises(ValueError):self.sponsor.accept_value({'expected':self.ref(),'confirm':True})
        self.accept_value()
        new=self.sponsor.latest('VALUE-ACCEPTANCE-001')
        self.assertEqual(new['ref'].revision,2)
        self.assertEqual(new['body']['supersedes'],asdict(original['ref']))
        self.assertEqual(self.store.read(original['ref'],{PRIVATE}),original)
        self.assertEqual(self.sponsor.draft()['body']['values']['user_situation'],CONTEXT['user_situation'])

    def test_acceptance_is_private_until_sponsor_releases_direction(self):
        self.write_value();self.accept_value()
        for actor in ('sam','maya','alex'):
            state=Workspace(self.store,actor).state()
            self.assertIsNone(state['intake']['value_checkpoint'])
            self.assertNotIn('VALUE-ACCEPTANCE-001',json.dumps(state,default=str))
        self.sponsor.save({'expected':self.ref(),'step':'context',**CONTEXT})
        self.sponsor.build({'expected':self.ref()})
        case=self.sponsor.request({'expected':self.ref(),'confirm':True})['id']
        snapshot=Intake(self.store,'sam').latest(case)['body']['snapshot']
        self.assertEqual(snapshot['value_acceptance']['status'],'reviewed-starting-proposition')

    def test_context_agent_receives_exact_accepted_proposition(self):
        self.write_value();self.accept_value()
        model=RecordingModel();w=Workspace(self.store,'priya',model)
        w.command('intake-coach',{'expected':self.ref(),'skill':'context-questions','message':'Help','consent':True})
        self.assertEqual(model.context['phase'],'context')
        self.assertEqual(model.context['accepted_value_proposition']['values']['jobs'],VALUE['jobs'])
        self.assertEqual(model.context['accepted_value_proposition']['ref'],asdict(self.sponsor.latest('VALUE-ACCEPTANCE-001')['ref']))
        self.assertEqual(w.coaching.records('intake-coach-run')[-1]['body']['accepted_value'],model.context['accepted_value_proposition']['ref'])

    def test_value_coach_stays_with_proposition_and_cannot_advance_context(self):
        self.write_value();model=RecordingModel();w=Workspace(self.store,'priya',model)
        model.custom={'reply':'Clarify the proposed gain.', 'suggestions':[], 'questions':[{'field':'gains','question':'What gain matters most?','reason':'Make the intended value specific.','based_on':['value']}]}
        w.command('intake-coach',{'expected':self.ref(),'skill':'review-value','message':'Review','consent':True})
        self.assertEqual(model.context['phase'],'value')
        self.assertNotIn('user_situation',model.schema['properties']['questions']['items']['properties']['field']['enum'])
        model.custom['questions'][0]['field']='user_situation'
        with self.assertRaises(ModelUnavailable):
            w.command('intake-coach',{'expected':self.ref(),'skill':'review-value','message':'Review','consent':True})

    def test_applying_coach_wording_reopens_checkpoint_without_erasing_prior(self):
        self.write_value();self.accept_value()
        model=RecordingModel();w=Workspace(self.store,'priya',model)
        model.custom={'reply':'Try this synthesis.','questions':[],'suggestions':[{'field':'value','text':'A new proposed value, to test.','rationale':'Relates the job and benefit.','basis':'hypothesis','citations':[]}]}
        run=w.command('intake-coach',{'expected':self.ref(),'skill':'review-value','message':'Review','consent':True})
        w.command('intake-coach-apply',{'expected':self.ref(),'run_id':run['ref']['id'],'field':'value','confirm':True})
        self.assertEqual(self.sponsor.state()['value_checkpoint']['status'],'needs-review')
        self.assertEqual(self.sponsor.latest('VALUE-ACCEPTANCE-001')['body']['values']['value'],VALUE['value'])


if __name__=='__main__': unittest.main()

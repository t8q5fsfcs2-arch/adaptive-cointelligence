from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import json
import tempfile
import unittest

from workbench.core import Store, Ref, StaleBasis
from workbench.workspace import Workspace
from workbench.intake import PRIVATE, ALL_FIELDS
from workbench.expertise_methods import METHODS, grounding, configured_methods
from workbench.agent_quality import CASES, digest
from workbench.agent_runs import monitoring
from workbench.model_provider import ModelUnavailable, UnconfiguredModel


class TestModel:
    def __init__(self):self.calls=[];self.fail_assessment=False;self.fail_agent=False;self.during=None;self.bad_rating=False
    def status(self):return dict(configured=True,provider='TEST DOUBLE',model='synthetic')
    def generate(self,**kw):
        self.calls.append(deepcopy(kw));c=kw['context']
        if self.during:self.during()
        if 'candidate_response' in c:
            if self.fail_assessment:raise ModelUnavailable('Synthetic assessment failure')
            output={x['id']:dict(rating='pass',note='Synthetic rating, not semantic validation.') for x in c['case']['criteria']}
            if self.bad_rating:output['invented']={}
        elif self.fail_agent:raise ModelUnavailable('Synthetic agent failure')
        elif 'drawer' in c:
            output=dict(summary='Review the boundary.',requirement='Resume the saved draft.' if c['skill']=='draft' else '',
                acceptance_criteria=['Saved fields reappear.'] if c['skill']=='draft' else [],rationale='Supports continuity.',basis_fields=['value'],findings=[],open_questions=[])
        else:
            output=dict(reply='A focused improvement.',suggestions=[],questions=[])
            if c['skill']=='compose-value':output['suggestions']=[dict(field='value',text='A proposed benefit for coordinators.',rationale='Supplied basis.',basis='hypothesis',citations=[])]
        return dict(output=output,usage=dict(total_tokens=12),model='synthetic')


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'quality.sqlite3';self.store=Store(self.path)
        self.model=TestModel();self.ws=Workspace(self.store,'priya',self.model)
        self.ws.command('intake-start',{'title':'Private project title sentinel'})
        self.ws.command('intake-save',dict(expected=asdict(self.ws.intake.draft()['ref']),step='value',value='PRIVATE INTAKE SENTINEL'))
        self.ws.command('intake-source',dict(title='Private source sentinel',text='PRIVATE DOCUMENT SENTINEL',kind='notes',role='hypothesis'))
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def run_case(self,id='priority',**kw):
        return self.ws.command('agent-quality-run',dict(case_id=id,expected=digest(self.ws.quality.signature(CASES[id])),consent=True,**kw))
    def method(self,persona='P02',id='priority',**kw):
        return self.ws.command('agent-method-save',dict(persona_id=persona,method_id=id,expected=configured_methods(self.ws.intake,persona)['ref'],guidance='Emphasize OPPORTUNITY COST.',example='Fictional: explain what waits if we choose this initiative.',**kw))
    def test_each_question_has_method_and_each_case_uses_real_role_contract(self):
        for field in ALL_FIELDS:self.assertTrue(grounding('P02','coach-field',field)['methods'],field)
        for case in CASES.values():
            r=self.run_case(case['id']);self.assertEqual(r['status'],'assessed',case['id'])
            row=self.store.read(Ref(**r['ref']),{PRIVATE})['body']
            self.assertEqual(row['signature']['mode'],'simulated')
            self.assertIsNone(row['human_review']);self.assertTrue(row['output'])
            self.assertEqual(set(row['assessment']),{c['id'] for c in case['criteria']})
        self.assertEqual(len(self.model.calls),2*len(CASES))
    def test_evaluation_isolated_from_saved_inputs_and_durable(self):
        before=self.ws.intake.draft();result=self.run_case();dump=json.dumps(self.model.calls)
        for sentinel in ('PRIVATE INTAKE SENTINEL','PRIVATE DOCUMENT SENTINEL','Private project title sentinel','Private source sentinel'):self.assertNotIn(sentinel,dump)
        self.assertEqual(self.ws.intake.draft(),before)
        self.assertEqual(self.ws.coaching.records('intake-coach-run'),[])
        self.store.close();self.store=Store(self.path);self.ws=Workspace(self.store,'priya',self.model)
        result=self.ws.quality.state()['results'][0]
        self.assertTrue(result['current']);self.assertIsNone(result['human_review']);self.assertEqual(result['status'],'assessed')
        summaries=monitoring(self.store,'priya')['summaries']
        self.assertEqual({s['purpose'] for s in summaries},{'evaluation','evaluation-assessment'})
    def test_method_refinement_reaches_preview_normal_run_and_evaluation_and_invalidates_prior(self):
        self.run_case();self.method()
        self.assertFalse(self.ws.quality.state()['results'][0]['current'])
        preview=self.ws.coaching.preview_instructions(dict(skill='coach-field',field='why_now'))
        self.assertIn('OPPORTUNITY COST',preview['instructions'])
        self.ws.coaching.run(dict(expected=asdict(self.ws.intake.draft()['ref']),skill='coach-field',field='why_now',consent=True))
        self.assertIn('OPPORTUNITY COST',self.model.calls[-1]['instructions'])
        self.run_case();self.assertIn('OPPORTUNITY COST',self.model.calls[-2]['instructions'])
        self.assertNotIn('OPPORTUNITY COST',self.model.calls[-1]['instructions'])
        self.assertTrue(self.ws.quality.state()['results'][0]['current'])
    def test_requirement_methods_are_separate_config_and_reach_inference(self):
        old=self.ws.coaching.settings.coaching()['fingerprint'];self.method('P04','requirement')
        self.assertEqual(old,self.ws.coaching.settings.coaching()['fingerprint'])
        self.run_case('threshold');self.assertIn('OPPORTUNITY COST',self.model.calls[-2]['instructions'])
        self.assertIn('Testable requirements',self.model.calls[-2]['instructions'])
    def test_partial_and_failed_results_keep_output_and_do_not_become_quality_passes(self):
        self.model.fail_assessment=True;r=self.run_case();self.assertEqual(r['status'],'assessment-failed')
        row=self.ws.quality.state()['results'][0];self.assertTrue(row['output']);self.assertIsNone(row['assessment'])
        self.model.fail_agent=True;r=self.run_case();self.assertEqual(r['status'],'failed')
        row=self.ws.quality.state()['results'][0];self.assertIsNone(row['output']);self.assertIsNone(row['assessment'])
    def test_invalid_assessment_is_not_saved_as_success(self):
        self.model.bad_rating=True;r=self.run_case();self.assertEqual(r['status'],'assessment-failed')
        self.assertIsNone(self.ws.quality.state()['results'][0]['assessment'])
    def test_permissions_staleness_consent_and_unconfigured_model_fail_without_inference(self):
        for actor in ('sam','alex','maya'):
            ws=Workspace(self.store,actor,self.model)
            self.assertIsNone(ws.quality.state());self.assertIsNone(ws.methods.state())
            with self.assertRaises(PermissionError):ws.quality.run(dict(case_id='priority'))
            with self.assertRaises(PermissionError):ws.methods.save({})
            with self.assertRaises(PermissionError):ws.quality.review({})
        with self.assertRaises(StaleBasis):self.ws.quality.run(dict(case_id='priority',expected='old',consent=True))
        with self.assertRaises(ValueError):self.ws.quality.run(dict(case_id='priority',expected=digest(self.ws.quality.signature(CASES['priority'])),consent=False))
        ws=Workspace(self.store,'priya',UnconfiguredModel())
        with self.assertRaises(ModelUnavailable):ws.quality.run(dict(case_id='priority',expected=digest(ws.quality.signature(CASES['priority'])),consent=True))
        self.assertEqual(self.model.calls,[])
    def test_concurrent_configuration_change_retains_exact_evaluation_but_marks_it_earlier(self):
        def change():
            self.model.during=None;self.method()
        self.model.during=change;self.run_case()
        self.assertFalse(self.ws.quality.state()['results'][0]['current'])
        self.assertNotIn('OPPORTUNITY COST',self.model.calls[0]['instructions'])
    def test_human_review_is_explicit_versioned_and_never_auto_copied(self):
        result=self.run_case();ratings={c['id']:dict(rating='needs-work',note='Human found an omission.') for c in CASES['priority']['criteria']}
        payload=dict(expected=result['ref'],ratings=ratings,reviewer_context='Business analysis practitioner',note='Clarify priority comparison.')
        reviewed=self.ws.command('agent-quality-review',payload)
        row=self.store.read(Ref(**reviewed['ref']),{PRIVATE})['body']
        self.assertEqual(row['human_review']['reviewer'],'priya');self.assertEqual(row['assessment']['c1']['rating'],'pass')
        self.assertEqual(row['human_review']['ratings']['c1']['rating'],'needs-work')
        with self.assertRaises(StaleBasis):self.ws.command('agent-quality-review',payload)
        self.assertIsNone(self.store.read(Ref(**result['ref']),{PRIVATE})['body']['human_review'])
        self.run_case();self.assertIsNone(self.ws.quality.state()['results'][0]['human_review'])
    def test_method_metadata_is_not_overwritten_and_stale_changes_rejected(self):
        self.method();m=configured_methods(self.ws.intake,'P02')['methods']['priority']
        self.assertEqual(m['guidance'],METHODS['priority']['guidance']);self.assertEqual(m['source'],METHODS['priority']['source'])
        with self.assertRaises(StaleBasis):self.ws.methods.save(dict(persona_id='P02',method_id='priority',expected=None,guidance='New',example='New'))

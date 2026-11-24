from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store, StaleBasis, Ref
from workbench.workspace import Workspace
from workbench.intake import PRIVATE
from workbench.model_provider import ModelUnavailable, UnconfiguredModel


class RecordingModel:
    def __init__(self): self.calls=[]; self.fail_at=None; self.during=None
    def status(self): return dict(configured=True, provider='TEST DOUBLE', model='config-test')
    def generate(self, *, instructions, context, schema):
        self.calls.append(deepcopy(dict(instructions=instructions,context=context,schema=schema)))
        if self.during:self.during()
        if self.fail_at==len(self.calls):raise ModelUnavailable('Synthetic model failure')
        reply='Examine opportunity cost.' if 'OPPORTUNITY COST' in instructions else 'Clarify the benefit.'
        suggestions=[]
        if context['skill']=='compose-value':
            suggestions=[dict(field='value',text='A tentative benefit.',rationale='From supplied answers.',basis='hypothesis',citations=[])]
        return dict(model='config-test',usage={'input_tokens':10},output=dict(reply=reply,suggestions=suggestions,questions=[]))


class ExperimentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite3'
        self.store=Store(self.path);self.model=RecordingModel();self.ws=Workspace(self.store,'priya',self.model)
        self.ws.command('intake-start',{'title':'Synthetic comparison'})
        self.ws.command('intake-save',dict(expected=self.basis(),step='value',business_challenge='Repeated data entry.',need='Less repeated effort.',why_now='It seems important.',value='Reduce repeated effort.'))
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def basis(self):return asdict(self.ws.intake.draft()['ref'])
    def payload(self, **extras):
        current=self.ws.coaching.settings.coaching();p=deepcopy(current['config']['questions']['why_now'])
        p['quality_checks'].append('Focus on OPPORTUNITY COST.')
        return dict(expected=current['ref'],draft_expected=self.basis(),area='question',key='why_now',config=p,
                    consent=True,test_answer='This is a test answer.',**extras)
    def compare(self,data=None):return self.ws.command('coach-settings-test',data or self.payload())
    def test_frozen_comparison_is_separate_from_intake_and_normal_coaching(self):
        before=self.ws.intake.draft();settings=self.ws.coaching.settings.coaching()
        result=self.compare();self.assertEqual(result['status'],'completed');self.assertTrue(result['current'])
        self.assertEqual(self.ws.intake.draft(),before);self.assertEqual(self.ws.coaching.settings.coaching(),settings)
        self.assertEqual(self.ws.coaching.records('intake-coach-run'),[])
        a,b=self.model.calls
        for key in ('values','sources','working_answer','profile','phase','message','prior_dialogue','accepted_value_proposition'):
            self.assertEqual(a['context'][key],b['context'][key],key)
        self.assertEqual(a['context']['values']['why_now'],'This is a test answer.')
        self.assertEqual(a['context']['prior_dialogue'],[])
        self.assertNotIn('OPPORTUNITY COST',a['instructions']);self.assertIn('OPPORTUNITY COST',b['instructions'])
        self.assertNotEqual(result['results']['current']['output'],result['results']['proposed']['output'])
        self.store.close();self.store=Store(self.path);self.ws=Workspace(self.store,'priya',self.model)
        saved=self.store.read(Ref(**result['ref']),{PRIVATE})['body']
        self.assertEqual(saved['results']['proposed']['instructions'],b['instructions'])
        self.assertEqual(saved['results']['current']['context']['values'],a['context']['values'])
        self.assertEqual(saved['persona_id'],'P02');self.assertEqual(saved['provider'],'TEST DOUBLE')
    def test_activation_uses_exact_tested_config_and_next_real_request(self):
        data=self.payload();result=self.compare(data)
        saved=self.ws.command('coach-settings-save',{**data,'comparison':result['ref']})
        self.assertEqual(saved['ref']['revision'],1)
        self.ws.command('intake-coach',dict(expected=self.basis(),skill='coach-field',field='why_now',consent=True))
        c=self.model.calls[-1];self.assertIn('OPPORTUNITY COST',c['instructions'])
        self.assertEqual(c['context']['working_answer']['text'],'It seems important.')
        self.assertEqual(self.ws.intake.latest('SETTINGS-COACH')['body']['comparison'],result['ref'])
    def test_changed_edits_or_intake_cannot_claim_tested_activation(self):
        data=self.payload();r=self.compare(data)
        modified=deepcopy(data);modified['config']['answer_goal']='A different goal.'
        with self.assertRaises(StaleBasis):self.ws.command('coach-settings-save',{**modified,'comparison':r['ref']})
        self.ws.command('intake-save',dict(expected=self.basis(),step='value',why_now='Changed while testing.'))
        with self.assertRaises(StaleBasis):self.ws.command('coach-settings-save',{**data,'comparison':r['ref']})
        self.assertIsNone(self.ws.coaching.settings.coaching()['ref'])
    def test_partial_failure_retains_success_and_cannot_activate_as_tested(self):
        data=self.payload();self.model.fail_at=2;r=self.compare(data)
        self.assertEqual(r['status'],'partial');self.assertEqual(r['results']['current']['status'],'completed')
        self.assertEqual(r['results']['proposed']['error'],'Synthetic model failure')
        self.assertEqual(len(self.ws.coaching.records('coach-config-test')),1)
        with self.assertRaises(ValueError):self.ws.command('coach-settings-save',{**data,'comparison':r['ref']})
    def test_permissions_consent_stale_and_unchanged_fail_before_model_calls(self):
        with self.assertRaises(PermissionError):Workspace(self.store,'sam',self.model).command('coach-settings-test',self.payload())
        data=self.payload();data['consent']=False
        with self.assertRaises(ValueError):self.compare(data)
        data=self.payload();data['draft_expected']={'id':'INTAKE-001','revision':1}
        with self.assertRaises(StaleBasis):self.compare(data)
        data=self.payload();data['config']=deepcopy(self.ws.coaching.settings.coaching()['config']['questions']['why_now'])
        with self.assertRaisesRegex(ValueError,'Change the AI partner instructions'):self.compare(data)
        self.assertEqual(self.model.calls,[])
    def test_invalid_configuration_or_sources_fail_before_calls(self):
        data=self.payload();data['config']['connections']=['private-domain']
        with self.assertRaises(ValueError):self.compare(data)
        data=self.payload();data['test_answer']='x'*20001
        with self.assertRaises(ValueError):self.compare(data)
        data=self.payload();data['sources']=[self.basis()]
        with self.assertRaises(ValueError):self.compare(data)
        self.assertEqual(self.model.calls,[])
    def test_changed_settings_during_inference_preserve_historical_test_but_mark_stale(self):
        data=self.payload();changed=False
        def update():
            nonlocal changed
            if not changed:
                changed=True
                self.ws.command('coach-settings-save',data)
        self.model.during=update;r=self.compare(data)
        self.assertFalse(r['current']);self.assertEqual(r['status'],'completed')
        self.assertEqual(self.model.calls[0]['context']['values'],self.model.calls[1]['context']['values'])
        with self.assertRaises(StaleBasis):self.ws.command('coach-settings-save',{**data,'comparison':r['ref']})
    def test_missing_model_never_uses_a_substitute(self):
        self.ws.coaching.agent.model=UnconfiguredModel()
        with self.assertRaises(ModelUnavailable):self.compare()
        self.assertEqual(self.ws.coaching.records('coach-config-test'),[])
    def test_shared_persona_and_skill_changes_reach_their_actual_tasks(self):
        data=self.payload();data.update(area='persona',key='',field='why_now',config=dict(name='Coach',remit='Focus on OPPORTUNITY COST.',style='Be concise.'))
        self.compare(data);self.assertIn('OPPORTUNITY COST',self.model.calls[-1]['instructions'])
        data=self.payload();data.pop('test_answer');data.update(area='skill',key='compose-value',config={'instructions':'Explain OPPORTUNITY COST.'})
        r=self.compare(data);self.assertEqual(r['status'],'completed')
        self.assertEqual(self.model.calls[-1]['context']['skill'],'compose-value')
        self.assertEqual(self.model.calls[-1]['context']['values']['why_now'],'It seems important.')


if __name__=='__main__':unittest.main()

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
import tempfile
import unittest

from workbench.agent_runs import AgentRun, monitoring, execution_mode
from workbench.core import Store, Ref, StaleBasis
from workbench.intake import PRIVATE
from workbench.workspace import Workspace
from workbench.model_provider import ModelUnavailable, OpenAIModel, UnconfiguredModel
from workbench.requirement_assistant import RequirementAgent, settings
from test_intake import VALUE, CONTEXT

class RequirementTestModel:
    def __init__(self): self.calls=[]; self.during=None; self.bad=None; self.fail=False
    def status(self): return dict(configured=True,provider='TEST DOUBLE',model='fake')
    def generate(self,**kwargs):
        self.calls.append(deepcopy(kwargs)); ctx=kwargs['context']
        if self.during:self.during()
        if self.fail:raise ModelUnavailable('sensitive provider body must not enter telemetry')
        out=dict(summary='The requirement connects resumption to reduced repetition.',
            requirement='A customer can resume enrollment from the last saved step.' if ctx['skill']=='draft' else '',
            acceptance_criteria=['Resuming shows the previously saved step.'] if ctx['skill']=='draft' else [],
            rationale='Connects the stated job with reduced repeated effort.',basis_fields=['jobs','value'],
            findings=[],open_questions=['Which interruption scenarios need validation?'])
        if self.bad:self.bad(out)
        return dict(output=out,model='fake',usage=dict(input_tokens=30,output_tokens=20,total_tokens=50))

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3';self.store=Store(self.path)
        self.model=RequirementTestModel();self.ws=Workspace(self.store,'priya',self.model)
        self.ws.intake.start({'title':'Synthetic runtime test'})
        self.ws.intake.save(dict(expected=self.ref(),step='value',**VALUE))
        self.ws.intake.accept_value(dict(expected=self.ref(),confirm=True))
        self.ws.intake.save(dict(expected=self.ref(),step='context',**CONTEXT))
        self.ws.intake.build(dict(expected=self.ref()))
        self.key=self.ws.intake.draft()['body']['scaffold'][0]['key']
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def ref(self):return asdict(self.ws.intake.draft()['ref'])
    def run_agent(self,**kw):return self.ws.command('requirement-agent-run',{**dict(expected=self.ref(),skill='draft',drawer=self.key,consent=True),**kw})
    def apply(self,result,**kw):
        b=self.store.read(Ref(**result['ref']),{PRIVATE})['body']
        return self.ws.command('requirement-agent-apply',{**dict(result=result['ref'],expected=self.ref(),confirm=True,
            requirement=b['output']['requirement'],acceptance_criteria='\n'.join(b['output']['acceptance_criteria'])),**kw})
    def monitor(self):return monitoring(self.store,'priya')
    def test_requirement_preparation_works_on_unreviewed_draft_without_authorizing_it(self):
        self.ws.intake.save(dict(expected=self.ref(),step='value',value='Changed proposed benefit'))
        self.ws.intake.build(dict(expected=self.ref(),confirm=True))
        before=self.ref();self.run_agent()
        self.assertIsNone(self.model.calls[-1]['context']['accepted_value'])
        self.assertEqual(self.ref(),before)
        self.assertIsNone(self.ws.intake.latest('INT-001'))

    def test_draft_is_durable_and_only_explicit_use_changes_drawer(self):
        before=self.ref();result=self.run_agent();self.assertEqual(before,self.ref())
        ctx=self.model.calls[0]['context'];self.assertEqual(ctx['values']['value'],VALUE['value'])
        self.assertEqual(ctx['drawer']['key'],self.key)
        self.assertEqual(self.monitor()['runs'][0]['status'],'succeeded')
        self.assertEqual(self.monitor()['runs'][0]['mode'],'simulated')
        self.assertEqual(self.monitor()['summaries'][0]['tokens'],50)
        self.apply(result,requirement='Human refinement of the proposed resumption requirement.')
        drawer=self.ws.intake.draft()['body']['scaffold'][0]
        self.assertEqual(drawer['requirement'],'Human refinement of the proposed resumption requirement.')
        self.assertTrue(drawer['agent_provenance']['edited']);self.assertTrue(self.monitor()['runs'][0]['applied'])
        self.assertIsNone(self.ws.intake.latest('INT-001'))
        self.store.close();self.store=Store(self.path);self.ws=Workspace(self.store,'priya',self.model)
        self.assertEqual(self.monitor()['runs'][0]['status'],'succeeded')
        self.assertEqual(len(self.ws.requirement_agent.state()['runs']),1)
        with self.assertRaises(ValueError):self.apply(result)
    def test_review_has_distinct_contract_and_is_never_adoptable(self):
        self.apply(self.run_agent(),requirement='Human-selected current requirement.');before=self.ref();result=self.run_agent(skill='review')
        self.assertEqual(self.model.calls[-1]['context']['drawer']['requirement'],'Human-selected current requirement.')
        self.assertNotIn('agent_provenance',self.model.calls[-1]['context']['drawer'])
        self.assertIn('agent_provenance',self.ws.intake.draft()['body']['scaffold'][0])
        self.assertEqual(self.ref(),before)
        self.assertIn('Review the selected requirement',self.model.calls[-1]['instructions'])
        with self.assertRaises(ValueError):self.apply(result)
        self.model.bad=lambda out:out.update(requirement='An unauthorized replacement')
        with self.assertRaises(ModelUnavailable):self.run_agent(skill='review')
        self.assertEqual(self.monitor()['runs'][0]['status'],'failed');self.assertEqual(self.ref(),before)
    def test_configuration_reaches_model_and_old_results_cannot_be_used(self):
        result=self.run_agent();c=settings(self.ws.intake)
        self.ws.command('requirement-agent-settings',dict(expected=c['ref'],draft='Emphasize accessibility and explicitly ask about unknown constraints.',review=c['config']['review']))
        with self.assertRaises(StaleBasis):self.apply(result)
        self.run_agent();self.assertIn('Emphasize accessibility',self.model.calls[-1]['instructions'])
        self.assertEqual(self.monitor()['runs'][0]['configuration']['revision'],1)
    def test_permission_consent_and_saved_basis_block_before_inference(self):
        for actor in ('alex','sam','maya'):
            with self.assertRaises(PermissionError):Workspace(self.store,actor,self.model).command('requirement-agent-run',dict(expected=self.ref(),skill='draft',drawer=self.key,consent=True))
            state=Workspace(self.store,actor,self.model).state()
            self.assertIsNone(state['requirement_agent']);self.assertIsNone(state['agent_monitoring'])
        with self.assertRaises(ValueError):self.run_agent(consent=False)
        with self.assertRaises(ValueError):self.run_agent(drawer='missing')
        with self.assertRaises(StaleBasis):self.run_agent(expected={'id':'INTAKE-001','revision':1})
        self.assertEqual(self.model.calls,[]);self.assertEqual(self.monitor()['runs'],[])
    def test_failure_and_invalid_references_are_counted_without_fabricating_output(self):
        before=self.ref();self.model.fail=True
        with self.assertRaises(ModelUnavailable):self.run_agent()
        m=self.monitor();self.assertEqual(m['summaries'][0]['failed'],1)
        self.assertNotIn('sensitive provider body',str(m));self.assertIsNone(m['runs'][0]['usage'])
        self.assertEqual(self.ws.requirement_agent.state()['runs'],[])
        self.model.fail=False;self.model.bad=lambda out:out.update(basis_fields=['invented'])
        with self.assertRaises(ModelUnavailable):self.run_agent()
        self.assertEqual(self.ref(),before);self.assertEqual(self.monitor()['summaries'][0]['failed'],2)
    def test_intake_and_config_races_reject_result_but_keep_execution_receipt(self):
        self.model.during=lambda:self.ws.intake.save(dict(expected=self.ref(),step='context',in_scope='Changed while request ran'))
        with self.assertRaises(StaleBasis):self.run_agent()
        m=self.monitor();self.assertEqual(m['runs'][0]['status'],'stale');self.assertEqual(m['runs'][0]['usage']['total_tokens'],50)
        self.assertEqual(self.ws.requirement_agent.state()['runs'],[])
    def test_modes_are_code_owned_and_live_metrics_exclude_test_doubles(self):
        self.assertEqual(execution_mode(OpenAIModel('unused-key','unused-model')),'live')
        self.assertEqual(execution_mode(UnconfiguredModel()),'not-connected')
        self.run_agent();self.assertFalse(any(s['mode']=='live' for s in self.monitor()['summaries']))
        registry=self.ws.coaching.settings.agent_registry()
        p4=next(p for p in registry['profiles'] if p['id']=='P04');self.assertEqual(p4['implementation']['label'],'Simulated')
        p6=next(p for p in registry['profiles'] if p['id']=='P06');self.assertEqual(p6['implementation']['label'],'Simulated')
        self.ws.command('agent-descriptor-save',dict(expected=None,persona_id='P06',descriptor='New name',mode='live'))
        self.assertEqual(next(p for p in self.ws.coaching.settings.agent_registry()['profiles'] if p['id']=='P06')['implementation']['label'],'Simulated')
    def test_pending_runs_have_unknown_outcome_after_timeout_and_windows_are_separate(self):
        agent=RequirementAgent(self.model)
        run=AgentRun(self.store,'priya',agent,'draft',self.ref(),purpose='configuration-test')
        b=run.body;b['started_at']=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
        self.store.put(run.ref.id,'agent-execution',PRIVATE,b,run.ref.revision)
        self.run_agent()
        m=self.monitor();self.assertEqual(len(m['summaries']),2)
        test=next(s for s in m['summaries'] if s['purpose']=='configuration-test')
        self.assertEqual(test['unknown'],1);self.assertIsNone(test['completion_rate']);self.assertIsNone(test['tokens']);self.assertIsNone(test['cost'])
        self.assertEqual(len(m['runs']),2)
    def test_config_change_during_inference_is_a_stale_run(self):
        def change():
            c=settings(self.ws.intake)
            self.ws.requirement_agent.configure(dict(expected=c['ref'],draft='Changed drafting instructions',review=c['config']['review']))
        self.model.during=change
        with self.assertRaises(StaleBasis):self.run_agent()
        self.assertEqual(self.monitor()['runs'][0]['status'],'stale')
        self.assertEqual(self.ws.requirement_agent.state()['runs'],[])

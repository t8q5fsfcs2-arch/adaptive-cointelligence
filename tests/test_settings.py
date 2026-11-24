from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store, StaleBasis, Ref
from workbench.workspace import Workspace
from workbench.settings import PROFILES


class Model:
    def __init__(self): self.during = None; self.calls = 0
    def status(self): return {'configured':True,'provider':'TEST DOUBLE','model':'settings-test'}
    def generate(self, *, instructions, context, schema):
        self.calls += 1; self.instructions = instructions; self.context = deepcopy(context)
        if self.during: self.during()
        return {'model':'settings-test','output':{'reply':'Keep the intended benefit explicit.','questions':[],
            'suggestions':[{'field':context['field'],'text':'A qualified business reason.',
                            'rationale':'Preserve uncertainty.','basis':'hypothesis','citations':[]}]}}


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name)/'db.sqlite3'
        self.store = Store(self.path); self.model = Model(); self.ws = Workspace(self.store,'priya',self.model)
        self.ws.command('intake-start', {'title':'Synthetic settings project'})
        self.ws.command('intake-save', {'expected':asdict(self.ws.intake.draft()['ref']), 'step':'value',
                                      'business_challenge':'Repeated effort may delay enrollment.', 'value':'Reduce repeated effort.'})
    def tearDown(self): self.store.close(); self.tmp.cleanup()
    def config(self): return self.ws.coaching.settings.coaching()
    def save(self, area='question', key='why_now', config=None, **extra):
        if config is None:
            config = deepcopy(self.config()['config']['questions'][key]); config['expert_role']='Portfolio priority expert'
        return self.ws.command('coach-settings-save', {'expected':self.config()['ref'], 'area':area,'key':key,'config':config,**extra})
    def coach(self):
        return self.ws.command('intake-coach', {'expected':asdict(self.ws.intake.draft()['ref']), 'field':'why_now','skill':'coach-field','consent':True})
    def test_edit_survives_reopen_and_keeps_previous_version_and_rationale(self):
        self.assertIsNone(self.config()['ref'])
        first = self.save(reason='Use portfolio context')['ref']
        self.save('persona', config={'name':'Initiative coach','remit':'Clarify value.','style':'Concise and empathetic.'})
        self.store.close(); self.store = Store(self.path); self.ws = Workspace(self.store,'priya',self.model)
        self.assertEqual(self.config()['ref']['revision'],2)
        self.assertEqual(self.config()['config']['questions']['why_now']['expert_role'],'Portfolio priority expert')
        previous=self.ws.intake.latest('SETTINGS-COACH')
        self.assertEqual(previous['body']['previous'],first)
        from workbench.intake import PRIVATE
        self.assertEqual(self.store.read(Ref(**first),{PRIVATE})['body']['reason'],'Use portfolio context')
        self.assertEqual(PROFILES['why_now']['expert_role'],'Prioritization AI partner')
        self.assertEqual(self.model.calls,0)
    def test_saved_profile_persona_skill_and_exact_connections_reach_model_and_run(self):
        p=deepcopy(self.config()['config']['questions']['why_now']);p.update(expert_role='Portfolio coach',quality_checks=['Assess the opportunity cost.'],connections=['value'])
        self.save(config=p)
        self.save('persona',config={'name':'Strategy coach','remit':'Clarify strategic tradeoffs.','style':'Use short sentences.'})
        self.save('skill','coach-field',{'instructions':'Consider alternatives before recommending priority.'})
        preview=self.ws.command('coach-settings-preview',{'skill':'coach-field','field':'why_now'})
        run=self.coach();c=self.model.context
        self.assertEqual(preview['instructions'],self.model.instructions)
        self.assertIn('Portfolio coach',self.model.instructions);self.assertIn('Strategy coach',self.model.instructions)
        self.assertIn('Consider alternatives before recommending priority.',self.model.instructions)
        self.assertEqual(c['connected_answers'],[{'field':'value','text':'Reduce repeated effort.'}])
        self.assertEqual(c['expert_profile']['quality_checks'],['Assess the opportunity cost.'])
        saved=self.ws.intake.latest(run['ref']['id'])['body']
        self.assertEqual(saved['instructions'],self.model.instructions)
        self.assertEqual(saved['configuration'],self.config()['ref'])
        self.assertEqual(saved['configuration_fingerprint'],self.config()['fingerprint'])
    def test_old_advice_cannot_be_adopted_or_used_as_history_after_config_change(self):
        run=self.coach();self.save()
        with self.assertRaises(StaleBasis):
            self.ws.command('intake-coach-apply',{'expected':asdict(self.ws.intake.draft()['ref']), 'run_id':run['ref']['id'],'field':'why_now','confirm':True})
        self.coach();self.assertEqual(self.model.context['prior_dialogue'],[])
    def test_config_change_during_inference_rejects_result(self):
        self.model.during=lambda:self.save()
        with self.assertRaises(StaleBasis):self.coach()
        self.assertEqual(self.ws.coaching.records('intake-coach-run'),[])
    def test_stale_save_rejected_and_other_profile_cannot_read_or_edit(self):
        self.save()
        with self.assertRaises(StaleBasis):self.save(expected=None)
        other=Workspace(self.store,'sam',self.model)
        self.assertNotIn('settings',other.coaching.state())
        self.assertIsNone(other.coaching.settings.state())
        for action in ('coach-settings-save','integration-settings-save','coach-settings-preview','agent-descriptor-save'):
            with self.assertRaises(PermissionError):other.command(action,{})
    def test_invalid_connections_and_configuration_rejected_without_revision(self):
        p=deepcopy(self.config()['config']['questions']['why_now'])
        for connections in [['private-secret'],['value','value'],['why_now'],[{}]]:
            with self.subTest(connections=connections),self.assertRaises(ValueError):self.save(config={**p,'connections':connections})
        with self.assertRaises(ValueError):self.save(config={**p,'quality_checks':[]})
        with self.assertRaises(ValueError):self.save('skill','invented',{'instructions':'Grant tools'})
        self.assertIsNone(self.config()['ref'])
    def descriptor(self, key='P02', value='Business intent and priority partner', **extra):
        return self.ws.command('agent-descriptor-save', {'expected':self.ws.coaching.settings.agent_registry()['ref'],
            'persona_id':key,'descriptor':value,**extra})
    def test_inventory_is_source_linked_and_distinguishes_specs_from_runtime(self):
        registry=self.ws.coaching.settings.agent_registry()
        self.assertEqual([p['id'] for p in registry['profiles']],[f'P{i:02}' for i in range(1,15)])
        self.assertEqual(registry['source']['document_id'],'a59add43-b208-4689-9452-9f88c25ff3f8')
        bound=[p for p in registry['profiles'] if p['implementation']['runtime_id']]
        self.assertEqual([p['id'] for p in bound],['P02','P04','P06','P07','P12'])
        self.assertEqual(bound[0]['implementation']['status'],'partial')
        for p in registry['profiles']:
            for field in ['purpose','trigger','inputs','skills','output','boundaries','prior_work','source_nodes']:
                self.assertTrue(p[field])
        self.assertEqual(self.model.calls,0)
    def test_descriptors_persist_keep_history_and_cannot_enable_an_agent(self):
        before=self.config()['fingerprint']
        first=self.descriptor('P04','Requirements quality partner',reason='Clearer local name',runtime_id='new-agent',status='live')['ref']
        self.descriptor('P02','Intake partner')
        self.store.close();self.store=Store(self.path);self.ws=Workspace(self.store,'priya',self.model)
        registry=self.ws.coaching.settings.agent_registry()
        p4=next(p for p in registry['profiles'] if p['id']=='P04')
        self.assertEqual(p4['descriptor'],'Requirements quality partner')
        self.assertEqual(p4['implementation']['runtime_id'],'requirement-assistant')
        self.assertEqual(p4['implementation']['mode'],'simulated')
        self.assertEqual(registry['ref']['revision'],2)
        self.assertEqual(registry['history'][-1]['reason'],'Clearer local name')
        self.assertEqual(self.ws.intake.latest('SETTINGS-AGENTS')['body']['previous'],first)
        self.assertEqual(self.config()['fingerprint'],before)
        self.assertEqual(self.model.calls,0)
        with self.assertRaises(StaleBasis):self.descriptor(expected=None)
        for key,value in [('P99','Unknown'),('P02',''),('P02','x'*601)]:
            with self.assertRaises(ValueError):self.descriptor(key,value)
    def test_new_runs_pin_persona_catalog_and_descriptor_without_relabeling_old_runs(self):
        self.descriptor(value='Priority advisor')
        first=self.coach();old=self.ws.intake.latest(first['ref']['id'])['body']
        self.assertEqual(old['persona_id'],'P02')
        self.assertEqual(old['agent'],'business-intent-coach')
        self.assertEqual(old['persona_specification']['id'],'P02')
        self.assertIn('does not select the strategy',old['persona_specification']['boundaries'].lower())
        self.assertEqual(old['persona_source']['document_id'],'a59add43-b208-4689-9452-9f88c25ff3f8')
        self.assertEqual(old['catalog_version'],'lucid-personas-v1')
        self.assertEqual(len(old['catalog_fingerprint']),64)
        self.assertEqual(old['descriptor'],'Priority advisor')
        self.assertEqual(old['descriptor_configuration']['revision'],1)
        self.descriptor(value='Business intent partner')
        second=self.coach();new=self.ws.intake.latest(second['ref']['id'])['body']
        self.assertEqual(new['descriptor'],'Business intent partner')
        self.assertEqual(new['descriptor_configuration']['revision'],2)
        self.assertEqual(self.ws.intake.latest(first['ref']['id'])['body']['descriptor'],'Priority advisor')
        self.assertEqual(new['configuration_fingerprint'],old['configuration_fingerprint'])
        self.assertNotIn('descriptor',self.model.context)
    def connection(self, **extra):
        return self.ws.command('integration-settings-save',{'expected':self.ws.coaching.settings.connections()['ref'],
            'name':'Test requirements API','kind':'api','endpoint':'https://example.invalid/api','purpose':'Read approved requirements.','credential_ref':'REQUIREMENTS_API_TOKEN',**extra})
    def test_connections_are_versioned_definitions_and_never_enable_tools(self):
        self.connection();c=self.ws.coaching.settings.connections();item=c['items'][0]
        self.assertEqual(item['status'],'not-connected');self.assertEqual(self.model.calls,0)
        self.connection(id=item['id'],kind='mcp',endpoint='https://example.invalid/mcp')
        self.assertEqual(len(self.ws.coaching.settings.connections()['items']),1)
        self.assertEqual(self.ws.coaching.settings.connections()['ref']['revision'],2)
        self.coach()
        self.assertNotIn('integrations',self.model.context)
        self.assertIn('cannot approve, publish, change permissions or call external tools',self.model.instructions)
    def test_credentials_in_urls_and_token_values_are_rejected(self):
        for endpoint in ['https://user:password@example.invalid/','https://example.invalid/?token=secret','https://example.invalid/#secret','file:///tmp/socket','https://[bad','https://example.invalid:bad/']:
            with self.subTest(endpoint=endpoint),self.assertRaises(ValueError):self.connection(endpoint=endpoint)
        with self.assertRaises(ValueError):self.connection(credential_ref='sk-private-secret')
        self.assertEqual(self.ws.coaching.settings.connections()['items'],[])
    def test_configuration_is_project_local(self):
        self.save();self.connection();self.descriptor()
        other=Store(Path(self.tmp.name)/'other.sqlite3')
        try:
            ws=Workspace(other,'priya',self.model);ws.command('intake-start',{'title':'Other synthetic project'})
            self.assertIsNone(ws.coaching.settings.coaching()['ref'])
            self.assertEqual(ws.coaching.settings.coaching()['config']['questions']['why_now']['expert_role'],'Prioritization AI partner')
            self.assertEqual(ws.coaching.settings.connections()['items'],[])
            self.assertIsNone(ws.coaching.settings.agent_registry()['ref'])
            self.assertEqual(ws.coaching.settings.agent_registry()['history'],[])
        finally:other.close()

if __name__ == '__main__': unittest.main()

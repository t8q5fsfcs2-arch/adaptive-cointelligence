"""All local prototype profiles configure Settings without changing workflow roles."""
from contextlib import closing
from copy import deepcopy
from dataclasses import asdict
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest

from workbench.core import Store
from workbench.decisions import PERSONAS
from workbench.domain import EDITABLE
from workbench.intake import PRIVATE
from workbench.model_connection import ModelConnections
from workbench.web import BrowserServer
from workbench.workspace import Workspace

class DevelopmentSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'workbench.sqlite3'
        with closing(Store(self.path)) as store:
            Workspace(store,'priya').command('intake-start',{'title':'Fictional settings access'})
        self.server=BrowserServer(('127.0.0.1',0),self.path,development=True,
                                  model_connection=ModelConnections(Path(self.tmp.name)/'models.json'))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=20);self.cookie='';self.csrf='';self.get('/api/home')
    def tearDown(self):
        self.conn.close();self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,method,path,data=None):
        headers={'Cookie':self.cookie,'Content-Type':'application/json','X-CSRF-Token':self.csrf,
                 'X-Workbench-Project':'original','X-Workbench-Version':'1'}
        self.conn.request(method,path,json.dumps(data) if data is not None else None,headers)
        response=self.conn.getresponse();result=json.loads(response.read())
        if response.getheader('Set-Cookie'):self.cookie=response.getheader('Set-Cookie').split(';')[0]
        if result.get('csrf'):self.csrf=result['csrf']
        return response.status,result
    def get(self,path):return self.request('GET',path)
    def post(self,action,data):return self.request('POST','/api/'+action,data)
    def test_all_profiles_can_read_and_save_settings_with_their_own_attribution(self):
        for actor in PERSONAS:
            with self.subTest(actor=actor):
                self.assertEqual(self.post('profile',{'actor':actor})[0],200)
                home=self.get('/api/home')[1];self.assertTrue(home['auth']['settings_access'])
                self.assertEqual(home['auth']['administrator'],actor=='administrator')
                for path in ('/api/admin-announcements','/api/model-connections','/api/admin-integrations','/api/portfolio-access'):
                    status,result=self.get(path);self.assertEqual(status,200,(path,result))
                self.assertTrue(self.get('/api/model-connections')[1]['can_manage'])
                status,state=self.get('/api/state?project=original');self.assertEqual(status,200,state)
                self.assertTrue(state['domain_knowledge']['can_add'])
                self.assertEqual(set(state['domains']['can_configure']),{'research','design'})
                settings=state['coaching']['settings'];self.assertIsNotNone(settings)
                config=deepcopy(settings['config']['persona']);config['name']='Fictional coach '+actor
                status,result=self.post('coach-settings-save',dict(expected=settings['ref'],area='persona',key='',config=config))
                self.assertEqual(status,200,result)
                status,result=self.post('agent-descriptor-save',dict(expected=settings['agent_registry']['ref'],persona_id='P02',descriptor='Configured by '+actor))
                self.assertEqual(status,200,result)
                profile=state['domains']['profiles'][0];config={k:deepcopy(profile['config'][k]) for k in EDITABLE};config['descriptor']='Domain coach configured by '+actor
                status,result=self.post('domain-configure',dict(domain=profile['key'],expected=profile['ref'],config=config,reason='Fictional settings check'))
                self.assertEqual(status,200,result)
                status,result=self.post('intake-configure',dict(expected=state['intake']['profile']['ref'],name='Fictional profile '+actor,drawers=state['intake']['profile']['body']['drawers']))
                self.assertEqual(status,200,result)
                instructions=state['requirement_agent']['settings']
                status,result=self.post('requirement-agent-settings',dict(expected=instructions['ref'],**instructions['config']))
                self.assertEqual(status,200,result)
                method=state['agent_methods']['P02'];key=next(iter(method['methods']))
                status,result=self.post('agent-method-save',dict(expected=method['ref'],persona_id='P02',method_id=key,guidance='Keep evidence and assumptions separate.',example='Fictional example.'))
                self.assertEqual(status,200,result)
                knowledge=next(d for d in state['domain_knowledge']['domains'] if d['key']=='research')
                status,result=self.post('domain-knowledge-save',dict(domain='research',expected=knowledge['ref'],entries=knowledge['entries'],reason='Fictional settings check',confirm_active=True))
                # D005: team knowledge is edited only by the team's lead, even with development settings access.
                if actor=='sam':self.assertEqual(status,200,result)
                else:self.assertNotEqual(status,200,result);self.assertFalse(knowledge['can_edit'])
                model=self.get('/api/model-connections')[1]
                status,result=self.post('model-connection-save',dict(expected=model['revision'],name='Fictional model '+actor,provider='openai',model='test-only-model',api_key='synthetic-test-only-key'))
                self.assertEqual(status,200,result)
                self.assertNotIn('synthetic-test-only-key',json.dumps(self.get('/api/model-connections')[1]))
                rights=self.get('/api/decision-rights?project=original')[1];self.assertTrue(rights['can_edit'])
                status,result=self.post('decision-rights-save',dict(expected=rights['ref'],rules=rights['rules'],reason='Retain configured workflow rights'))
                self.assertEqual(status,200,result)
                announcement=self.get('/api/admin-announcements')[1]
                status,result=self.post('announcements-save',dict(expected=announcement['revision'],items=[{'title':'Draft by '+actor,'body':'Local settings test'}]))
                self.assertEqual(status,200,result)
                self.assertEqual(self.get('/api/admin-announcements')[1]['draft']['author']['name'],PERSONAS[actor]['name'])
                self.assertTrue(self.get('/api/home')[1]['announcements']['sample'])
                with closing(Store(self.path)) as store:
                    self.assertEqual(store.latest('SETTINGS-COACH',{PRIVATE})['body']['author'],actor)
                    workspace=Workspace(store,actor,admin=actor=='administrator',settings_access=True)
                    self.assertEqual(workspace.is_admin,actor=='administrator')
                    if actor!='priya':
                        self.assertIsNone(workspace.intake.state()['draft'])
                        with self.assertRaises(PermissionError):workspace.command('intake-save',{'expected':asdict(workspace.intake.draft()['ref'])})
                        with self.assertRaises(PermissionError):workspace.coaching.run({})
    def test_full_access_is_explicit_and_does_not_change_default_configuration_rights(self):
        with closing(Store(self.path)) as store:
            research=Workspace(store,'sam');self.assertFalse(research.settings_admin)
            self.assertIsNone(research.coaching.settings.state())
            with self.assertRaises(PermissionError):research.command('agent-descriptor-save',dict(expected=None,persona_id='P02',descriptor='No authority'))
            with self.assertRaises(PermissionError):research.command('decision-rights-save',{})
            with self.assertRaises(PermissionError):research.command('domain-add',{})
            prototype=Workspace(store,'sam',settings_access=True)
            self.assertTrue(prototype.settings_admin);self.assertFalse(prototype.is_admin)
            self.assertFalse(prototype.rights.state()['can_prepare_requirement'])

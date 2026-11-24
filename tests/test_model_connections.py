"""Model setup and routing use explicit project assignments; fixtures make no vendor calls."""
import base64
from contextlib import closing
from copy import deepcopy
from dataclasses import asdict
import http.client
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch
import zipfile

from workbench.core import Store, StaleBasis
from workbench.demo_package import initialize
from workbench.model_connection import ModelConnections, GENERAL
from workbench.model_provider import OpenAIModel, AnthropicModel, ModelUnavailable
from workbench.web import BrowserServer
from workbench.decisions import SCOPE

KEY = 'test-only-never-a-real-key'


class ModelConnectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'managed'/'model-connections.json';self.runtime=ModelConnections(self.path)
    def tearDown(self):self.tmp.cleanup()
    def save(self,name='Pilot connection',model='synthetic-model',provider='openai',key=KEY,**extra):
        result=self.runtime.save(dict(expected=self.runtime.config['revision'],name=name,provider=provider,model=model,api_key=key,**extra),'admin')
        return result['modelConnectionProfile']
    def assign(self,key,projects):
        return self.runtime.assign(dict(expected=self.runtime.config['revision'],id=key,projects=projects),'admin',{'a','b'})
    def test_explicit_existing_connection_import_preserves_scope_and_never_overwrites_settings(self):
        with patch('workbench.model_provider.urlopen',side_effect=AssertionError('Import must not call a provider')):
            self.assertTrue(self.runtime.import_existing(OpenAIModel(KEY,'existing-model'),{'a','b'}))
            self.assertEqual(self.runtime.select(['a']).model,'existing-model')
            self.assertEqual(self.runtime.select(['b']).api_key,KEY)
            self.assertEqual(self.runtime.select().model,'existing-model')
            self.assertFalse(self.runtime.select(['new-project']).status()['configured'])
            before=self.path.read_bytes()
            self.assertFalse(self.runtime.import_existing(AnthropicModel('other-key','other-model'),{'new-project'}))
            self.assertEqual(self.path.read_bytes(),before)
            self.assertNotIn(KEY,json.dumps(self.runtime.state([],admin=True)))

    def test_credentials_are_local_private_and_never_returned_or_written_into_audit(self):
        with patch('workbench.model_provider.urlopen',side_effect=AssertionError('Saving must not call a model')):
            key=self.save();self.assign(key,['a',GENERAL])
        state=self.runtime.state([dict(id='a',title='A'),dict(id='b',title='B')],admin=True)
        self.assertNotIn(KEY,json.dumps(state));self.assertNotIn('api_key',json.dumps(state))
        self.assertNotIn(KEY,json.dumps(self.runtime.config['history']))
        if os.name!='nt':self.assertEqual(self.path.stat().st_mode&0o777,0o600)
        reopened=ModelConnections(self.path);self.assertEqual(reopened.select(['a']).api_key,KEY)
        self.assertFalse(reopened.select(['b']).status()['configured'])
        self.assertEqual(reopened.effective('a')['profile']['id'],key)
    def test_updates_are_selective_snapshots_are_immutable_and_nonadmins_do_not_see_library(self):
        a=self.save();b=self.save(name='Other',model='other-model');self.assign(a,['a']);self.assign(b,['b'])
        pinned=self.runtime.select(['a']);self.save(id=a,key='',model='revised-model')
        self.assertEqual(pinned.model,'synthetic-model');self.assertEqual(self.runtime.select(['a']).model,'revised-model')
        self.assertEqual(self.runtime.select(['b']).model,'other-model')
        visible=self.runtime.state([],project='a');self.assertNotIn('profiles',visible);self.assertNotIn('projects',visible)
        self.assertEqual(visible['profile']['id'],a)
        self.assertEqual(pinned.status()['connection']['revision'],1)
        with self.assertRaisesRegex(ValueError,'different model connections'):self.runtime.select(['a','b'])
    def test_validation_staleness_and_failed_test_cannot_destroy_saved_settings(self):
        key=self.save();before=self.path.read_bytes()
        with self.assertRaises(StaleBasis):self.runtime.save(dict(expected=0,name='Wrong'), 'admin')
        with self.assertRaises(ValueError):self.save(id=key,provider='anthropic',key='')
        with self.assertRaises(ValueError):self.runtime.assign(dict(expected=self.runtime.config['revision'],id=key,projects=['unknown']),'admin',{'a'})
        self.assertEqual(self.path.read_bytes(),before)
        with patch.object(OpenAIModel,'generate',side_effect=ModelUnavailable('Bad credential '+KEY)):
            self.runtime.test(dict(expected=self.runtime.config['revision'],id=key),'admin')
        state=self.runtime.state([],admin=True);self.assertNotIn(KEY,json.dumps(state));self.assertEqual(state['profiles'][0]['test']['status'],'failed')
        self.assertEqual(self.runtime.select().status()['configured'],False)
    def test_connection_test_contains_no_project_context_and_cannot_validate_a_changed_profile(self):
        key=self.save();calls=[]
        def generate(model,**values):calls.append(values);return {'output':{'ready':True}}
        with patch.object(OpenAIModel,'generate',generate):self.runtime.test(dict(expected=self.runtime.config['revision'],id=key),'admin')
        self.assertEqual(calls[0]['context'],{'purpose':'local-connection-test'})
        self.assertEqual(self.runtime.config['profiles'][key]['test']['status'],'passed')
        def changed(model,**values):self.save(id=key,key='',model='changed-model');return {'output':{'ready':True}}
        with patch.object(OpenAIModel,'generate',changed):
            with self.assertRaises(StaleBasis):self.runtime.test(dict(expected=self.runtime.config['revision'],id=key),'admin')
        self.assertNotIn('test',self.runtime.config['profiles'][key])
    def test_removal_clears_key_and_assignments_but_retains_other_connections(self):
        a=self.save();b=self.save(name='Other',provider='anthropic',key='other-test-key');self.assign(a,['a',GENERAL]);self.assign(b,['b'])
        with self.assertRaises(ValueError):self.runtime.remove(dict(expected=self.runtime.config['revision'],id=a),'admin')
        self.runtime.remove(dict(expected=self.runtime.config['revision'],id=a,confirm_remove=True),'admin')
        self.assertNotIn(KEY,self.path.read_text());self.assertFalse(self.runtime.select(['a']).status()['configured'])
        self.assertIsInstance(self.runtime.select(['b']),AnthropicModel)


class ModelConnectionHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'data'/'workbench.sqlite3';self.report=initialize(self.path)
        self.runtime=ModelConnections(Path(self.tmp.name)/'model-connections.json')
        self.server=BrowserServer(('127.0.0.1',0),self.path,development=True,model_connection=self.runtime)
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True);self.worker.start()
        self.conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=30);self.cookie='';self.state={}
        self.request('GET','/api/state')
    def tearDown(self):self.conn.close();self.server.shutdown();self.server.server_close();self.worker.join();self.tmp.cleanup()
    def request(self,method,path,data=None,headers=None):
        sent={'Cookie':self.cookie,'X-CSRF-Token':self.state.get('csrf',''),'X-Workbench-Project':'original','X-Workbench-Version':'1'}
        if data is not None:sent['Content-Type']='application/json'
        sent.update(headers or {})
        self.conn.request(method,path,body=json.dumps(data) if data is not None else None,headers=sent)
        response=self.conn.getresponse();raw=response.read();status=response.status
        if response.getheader('Set-Cookie'):self.cookie=response.getheader('Set-Cookie').split(';')[0]
        result=json.loads(raw)
        if path in ('/api/state','/api/home') and status==200:self.state=result
        return status,result
    def post(self,action,**data):return self.request('POST','/api/'+action,data)
    def role(self,actor):self.assertEqual(self.post('profile',actor=actor)[0],200);self.request('GET','/api/state')
    def library(self):return self.request('GET','/api/model-connections')[1]
    def connect(self):
        self.role('administrator');state=self.library()
        status,out=self.post('model-connection-save',expected=state['revision'],name='Clinic test connection',provider='openai',model='synthetic-model',api_key=KEY)
        self.assertEqual(status,200,out);key=out['modelConnectionProfile']
        status,out=self.post('model-connection-assign',expected=self.library()['revision'],id=key,projects=['original',GENERAL]);self.assertEqual(status,200,out)
        return key
    def docx(self):
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="urn:w"><w:p><w:r><w:t>Fictional interview: receptionists lose draft feedback after an interruption.</w:t></w:r></w:p></w:document>')
        return base64.b64encode(out.getvalue()).decode()
    def transport(self,requests):
        def call(request,timeout):
            payload=json.loads(request.data);requests.append(payload);context=json.loads(payload['input'])
            if context.get('purpose')=='local-connection-test':output={'ready':True}
            elif context.get('skill')=='personal-conversation':output={'reply':'The document describes interrupted draft feedback; investigate recovery.','citations':['D1:P1'] if context['sources'] and context['sources'][0]['id']=='D1:P1' else []}
            else:output={'summary':'Investigate recoverability and distinguish the observation from a requirement decision.','strengths':[],'suggestions':[]}
            response=io.BytesIO(json.dumps({'status':'completed','model':'synthetic-model','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(output)}]}],'usage':{'input_tokens':10,'output_tokens':20}}).encode())
            return response
        return call
    def test_development_roles_share_settings_but_csrf_and_cross_origin_remain_enforced(self):
        before=self.runtime.config['revision']
        for actor in ('priya','sam','lee','maya','alex','administrator'):
            self.role(actor)
            self.assertEqual(self.request('GET','/api/model-connections')[0],200)
            self.assertTrue(self.library()['can_manage'])
            self.assertEqual(self.request('POST','/api/model-connection-save',{},headers={'X-CSRF-Token':'wrong'})[0],403)
            self.assertEqual(self.request('POST','/api/model-connection-save',{},headers={'Origin':'https://untrusted.example'})[0],403)
        self.assertEqual(self.runtime.config['revision'],before)
    def test_real_adapters_are_wired_to_uploaded_word_and_domain_workflow_without_scripted_fallback(self):
        requests=[]
        with patch('workbench.model_provider.urlopen',self.transport(requests)):
            key=self.connect();self.assertEqual(requests,[])
            state=self.library();status,out=self.post('model-connection-test',expected=state['revision'],id=key);self.assertEqual(status,200,out)
            self.assertEqual(requests[0]['input'],json.dumps({'purpose':'local-connection-test'}))
            self.role('sam');status,state=self.request('GET','/api/state');self.assertTrue(state['domains']['model']['configured'])
            self.assertNotIn(KEY,json.dumps(state));self.assertTrue(state['model_connection']['can_manage'])
            status,thread=self.post('thought-chat-create',title='Real upload workflow test');self.assertEqual(status,200)
            status,doc=self.post('thought-chat-attach',thread=thread['id'],filename='interview.docx',content=self.docx());self.assertEqual(status,200,doc)
            self.assertEqual(len(requests),1)
            status,sent=self.post('thought-chat-send',thread=thread['id'],request_id='real-wiring-001',expected_count=0,projects=[{'id':'original','version':1}],message='What does this interview say about draft feedback?',consent=True)
            self.assertEqual(status,200,sent);self.assertEqual(sent['status'],'complete')
            status,personal=self.request('GET','/api/thought-chat?thread='+thread['id']);self.assertEqual(status,200)
            assistant=personal['thread']['messages'][-1];self.assertEqual(assistant['mode'],'live');self.assertEqual(assistant['context']['model_connection']['id'],key)
            self.assertIn('receptionists lose draft feedback',requests[-1]['input'])
            status,chat=self.post('domain-chat-start',title='New domain upload');self.assertEqual(status,200,chat)
            with closing(Store(self.path)) as store:draft=store.latest(chat['id'],{'domain:research'})
            status,attached=self.post('domain-chat-attach',conversation=chat['conversation'],expected=asdict(draft['ref']),filename='interview.docx',content=self.docx());self.assertEqual(status,200,attached)
            self.request('GET','/api/state')
            current=next(t for t in self.state['domain_chat']['threads'] if t['ref']['id']==chat['conversation']['id'])
            draft=next(r for r in self.state['records'] if r['ref']['id']==chat['id'])
            status,out=self.post('domain-chat-send',conversation=current['ref'],expected=draft['ref'],message='Review the interview against the project requirements.',consent=True,request_id='real-domain-001',purpose='review',batch=0)
            self.assertEqual(status,200,out);self.assertIn('chatReport',out)
            self.request('GET','/api/state');review=next(r for r in self.state['domain_chat']['reports'] if r['ref']['id']==out['chatReport'])
            self.assertEqual(review['body']['mode'],'live');self.assertIn('receptionists lose draft feedback',requests[-1]['input'])
            self.assertTrue(any(r['body'].get('model_connection',{}).get('id')==key for r in self.state['records'] if r['kind']=='agent-execution'))
            self.assertNotIn(KEY,json.dumps(personal));self.assertNotIn(KEY,json.dumps(self.state))
            # Provider failure is retained as a real error, never replaced by a fixture.
            from urllib.error import HTTPError
            with patch('workbench.model_provider.urlopen',side_effect=HTTPError('https://api.openai.com/v1/responses',401,'Unauthorized',{},io.BytesIO(b'{}'))):
                status,failed=self.post('thought-chat-send',thread=thread['id'],request_id='real-failure-002',expected_count=2,projects=[{'id':'original','version':1}],message='Continue.',consent=True)
            self.assertEqual(status,200);self.assertEqual(failed['status'],'failed')
            self.assertEqual(self.request('GET','/api/thought-chat?thread='+thread['id'])[1]['thread']['documents'][0]['id'],doc['id'])
        with closing(Store(self.path)) as store:
            self.assertEqual(store.latest(self.report['manifest']['requirement_after']['id'],{SCOPE})['ref'].revision,self.report['manifest']['requirement_after']['revision'])

    def test_cross_project_chat_respects_assignments_including_prior_history(self):
        first=self.connect()
        other=self.server.projects.create({'title':'Second synthetic project'},'priya')['project_id']
        status,out=self.post('model-connection-save',expected=self.library()['revision'],name='Second connection',provider='openai',model='other-model',api_key='second-test-key')
        self.assertEqual(status,200,out);second=out['modelConnectionProfile']
        status,out=self.post('model-connection-assign',expected=self.library()['revision'],id=second,projects=[other]);self.assertEqual(status,200,out)
        self.role('sam');calls=[]
        with patch('workbench.model_provider.urlopen',self.transport(calls)):
            thread=self.post('thought-chat-create',title='Project isolation')[1]['id']
            mixed=[{'id':'original','version':1},{'id':other,'version':1}]
            status,out=self.post('thought-chat-send',thread=thread,request_id='cross-project-001',expected_count=0,projects=mixed,message='Compare these projects.',consent=True)
            self.assertEqual(status,400,out);self.assertIn('different model connections',out['error']);self.assertEqual(calls,[])
            status,out=self.post('thought-chat-send',thread=thread,request_id='cross-project-002',expected_count=0,projects=[{'id':'original','version':1}],message='What is the project requirement?',consent=True)
            self.assertEqual(status,200,out);self.assertEqual(out['status'],'complete');self.assertEqual(len(calls),1)
            status,out=self.post('thought-chat-send',thread=thread,request_id='cross-project-003',expected_count=2,projects=[{'id':other,'version':1}],message='Now discuss the other project.',consent=True)
            self.assertEqual(status,400,out);self.assertEqual(len(calls),1)
            self.role('administrator')
            status,other_state=self.request('GET','/api/state?project='+other);self.assertEqual(status,200)
            self.assertEqual(other_state['model_connection']['profile']['id'],second)
            self.assertEqual(self.runtime.effective('original')['profile']['id'],first)

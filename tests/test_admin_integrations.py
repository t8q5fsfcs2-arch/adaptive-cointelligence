"""Admin navigation reaches the existing project configuration without private work."""
from contextlib import closing
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from workbench.core import Store
from workbench.demo_package import initialize
from workbench.intake import PRIVATE
from workbench.web import BrowserServer
from workbench.model_provider import UnconfiguredModel


class AdminIntegrationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'workbench.sqlite3';initialize(self.path)
        self.server=BrowserServer(('127.0.0.1',0),self.path,development=True,model=UnconfiguredModel())
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True);self.worker.start()
        self.conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=30);self.cookie='';self.csrf=''
        self.get('/api/home')
    def tearDown(self):
        self.conn.close();self.server.shutdown();self.server.server_close();self.worker.join();self.tmp.cleanup()
    def request(self,method,path,data=None,headers=None):
        sent={'Cookie':self.cookie,'X-CSRF-Token':self.csrf}
        if data is not None:sent['Content-Type']='application/json'
        sent.update(headers or {})
        self.conn.request(method,path,json.dumps(data) if data is not None else None,sent)
        response=self.conn.getresponse();status=response.status;result=json.loads(response.read())
        if response.getheader('Set-Cookie'):self.cookie=response.getheader('Set-Cookie').split(';')[0]
        if result.get('csrf'):self.csrf=result['csrf']
        return status,result
    def get(self,path):return self.request('GET',path)
    def post(self,action,data=None,**headers):return self.request('POST','/api/'+action,data or {},headers)
    def role(self,actor):self.assertEqual(self.post('profile',{'actor':actor})[0],200)
    def config(self,project='original'):
        status,data=self.get('/api/admin-integrations?project='+project);self.assertEqual(status,200,data);return data
    def save(self,data,action='admin-integration-save',project='original',version='1',**headers):
        return self.post(action,data,**{'X-Workbench-Project':project,'X-Workbench-Version':version,**headers})
    def definition(self,**extra):
        return {'id':None,'expected':None,'name':'Fictional context API','kind':'api','endpoint':'https://example.test/context','purpose':'Read approved context.','credential_ref':'WB_CONTEXT_TOKEN',**extra}
    def test_all_development_profiles_can_configure_with_project_and_request_guards(self):
        for actor in ('priya','sam','lee','maya','alex','administrator'):
            self.role(actor)
            self.assertEqual(self.get('/api/admin-integrations')[0],200)
            self.assertEqual(self.post('admin-integration-save',self.definition())[0],409)
            self.assertEqual(self.save(self.definition(),**{'X-CSRF-Token':'invalid'})[0],403)
            self.assertEqual(self.save(self.definition(),Origin='https://untrusted.example')[0],403)
            self.assertEqual(self.save(self.definition(),version='999')[0],409)
        self.assertEqual(self.config()['connections']['items'],[])
    def test_projection_excludes_private_intake_domain_work_and_credentials_and_reads_make_no_records(self):
        with closing(Store(self.path)) as store:
            store.put('TEST-PRIVATE','source',PRIVATE,{'text':'private sponsor document sentinel'},0)
            store.put('TEST-DOMAIN-SECRET','source','domain:research',{'text':'private research sentinel','token':'never-return-this'},0)
            before=store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        self.role('administrator')
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Settings must not call a tool')):
            data=self.config()
        self.assertEqual(set(data),{'project','projects','tools','connections'})
        raw=json.dumps(data)
        for text in ('private sponsor document sentinel','private research sentinel','never-return-this','credential_available'):
            self.assertNotIn(text,raw)
        with closing(Store(self.path)) as store:self.assertEqual(store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0],before)
    def test_admin_updates_existing_records_with_attribution_staleness_and_project_isolation(self):
        status,new=self.post('project-create',{'title':'Other fictional project'});self.assertEqual(status,200,new)
        self.role('administrator');other=self.config(new['project_id'])
        before=self.config()
        with closing(Store(self.path)) as store:before_rows=store.db.execute('SELECT id,revision FROM records ORDER BY id,revision').fetchall()
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Save must not connect')):
            status,result=self.save(self.definition());self.assertEqual(status,200,result)
        saved=self.config()['connections'];self.assertEqual(saved['items'][0]['name'],'Fictional context API')
        self.assertEqual(saved['items'][0]['status'],'not-connected')
        self.assertEqual(self.save(self.definition())[0],409)
        item=saved['items'][0]
        status,result=self.save(self.definition(id=item['id'],expected=saved['ref'],name='Updated fictional API'));self.assertEqual(status,200,result)
        self.assertEqual(self.config(new['project_id']),other)
        with closing(Store(self.path)) as store:
            row=store.latest('SETTINGS-INTEGRATIONS',{PRIVATE});self.assertEqual(row['body']['author'],'administrator')
            for id,revision in before_rows:self.assertIsNotNone(store.db.execute('SELECT 1 FROM records WHERE id=? AND revision=?',(id,revision)).fetchone())
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM records WHERE id!='SETTINGS-INTEGRATIONS'").fetchone()[0],len(before_rows))
        self.assertEqual(self.save(self.definition(expected=result['ref'],endpoint='https://secret@example.test/api'))[0],400)
    def test_file_link_editor_keeps_domain_fields_and_refuses_unapproved_destinations(self):
        self.role('administrator');before=self.config()
        links={'research_figjam':'https://www.figma.com/board/FictionalResearch','design_figma':'https://www.figma.com/design/FictionalDesign','design_figjam':''}
        status,result=self.save({'expected':before['tools']['ref'],'links':links},'admin-work-tools-save');self.assertEqual(status,200,result)
        current=self.config();self.assertEqual(current['tools']['links'],links)
        self.assertEqual(current['connections'],before['connections'])
        status,result=self.save({'expected':current['tools']['ref'],'links':{'design_figma':'https://evil.example/design/File'}},'admin-work-tools-save');self.assertEqual(status,400,result)
        self.assertEqual(self.config(),current)
        # The admin settings operation does not confer sponsor workflow authority.
        status,result=self.save({'title':'Unapproved intake'},'intake-start');self.assertEqual(status,403,result)

if __name__=='__main__':unittest.main()

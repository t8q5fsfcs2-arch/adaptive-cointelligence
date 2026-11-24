"""Home publication, privacy, stale edits and durable history without model calls."""
from contextlib import closing
from copy import deepcopy
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch

from workbench.announcements import Announcements, SAMPLE_ITEMS
from workbench.core import Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.projects import Projects
from workbench.web import BrowserServer
from workbench.model_provider import UnconfiguredModel

ADMIN={'id':'account:test-admin','name':'Fictional administrator'}
ITEMS=[{'title':'Pilot update','body':'A fictional release is ready for review.'}]


class AnnouncementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'workbench.sqlite3'
        with closing(Store(self.path)) as store:store.put('PROJECT-001','project',SCOPE,{'title':'Fictional project'},0)
        self.projects=Projects(self.path);self.a=Announcements(self.projects)
    def tearDown(self):self.tmp.cleanup()
    def test_samples_are_a_labelled_fallback_and_saving_never_publishes(self):
        with self.projects.db() as db:before=db.execute('SELECT COUNT(*) FROM home_announcement_versions').fetchone()[0]
        for _ in range(3):self.assertEqual(self.a.public(),dict(items=SAMPLE_ITEMS,sample=True,published_at=None))
        with self.projects.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM home_announcement_versions').fetchone()[0],before)
        self.a.save({'expected':0,'items':ITEMS},ADMIN)
        self.assertEqual(self.a.state()['items'],ITEMS);self.assertEqual(self.a.public()['items'],SAMPLE_ITEMS)
        reopened=Announcements(Projects(self.path));self.assertEqual(reopened.state()['revision'],1)
        self.assertNotIn('Pilot update',json.dumps(reopened.public()))
    def test_exact_publication_retains_prior_content_and_drafts_are_private(self):
        self.a.save({'expected':0,'items':ITEMS},ADMIN)
        with self.assertRaises(ValueError):self.a.publish({'expected':1},ADMIN)
        self.a.publish({'expected':1,'confirm':True},ADMIN)
        self.assertEqual(self.a.public()['items'],ITEMS);self.assertFalse(self.a.public()['sample'])
        second=[{'title':'New draft only','body':'Keep this private until publication.'}]
        self.a.save({'expected':2,'items':second},ADMIN)
        self.assertEqual(self.a.public()['items'],ITEMS)
        with self.assertRaises(StaleBasis):self.a.publish({'expected':1,'confirm':True},ADMIN)
        self.a.publish({'expected':3,'confirm':True},ADMIN)
        state=self.a.state();self.assertEqual([r['items'] for r in state['history']],[second,ITEMS])
        self.assertEqual(state['published']['author'],ADMIN);self.assertEqual(state['published']['basis'],3)
        # Retrying the exact publish does not add a second event.
        self.a.publish({'expected':3,'confirm':True},ADMIN);self.assertEqual(self.a.state()['revision'],4)
        self.a.save({'expected':4,'items':[]},ADMIN);self.assertEqual(self.a.public()['items'],second)
        self.a.publish({'expected':5,'confirm':True},ADMIN);self.assertEqual(self.a.public()['items'],[])
        self.assertFalse(self.a.public()['sample']);self.assertEqual(len(self.a.state()['history']),3)
    def test_validation_and_concurrent_writers_preserve_existing_data(self):
        self.a.save({'expected':0,'items':ITEMS},ADMIN);before=self.a.state()
        for invalid in (None,{},[{}],ITEMS*4,[{'title':'','body':'x'}],[{'title':'A'*101,'body':'x'}],[{'title':'One','body':'x'*501}],[{'title':'New\nline','body':'x'}],[{'title':'One','body':'\x00secret'}]):
            with self.assertRaises(ValueError):self.a.save({'expected':1,'items':invalid},ADMIN)
        with self.assertRaises(StaleBasis):self.a.save({'expected':True,'items':ITEMS},ADMIN)
        self.assertEqual(self.a.state(),before)
        outcomes=[];barrier=threading.Barrier(2)
        def writer(title):
            barrier.wait()
            try:self.a.save({'expected':1,'items':[{'title':title,'body':'Concurrent update.'}]},ADMIN);outcomes.append('saved')
            except StaleBasis:outcomes.append('stale')
        threads=[threading.Thread(target=writer,args=(title,)) for title in ('A','B')]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertCountEqual(outcomes,['saved','stale']);self.assertEqual(self.a.state()['revision'],2)
        with closing(Store(self.path)) as store:self.assertEqual(store.latest('PROJECT-001',{SCOPE})['body']['title'],'Fictional project')


class AnnouncementHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'workbench.sqlite3'
        with closing(Store(self.path)) as store:store.put('PROJECT-001','project',SCOPE,{'title':'Fictional project'},0)
        self.server=BrowserServer(('127.0.0.1',0),self.path,development=True,model=UnconfiguredModel())
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True);self.worker.start()
        self.conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=20);self.cookie='';self.csrf='';self.get('/api/home')
    def tearDown(self):self.conn.close();self.server.shutdown();self.server.server_close();self.worker.join();self.tmp.cleanup()
    def request(self,method,path,data=None,headers=None):
        sent={'Cookie':self.cookie,'Content-Type':'application/json','X-CSRF-Token':self.csrf,**(headers or {})}
        self.conn.request(method,path,json.dumps(data) if data is not None else None,sent);r=self.conn.getresponse();body=json.loads(r.read())
        if r.getheader('Set-Cookie'):self.cookie=r.getheader('Set-Cookie').split(';')[0]
        if body.get('csrf'):self.csrf=body['csrf']
        return r.status,body
    def get(self,path):return self.request('GET',path)
    def post(self,action,data):return self.request('POST','/api/'+action,data)
    def role(self,actor):self.assertEqual(self.post('profile',{'actor':actor})[0],200)
    def test_all_development_roles_can_configure_but_csrf_and_origin_still_apply(self):
        for actor in ('priya','sam','lee','maya','alex','administrator'):
            self.role(actor);self.assertEqual(self.get('/api/admin-announcements')[0],200)
            for extra in ({'X-CSRF-Token':'wrong'},{'Origin':'https://untrusted.example'}):
                self.assertEqual(self.request('POST','/api/announcements-save',{'expected':0,'items':ITEMS},extra)[0],403)
        self.assertEqual(self.get('/api/admin-announcements')[1]['revision'],0)
    def test_sitewide_publish_changes_home_for_all_roles_and_preserves_project_records(self):
        with closing(Store(self.path)) as store:before=list(store.db.iterdump())
        self.role('administrator')
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Announcements never call a model or connector')):
            self.assertEqual(self.post('announcements-save',{'expected':0,'items':ITEMS})[0],200)
            self.assertEqual(self.get('/api/home')[1]['announcements']['items'],SAMPLE_ITEMS)
            self.assertEqual(self.post('announcements-publish',{'expected':1,'confirm':True})[0],200)
        self.post('announcements-save',{'expected':2,'items':[{'title':'Private draft sentinel','body':'Not released'}]})
        for actor in ('priya','sam','lee','administrator'):
            self.role(actor);home=self.get('/api/home')[1]
            self.assertEqual(home['announcements']['items'],ITEMS);self.assertNotIn('Private draft sentinel',json.dumps(home))
        with closing(Store(self.path)) as store:self.assertEqual(list(store.db.iterdump()),before)
        self.assertEqual(self.server.announcements.state()['published']['author']['name'],'Administrator')

if __name__=='__main__':unittest.main()

"""Destination authority, atomic private saves and safe retry receipts."""
import base64
import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from workbench.core import Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.file_uploads import FileUploads
from workbench.model_provider import UnconfiguredModel
from workbench.workspace import Workspace
from workbench.web import BrowserServer
import test_my_files as fixtures
upload,core_rows=fixtures.upload,fixtures.core_rows
from test_access import Client,PASSWORD


class NoCalls(UnconfiguredModel):
    def generate(self,**kwargs):raise AssertionError('Upload must not call a model.')


class UploadRoutingTests(unittest.TestCase):
    def setUp(self):
        fixtures.FileLibraryTests.setUp(self)
        self.model=NoCalls();self.router=FileUploads(self.projects,self.chat,self.library,self.model)
    def tearDown(self):fixtures.FileLibraryTests.tearDown(self)
    def save(self,destination,actor='priya',request='upload-attempt-001',**data):
        return self.router.upload('profile:'+actor,actor,None,{'original'},dict(expected_owner='profile:'+actor,request_id=request,destination=destination,**(data or upload())))
    def business(self):return self.router.destinations('profile:priya','priya',{'original'})['projects'][0]['destination']
    def test_explicit_project_destination_keeps_other_projects_and_governing_work_unchanged(self):
        other=self.projects.create(dict(title='Second synthetic project'),'priya')['project_id']
        destination=next(p['destination'] for p in self.router.destinations('profile:priya','priya',{'original',other})['projects'] if p['destination']['project']==other)
        before=core_rows(self.path)
        result=self.router.upload('profile:priya','priya',None,{'original',other},dict(expected_owner='profile:priya',request_id='different-project-001',destination=destination,**upload('New private evidence.')))
        self.assertEqual(core_rows(self.path),before)
        file=self.library.detail('profile:priya','priya',{'original',other},result['id'])
        self.assertEqual(file['project'],other);self.assertEqual(file['text'],'New private evidence.')
        self.assertEqual(self.library.download('profile:priya','priya',{'original',other},result['id'],'original')[0],b'New private evidence.')
    def test_retry_is_idempotent_and_cannot_silently_change_file_or_destination(self):
        destination=self.business();first=self.save(destination);after=core_rows(self.path)
        self.assertEqual(self.save(destination),first);self.assertEqual(core_rows(self.path),after)
        with self.assertRaises(StaleBasis):self.save(destination,**upload('Different bytes.'))
        with self.assertRaises(StaleBasis):self.save(dict(kind='new-conversation'))
        self.assertEqual(core_rows(self.path),after)
    def test_new_conversation_and_file_commit_together_without_a_model_call(self):
        with self.assertRaises(ValueError):self.save(dict(kind='new-conversation'),**upload('Not a supported file.','bad.exe'))
        with self.chat.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM threads').fetchone()[0],0)
        destination=dict(kind='new-conversation');first=self.save(destination,request='new-chat-file-001')
        self.assertEqual(first,self.save(destination,request='new-chat-file-001'))
        with self.chat.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM threads').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM documents').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM messages').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT projects FROM threads').fetchone()[0],'[]')
        self.library.update('profile:priya','priya',{'original'},dict(id=first['id'],action='archive',expected_revision=0))
        self.save(destination,request='new-chat-file-001')
        self.assertFalse(self.library.resolve('profile:priya','priya',{'original'},first['id'])['archived'])
    def test_existing_conversation_requires_owner_and_keeps_pending_threads_closed(self):
        tid=self.chat.create('profile:priya',dict(title='Existing private conversation'))['id']
        destination=dict(kind='conversation',thread=tid);self.save(destination)
        with self.assertRaises(PermissionError):self.save(destination,actor='sam',request='other-owner-attempt')
        with self.chat.db() as db:
            db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',('M',tid,1,'user','Question','pending','request','{}','[]','2026-11-11',None,'not-connected'))
        choice=next(c for c in self.router.destinations('profile:priya','priya',{'original'})['conversations'] if c['destination']==destination)
        self.assertTrue(choice['disabled'])
        with self.assertRaisesRegex(ValueError,'current response'):self.save(destination,request='pending-chat-attempt',**upload('Another private document.'))
        with self.chat.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM documents').fetchone()[0],1)
    def test_domain_conversation_attaches_in_place_without_approving_or_reviewing(self):
        sam=Workspace(self.store,'sam',self.model);sam.command('domain-chat-start',dict(title='Research conversation'))
        destination=next(c['destination'] for c in self.router.destinations('profile:sam','sam',{'original'})['conversations'] if c['destination']['kind']=='domain-conversation')
        requirements=[r for r in core_rows(self.path)['records'] if r[2]=='requirement']
        result=self.save(destination,actor='sam')
        after=core_rows(self.path)
        self.assertEqual(self.save(destination,actor='sam'),result);self.assertEqual(core_rows(self.path),after)
        file=self.library.detail('profile:sam','sam',{'original'},result['id'])
        self.assertEqual(file['domain'],'research');self.assertTrue(file['locations'])
        self.assertEqual([r for r in after['records'] if r[2]=='requirement'],requirements)
        self.assertFalse(any(r[2] in ('domain-chat-review','decision','intake-decision') for r in after['records']))
    def test_project_domain_upload_does_not_create_a_conversation_or_give_admin_private_rights(self):
        destinations=self.router.destinations('profile:sam','sam',{'original'})
        result=self.save(destinations['projects'][0]['destination'],actor='sam')
        file=self.library.detail('profile:sam','sam',{'original'},result['id'])
        self.assertEqual(file['area'],'Research');self.assertEqual(file['locations'],[])
        self.assertEqual(self.router.destinations('profile:administrator','administrator',{'original'})['projects'],[])
        with self.assertRaises(PermissionError):self.save(self.business(),actor='administrator')
        with self.assertRaises(PermissionError):self.save(self.business(),actor='sam',request='sam-cannot-business')
    def test_reset_membership_owner_and_domain_changes_invalidate_the_destination(self):
        destination=self.business()
        with self.assertRaises(StaleBasis):
            self.router.upload('profile:priya','priya',None,{'original'},dict(expected_owner='profile:sam',request_id='wrong-owner-0001',destination=destination,**upload()))
        with self.assertRaises(PermissionError):
            self.router.upload('profile:priya','priya',None,set(),dict(expected_owner='profile:priya',request_id='no-membership-001',destination=destination,**upload()))
        sam_dest=self.router.destinations('profile:sam','sam',{'original'})['projects'][0]['destination']
        self.store.put('REASSIGN','domain-definition',SCOPE,dict(key='research',label='Research',purpose='Reassigned',members=['lee'],leaders=['lee']))
        with self.assertRaises(PermissionError):self.save(sam_dest,actor='sam')
        self.projects.replace(self.projects.current('original'),dict(confirm_title='Synthetic files'),'priya')
        with self.assertRaises(StaleBasis):self.save(destination,request='reset-destination-001')
    def test_failed_project_extraction_creates_no_source_or_intake(self):
        other=self.projects.create(dict(title='Failed upload target'),'priya')['project_id']
        project=self.projects.current(other);before=core_rows(project['path'])
        destination=dict(kind='project',project=other,generation=project['version'],domain='business')
        with self.assertRaises(ValueError):
            self.router.upload('profile:priya','priya',None,{other},dict(expected_owner='profile:priya',request_id='failed-source-001',destination=destination,**upload('Bad file.','bad.exe')))
        self.assertEqual(core_rows(project['path']),before)


class UploadRoutingHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory();path=Path(cls.tmp.name)/'http.sqlite3';store=Store(path)
        Workspace(store,'alex').setup(dict(title='Upload destination fixture',intent='Private files',boundary='Synthetic only'));store.close()
        cls.server=BrowserServer(('127.0.0.1',0),path,NoCalls());cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.admin=Client(cls.server);token=cls.server.access.setup_file.read_text().split('#enroll=')[1].strip()
        cls.admin.post('auth-enroll',dict(token=token,username='admin',password=PASSWORD))
        _,invite=cls.admin.post('access-invite',dict(actor='priya'));cls.user=Client(cls.server)
        cls.user.post('auth-enroll',dict(token=invite['token'],username='sponsor',password=PASSWORD))
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
    def test_http_upload_is_authenticated_csrf_bound_owner_checked_and_supports_existing_file_limit(self):
        self.assertEqual(Client(self.server).get('/api/my-file-destinations')[0],401)
        status,choices=self.user.get('/api/my-file-destinations');self.assertEqual(status,200);self.assertEqual(len(choices['projects']),1)
        body=dict(expected_owner=choices['owner'],request_id='large-http-file-001',destination=dict(kind='new-conversation'),**upload('界'*90000,'large.txt'))
        self.assertGreater(len(json.dumps(body)),262144)
        self.assertEqual(self.user.request('POST','/api/my-file-upload',body,{'X-CSRF-Token':''})[0],403)
        self.assertEqual(self.admin.post('my-file-upload',body)[0],409)
        status,result=self.user.post('my-file-upload',body);self.assertEqual(status,200,result)
        self.assertEqual(self.user.post('my-file-upload',body)[1]['id'],result['id'])
        library=self.user.get('/api/my-files')[1];self.assertEqual(len(library['files']),1);self.assertEqual(library['files'][0]['characters'],90000)
        self.assertEqual(self.admin.get('/api/my-files')[1]['files'],[])
        self.assertEqual(self.user.get('/api/my-file?id='+result['id'])[1]['text'],'界'*90000)

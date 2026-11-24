"""Personal inventory never widens source access or alters evidence."""
import base64
import hashlib
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import unittest

from workbench.core import Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.intake import PRIVATE
from workbench.model_provider import UnconfiguredModel
from workbench.my_files import MyFiles, readonly
from workbench.projects import Projects
from workbench.thought_partner import ThoughtPartner
from workbench.web import BrowserServer
from workbench.workspace import Workspace
from test_access import Client, PASSWORD


def upload(text='Synthetic source text.',name='example.txt'):
    return dict(filename=name,content=base64.b64encode(text.encode()).decode())


def core_rows(path):
    with readonly(path) as db:
        return {t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in ('records','dependencies','packets')}


class FileLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'files.sqlite3'
        self.store=Store(self.path)
        Workspace(self.store,'alex').setup(dict(title='Synthetic files',intent='Keep evidence',boundary='Test only'))
        self.priya=Workspace(self.store,'priya')
        self.priya.command('intake-start',dict(title='Synthetic files'))
        self.projects=Projects(self.path);self.chat=ThoughtPartner(self.path,self.projects,UnconfiguredModel())
        self.library=MyFiles(self.path,self.projects,self.chat)
    def tearDown(self):
        self.store.close();self.tmp.cleanup()
    def source(self,w=None,**data):
        return (w or self.priya).command('intake-source',data or upload())['ref']
    def files(self,owner='profile:priya',actor='priya',allowed=None):
        return self.library.listing(owner,actor,{'original'} if allowed is None else allowed)['files']
    def test_inventory_joins_project_and_conversation_without_reading_other_people(self):
        self.source()
        tid=self.chat.create('profile:priya',dict(title='Private conversation'))['id']
        self.chat.attach('profile:priya',{'original'},dict(thread=tid,**upload('Conversation material.','chat.txt')))
        other=self.chat.create('profile:sam',dict(title='SECRET_OTHER_THREAD'))['id']
        self.chat.attach('profile:sam',{'original'},dict(thread=other,**upload('SECRET_OTHER_FILE','other.txt')))
        Workspace(self.store,'sam').command('domain-source',upload('SECRET_RESEARCH','research.txt'))
        before=core_rows(self.path);files=self.files();encoded=json.dumps(files)
        self.assertEqual(len(files),2);self.assertEqual({f['kind'] for f in files},{'project','conversation'})
        for forbidden in ('SECRET','Synthetic source text','Conversation material','_path','original_bytes','context'):self.assertNotIn(forbidden,encoded)
        self.assertTrue(all(f['original_available'] for f in files));self.assertEqual(core_rows(self.path),before)
        self.assertEqual(self.files('profile:administrator','administrator'),[])
        self.assertEqual(self.library.path.stat().st_mode&0o777,0o600)
    def test_original_round_trip_integrity_and_explicit_legacy_text_fallback(self):
        self.source(**upload('Precise original bytes.','résumé.txt'));f=self.files()[0]
        raw,name,mime=self.library.download('profile:priya','priya',{'original'},f['id'],'original')
        self.assertEqual(raw,b'Precise original bytes.');self.assertEqual(name,'résumé.txt')
        legacy=self.store.put('LEGACY','intake-source',PRIVATE,dict(author='priya',title='Earlier.docx',text='Retained text.',parser='docx-text-v1',at='2026-01-01'))
        old=next(f for f in self.files() if f['source']['id']==legacy.id)
        self.assertFalse(old['original_available']);self.assertEqual(old['ownership'],'earlier-role-upload')
        with self.assertRaises(ValueError):self.library.download('profile:priya','priya',{'original'},old['id'],'original')
        self.assertEqual(self.library.download('profile:priya','priya',{'original'},old['id'],'text')[0],b'Retained text.')
        self.store.db.execute("UPDATE user_uploads SET original=?",(b'tampered',));self.store.db.commit()
        with self.assertRaisesRegex(ValueError,'integrity'):self.library.download('profile:priya','priya',{'original'},f['id'],'original')
    def test_names_archive_restore_are_personal_and_preserve_exact_evidence_and_chat(self):
        self.source();f=self.files()[0];before=core_rows(self.path)
        for revision,action in enumerate(('rename','archive','restore')):
            self.library.update('profile:priya','priya',{'original'},dict(id=f['id'],expected_revision=revision,action=action,title='My display name'))
        current=self.files()[0];self.assertEqual(current['title'],'My display name');self.assertFalse(current['archived']);self.assertEqual(current['revision'],3)
        self.assertEqual(core_rows(self.path),before)
        with self.assertRaises(StaleBasis):self.library.update('profile:priya','priya',{'original'},dict(id=f['id'],expected_revision=0,action='archive'))
        tid=self.chat.create('profile:priya',{})['id'];doc=self.chat.attach('profile:priya',{'original'},dict(thread=tid,**upload('Keep future source use.','keep.txt')))
        cf=next(f for f in self.files() if f['kind']=='conversation')
        self.library.update('profile:priya','priya',{'original'},dict(id=cf['id'],expected_revision=0,action='archive'))
        self.assertFalse(self.chat.document('profile:priya',{'original'},tid,doc['id'])['archived'])
    def test_new_principal_receipts_override_legacy_role_inference_and_deduplicate_safely(self):
        w=Workspace(self.store,'priya',principal_id='alice');self.source(w,**upload('Alice account upload.','alice.txt'))
        self.assertEqual(self.files(),[])
        self.assertEqual(len(self.files('account:alice')),1);self.assertEqual(self.files('account:bob'),[])
        first=Workspace(self.store,'sam',principal_id='alice').command('domain-source',upload('Shared domain file.','one.txt'))
        second=Workspace(self.store,'sam',principal_id='bob').command('domain-source',upload('Shared domain file.','two.txt'))
        self.assertEqual(first['ref'],second['ref'])
        a=self.files('account:alice','sam');b=self.files('account:bob','sam')
        self.assertEqual(len(a),1);self.assertEqual(len(b),1);self.assertEqual(a[0]['filename'],'one.txt');self.assertEqual(b[0]['filename'],'two.txt')
        self.assertEqual(self.files('profile:sam','sam'),[])
    def test_project_and_domain_revocation_recheck_detail_download_and_updates(self):
        sam=Workspace(self.store,'sam');sam.command('domain-source',upload('Private Research file.','research.txt'))
        f=self.files('profile:sam','sam')[0]
        for operation in ('detail','download','update'):
            with self.assertRaises(PermissionError):
                if operation=='detail':self.library.detail('profile:sam','sam',set(),f['id'])
                elif operation=='download':self.library.download('profile:sam','sam',set(),f['id'],'original')
                else:self.library.update('profile:sam','sam',set(),dict(id=f['id'],expected_revision=0,action='archive'))
        self.store.put('DOMAIN-research','domain-definition',SCOPE,dict(key='research',label='Research',purpose='Reassigned',members=['lee'],leaders=['lee']))
        self.assertEqual(self.files('profile:sam','sam'),[])
        with self.assertRaises(PermissionError):self.library.detail('profile:sam','sam',{'original'},f['id'])
    def test_blocked_thread_files_and_names_never_enter_the_index(self):
        tid=self.chat.create('profile:priya',dict(title='SECRET_REVOKED_THREAD'))['id']
        self.chat.attach('profile:priya',{'original'},dict(thread=tid,**upload('Private blocked file.','SECRET_DOCUMENT.txt')))
        with self.chat.db() as db:
            db.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',('M',tid,1,'user','Question','complete','request',json.dumps(dict(projects=[dict(id='revoked')])), '[]','2026-01-01',None,'live'))
        data=self.library.listing('profile:priya','priya',{'original'})
        self.assertNotIn('SECRET',json.dumps(data));self.assertEqual(data['files'],[])
    def test_saved_project_versions_keep_originals_and_domain_thread_locations(self):
        self.source(**upload('Before reset.','before.txt'));old=self.files()[0]
        self.store.close()
        self.projects.replace(self.projects.current('original'),dict(confirm_title='Synthetic files'),'priya')
        self.store=Store(self.projects.current('original')['path'])
        saved=self.files()[0];self.assertEqual(saved['id'],old['id']);self.assertTrue(saved['saved_version'])
        self.assertEqual(self.library.download('profile:priya','priya',{'original'},saved['id'],'original')[0],b'Before reset.')
        sam=Workspace(self.store,'sam');start=sam.command('domain-chat-start',dict(title='Review notes'));draft=self.store.latest(start['id'],sam.scopes)
        thread=sam.domain_chat.threads()[0]
        sam.command('domain-chat-attach',dict(conversation=dict(id=thread['ref'].id,revision=thread['ref'].revision),expected=dict(id=draft['ref'].id,revision=draft['ref'].revision),**upload('Research notes.','notes.txt')))
        f=self.files('profile:sam','sam')[0];self.assertEqual(f['locations'][0]['id'],thread['ref'].id);self.assertEqual(f['locations'][0]['draft'],draft['ref'].id)


class FileLibraryHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=TemporaryDirectory();path=Path(cls.tmp.name)/'web.sqlite3';store=Store(path)
        Workspace(store,'alex').setup(dict(title='Private file access',intent='Scope files',boundary='Synthetic only'));store.close()
        cls.server=BrowserServer(('127.0.0.1',0),path,UnconfiguredModel())
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.admin=Client(cls.server);token=cls.server.access.setup_file.read_text().split('#enroll=')[1].strip()
        cls.admin.post('auth-enroll',dict(token=token,username='admin',password=PASSWORD))
        _,invite=cls.admin.post('access-invite',dict(actor='priya'));cls.user=Client(cls.server)
        cls.user.post('auth-enroll',dict(token=invite['token'],username='sponsor',password=PASSWORD))
        cls.user.post('intake-start',dict(title='Private file access'))
        status,result=cls.user.post('intake-source',upload('Owned file body.','owned.txt'));assert status==200,result
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
    def test_library_has_owner_csrf_membership_and_binary_download_boundaries(self):
        self.assertEqual(Client(self.server).get('/api/my-files')[0],401)
        status,data=self.user.get('/api/my-files');self.assertEqual(status,200);f=data['files'][0]
        self.assertNotIn('Owned file body',json.dumps(data));self.assertEqual(self.admin.get('/api/my-files')[1]['files'],[])
        self.assertEqual(self.admin.get('/api/my-file?id='+f['id'])[0],403)
        self.assertEqual(self.user.request('POST','/api/my-file-update',dict(id=f['id'],action='archive',expected_revision=0),{'X-CSRF-Token':''})[0],403)
        self.assertEqual(self.user.post('my-file-update',dict(id=f['id'],action='rename',title='Mine',expected_revision=0,owner='account:someone-else',admin=True))[0],200)
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port);conn.request('GET','/api/my-file-download?id='+f['id']+'&format=original',headers={'Cookie':self.user.cookie})
        response=conn.getresponse();self.assertEqual(response.status,200);self.assertEqual(response.read(),b'Owned file body.');self.assertIn('attachment;',response.getheader('Content-Disposition'));conn.close()
        account=self.user.get('/api/auth')[1]['account']
        self.admin.post('access-revoke',dict(account=account['id']))
        self.assertEqual(self.user.get('/api/my-files')[1]['files'],[])
        self.assertEqual(self.user.get('/api/my-file?id='+f['id'])[0],403)

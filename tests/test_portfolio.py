"""Portfolio visibility never grants project/private work access."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3
import threading
import unittest
from workbench.core import Store
from workbench.projects import Projects
from workbench.portfolio import portfolio
from workbench.project_connections import connect,fingerprint,readonly
from workbench.decisions import SCOPE
from workbench.intake import PRIVATE
from workbench.web import BrowserServer
from workbench.model_provider import UnconfiguredModel
from workbench.access import Access
from workbench.workspace import Workspace
from test_access import Client,PASSWORD

class ProjectConnectionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();root=Path(self.tmp.name);self.source=root/'earlier.sqlite3';self.target=root/'current.sqlite3'
  for p,title in ((self.source,'Earlier project'),(self.target,'Current project')):
   store=Store(p);store.put('PROJECT-001','project',SCOPE,dict(title=title,sponsor='priya'));store.put('PRIVATE','intake-source',PRIVATE,dict(text='SECRET_PRIVATE_DOCUMENT'));store.close()
  self.src=Projects(self.source);self.dest=Projects(self.target)
 def tearDown(self):self.tmp.cleanup()
 def test_connect_preserves_exact_current_history_and_original_store(self):
  self.src.replace(self.src.current('original'),dict(confirm_title='Earlier project'),'priya')
  with readonly(self.src.current('original')['path']) as db:source=fingerprint(db)
  with self.src.db() as db:original_history=db.execute("SELECT path FROM saved_versions WHERE project_id='original'").fetchone()[0]
  with readonly(original_history) as db:old=fingerprint(db)
  result=connect(self.dest,self.src.catalog,'Earlier Workbench');pid=result[0]['project_id'];project=self.dest.current(pid)
  self.assertEqual(project['version'],2)
  with readonly(project['path']) as db:self.assertEqual(fingerprint(db),source)
  copied_history=self.dest.history(pid)
  self.assertEqual(len(copied_history),1)
  with self.dest.db() as db:copied_path=db.execute('SELECT path FROM saved_versions WHERE project_id=?',(pid,)).fetchone()[0]
  with readonly(copied_path) as db:self.assertEqual(fingerprint(db),old)
  with readonly(original_history) as db:self.assertEqual(fingerprint(db),old)
  self.assertEqual(len(self.dest.listing()),2);self.assertEqual(self.dest.info(project)['origin'],'Earlier Workbench')
  self.assertNotEqual(project['path'],self.src.current('original')['path'])
 def test_reconnecting_never_overwrites_a_working_copy_or_merges_names(self):
  pid=connect(self.dest,self.src.catalog,'Earlier Workbench')[0]['project_id'];path=self.dest.current(pid)['path']
  store=Store(path);store.put('EDIT','note',PRIVATE,dict(text='Keep authored work'));store.close()
  store=Store(self.source);store.put('SOURCE-CHANGED','note',PRIVATE,dict(text='New upstream note'));store.close()
  result=connect(self.dest,self.src.catalog,'Earlier Workbench')[0];self.assertEqual(result['status'],'already-connected');self.assertTrue(result['source_changed'])
  with readonly(path) as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM records WHERE id='EDIT'").fetchone()[0],1);self.assertEqual(db.execute("SELECT COUNT(*) FROM records WHERE id='SOURCE-CHANGED'").fetchone()[0],0)
  other=Path(self.tmp.name)/'other.sqlite3';store=Store(other);store.put('PROJECT-001','project',SCOPE,dict(title='Earlier project',sponsor='priya'));store.close()
  second=connect(self.dest,Projects(other).catalog,'Other branch')[0]['project_id'];self.assertNotEqual(pid,second)
  self.assertEqual(len(self.dest.listing()),3)
 def test_empty_sources_are_skipped_and_no_account_or_chat_sidecars_are_imported(self):
  empty=Path(self.tmp.name)/'empty.sqlite3';Store(empty).close();catalog=Projects(empty)
  empty.with_name('empty-thought-partner.sqlite3').write_text('NEVER COPY CHAT')
  empty.with_name('empty-access.sqlite3').write_text('NEVER COPY ACCOUNTS')
  self.assertEqual(connect(self.dest,catalog.catalog,'Empty')[0]['status'],'empty-skipped');self.assertEqual(len(self.dest.listing()),1)

class PortfolioProjectionTests(unittest.TestCase):
 def test_only_shared_signals_are_exposed_and_reads_do_not_write(self):
  with TemporaryDirectory() as tmp:
   path=Path(tmp)/'project.sqlite3';store=Store(path)
   store.put('PROJECT-001','project',SCOPE,dict(title='Synthetic project',sponsor='priya',created_at='2026-11-11'))
   store.put('INT','intent',SCOPE,dict(text='Shared intent text must not be repeated',status='accepted'))
   store.put('ISSUE','bridge-issue',SCOPE,dict(title='Evidence ownership',status='investigating',next_owner='sam',updated_at='2026-11-11T12:00:00Z'))
   store.put('CASE','decision-case',SCOPE,dict(status='pending-review',proposal='DO NOT SERIALIZE ENTIRE PROPOSAL'))
   store.put('PUBLIC','contribution',SCOPE,dict(domain_key='research',published_at='2026-11-11T11:00:00Z',text='Do not serialize report contents'))
   store.put('PRIVATE','contribution','domain:design',dict(domain_key='LEAK_PRIVATE_TEAM',title='SECRET_PRIVATE_DOCUMENT',status='working',published_at='2099-01-01'))
   store.put('UNPUBLISHED','contribution',SCOPE,dict(domain_key='LEAK_UNPUBLISHED',status='draft',published_at='2099-01-01'))
   store.put('DRAFT','intake-draft',PRIVATE,dict(text='SECRET_INTAKE'));store.close();catalog=Projects(path)
   with readonly(path) as db:before=fingerprint(db)
   rows=portfolio(catalog,{'original'},set());encoded=json.dumps(rows)
   for secret in ('SECRET','LEAK_PRIVATE','DO NOT SERIALIZE','Do not serialize','2099','summary','source_count'):self.assertNotIn(secret,encoded)
   row=rows[0];self.assertFalse(row['can_open']);self.assertEqual(row['open_issues'],1);self.assertEqual(row['pending_decisions'],1);self.assertEqual(row['teams'],['Research']);self.assertEqual(row['sponsor'],'Dana Okafor')
   with readonly(path) as db:self.assertEqual(fingerprint(db),before)
   with self.assertRaises(PermissionError):portfolio(catalog,set(),{'original'})

class PortfolioHTTPTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=TemporaryDirectory();path=Path(cls.tmp.name)/'accounts.sqlite3';store=Store(path);store.put('PROJECT-001','project',SCOPE,dict(title='Member project',sponsor='priya'));store.close()
  cls.server=BrowserServer(('127.0.0.1',0),path,UnconfiguredModel());cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.admin=Client(cls.server);token=cls.server.access.setup_file.read_text().split('#enroll=')[1].strip();status,result=cls.admin.post('auth-enroll',dict(token=token,username='portfolio-admin',password=PASSWORD));assert status==200,result
  _,invite=cls.admin.post('access-invite',dict(actor='sam'));cls.leader=Client(cls.server);status,result=cls.leader.post('auth-enroll',dict(token=invite['token'],username='leader',password=PASSWORD));assert status==200,result;cls.leader_id=result['account']['id']
  cls.other=cls.server.projects.create(dict(title='Unassigned project'),'priya')['project_id']
  project=cls.server.projects.current(cls.other);store=Store(project['path']);store.put('SECRET','contribution-draft','domain:research',dict(text='SECRET_OTHER_PRIVATE_WORK'));store.close()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
 def test_explicit_portfolio_permission_is_independent_of_admin_membership_and_chat(self):
  self.assertEqual(self.admin.get('/api/portfolio')[0],403);self.assertEqual(self.leader.get('/api/portfolio-access')[0],403)
  status,cfg=self.admin.get('/api/portfolio-access');self.assertEqual(status,200);person=next(a for a in cfg['accounts'] if a['id']==self.leader_id)
  status,result=self.admin.post('portfolio-access-save',dict(account=self.leader_id,projects=['original',self.other],expected=person['basis']));self.assertEqual(status,200,result)
  status,home=self.leader.get('/api/home');self.assertEqual(status,200);self.assertEqual([p['id'] for p in home['projects']],['original']);self.assertTrue(home['portfolio']['available']);self.assertEqual(home['records'],[])
  status,result=self.leader.get('/api/portfolio');self.assertEqual(status,200);self.assertEqual(len(result['projects']),2);self.assertNotIn('SECRET',json.dumps(result));self.assertFalse(next(p for p in result['projects'] if p['id']==self.other)['can_open'])
  self.assertEqual(self.leader.get('/api/state?project='+self.other)[0],403)
  _,thread=self.leader.post('thought-chat-create',dict(title='Private conversation'))
  status,_=self.leader.post('thought-chat-send',dict(thread=thread['id'],request_id='portfolio-deny',expected_count=0,message='Read the other project',projects=[dict(id=self.other,version=1)],consent=True));self.assertEqual(status,403)
  self.assertEqual(self.leader.post('portfolio-access-save',dict(account=self.leader_id,projects=[],admin=True))[0],403)
  # A portfolio-only user can reach global Home without receiving project membership.
  with self.server.access.db() as db:db.execute('DELETE FROM memberships WHERE account=?',(self.leader_id,))
  status,home=self.leader.get('/api/home');self.assertEqual(status,200);self.assertEqual(home['projects'],[]);self.assertTrue(home['portfolio']['available'])
  _,cfg=self.admin.get('/api/portfolio-access');person=next(a for a in cfg['accounts'] if a['id']==self.leader_id)
  self.assertEqual(self.admin.post('portfolio-access-save',dict(account=self.leader_id,projects=[],expected=person['basis']))[0],200)
  self.assertEqual(self.leader.get('/api/portfolio')[0],403);self.assertEqual(self.admin.get('/api/portfolio')[0],403)

class AdministratorPersonaTests(unittest.TestCase):
 def test_administrator_is_separate_from_sponsor_and_private_domain_work_in_development(self):
  with TemporaryDirectory() as tmp:
   path=Path(tmp)/'personas.sqlite3';store=Store(path)
   Workspace(store,'alex').setup(dict(title='Synthetic separate personas',intent='Keep context',boundary='Test only'))
   store.put('PRIVATE-INTAKE','intake-source',PRIVATE,dict(text='NEVER_SHOW_SPONSOR_DOCUMENT'))
   store.put('PRIVATE-RESEARCH','contribution-draft','domain:research',dict(title='NEVER_SHOW_DOMAIN_DRAFT'))
   store.close();server=BrowserServer(('127.0.0.1',0),path,UnconfiguredModel(),development=True)
   source=Path(tmp)/'earlier.sqlite3';older=Store(source);older.put('PROJECT-001','project',SCOPE,dict(title='Earlier private sponsor project',sponsor='priya'));older.put('OLD-PRIVATE','intake-source',PRIVATE,dict(text='NEVER_SHOW_IMPORTED_DOCUMENT'));older.close()
   imported=connect(server.projects,Projects(source).catalog,'Earlier version')[0]['project_id']
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    client=Client(server);status,home=client.get('/api/home');self.assertEqual(status,200)
    self.assertEqual(home['actor'],'priya');self.assertFalse(home['auth']['administrator']);self.assertFalse(home['portfolio']['available']);self.assertIsNone(home['overview'])
    self.assertEqual([p['id'] for p in home['projects']],['original']);self.assertEqual(client.get('/api/state?project='+imported)[0],403)
    self.assertEqual(client.get('/api/portfolio')[0],403);self.assertTrue(client.get('/api/portfolio-access')[1]['preview'])
    self.assertTrue(client.get()[1]['domain_knowledge']['can_add'])
    self.assertEqual(client.post('domain-add',dict(label='Fictional settings team',purpose='Local configuration test',members=['sam'],leaders=['sam']))[0],200)
    self.assertEqual(client.post('profile',dict(actor='administrator'))[0],200)
    status,home=client.get('/api/home');self.assertEqual(status,200);self.assertTrue(home['auth']['administrator']);self.assertTrue(home['portfolio']['available']);self.assertEqual(len(home['overview']),2)
    self.assertNotIn('NEVER_SHOW',json.dumps(home));self.assertEqual(client.get('/api/portfolio-access')[1]['preview'],True)
    status,imported_state=client.get('/api/state?project='+imported);self.assertEqual(status,200);self.assertNotIn('NEVER_SHOW',json.dumps(imported_state))
    status,state=client.get();self.assertEqual(status,200);self.assertTrue(state['domain_knowledge']['can_add']);self.assertNotIn('NEVER_SHOW',json.dumps(state))
    self.assertEqual(client.post('project-create',dict(title='Admin cannot be sponsor'))[0],403)
    self.assertEqual(client.post('intake-start',dict(title='Admin cannot draft sponsor intent'))[0],403)
    self.assertEqual(client.post('profile',dict(actor='priya'))[0],200);self.assertFalse(client.get('/api/home')[1]['portfolio']['available'])
   finally:server.shutdown();server.server_close();thread.join()

 def test_account_bootstrap_and_legacy_migration_preserve_identity_without_implicit_private_access(self):
  with TemporaryDirectory() as tmp:
   anchor=Path(tmp)/'accounts.sqlite3';access=Access(anchor)
   with access.db() as db:
    db.execute('INSERT INTO accounts VALUES (?,?,?,?,?,?)',('stable-owner','existing-admin','priya','existing-salt','existing-hash',1))
    db.execute('INSERT INTO memberships VALUES (?,?)',('stable-owner','original'))
   reopened=Access(anchor);account=reopened.account('stable-owner')
   self.assertEqual(account['actor'],'administrator');self.assertTrue(account['admin']);self.assertEqual(reopened.projects(account),{'original'});self.assertEqual(reopened.portfolio_projects(account),set())
   with reopened.db() as db:
    row=db.execute('SELECT salt,hash FROM accounts WHERE id=?',('stable-owner',)).fetchone();self.assertEqual(tuple(row),('existing-salt','existing-hash'))
    self.assertEqual(db.execute("SELECT COUNT(*) FROM access_audit WHERE action='separate-admin-persona'").fetchone()[0],1)
   Access(anchor)
   with reopened.db() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM access_audit WHERE action='separate-admin-persona'").fetchone()[0],1)

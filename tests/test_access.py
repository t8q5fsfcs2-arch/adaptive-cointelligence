from brief_fixture import complete_design_brief
"""Authenticated HTTP boundary tests with independent browser sessions and synthetic data."""
from dataclasses import asdict
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from workbench.core import Store, Ref
from workbench.decisions import SCOPE
from workbench.web import BrowserServer
from workbench.workspace import Workspace
from workbench.model_provider import UnconfiguredModel

PASSWORD='Synthetic test passphrase 2026!'

class Client:
    def __init__(self,server):
        self.server=server;self.cookie='';self.csrf='';self.project='original';self.version=1
        _,state=self.get('/api/auth');self.csrf=state['csrf']
    def request(self,method,path,data=None,extra=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        headers={'Cookie':self.cookie,'Content-Type':'application/json','X-CSRF-Token':self.csrf,
                 'X-Workbench-Project':self.project,'X-Workbench-Version':str(self.version),**(extra or {})}
        conn.request(method,path,json.dumps(data) if data is not None else None,headers)
        r=conn.getresponse();cookie=r.getheader('Set-Cookie')
        if cookie:self.cookie=cookie.split(';')[0]
        body=json.loads(r.read());status=r.status;conn.close()
        if 'csrf' in body:self.csrf=body['csrf']
        return status,body
    def get(self,path='/api/state'):return self.request('GET',path)
    def post(self,action,data):return self.request('POST','/api/'+action,data)

class AccountBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.path=Path(cls.tmp.name)/'fixture.sqlite3'
        store=Store(cls.path)
        try:Workspace(store,'alex').setup(dict(title='Synthetic account isolation',intent='Preserve work',boundary='Retain evidence'))
        finally:store.close()
        cls.server=BrowserServer(('127.0.0.1',0),cls.path,UnconfiguredModel())
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.admin=Client(cls.server)
        cls.bootstrap_token=cls.server.access.setup_file.read_text().split('#enroll=')[1].strip()
        status,body=cls.admin.post('auth-enroll',dict(token=cls.bootstrap_token,username='owner',password=PASSWORD))
        assert status==200,body
        cls.accounts={}
        for actor in ('sam','lee'):
            status,inv=cls.admin.post('access-invite',dict(actor=actor));assert status==200,inv
            client=Client(cls.server)
            status,account=client.post('auth-enroll',dict(token=inv['token'],username=actor,password=PASSWORD))
            assert status==200,account
            cls.accounts[actor]=account['account']
        cls.other=cls.server.projects.create({'title':'Unassigned private project'},'priya')['project_id']
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
    def signed(self,actor):
        c=Client(self.server);status,body=c.post('auth-login',dict(username=actor,password=PASSWORD));self.assertEqual(status,200,body);return c
    def test_unauthenticated_cannot_read_or_mutate(self):
        c=Client(self.server);self.assertEqual(c.get()[0],401)
        self.assertEqual(c.post('profile',{'actor':'priya'})[0],401)
        self.assertEqual(c.post('domain-save',{})[0],401)
        self.assertEqual(c.post('auth-enroll',dict(token=self.bootstrap_token,username='intruder',password=PASSWORD))[0],400)
        self.assertFalse(self.server.access.setup_file.exists())
    def test_membership_filters_catalog_and_denies_direct_project_access(self):
        c=self.signed('sam');status,state=c.get();self.assertEqual(status,200)
        self.assertEqual(state['actor'],'sam');self.assertEqual([p['id'] for p in state['projects']],['original'])
        self.assertEqual([p['key'] for p in state['domains']['profiles']],['research'])
        self.assertEqual(c.get('/api/state?project='+self.other)[0],403)
        c.project=self.other
        self.assertEqual(c.post('domain-save',{})[0],403)
    def test_agent_activity_requires_membership_and_current_project_generation(self):
        base='/api/project-agent-activity?project='
        self.assertEqual(Client(self.server).get(base+'original&generation=1')[0],401)
        client=self.signed('sam')
        self.assertEqual(client.get(base+self.other+'&generation=1')[0],403)
        self.assertEqual(client.get(base+'original&generation=999')[0],409)
        self.assertEqual(client.get(base+'original&generation=1')[0],200)

    def test_no_role_switch_or_posted_actor_escalation(self):
        c=self.signed('sam')
        self.assertEqual(c.post('profile',{'actor':'lee'})[0],403)
        self.assertEqual(c.post('setup',{'actor':'alex','title':'spoof','intent':'no','boundary':'no'})[0],403)
        self.assertEqual(c.post('access-invite',{'actor':'lee'})[0],403)
        self.assertEqual(c.post('project-create',{'title':'spoof'})[0],403)
    def test_administrator_has_own_persona_and_sponsor_membership_does_not_grant_admin(self):
        home=self.admin.get('/api/home')[1]
        self.assertEqual(home['actor'],'administrator');self.assertTrue(home['auth']['account']['admin'])
        self.assertEqual(home['projects'],[]);self.assertFalse(home['portfolio']['available'])
        status,inv=self.admin.post('access-invite',dict(actor='priya'));self.assertEqual(status,200,inv)
        sponsor=Client(self.server);status,account=sponsor.post('auth-enroll',dict(token=inv['token'],username='sponsor',password=PASSWORD));self.assertEqual(status,200,account)
        self.assertEqual(account['account']['actor'],'priya');self.assertFalse(account['account']['admin'])
        state=sponsor.get()[1];self.assertEqual(state['actor'],'priya');self.assertFalse(state['domain_knowledge']['can_add'])
        self.assertEqual(sponsor.get('/api/portfolio-access')[0],403);self.assertEqual(sponsor.post('profile',dict(actor='administrator'))[0],403)
        self.assertEqual(sponsor.post('access-invite',dict(actor='alex',admin=True))[0],403)
    def test_admin_integration_configuration_is_separate_from_project_membership_and_private_work(self):
        anonymous=Client(self.server)
        self.assertEqual(anonymous.get('/api/admin-integrations')[0],401)
        member=self.signed('sam')
        self.assertEqual(member.get('/api/admin-integrations')[0],403)
        self.assertEqual(member.post('admin-integration-save',{'admin':True})[0],403)
        # Admin has no membership in this project; configuration does not grant it.
        self.assertEqual(self.admin.get('/api/state?project='+self.other)[0],403)
        status,data=self.admin.get('/api/admin-integrations?project='+self.other)
        self.assertEqual(status,200,data);self.assertEqual(set(data),{'project','projects','tools','connections'})
        status,saved=self.admin.request('POST','/api/admin-integration-save',dict(expected=data['connections']['ref'],name='Admin configuration test',kind='mcp',endpoint='https://example.test/mcp',purpose='Read approved content',credential_ref='WB_TEST_TOKEN'),{'X-Workbench-Project':self.other,'X-Workbench-Version':str(data['project']['version'])})
        self.assertEqual(status,200,saved)
        self.assertEqual(self.admin.get('/api/state?project='+self.other)[0],403)
        self.assertEqual(self.admin.post('intake-start',dict(title='Not authorized'))[0],403)

    def test_announcements_require_actual_admin_account_and_publish_no_private_drafts(self):
        self.assertEqual(Client(self.server).get('/api/admin-announcements')[0],401)
        member=self.signed('sam')
        self.assertEqual(member.get('/api/admin-announcements')[0],403)
        self.assertEqual(member.post('announcements-save',dict(expected=0,items=[],admin=True))[0],403)
        status,data=self.admin.get('/api/admin-announcements');self.assertEqual(status,200,data)
        items=[dict(title='Fictional product update',body='An announcement visible across projects.')]
        self.assertEqual(self.admin.post('announcements-save',dict(expected=data['revision'],items=items))[0],200)
        saved=self.admin.get('/api/admin-announcements')[1]
        self.assertNotEqual(member.get('/api/home')[1]['announcements']['items'],items)
        self.assertEqual(self.admin.post('announcements-publish',dict(expected=saved['revision'],confirm=True))[0],200)
        self.assertEqual(member.get('/api/home')[1]['announcements']['items'],items)
        self.assertEqual(self.admin.get('/api/admin-announcements')[1]['published']['author']['name'],'owner')
        self.assertEqual(self.admin.get('/api/state?project='+self.other)[0],403)

    def test_session_rotation_logout_expiry_and_cross_site_guards(self):
        c=Client(self.server);anon=c.cookie;csrf=c.csrf
        self.assertEqual(c.post('auth-login',dict(username='sam',password=PASSWORD))[0],200)
        self.assertNotEqual(anon,c.cookie);self.assertNotEqual(csrf,c.csrf)
        old=Client(self.server);old.cookie=anon;self.assertEqual(old.get()[0],401)
        self.assertEqual(c.request('POST','/api/domain-save',{}, {'Origin':'https://example.invalid'})[0],403)
        self.assertEqual(c.request('POST','/api/domain-save',{}, {'X-CSRF-Token':''})[0],403)
        signed=c.cookie;c.post('auth-logout',{});old.cookie=signed;self.assertEqual(old.get()[0],401)
        c=self.signed('sam');key=c.cookie.split('=',1)[1];self.server.sessions[key]['seen']=time.time()-1900
        self.assertEqual(c.get()[0],401)
        c=self.signed('sam');key=c.cookie.split('=',1)[1];self.server.sessions[key]['created']=time.time()-29000
        self.assertEqual(c.get()[0],401)
    def test_private_drafts_and_preflight_do_not_cross_domains(self):
        research=self.signed('sam');design=self.signed('lee')
        states={a:c.get()[1] for a,c in [('sam',research),('lee',design)]}
        drafts={}
        for a,c in [('sam',research),('lee',design)]:
            kind=states[a]['domains']['profiles'][0]['config']['deliverable_types'][0]
            status,result=c.post('domain-save',dict(title=a+' private draft',deliverable_type=kind,observation=a+' observation',source='Synthetic source',limitation='Synthetic only',interpretation=a+' private interpretation',source_refs=[],links=[]))
            self.assertEqual(status,200,result)
            state=c.get()[1];draft=next(r for r in state['records'] if r['ref']['id']==result['id']);drafts[a]=draft
            if a=='lee':
                with_store=Store(self.path)
                try:
                    w=Workspace(with_store,'lee');complete_design_brief(w,with_store.read(Ref(**draft['ref']),w.scopes))
                finally:with_store.close()
            status,h=c.post('domain-prepare',dict(expected=draft['ref'],recipient='bridge',open_questions=a+' private preflight'))
            self.assertEqual(status,200,h)
        rs=research.get()[1];ds=design.get()[1]
        self.assertNotIn('lee private',json.dumps(rs));self.assertNotIn('sam private',json.dumps(ds))
        self.assertEqual(self.admin.get()[0],403)
        self.assertNotIn('sam private',json.dumps(self.admin.get('/api/home')[1]))
        self.assertEqual(design.post('domain-prepare',dict(expected=drafts['sam']['ref'],recipient='bridge'))[0],403)
        self.assertEqual(design.post('domain-save',{**drafts['sam']['body'],'expected':drafts['sam']['ref']})[0],403)
        # Release the prepared Research handoff; only then can Design see its contents.
        h=next(x for x in rs['domains']['handoffs'] if x['body']['draft']==drafts['sam']['ref'])
        status,pub=research.post('domain-publish',dict(expected=drafts['sam']['ref'],preflight=h['ref'],confirm=True))
        self.assertEqual(status,200,pub)
        ds=design.get()[1]
        self.assertTrue(any(r['ref']['id']==pub['id'] for r in ds['records']))
        self.assertFalse(any(r['ref']['id']==drafts['sam']['ref']['id'] for r in ds['records']))
        self.assertFalse(any(x['body']['owner']=='sam' for x in ds['domains']['handoffs']))
    def test_revocation_takes_effect_for_existing_session(self):
        c=self.signed('sam');self.assertEqual(c.get()[0],200)
        self.assertEqual(self.admin.post('access-revoke',{'account':self.accounts['sam']['id']})[0],200)
        self.assertEqual(c.get()[0],403);self.assertEqual(c.post('domain-source',{'title':'x','text':'y'})[0],403)
        self.assertEqual(c.get('/api/auth')[1]['projects'],[])
        status,result=self.admin.post('access-invite',{'actor':'sam'})
        self.assertEqual(status,200,result);self.assertNotIn('token',result)
        self.assertEqual(c.get()[0],200)
    def test_password_storage_and_rate_limit(self):
        self.assertEqual(self.server.access.path.stat().st_mode & 0o777,0o600)
        with self.server.access.db() as db:
            row=db.execute('SELECT * FROM accounts WHERE username="sam"').fetchone()
            self.assertNotEqual(row['hash'],PASSWORD);self.assertNotIn(PASSWORD,str(dict(row)))
        c=Client(self.server)
        for _ in range(5):self.assertEqual(c.post('auth-login',dict(username='unknown',password='wrong'))[0],401)
        status,body=c.post('auth-login',dict(username='unknown',password='wrong'))
        self.assertEqual(status,401);self.assertIn('temporarily',body['error'])
    def test_account_protected_store_cannot_start_in_test_profile_mode(self):
        with self.assertRaisesRegex(ValueError,'account protection'):
            BrowserServer(('127.0.0.1',0),self.path,UnconfiguredModel(),test_profiles=True)

    def test_development_opens_existing_project_without_changing_accounts(self):
        def account_snapshot():
            with self.server.access.db() as db:
                return {table:[tuple(row) for row in db.execute('SELECT * FROM '+table+' ORDER BY 1')]
                        for table in ('accounts','memberships','invitations','access_audit')}
        before=account_snapshot()
        dev=BrowserServer(('127.0.0.1',0),self.path,UnconfiguredModel(),development=True)
        thread=threading.Thread(target=dev.serve_forever,daemon=True);thread.start()
        try:
            client=Client(dev)
            self.assertEqual(client.get('/api/auth')[1]['mode'],'development')
            status,state=client.get()
            self.assertEqual(status,200,state)
            self.assertEqual(state['actor'],'priya')
            self.assertEqual(state['project']['title'],'Synthetic account isolation')
            self.assertEqual(client.post('profile',{'actor':'sam'})[0],200)
            self.assertEqual(client.get()[1]['actor'],'sam')
            self.assertEqual(client.request('POST','/api/profile',{'actor':'priya'},{'X-CSRF-Token':''})[0],403)
        finally:
            dev.shutdown();dev.server_close();thread.join()
        self.assertEqual(account_snapshot(),before)
        self.assertEqual(Client(self.server).get()[0],401)

    def test_development_still_refuses_network_exposure(self):
        with self.assertRaisesRegex(ValueError,'127.0.0.1'):
            BrowserServer(('0.0.0.0',0),self.path,UnconfiguredModel(),development=True)

if __name__=='__main__':unittest.main()

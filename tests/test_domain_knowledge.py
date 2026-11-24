from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.domain_knowledge import entry, snapshot, seed_fictional_knowledge
from workbench.domain_interpretation import knowledge
from interpretation_fixture import FictionalInterpretationModel
from workbench.workspace import Workspace


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'db';self.store=Store(self.path)
        self.sam=Workspace(self.store,'sam',FictionalInterpretationModel());self.lee=Workspace(self.store,'lee');self.admin=Workspace(self.store,'administrator',admin=True)
        Workspace(self.store,'alex').setup(dict(title='Fictional knowledge',intent='Capture feedback',boundary='Non-safety'))
    def tearDown(self):self.store.close();self.temp.cleanup()
    def save(self,entries,w=None,key='research',**extra):
        values=dict(domain=key,expected=snapshot(self.store,key)['ref'],entries=entries,reason='Fictional domain-lead review.',confirm_active=True);values.update(extra)
        return (w or self.sam).command('domain-knowledge-save',values)
    def term(self,title='Observation',status='active'):return entry('term',title,'A bounded task observation.','Fictional locally authored definition.',status)
    def test_boundaries_and_reach_are_optional_lead_set_and_never_widen_without_a_proposal(self):
        plain=self.term();self.save([plain])
        self.assertEqual(snapshot(self.store,'research')['entries'],[plain])  # entries saved without meaning fields keep their exact content
        bounded=dict(self.term('Missed appointment'),includes=' Confirmed visits. ',excludes='Cancellations.',not_confused_with='Late cancellation',reach='domain')
        self.save([plain,bounded]);saved=snapshot(self.store,'research')['entries']
        self.assertEqual(saved[0],plain);self.assertEqual(saved[1]['includes'],'Confirmed visits.');self.assertEqual(saved[1]['reach'],'domain')
        for reach in ('named-domains','enterprise','everywhere'):
            with self.assertRaises(ValueError):self.save([plain,dict(bounded,reach=reach)])
        with self.assertRaises(ValueError):self.save([plain,bounded,dict(entry('standard','Rule','A rule.','Fictional.'),includes='x')])
        with self.assertRaises(ValueError):self.save([plain,dict(bounded,includes='x'*601)])
        with self.assertRaises(PermissionError):self.save([plain,dict(bounded,reach='project')],w=self.lee)
        state=self.sam.state()['domain_knowledge'];self.assertEqual(state['lead_reach'],['domain','project']);self.assertIn('enterprise',state['reach'])
    def test_active_boundaries_are_supplied_as_guidance(self):
        bounded=dict(self.term('Missed appointment'),includes='Confirmed visits.',excludes='Cancellations.',not_confused_with='Late cancellation',reach='project')
        text=next(e['text'] for e in knowledge(dict(config=dict(criteria=[]),knowledge_entries=[bounded])) if e['id']==bounded['id'])
        self.assertIn('Includes: Confirmed visits.',text);self.assertIn('Excludes: Cancellations.',text);self.assertIn('Not to be confused with: Late cancellation',text)
    def test_only_the_team_lead_edits_knowledge_and_posted_actor_is_ignored(self):
        t=self.term();self.save([t])
        with self.assertRaises(PermissionError):self.save([t],w=self.lee,actor='sam',admin=True)
        sponsor=Workspace(self.store,'priya',principal_id='ordinary-sponsor',admin=False)
        with self.assertRaises(PermissionError):self.save([t],w=sponsor)
        admin=Workspace(self.store,'alex',principal_id='actual-admin',admin=True)
        with self.assertRaises(PermissionError):self.save([t],w=admin)  # D005: lead only, not administrators
        self.save([t]);self.assertEqual(snapshot(self.store,'research')['ref']['revision'],2)
        self.assertTrue(admin.domain_knowledge.allowed(admin.domain_knowledge.definition('research')))  # admins still manage team setup
    def test_add_domain_is_admin_only_and_does_not_grant_project_membership(self):
        with self.assertRaises(PermissionError):self.sam.command('domain-add',dict(label='Training',purpose='Training quality',leaders=['sam'],admin=True))
        out=self.admin.command('domain-add',dict(label='Training',purpose='Training deliverables and knowledge',leaders=['sam']))
        self.assertEqual(out['domainKnowledge'],'training');d=self.sam.domain_knowledge.definition('training');self.assertEqual(d['runtime'],'available')
        self.assertEqual(self.sam.domains.key,'research');self.assertIn('training',[p['key'] for p in self.sam.domains.state()['profiles']])
        self.save([self.term('Course')],key='training');self.assertFalse(self.lee.domain_knowledge.allowed(d));self.assertTrue(self.sam.domain_knowledge.allowed(d))
        with self.assertRaises(ValueError):self.admin.command('domain-add',dict(label='TRAINING',purpose='Duplicate',leaders=['sam']))
    def test_history_identity_stale_save_and_archival_preserved(self):
        t=self.term();out=self.save([t]);old=deepcopy(t);t['definition']='Revised with a narrower scope.';self.save([t])
        state=self.sam.domain_knowledge.state()['domains'][0];self.assertEqual(len(state['history']),2);self.assertEqual(state['history'][1]['entries'][0],old)
        with self.assertRaises(StaleBasis):self.sam.command('domain-knowledge-save',dict(domain='research',expected=out['ref'],entries=[t],reason='Stale',confirm_active=True))
        with self.assertRaises(ValueError):self.save([])
        t['status']='archived';self.save([t]);self.assertEqual(snapshot(self.store,'research')['entries'][0]['id'],old['id'])
    def test_drafts_archived_entries_not_supplied_to_model(self):
        active=self.term();draft=self.term('Unconfirmed policy','draft');archived=self.term('Old policy','archived');self.save([active,draft,archived])
        p=self.sam.domains.profile();self.assertEqual([e['id'] for e in p['knowledge_entries']],[active['id']]);ks=knowledge(p)
        self.assertTrue(any(k['id']==active['id'] for k in ks));self.assertNotIn('Unconfirmed policy',str(p));self.assertNotIn(archived['id'],str(p))
        self.assertEqual(next(k for k in ks if k['id']==active['id'])['ref']['revision'],1)
    def test_active_guidance_needs_source_and_explicit_confirmation(self):
        t=self.term();t['source']=''
        with self.assertRaises(ValueError):self.save([t])
        t['source']='Declared local practice'
        with self.assertRaises(ValueError):self.save([t],confirm_active=False)
        self.assertIsNone(snapshot(self.store,'research')['ref'])
    def test_ontology_links_and_taxonomy_cycles_validated(self):
        a=self.term('Local draft');b=self.term('Server submission');r=entry('relationship','Different states','A local draft is not a confirmed submission.','Fictional rule');r.update(subject_id=a['id'],object_id=b['id'],predicate='differs-from')
        self.save([a,b,r]);bad=deepcopy(r);bad['object_id']='KN-000000000000'
        with self.assertRaises(ValueError):self.save([a,b,bad])
        archived=deepcopy(a);archived['status']='archived'
        with self.assertRaises(ValueError):self.save([archived,b,r])
        c=entry('category','Recovery','Recovery states','Local rationale');d=entry('category','Offline','Offline states','Local rationale');c['parent_id']=d['id'];d['parent_id']=c['id']
        with self.assertRaises(ValueError):self.save([a,b,r,c,d])
        c['parent_id']='';c['status']='draft';d['parent_id']=c['id']
        with self.assertRaises(ValueError):self.save([a,b,r,c,d])
    def test_knowledge_changes_invalidate_assessment_and_preserve_original_basis(self):
        req=Workspace(self.store,'alex').create_requirement(dict(title='Photo',text='Assumption: every initial report needs a photo.',rationale='Untested',conditions='Fictional',drawer='Experience',acceptance_criteria='Investigate'))
        m=self.store.put('M','success-measure',SCOPE,dict(definition='Baseline and target unknown.'));rr=self.store.latest(req['id'],{SCOPE})['ref'];packet=dict(id='PKT-TEST',revision=1);self.store.packet('PKT-TEST',1,'Fictional',[rr,m],{SCOPE},{SCOPE})
        t=self.term();self.save([t]);out=self.sam.command('domain-interpretation-assess',dict(packet=packet,consent=True));report=self.sam.domain_interpretation.reports()[0]
        self.assertEqual(report['body']['profile']['knowledge_ref']['revision'],1);self.assertIn('DOMAIN-KNOWLEDGE-research',[r['id'] for r in report['body']['basis']])
        t['definition']='Revised bounded definition';self.save([t]);self.assertFalse(self.sam.domain_interpretation.freshness(report));self.assertEqual(report['body']['profile']['knowledge_entries'][0]['definition'],'A bounded task observation.')
    def test_seeded_domain_definitions_remain_distinct_and_persist(self):
        seed_fictional_knowledge({'sam':self.sam,'lee':self.lee});seed_fictional_knowledge({'sam':self.sam,'lee':self.lee})
        self.assertEqual(snapshot(self.store,'research')['ref']['revision'],1);self.assertEqual(len(snapshot(self.store,'design')['entries']),5)
        self.assertNotEqual(self.sam.domains.profile()['fingerprint'],self.lee.domains.profile()['fingerprint'])
        self.store.close();self.store=Store(self.path);self.assertEqual(len(Workspace(self.store,'lee').domain_knowledge.state()['domains'][1]['history']),1)

    def add_domain(self):
        self.admin.command('domain-add',dict(label='Support readiness',purpose='Prepare support knowledge and evaluate readiness.',members=['sam','lee'],leaders=['sam'],template='research'))
        return Workspace(self.store,'sam',domain_key='support-readiness')
    def test_new_domain_uses_shared_chassis_with_isolated_upload_and_release(self):
        import base64
        training=self.add_domain();research=self.sam
        self.assertEqual(training.domains.key,'support-readiness');self.assertNotIn('domain:research',training.scopes)
        started=training.command('domain-chat-start',dict(title='Fictional readiness work'));draft=self.store.latest(started['id'],training.scopes)
        uploaded=training.command('domain-source',dict(filename='fictional.txt',content=base64.b64encode(b'Fictional support dependency.').decode()))
        training.command('domain-save',{**draft['body'],'expected':asdict(draft['ref']),'source_refs':[uploaded['ref']],'links':[],'observation':'A fictional support dependency needs confirmation.','source':'Fictional note v1','limitation':'Not validated.'})
        draft=self.store.latest(draft['ref'].id,training.scopes)
        with self.assertRaises(PermissionError):research.domains.draft(asdict(draft['ref']))
        self.assertNotIn(draft['ref'].id,[r['ref'].id for r in research.latest_records()])
        prepared=training.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='bridge'))
        h=self.store.latest(prepared['domainHandoff'],training.scopes)
        with self.assertRaises(PermissionError):training.command('domain-publish',dict(expected=asdict(draft['ref']),preflight=asdict(h['ref']),confirm=True))
        out=training.command('domain-publish',dict(expected=asdict(draft['ref']),preflight=asdict(h['ref']),confirm=True,release_sources=True))
        shared=research.store.latest(out['id'],{SCOPE});self.assertEqual(shared['body']['domain_key'],'support-readiness');self.assertEqual(shared['body']['domain'],'Support readiness')
        self.assertFalse(self.store.db.execute("SELECT 1 FROM records WHERE kind='decision'").fetchone())
    def test_configured_domain_coach_uses_shared_runtime_and_monitoring(self):
        from workbench.agent_runs import monitoring
        class Model:
            def status(self):return dict(configured=True,provider='TEST DOUBLE',model='synthetic')
            def generate(self,**kw):
                self.context=kw['context'];return dict(output=dict(summary='Bounded configured-domain advice.',strengths=[],suggestions=[]))
        self.add_domain();model=Model();w=Workspace(self.store,'sam',model,domain_key='support-readiness');result=w.command('domain-chat-start',dict(title='Synthetic support review'));draft=self.store.latest(result['id'],w.scopes)
        w.command('domain-review',dict(expected=asdict(draft['ref']),consent=True))
        self.assertEqual(model.context['domain_profile']['key'],'support-readiness');run=w.latest_records('agent-execution')[0];self.assertEqual(run['body']['persona_id'],'P07');self.assertEqual(run['scope'],'domain:support-readiness')
        admin=monitoring(self.store,'alex',admin=True);self.assertEqual(admin['runs'][0]['persona_id'],'P07');self.assertNotIn('context',admin['runs'][0]);self.assertNotIn('output',admin['runs'][0])
    def test_rename_and_membership_changes_keep_identity_and_revoke_private_access(self):
        w=self.add_domain();work=w.command('domain-chat-start',dict(title='Retain history'));d=self.admin.domain_knowledge.definition('support-readiness')
        self.admin.command('domain-update',dict(domain=d['key'],expected=d['definition_ref'],label='Support experience',purpose=d['purpose'],members=['lee'],leaders=['lee'],reason='Fictional role handoff.'))
        self.assertEqual(w.domains.profile()['config']['label'],'Support experience')
        with self.assertRaises(PermissionError):w.domains.author()
        revoked=Workspace(self.store,'sam',domain_key='support-readiness');self.assertIsNone(revoked.domains.key);self.assertNotIn(work['id'],[r['ref'].id for r in revoked.latest_records()])
        self.assertEqual(Workspace(self.store,'lee',domain_key='support-readiness').domains.key,'support-readiness')
        with self.assertRaises(PermissionError):Workspace(self.store,'alex',principal_id='admin',admin=True,domain_key='support-readiness').domains.author()
    def test_leader_can_rename_but_cannot_grant_other_users_access(self):
        w=self.add_domain();d=w.domain_knowledge.definition('support-readiness');values=dict(domain=d['key'],expected=d['definition_ref'],label='Support planning',purpose=d['purpose'],members=d['members'],leaders=d['leaders'],reason='Clarify domain purpose.')
        w.command('domain-update',values)
        d=w.domain_knowledge.definition(d['key']);values.update(expected=d['definition_ref'],members=['sam','lee','alex'])
        with self.assertRaises(PermissionError):w.command('domain-update',values)
    def test_domain_brief_cannot_start_in_wrong_domain_for_same_user(self):
        w=self.add_domain();owner=Workspace(self.store,'alex');out=owner.create_requirement(dict(title='Ready',text='Make support readiness explicit.',rationale='Handoff',conditions='Fictional',drawer='Support',acceptance_criteria='Show the open support question.'));req=self.store.latest(out['id'],{SCOPE})['ref'];packet=dict(id='PKT-'+out['id'],revision=1)
        task=Workspace(self.store,'priya').project_flow.seed_legacy_request(dict(title='Readiness brief',recipient='sam',recipient_domain='support-readiness',objective='Prepare readiness evidence.',local_context='Use local support terminology.',expected_output='A bounded readiness contribution.',packet_refs=[packet],requirement_refs=[asdict(req)],requirement_guidance=[dict(ref=asdict(req),local_application='Identify support needs.',expected_evidence='A source-linked readiness gap.')]))
        ref=dict(id=task['id'],revision=1)
        with self.assertRaises(PermissionError):self.sam.command('work-request-start',dict(expected=ref))
        result=w.command('work-request-start',dict(expected=ref));draft=self.store.latest(result['id'],w.scopes);self.assertEqual(draft['scope'],'domain:support-readiness');self.assertEqual(draft['body']['work_request'],dict(id=task['id'],revision=2))


class DomainSetupHttpTests(unittest.TestCase):
    def setUp(self):
        import test_web
        test_web.WebTests.setUp(self);self.post=test_web.WebTests.post.__get__(self)
        self.post('profile',dict(actor='alex'));self.post('setup',dict(title='Fictional setup',intent='Capture feedback',boundary='Non-safety'))
    def tearDown(self):
        import test_web
        test_web.WebTests.tearDown(self)
    def get_state(self):
        self.conn.request('GET','/api/state',headers={'Cookie':self.cookie});response=self.conn.getresponse();self.assertEqual(response.status,200);return __import__('json').loads(response.read())
    def test_domain_selection_assignment_scope_and_revocation_over_http(self):
        self.post('profile',dict(actor='sam'));self.assertEqual(self.post('domain-add',dict(label='Support',purpose='Support readiness',members=['sam'],leaders=['sam'],admin=True))[0],403)
        self.post('profile',dict(actor='administrator'));status,out=self.post('domain-add',dict(label='Support',purpose='Support readiness',members=['sam','lee'],leaders=['sam']));self.assertEqual(status,200,out)
        self.assertEqual(self.post('domain-select',dict(domain='support'))[0],403)  # Admin has no implicit private access.
        self.post('profile',dict(actor='sam'));self.assertEqual(self.post('domain-select',dict(domain='support'))[0],200);self.assertEqual(self.get_state()['domains']['active'],'support')
        self.assertEqual(self.post('domain-chat-start',{},headers={'X-Workbench-Domain':'research'})[0],409)
        status,work=self.post('domain-chat-start',{},headers={'X-Workbench-Domain':'support'});self.assertEqual(status,200,work)
        self.post('profile',dict(actor='administrator'));d=next(d for d in self.get_state()['domain_knowledge']['domains'] if d['key']=='support')
        self.assertEqual(self.post('domain-update',dict(domain='support',expected=d['definition_ref'],label='Support renamed',purpose='Readiness',members=['lee'],leaders=['lee'],reason='Fictional handoff'))[0],200)
        self.post('profile',dict(actor='sam'));self.assertEqual(self.post('domain-select',dict(domain='support'))[0],403);self.assertNotIn(work['id'],[r['ref']['id'] for r in self.get_state()['records']])
        self.conn.request('GET','/domain-knowledge.js');response=self.conn.getresponse();self.assertEqual(response.status,200);self.assertIn(b'Assigned project users',response.read())

from brief_fixture import complete_design_brief
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench.domain import EDITABLE
from workbench.model_provider import UnconfiguredModel, ModelUnavailable
from workbench.workspace import Workspace
from interpretation_fixture import FictionalInterpretationModel, populate, seed_project, PROJECT_ID
from workbench.projects import Projects


class Model(FictionalInterpretationModel):
    calls=0;during=None;bad=None
    def generate(self,**kw):
        self.calls+=1;self.context=deepcopy(kw['context'])
        out=super().generate(**kw)
        if self.during:self.during()
        if self.bad:self.bad(out['output'])
        return out


class InterpretationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3';self.store=Store(self.path)
        self.owner=Workspace(self.store,'alex');self.owner.setup(dict(title='Fictional crossing',intent='Preserve usable feedback.',boundary='Non-safety only.'))
        self.req=self.owner.create_requirement(dict(title='Photo timing',text='Assumption: every initial report needs a photo before submission.',rationale='An untested assumption.',conditions='Non-safety',drawer='Experience',acceptance_criteria='Capture criteria need research.'))
        self.ref=self.store.latest(self.req['id'],{SCOPE})['ref'];self.measure=self.store.put('M','success-measure',SCOPE,dict(definition='Baseline and target unknown.'))
        self.packet=dict(id='PKT-INCOMING',revision=1);self.store.packet('PKT-INCOMING',1,'Fictional business packet',[self.ref,self.measure],{SCOPE},{SCOPE})
        self.model=Model();self.sam=Workspace(self.store,'sam',self.model);self.lee=Workspace(self.store,'lee',self.model)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def assess(self,w=None):
        w=w or self.sam;out=w.command('domain-interpretation-assess',dict(packet=self.packet,consent=True));return self.store.latest(out['interpretationResult'],w.scopes)
    def bridge(self,r,index=0,**kw):
        data=dict(expected=asdict(r['ref']),index=index,route='requirement',target=asdict(self.ref),owner='sam',boards=['business-research'],confirm=True);data.update(kw)
        return self.sam.command('domain-interpretation-bridge',data)
    def configure(self,w):
        p=w.domains.profile();cfg={k:deepcopy(p['config'][k]) for k in EDITABLE};cfg['vocabulary']+=' Changed test definition.'
        return w.command('domain-configure',dict(domain=w.domains.key,expected=p['ref'],config=cfg,reason='Test targeted invalidation.'))
    def test_saved_basis_grounding_immutable_packet_and_idempotent_assessment(self):
        before=self.store.resolve_packet('PKT-INCOMING',1,{SCOPE});r=self.assess();b=r['body']
        self.assertEqual(b['mode'],'simulated');self.assertEqual(b['packet'],{**self.packet,'purpose':'Fictional business packet'})
        self.assertEqual(self.model.calls,1);self.assertEqual(self.assess()['ref'],r['ref']);self.assertEqual(self.model.calls,1)
        for app in b['output']['applications']:
            for e in app['evidence']:self.assertIn(e['quote'],self.store.read(Ref(**e['ref']),{SCOPE})['body'][e['field']])
        self.assertEqual(before,self.store.resolve_packet('PKT-INCOMING',1,{SCOPE}));self.assertEqual(self.store.latest(self.ref.id,{SCOPE})['ref'],self.ref)
        self.assertFalse(self.sam.bridge.issues());self.assertTrue(self.sam.domain_interpretation.freshness(r))
    def test_simulated_fixture_cannot_satisfy_a_live_assessment_request(self):
        simulated=self.assess()
        with patch('workbench.domain_interpretation.execution_mode',return_value='live'):
            live=self.assess()
        self.assertEqual(self.model.calls,2);self.assertNotEqual(live['ref'],simulated['ref']);self.assertEqual(live['body']['mode'],'live')
    def test_consent_and_context_budgets_are_enforced(self):
        with self.assertRaises(ValueError):self.sam.command('domain-interpretation-assess',dict(packet=self.packet))
        refs=[self.store.put('S-'+str(i),'source',SCOPE,dict(text='Fictional source '+str(i))) for i in range(61)]
        self.store.packet('BIG',1,'Too broad',refs,{SCOPE},{SCOPE})
        with self.assertRaises(ValueError):self.sam.domain_interpretation.context(dict(id='BIG',revision=1))
        self.assertEqual(self.model.calls,0)
    def test_private_roles_and_packets_never_leak(self):
        r=self.assess();self.assertFalse(self.lee.domain_interpretation.state()['reports']);self.assertFalse(Workspace(self.store,'priya').domain_interpretation.state()['reports'])
        with self.assertRaises(PermissionError):self.lee.domain_interpretation.owned(asdict(r['ref']))
        private=self.store.put('SECRET','source','domain:research',dict(text='Private source'))
        self.store.packet('PRIVATE',1,'Restricted',[private],{'domain:research'},{'domain:research'})
        with self.assertRaises(PermissionError):self.sam.command('domain-interpretation-assess',dict(packet=dict(id='PRIVATE',revision=1),consent=True))
        with self.assertRaises(PermissionError):Workspace(self.store,'alex',self.model).domain_interpretation.context(self.packet)
        self.assertNotIn('SECRET',str(self.model.context));self.assertNotIn('PRIVATE',[p['id'] for p in self.sam.domain_interpretation.state()['packets']])
    def test_profile_change_invalidates_only_affected_domain(self):
        r=self.assess();self.configure(self.lee);self.assertTrue(self.sam.domain_interpretation.freshness(r))
        self.configure(self.sam);self.assertFalse(self.sam.domain_interpretation.freshness(r))
        with self.assertRaises(StaleBasis):self.bridge(r)
        new=self.assess();self.assertNotEqual(new['ref'].id,r['ref'].id);self.assertEqual(new['body']['profile']['ref']['revision'],1)
    def test_new_source_and_packet_versions_require_explicit_reassessment(self):
        r=self.assess();original=self.store.read(self.ref,{SCOPE})
        newer=self.store.put(self.ref.id,'requirement',SCOPE,{**original['body'],'text':'Assumption: every initial report needs a photo; newly challenged.'},1)
        self.assertFalse(self.sam.domain_interpretation.freshness(r));self.assertEqual(self.store.read(self.ref,{SCOPE}),original)
        with self.assertRaises(StaleBasis):self.bridge(r)
        new=self.assess();self.assertIn(dict(selected=asdict(self.ref),current=asdict(newer)),new['body']['observed'])
        self.store.packet('PKT-INCOMING',2,'Newly selected input',[newer,self.measure],{SCOPE},{SCOPE})
        self.assertFalse(self.sam.domain_interpretation.freshness(new))
    def test_instruction_change_invalidates_cached_assessment(self):
        import workbench.domain_interpretation as implementation
        r=self.assess()
        with patch.object(implementation,'INSTRUCTIONS',implementation.INSTRUCTIONS+' New evidence boundary.'):
            self.assertFalse(self.sam.domain_interpretation.freshness(r));new=self.assess()
        self.assertNotEqual(r['ref'].id,new['ref'].id);self.assertEqual(self.model.calls,2)
    def test_unrelated_records_do_not_rerun_or_change_assessment(self):
        r=self.assess();self.store.put('UNRELATED','source',SCOPE,dict(text='A photo of the orange office wall.'))
        self.assertTrue(self.sam.domain_interpretation.freshness(r));self.assess();self.assertEqual(self.model.calls,1);self.assertNotIn('UNRELATED',str(self.model.context))
    def test_invalid_knowledge_and_citations_rejected_without_canned_fallback(self):
        for bad in [lambda out:out['applications'][0].update(knowledge_id='invented-policy'),lambda out:out['findings'][0].update(evidence_ids=['FAKE']),lambda out:out['findings'][0].update(requirement_ids=['UNKNOWN'])]:
            self.model.bad=bad
            with self.assertRaises(ModelUnavailable):self.assess()
        self.assertFalse(self.sam.domain_interpretation.reports());self.assertEqual(self.sam.latest_records('agent-execution')[0]['body']['status'],'failed')
        with self.assertRaises(ModelUnavailable):Workspace(self.store,'sam',UnconfiguredModel()).command('domain-interpretation-assess',dict(packet=self.packet,consent=True))
    def test_changed_inputs_during_generation_discard_result(self):
        self.model.during=lambda:self.configure(self.sam)
        with self.assertRaises(StaleBasis):self.assess()
        self.assertFalse(self.sam.domain_interpretation.reports());self.assertEqual(self.sam.latest_records('agent-execution')[0]['body']['status'],'stale')
    def test_bridge_requires_confirmation_releases_selected_finding_and_preserves_authority(self):
        r=self.assess()
        with self.assertRaises(ValueError):self.bridge(r,confirm=False)
        self.assertFalse(self.sam.bridge.issues())
        out=self.bridge(r);issue=self.store.latest(out['bridgeIssue'],{SCOPE});self.assertEqual(issue['body']['decision_owner'],'alex')
        self.assertEqual(issue['body']['status'],'open');self.assertIsNone(issue['body']['resolution'])
        release=Workspace(self.store,'alex').latest_records('domain-interpretation-release')[0]
        self.assertEqual(len(release['body']['output']['findings']),1);self.assertNotIn('Runtime value has no baseline',json.dumps(release['body']))
        self.assertEqual(self.store.latest(self.ref.id,{SCOPE})['ref'],self.ref)
        current=self.sam.domain_interpretation.reports()[0];again=self.bridge(current);self.assertEqual(out['bridgeIssue'],again['bridgeIssue']);self.assertEqual(len(self.sam.bridge.issues()),1)
        self.assertTrue(any(p['id']=='PKT-'+release['ref'].id for p in self.store.packet_manifests({SCOPE})))
        self.assertFalse(Workspace(self.store,'alex').domain_interpretation.state()['reports'])
    def test_reopen_store_retains_private_assessment_and_shared_receipt(self):
        r=self.assess();out=self.bridge(r);self.store.close();self.store=Store(self.path);self.sam=Workspace(self.store,'sam',self.model)
        self.assertEqual(self.sam.domain_interpretation.state()['reports'][0]['body']['bridge_links']['0']['issue']['id'],out['bridgeIssue'])
        self.assertEqual(len(self.sam.latest_records('domain-interpretation')),1)


class CrossingTests(unittest.TestCase):
    def test_fictional_crossing_preserves_pillars_and_all_versions(self):
        with tempfile.TemporaryDirectory() as temp:
            store=Store(Path(temp)/'demo.db')
            try:
                result=populate(store);sam=Workspace(store,'sam');lee=Workspace(store,'lee');alex=Workspace(store,'alex')
                sr=sam.domain_interpretation.state()['reports'][0];dr=lee.domain_interpretation.state()['reports'][0]
                self.assertEqual(sr['body']['domain'],'research');self.assertEqual(dr['body']['domain'],'design');self.assertNotEqual(sr['body']['profile']['fingerprint'],dr['body']['profile']['fingerprint'])
                self.assertTrue(sr['current']);self.assertTrue(dr['current']);self.assertEqual(dr['body']['mode'],'simulated')
                research=next(r for r in lee.latest_records('contribution') if r['body']['domain_key']=='research')
                self.assertIn('No population estimate',research['body']['limitation']);self.assertIn('three of six invented',research['body']['observation'])
                self.assertEqual(len(lee.latest_records('requirement')),2);self.assertTrue(all(r['body']['status']=='proposed' for r in lee.latest_records('requirement')))
                self.assertFalse(alex.loop.history());issue=alex.bridge.issues()[0];self.assertEqual(issue['body']['decision_owner'],'alex');self.assertEqual(issue['body']['status'],'open')
                ctx=lee.domains.context(asdict(lee.domain_chat.draft(lee.domain_chat.threads()[0])['ref']))
                self.assertEqual(ctx['packet_interpretations'][0]['ref'],asdict(dr['ref']));self.assertIn('runtime KPI',dr['body']['output']['applications'][1]['application'])
                packet=store.resolve_packet(result['research_packet']['id'],1,{SCOPE});self.assertTrue(any(r['kind']=='domain-interpretation-release' for r in packet['records']))
                private=sam.domain_interpretation.reports()[0]['ref'];self.assertNotIn(private,[r['ref'] for r in packet['records']])
                # Sharing is separately authorized; stale private advice cannot silently become published.
                draft=lee.domain_chat.draft(lee.domain_chat.threads()[0]);complete_design_brief(lee,draft);prepared=lee.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='bridge'))
                h=store.latest(prepared['domainHandoff'],lee.scopes)
                with self.assertRaises(PermissionError):lee.command('domain-publish',dict(expected=asdict(draft['ref']),preflight=asdict(h['ref']),confirm=True))
                lee.command('domain-publish',dict(expected=asdict(draft['ref']),preflight=asdict(h['ref']),confirm=True,release_interpretations=True))
                self.assertEqual(store.latest(result['requirements'][0]['id'],{SCOPE})['ref'].revision,1)
            finally:store.close()
    def test_seed_isolated_idempotent_preserves_existing_project(self):
        with tempfile.TemporaryDirectory() as temp:
            anchor=Path(temp)/'anchor.db';s=Store(anchor);Workspace(s,'priya').command('intake-start',dict(title='Existing project'));before=list(s.db.iterdump());s.close()
            result=seed_project(anchor);again=seed_project(anchor);self.assertEqual(result,again)
            s=Store(anchor);self.assertEqual(before,list(s.db.iterdump()));s.close()
            with Projects(anchor).locked(PROJECT_ID) as p:self.assertNotEqual(p['path'],str(anchor))


class InterpretationHttpTests(unittest.TestCase):
    def setUp(self):
        import test_web
        test_web.WebTests.setUp(self);self.server.model=Model();self.post=test_web.WebTests.post.__get__(self)
        self.post('profile',dict(actor='alex'));self.post('setup',dict(title='Fictional HTTP',intent='Capture feedback.',boundary='Non-safety'))
        _,out=self.post('requirement',dict(title='Photo',text='Assumption: every initial report needs a photo.',rationale='Unknown',conditions='Non-safety',drawer='Experience',acceptance_criteria='Investigate'))
        with self.server.projects.locked('original') as project:
            store=Store(project['path']);measure=store.put('M','success-measure',SCOPE,dict(definition='Baseline and target unknown.'));req=store.latest(out['id'],{SCOPE})['ref'];store.packet('PKT-HTTP',1,'Fictional HTTP packet',[req,measure],{SCOPE},{SCOPE});store.close()
    def tearDown(self):
        import test_web
        test_web.WebTests.tearDown(self)
    def test_real_routes_roles_and_asset(self):
        status,_=self.post('domain-interpretation-assess',dict(packet=dict(id='PKT-HTTP',revision=1),consent=True));self.assertEqual(status,403)
        self.post('profile',dict(actor='sam'));status,out=self.post('domain-interpretation-assess',dict(packet=dict(id='PKT-HTTP',revision=1),consent=True));self.assertEqual(status,200,out);self.assertIn('interpretationResult',out)
        self.conn.request('GET','/domain-interpretation.js');resp=self.conn.getresponse();self.assertEqual(resp.status,200);self.assertIn(b'Domain interpretation',resp.read())
        self.conn.request('GET','/api/state',headers={'Cookie':self.cookie});resp=self.conn.getresponse();state=json.loads(resp.read());self.assertEqual(len(state['domain_interpretation']['reports']),1)
        self.post('profile',dict(actor='lee'));self.conn.request('GET','/api/state',headers={'Cookie':self.cookie});resp=self.conn.getresponse();self.assertFalse(json.loads(resp.read())['domain_interpretation']['reports'])

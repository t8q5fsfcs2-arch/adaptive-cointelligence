from copy import deepcopy
from dataclasses import asdict
import base64
from unittest import TestCase

from workbench.workspace import Workspace
from workbench.core import StaleBasis
from workbench.decisions import SCOPE
from workbench.validation import reference
import test_prototype_workflow as proto

class DeveloperBriefTests(TestCase):
    setUp=proto.PrototypeTests.setUp;tearDown=proto.PrototypeTests.tearDown
    seed=proto.PrototypeTests.seed;generate_brief=proto.PrototypeTests.generate_brief;payload=proto.PrototypeTests.payload;start=proto.PrototypeTests.start;data=proto.PrototypeTests.data
    def current_thread(self):return self.store.latest(self.t['ref'].id,self.design.scopes)
    def open(self):
        self.design.command('developer-brief-open',dict(conversation=asdict(self.current_thread()['ref'])))
        return self.design.developer_briefs.latest(self.current_thread())
    def save(self,r,text='A fictional developer brief. Human testing remains outstanding.',**extra):
        data=dict(conversation=asdict(self.current_thread()['ref']),expected=asdict(r['ref']),title=r['body']['title'],text=text,source_refs=r['body']['source_refs'],prototype=r['body']['prototype']['ref'] if r['body'].get('prototype') else None)
        out=self.design.command('developer-brief-save',{**data,**extra});return self.store.read(reference(out['ref']),self.design.scopes)
    def prepare(self,r):return self.design.command('developer-brief-prepare',dict(conversation=asdict(self.current_thread()['ref']),expected=asdict(r['ref'])))
    def test_only_configured_brief_outputs_can_be_created_or_edited_and_history_survives_retirement(self):
        from workbench.domain import EDITABLE
        self.start();r=self.open();profile=self.design.domains.profile()
        config={key:deepcopy(profile['config'][key]) for key in EDITABLE}
        config['deliverable_types']=['Task flow and interaction specification']
        self.design.command('domain-configure',dict(domain='design',expected=profile['ref'],config=config,reason='Retire brief outputs for this synthetic configuration test.'))
        before=list(self.store.db.execute('SELECT * FROM records ORDER BY id,revision'))
        with self.assertRaisesRegex(PermissionError,'not an enabled output'):
            self.design.command('developer-brief-open',dict(conversation=asdict(self.current_thread()['ref'])))
        with self.assertRaisesRegex(PermissionError,'not an enabled output'):self.save(r)
        self.assertFalse(self.design.developer_briefs.state()['can_author'])
        historical=self.design.command('developer-brief-read',dict(ref=asdict(r['ref'])))
        self.assertEqual(historical['body'],r['body'])
        self.assertEqual(before,list(self.store.db.execute('SELECT * FROM records ORDER BY id,revision')))
        # A private antecedent work plan is not a configured output deliverable.
        self.design.command('domain-brief-create',{});self.assertTrue(self.design.domain_brief.state()[0]['body']['include_domain_brief'])
    def publish(self,prepared,**extra):
        h=self.store.latest(prepared['domainHandoff'],self.design.scopes)
        return self.design.command('domain-publish',dict(expected=h['body']['draft'],preflight=asdict(h['ref']),confirm=True,**extra))
    def test_named_parking_is_private_idempotent_and_preserves_current_submission(self):
        self.start();t=self.current_thread();draft=self.design.domain_chat.draft(t)
        sub=self.design.command('domain-submission-save',dict(conversation=asdict(t['ref']),expected=asdict(draft['ref']),submission=None,text='The existing prototype submission.',source_refs=[],implication_refs=[],primary_source=None,review_mode='text'))
        r=self.open();self.assertEqual(r['body']['text'],'');self.assertEqual(self.open()['ref'],r['ref']);self.save(r)
        self.assertEqual(self.design.submissions.latest(t)['ref'],reference(sub['ref']));self.assertEqual(self.sam.developer_briefs.state()['private'],[]);self.assertEqual(self.sam.developer_briefs.state()['shared'],[])
        with self.assertRaises(PermissionError):self.sam.command('developer-brief-read',dict(ref=asdict(r['ref'])))
        with self.assertRaises(PermissionError):self.sam.command('developer-brief-open',dict(conversation=asdict(t['ref'])))
    def test_edits_keep_exact_history_and_reject_stale_saves(self):
        self.start();r=self.open();saved=self.save(r,'First wording.');latest=self.save(saved,'Second wording.')
        old=self.design.command('developer-brief-read',dict(ref=asdict(saved['ref'])));self.assertEqual(old['body']['text'],'First wording.');self.assertEqual(self.store.read(latest['ref'],self.design.scopes)['body']['text'],'Second wording.')
        with self.assertRaises(StaleBasis):self.save(saved,'Competing wording.')
        self.assertGreater(len(self.design.developer_briefs.state()['private'][0]['history']),0)
    def test_save_does_not_call_model_or_change_requirement_authority(self):
        self.start();r=self.open()
        with self.assertRaisesRegex(ValueError,'Add brief content'):self.prepare(r)
        before=self.store.latest(self.req['ref'].id,self.design.scopes);calls=len(self.m.calls);self.save(r)
        self.assertEqual(len(self.m.calls),calls);self.assertEqual(self.store.latest(self.req['ref'].id,self.design.scopes),before);self.assertEqual(self.design.delivery.state()['drafts'],[])
    def test_unselected_files_and_private_chat_do_not_cross_publication(self):
        self.start();self.design.command('domain-chat-attach',{**self.data(),'filename':'test-results.txt','content':base64.b64encode(b'Fictional test notes; not actual human research.').decode()})
        selected=self.design.domain_chat.draft(self.current_thread())['body']['source_refs'][0]
        self.design.command('domain-chat-attach',{**self.data(),'filename':'private.txt','content':base64.b64encode(b'NEVER SHARE THIS PRIVATE NOTE').decode()})
        self.design.domain_chat.turn(self.current_thread(),'user','NEVER SHARE THIS CONVERSATION')
        r=self.save(self.open(),source_refs=[selected]);prepared=self.prepare(r)
        with self.assertRaises(PermissionError):self.publish(prepared)
        out=self.publish(prepared,release_sources=True);shared=self.sam.developer_briefs.state()['shared'][0]
        self.assertEqual(shared['body']['text'],r['body']['text']);self.assertEqual(shared['body']['status'],'shared-for-review');self.assertNotIn('NEVER SHARE',str(shared));self.assertNotIn('conversation',shared['body']);self.assertNotIn('draft_id',shared['body'])
        self.assertTrue(shared['body']['source_refs'][0]['id'].startswith('RELEASE-'));self.assertEqual(shared['packet'],out['packet'])
        packet=self.store.resolve_packet(out['packet']['id'],out['packet']['revision'],{SCOPE})
        self.assertTrue(any(x['kind']=='project-developer-brief' for x in packet['records']));self.assertNotIn('NEVER SHARE',str(packet))
        self.assertTrue(all(x['scope']==SCOPE for x in packet['records']));self.assertEqual(self.design.developer_briefs.state()['private'][0]['shared'],asdict(shared['ref']))
    def test_editing_prepared_brief_invalidates_preview_and_published_snapshots_do_not_change(self):
        self.start();r=self.save(self.open());prepared=self.prepare(r);changed=self.save(r,'An amended implementation draft.')
        with self.assertRaises(StaleBasis):self.publish(prepared)
        self.publish(self.prepare(changed));published=self.sam.developer_briefs.state()['shared'][0];again=self.save(changed,'A private later revision.')
        self.assertEqual(self.sam.developer_briefs.state()['shared'][0]['body']['text'],'An amended implementation draft.');self.assertNotEqual(published['body']['source_version'],asdict(again['ref']))
        self.publish(self.prepare(again));self.assertEqual(self.sam.developer_briefs.state()['shared'][0]['ref'].revision,2)
        self.assertEqual(self.store.read(published['ref'],{SCOPE})['body']['text'],'An amended implementation draft.')
    def test_current_context_and_complete_design_brief_remain_preflight_guards(self):
        self.start();r=self.save(self.open());req=self.store.latest(self.req['ref'].id,self.design.scopes);self.store.put(req['ref'].id,req['kind'],req['scope'],{**req['body'],'text':'A changed agreed behavior.'},req['ref'].revision)
        self.assertTrue(self.design.developer_briefs.state()['private'][0]['changed'])
        with self.assertRaises(StaleBasis):self.prepare(r)
        # Saving prose does not silently adopt a changed requirement.
        edited=self.save(r,'More detail, with the original basis retained.');self.assertEqual(edited['body']['requirement_refs'],r['body']['requirement_refs'])
        self.tearDown();self.setUp();self.seed();self.t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation']);r=self.save(self.open())
        with self.assertRaisesRegex(ValueError,'Complete the Working brief'):self.prepare(r)
    def test_evidence_selection_and_discussion_application_validate_exact_ownership(self):
        self.start();r=self.open()
        with self.assertRaises(ValueError):self.save(r,source_refs=[dict(id='PRIVATE-STUDY',revision=1)])
        turn=self.design.domain_chat.turn(self.current_thread(),'assistant','A proposed implementation draft, with evidence gaps.')
        saved=self.save(r,'A proposed implementation draft, with evidence gaps.',discussion=asdict(turn));self.assertEqual(saved['body']['drafted_from'],asdict(turn))
        with self.assertRaises(ValueError):self.save(saved,'A forged passage.',discussion=asdict(turn))
    def test_long_brief_is_not_clipped_in_shared_snapshot_or_packet(self):
        self.start();text='Fictional implementation detail. '*900;r=self.save(self.open(),text);out=self.publish(self.prepare(r));shared=self.sam.developer_briefs.state()['shared'][0];self.assertEqual(shared['body']['text'],text)
        con=self.store.latest(out['id'],{SCOPE});self.assertEqual(''.join(e['text'] for e in con['body']['working_report']['entries']),text)

class DeveloperBriefHTTPTests(TestCase):
    def setUp(self):
        from test_web import WebTests
        WebTests.setUp(self);self.post=WebTests.post.__get__(self)
    def tearDown(self):
        from test_web import WebTests
        WebTests.tearDown(self)
    def test_new_asset_and_command_are_exposed_over_actual_http(self):
        self.conn.request('GET','/developer-brief.js');response=self.conn.getresponse();self.assertEqual(response.status,200);self.assertIn(b'Developer brief',response.read())
        self.post('profile',dict(actor='lee'));status,thread=self.post('domain-chat-start',{});self.assertEqual(status,200)
        status,out=self.post('developer-brief-open',dict(conversation=thread['conversation']));self.assertEqual(status,200,out)

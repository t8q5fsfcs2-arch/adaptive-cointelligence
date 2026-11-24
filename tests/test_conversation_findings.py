"""One conversational call coauthors a private document; publication is still human."""
from copy import deepcopy
from dataclasses import asdict
import unittest
import test_domain_chat as fixture
from brief_fixture import complete_design_brief
from workbench.core import StaleBasis, Store
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench.conversation_findings import document

class Coauthor(fixture.ChatModel):
    def __init__(self):super().__init__();self.document='Finding\nA bounded draft; prevalence is unknown.'
    def generate(self,**kw):
        result=super().generate(**kw);
        if 'findings_document' in kw['schema']['properties']:result['output']['findings_document']=self.document
        return result
    def generate_visual(self,**kw):
        result=super().generate_visual(**kw);
        if 'findings_document' in kw['schema']['properties']:result['output']['findings_document']=self.document
        return result

class ConversationFindingsTests(unittest.TestCase):
    setUp=fixture.ChatTests.setUp
    tearDown=fixture.ChatTests.tearDown
    start=fixture.ChatTests.start
    draft=fixture.ChatTests.draft
    current=fixture.ChatTests.current
    attach=fixture.ChatTests.attach
    def send(self,w,t,**kw):return fixture.ChatTests.send(self,w,t,purpose='prepare-sharing',**kw)
    def coauthor(self,w=None,pdf=False):
        self.model=Coauthor();w=Workspace(self.store,(w or self.sam).actor,self.model);self.sam=w if w.actor=='sam' else self.sam;self.lee=w if w.actor=='lee' else self.lee
        return w,self.attach(w,self.start(w),pdf=pdf)
    def save(self,w,t,value):return w.command('domain-findings-save',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(self.draft(w,t)['ref']),document=value))
    def test_one_reply_aggregates_findings_and_exact_evidence_without_a_second_call(self):
        w,t=self.coauthor();before=self.draft(w,t);result=self.send(w,t);after=self.draft(w,t)
        self.assertTrue(result['findings_updated']);self.assertEqual(len(self.model.calls),1);self.assertEqual(document(after['body']),self.model.document)
        report=after['body']['working_report'];self.assertEqual(report['format'],'document');self.assertEqual(report['conversation_update']['before'],asdict(before['ref']))
        self.assertEqual(report['entries'][0]['citations'][0]['ref'],before['body']['source_refs'][0]);self.assertEqual(self.store.read(before['ref'],w.scopes),before)
        self.assertIn('findings_document',self.model.calls[0]['schema']['properties']);self.assertIn('current saved',self.model.calls[0]['instructions'])
    def test_human_edits_enter_next_exchange_and_unchanged_or_empty_reply_keeps_them(self):
        w,t=self.coauthor();self.send(w,t);wording='Author-refined findings\nPreserve this important limitation.';self.save(w,t,wording)
        for i,value in enumerate([wording,'']):
            self.model.document=value;out=self.send(w,t,request_id='synthetic-next-'+str(i))
            self.assertFalse(out['findings_updated']);self.assertEqual(document(self.draft(w,t)['body']),wording)
            self.assertEqual(self.model.calls[-1]['context']['conversation_findings']['document'],wording)
    def test_undo_restores_previous_human_findings_without_touching_publication(self):
        w,t=self.coauthor();self.save(w,t,'Earlier authored findings');before=self.draft(w,t);self.send(w,t);after=self.draft(w,t)
        out=w.command('domain-findings-undo',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(after['ref'])))
        self.assertEqual(document(self.draft(w,t)['body']),'Earlier authored findings');self.assertGreater(out['ref']['revision'],after['ref'].revision);self.assertEqual(len(self.model.calls),1)
        self.assertEqual(self.store.read(before['ref'],w.scopes),before);self.assertEqual(self.store.read(after['ref'],w.scopes),after)
        with self.assertRaises(StaleBasis):w.command('domain-findings-undo',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(self.draft(w,t)['ref'])))
    def test_manual_edit_removes_undo_offer_and_stale_saves_are_atomic(self):
        w,t=self.coauthor();self.send(w,t);old=self.draft(w,t);self.save(w,t,'Human revision');count=self.store.db.execute('select count(*) from records').fetchone()[0]
        self.assertNotIn('conversation_update',self.draft(w,t)['body']['working_report'])
        with self.assertRaises(StaleBasis):w.command('domain-findings-save',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(old['ref']),document='Stale'))
        with self.assertRaises(StaleBasis):w.command('domain-findings-undo',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(self.draft(w,t)['ref'])))
        self.assertEqual(self.store.db.execute('select count(*) from records').fetchone()[0],count)
    def test_one_share_action_prepares_exact_packet_then_author_explicitly_publishes(self):
        w,t=self.coauthor();self.send(w,t);d=self.draft(w,t)
        before_shared=deepcopy(w.latest_records('contribution'))
        p=w.command('domain-findings-prepare',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(d['ref'])))
        self.assertEqual(w.latest_records('contribution'),before_shared)
        h=self.store.latest(p['domainHandoff'],w.scopes);self.assertEqual(h['body']['draft'],asdict(d['ref']))
        out=w.command('domain-publish',dict(expected=asdict(d['ref']),preflight=asdict(h['ref']),confirm=True,release_sources=True))
        shared=self.store.latest(out['id'],{SCOPE});self.assertEqual(document(shared['body']),self.model.document);self.assertNotIn('conversation_update',shared['body']['working_report'])
        self.assertTrue(shared['body']['working_report']['entries'][0]['citations'][0]['ref']['id'].startswith('RELEASE-'))
        packet=self.store.resolve_packet(out['packet']['id'],out['packet']['revision'],{SCOPE});self.assertFalse(any(r['kind'] in ('domain-conversation','domain-chat-turn','domain-chat-review') for r in packet['records']))
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req);self.assertEqual(len(self.model.calls),1)
    def test_design_uses_same_document_contract_and_keeps_brief_gate(self):
        w,t=self.coauthor(self.lee,pdf=True);self.send(w,t);d=self.draft(w,t)
        self.assertEqual(document(d['body']),self.model.document);self.assertTrue(d['body']['working_report']['entries'][0]['citations'][0]['page'])
        with self.assertRaises(ValueError):w.command('domain-findings-prepare',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(d['ref'])))
        complete_design_brief(w,d);w.command('domain-findings-prepare',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(d['ref'])))
        self.assertEqual(len(self.model.calls),1)
    def test_other_domain_cannot_edit_or_undo_private_findings(self):
        w,t=self.coauthor();self.send(w,t)
        for action in ('domain-findings-save','domain-findings-undo','domain-findings-prepare'):
            with self.assertRaises(PermissionError):self.lee.command(action,dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(self.draft(w,t)['ref']),document='Forbidden'))
        self.assertFalse(self.lee.domain_chat.state()['working_history'])
    def test_concurrent_edit_or_invalid_document_does_not_replace_saved_wording(self):
        w,t=self.coauthor();self.save(w,t,'Keep the author wording')
        self.model.during=lambda:self.save_during(w,t)
        out=self.send(w,t);self.assertIn('chat_error',out);self.assertEqual(document(self.draft(w,t)['body']),'Concurrent author wording')
        self.model.during=None;self.model.document=123
        out=self.send(w,t,request_id='synthetic-invalid-doc');self.assertIn('chat_error',out);self.assertEqual(document(self.draft(w,t)['body']),'Concurrent author wording')
    def save_during(self,w,t):
        # A second writer advances the exact draft while the original request is pending.
        d=self.draft(w,t);w.working_report.persist(d,w.working_report.document_report(d,'Concurrent author wording'))
    def test_reopen_retains_document_and_older_adapters_do_not_fabricate_findings(self):
        w,t=self.coauthor();self.send(w,t);saved=document(self.draft(w,t)['body']);reopened=Store(self.path)
        try:self.assertEqual(document(Workspace(reopened,'sam').domain_chat.draft(t)['body']),saved)
        finally:reopened.close()
        self.model=fixture.ChatModel();w=Workspace(self.store,'sam',self.model);out=self.send(w,t,request_id='synthetic-old-adapter')
        self.assertFalse(out['findings_updated']);self.assertEqual(document(self.draft(w,t)['body']),saved)

    def test_default_exploration_and_review_leave_authored_sharing_draft_unchanged(self):
        w,t=self.coauthor();self.save(w,t,'Author-selected learning. Preserve its limits.')
        before=self.draft(w,t);published=deepcopy(w.latest_records('contribution'))
        for purpose in ('explore','review'):
            out=fixture.ChatTests.send(self,w,t,purpose=purpose,request_id='purpose-'+purpose)
            self.assertIn('chatReport',out);self.assertFalse(out['findings_updated'])
            self.assertEqual(self.draft(w,t),before)
            call=self.model.calls[-1]
            self.assertNotIn('findings_document',call['schema']['properties'])
            self.assertEqual(call['context']['conversation_findings']['document'],'Author-selected learning. Preserve its limits.')
            self.assertIn('do not bend evidence'.lower(),call['instructions'].lower())
            self.assertTrue(w.domain_chat.state()['reports'][0]['current'])
        self.assertEqual(w.latest_records('contribution'),published)

    def test_invalid_purpose_is_rejected_before_recording_a_request(self):
        w,t=self.coauthor();before=self.draft(w,t)
        with self.assertRaises(ValueError):fixture.ChatTests.send(self,w,t,purpose='publish')
        self.assertEqual(self.model.calls,[]);self.assertEqual(self.draft(w,t),before)

    def test_older_review_basis_remains_reconstructable_without_task_field(self):
        w,t=self.coauthor();ctx,_=w.domain_chat.basis(t,w.domain_chat.plan(t)[0])
        self.assertNotIn('workbench_task',ctx)
        from workbench.conversation_findings import enabled
        self.assertTrue(enabled(ctx))

    def test_conversation_can_explain_in_paragraphs_without_changing_standalone_review_limits(self):
        w,t=self.coauthor();before=self.draft(w,t)
        original=self.model.generate
        def explain(**kw):
            result=original(**kw);result['output']['summary']='Explain the task, evidence and uncertainties. '*28+'\n\nThen consider the implications.'
            return result
        self.model.generate=explain
        out=fixture.ChatTests.send(self,w,t,request_id='synthetic-explanation',purpose='explore')
        self.assertIn('chatReport',out);self.assertEqual(self.draft(w,t),before)
        self.assertEqual(self.model.calls[-1]['schema']['properties']['summary']['maxLength'],8000)
        from workbench.domain import schema
        self.assertEqual(schema({'requirements':[]})['properties']['summary']['maxLength'],700)

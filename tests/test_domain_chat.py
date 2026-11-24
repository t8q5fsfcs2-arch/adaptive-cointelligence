import base64
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store,Ref,StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench.model_provider import ModelUnavailable
from pdf_fixture import prototype_pdf

class ChatModel:
    def __init__(self):self.calls=[];self.during=None;self.fail=False
    def status(self):return dict(configured=True,provider='TEST DOUBLE',model='synthetic')
    def generate(self,**kw):
        self.calls.append(deepcopy(kw));c=kw['context']
        if self.during:self.during()
        if self.fail:raise ModelUnavailable('Synthetic provider failure. No substitute response was used.')
        source=c['sources'][0] if c['sources'] else None
        return dict(output=dict(summary='The evidence needs a bounded interpretation.',strengths=[],suggestions=[dict(kind='evidence',direction='evidence',issue='Check the scope of the observation.',question='Which reporting task was observed?',basis=source['ref']['id'] if source else 'observation',quote=source['body']['text'][:60] if source else c['deliverable']['observation'][:60],edit=dict(field='interpretation',text='The supplied observation suggests a reporting barrier; prevalence is unknown.'),requirement_ids=[r['ref']['id'] for r in c['requirements']])]),model='synthetic',usage=dict(input_tokens=20,output_tokens=30))
    def generate_visual(self,**kw):
        self.calls.append(deepcopy(kw));c=kw['context'];r=c['requirements'][0]
        return dict(output=dict(summary='Review the photo gate against staged evidence.',reviewed_pages=[p['page'] for p in c['pages']],limitations='Static screens cannot demonstrate interaction behavior.',findings=[dict(page=c['pages'][-1]['page'],area='Photo gate',assessment='tension',observation='Photo required before reporting.',rationale='This could prevent initial capture.',recommendation='Permit initial capture; test evidence follow-up.',uncertainty='Confirm the intended screen state.',context_links=[dict(ref=deepcopy(r['ref']),quote=r['body']['text'])])]),model='synthetic',usage=dict(input_tokens=40,output_tokens=30))

class ChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'chat.db';self.store=Store(self.path);self.model=ChatModel()
        owner=Workspace(self.store,'alex');owner.setup(dict(title='Fictional Clinic',intent='Capture feedback without interrupting maintenance.',boundary='Non-safety feedback only.'))
        result=owner.create_requirement(dict(title='Capture before evidence',text='A technician can submit a report without a photo.',rationale='Avoid abandoned reporting.',conditions='Non-safety only.',drawer='Experience',acceptance_criteria='Submit without a photo; show evidence pending.'))
        self.req=self.store.latest(result['id'],{SCOPE})
        self.research=self.store.put('PUB-RESEARCH','contribution',SCOPE,dict(domain_key='research',domain='Research',title='Fictional task study',observation='Six invented participants abandoned the report at the photo gate.',limitation='Synthetic; not empirical evidence.',requirement_refs=[asdict(self.req['ref'])]))
        self.sam=Workspace(self.store,'sam',self.model);self.lee=Workspace(self.store,'lee',self.model)
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def start(self,w=None):
        w=w or self.sam;out=w.command('domain-chat-start',{});return w.domain_chat.owned(out['conversation'])
    def current(self,w,t):return self.store.latest(t['ref'].id,{w.domains.scope})
    def draft(self,w,t):return w.domain_chat.draft(t)
    def attach(self,w,t,text=None,pdf=False):
        raw=prototype_pdf() if pdf else (text or 'Fictional observation: technicians paused reporting to collect a photo.').encode()
        out=w.command('domain-chat-attach',dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(self.draft(w,t)['ref']),filename='fictional.pdf' if pdf else 'fictional.txt',content=base64.b64encode(raw).decode()))
        return w.domain_chat.owned(out['conversation'])
    def send(self,w,t,request_id='synthetic-request-001',**extra):
        return w.command('domain-chat-send',{**dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(self.draft(w,t)['ref']),consent=True,message='Review the reporting observation.',request_id=request_id),**extra})
    def test_quiet_suggestions_keep_only_a_private_switch_and_dismissals_and_never_call_the_model(self):
        t=self.attach(self.sam,self.start());out=self.send(self.sam,t);report=out['chatReport'];calls=len(self.model.calls)
        state=self.sam.state()['quiet_suggestions'];self.assertEqual((state['enabled'],state['dismissed'],state['ref']),(True,[],None))
        for bad in (dict(items=[]),dict(items=[dict(report=report,index=9)]),dict(items=[dict(report='CREV-000000000000',index=0)]),dict(items=[dict(report=report,index='0')])):
            with self.assertRaises((ValueError,PermissionError)):self.sam.command('suggestions-dismiss',dict(expected=None,**bad))
        with self.assertRaises((ValueError,PermissionError)):self.lee.command('suggestions-dismiss',dict(expected=None,items=[dict(report=report,index=0)]))
        self.sam.command('suggestions-dismiss',dict(expected=None,items=[dict(report=report,index=0)]))
        state=self.sam.state()['quiet_suggestions'];self.assertEqual(state['dismissed'],[dict(report=report,index=0)])
        with self.assertRaises(StaleBasis):self.sam.command('suggestions-toggle',dict(expected=None,enabled=False))
        with self.assertRaises(ValueError):self.sam.command('suggestions-toggle',dict(expected=state['ref'],enabled='no'))
        self.sam.command('suggestions-toggle',dict(expected=state['ref'],enabled=False))
        mine=self.sam.state()['quiet_suggestions'];self.assertFalse(mine['enabled']);self.assertEqual(mine['ref']['revision'],2)
        self.assertEqual(self.lee.state()['quiet_suggestions']['enabled'],True);self.assertEqual(self.lee.state()['quiet_suggestions']['dismissed'],[])
        self.assertIsNone(Workspace(self.store,'priya').state()['quiet_suggestions']);self.assertEqual(len(self.model.calls),calls)
        self.assertEqual(self.store.latest(report,{self.sam.domains.scope})['body']['output']['suggestions'][0]['issue'],'Check the scope of the observation.')
    def test_model_schema_enforces_bounds_and_supplied_requirement_ids(self):
        from workbench.domain import schema
        value=schema(dict(requirements=[dict(ref=asdict(self.req['ref']))]))
        self.assertEqual(value['properties']['summary']['maxLength'],700)
        suggestion=value['properties']['suggestions']['items']['properties']
        self.assertEqual(suggestion['quote']['maxLength'],500)
        self.assertEqual(suggestion['requirement_ids']['items']['enum'],[self.req['ref'].id])

    def test_same_lifecycle_with_defaults_for_research_and_design(self):
        for w in (self.sam,self.lee):
            t=self.start(w);d=self.draft(w,t);self.assertEqual(d['body']['requirement_refs'],[asdict(self.req['ref'])])
            self.assertEqual(len(d['body']['input_refs']),1 if w==self.lee else 0)
            t=self.attach(w,t,pdf=w==self.lee);out=self.send(w,t)
            self.assertIn('chatReport',out);state=w.state()['domain_chat'];self.assertEqual(len(state['reports']),1);self.assertTrue(state['reports'][0]['current'])
            self.assertEqual(state['reports'][0]['body']['mode'],'simulated');self.assertTrue(any(r['body']['role']=='assistant' for r in state['turns']))
            self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
    def test_followup_uses_persisted_history_and_idempotent_request(self):
        t=self.attach(self.sam,self.start());self.send(self.sam,t)
        out=self.send(self.sam,t,request_id='synthetic-followup-002',message='What makes that interpretation uncertain?')
        self.assertIn('chatReport',out);self.assertTrue(self.model.calls[-1]['context']['previous_exchanges'])
        calls=len(self.model.calls);again=self.send(self.sam,t,request_id='synthetic-followup-002')
        self.assertTrue(again['duplicate']);self.assertEqual(len(self.model.calls),calls)
        self.store.close();self.store=Store(self.path);self.sam=Workspace(self.store,'sam',self.model)
        self.assertEqual(len(self.sam.domain_chat.state()['reports']),2)
    def test_text_batching_uses_only_current_passage_and_exact_location(self):
        text='First observation.\n'+('A relevant passage.\n'*1700)
        t=self.attach(self.sam,self.start(),text=text);plan=self.sam.domain_chat.plan(t);self.assertEqual(len(plan),2)
        self.send(self.sam,t,batch=1);ctx=self.model.calls[-1]['context'];self.assertEqual(ctx['sources'][0]['body']['text'],text.strip()[24000:]);self.assertNotIn('First observation.',str(ctx['sources']))
        r=self.sam.domain_chat.state()['reports'][0];self.assertEqual(r['body']['locations'][0]['start'],24000);self.assertTrue(r['current'])
    def test_scope_is_adjustable_current_and_not_an_approval(self):
        t=self.start(self.lee);d=self.draft(self.lee,t)
        out=self.lee.command('domain-chat-context',dict(conversation=asdict(t['ref']),expected=asdict(d['ref']),requirement_ids=[],input_refs=[]))
        t=self.lee.domain_chat.owned(out['conversation']);self.assertEqual(self.draft(self.lee,t)['body']['requirement_refs'],[])
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
    def test_cross_domain_threads_and_private_sources_are_isolated(self):
        t=self.attach(self.sam,self.start());self.send(self.sam,t)
        with self.assertRaises(PermissionError):self.lee.domain_chat.owned(asdict(t['ref']))
        self.assertNotIn(t['ref'].id,str(self.lee.state()['domain_chat']))
        self.assertIsNone(Workspace(self.store,'priya').state()['domain_chat'])
    def test_model_failure_preserves_message_and_file_and_can_retry_explicitly(self):
        t=self.attach(self.sam,self.start());self.model.fail=True;out=self.send(self.sam,t)
        self.assertIn('chat_error',out);state=self.sam.domain_chat.state();self.assertFalse(state['reports']);self.assertTrue(any(x['body']['role']=='user' for x in state['turns']));self.assertTrue(any(x['body']['role']=='error' for x in state['turns']))
        self.assertIsNone(state['threads'][0]['body']['pending']);self.model.fail=False
        self.assertIn('chatReport',self.send(self.sam,t,request_id='synthetic-retry-002'))
    def test_changed_requirement_invalidates_report_and_requires_explicit_refresh(self):
        t=self.attach(self.sam,self.start());self.send(self.sam,t)
        new=self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'Revised required behavior.'},self.req['ref'].revision)
        self.assertFalse(self.sam.domain_chat.state()['reports'][0]['current'])
        with self.assertRaises(StaleBasis):self.send(self.sam,t,request_id='synthetic-stale-002')
        t=self.current(self.sam,t)
        out=self.sam.command('domain-chat-context',dict(conversation=asdict(t['ref']),expected=asdict(self.draft(self.sam,t)['ref']),requirement_ids=[new.id],input_refs=[]))
        self.assertIn('chatReport',self.send(self.sam,self.sam.domain_chat.owned(out['conversation']),request_id='synthetic-refreshed-003'))
    def test_change_during_request_cannot_commit_feedback(self):
        t=self.attach(self.sam,self.start());d=self.draft(self.sam,t)
        self.model.during=lambda:self.store.put(d['ref'].id,'contribution-draft','domain:research',{**d['body'],'interpretation':'Author revision during request'},d['ref'].revision)
        out=self.send(self.sam,t);self.assertIn('chat_error',out);self.assertFalse(self.sam.domain_chat.state()['reports'])
        self.assertEqual(self.sam.latest_records('agent-execution')[0]['body']['status'],'stale')
    def test_reviewed_suggested_edit_creates_new_draft_version(self):
        t=self.attach(self.sam,self.start());out=self.send(self.sam,t);r=self.store.latest(out['chatReport'],self.sam.scopes);before=self.draft(self.sam,t)
        saved=self.sam.command('domain-chat-apply',dict(conversation=asdict(self.current(self.sam,t)['ref']),expected=asdict(before['ref']),report=asdict(r['ref']),index=0,text='Author-refined interpretation; investigate prevalence.',confirm=True))
        after=self.draft(self.sam,t);self.assertEqual(after['ref'].revision,before['ref'].revision+1);self.assertEqual(after['body']['interpretation'],'Author-refined interpretation; investigate prevalence.')
        self.assertFalse(self.sam.domain_chat.state()['reports'][0]['current']);self.assertTrue(self.sam.latest_records('domain-coach-edit'))
    def test_concurrent_or_interrupted_requests_do_not_silently_retry(self):
        t=self.start();t=self.sam.domain_chat.update(t,pending=dict(request_id='interrupted-request',at=(datetime.now(timezone.utc)-timedelta(minutes=7)).isoformat()))
        with self.assertRaises(ValueError):self.send(self.sam,t)
        self.sam.command('domain-chat-recover',dict(conversation=asdict(t['ref'])))
        self.assertIsNone(self.current(self.sam,t)['body']['pending']);self.assertFalse(self.model.calls)
    def test_publication_releases_authored_work_not_private_conversation(self):
        t=self.attach(self.sam,self.start());self.send(self.sam,t);d=self.draft(self.sam,t)
        saved=self.sam.command('domain-save',{**d['body'],'expected':asdict(d['ref']),'observation':'Author-reviewed fictional finding; verify with real research before use.'})
        current=self.store.latest(saved['id'],self.sam.scopes)
        prepared=self.sam.command('domain-prepare',dict(expected=asdict(current['ref']),recipient='design'))
        handoff=self.store.latest(prepared['domainHandoff'],self.sam.scopes)
        result=self.sam.command('domain-publish',dict(expected=asdict(current['ref']),preflight=asdict(handoff['ref']),confirm=True,release_sources=True))
        contribution=self.store.latest(result['id'],{SCOPE});self.assertEqual(contribution['body']['observation'],current['body']['observation'])
        packet=self.store.resolve_packet('PKT-'+result['id'],1,{SCOPE})
        self.assertFalse(any(r['kind'] in ('domain-conversation','domain-chat-turn','domain-chat-review') for r in packet['records']))
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)

    def test_research_pdf_citations_retain_exact_page_locations(self):
        t=self.start();raw=prototype_pdf();out=self.sam.command('domain-chat-attach',dict(conversation=asdict(t['ref']),expected=asdict(self.draft(self.sam,t)['ref']),filename='fictional-study.pdf',content=base64.b64encode(raw).decode()))
        t=self.sam.domain_chat.owned(out['conversation']);self.send(self.sam,t)
        report=self.sam.domain_chat.state()['reports'][0];self.assertEqual(report['body']['locations'][0]['page'],1)
        source=self.sam.domain_chat.source(t)['body'];offset=source['text'].index('Photo required before you can submit')
        self.assertEqual(next(p['page'] for p in source['page_spans'] if p['start']<=offset<p['end']),2)

    def test_existing_deliverable_and_publication_connections_are_retained(self):
        t=self.attach(self.sam,self.start());d=self.draft(self.sam,t);again=self.sam.command('domain-chat-start',dict(draft=asdict(d['ref'])))
        self.assertEqual(again['conversation']['id'],t['ref'].id)
        handoff=self.sam.command('domain-prepare',dict(expected=asdict(d['ref']),recipient='design'));self.assertTrue(handoff['domainHandoff'])
        self.assertEqual(len(self.sam.latest_records('contribution')),1)

if __name__=='__main__':unittest.main()

class ChatWebTests(unittest.TestCase):
    def setUp(self):
        from test_web import WebTests
        WebTests.setUp(self);self.post=WebTests.post.__get__(self);self.server.model=ChatModel();self.post('profile',dict(actor='sam'))
    def tearDown(self):
        from test_web import WebTests
        WebTests.tearDown(self)
    def test_shared_assets_and_complete_http_upload_review_chain(self):
        import json
        for path in ('/domain-chat.js','/domain-chat.css'):
            self.conn.request('GET',path);r=self.conn.getresponse();self.assertEqual(r.status,200);r.read()
        status,start=self.post('domain-chat-start',{});self.assertEqual(status,200)
        status,attached=self.post('domain-chat-attach',dict(conversation=start['conversation'],expected=dict(id=start['id'],revision=1),filename='http-fictional.txt',content=base64.b64encode(b'Fictional task observation.').decode()));self.assertEqual(status,200,attached)
        self.conn.request('GET','/api/state',headers={'Cookie':self.cookie});state=json.loads(self.conn.getresponse().read());thread=state['domain_chat']['threads'][0]
        status,result=self.post('domain-chat-send',dict(conversation=thread['ref'],expected=thread['draft'],consent=True,message='Review this synthetic observation.',request_id='http-synthetic-request'))
        self.assertEqual(status,200,result);self.assertIn('chatReport',result)
        self.post('profile',dict(actor='lee'))
        status,denied=self.post('domain-chat-send',dict(conversation=thread['ref'],expected=thread['draft'],consent=True,message='Wrong author',request_id='http-wrong-author-request'))
        self.assertEqual(status,403,denied)

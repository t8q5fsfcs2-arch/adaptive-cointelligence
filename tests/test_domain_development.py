import base64
from copy import deepcopy
from dataclasses import asdict
import io
import unittest
import zipfile
from unittest.mock import patch

import test_domain_chat as fixture
from workbench.core import Ref, StaleBasis
from workbench.decisions import SCOPE, fingerprint, now
from workbench.workspace import Workspace
from workbench.domain_alignment import key
from workbench.model_provider import ModelUnavailable
from pdf_fixture import prototype_pdf

class ObjectiveScopeContractTests(unittest.TestCase):
    def test_submission_without_objectives_cannot_request_an_invented_objective_review(self):
        from workbench.domain_submission import schema
        ctx=dict(sources=[],requirements=[],goals_and_measures=[],business_intent=[])
        self.assertEqual(schema(ctx)['properties']['objective_review']['maxItems'],0)
    def test_proposed_criteria_and_unresolved_gaps_cannot_masquerade_as_existing_supported_terms(self):
        from workbench.project_implications import schema
        ctx=dict(requirements=[dict(ref=dict(id='REQ-1',revision=1),body=dict(acceptance_criteria='Existing exact condition.'))])
        props=schema(ctx)['items']['properties']
        self.assertEqual(props['criterion']['enum'],['','Existing exact condition.'])
        branches=props['support']['anyOf']
        substantive=next(x for x in branches if x['properties']['assessment']['enum']==['substantive'])
        self.assertEqual(substantive['properties']['gaps']['maxItems'],0)

class DevelopmentModel(fixture.ChatModel):
    def implication(self,ctx):
        source=ctx['sources'][0] if ctx['sources'] else None
        cite=[dict(source=key(source['ref']),quote=source['body']['text'][-60:],page=None)] if source else [dict(source=key(ctx['visual_source']['ref']),quote='',page=ctx['pages'][0]['page'])] if ctx.get('visual_source') else []
        return dict(kind='new-requirement',title='Recover interrupted reports',statement='Preserve entered feedback across an interruption.',rationale='The fictional evidence suggests recovery needs; generalization remains uncertain.',targets=[],evidence=cite)
    def generate(self,**kw):
        ctx=kw['context']
        if ctx.get('workbench_task')!='submission-evaluation':
            result=super().generate(**kw)
            if 'implications' in kw['schema']['properties']:result['output'].update(implications=[self.implication(ctx)],objective_review=[])
            return result
        self.calls.append(deepcopy(kw))
        if self.during:self.during()
        if self.fail:raise ModelUnavailable('Synthetic evaluation failure')
        p=self.implication(ctx)
        return dict(output=dict(summary='Consider recovery as a new requirement; preserve the limits.',implications=[p],objective_review=[dict(objective_id=o['id'],assessment='partial',rationale='Capture is described; recovery and triage need more evidence.',evidence=p['evidence'],next_step='Observe an interrupted attempt and ask about the triage handoff.') for o in ctx.get('working_objectives',{}).get('objectives',[])],limitations=['Fictional data. No runtime benefit or product validation.']),model='synthetic',usage={})
    def generate_visual(self,**kw):
        if kw['context'].get('workbench_task')=='submission-evaluation':return self.generate(**kw)
        return super().generate_visual(**kw)

class DevelopmentTests(unittest.TestCase):
    tearDown=fixture.ChatTests.tearDown
    start=fixture.ChatTests.start
    current=fixture.ChatTests.current
    draft=fixture.ChatTests.draft
    attach=fixture.ChatTests.attach
    send=fixture.ChatTests.send
    def setUp(self):
        fixture.ChatTests.setUp(self);self.model=DevelopmentModel();self.sam=Workspace(self.store,'sam',self.model);self.lee=Workspace(self.store,'lee',self.model)
        ctx=self.sam.domain_brief.context(None)
        self.plan=self.store.put('RESEARCH-OBJECTIVES','domain-work-plan','domain:research',dict(owner='sam',work_request=None,signature=fingerprint(ctx),basis=ctx['basis'],profile=ctx['domain_profile'],output={'objectives':[]},objectives=[dict(title='Understand interruption and resumption',question='What does the receptionist need to resume?',why='Avoid lost feedback.',output='Task evidence.',evidence='Interview and observation.')],status='working',at=now()))
        self.t=self.attach(self.sam,self.start(),text='Fictional interview: a receptionist lost entered feedback after interruption.')
    def data(self,w=None,t=None):
        w=w or self.sam;t=t or self.t;sub=w.submissions.latest(self.current(w,t))
        return dict(conversation=asdict(self.current(w,t)['ref']),expected=asdict(self.draft(w,t)['ref']),submission=asdict(sub['ref']) if sub else None)
    def save(self,**extra):
        b=dict(text='A proposed discovery contribution.',source_refs=self.draft(self.sam,self.t)['body']['source_refs'],implication_refs=[],primary_source=None,review_mode='text')
        return self.sam.command('domain-submission-save',{**self.data(),**b,**extra})
    def evaluate(self,request='evaluation-request-001',**extra):
        return self.sam.command('domain-submission-evaluate',{**self.data(),'consent':True,'request_id':request,'cycle':'evaluation-cycle-001','batch':0,**extra})
    def test_discussion_holds_new_unmatched_implications_and_reflects_research_objectives(self):
        before=self.draft(self.sam,self.t);self.send(self.sam,self.t)
        state=self.sam.domain_chat.state();row=state['implications'][0]
        self.assertEqual(row['body']['payload']['targets'],[]);self.assertEqual(row['body']['status'],'suggested')
        self.assertEqual(state['objectives'][0]['objectives'][0]['id'],'objective-0')
        self.sam.command('domain-implication-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=asdict(row['ref']),status='held',statement='Researcher-refined recovery need.'))
        self.send(self.sam,self.t,request_id='second-discussion-request')
        self.assertEqual(self.model.calls[-1]['context']['working_implications'][0]['statement'],'Researcher-refined recovery need.')
        self.assertEqual(self.draft(self.sam,self.t),before)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
        self.assertEqual(self.lee.domain_chat.state()['implications'],[])
    def test_entire_word_document_is_imported_evaluated_edited_and_reentered(self):
        text='Fictional full report.\n'+('A receptionist explained an interruption.\n'*900)+'ENDING: the recovery question remains open.'
        raw=io.BytesIO()
        with zipfile.ZipFile(raw,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>'+text+'</w:t></w:r></w:p></w:body></w:document>')
        self.sam.command('domain-submission-import',{**self.data(),'filename':'fictional-research.docx','content':base64.b64encode(raw.getvalue()).decode()})
        sub=self.sam.submissions.latest(self.current(self.sam,self.t));self.assertIn('ENDING:',sub['body']['text']);self.assertGreater(len(sub['body']['text']),24000)
        first=self.evaluate();call=self.model.calls[-1]['context'];self.assertEqual(call['submission']['content_source'],sub['body']['primary_source']);self.assertEqual(call['sources'][0]['body']['text'],sub['body']['text']);self.assertIn('ENDING:',call['sources'][0]['body']['text'])
        r=self.store.read(Ref(**first['evaluation']),self.sam.scopes)
        self.assertEqual(r['body']['output']['objective_review'][0]['assessment'],'partial')
        self.sam.command('domain-submission-edit-evaluation',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),evaluation=first['evaluation'],expected=None,summary='Researcher: recovery is plausible; further observation needed.'))
        self.assertEqual(self.store.read(r['ref'],self.sam.scopes),r)
        body=sub['body'];self.save(**{k:body[k] for k in ('source_refs','implication_refs','primary_source','review_mode')},text=body['text']+'\nA new author clarification.')
        self.assertFalse(self.sam.submissions.is_current(r,self.current(self.sam,self.t)))
        self.evaluate(request='evaluation-request-002');self.assertEqual(len(self.sam.submissions.evaluations(self.current(self.sam,self.t))),2)
        with self.assertRaises(ValueError):self.sam.command('domain-submission-import',{**self.data(),'filename':'new.txt','content':base64.b64encode(b'New report').decode()})
    def test_selected_submission_reaches_real_packet_without_discussion_or_unselected_files(self):
        self.attach(self.sam,self.t,text='PRIVATE UNSELECTED SOURCE must stay private.')
        self.send(self.sam,self.t,message='PRIVATE DISCUSSION must stay private.')
        sources=self.draft(self.sam,self.t)['body']['source_refs'];selected=next(raw for raw in sources if 'PRIVATE UNSELECTED SOURCE' not in self.store.read(Ref(**raw),self.sam.scopes)['body']['text'])
        self.save(source_refs=[selected]);out=self.evaluate()
        row=next(r for r in self.sam.implications.records(self.current(self.sam,self.t)) if r['body']['origin']['id']==out['evaluation']['id'])
        saved=self.sam.command('domain-implication-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=asdict(row['ref']),status='held'))
        self.save(source_refs=[selected],implication_refs=[saved['ref']])
        before=self.draft(self.sam,self.t)
        prepared=self.sam.command('domain-submission-prepare',{**self.data(),'include_evaluation':True})
        handoff=self.store.latest(prepared['domainHandoff'],self.sam.scopes);snap=handoff['body']['draft']
        self.assertEqual(self.draft(self.sam,self.t),before)
        published=self.sam.command('domain-publish',dict(expected=snap,preflight=asdict(handoff['ref']),confirm=True,release_sources=True))
        packet=self.store.resolve_packet(published['packet']['id'],published['packet']['revision'],{SCOPE})
        encoded=str(packet)
        self.assertNotIn('PRIVATE DISCUSSION',encoded);self.assertNotIn('PRIVATE UNSELECTED SOURCE',encoded)
        self.assertIn('Recover interrupted reports',encoded);self.assertIn('Submission evaluation',encoded)
        self.assertTrue(all(r['scope']==SCOPE for r in packet['records']))
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
    def test_failed_or_stale_evaluation_preserves_submission_and_can_retry(self):
        self.save();before=self.sam.submissions.latest(self.current(self.sam,self.t));self.model.fail=True
        with self.assertRaises(ModelUnavailable):self.evaluate()
        self.assertEqual(self.sam.submissions.latest(self.current(self.sam,self.t)),before)
        self.assertIsNone(self.current(self.sam,self.t)['body']['pending'])
        self.model.fail=False;self.evaluate(request='evaluation-request-retry')
        count=len(self.model.calls);self.evaluate(request='evaluation-request-retry');self.assertEqual(len(self.model.calls),count)
        self.model.during=lambda:self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'Changed during evaluation.'},self.req['ref'].revision)
        with self.assertRaises(StaleBasis):self.evaluate(request='evaluation-stale-basis')
        self.assertEqual(len(self.sam.submissions.evaluations(self.current(self.sam,self.t))),1)
    def test_other_author_cannot_edit_submission_evaluation_or_implication(self):
        self.save();out=self.evaluate();self.assertEqual(self.lee.domain_chat.state()['submissions'],[])
        with self.assertRaises(PermissionError):self.lee.command('domain-submission-edit-evaluation',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),evaluation=out['evaluation'],expected=None,summary='Forged'))
        row=self.sam.implications.records(self.current(self.sam,self.t))[0]
        with self.assertRaises(PermissionError):self.lee.command('domain-implication-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=asdict(row['ref']),status='held'))
    def test_pdf_exports_inspect_actual_pages_and_record_complete_coverage(self):
        self.sam.command('domain-submission-import',{**self.data(),'filename':'fictional-figjam.pdf','content':base64.b64encode(prototype_pdf()).decode()})
        sub=self.sam.submissions.latest(self.current(self.sam,self.t));self.assertEqual(sub['body']['review_mode'],'visual')
        self.evaluate();call=self.model.calls[-1];self.assertTrue(call['images']);self.assertEqual(call['context']['pages'][0]['page'],1)
        self.assertEqual(call['context']['submission']['text'],'')
        self.assertEqual(len(self.sam.domain_chat.state()['submissions'][0]['evaluations']),1)
    def test_design_uses_the_same_submission_lifecycle_and_retains_its_brief_gate(self):
        t=self.start(self.lee)
        self.lee.command('domain-submission-save',{**self.data(self.lee,t),'text':'Fictional design submission','source_refs':[],'implication_refs':[],'primary_source':None,'review_mode':'text'})
        self.lee.command('domain-submission-evaluate',{**self.data(self.lee,t),'consent':True,'request_id':'design-evaluation-001','cycle':'design-evaluation-cycle','batch':0})
        with self.assertRaises(ValueError):self.lee.command('domain-submission-prepare',{**self.data(self.lee,t),'include_evaluation':True})
        self.assertEqual(len(self.lee.submissions.state(self.lee.domain_chat.threads())[0]['evaluations']),1)

    def test_passage_ids_resolve_to_exact_quotes_and_unknown_ids_are_rejected(self):
        self.save();original=self.model.generate
        def selected(**kw):
            result=original(**kw)
            for group in ('implications','objective_review'):
                for row in result['output'].get(group,[]):row['evidence']=[dict(passage=kw['context']['evidence_passages'][0]['id'])]
            return result
        self.model.generate=selected;out=self.evaluate();r=self.store.read(Ref(**out['evaluation']),self.sam.scopes)
        self.assertEqual(r['body']['output']['implications'][0]['evidence'][0]['quote'],r['body']['context']['evidence_passages'][0]['quote'])
        def forged(**kw):
            result=selected(**kw);result['output']['implications'][0]['evidence']=[dict(passage='EV-NOT-SUPPLIED')];return result
        self.model.generate=forged
        with self.assertRaises(ModelUnavailable):self.evaluate(request='forged-passage-request')
        self.assertEqual(len(self.sam.submissions.evaluations(self.current(self.sam,self.t))),1)

    def test_submission_versions_are_inspectable_without_replacing_current_work(self):
        first=self.save(text='Earlier author wording.')
        self.save(text='Revised author wording.')
        read=self.sam.command('domain-submission-read',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),version=first['ref']))
        self.assertEqual(read['text'],'Earlier author wording.')
        self.assertEqual(self.sam.submissions.latest(self.current(self.sam,self.t))['body']['text'],'Revised author wording.')
        self.assertTrue(self.sam.submissions.state([self.current(self.sam,self.t)])[0]['history'])
        with self.assertRaises(PermissionError):self.lee.command('domain-submission-read',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),version=first['ref']))


    def test_image_only_figjam_export_evaluates_every_page_in_bounded_parts(self):
        from pypdf import PdfWriter
        writer=PdfWriter()
        for i in range(8):writer.add_blank_page(width=300,height=200)
        data=io.BytesIO();writer.write(data)
        self.sam.command('domain-submission-import',{**self.data(),'filename':'image-only-figjam.pdf','content':base64.b64encode(data.getvalue()).decode()})
        sub=self.sam.submissions.latest(self.current(self.sam,self.t));plan=self.sam.submissions.plan(sub)
        self.assertEqual([p['pages'] for p in plan],[list(range(1,7)),[7,8]])
        self.evaluate(request='image-only-pages-1',batch=0)
        self.evaluate(request='image-only-pages-2',batch=1)
        rows=self.sam.submissions.state([self.current(self.sam,self.t)])[0]['evaluations']
        self.assertEqual(len(rows),2);self.assertTrue(all(r['current'] for r in rows))
        self.assertEqual({page for r in rows for page in r['body']['batch']['pages']},set(range(1,9)))


class DevelopmentHTTPTests(unittest.TestCase):
    def setUp(self):
        from test_web import WebTests
        WebTests.setUp(self);self.post=WebTests.post.__get__(self);self.server.model=DevelopmentModel();self.post('profile',dict(actor='sam'))
    def tearDown(self):
        from test_web import WebTests
        WebTests.tearDown(self)
    def test_saved_submission_and_evaluation_use_actual_routes_and_role_guards(self):
        import json
        self.conn.request('GET','/domain-development.js');response=self.conn.getresponse();self.assertEqual(response.status,200);self.assertIn(b'Project implications',response.read())
        status,thread=self.post('domain-chat-start',{});self.assertEqual(status,200)
        data=dict(conversation=thread['conversation'],expected=dict(id=thread['id'],revision=1),submission=None,text='A fictional research synthesis.',source_refs=[],implication_refs=[],primary_source=None,review_mode='text')
        status,saved=self.post('domain-submission-save',data);self.assertEqual(status,200,saved)
        status,evaluated=self.post('domain-submission-evaluate',{**data,'submission':saved['ref'],'consent':True,'request_id':'http-evaluation-request','cycle':'http-evaluation-cycle','batch':0});self.assertEqual(status,200,evaluated)
        self.post('profile',dict(actor='lee'))
        status,denied=self.post('domain-submission-edit-evaluation',dict(conversation=data['conversation'],evaluation=evaluated['evaluation'],expected=None,summary='Wrong author'));self.assertEqual(status,403,denied)

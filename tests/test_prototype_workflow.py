import json
import os
from copy import deepcopy
from dataclasses import asdict
from unittest import TestCase
from unittest.mock import patch

import test_design_brief as brief
from workbench.core import StaleBasis
from workbench.workspace import Workspace
from workbench.model_provider import ModelUnavailable
from workbench.prototype_render import figma_code
from workbench.prototype_workflow import validate
from workbench.tool_imports import PROVIDERS

def example(ctx):
    reqs=[r['ref']['id'] for r in ctx['requirements']];section=ctx['working_design_brief']['adopted'][0]['id']
    def screen(key,destination):return dict(key=key,title='Capture feedback' if key=='capture' else 'Pending confirmation',description='Fictional design representation; no storage test.',status='Not submitted',fields=[dict(label='Description',value='Fictional blocked cart',help='Describe the non-safety issue.')],actions=[dict(label='Continue',destination=destination)],requirement_ids=reqs,brief_section_ids=[section])
    return dict(title='Fictional capture alternatives',hypothesis='Visible state may reduce uncertainty; test with people.',variants=[dict(key=k,name='Variant '+k,hypothesis='A fictional hypothesis.',change='One explicitly varied interaction.',screens=[screen('capture','recovery'),screen('recovery','confirmed'),screen('confirmed','capture')]) for k in ('A','B')],factors=[dict(name='Save interaction',levels=['Manual save','Automatic draft'],why='Compare a bounded behavior.')],test_plan={k:'Researcher must establish the task, controls and actual evidence; no outcome claimed.' for k in ('question','task','success_signals','controls','allocation','evidence_needed','decision_rule','limitations')},open_questions=['No actual human test has run.'])

class PrototypeModel:
    def __init__(self):self.calls=[];self.during=None;self.bad=False
    def status(self):return dict(configured=True,provider='TEST DOUBLE',model='prototype-test')
    def generate(self,**kw):
        self.calls.append(deepcopy(kw));out=example(kw['context'])
        if self.bad:out['variants'][0]['screens'][0]['requirement_ids']=['FORGED']
        if self.during:self.during()
        return dict(output=out,model='prototype-test')

class PrototypeTests(TestCase):
    setUp=brief.DesignBriefTests.setUp;tearDown=brief.DesignBriefTests.tearDown
    seed=brief.DesignBriefTests.seed;generate_brief=brief.DesignBriefTests.generate;payload=brief.DesignBriefTests.payload
    def start(self):
        self.seed();plan=self.generate_brief();data=self.payload(plan)
        for s in data['brief_sections']:
            if s['kind']!='requirement-implication':s['disposition']='use'
        self.design.command('domain-objectives-save',{**data,'complete':True})
        self.m=PrototypeModel();self.design=Workspace(self.store,'lee',self.m)
        self.t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation'])
    def data(self):
        t=self.store.latest(self.t['ref'].id,{'domain:design'})
        return dict(conversation=asdict(t['ref']),expected=asdict(self.design.domain_chat.draft(t)['ref']))
    def generate(self):
        preview=self.design.command('domain-prototype-preview',self.data())
        out=self.design.command('domain-prototype-generate',{**self.data(),'signature':preview['signature'],'consent':True})
        return self.store.latest(out['id'],self.design.scopes)
    def stage(self,r):return self.design.command('domain-prototype-stage',dict(plan=asdict(r['ref']),url='https://www.figma.com/design/TEST/Prototype'))
    def configure(self):self.design.command('domain-tool-settings',dict(provider='figma',expected=None,enabled=True,export_enabled=True,protocol='2025-11-25',tool=PROVIDERS['figma']['tool'],arguments=PROVIDERS['figma']['arguments']))
    def test_brief_and_released_research_are_required_and_inputs_exact(self):
        self.seed();self.t=self.design.domain_chat.owned(self.design.command('domain-chat-start',{})['conversation'])
        with self.assertRaises(ValueError):self.design.command('domain-prototype-preview',self.data())
        self.tearDown();self.setUp();self.start();preview=self.design.command('domain-prototype-preview',self.data());self.assertIn('PUB-RESEARCH',str(preview));self.assertNotIn('PRIVATE-STUDY',str(preview))
        ctx=self.design.prototypes.context(self.data())[1];self.assertEqual(ctx['requirements'][0]['body']['acceptance_criteria'],'Show evidence pending.');self.assertIn('working_design_brief',ctx);self.assertIn('working_objectives',ctx)
    def test_generation_is_private_editable_and_does_not_select_winner_or_change_requirements(self):
        self.start();before=self.store.latest(self.req['ref'].id,self.design.scopes);r=self.generate();self.assertEqual(len(r['body']['output']['variants']),2);self.assertEqual(r['body']['mode'],'simulated');self.assertFalse(self.design.bridge.issues());self.assertEqual(self.store.latest(self.req['ref'].id,self.design.scopes),before)
        edited=deepcopy(r['body']['output']);edited['variants'][0]['hypothesis']='Designer-refined hypothesis.'
        self.design.command('domain-prototype-save',dict(plan=asdict(r['ref']),output=edited));self.assertEqual(self.store.read(r['ref'],self.design.scopes)['body']['output']['variants'][0]['hypothesis'],'A fictional hypothesis.')
        saved=self.store.latest(r['ref'].id,self.design.scopes);self.assertTrue(self.design.prototypes.current(saved));self.assertEqual(saved['body']['output']['variants'][0]['hypothesis'],'Designer-refined hypothesis.')
    def test_preview_staleness_unverified_links_and_cross_variant_navigation_rejected(self):
        self.start()
        with self.assertRaises(StaleBasis):self.design.command('domain-prototype-generate',{**self.data(),'consent':True,'signature':'old'})
        self.assertEqual(self.m.calls,[]);self.m.bad=True
        with self.assertRaises(ModelUnavailable):self.generate()
        self.m.bad=False;r=self.generate();out=deepcopy(r['body']['output']);out['variants'][0]['screens'][0]['actions'][0]['destination']='OUTSIDE'
        with self.assertRaises(ValueError):validate(out,r['body']['context'])
    def test_changed_brief_or_requirements_invalidate_export_and_preserve_old_plan(self):
        self.start();r=self.generate();req=self.store.latest(self.req['ref'].id,self.design.scopes);self.store.put(req['ref'].id,req['kind'],req['scope'],{**req['body'],'text':'Changed governing wording.'},req['ref'].revision)
        self.assertFalse(self.design.prototypes.current(r))
        with self.assertRaises(StaleBasis):self.stage(r)
    def test_source_upload_does_not_invalidate_unrelated_prototype_basis(self):
        import base64
        self.start();r=self.generate();self.design.command('domain-chat-attach',{**self.data(),'filename':'user-testing.txt','content':base64.b64encode(b'New fictional user testing input.').decode()});self.assertTrue(self.design.prototypes.current(r))
    def test_other_domains_and_owners_cannot_read_or_export_private_prototype(self):
        self.start();r=self.generate()
        with self.assertRaises(PermissionError):self.sam.command('domain-prototype-stage',dict(plan=asdict(r['ref']),url='https://www.figma.com/design/TEST'))
        self.assertNotIn(r['ref'].id,str(self.sam.domain_chat.state()))
    def test_staging_is_not_external_execution_and_no_credentials_leave_server(self):
        self.start();r=self.generate();out=self.stage(r);exp=self.store.read(reference(out['export']),self.design.scopes);self.assertEqual(exp['body']['status'],'staged')
        self.configure()
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):self.design.command('domain-prototype-send',dict(export=out['export'],confirm=True))
        self.assertEqual(self.store.latest(exp['ref'].id,self.design.scopes)['body']['status'],'staged');self.assertNotIn('TOKEN',str(exp['body']))
    def test_confirmed_write_is_recorded_and_cannot_be_retried(self):
        self.start();r=self.generate();out=self.stage(r);self.configure();calls=[]
        class Writer:
            def __init__(self,*args):pass
            def prepare(self):pass
            def write(self,args):calls.append(args);return dict(structuredContent=dict(createdNodeIds=['1:1','1:2'],frames=[dict(id='1:2',name='A/capture')]))
        self.design.prototypes.writer=Writer
        with patch.dict(os.environ,{self.design.tool_imports.credential('figma'):'test-secret'}):self.design.command('domain-prototype-send',dict(export=out['export'],confirm=True))
        exp=self.store.latest(out['export']['id'],self.design.scopes);self.assertEqual(exp['body']['status'],'sent');self.assertEqual(exp['body']['channel'],'workbench-mcp');self.assertNotIn('test-secret',str(exp));self.assertNotIn('PRIVATE-STUDY',str(calls));self.assertNotIn('business_intent',str(calls));self.assertIn('createAutoLayout',calls[0]['code'])
        with self.assertRaises((ValueError,StaleBasis)):self.design.command('domain-prototype-send',dict(export=asdict(exp['ref']),confirm=True))
        self.assertEqual(len(calls),1)
    def test_uncertain_write_is_retained_without_automatic_retry(self):
        self.start();r=self.generate();out=self.stage(r);self.configure()
        class Writer:
            def __init__(self,*args):pass
            def prepare(self):pass
            def write(self,args):raise TimeoutError('Unknown outcome')
        self.design.prototypes.writer=Writer
        with patch.dict(os.environ,{self.design.tool_imports.credential('figma'):'test-secret'}):
            with self.assertRaises(ValueError):self.design.command('domain-prototype-send',dict(export=out['export'],confirm=True))
        self.assertEqual(self.store.latest(out['export']['id'],self.design.scopes)['body']['status'],'outcome-unknown')
    def test_renderer_treats_user_text_as_data_not_javascript(self):
        self.start();r=self.generate();p=r['body']['output'];p['title']='</script> `${throw Error("execute")}`';script=figma_code(p,'WB-test');self.assertIn('const spec=',script);self.assertIn('setReactionsAsync',script);self.assertNotIn('eval(',script);self.assertIn('characters=value',script)
        from workbench.model_provider import request_timeout
        self.assertEqual(request_timeout({'skill':'domain-design-brief'}),180);self.assertEqual(request_timeout({'skill':'domain-prototype-alternatives'}),180)

from workbench.validation import reference


class PrototypeHTTPTests(TestCase):
    def setUp(self):
        from test_web import WebTests
        WebTests.setUp(self);self.post=WebTests.post.__get__(self)
    def tearDown(self):
        from test_web import WebTests
        WebTests.tearDown(self)
    def test_shared_script_and_design_action_are_served_by_the_real_http_backend(self):
        self.conn.request('GET','/domain-prototypes.js');response=self.conn.getresponse();self.assertEqual(response.status,200);self.assertIn(b'Prototype alternatives',response.read())
        self.conn.request('GET','/');response=self.conn.getresponse();self.assertEqual(response.status,200);self.assertIn(b'/domain-prototypes.js',response.read())
        self.post('profile',dict(actor='lee'));status,thread=self.post('domain-chat-start',{})
        self.assertEqual(status,200,thread)
        status,out=self.post('domain-prototype-preview',dict(conversation=thread['conversation'],expected=dict(id=thread['id'],revision=1)))
        self.assertEqual(status,400,out);self.assertIn('Working brief',out['error'])


class VisualPassageTests(TestCase):
    def test_model_selects_exact_context_passage_and_service_attaches_source_wording(self):
        from workbench.design_visual import VisualAgent,review_schema
        context=dict(pages=[dict(page=1)],review_basis=[dict(ref=dict(id='REQ',revision=3),body=dict(text='The exact requirement for a recoverable draft.'))],review_passages=[dict(id='RP1',ref=dict(id='REQ',revision=3),quote='The exact requirement for a recoverable draft.')])
        class Model:
            def generate_visual(self,**kw):return dict(output=dict(summary='A bounded visual review.',limitations='Static screenshots do not prove runtime storage.',reviewed_pages=[1],findings=[dict(page=1,area='Confirmation',observation='A stored state is visible.',assessment='question',rationale='Storage behavior still needs a test.',recommendation='Test interruption and retry.',context_links=[dict(passage_id='RP1')],uncertainty='No actual test evidence.')]))
        schema=review_schema(context);self.assertIn('passage_id',schema['properties']['findings']['items']['properties']['context_links']['items']['properties'])
        result=VisualAgent(Model()).run(context,[]);cite=result['output']['findings'][0]['context_links'][0];self.assertEqual(cite['ref']['revision'],3);self.assertEqual(cite['quote'],context['review_basis'][0]['body']['text'])
        context['review_passages']=[]
        with self.assertRaises(ModelUnavailable):VisualAgent(Model()).run(context,[])

class EvidenceSelectionContractTests(TestCase):
    def test_schema_only_allows_actual_supplied_passage_identifiers(self):
        from workbench.evidence_catalog import schema
        result=schema(dict(evidence_passages=[dict(id='EV1'),dict(id='EV2')]))
        self.assertEqual(result['items']['properties']['passage']['enum'],['EV1','EV2'])
        self.assertEqual(schema(dict(evidence_passages=[]))['maxItems'],0)

    def test_alignment_schema_limits_criteria_to_exact_requirement_wording(self):
        from workbench.domain_alignment import schema
        ctx=dict(requirements=[dict(ref=dict(id='REQ',revision=1),kind='requirement',body=dict(acceptance_criteria='Keep the draft.\nConfirm stored reports.'))],goals_and_measures=[dict(ref=dict(id='KPI',revision=1),kind='measure',body=dict(definition='Stored reports / starts'))])
        criteria=schema(ctx)['items']['properties']['criterion']['enum']
        self.assertIn('',criteria);self.assertIn('Keep the draft.',criteria)
        self.assertNotIn('Stored reports / starts',criteria)

    def test_unreadable_visual_payload_is_rejected_as_a_review_failure(self):
        from workbench.design_visual import VisualAgent
        class Model:
            def generate_visual(self,**kw):return dict(output=None)
        with self.assertRaises(ModelUnavailable):VisualAgent(Model()).run(dict(review_basis=[],pages=[]),[])

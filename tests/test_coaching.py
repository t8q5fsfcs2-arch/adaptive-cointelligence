from dataclasses import asdict
import base64
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from workbench.core import Store, StaleBasis
from workbench.workspace import Workspace
from workbench.model_provider import OpenAIModel, AnthropicModel, UnconfiguredModel, ModelUnavailable, load_model
from workbench.intake_sources import extract
from workbench.intake import VALUE_FIELDS, CONTEXT_FIELDS, ALL_FIELDS
from test_intake import VALUE, CONTEXT


class RecordingModel:
    def __init__(self):
        self.context = None
        self.custom = None
        self.during = None
    def status(self):
        return {'configured':True,'provider':'TEST DOUBLE','model':'test-only'}
    def generate(self, *, instructions, context, schema):
        self.context=deepcopy(context)
        self.schema=deepcopy(schema)
        if self.during:self.during()
        if self.custom is not None:out=deepcopy(self.custom)
        elif context['skill']=='review-value':
            out={'reply':'The proposed route connects to the stated job. Test whether it relieves repeated effort.', 'suggestions':[], 'questions':[]}
        elif context['skill']=='context-questions':
            out={'reply':'Explore when help is needed.','suggestions':[], 'questions':[{'field':'user_situation','question':'When do customers need assistance?','reason':'Availability affects the proposed assisted route.','based_on':['approach']}]}
        else:
            fields=['business_challenge','need'] if context['skill']=='seed-value' else [context['field']]
            out={'reply':'The source describes a limited observation, not prevalence.','questions':[], 'suggestions':[{'field':f,'text':'Some customers lose their place after asking for help.','rationale':'Preserve the observation and investigate scale.','basis':'source-supported','citations':[{'passage_id':context['sources'][0]['passages'][0]['id']}] if context['skill']=='seed-value' else [{'source_id':context['sources'][0]['id'],'quote':'customers lose their place'}]} for f in fields]}
        if context['skill']=='seed-value' and isinstance(out.get('suggestions'),list):
            slots={f:None for f in ALL_FIELDS if f not in ('assumption_owner','work_kind')}
            for proposal in out['suggestions']:
                slots[proposal['field']]={k:v for k,v in proposal.items() if k!='field'}
            out['suggestions']=slots
        return {'output':out,'model':'test-only','usage':{'input_tokens':10,'output_tokens':10}}


class CoachingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'db.sqlite3')
        self.model=RecordingModel();self.ws=Workspace(self.store,'priya',self.model)
        self.ws.command('intake-start',{'title':'Fictional enrollment'})
        self.ws.command('intake-save',{'expected':self.ref(),'step':'value',**VALUE})
        self.ws.command('intake-accept-value',{'expected':self.ref(),'confirm':True})
        self.source=self.ws.command('intake-source',{'title':'Fictional interview','text':'In this small study, customers lose their place after seeking help.','role':'evidence'})['ref']
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def ref(self):return asdict(self.ws.intake.draft()['ref'])
    def run_coach(self,**kw):
        return self.ws.command('intake-coach',{'expected':self.ref(),'skill':'coach-field','field':'need','message':'Help make this precise','sources':[self.source],'consent':True,**kw})['ref']
    def apply(self,r,field='need'):
        return self.ws.command('intake-coach-apply',{'run_id':r['id'],'field':field,'expected':self.ref(),'confirm':True})
    def test_model_is_separate_and_does_not_mutate_intake(self):
        before=self.ref();run=self.run_coach()
        self.assertEqual(self.ref(),before)
        self.assertEqual(self.model.context['values']['jobs'],VALUE['jobs'])
        self.assertEqual(self.model.context['sources'][0]['ref'],self.source)
        saved=self.ws.coaching.records('intake-coach-run')[0]
        self.assertEqual(saved['body']['agent'],'business-intent-coach')
        citation=saved['body']['output']['suggestions'][0]['citations'][0]
        self.assertEqual(citation['start'],self.model.context['sources'][0]['text'].index(citation['quote']))
        self.apply(run)
        self.assertEqual(self.ref()['revision'],before['revision']+1)
        self.assertIsNone(self.ws.intake.latest('INT-001'))
        self.assertFalse(self.ws.state()['decisions'])
    def test_seed_can_apply_several_fields_but_never_control_fields(self):
        run=self.run_coach(skill='seed-value')
        self.apply(run,'business_challenge');self.apply(run,'need')
        with self.assertRaises(ValueError):self.apply(run,'need')
        self.model.custom={'reply':'bad','questions':[], 'suggestions':[{'field':'work_kind','text':'Approve all','rationale':'no','basis':'hypothesis','citations':[]}]}
        with self.assertRaises(ModelUnavailable):self.run_coach(skill='seed-value')
    def test_context_questions_are_based_on_value_not_canned(self):
        self.run_coach(skill='context-questions')
        self.assertEqual(self.model.context['values']['approach'],VALUE['approach'])
        self.assertEqual(self.model.context['values']['pain_relievers'],VALUE['pain_relievers'])
        self.assertFalse(self.ws.coaching.records('intake-coach-run')[0]['body']['output']['suggestions'])
    def test_current_answer_sent_without_a_separate_message(self):
        self.run_coach()  # Earlier conversation must not replace the newly edited answer.
        current='Fictional follow-up: people may lose progress when they request help.'
        self.ws.intake.save({'expected':self.ref(),'step':'value','need':current})
        basis=self.ref()
        self.run_coach(message='   ')
        answer=self.model.context['working_answer']
        self.assertEqual(answer,{'field':'need','text':current,'basis':basis})
        self.assertEqual(self.model.context['values']['need'],current)
        self.assertTrue(self.model.context['prior_dialogue'])
        self.assertIn('Review my current working answer',self.model.context['message'])
        run=self.ws.coaching.records('intake-coach-run')[-1]['body']
        self.assertEqual(run['user_message'],'')
        self.assertEqual(run['working_answer'],answer)
        self.assertEqual(self.ref(),basis)  # Coaching itself never applies its proposal.
    def test_optional_instruction_supplements_the_current_answer(self):
        self.run_coach(message='Focus on the business consequence, without inventing a number.')
        self.assertEqual(self.model.context['working_answer']['text'],VALUE['need'])
        self.assertEqual(self.model.context['message'],'Focus on the business consequence, without inventing a number.')
        self.assertEqual(self.model.context['values']['approach'],VALUE['approach'])
    def test_cleared_answer_is_empty_not_replaced_by_previous_dialogue(self):
        self.run_coach()
        self.ws.intake.save({'expected':self.ref(),'step':'value','need':''})
        self.run_coach(message='')
        self.assertEqual(self.model.context['working_answer']['text'],'')
        self.assertEqual(self.model.context['values']['need'],'')
        self.assertIn('Help me get started',self.model.context['message'])
        with self.assertRaises(ValueError):self.run_coach(message={'bad':'type'})
    def only_challenge_answered(self):
        self.ws.intake.save({'expected':self.ref(),'step':'value',
            **{k:'' for k in VALUE_FIELDS if k!='assumption_owner'},
            'business_challenge':'Customers may abandon enrollment after seeking help.'})
        self.model.custom={'reply':'Let us establish how this challenge would be measured.',
            'suggestions':[], 'questions':[{'field':'measures',
                'question':'How would you measure whether customers can resume enrollment?',
                'reason':'Your business challenge identifies a possible loss of progress.',
                'based_on':['business_challenge']}]}
    def test_partial_intake_can_ask_about_an_unanswered_field(self):
        self.only_challenge_answered()
        before=self.ref()
        run=self.run_coach(field='business_challenge',sources=[],message='')
        basis=self.model.schema['properties']['questions']['items']['properties']['based_on']
        self.assertEqual(basis['items']['enum'],['business_challenge'])
        self.assertEqual(self.model.context['answered_fields'],['business_challenge'])
        saved=self.ws.coaching.records('intake-coach-run')[-1]
        self.assertEqual(asdict(saved['ref']),run)
        self.assertEqual(saved['body']['output']['questions'][0]['field'],'measures')
        self.assertEqual(self.ref(),before)
        self.assertEqual(self.ws.intake.draft()['body']['values']['measures'],'')
    def test_unanswered_or_unknown_basis_is_still_rejected(self):
        self.only_challenge_answered()
        for basis in (['measures'],['missing_field'],['business_challenge','measures'],[{}]):
            with self.subTest(basis=basis):
                self.model.custom['questions'][0]['based_on']=basis
                with self.assertRaisesRegex(ModelUnavailable,'intake references'):
                    self.run_coach(sources=[],message='')
        self.assertEqual(self.ws.coaching.records('intake-coach-run'),[])
    def test_empty_intake_can_receive_an_opening_question(self):
        self.only_challenge_answered()
        self.ws.intake.save({'expected':self.ref(),'step':'value','business_challenge':''})
        self.model.custom={'reply':'Start with the business challenge.','suggestions':[],
            'questions':[{'field':'business_challenge','question':'What business problem prompted this initiative?',
                'reason':'No intake answers have been supplied yet.','based_on':[]}]}
        self.run_coach(field='business_challenge',sources=[],message='')
        basis=self.model.schema['properties']['questions']['items']['properties']['based_on']
        self.assertEqual(basis['maxItems'],0)
        self.assertEqual(self.model.context['answered_fields'],[])
        self.assertEqual(self.model.context['working_answer']['text'],'')
    def test_question_basis_refreshes_after_answers_are_cleared(self):
        self.only_challenge_answered()
        self.run_coach(sources=[],message='')
        self.ws.intake.save({'expected':self.ref(),'step':'value','business_challenge':'', 'jobs':'Resume enrollment after asking for help.'})
        self.model.custom['questions'][0]['based_on']=['jobs']
        self.run_coach(sources=[],message='')
        basis=self.model.schema['properties']['questions']['items']['properties']['based_on']
        self.assertEqual(basis['items']['enum'],['jobs'])
        self.assertEqual(self.model.context['answered_fields'],['jobs'])
        self.assertTrue(self.model.context['prior_dialogue'])
    def test_context_questions_still_require_an_existing_answer(self):
        self.model.custom={'reply':'Explore the situation.', 'suggestions':[], 'questions':[{'field':'user_situation','question':'When is help needed?', 'reason':'This informs the proposed assistance route.', 'based_on':['business_challenge']}]}
        self.run_coach(skill='context-questions',sources=[])
        basis=self.model.schema['properties']['questions']['items']['properties']['based_on']
        self.assertEqual(basis['minItems'],1)
        self.assertIn('business_challenge',basis['items']['enum'])
        self.model.custom['questions'][0]['based_on']=[]
        with self.assertRaisesRegex(ModelUnavailable,'intake references'):
            self.run_coach(skill='context-questions',sources=[])
    def test_sources_and_dialogue_stay_private(self):
        self.run_coach()
        for actor in ('sam','maya','alex'):
            ws=Workspace(self.store,actor,self.model)
            self.assertEqual(ws.state()['coaching']['sources'],[])
            self.assertEqual(ws.state()['coaching']['runs'],[])
            self.assertNotIn('Fictional interview',json.dumps(ws.state(),default=str))
            with self.assertRaises(PermissionError):ws.command('intake-source',{'title':'x','text':'x'})
            with self.assertRaises(PermissionError):ws.command('intake-coach',{})
    def test_unselected_source_not_sent_and_missing_connection_not_faked(self):
        self.ws.command('intake-source',{'title':'Keep private','text':'Secret not for this request'})
        self.run_coach()
        self.assertNotIn('Secret',json.dumps(self.model.context))
        with self.assertRaises(ModelUnavailable):Workspace(self.store,'priya').command('intake-coach',{'expected':self.ref(),'skill':'coach-field','field':'need','message':'help','consent':True})
    def test_fabricated_quotes_and_other_fields_rejected(self):
        self.model.custom={'reply':'proposal','questions':[], 'suggestions':[{'field':'need','text':'Candidate','rationale':'Reason','basis':'source-supported','citations':[{'source_id':self.source['id'],'quote':'Made up quote'}]}]}
        with self.assertRaises(ModelUnavailable):self.run_coach()
        self.assertEqual(self.ws.coaching.records('intake-coach-run'),[])
        self.model.custom['suggestions'][0].update(field='value',basis='hypothesis',citations=[])
        with self.assertRaises(ModelUnavailable):self.run_coach()
    def test_stale_draft_during_call_or_before_apply(self):
        run=self.run_coach()
        self.ws.intake.save({'expected':self.ref(),'step':'value','jobs':'Changed jobs'})
        with self.assertRaises(StaleBasis):self.apply(run)
        count=len(self.ws.coaching.records('intake-coach-run'))
        self.model.during=lambda:self.ws.intake.save({'expected':self.ref(),'step':'value','value':'New direction'})
        with self.assertRaises(StaleBasis):self.run_coach()
        self.assertEqual(len(self.ws.coaching.records('intake-coach-run')),count)
    def test_review_releases_adopted_excerpts_not_source_or_conversation(self):
        self.apply(self.run_coach())
        # New material must receive an explicit disposition before this checkpoint.
        from test_document_changes import ChangeModel
        changes=Workspace(self.store,'priya',ChangeModel()).document_changes
        review=changes.assess({'expected':self.ref(),'trigger_source':self.source,'sources':[self.source],'consent':True})['ref']
        changes.resolve({'expected':self.ref(),'review':review,'disposition':'keep','reason':'Retain the wording already adopted after reviewing the new material.','confirm':True})
        self.ws.intake.accept_value({'expected':self.ref(),'confirm':True,'rationale':'Reviewed the adopted wording'})
        self.ws.intake.save({'expected':self.ref(),'step':'context',**CONTEXT})
        self.ws.intake.build({'expected':self.ref()})
        case=self.ws.intake.request({'expected':self.ref(),'confirm':True})['id']
        shared=Workspace(self.store,'sam').intake.latest(case)['body']['snapshot']
        self.assertIn('customers lose their place',json.dumps(shared))
        self.assertNotIn('In this small study,',json.dumps(shared))
        self.assertNotIn('Help make this precise',json.dumps(shared))
        self.assertNotIn('intake-coach-run',json.dumps(shared))
    def test_edit_retains_provenance_as_edited_and_fresh_advice_can_follow(self):
        self.apply(self.run_coach())
        # New material must receive an explicit disposition before this checkpoint.
        from test_document_changes import ChangeModel
        changes=Workspace(self.store,'priya',ChangeModel()).document_changes
        review=changes.assess({'expected':self.ref(),'trigger_source':self.source,'sources':[self.source],'consent':True})['ref']
        changes.resolve({'expected':self.ref(),'review':review,'disposition':'keep','reason':'Retain the wording already adopted after reviewing the new material.','confirm':True})
        self.ws.intake.accept_value({'expected':self.ref(),'confirm':True,'rationale':'Reviewed the adopted wording'})
        self.ws.intake.save({'expected':self.ref(),'step':'value','need':'A narrower observation'})
        p=self.ws.intake.draft()['body']['field_provenance']['need']
        self.assertEqual(p['status'],'sponsor-edited-after-coaching')
        self.run_coach()
        self.assertEqual(self.model.context['values']['need'],'A narrower observation')
    def test_consent_and_source_roles_validated(self):
        with self.assertRaises(ValueError):self.run_coach(consent=False)
        with self.assertRaises(ValueError):self.ws.command('intake-source',{'title':'x','text':'x','role':'approved-truth'})
        with self.assertRaises(ValueError):self.run_coach(sources=[self.source,self.source])


class ExtractionTests(unittest.TestCase):
    def test_text_and_word_extract_locally(self):
        self.assertEqual(extract({'title':'Notes','text':'Hello'})['text'],'Hello')
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="urn:w"><w:p><w:r><w:t>Test source</w:t></w:r></w:p></w:document>')
        out=extract({'filename':'test.docx','content':base64.b64encode(b.getvalue()).decode()})
        self.assertEqual(out['text'],'Test source');self.assertFalse(out['original_retained'])
    def test_text_pdf_above_fifty_pages_keeps_every_page_and_remains_bounded(self):
        from pypdf import PdfWriter
        from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
        writer=PdfWriter()
        for i in range(54):
            page=writer.add_blank_page(width=200,height=200)
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
            stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 20 100 Td (Evidence page '+str(i+1)+') Tj ET').encode());page[NameObject('/Contents')]=writer._add_object(stream)
        buf=io.BytesIO();writer.write(buf);data=dict(filename='research.pdf',content=base64.b64encode(buf.getvalue()).decode())
        out=extract(data);self.assertEqual(len(out['page_spans']),54);self.assertIn('Evidence page 54',out['text'])
        for _ in range(47):writer.add_blank_page(width=200,height=200)
        buf=io.BytesIO();writer.write(buf)
        with self.assertRaisesRegex(ValueError,'100 pages'):extract(dict(filename='research.pdf',content=base64.b64encode(buf.getvalue()).decode()))
    def test_empty_unsupported_and_oversized_rejected(self):
        for data in [{'title':'x','text':''},{'filename':'test.exe','content':'eA=='},{'title':'x','text':'x'*120001}]:
            with self.assertRaises(ValueError):extract(data)


class ProviderTests(unittest.TestCase):
    def test_openai_limits_distinguish_billing_spend_and_request_rate(self):
        from urllib.error import HTTPError
        model=OpenAIModel('test','gpt-5-mini')
        for code,expected in (
            ('credit_balance_exhausted','no API credits'),
            ('organization_spend_limit_exceeded','organization has reached its API spending'),
            ('project_spend_limit_exceeded','project has reached its spending'),
            ('organization_usage_limit_exceeded','API usage allowance'),
            ('insufficient_quota','billing or quota'),
            ('rate_limit_exceeded','temporarily limiting requests'),
            ('slow_down','temporarily limiting requests'),
        ):
            with self.subTest(code=code):
                body={'error':{'code':code,'message':'private-provider-body'}}
                error=HTTPError('url',429,'private-provider-body',{},io.BytesIO(json.dumps(body).encode()))
                with patch('workbench.model_provider.urlopen',side_effect=error):
                    with self.assertRaisesRegex(ModelUnavailable,expected) as raised:
                        model.generate(instructions='test',context={},schema={})
                self.assertNotIn('private-provider-body',str(raised.exception))
    def test_openai_limit_type_fallback_and_malformed_body_stay_safe(self):
        from urllib.error import HTTPError
        model=OpenAIModel('test','gpt-5-mini')
        cases=[({'error':{'type':'insufficient_quota'}},'billing or quota'),
               ({'error':{'type':'rate_limit_error'}},'temporarily limiting requests'),
               ({'error':{'code':{'unexpected':True}}},'usage or rate limit'),
               ({'error':[]},'usage or rate limit'),([], 'usage or rate limit')]
        for body,expected in cases:
            error=HTTPError('url',429,'ignored',{},io.BytesIO(json.dumps(body).encode()))
            with patch('workbench.model_provider.urlopen',side_effect=error):
                with self.assertRaisesRegex(ModelUnavailable,expected):
                    model.generate(instructions='test',context={},schema={})
        for body in (b'not json',b'x'*17000):
            error=HTTPError('url',429,'ignored',{},io.BytesIO(body))
            with patch('workbench.model_provider.urlopen',side_effect=error):
                with self.assertRaisesRegex(ModelUnavailable,'usage or rate limit'):
                    model.generate(instructions='test',context={},schema={})
    def test_document_requests_have_a_longer_timeout_without_hidden_retries(self):
        replies={
            'OpenAI': {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"reply":"ok"}'}]}]},
            'Anthropic': {'content':[{'type':'tool_use','name':'propose_intake_help','input':{'reply':'ok'}}]},
        }
        for model in (OpenAIModel('test','gpt-5-mini'),AnthropicModel('test','test-model')):
            for skill,seconds in (('seed-value',180),('coach-field',55),('review-value',55)):
                with self.subTest(provider=model.status()['provider'],skill=skill):
                    response=io.BytesIO(json.dumps(replies[model.status()['provider']]).encode())
                    with patch('workbench.model_provider.urlopen',return_value=response) as call:
                        model.generate(instructions='test',context={'skill':skill},schema={})
                    self.assertEqual(call.call_args.kwargs['timeout'],seconds)
                    self.assertEqual(call.call_count,1)
                    if isinstance(model,OpenAIModel):
                        self.assertFalse(json.loads(call.call_args.args[0].data)['store'])

    def test_timeout_connection_and_unreadable_errors_remain_distinct(self):
        from urllib.error import URLError
        for model in (OpenAIModel('test','gpt-5-mini'),AnthropicModel('test','test-model')):
            for error,expected in ((TimeoutError('private-payload'),'longer than 180 seconds'),
                    (URLError(TimeoutError('private-payload')),'longer than 180 seconds'),
                    (URLError('private-payload'),'connection'),(OSError('private-payload'),'connection')):
                with patch('workbench.model_provider.urlopen',side_effect=error) as call:
                    with self.assertRaisesRegex(ModelUnavailable,expected) as raised:
                        model.generate(instructions='test',context={'skill':'seed-value'},schema={})
                self.assertNotIn('private-payload',str(raised.exception));self.assertEqual(call.call_count,1)
            for raw in (b'invalid json',b'[]',b'null'):
                with patch('workbench.model_provider.urlopen',return_value=io.BytesIO(raw)):
                    with self.assertRaisesRegex(ModelUnavailable,'unreadable response'):
                        model.generate(instructions='test',context={'skill':'seed-value'},schema={})

    def test_openai_adapter_structured_response_and_secret_not_exposed(self):
        model=OpenAIModel('secret-not-for-browser','gpt-5-mini')
        reply={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'{"reply":"ok"}'}]}], 'model':'returned-model'}
        response=io.BytesIO(json.dumps(reply).encode())
        with patch('workbench.model_provider.urlopen',return_value=response) as call:
            result=model.generate(instructions='test',context={'value':'hypothesis'},schema={'type':'object'})
        request=call.call_args[0][0];payload=json.loads(request.data)
        self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
        self.assertFalse(payload['store']);self.assertEqual(payload['text']['format']['type'],'json_schema')
        self.assertEqual(result['output']['reply'],'ok')
        self.assertNotIn('secret-not-for-browser',repr(model)+json.dumps(model.status())+json.dumps(result))
    def test_config_switches_provider_without_agent_or_ui_changes(self):
        with tempfile.TemporaryDirectory() as d, patch.dict('os.environ',{},clear=True):
            p=Path(d)/'env';p.write_text('COACH_LLM_PROVIDER=openai\nOPENAI_API_KEY=not-a-real-key\nCOACH_LLM_MODEL=chosen-model\n')
            self.assertIsInstance(load_model(p),OpenAIModel)
            p.write_text('COACH_LLM_PROVIDER=anthropic\nCOACH_LLM_API_KEY=not-a-real-key\nCOACH_LLM_MODEL=chosen-model\n')
            self.assertIsInstance(load_model(p),AnthropicModel)
    def test_refusal_incomplete_and_http_error_fail_explicitly(self):
        from urllib.error import HTTPError
        model=OpenAIModel('test','gpt-5-mini')
        for result in [{'status':'incomplete'},{'status':'completed','output':[{'type':'message','content':[{'type':'refusal'}]}]}]:
            with patch('workbench.model_provider.urlopen',return_value=io.BytesIO(json.dumps(result).encode())):
                with self.assertRaises(ModelUnavailable):model.generate(instructions='test',context={},schema={})
        with patch('workbench.model_provider.urlopen',side_effect=HTTPError('url',401,'secret',{},None)):
            with self.assertRaisesRegex(ModelUnavailable,'key was not accepted'):model.generate(instructions='test',context={},schema={})

"""Private chat is durable advice, never a project write or approval."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import base64
import io
import zipfile
import sqlite3
import unittest
from workbench.core import Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.intake import Intake, PRIVATE
from workbench.projects import Projects
from workbench.thought_partner import ThoughtPartner
from workbench.model_provider import UnconfiguredModel, ModelUnavailable
import test_web

class Model:
 def __init__(self):self.calls=[];self.result={'reply':'Consider the outcome and its evidence.','citations':[]};self.error=None
 def status(self):return dict(configured=True,mode='simulated')
 def generate(self,**kwargs):
  self.calls.append(kwargs)
  if self.error:raise self.error
  return dict(output=self.result,usage={},model='test-fixture')

class ThoughtPartnerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'chat.sqlite3';store=Store(self.path);Intake(store,'priya').start({'title':'Synthetic initiative'})
  store.put('INT-TEST','intent',SCOPE,{'text':'Capture usable feedback','status':'accepted'})
  store.put('REQ-TEST','requirement',SCOPE,{'text':'Save submitted feedback','acceptance_criteria':['A receipt is shown'],'status':'accepted'})
  store.put('PRIVATE-TEST','intake-source',PRIVATE,{'text':'SECRET-UPLOAD'})
  store.put('DESIGN-TEST','contribution-draft','domain:design',{'text':'SECRET-VAULT'});store.close()
  self.projects=Projects(self.path);self.model=Model();self.chat=ThoughtPartner(self.path,self.projects,self.model)
  self.tid=self.chat.create('alice',{'title':'New conversation'})['id']
 def tearDown(self):self.tmp.cleanup()
 def send(self,**kw):return self.chat.send('alice',{'original'},{**dict(thread=self.tid,request_id='request-0001',message='What is the requirement for feedback?',expected_count=0,projects=[],consent=True),**kw})
 def test_general_chat_persists_without_modifying_project_and_uses_bounded_history(self):
  with sqlite3.connect(self.path) as db:before=list(db.iterdump())
  self.send();reopened=ThoughtPartner(self.path,self.projects,self.model).state('alice',{'original'},self.tid)
  self.assertEqual(len(reopened['thread']['messages']),2);self.assertEqual(reopened['thread']['messages'][1]['mode'],'simulated')
  self.assertFalse(self.model.calls[0]['context']['projects']);self.assertFalse(self.model.calls[0]['context']['sources'])
  for i in range(1,7):self.send(request_id=f'request-loop-{i:04}',expected_count=2*i)
  self.assertEqual(len(self.model.calls[-1]['context']['history']),10)
  with sqlite3.connect(self.path) as db:self.assertEqual(before,list(db.iterdump()))
 def test_selected_context_has_exact_shared_refs_criteria_and_no_private_content(self):
  self.model.result={'reply':'Show a receipt.','citations':['P1:S2']}
  result=self.send(projects=[dict(id='original',version=1)]);self.assertEqual(result['status'],'complete')
  ctx=self.model.calls[0]['context'];serialized=json.dumps(ctx)
  self.assertNotIn('SECRET',serialized);self.assertIn('A receipt is shown',serialized)
  source=next(s for s in ctx['sources'] if s['record_id']=='REQ-TEST');self.assertEqual(source['revision'],1);self.assertEqual(source['generation'],1)
  self.assertEqual(self.chat.state('alice',{'original'},self.tid)['thread']['projects'],['original'])
 def test_owner_and_membership_cannot_be_forged_or_revoked_history_exposed(self):
  self.assertEqual(self.chat.state('bob',{'original'})['threads'],[])
  with self.assertRaises(PermissionError):self.chat.state('bob',{'original'},self.tid)
  with self.assertRaises(PermissionError):self.chat.send('bob',{'original'},dict(thread=self.tid,request_id='request-spoof',message='Read it',expected_count=0,projects=[],consent=True))
  with self.assertRaises(PermissionError):self.chat.context([dict(id='original',version=1)],set(),'feedback')
  self.send(projects=[dict(id='original',version=1)])
  state=self.chat.state('alice',set(),self.tid);self.assertTrue(state['thread']['blocked']);self.assertEqual(state['thread']['messages'],[]);self.assertEqual(state['projects'],[])
  with self.assertRaises(PermissionError):self.chat.send('alice',set(),dict(thread=self.tid,request_id='request-new',message='Continue',expected_count=2,projects=[],consent=True))
 def test_stale_generation_count_and_missing_send_consent_do_not_call_model(self):
  with self.assertRaises(StaleBasis):self.send(projects=[dict(id='original',version=2)])
  with self.assertRaises(StaleBasis):self.send(expected_count=2)
  with self.assertRaises(ValueError):self.send(consent=False)
  self.assertEqual(self.model.calls,[]);self.assertEqual(self.chat.state('alice',None,self.tid)['thread']['count'],0)
 def test_duplicate_request_does_not_repeat_the_model_transaction(self):
  self.send();self.assertTrue(self.send()['duplicate']);self.assertEqual(len(self.model.calls),1);self.assertEqual(self.chat.state('alice',None,self.tid)['thread']['count'],2)
 def test_invalid_citations_and_unavailable_provider_preserve_message_without_fabricated_answer(self):
  self.model.result={'reply':'Invented citation','citations':['unknown']};self.assertEqual(self.send()['status'],'failed')
  message=self.chat.state('alice',None,self.tid)['thread']['messages'][-1];self.assertNotIn('Invented citation',message['text']);self.assertEqual(message['citations'],[])
  self.model.error=ModelUnavailable('The model is temporarily unavailable.');self.assertEqual(self.send(request_id='request-next',expected_count=2)['status'],'failed')
  self.assertIn('temporarily unavailable',self.chat.state('alice',None,self.tid)['thread']['messages'][-1]['text'])
 def test_restart_marks_pending_as_interrupted_without_silently_retrying(self):
  self.send()
  with self.chat.db() as db:db.execute("UPDATE messages SET status='pending',text='' WHERE role='assistant'")
  restarted=ThoughtPartner(self.path,self.projects,self.model)
  self.assertEqual(restarted.state('alice',None,self.tid)['thread']['messages'][-1]['status'],'interrupted');self.assertEqual(len(self.model.calls),1)
 def test_unconfigured_mode_saves_real_error_and_explicit_mode(self):
  self.chat.model=UnconfiguredModel();self.send();m=self.chat.state('alice',None,self.tid)['thread']['messages'][-1]
  self.assertEqual(m['status'],'failed');self.assertEqual(m['mode'],'unconfigured');self.assertTrue(m['text'])

 def upload(self,filename='research.docx'):
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="urn:w"><w:p><w:r><w:t>Fictional study: reporting should preserve drafts after interruption.</w:t></w:r></w:p></w:document>')
  return self.chat.attach('alice',{'original'},dict(thread=self.tid,filename=filename,content=base64.b64encode(raw.getvalue()).decode())),raw.getvalue()
 def test_private_document_extract_download_dedup_and_cited_passage(self):
  uploaded,raw=self.upload();did=uploaded['id'];self.assertEqual(self.model.calls,[])
  self.assertEqual(self.chat.download_document('alice',{'original'},self.tid,did),raw)
  duplicate,_=self.upload();self.assertEqual(duplicate['id'],did);self.assertTrue(duplicate['duplicate'])
  doc=self.chat.document('alice',{'original'},self.tid,did);self.assertTrue(doc['original_retained'])
  self.model.result={'reply':'Preserve drafts.','citations':['D1:P1']};self.send()
  ctx=self.model.calls[-1]['context'];source=ctx['sources'][0]
  self.assertEqual(source['content'],doc['text'][source['start']:source['end']]);self.assertEqual(source['sha256'],doc['sha256']);self.assertNotIn('original',ctx)
  with self.assertRaises(PermissionError):self.chat.download_document('bob',{'original'},self.tid,did)
  with self.assertRaises(PermissionError):self.chat.attach('bob',{'original'},dict(thread=self.tid,filename='x.txt',content='eA=='))
 def test_document_rename_remove_restore_preserve_historical_source_and_version_guards(self):
  uploaded,raw=self.upload();did=uploaded['id'];self.model.result={'reply':'Preserve drafts.','citations':['D1:P1']};self.send()
  saved=self.chat.state('alice',None,self.tid)['thread']['messages'][-1]['context']['sources'][0]
  data=dict(thread=self.tid,document=did,expected_revision=1,action='rename',title='Updated study name');self.chat.update_document('alice',None,data)
  with self.assertRaises(StaleBasis):self.chat.update_document('alice',None,data)
  self.chat.update_document('alice',None,{**data,'expected_revision':2,'action':'archive'})
  self.assertTrue(self.chat.state('alice',None,self.tid)['thread']['documents'][0]['archived'])
  self.model.result={'reply':'General advice.','citations':[]};self.send(request_id='request-after-archive',expected_count=2)
  self.assertEqual(self.model.calls[-1]['context']['documents'],[]);self.assertEqual(self.model.calls[-1]['context']['history'],[])
  self.assertEqual(self.chat.state('alice',None,self.tid)['thread']['messages'][1]['context']['sources'][0],saved)
  self.chat.update_document('alice',None,{**data,'expected_revision':3,'action':'restore'})
  self.send(request_id='request-after-restore',expected_count=4);self.assertEqual(self.model.calls[-1]['context']['documents'][0]['title'],'Updated study name')
  self.assertEqual(self.chat.download_document('alice',None,self.tid,did),raw)
 def test_upload_validation_and_revoked_project_context_deny_document_access(self):
  with self.assertRaises(ValueError):self.chat.attach('alice',None,dict(thread=self.tid,filename='bad.exe',content='eA=='))
  with self.assertRaises(ValueError):self.chat.attach('alice',None,dict(thread=self.tid,filename='bad.txt',content='not-base64'))
  uploaded,_=self.upload();self.send(projects=[dict(id='original',version=1)])
  with self.assertRaises(PermissionError):self.chat.document('alice',set(),self.tid,uploaded['id'])
  with self.assertRaises(PermissionError):self.chat.download_document('alice',set(),self.tid,uploaded['id'])

 def test_bounded_document_retrieval_includes_every_active_document_and_relevant_last_file(self):
  for i in range(5):
   text=('Long ordinary passage about workflow. '*80+'\n')*4+'\nDistinctive finding number '+str(i)
   self.chat.attach('alice',None,dict(thread=self.tid,filename=f'finding-{i}.txt',content=base64.b64encode(text.encode()).decode()))
  self.send(message='Explain distinctive finding number 4.')
  ctx=self.model.calls[-1]['context'];self.assertLessEqual(len(ctx['sources']),24);self.assertEqual(len({s['document_id'] for s in ctx['sources']}),5)
  self.assertTrue(any('Distinctive finding number 4' in s['content'] for s in ctx['sources']))

class ThoughtPartnerHTTPTests(unittest.TestCase):
 def test_routes_use_server_profile_and_csrf_without_requiring_active_project_headers(self):
  h=test_web.WebTests();h.setUp()
  try:
   h.server.model=h.server.thought_partner.model=Model()
   status,result=h.post('thought-chat-create',{'owner':'profile:sam','title':'Synthetic chat'});self.assertEqual(status,200);tid=result['id']
   headers={'Cookie':h.cookie,'X-CSRF-Token':h.csrf,'Content-Type':'application/json'}
   body=dict(thread=tid,request_id='http-00001',message='Explain a goal.',expected_count=0,projects=[],consent=True)
   h.conn.request('POST','/api/thought-chat-send',body=json.dumps(body),headers=headers);r=h.conn.getresponse();self.assertEqual(r.status,200);r.read()
   self.assertEqual(h.post('thought-chat-create',{}, {'X-CSRF-Token':''})[0],403)
   raw=io.BytesIO()
   with zipfile.ZipFile(raw,'w') as z:
    z.writestr('word/document.xml','<w:document xmlns:w="urn:w"><w:p><w:r><w:t>Fictional uploaded document.</w:t></w:r></w:p></w:document>')
    z.writestr('word/media/unused.bin',bytes(range(256))*1200)
   status,uploaded=h.post('thought-chat-attach',dict(thread=tid,filename='synthetic.docx',content=base64.b64encode(raw.getvalue()).decode()));self.assertEqual(status,200,uploaded)
   url='/api/thought-chat-download?thread='+tid+'&document='+uploaded['id'];h.conn.request('GET',url,headers={'Cookie':h.cookie});r=h.conn.getresponse();self.assertEqual(r.status,200);self.assertEqual(r.read(),raw.getvalue())
   h.post('profile',{'actor':'sam'});h.conn.request('GET',url,headers={'Cookie':h.cookie});r=h.conn.getresponse();self.assertEqual(r.status,403);r.read()
   h.conn.request('GET','/api/thought-chat?thread='+tid,headers={'Cookie':h.cookie});r=h.conn.getresponse();self.assertEqual(r.status,403);r.read()
   h.conn.request('GET','/thought-partner.js');r=h.conn.getresponse();self.assertEqual(r.status,200);self.assertIn(b'personal-chat-form',r.read())
  finally:h.tearDown()

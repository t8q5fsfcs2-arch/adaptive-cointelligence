from copy import deepcopy
from dataclasses import asdict
import io,json,os,unittest
from unittest.mock import patch
import test_domain_development as development
from workbench.tool_imports import MCPReader,PROVIDERS,locator
from workbench.core import Ref,StaleBasis

class Reader:
    calls=[]
    def __init__(self,endpoint,token,version):self.config=(endpoint,token,version)
    def read(self,tool,args):
        self.calls.append((self.config,tool,args));return {'content':[{'type':'text','text':'Imported fictional task map: interruption -> preserve draft -> resume. This is a synthetic transport test, not real research.'}]}

class ToolTests(unittest.TestCase):
    setUp=development.DevelopmentTests.setUp;tearDown=development.DevelopmentTests.tearDown
    start=development.DevelopmentTests.start;current=development.DevelopmentTests.current;draft=development.DevelopmentTests.draft;attach=development.DevelopmentTests.attach;send=development.DevelopmentTests.send;data=development.DevelopmentTests.data;save=development.DevelopmentTests.save
    def configure(self,p='figjam'):
        return self.sam.command('domain-tool-settings',dict(provider=p,expected=None,enabled=True,protocol='2025-11-25',tool=PROVIDERS[p]['tool'],arguments=PROVIDERS[p]['arguments']))
    def preview(self,p='figjam'):
        return self.sam.command('domain-tool-preview',{**self.data(), 'provider':p,'url':'https://www.figma.com/board/FICTIONAL/File?node-id=1-2' if p=='figjam' else 'https://www.figma.com/design/FICTIONAL/File?node-id=1-2'})
    def test_import_is_previewed_private_exact_and_does_not_evaluate_or_publish(self):
        self.save();before=self.sam.submissions.latest(self.current(self.sam,self.t));self.configure();self.sam.tool_imports.reader=Reader
        with patch.dict(os.environ,{self.sam.tool_imports.credential('figjam'):'synthetic-token'}):out=self.preview()
        self.assertEqual(self.sam.submissions.latest(self.current(self.sam,self.t)),before)
        self.assertEqual(Reader.calls[-1][2],{'fileKey':'FICTIONAL','nodeId':'1:2'})
        self.assertNotIn('Project',json.dumps(Reader.calls[-1][2]));self.assertNotIn('synthetic-token',json.dumps(out))
        self.sam.command('domain-tool-import',{**self.data(),'preview':out['preview'],'confirm':True})
        sub=self.sam.submissions.latest(self.current(self.sam,self.t));self.assertIn('fictional task map',sub['body']['text'])
        source=self.store.read(Ref(**sub['body']['primary_source']),self.sam.scopes)
        self.assertEqual(source['body']['tool_origin']['provider'],'figjam');self.assertIn('Selected text/structure',source['body']['tool_origin']['limits'])
        self.assertEqual(source['ref'].revision,sub['body']['source_refs'][0]['revision'])
        self.assertEqual(self.store.read(before['ref'],self.sam.scopes),before);self.assertEqual(self.model.calls,[])
        self.assertEqual(self.store.latest(self.req['ref'].id,self.sam.scopes),self.req)
    def test_setup_and_authorization_are_not_inferred_from_a_file_shortcut(self):
        with self.assertRaises(ValueError):self.preview()
        self.configure()
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(ValueError):self.preview()
        self.assertEqual(self.sam.tool_imports.state()[0]['status'],'Authorization needed')
    def test_write_tools_and_arbitrary_destinations_are_rejected(self):
        with self.assertRaises(ValueError):self.sam.command('domain-tool-settings',dict(provider='figma',expected=None,enabled=True,protocol='2025-11-25',tool='delete_document',arguments={}))
        for url in ['http://127.0.0.1/data','https://evil.example/board/X','https://user:password@www.figma.com/board/X']:
            with self.assertRaises(ValueError):locator('figjam',url)
    def test_other_domain_cannot_apply_private_tool_preview_and_setup_changes_invalidate_it(self):
        self.save();configured=self.configure();self.sam.tool_imports.reader=Reader
        with patch.dict(os.environ,{self.sam.tool_imports.credential('figjam'):'synthetic-token'}):out=self.preview()
        with self.assertRaises(PermissionError):self.lee.command('domain-tool-import',{**self.data(),'preview':out['preview'],'confirm':True})
        self.sam.command('domain-tool-settings',dict(provider='figjam',expected=configured['ref'],enabled=False,protocol='2025-11-25',tool='get_figjam',arguments={}))
        with self.assertRaises(StaleBasis):self.sam.command('domain-tool-import',{**self.data(),'preview':out['preview'],'confirm':True})

    def test_lucid_uses_its_document_fetch_read_operation_and_explicit_first_page(self):
        self.save();self.configure('lucid');self.sam.tool_imports.reader=Reader
        with patch.dict(os.environ,{self.sam.tool_imports.credential('lucid'):'synthetic-lucid-token'}):
            out=self.sam.command('domain-tool-preview',{**self.data(),'provider':'lucid','url':'https://lucid.app/lucidchart/11111111-2222-3333-4444-555555555555/edit'})
        self.assertEqual(Reader.calls[-1][1],'fetch');self.assertEqual(Reader.calls[-1][2]['page_index'],1)
        self.assertIn('Other pages/regions',out['limits']);self.assertNotIn('synthetic-lucid-token',json.dumps(out))

class WireTests(unittest.TestCase):
    def test_legacy_mcp_handshake_session_and_read_tool_are_used_without_project_context(self):
        calls=[]
        class Response(io.BytesIO):
            headers={'Content-Type':'application/json','Mcp-Session-Id':'synthetic-session'}
        class Opener:
            def open(self,request,timeout):
                body=json.loads(request.data);calls.append((body,dict(request.header_items())))
                result={'initialize':{'protocolVersion':'2025-11-25'},'notifications/initialized':{},'tools/list':{'tools':[{'name':'get_figjam'}]},'tools/call':{'content':[{'type':'text','text':'Selected fake board text'}]}}[body['method']]
                return Response(json.dumps({'jsonrpc':'2.0','id':body.get('id'),'result':result}).encode())
        with patch('workbench.tool_imports.build_opener',return_value=Opener()):result=MCPReader(PROVIDERS['figjam']['endpoint'],'test-secret','2025-11-25').read('get_figjam',{'fileKey':'X'})
        self.assertEqual([c[0]['method'] for c in calls],['initialize','notifications/initialized','tools/list','tools/call'])
        self.assertEqual(calls[-1][0]['params']['arguments'],{'fileKey':'X'});self.assertIn('Selected fake',result['content'][0]['text'])
    def test_stateless_sse_response_uses_request_metadata_and_blocks_unapproved_tools(self):
        calls=[]
        class Response(io.BytesIO):headers={'Content-Type':'text/event-stream'}
        class Opener:
            def open(self,request,timeout):
                body=json.loads(request.data);calls.append(body);result={'tools':[{'name':'get_document'}]} if body['method']=='tools/list' else {'content':[{'type':'text','text':'Fake diagram'}]}
                return Response(('data: '+json.dumps({'id':body['id'],'result':result})+'\n\n').encode())
        with patch('workbench.tool_imports.build_opener',return_value=Opener()):
            MCPReader(PROVIDERS['lucid']['endpoint'],'test-secret','2026-07-28').read('get_document',{'id':'fake'})
            with self.assertRaises(ValueError):MCPReader(PROVIDERS['lucid']['endpoint'],'test-secret','2026-07-28').read('delete_document',{})
        self.assertEqual(calls[0]['params']['_meta']['io.modelcontextprotocol/protocolVersion'],'2026-07-28')

class ToolHTTPTests(unittest.TestCase):
    setUp=development.DevelopmentHTTPTests.setUp
    tearDown=development.DevelopmentHTTPTests.tearDown
    def test_connections_and_missing_authorization_use_real_http_routes(self):
        status,thread=self.post('domain-chat-start',{});self.assertEqual(status,200)
        status,setup=self.post('domain-tool-settings',dict(provider='figjam',expected=None,enabled=True,protocol='2025-11-25',tool='get_figjam',arguments={'fileKey':'{file_key}','nodeId':'{node_id}'}));self.assertEqual(status,200,setup)
        with patch.dict(os.environ,{},clear=True):
            status,out=self.post('domain-tool-preview',dict(conversation=thread['conversation'],expected={'id':thread['id'],'revision':1},submission=None,provider='figjam',url='https://www.figma.com/board/FICTIONAL/File'))
        self.assertEqual(status,400);self.assertIn('authorization',out['error'].lower())

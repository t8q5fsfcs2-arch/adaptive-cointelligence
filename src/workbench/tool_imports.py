"""Explicit, read-only MCP imports into private domain submissions.

Transport credentials are supplied by the operator for this user's connection;
never reuse Codex's connector authorization or send project context to the server.
"""
from copy import deepcopy
from dataclasses import asdict
import base64
import hashlib
import json
import os
import re
import time
from urllib.parse import urlsplit,parse_qs
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from uuid import uuid4

from .core import StaleBasis
from .decisions import now,fingerprint
from .validation import reference

PROVIDERS={
 'figjam':dict(label='FigJam',endpoint='https://mcp.figma.com/mcp',tool='get_figjam',arguments={'fileKey':'{file_key}','nodeId':'{node_id}'}),
 'figma':dict(label='Figma',endpoint='https://mcp.figma.com/mcp',tool='get_metadata',arguments={'fileKey':'{file_key}','nodeId':'{node_id}'}),
 'lucid':dict(label='Lucid',endpoint='https://mcp.lucid.app/mcp/readonly',tool='fetch',arguments={'id':'{document_id}','page_index':1})}
READ_TOOLS={'fetch','lucid_fetch','get_figjam','get_metadata','get_design_context','get_screenshot','get_document','get_document_content','get_document_contents','get_document_pages','export_document','lucid_get_document','lucid_get_document_contents','lucid_get_document_pages','lucid_export_document'}
VERSIONS=('2025-11-25','2026-07-28')
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

class MCPReader:
    def __init__(self,endpoint,token,version):
        if not isinstance(token,str) or not token or len(token)>16000 or any(ord(c)<32 or ord(c)==127 for c in token):raise ValueError('The tool credential is invalid. Ask the operator to check its environment setting.')
        if endpoint not in {p['endpoint'] for p in PROVIDERS.values()} or version not in VERSIONS:raise ValueError('Choose an approved tool endpoint and protocol version')
        self.endpoint=endpoint;self.token=token;self.version=version;self.session=None;self.index=0
    def rpc(self,method,params=None,notification=False):
        self.index+=1;params=deepcopy(params or {})
        if self.version=='2026-07-28':params['_meta']={'io.modelcontextprotocol/protocolVersion':self.version,'io.modelcontextprotocol/clientCapabilities':{},'io.modelcontextprotocol/clientInfo':{'name':'intelligence-workbench','version':'1'}}
        body=dict(jsonrpc='2.0',method=method,params=params)
        if not notification:body['id']=self.index
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','Authorization':'Bearer '+self.token,'MCP-Protocol-Version':self.version}
        if self.session:headers['Mcp-Session-Id']=self.session
        try:
            with build_opener(NoRedirect).open(Request(self.endpoint,json.dumps(body).encode(),headers,method='POST'),timeout=30) as response:
                self.session=response.headers.get('Mcp-Session-Id',self.session)
                if notification:return {}
                content=response.headers.get('Content-Type','')
                if 'text/event-stream' in content:
                    data=[];size=0;started=time.monotonic();result=None
                    while time.monotonic()-started<30:
                        line=response.readline(2_000_001);size+=len(line)
                        if size>2_000_000:raise ValueError('The tool response is too large. Select a smaller section.')
                        if not line:break
                        if line.strip()==b'' and data:
                            try:message=json.loads(b'\n'.join(data))
                            except (ValueError,UnicodeError):raise ValueError('The MCP server returned unreadable event data.') from None
                            data=[]
                            if isinstance(message,dict) and message.get('id')==self.index:result=message;break
                        elif line.startswith(b'data:'):data.append(line[5:].strip())
                    if result is None:raise ValueError('The MCP response did not complete. The saved submission is unchanged.')
                    raw=json.dumps(result).encode()
                else:raw=response.read(2_000_001)
                if len(raw)>2_000_000:raise ValueError('The tool response is too large. Select a smaller section.')
        except HTTPError as error:
            raise ValueError('Tool authorization is required in Settings.' if error.code in (401,403) else 'The read-only tool request failed. Check the connection settings.') from None
        except (URLError,TimeoutError,OSError):raise ValueError('The tool did not respond. The saved submission is unchanged.') from None
        try:
            result=json.loads(raw)
            if not isinstance(result,dict) or result.get('id')!=self.index or 'error' in result or not isinstance(result.get('result'),dict):raise ValueError()
            return result['result']
        except (ValueError,KeyError,StopIteration,UnicodeError):raise ValueError('The MCP server returned an unsupported or failed response. Nothing was imported.') from None
    def start(self):
        if self.version=='2025-11-25':
            result=self.rpc('initialize',dict(protocolVersion=self.version,capabilities={},clientInfo={'name':'intelligence-workbench','version':'1'}))
            if result.get('protocolVersion')!=self.version:raise ValueError('The server requires a different MCP protocol version. Update Settings.')
            self.rpc('notifications/initialized',notification=True)
    def read(self,name,arguments):
        self.start();tools=self.rpc('tools/list').get('tools',[])
        tool=next((t for t in tools if isinstance(t,dict) and t.get('name')==name),None)
        if not tool or name.replace('-','_') not in READ_TOOLS:raise ValueError('The configured read tool is unavailable. Inspect its name and arguments in Settings.')
        result=self.rpc('tools/call',dict(name=name,arguments=arguments))
        if result.get('isError'):raise ValueError('The tool could not read this selection. Check its link, permissions and arguments.')
        return result

def locator(provider,value):
    if not isinstance(value,str) or len(value)>2000:raise ValueError('Choose a file or page link under 2,000 characters')
    u=urlsplit(value);allowed={'figma.com','www.figma.com'} if provider in ('figma','figjam') else {'lucid.app','lucidchart.com','www.lucidchart.com'}
    if u.scheme!='https' or u.hostname not in allowed or u.username or u.password or u.fragment or u.port not in (None,443):raise ValueError('Use a direct HTTPS file link for the selected tool, without credentials or fragments')
    parts=u.path.strip('/').split('/');query=parse_qs(u.query)
    if provider in ('figma','figjam'):
        kind='board' if provider=='figjam' else 'design'
        if len(parts)<2 or parts[0]!=kind or not re.fullmatch('[A-Za-z0-9]+',parts[1]):raise ValueError('Choose a '+PROVIDERS[provider]['label']+' file link')
        node=query.get('node-id',['0:1'])[0]
        if len(node)>100 or not re.fullmatch(r'[A-Za-z0-9:_.-]+',node):raise ValueError('Use a valid file or node link')
        return dict(file_key=parts[1],node_id=node.replace('-',':'),document_id='')
    ids=[p for p in parts if re.fullmatch('[0-9a-fA-F-]{32,36}',p)]
    if not ids:raise ValueError('Choose a Lucid document link containing its document ID')
    return dict(document_id=ids[0],file_key='',node_id='')

def content_text(result):
    content=result.get('content',[])
    if not isinstance(content,list) or any(not isinstance(v,dict) for v in content):raise ValueError('The tool returned unsupported content; nothing was imported.')
    parts=[v['text'] for v in content if v.get('type')=='text' and isinstance(v.get('text'),str)]
    if result.get('structuredContent') is not None:parts.append(json.dumps(result['structuredContent'],ensure_ascii=False,indent=2))
    value='\n\n'.join(parts)
    if not value.strip():raise ValueError('This tool returned no readable text. Upload a PDF export for visual evaluation.')
    if len(value)>120000:raise ValueError('The selection is too large. Choose a smaller section; nothing was truncated.')
    return value

class ToolImports:
    reader=MCPReader
    def __init__(self,w):self.w=w;self.store=w.store
    def identity(self,provider):
        if provider not in PROVIDERS:raise ValueError('Choose FigJam, Figma or Lucid')
        owner=self.w.principal_id or self.w.actor
        return 'TOOLCON-'+hashlib.sha256((owner+'|'+provider).encode()).hexdigest()[:20]
    def connection(self,provider):
        id=self.identity(provider)
        return self.store.latest(id,{self.w.domains.scope}) if self.store.db.execute('SELECT 1 FROM records WHERE id=?',(id,)).fetchone() else None
    def credential(self,provider):
        owner=self.w.principal_id or self.w.actor
        key=self.w.actor.upper() if not self.w.principal_id else hashlib.sha256(owner.encode()).hexdigest()[:12].upper()
        return 'WB_'+('FIGMA' if provider in ('figma','figjam') else 'LUCID')+'_'+key+'_TOKEN'
    def state(self):
        if not self.w.domains.key:return []
        result=[]
        for provider,p in PROVIDERS.items():
            r=self.connection(provider);b=r['body'] if r else {}
            result.append(dict(provider=provider,label=p['label'],ref=asdict(r['ref']) if r else None,endpoint=p['endpoint'],tool=b.get('tool',p['tool']),arguments=b.get('arguments',p['arguments']),protocol=b.get('protocol','2025-11-25'),credential_ref=self.credential(provider),credential_available=bool(os.environ.get(self.credential(provider))),export_enabled=b.get('export_enabled',False),enabled=b.get('enabled',False),status='Ready to test' if b.get('enabled') and os.environ.get(self.credential(provider)) else 'Authorization needed' if b.get('enabled') else 'Not configured'))
        return result
    def save(self,data):
        self.w.domains.author();p=data.get('provider');old=self.connection(p)
        if data.get('expected')!=(asdict(old['ref']) if old else None):raise StaleBasis('This tool connection changed. Reopen Settings.')
        tool=data.get('tool');args=data.get('arguments');version=data.get('protocol');enabled=data.get('enabled')
        if not isinstance(tool,str) or tool.replace('-','_') not in READ_TOOLS or not isinstance(args,dict) or len(json.dumps(args))>6000 or version not in VERSIONS or type(enabled) is not bool:raise ValueError('Choose an approved read tool, bounded JSON arguments and a supported MCP version')
        if re.search(r'\"[^\"]*(?:token|secret|password|authorization|api.?key|cookie)[^\"]*\"\s*:',json.dumps(args),re.I):raise ValueError('Keep credentials in the user-specific environment setting, never in tool arguments')
        export_enabled=data.get('export_enabled',old['body'].get('export_enabled',False) if old else False)
        if type(export_enabled) is not bool or export_enabled and p not in ('figma','figjam'):raise ValueError('Creation is an explicit Figma or FigJam capability')
        body=dict(owner=self.w.actor,principal=self.w.principal_id,provider=p,tool=tool,arguments=args,protocol=version,enabled=enabled,export_enabled=export_enabled,at=now())
        ref=self.store.put(self.identity(p),'domain-tool-connection',self.w.domains.scope,body,old['ref'].revision if old else 0)
        return dict(ref=asdict(ref),message='Import connection saved. Authorization and a successful read are still required.')
    def preview(self,data):
        thread,draft,sub=self.w.submissions.checked(data);provider=data.get('provider');r=self.connection(provider);b=r['body'] if r else {}
        if not b.get('enabled'):raise ValueError('Configure this import connection in Settings → Integrations first.')
        token=os.environ.get(self.credential(provider))
        if not token:raise ValueError('This Workbench connection needs authorization in Settings. Codex connections and file shortcuts do not authorize the Workbench.')
        values=locator(provider,data.get('url'));args=json.loads(json.dumps(b['arguments']))
        def expand(value):
            if isinstance(value,str):
                for k,v in values.items():value=value.replace('{'+k+'}',v)
                return value
            if isinstance(value,list):return [expand(v) for v in value]
            if isinstance(value,dict):return {k:expand(v) for k,v in value.items()}
            return value
        args=expand(args)
        # No project brief, chat, requirements or research evidence is sent externally.
        result=self.reader(PROVIDERS[provider]['endpoint'],token,b['protocol']).read(b['tool'],args);text=content_text(result)
        if token in text:raise ValueError('The tool returned credential material. Nothing was imported.')
        with self.store.transaction():
            fresh,_,_=self.w.submissions.checked(data)
            if self.connection(provider)['ref']!=r['ref']:raise StaleBasis('The tool connection changed during retrieval. Inspect the current setup.')
            ref=self.store.put('TOOLPRE-'+uuid4().hex[:12],'domain-tool-preview',self.w.domains.scope,dict(owner=self.w.actor,principal=self.w.principal_id,conversation=thread['ref'].id,connection=asdict(r['ref']),provider=provider,url=('https://www.figma.com/'+('board/' if provider=='figjam' else 'design/')+values['file_key']+'?node-id='+values['node_id'] if provider!='lucid' else 'https://lucid.app/lucidchart/'+values['document_id']+'/edit'),tool=b['tool'],arguments=args,text=text,digest=fingerprint(result),at=now(),basis=data,limits='Selected text/structure response only. Other pages/regions, images, live behavior and linked files were not reviewed. Not evidence validation.'))
            self.store.depend(ref,r['ref'],self.w.scopes)
        return dict(preview=asdict(ref),provider=provider,title=PROVIDERS[provider]['label']+' selection',text=text,at=now(),limits='Selected text/structure response only. Other pages/regions are not automatically retrieved. Use a PDF export for visual evaluation.')
    def apply(self,data):
        with self.store.transaction():
            thread,_,old=self.w.submissions.checked(data);preview=self.store.read(reference(data.get('preview')),{self.w.domains.scope});b=preview['body']
            if preview['kind']!='domain-tool-preview' or b['owner']!=self.w.actor or b['principal']!=self.w.principal_id or b['conversation']!=thread['ref'].id:raise PermissionError('Import a preview from your own workbench')
            if data.get('confirm') is not True:raise ValueError('Review the exact snapshot before importing')
            if self.connection(b['provider'])['ref']!=reference(b['connection']):raise StaleBasis('The connection changed. Retrieve a new preview.')
            out=self.w.submissions.import_file({**data,'filename':PROVIDERS[b['provider']]['label']+' snapshot.txt','content':base64.b64encode(b['text'].encode()).decode(),'confirm_replace':True})
            imported_thread=self.store.latest(thread['ref'].id,{self.w.domains.scope})
            imported_sub=self.w.submissions.latest(imported_thread)
            source=self.store.read(reference(imported_sub['body']['primary_source']),self.w.scopes)
            body={**source['body'],'tool_origin':{k:b[k] for k in ('provider','url','tool','arguments','digest','at','limits')}}
            ref=self.store.put(source['ref'].id,'source',source['scope'],body,source['ref'].revision)
            # Keep ordinary source/submission versions exact after adding provenance.
            thread=self.store.latest(thread['ref'].id,{self.w.domains.scope});draft=self.w.domain_chat.draft(thread)
            draft_ref=self.store.put(draft['ref'].id,'contribution-draft',draft['scope'],{**draft['body'],'source_refs':[asdict(ref) if v['id']==ref.id else v for v in draft['body']['source_refs']]},draft['ref'].revision)
            self.w.domain_chat.update(thread,focus_source=asdict(ref))
            sub=self.w.submissions.latest(thread);sb={k:sub['body'][k] for k in ('text','source_refs','implication_refs','primary_source','review_mode')};sb.update(source_refs=[asdict(ref)],primary_source=asdict(ref))
            saved=self.w.submissions.persist(thread,self.store.read(draft_ref,self.w.scopes),sub,sb)
            self.store.depend(ref,preview['ref'],self.w.scopes)
            return {**saved,'message':'Selected tool snapshot imported privately. Review it, then evaluate the submission.'}

"""Project initiation, historical work requests, and external work-tool bindings.

These records coordinate people. They do not approve requirements, share private
working notes, execute MCP tools, or imply external content has been ingested.
"""
from dataclasses import asdict
from urllib.parse import urlsplit, parse_qsl, urlencode
from uuid import uuid4
import re

from .core import StaleBasis
from .decisions import SCOPE, now, DecisionBlocked
from .validation import reference
from .bridge import text, BOARDS

RECIPIENTS={'sam':'Research','lee':'Design'}
AUTHORS={'priya','sam','lee','alex'}
MCP_ENDPOINT='https://mcp.figma.com/mcp'
MCP_DOCS='https://developers.figma.com/docs/figma-mcp-server/remote-server-installation/'
TOOL_FIELDS={'research_figjam':('sam','board'),'design_figma':('lee','design'),'design_figjam':('lee','board')}


def figma_link(value,kind):
    if value=='':return ''
    if not isinstance(value,str) or len(value)>2000:raise ValueError('Provide a Figma file link under 2,000 characters')
    u=urlsplit(value)
    if u.scheme!='https' or u.hostname not in {'figma.com','www.figma.com'} or u.username or u.password or u.port not in (None,443) or u.fragment:
        raise ValueError('Use an HTTPS figma.com file link without credentials or fragments')
    # Board and Design identity are explicit; arbitrary destinations and Make files are not interchangeable.
    match=re.fullmatch(r'/'+kind+r'/([A-Za-z0-9]+)(/[^?#]*)?/?',u.path)
    if not match:raise ValueError('Use a FigJam board link' if kind=='board' else 'Use a Figma Design file link')
    params=[(k,v) for k,v in parse_qsl(u.query) if k in {'node-id','page-id'}]
    if len(params)>2 or any(len(v)>100 or not re.fullmatch(r'[A-Za-z0-9:_.-]+',v) for _,v in params):raise ValueError('Use a file or node link without extra parameters')
    return 'https://www.figma.com/'+kind+'/'+match[1]+('?' + urlencode(params) if params else '')


class ProjectFlow:
    def __init__(self,w):self.w=w;self.store=w.store;self.actor=w.actor
    def recipients(self):
        return [dict(actor=a,domain=d['key'],label=d['label']) for d in self.w.domain_knowledge.definitions() for a in d['members']]
    def recipient_domain(self,r):
        return r['body'].get('recipient_domain') or {'sam':'research','lee':'design'}.get(r['body']['recipient'])
    def requests(self):return self.w.latest_records('project-work-request')
    def current(self,raw):
        r=self.store.latest(reference(raw).id,{SCOPE})
        if r['kind']!='project-work-request' or asdict(r['ref'])!=raw:raise StaleBasis('This work request changed. Reload before responding')
        return r
    def changed(self,r):
        b=r['body'];changes=[]
        for raw in b['requirement_refs']:
            current=self.store.latest(raw['id'],{SCOPE})['ref']
            if asdict(current)!=raw:changes.append(dict(previous=raw,current=asdict(current)))
        for raw in b['packet_refs']:
            p=self.store.resolve_packet(raw['id'],raw['revision'],{SCOPE})
            for change in p.get('changed_refs',[]):
                old=self.store.read(reference(change['previous']),{SCOPE});current=self.store.read(reference(change['current']),{SCOPE})
                if old['kind']=='intake-case' and old['body'].get('snapshot')==current['body'].get('snapshot'):continue
                changes.append(change)
        return changes
    def seed_legacy_request(self,data):
        """Build synthetic historical records for offline demos/tests, never a workspace command."""
        if self.actor not in self.w.bridge.participants():raise PermissionError('Use a project sponsor, Research, Design or requirement-owner role')
        receiving=data.get('recipient_domain') or {'sam':'research','lee':'design'}.get(data.get('recipient'))
        if not any(r['actor']==data.get('recipient') and r['domain']==receiving for r in self.recipients()) or (data['recipient']==self.actor and receiving==self.w.domains.key):raise ValueError('Choose an assigned user in another domain to receive the work request')
        with self.store.transaction():
            packets=data.get('packet_refs',[])
            if not isinstance(packets,list) or not 1<=len(packets)<=5 or len({(reference(p).id,reference(p).revision) for p in packets})!=len(packets):raise ValueError('Choose one to five distinct published packets')
            basis=set()
            for p in packets:
                p=reference(p);resolved=self.store.resolve_packet(p.id,p.revision,{SCOPE});basis.update(reference(r) for r in resolved['refs'])
            reqs=data.get('requirement_refs',[])
            if not isinstance(reqs,list) or len(reqs)>20 or len({reference(r).id for r in reqs})!=len(reqs):raise ValueError('Choose at most twenty distinct requirements')
            for raw in reqs:
                r=self.store.latest(reference(raw).id,{SCOPE})
                if r['kind']!='requirement' or asdict(r['ref'])!=raw:raise StaleBasis('Choose current project requirements')
                basis.add(r['ref'])
            boards=data.get('boards') or (['all-teams'] if receiving not in {'research','design'} or self.w.domains.key not in {None,'research','design'} else ['research-design'] if self.actor in RECIPIENTS else ['business-research' if data['recipient']=='sam' else 'business-design'])
            if not isinstance(boards,list) or not 1<=len(boards)<=len(BOARDS) or any(b not in BOARDS for b in boards) or len(set(boards))!=len(boards):raise ValueError('Choose distinct issue boards for this domain brief')
            guidance=data.get('requirement_guidance',[])
            if not isinstance(guidance,list) or len(guidance)!=len(reqs):raise ValueError('Explain the local application and expected evidence for each selected requirement')
            for raw in reqs:
                entries=[g for g in guidance if isinstance(g,dict) and g.get('ref')==raw]
                if len(entries)!=1:raise ValueError('Keep one exact requirement link per domain interpretation')
                text(entries[0],'local_application',4000);text(entries[0],'expected_evidence',4000)
            r=self.store.put('WORK-'+uuid4().hex[:12],'project-work-request',SCOPE,dict(title=text(data,'title',200),objective=text(data,'objective',4000),expected_output=text(data,'expected_output',4000),boundaries=text(data,'boundaries',4000,required=False),local_context=text(data,'local_context',6000),requirement_guidance=[dict(ref=g['ref'],local_application=text(g,'local_application',4000),expected_evidence=text(g,'expected_evidence',4000)) for g in guidance],boards=boards,translation_status='human-authored interpretation; governing requirements unchanged',recipient=data['recipient'],recipient_domain=receiving,requested_by=self.actor,status='requested',packet_refs=packets,requirement_refs=reqs,basis=[asdict(r) for r in sorted(basis)],at=now()))
            for raw in basis:self.store.depend(r,raw,{SCOPE})
        return dict(id=r.id,message='Working brief sent with exact published context. Governing requirements stay unchanged.')
    def respond(self,data):
        with self.store.transaction():
            r=self.current(data.get('expected'));b=r['body'];action=data.get('action')
            if action=='accept':
                if self.actor!=b['recipient'] or self.recipient_domain(r)!=self.w.domains.key:raise PermissionError('Only the assigned domain can accept this work request')
                if b['status']!='requested':raise DecisionBlocked('This work request has already been accepted or closed')
                if self.changed(r):raise StaleBasis('The assignment context changed. Ask the requester for a current work request')
                b.update(status='accepted',accepted_by=self.actor,accepted_at=now())
            elif action=='cancel':
                if self.actor!=b['requested_by']:raise PermissionError('Only the requester can cancel this work request')
                if b['status']=='cancelled':raise DecisionBlocked('This work request is already cancelled')
                b.update(status='cancelled',cancellation_reason=text(data,'note',2000))
            else:raise ValueError('Choose accept or cancel. A published finding is not the same as accepting an assignment')
            b.update(updated_by=self.actor,updated_at=now())
            ref=self.store.put(r['ref'].id,r['kind'],SCOPE,b,r['ref'].revision)
            for raw in b['basis']:self.store.depend(ref,reference(raw),{SCOPE})
        return dict(id=ref.id,message='Work request '+b['status']+'. No requirement approval changed.')
    def start(self,data):
        with self.store.transaction():
            r=self.current(data.get('expected'));b=r['body']
            if self.actor!=b['recipient'] or self.recipient_domain(r)!=self.w.domains.key:raise PermissionError('Open work assigned to your domain')
            if b['status']=='cancelled':raise DecisionBlocked('This work request was cancelled')
            if self.changed(r):raise StaleBasis('The assignment basis changed. Ask the requester to issue current context')
            if b['status']=='requested':
                self.respond(dict(expected=asdict(r['ref']),action='accept'));r=self.store.latest(r['ref'].id,{SCOPE});b=r['body']
            for t in self.w.domain_chat.threads():
                if (t['body'].get('work_request') or {}).get('id')==r['ref'].id:
                    draft=self.w.domain_chat.draft(t)
                    if not draft['body'].get('work_request'):self.w.domains.save({**draft['body'],'expected':asdict(draft['ref']),'work_request':asdict(r['ref'])})
                    return dict(id=t['body']['draft_id'],message='Assigned work opened.')
            inputs=[raw for raw in b['basis'] if self.store.read(reference(raw),{SCOPE})['kind']=='contribution']
            return self.w.domain_chat.start(dict(title=b['title'],work_request=asdict(r['ref']),requirement_ids=[x['id'] for x in b['requirement_refs']],input_refs=inputs[:5]))
    def tools(self):
        records=self.w.latest_records('project-work-tools');r=records[0] if records else None
        return dict(ref=asdict(r['ref']) if r else None,links=r['body']['links'] if r else {k:'' for k in TOOL_FIELDS},mcp=dict(endpoint=MCP_ENDPOINT,status='client-authorization-required',execution_available=False,docs=MCP_DOCS,config={'mcpServers':{'figma':{'url':MCP_ENDPOINT}}}))
    def save_tools(self,data):
        allowed=set(TOOL_FIELDS) if self.actor=='priya' or self.w.settings_admin else {k for k,(actor,_) in TOOL_FIELDS.items() if actor==self.actor}
        if not allowed:raise PermissionError('Only the sponsor or the owning domain can configure work tools')
        with self.store.transaction():
            current=self.tools()
            if data.get('expected')!=current['ref']:raise StaleBasis('Work tools changed. Reopen Settings before saving')
            patch=data.get('links')
            if not isinstance(patch,dict) or not patch or any(k not in allowed for k in patch):raise PermissionError('Configure only your domain work tools')
            links={**current['links'],**{k:figma_link(v,TOOL_FIELDS[k][1]) for k,v in patch.items()}}
            ref=self.store.put('PROJECT-WORK-TOOLS','project-work-tools',SCOPE,dict(links=links,author=self.actor,principal=self.w.principal_id,at=now(),previous=current['ref'],note='File links only. No content import, MCP authorization, external write or permission change.'),current['ref']['revision'] if current['ref'] else 0)
        return dict(ref=asdict(ref),message='Work-tool links saved. MCP authorization and content synchronization remain separate.')
    def pending(self,requirement_ids):
        ids=set(requirement_ids)
        return [r for r in self.w.bridge.issues() if r['body']['status']!='resolved' and (ids.intersection(x['id'] for x in r['body']['requirement_refs']) or (r['body']['route']=='intent' and not r['body']['requirement_refs']))]
    def state(self):
        released=self.w.latest_records('contribution')
        requests=[{**r,'changed':self.changed(r),'published_outputs':[dict(ref=asdict(o['ref']),title=o['body']['title'],packet=o['body'].get('packet')) for o in released if (o['body'].get('work_request') or {}).get('id')==r['ref'].id]} for r in self.requests()]
        intents=self.w.latest_records('intent');contexts=self.w.latest_records('project-context')
        return dict(requests=requests,tools=self.tools(),brief=dict(intent=intents[0] if intents else None,context=contexts[0] if contexts else None),can_request=False,recipients=[])

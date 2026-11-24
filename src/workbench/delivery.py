"""Exact-version delivery preparation and export; never simulates external writes."""
from dataclasses import asdict
from copy import deepcopy
import hashlib
import html
import json
from urllib.parse import quote
from .core import Ref, StaleBasis
from .decisions import SCOPE, now, fingerprint
from .intake import PRIVATE
from .validation import optional, reference
from .assessment_context import assessment_context, context_changes

TYPES={'jira':('Story','Task','Epic','Requirement'),'ado':('User Story','Product Backlog Item','Requirement','Feature','Epic','Task')}
MAPPING=[dict(source='Project',jira='Existing Jira project key',ado='Existing ADO project',rule='The initiative is the destination context. An issue never creates a project.'),dict(source='Requirement / human-edited story draft',jira='Story, Task or configured issue type',ado='User Story (Agile), Product Backlog Item (Scrum), Requirement (CMMI), or configured type',rule='Pin the requirement version. Confirm the target process and required fields.'),dict(source='Acceptance criteria',jira='Description by default; map a custom field only after metadata discovery',ado='Microsoft.VSTS.Common.AcceptanceCriteria when supported by the chosen type',rule='Keep exact wording and source references; verify applicability.'),dict(source='Requirement drawers',jira='Labels or a reviewed Epic mapping',ado='Tags or a reviewed Feature mapping',rule='Categories are not automatically converted into commitments or tickets.'),dict(source='Goals and KPIs',jira='Linked rationale and measurement references',ado='Linked rationale and measurement references',rule='Remain first-class Workbench objects. Create additional work items only by explicit mapping.'),dict(source='Shared issue / decision',jira='Source links in a reviewed change set',ado='Source links in a reviewed change set',rule='A discussion is not a bug or story. An approved requirement change may inform a separately authorized ticket update.')]

def adf(text):
    return dict(type='doc',version=1,content=[dict(type='paragraph',content=[dict(type='text',text=line)]) for line in text.split('\n') if line])

class Delivery:
    def __init__(self,w):self.w=w;self.store=w.store
    def safe_record(self, record):
        """Hide copied assessment text if its shared source access was withdrawn.

        The canonical preview remains immutable. This is a bounded delivery
        projection, not a universal historical-record revocation policy.
        """
        if record['kind']!='delivery-draft' or 'assessment_context' not in record['body']:
            return record
        try:
            for raw in record['body'].get('assessment_basis',[]):
                self.store.read(reference(raw), {SCOPE})
        except (ValueError, PermissionError):
            safe=deepcopy(record);body=safe['body']
            limitation='Assessment context is unavailable in this access scope. Prepare a fresh preview before export.'
            body['assessment_context']=dict(access_limited=True,limitation=limitation)
            body['assessment_basis']=[]
            for key in ('assessment_notes','assessment_limits'):
                body.pop(key,None)
            body['items']=[{**{key:item[key] for key in ('source','title','method','endpoint','content_type','idempotency_key') if key in item},
                            'warnings':[limitation], 'assessment_access_limited':True} for item in body.get('items',[])]
            return safe
        return record
    def assessment_changes(self, body):
        if 'assessment_context' not in body:
            return []
        try:
            return context_changes(self.w, body['assessment_context'])
        except (ValueError, PermissionError):
            return [dict(reason='The recorded assessment basis is unavailable or changed; prepare a fresh preview.')]
    def state(self):
        drafts=[]
        for r in self.w.latest_records('delivery-draft'):
            r=self.safe_record(r)
            changed=[]
            for raw in r['body']['requirements']:
                latest=self.store.latest(raw['id'],{SCOPE})['ref']
                if latest!=reference(raw):changed.append(dict(previous=raw,current=asdict(latest)))
            changed.extend(self.assessment_changes(r['body']))
            drafts.append({**r,'changed':changed,
                'assessment_limitation':None if 'assessment_context' in r['body'] else 'Legacy preview: no recorded assessment basis was captured. Prepare a fresh preview to include it.'})
        return dict(mode='preview-and-export',connected=False,mapping=MAPPING,drafts=drafts,types=TYPES,
                    write_status='No Jira/ADO connector is configured. Nothing is sent by preparing or exporting.')
    def prepare(self,data):
        if self.w.actor not in ('priya','alex'):raise PermissionError('The sponsor or requirement owner prepares delivery drafts')
        target=data.get('target');kind=data.get('work_item_type');destination=optional(data,'destination');parent=optional(data,'parent')
        if target not in TYPES or kind not in TYPES[target]:raise ValueError('Choose a supported destination and work item type')
        raw=data.get('requirements')
        if not isinstance(raw,list) or not 1<=len(raw)<=50:raise ValueError('Select between one and fifty current requirements')
        refs=[reference(r) for r in raw]
        if len(set(refs))!=len(refs):raise ValueError('Select each requirement once')
        with self.store.transaction():
            trace=assessment_context(self.w, refs)
            items=[]
            for ref in refs:
                r=self.store.read(ref,{SCOPE});b=r['body']
                if r['kind']!='requirement' or self.store.latest(ref.id,{SCOPE})['ref']!=ref:raise StaleBasis('Reopen the current requirement versions before preparing delivery')
                goals=[self.store.read(reference(g),{SCOPE}) for g in b.get('goal_refs',[])]
                notes='\n'.join([b['text'],'','Acceptance criteria:',b.get('acceptance_criteria','') or 'Not yet defined','','Conditions:',b.get('conditions',''),'','Rationale:',b.get('rationale',''),'','Workbench requirement: '+ref.label(),'Drawer: '+b.get('drawer',''),'Goals: '+', '.join(g['body'].get('title',g['ref'].id) for g in goals)])
                title=b.get('title') or b['text'][:120]
                if target=='jira':
                    payload={'fields':dict(project={'key':destination or '<project-key>'},issuetype={'name':kind},summary=title,description=adf(notes),labels=['workbench'])}
                    if parent:payload['fields']['parent']={'key':parent}
                    endpoint='/rest/api/3/issue';content_type='application/json'
                else:
                    payload=[dict(op='add',path='/fields/System.Title',value=title),dict(op='add',path='/fields/System.Description',value='<p>'+html.escape(notes).replace('\n','<br>')+'</p>')]
                    if kind in ('User Story','Product Backlog Item','Requirement'):
                        payload.append(dict(op='add',path='/fields/Microsoft.VSTS.Common.AcceptanceCriteria',value=html.escape(b.get('acceptance_criteria','')).replace('\n','<br>')))
                    if parent:payload.append(dict(op='add',path='/relations/-',value=dict(rel='System.LinkTypes.Hierarchy-Reverse',url=parent)))
                    endpoint='/'+quote(destination or '<project>',safe='')+'/_apis/wit/workitems/$'+quote(kind,safe='')+'?api-version=7.1';content_type='application/json-patch+json'
                warnings=[]
                if b.get('status')!='approved':warnings.append('Requirement is not approved; this is a provisional draft.')
                if not b.get('acceptance_criteria'):warnings.append('Acceptance criteria are missing.')
                if not destination:warnings.append('Destination is not configured.')
                if any(self.store.latest(g['ref'].id,{SCOPE})['ref']!=g['ref'] for g in goals):warnings.append('A linked goal has a newer version; review the requirement basis.')
                requirement_trace=next(value for value in trace['requirements'] if value['requirement']==asdict(ref))
                implementation=requirement_trace['uses'].get('implementation',{})
                if implementation.get('status')=='not-assessed':warnings.append('Implementation suitability has not been assessed; this local draft does not establish readiness.')
                if implementation.get('status') in {'needs-work','needs-reassessment'}:warnings.append('The recorded implementation assessment needs work or reassessment. Preserve its gaps and limits in review.')
                items.append(dict(source=asdict(ref),title=title,requirement=b['text'],acceptance_criteria=b.get('acceptance_criteria',''),goal_refs=b.get('goal_refs',[]),measure_refs=b.get('measure_refs',[]),drawer_id=b.get('drawer_id'),warnings=warnings,
                    assessment_context=deepcopy(requirement_trace),
                    method='POST',endpoint=endpoint,content_type=content_type,payload=payload,
                    idempotency_key=hashlib.sha256((target+'|'+destination+'|'+kind+'|'+ref.label()+'|'+parent).encode()).hexdigest()))
            specification=dict(target=target,work_item_type=kind,destination=destination,parent=parent,requirements=[asdict(r) for r in refs],items=items,
                assessment_context=trace,assessment_basis=deepcopy(trace['basis']),assessment_boundary=trace['boundary'])
            digest=fingerprint(specification);id='DELIVERY-'+self.w.actor+'-'+digest[:16]
            existing=self.store.db.execute('SELECT 1 FROM records WHERE id=?',(id,)).fetchone()
            if existing:
                # Scope is checked even for a repeated semantic preparation.
                self.store.latest(id,self.w.scopes)
                return dict(id=id,message='This exact delivery preview is already saved.')
            ref=self.store.put(id,'delivery-draft',PRIVATE if self.w.actor=='priya' else SCOPE,
                dict(**specification,status='preview-only',connector='not-connected',created_by=self.w.actor,at=now(),fingerprint=digest,external_receipts=[],boundary='Export is not external authorization or a delivery receipt.'))
            for basis in {*(reference(raw) for raw in trace['basis']),*refs}:self.store.depend(ref,basis,self.w.scopes)
            return dict(id=id,message='Delivery preview saved. Nothing was sent to Jira or Azure DevOps.')
    def export(self,data):
        ref=reference(data.get('expected'));r=self.store.read(ref,self.w.scopes)
        if r['kind']!='delivery-draft':raise ValueError('Choose a delivery preview')
        if self.store.latest(ref.id,self.w.scopes)['ref']!=ref:raise StaleBasis('Reopen the current delivery preview')
        for raw in r['body']['requirements']:
            if self.store.latest(raw['id'],{SCOPE})['ref']!=reference(raw):raise StaleBasis('A requirement changed. Prepare a fresh delivery preview before exporting.')
        if self.assessment_changes(r['body']):
            raise StaleBasis('The assessment, evidence or Business Intent basis changed. Prepare a fresh delivery preview before exporting.')
        return dict(message='Payload exported locally; no external items were created.',export=deepcopy(r['body']))

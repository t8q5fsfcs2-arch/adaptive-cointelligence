"""One private, durable conversation surface over the Research/Design lifecycle."""
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
import json
import re
from uuid import uuid4

from .core import StaleBasis
from .decisions import SCOPE,fingerprint,now
from .domain import DomainAgent,GUARDRAILS,txt,shared_input_references
from .design_visual import VisualAgent,INSTRUCTIONS as VISUAL_INSTRUCTIONS
from .agent_runs import AgentRun,execution_mode
from .model_provider import ModelUnavailable
from .validation import reference
from . import conversation_findings, domain_alignment, evidence_catalog, card_placement, brief_development

TEXT_BATCH=24000

class DomainChat:
    def __init__(self,workspace):
        self.w=workspace;self.store=workspace.store;self.domain=workspace.domains;self.model=self.domain.model
    def owned(self,raw,current=True):
        self.domain.author();ref=reference(raw);r=self.store.read(ref,{self.domain.scope})
        if r['kind']!='domain-conversation' or r['body']['owner']!=self.w.actor:raise PermissionError('Open your domain conversation')
        if current and self.store.latest(ref.id,{self.domain.scope})['ref']!=ref:raise StaleBasis('This conversation changed. Reload to continue; your message is still in the composer.')
        return r
    def threads(self):
        return [r for r in self.w.latest_records('domain-conversation') if r['scope']==self.domain.scope and r['body']['owner']==self.w.actor] if self.domain.key else []
    def turns(self,thread):
        return sorted([r for r in self.w.latest_records('domain-chat-turn') if r['scope']==self.domain.scope and r['body']['conversation']==thread['ref'].id],key=lambda r:r['body']['at'])
    def draft(self,thread):return self.store.latest(thread['body']['draft_id'],{self.domain.scope})
    def update(self,thread,**patch):
        ref=self.store.put(thread['ref'].id,'domain-conversation',self.domain.scope,{**thread['body'],**patch,'at':now()},thread['ref'].revision)
        return self.store.read(ref,{self.domain.scope})
    def turn(self,thread,role,message,**extra):
        return self.store.put('TURN-'+uuid4().hex[:12],'domain-chat-turn',self.domain.scope,dict(conversation=thread['ref'].id,owner=self.w.actor,role=role,message=message,at=now(),**extra))
    def defaults(self):
        requirements=self.w.latest_records('requirement')
        # Project scope is explicit, not a semantic-match assertion. Large scopes need selection.
        return requirements if len(requirements)<=20 else []
    def start(self,data):
        self.domain.author()
        with self.store.transaction():
            if data.get('draft'):
                draft=self.domain.draft(data['draft'])
                for old in self.threads():
                    if old['body']['draft_id']==draft['ref'].id:return dict(conversation=asdict(old['ref']),id=draft['ref'].id,message='Conversation opened.')
            else:
                title=txt(data,'title',200) or 'New '+self.domain.profile()['config']['label']+' work'
                reqs=[self.store.latest(id,{SCOPE}) for id in data['requirement_ids']] if data.get('work_request') else self.defaults();ids={r['ref'].id for r in reqs}
                inputs=[r for r in self.w.latest_records('contribution') if r['body'].get('domain_key')!=self.domain.key and ids.intersection(x['id'] for x in r['body'].get('requirement_refs',[]))][:5]
                if data.get('work_request'):
                    task=self.w.project_flow.current(data['work_request'])
                    if task['body']['recipient']!=self.w.actor or self.w.project_flow.recipient_domain(task)!=self.domain.key or task['body']['status']!='accepted':raise PermissionError('Accept work assigned to your domain first')
                    if self.w.project_flow.changed(task):raise StaleBasis('The work request context changed')
                    if data.get('requirement_ids')!=[r['id'] for r in task['body']['requirement_refs']]:raise ValueError('Use the assignment requirement scope')
                    allowed=[r for r in task['body']['basis'] if self.store.read(reference(r),{SCOPE})['kind']=='contribution'][:5]
                    if data.get('input_refs')!=allowed:raise ValueError('Use the assignment published-input scope')
                    inputs=[self.store.read(reference(r),{SCOPE}) for r in allowed]
                result=self.domain.save(dict(title=title,work_request=data.get('work_request'),deliverable_type=self.domain.profile()['config']['deliverable_types'][0],observation='Working material; conclusions have not yet been authored.',source='Private working conversation',limitation='Draft work, not a published finding or validated outcome.',source_refs=[],input_refs=[asdict(r['ref']) for r in inputs],links=[dict(ref=asdict(r['ref']),relation='refines',rationale='Project review scope; applicability remains for the author to assess.') for r in reqs]))
                draft=self.store.latest(result['id'],{self.domain.scope})
            refs=draft['body'].get('source_refs',[])
            ref=self.store.put('CHAT-'+uuid4().hex[:12],'domain-conversation',self.domain.scope,dict(owner=self.w.actor,domain=self.domain.key,draft_id=draft['ref'].id,focus_source=refs[-1] if refs else None,pending=None,work_request=data.get('work_request'),at=now()))
        return dict(conversation=asdict(ref),id=draft['ref'].id,message='New conversation ready.')
    def attach(self,data):
        with self.store.transaction():
            thread=self.owned(data.get('conversation'));self.available(thread);draft=self.draft(thread)
            if reference(data.get('expected'))!=draft['ref']:raise StaleBasis('Your work changed. Reload before attaching a revision.')
            imported=self.domain.import_source(data);refs=[r for r in draft['body'].get('source_refs',[]) if r['id']!=imported['ref']['id']]+[imported['ref']]
            body={**draft['body'],'expected':asdict(draft['ref']),'source_refs':refs}
            imported_source=self.store.read(reference(imported['ref']),{self.domain.scope})
            if body['title']=='New '+self.domain.profile()['config']['label']+' work':body['title']=imported_source['body']['title'][:200]
            if body['observation']=='Working material; conclusions have not yet been authored.':
                body['observation']='Working material: '+imported_source['body']['title']+'. Findings remain to be authored.'
                body['source']='Private upload: '+imported_source['body']['title']
            self.domain.save(body)
            thread=self.update(thread,focus_source=imported['ref'],review_mode=None)
            self.turn(thread,'attachment','Attached '+self.store.read(reference(imported['ref']),{self.domain.scope})['body']['title'],source=imported['ref'])
        return dict(conversation=asdict(thread['ref']),id=draft['ref'].id,message='File saved privately. Ready for review.')
    def set_context(self,data):
        with self.store.transaction():
            thread=self.owned(data.get('conversation'));self.available(thread);draft=self.draft(thread)
            if reference(data.get('expected'))!=draft['ref']:raise StaleBasis('Your work changed. Reload before changing review scope.')
            values=data.get('requirement_ids');inputs=data.get('input_refs')
            if not isinstance(values,list) or len(values)>20 or len(set(values))!=len(values) or any(not isinstance(v,str) for v in values):raise ValueError('Select at most twenty project requirements')
            reqs=[self.store.latest(id,{SCOPE}) for id in values]
            if any(r['kind']!='requirement' for r in reqs):raise ValueError('Select project requirements')
            shared_input_references(self.store,inputs)
            self.domain.save({**draft['body'],'expected':asdict(draft['ref']),'input_refs':inputs,'links':[dict(ref=asdict(r['ref']),relation='refines',rationale='Review scope selected by the author; this does not propose a requirement change.') for r in reqs]})
            thread=self.update(thread)
        return dict(conversation=asdict(thread['ref']),message='Current review scope saved.')
    def focus(self,data):
        with self.store.transaction():
            thread=self.owned(data.get('conversation'));self.available(thread);draft=self.draft(thread);raw=data.get('source')
            if raw not in draft['body']['source_refs']:raise ValueError('Choose a file attached to this work')
            mode=data.get('mode',thread['body'].get('review_mode') if thread['body'].get('focus_source')==raw else None)
            if mode not in (None,'text','visual'):raise ValueError('Choose text or page review')
            if mode=='visual' and not self.store.read(reference(raw),self.w.scopes)['body'].get('visual_pdf'):raise ValueError('Choose a retained PDF for page review')
            thread=self.update(thread,focus_source=raw,review_mode=mode)
        return dict(conversation=asdict(thread['ref']),message='Review file selected.')
    def source(self,thread):
        raw=thread['body'].get('focus_source')
        return self.store.read(reference(raw),self.w.scopes) if raw else None
    def plan(self,thread):
        source=self.source(thread)
        if source and source['body'].get('visual_pdf') and (thread['body'].get('review_mode') or self.domain.profile()['config'].get('pdf_review_mode','text'))=='visual':
            count=source['body']['visual_pdf']['page_count']
            return [dict(mode='visual',pages=list(range(n,min(n+6,count+1)))) for n in range(1,count+1,6)]
        length=len(source['body']['text']) if source else 0
        return [dict(mode='text',start=n,end=min(n+TEXT_BATCH,length)) for n in range(0,max(length,1),TEXT_BATCH)]
    def available(self,thread):
        if thread['body'].get('pending'):raise ValueError('A review is in progress. Wait for it to finish or recover an interrupted request.')
    def basis(self,thread,batch,render=False,expected=None,source_ref=None,purpose=None):
        draft=self.domain.draft(expected or asdict(self.draft(thread)['ref']))
        source=self.store.read(reference(source_ref),self.w.scopes) if source_ref else self.source(thread)
        if source and asdict(source['ref']) not in draft['body']['source_refs']:raise ValueError('The reviewed file is no longer attached')
        images=[]
        if batch['mode']=='visual':
            ctx,images=self.w.design_visual.context(dict(expected=asdict(draft['ref']),source=asdict(source['ref']),pages=batch['pages'],question='',source_filter=[asdict(source['ref'])]),render=render,shared_workbench=True)
        else:
            ctx=self.domain.context(asdict(draft['ref']),selected_sources=[asdict(source['ref'])] if source else [])
            if source:
                ctx['sources'][0]['body']['text']=source['body']['text'][batch['start']:batch['end']]
                ctx['sources'][0]['body']['excerpt_range']=dict(start=batch['start'],end=batch['end'],total=len(source['body']['text']))
            ctx['skill']='domain-conversation'
        if thread['body'].get('work_request'):
            selected=thread['body']['work_request'];task=self.store.latest(selected['id'],{SCOPE})
            ctx['work_request']=dict(selected=selected,current=asdict(task['ref']),**{k:task['body'][k] for k in ('title','objective','expected_output','boundaries','status','local_context','requirement_guidance','translation_status')})
            ctx['basis'].append(asdict(task['ref']))
        self.working_objectives(thread,ctx)
        if purpose in ('explore','review'):
            ctx['evidence_passages']=evidence_catalog.build(ctx)
            ctx['evidence_reasoning_standard']=domain_alignment.standard_context()
        ctx['review_batch']=batch
        if purpose is not None:ctx['workbench_task']=purpose
        ctx[conversation_findings.MARKER]=dict(document=conversation_findings.document(draft['body']),status='Private editable findings, not approved requirements')
        return ctx,images
    def working_objectives(self,thread,ctx):
        candidates=[r for r in self.w.domain_brief.state() if (r['body'].get('work_request') or {}).get('id')==(thread['body'].get('work_request') or {}).get('id')]
        if candidates:
            plan=candidates[0];b=plan['body'];sections=b.get('brief_sections',b.get('output',{}).get('brief_sections',[]))
            ctx['brief_for_coaching']=dict(ref=asdict(plan['ref']),status=b['status'],objectives=b.get('objectives',b['output'].get('objectives',[])),plan=[s for s in sections if s.get('kind')!='requirement-implication'],interpretations=[s for s in sections if s.get('kind')=='requirement-implication'],open_questions=b['output'].get('open_questions',[]),boundary='Private saved brief for discussion. Proposed sections are unadopted suggestions; interpretations are read only and not governing requirements. Help refine objectives, approach and evaluation criteria using supplied domain knowledge and upstream evidence. Suggest wording for the user to edit; do not claim it was saved, completed or approved.')
            if not plan['current']:ctx['brief_for_coaching']['earlier_inputs']='This private plan retains earlier inputs. Refine it privately; current project requirements remain authoritative. Refresh incoming context before marking it ready.'
            if asdict(plan['ref']) not in ctx['basis']:ctx['basis'].append(asdict(plan['ref']))
        plans=[r for r in self.w.domain_brief.state() if r['body']['status'] in {'working','completed'} and (r['body'].get('work_request') or {}).get('id')==(thread['body'].get('work_request') or {}).get('id')]
        if plans:
            ctx['working_objectives']=dict(ref=asdict(plans[0]['ref']),objectives=[{**o,'id':o.get('id','objective-'+str(i))} for i,o in enumerate(plans[0]['body']['objectives'])],status='Author-edited private working objectives; not governing requirements')
            if plans[0]['body'].get('include_design_brief'):
                sections=plans[0]['body'].get('brief_sections',[])
                ctx['working_design_brief']=dict(ref=asdict(plans[0]['ref']),adopted=[s for s in sections if s.get('kind')!='requirement-implication' and s.get('disposition')=='use'],questions=[s for s in sections if s.get('kind')!='requirement-implication' and s.get('disposition')=='question'],interpretations=[s for s in sections if s.get('kind')=='requirement-implication'],status='Author-selected private guidance. Interpretations are not governing requirements; questions remain unresolved.')
            if asdict(plans[0]['ref']) not in ctx['basis']:ctx['basis'].append(asdict(plans[0]['ref']))
        return ctx
    def report_current(self,report,thread):
        b=report['body']
        try:
            ctx,_=self.basis(thread,b['batch'],expected=b['draft'],source_ref=b.get('source'),purpose=b.get('purpose'))
            if 'evidence_passages' not in b.get('context',{}):ctx.pop('evidence_passages',None)
            return fingerprint(ctx)==b['signature']
        except (PermissionError,ValueError):return False
    def history(self,thread):
        entries=[]
        for turn in self.turns(thread)[-8:]:
            b=turn['body']
            if b['role'] in ('user','assistant'):entries.append(dict(ref=asdict(turn['ref']),role=b['role'],message=b['message'][:1500],draft=b.get('draft'),report=b.get('report')))
        return entries[-6:]
    def send(self,data):
        if data.get('consent') is not True:raise ValueError('Send shares this message, review file and displayed project context with the configured model')
        request_id=data.get('request_id','')
        if not isinstance(request_id,str) or not re.fullmatch(r'[A-Za-z0-9:_-]{8,100}',request_id):raise ValueError('Provide a unique request identifier')
        purpose=data.get('purpose','explore')
        if purpose not in ('explore','review','prepare-sharing'):raise ValueError('Choose exploration, review or preparation for sharing')
        question=txt(data,'message',3000) or 'Review the attached work against the business intent, selected upstream findings and requirements. Prioritize the most consequential gap and explain what needs attention.'
        with self.store.transaction():
            thread=self.owned(data.get('conversation'),current=False)
            for turn in self.turns(thread):
                if turn['body'].get('request_id')==request_id:return dict(conversation=asdict(self.store.latest(thread['ref'].id,{self.domain.scope})['ref']),message='This request is already recorded. Open its saved result or status.',duplicate=True)
            thread=self.owned(data['conversation']);self.available(thread)
            draft=self.draft(thread)
            if reference(data.get('expected'))!=draft['ref']:raise StaleBasis('Your work changed. Reload before sending; your message has been retained in the composer.')
            index=data.get('batch',0);plan=self.plan(thread)
            if type(index) is not int or not 0<=index<len(plan):raise ValueError('Choose a batch from this file')
            batch=plan[index];ctx,images=self.basis(thread,batch,render=True,purpose=purpose);signature=fingerprint(ctx)
            # References and quotes in past exchanges are historical, not current evidence.
            ctx['question']=question;ctx['previous_exchanges']=self.history(thread)
            ctx['card_capture_options']=card_placement.options(self.w)
            if data.get('brief_development') is True:ctx['brief_development']=brief_development.focus(self.w,thread)
            if data.get('card_assessment'):
                ctx['card_assessment']=card_placement.assessment(self.w,data['card_assessment'])
                if not any(v['ref']==ctx['card_assessment']['ref'] for v in ctx['card_capture_options']):ctx['card_capture_options']=ctx['card_capture_options'][:11]+[{k:v for k,v in ctx['card_assessment'].items() if k in ('ref','type','title','statement','fields','relations')}]
            if held:=self.w.implications.context(thread):ctx['working_implications']=held
            if assessments:=domain_alignment.author_context(self.w,thread,ctx):ctx['author_assessments']=assessments
            if len(json.dumps(ctx))>150000:raise ValueError('Use a shorter message or narrower project context')
            self.turn(thread,'user' if index==0 else 'batch',question,request_id=request_id,draft=asdict(draft['ref']),batch=batch,purpose=purpose,card_assessment=data.get('card_assessment'),brief_development=data.get('brief_development') is True)
            thread=self.update(thread,pending=dict(request_id=request_id,at=now()))
        agent=VisualAgent(self.model,self.domain.profile()) if batch['mode']=='visual' else DomainAgent(self.domain.key,self.model,self.domain.profile())
        instructions=conversation_findings.instructions(VISUAL_INSTRUCTIONS if batch['mode']=='visual' else GUARDRAILS,ctx)
        try:
            with AgentRun(self.store,self.w.actor,agent,'domain-conversation',asdict(draft['ref']),ctx['domain_profile']['ref'],ctx['domain_profile']['fingerprint'],context=ctx,instructions=instructions,scope=self.domain.scope) as execution:
                result=agent.run(ctx,images) if images else agent.run(ctx);execution.result=result
                with self.store.transaction():
                    current=self.owned(asdict(thread['ref']));fresh,_=self.basis(current,batch,expected=asdict(draft['ref']),purpose=purpose)
                    if fingerprint(fresh)!=signature:raise StaleBasis('The work or review context changed while the AI partner was responding. Review the current basis again.')
                    report=self.store.put('CREV-'+uuid4().hex[:12],'domain-chat-review',self.domain.scope,dict(owner=self.w.actor,conversation=thread['ref'].id,draft=asdict(draft['ref']),source=asdict(self.source(thread)['ref']) if self.source(thread) else None,batch=batch,parts_total=len(plan),purpose=purpose,signature=signature,basis=ctx['basis'],context=ctx,format=batch['mode'],output=result['output'],mode=execution_mode(self.model),at=now()))
                    for raw in ctx['basis']:self.store.depend(report,reference(raw),self.w.scopes)
                    self.w.implications.capture(current,self.store.read(report,{self.domain.scope}))
                    self.turn(current,'assistant',result['output']['summary'],request_id=request_id,report=asdict(report),draft=asdict(draft['ref']),mode=execution_mode(self.model),batch=batch,purpose=purpose)
                    thread=self.update(current,pending=None)
                    findings=self.w.working_report.aggregate(thread,self.store.read(report,{self.domain.scope})) if purpose=='prepare-sharing' else None
                    execution.complete(result,report)
            return dict(conversation=asdict(thread['ref']),chatReport=report.id,message='Sharing draft prepared.' if findings else 'Reply saved.',findings_updated=bool(findings),batch=index,batches=len(plan))
        except (ModelUnavailable,StaleBasis,ValueError) as error:
            with self.store.transaction():
                thread=self.store.latest(thread['ref'].id,{self.domain.scope})
                self.turn(thread,'error',str(error),request_id=request_id,draft=asdict(draft['ref']))
                if (thread['body'].get('pending') or {}).get('request_id')==request_id:thread=self.update(thread,pending=None)
            return dict(conversation=asdict(thread['ref']),chat_error=str(error),message='Your message and files are saved. The review needs attention.')
    def apply(self,data):
        if data.get('confirm') is not True:raise ValueError('Confirm saving this wording to your draft')
        with self.store.transaction():
            thread=self.owned(data.get('conversation'));self.available(thread)
            report=self.store.read(reference(data.get('report')),{self.domain.scope})
            if report['kind']!='domain-chat-review' or report['body']['conversation']!=thread['ref'].id or report['body']['format']!='text':raise ValueError('Choose a text suggestion from this conversation')
            if not self.report_current(report,thread):raise StaleBasis('This suggestion uses earlier inputs. Request a current review before applying it.')
            i=data.get('index');items=report['body']['output']['suggestions']
            if type(i) is not int or not 0<=i<len(items):raise ValueError('Choose a suggestion')
            field=items[i]['edit']['field']
            if not field:raise ValueError('This suggestion has no draft wording')
            draft=self.draft(thread)
            if reference(data.get('expected'))!=draft['ref']:raise StaleBasis('Your draft changed. Reload before applying wording')
            saved=self.domain.save({**draft['body'],'expected':asdict(draft['ref']),field:txt(data,'text',20000,True)})
            self.store.put('EDIT-'+uuid4().hex[:12],'domain-coach-edit',self.domain.scope,dict(owner=self.w.actor,report=asdict(report['ref']),suggestion=i,before=asdict(draft['ref']),after=asdict(self.store.latest(saved['id'],self.w.scopes)['ref']),field=field,proposed=items[i]['edit']['text'],applied=data['text'],at=now()))
            thread=self.update(thread)
        return dict(conversation=asdict(thread['ref']),message='Wording saved as a new draft version. Publication remains separate.')
    def recover(self,data):
        with self.store.transaction():
            thread=self.owned(data.get('conversation'));pending=thread['body'].get('pending')
            if not pending or datetime.now(timezone.utc)-datetime.fromisoformat(pending['at'].replace('Z','+00:00'))<timedelta(minutes=5):raise ValueError('The current request is still within its processing window')
            self.turn(thread,'error','The earlier request was interrupted; its outcome is unknown. No approval or publication occurred. Send again explicitly to request a new review.',request_id=pending['request_id'])
            thread=self.update(thread,pending=None)
        return dict(conversation=asdict(thread['ref']),message='Interrupted request retained in history. You can send a new request.')
    def save_alignment(self,data):return domain_alignment.save(self.w,data)
    def state(self):
        if not self.domain.key:return None
        threads=self.threads();reports=[]
        for r in self.w.latest_records('domain-chat-review'):
            thread=next((t for t in threads if t['ref'].id==r['body']['conversation']),None)
            if not thread:continue
            # Context snapshots are accessible in the author's scope, not repeated in the view payload.
            body={k:v for k,v in r['body'].items() if k!='context'}
            body['question']=r['body']['context'].get('question','')
            if r['body']['format']=='visual':body['citation_records']=r['body']['context']['review_basis']
            else:
                body['citation_records']=r['body']['context']['sources'];body['deliverable_basis']=r['body']['context']['deliverable'];body['locations']=[]
                for suggestion in body['output']['suggestions']:
                    source=next((s for s in body['citation_records'] if s['ref']['id']==suggestion['basis']),None)
                    location=None
                    if source:
                        full=self.store.read(reference(source['ref']),self.w.scopes)['body'];offset=source['body'].get('excerpt_range',{}).get('start',0)+source['body']['text'].index(suggestion['quote'])
                        page=next((p['page'] for p in full.get('page_spans',[]) if p['start']<=offset<p['end']),None)
                        location=dict(source=source['ref'],start=offset,line=full['text'][:offset].count('\n')+1,page=page,quote=suggestion['quote'])
                    body['locations'].append(location)
            reports.append({**r,'body':body,'current':self.report_current(r,thread),'selection_current':self.w.working_report.selection_current(r,thread)})
        return dict(prototypes=self.w.prototypes.state(threads),user_flows=self.w.flows.state(),import_tools=self.w.tool_imports.state(),threads=[{**t,'draft':asdict(self.draft(t)['ref']),'plan':self.plan(t)} for t in threads],turns=[r for t in threads for r in self.turns(t)],reports=reports,working_history=self.w.working_report.history(),alignment=domain_alignment.rows(self.w,threads),implications=self.w.implications.state(threads),knowledge_cards={**self.w.cards.state(threads),'placements':card_placement.projection(self.w,reports)},submissions=self.w.submissions.state(threads),objectives=[dict(conversation=t['ref'].id,**self.working_objectives(t,{'basis':[]}).get('working_objectives',{})) for t in threads])

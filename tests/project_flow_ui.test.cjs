const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function setup(actor='sam'){
 let modal;const req={kind:'requirement',ref:{id:'REQ',revision:2},body:{title:'Staged evidence',text:'Capture first.',acceptance_criteria:'Show pending.'}},task={ref:{id:'WORK',revision:1},body:{title:'Study the reporting interruption',recipient:'sam',requested_by:'priya',status:'requested',objective:'Find the loss point.',expected_output:'Bounded finding.',local_context:'Observe the receptionist workflow.',boundaries:'No safety changes.',boards:['business-research','research-design'],packet_refs:[],requirement_refs:[req.ref],requirement_guidance:[{ref:req.ref,local_application:'Investigate interruption.',expected_evidence:'Task observation.'}]},changed:[]};
 const c={URL,console,state:{domains:{active:actor==='lee'?'design':'research',profiles:[{key:'design',config:{label:'Design',deliverable_types:['Prototype design brief','Evidence-backed developer brief']}},{key:'research',config:{label:'Research',deliverable_types:['Research finding','Study synthesis']}}]},actor,actors:{priya:{name:'Sponsor'},sam:{name:'Research'},lee:{name:'Design'}},project_flow:{requests:[task],tools:{ref:null,links:{research_figjam:'https://www.figma.com/board/FictionalResearch',design_figma:'https://www.figma.com/design/FictionalDesign'},mcp:{endpoint:'https://mcp.figma.com/mcp',config:{mcpServers:{figma:{url:'https://mcp.figma.com/mcp'}}}}},brief:{intent:{ref:{id:'INT',revision:1},body:{text:'Avoid lost reports.'}}},can_request:true},bridge:{issues:[]}},bridgeBoard:'research-design',bridgeSection:'boards',chatThread:()=>null,records:kind=>kind==='requirement'?[req]:[],get:()=>req,projectTitle:()=> 'Fictional',projectTaskName:id=>id,esc:v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),button:(t,a,id='')=>`<button data-action="${a}" data-id="${id}">${t}</button>`,tag:t=>t,label:r=>r.id+':v'+r.revision,packetKey:r=>r.id+':'+r.revision,para:v=>`<p>${v}</p>`,val:(k,v)=>`<strong>${k}</strong><p>${v}</p>`,modal:(...x)=>{modal=x;},document:{addEventListener:()=>{}},render:()=>{},bridgeInfo:()=>({boards:{'business-research':'Sponsor Research','research-design':'Research Design'}})};
 vm.createContext(c);require('./ui_reference_helpers.cjs')(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/project-flow.js'),'utf8'),c);return {c,req,task,run:s=>vm.runInContext(s,c),modal:()=>modal};
}
test('both profiles use one brief entry and retain own external work tools',()=>{for(const a of ['sam','lee']){const h=setup(a),html=h.run('projectEntryStrip()');assert.match(html,/data-action="pflow-brief" aria-label="Working brief"/);assert.doesNotMatch(html,/Ask sponsor/);assert.doesNotMatch(html,/pflow-objectives-open|Research objectives|Design objectives/);assert.match(html,a==='sam'?/Open FigJam/:/Open Figma/);}});
test('domain brief preserves shared requirement beside attributed local interpretation',()=>{const h=setup();h.run('projectRequestDetail(projectTask("WORK"))');const html=h.modal()[1];for(const phrase of ['Capture first.','Investigate interruption.','Task observation.','Interpretation by Sponsor','Observe the receptionist workflow.'])assert.ok(html.includes(phrase));});
test('assignment-only records are excluded from the brief collection on every board',()=>{const h=setup();assert.equal(h.run('domainBriefItems().length'),0);h.c.bridgeBoard='business-design';assert.equal(h.run('domainBriefItems().length'),0);});
test('pending bridge questions retain next responder and do not look resolved',()=>{const h=setup();h.c.state.bridge.issues=[{ref:{id:'ISSUE',revision:1},body:{title:'Ownership pending',question:'Who follows up?',status:'investigating',next_owner:'priya',route:'coordination',requirement_refs:[h.req.ref]}}];const html=h.run('projectDependencies({body:{requirement_refs:[{id:"REQ",revision:2}],input_refs:[]}})');assert.match(html,/Pending cross-team questions/);assert.match(html,/Next: Sponsor/);assert.match(html,/Current requirements still apply/);assert.match(html,/Open question/);});
test('work links reject script destinations and MCP status remains explicit',()=>{const h=setup();assert.equal(h.run('projectToolLink("javascript:alert(1)","Bad")'),'');h.run('projectToolsForm()');assert.match(h.modal()[1],/Settings → Integrations/);assert.doesNotMatch(h.modal()[1],/Server configuration|type="password"/);const mcp=h.run('projectMcpSetup()');assert.match(mcp,/needs its own user authorization/);assert.match(mcp,/does not grant access/);});
test('private suggested objectives are editable with source and requirement basis disclosed',()=>{const h=setup();h.c.state.domain_objectives=[{ref:{id:'OBJ',revision:1},current:true,body:{status:'suggested',mode:'simulated',work_request:null,output:{summary:'Investigate task loss.',objectives:[{title:'Locate interruption',question:'Where is capture lost?',why:'Protect reporting.',output:'Bounded finding',evidence:'Observation',requirement_ids:['REQ'],basis_links:[{id:'REQ',revision:2,quote:'Capture first.'}]}],open_questions:['Who follows up?']}}}];h.run('projectObjectives()');const html=h.modal()[1];assert.match(html,/Locate interruption/);assert.match(html,/name="question-0"/);assert.equal(h.modal()[2],'Save objectives');assert.match(html,/aria-label="Objective references"/);assert.match(html,/Requirements:<\/span> Staged evidence/);assert.match(html,/Sources: Staged evidence · v2/);assert.match(html,/Capture first\./);assert.match(html,/Open questions/);assert.match(html,/Suggested plan/);});

test('opening an update highlights its declared requirements without changing review scope',()=>{const h=setup();h.c.projectUpdateFocus={ref:{id:'EVENT',revision:1},key:'one||development|sam',title:'Recorded decision',detail:'Staged evidence is approved.',requirement_refs:[h.req.ref]};h.c.state.project={id:'one'};h.run('projectUpdateFocus='+JSON.stringify(h.c.projectUpdateFocus));assert.equal(h.run('projectRequirementUpdated("REQ")'),true);assert.match(h.run('projectUpdatePanel()'),/selected review scope has not changed/);h.c.state.project.id='other';assert.equal(h.run('projectRequirementUpdated("REQ")'),false);});

test('domain toolbar retains brief access without separate objectives or integration configuration',()=>{const h=setup();const html=h.run('projectEntryStrip()');assert.doesNotMatch(html,/Project references|pflow-tools|FigJam & Figma settings/);assert.match(html,/Working brief/);assert.doesNotMatch(html,/Research objectives|pflow-objectives-open/);});

test('framing connection shortcuts show saved files rather than configuration controls or invented MCP activity',()=>{
 const h=setup('priya');h.c.state.coaching={settings:{integrations:{items:[{id:'one',kind:'mcp',name:'Saved server',endpoint:'https://example.test/mcp'}]}}};
 const before=JSON.stringify(h.c.state),html=h.run('projectConnectionShortcuts()');
 assert.match(html,/Research · FigJam board/);assert.match(html,/Design · Figma file/);assert.match(html,/href="https:\/\/www.figma.com\/board\/FictionalResearch"/);assert.match(html,/File link/);assert.match(html,/Authorize selected-content imports/);
 assert.doesNotMatch(html,/data-action="(?:pflow-tools|settings-connection)"|<input|<textarea|Connected<|Lucid|Miro|Copilot/);
 assert.equal(JSON.stringify(h.c.state),before);
});
test('an unconfigured project offers one path to integration settings and no placeholder tool connections',()=>{
 const h=setup('priya');h.c.state.project_flow.tools.links={};const html=h.run('projectConnectionShortcuts()');
 assert.match(html,/No connections configured/);assert.match(html,/Settings → Integrations/);assert.match(html,/data-action="settings-integrations"/);assert.doesNotMatch(html,/href=|Configure<|Lucid|Miro|Copilot/);
});
test('domain settings list only the actor’s work tools and retain the existing save contract',async()=>{
 for(const actor of ['sam','lee']){
  const h=setup(actor);h.c.command=async(action,data)=>({action,data});h.run('projectToolsForm()');const dialog=h.modal(),fields=new Map([['research_figjam','https://www.figma.com/board/ChangedResearch'],['design_figma','https://www.figma.com/design/ChangedDesign'],['design_figjam','']]);const out=await dialog[3](fields);
  assert.equal(out.action,'work-tools-save');assert.deepEqual(Object.keys(out.data.links),actor==='sam'?['research_figjam']:['design_figma','design_figjam']);
  const html=h.run('projectToolsSummary()');assert.match(html,actor==='sam'?/Research · FigJam board/:/Design · Figma file/);assert.doesNotMatch(html,actor==='sam'?/Design · Figma file/:/Research · FigJam board/);
 }
});
test('shortcut links reject credentials and non-Figma destinations',()=>{
 const h=setup('priya');for(const url of ['https://name:secret@www.figma.com/design/File','https://example.test/design/File','javascript:alert(1)'])assert.equal(h.run('projectToolLink('+JSON.stringify(url)+',"Open")'),'');
});

function savedObjective(h,task=null){const r={ref:{id:'OBJ-'+h.c.state.actor,revision:2},current:true,body:{status:'working',mode:'simulated',work_request:task?.ref||null,output:{summary:'Fictional bounded guidance.',objectives:[{title:'Locate interruption',question:'Where is capture lost?',why:'Protect reporting.',output:'Bounded finding',evidence:'Observation',requirement_ids:['REQ'],basis_links:[{id:'REQ',revision:2,quote:'Capture first.'}]}],open_questions:['Who follows up?']}}};h.c.state.domain_objectives=[r];return r;}
test('editing objectives inside either brief saves its exact version without modifying sources or shared assignment',async()=>{
 for(const actor of ['sam','lee']){const h=setup(actor),r=savedObjective(h),before=JSON.stringify({req:h.req,task:h.task,output:r.body.output}),calls=[];h.c.command=async(action,data)=>{calls.push({action,data});return {message:'Saved'};};h.run('projectBrief()');
 assert.equal(h.modal()[0],'Working brief');assert.match(h.modal()[1],/brief-objectives/);assert.match(h.modal()[1],/name="evidence-0"/);
 const fields=new Map(Object.entries({title:'Clarify recovery',question:'When is recovery needed?',why:'Avoid losing work.',output:'Testable recovery states.',evidence:'Task observation.'}).map(([k,v])=>[k+'-0',v]));const result=await h.modal()[3](fields);
 assert.equal(calls.length,1);assert.equal(calls[0].action,'domain-objectives-save');assert.equal(calls[0].data.expected,r.ref);assert.equal(calls[0].data.objectives[0].question,'When is recovery needed?');assert.equal('basis_links' in calls[0].data.objectives[0],false);assert.equal(result.domainObjectives,true);assert.equal(result.workRequest,null);assert.equal(JSON.stringify({req:h.req,task:h.task,output:r.body.output}),before);
 }
});
test('Domain brief opens the current assignment and its scoped objectives rather than project-wide objectives',()=>{
 const h=setup();savedObjective(h,h.task);h.c.chatThread=()=>({body:{work_request:h.task.ref}});h.run('projectBrief()');assert.match(h.modal()[1],/Locate interruption/);assert.doesNotMatch(h.modal()[1],/Open assigned work|Cancel work request/);assert.equal(h.modal()[2],'Save objectives');
 const fields=new Map(['title','question','why','output','evidence'].map(k=>[k+'-0','Edited '+k]));h.c.command=async()=>({});return h.modal()[3](fields).then(result=>assert.equal(result.workRequest,'WORK'));
});
test('changed incoming context retains source basis and allows private objective edits',()=>{
 const h=setup(),r=savedObjective(h);r.current=false;r.editable=true;h.run('projectBrief()');assert.match(h.modal()[1],/Earlier incoming context/);assert.match(h.modal()[1],/Capture first./);assert.match(h.modal()[1],/<textarea/);assert.equal(typeof h.modal()[3],'function');assert.doesNotMatch(h.modal()[1],/name="brief-complete"/);
});
test('navigation or requesting new suggestions respects the existing unsaved-objectives discard guard',()=>{
 const h=setup();h.c.dirty=true;const dialog={open:true,querySelector:()=>({})};h.c.document.querySelector=()=>dialog;let closes=0;h.c.closeModal=()=>{closes++;};assert.equal(h.run('projectLeaveObjectiveEdits()'),false);assert.equal(closes,1);h.c.closeModal=()=>{dialog.open=false;};assert.equal(h.run('projectLeaveObjectiveEdits()'),true);
});

function completeBrief(h){const r=savedObjective(h);r.body.include_design_brief=true;r.body.design_inputs={research_count:1,additional_upstream:0,upstream:[{ref:{id:'RESEARCH',revision:3},kind:'contribution',title:'Study finding',domain:'Research',author:'sam',fields:[{label:'Evidence limits',text:'Fictional small study; prevalence unknown.',truncated:false}]}],requirements:[{ref:h.req.ref,title:'Staged evidence',text:'Capture first.',acceptance_criteria:'Show pending.',conditions:'Non-safety only.',status:'proposed'}]};r.body.output.brief_sections=[{kind:'purpose',title:'Protect reporting continuity',text:'Propose recoverable reporting.',rationale:'The research identifies interruptions.',requirement_ids:['REQ'],basis_links:[{id:'RESEARCH',revision:3,quote:'Observed interruptions.'}]},{kind:'requirement-implication',title:'Explore pending states',text:'Distinguish draft retention from successful submission.',rationale:'The requirement separates initial capture from evidence.',requirement_ids:['REQ'],basis_links:[{id:'REQ',revision:2,quote:'Capture first.'}]}];return r;}
test('complete Working brief separates original upstream input canonical criteria and coach inference',()=>{
 const h=setup('lee');completeBrief(h);h.run('projectBrief()');const html=h.modal()[1];for(const phrase of ['Incoming context','Requirements','Related requirement: Staged evidence','Implication for this work','Approach','Evaluation criteria','Distinguish draft retention from successful submission.','(Read only) User needs and requirements translated for your role.','Needs discussion','Review needed'])assert.ok(html.includes(phrase),phrase);assert.equal(h.modal()[2],'Save working brief');assert.match(html,/pflow-design-brief/);assert.doesNotMatch(h.run('projectEntryStrip()'),/pflow-design-brief|pflow-objectives-open/);
});
test('read-only interpretation is outside all editable plan fields and raw incoming inputs stay in preview',()=>{
 const h=setup('lee'),r=completeBrief(h);r.body.profile={config:{label:'Design',vocabulary:'Recovery state means retained work, not confirmed submission.',evidence_standard:'Evaluate observable state transitions.'},knowledge_entries:[{title:'Task recovery',definition:'Preserve user input before retry.'}]};h.run('projectBrief()');const html=h.modal()[1];assert.doesNotMatch(html,/Task recovery|View knowledge sources|Professional approach|Vocabulary|Evidence standard/);assert.doesNotMatch(html,/name="brief-text-1"|Requirements to address|Show pending\.|Fictional small study; prevalence unknown\./);assert.match(html,/name="brief-text-0"/);assert.ok(html.indexOf('brief-objectives-title')<html.indexOf('<h4>Approach'));
});
test('saving Working brief uses same guarded version and sends editable content and explicit author choices only',async()=>{
 const h=setup('lee'),r=completeBrief(h),calls=[];h.c.command=async(action,data)=>{calls.push({action,data});return {message:'Saved'};};h.run('projectBrief()');const fields=new Map(['title','question','why','output','evidence'].map(k=>[k+'-0','Edited '+k]));r.body.output.brief_sections.forEach((s,i)=>{for(const k of ['title','text','rationale'])fields.set('brief-'+k+'-'+i,s[k]);fields.set('brief-disposition-'+i,i?'question':'use');});await h.modal()[3](fields);
 assert.equal(calls.length,1);assert.equal(calls[0].action,'domain-objectives-save');assert.equal(calls[0].data.expected,r.ref);assert.equal(calls[0].data.brief_sections[0].disposition,'use');assert.equal(calls[0].data.brief_sections.length,1);assert.equal(calls[0].data.brief_sections.some(s=>s.kind==='requirement-implication'),false);assert.equal('basis_links' in calls[0].data.brief_sections[0],false);
});
test('Design drafting previews and pins inputs before the explicit model request',async()=>{
 const h=setup('lee'),r=completeBrief(h),calls=[];h.c.state.project={id:'Fictional',version:1};h.c.state.domains={active:'design'};h.c.busy=false;h.c.document.querySelector=()=>null;h.c.command=async(action,data)=>{calls.push({action,data});return action==='domain-brief-preview'?{signature:'exact-preview',inputs:r.body.design_inputs,basis:[h.req.ref],additional_pending_questions:0}:{id:'PROPOSAL'};};await h.run('projectDraftDesignBrief()');assert.equal(calls.length,1);assert.equal(calls[0].action,'domain-brief-preview');assert.match(h.modal()[1],/displayed input versions/);assert.equal(h.modal()[2],'Draft brief');await h.modal()[3]();assert.equal(calls[1].action,'domain-objectives-suggest');assert.equal(calls[1].data.include_brief,true);assert.equal(calls[1].data.expected_signature,'exact-preview');assert.equal(calls[1].data.consent,true);
});

test('Working brief supports stable-key authored additions and explicit completion without discarding original inputs',async()=>{
 const h=setup('lee'),r=completeBrief(h),calls=[];r.readiness={missing:['Scope and exclusions'],completed:false};h.c.command=async(action,data)=>{calls.push({action,data});return {message:'Saved'};};h.run('projectBrief()');const html=h.modal()[1];for(const text of ['Add plan detail','Add objective','Use this plan to guide the work','Scope and exclusions'])assert.ok(html.includes(text),text);
 const fields=new Map([['brief-editor-present','1'],['brief-complete','on'],['objective-id-new-one','new-one'],['brief-id-new-two','new-two'],['brief-kind-new-two','scope'],['brief-disposition-new-two','use']]);for(const key of ['title','question','why','output','evidence'])fields.set(key+'-new-one','Authored '+key);for(const key of ['title','text','rationale'])fields.set('brief-'+key+'-new-two','Authored '+key);fields.getAll=name=>name==='objective-key'?['new-one']:name==='brief-section-key'?['new-two']:[];
 await h.modal()[3](fields);assert.equal(calls[0].data.complete,true);assert.equal(calls[0].data.objectives[0].id,'new-one');assert.equal(calls[0].data.brief_sections[0].id,'new-two');assert.equal(calls[0].data.brief_sections[0].kind,'scope');assert.equal(calls[0].data.expected,r.ref);
});
test('adding or removing brief content is an in-form edit and does not invoke discard navigation',()=>{
 const h=setup();h.c.dirty=true;h.c.document.querySelector=()=>{throw Error('Internal edits must stay in the current form');};for(const action of ['pflow-brief-add','pflow-objective-add','pflow-brief-remove','pflow-objective-remove'])assert.equal(h.run('projectLeaveObjectiveEdits('+JSON.stringify(action)+')'),true);
});

test('historical task context remains readable without becoming a new brief output',()=>{const h=setup();h.task.changed=['basis'];const before=JSON.stringify(h.task);h.run('projectRequestDetail(projectTask("WORK"))');assert.match(h.modal()[1],/Study the reporting interruption/);assert.match(h.modal()[1],/assignment context changed/);assert.equal(JSON.stringify(h.task),before);});

test('the collection uses actual configured domain briefs rather than assignment records',()=>{
 const h=setup('lee');h.task.body.recipient_domain='design';h.task.body.recipient='lee';h.c.bridgeBoard='business-research';
 assert.equal(h.run('domainBriefItems().length'),0);
 h.c.state.domain_objectives=[{ref:{id:'PLAN',revision:3},body:{owner:'lee',include_design_brief:true,work_request:h.task.ref,status:'working'},current:true}];
 const shared={ref:{id:'SHARED',revision:2},kind:'project-design-brief',body:{owner:'lee',domain:'Design',work_request:h.task.ref,source_version:{id:'PLAN',revision:2}}};h.c.records=kind=>kind==='project-design-brief'?[shared]:[];
 const rows=h.run('domainBriefItems()');assert.equal(rows.length,1);assert.equal(rows[0].title,'Design · Working brief');assert.equal(rows[0].type,'Working brief');assert.equal(rows[0].shared.ref.id,'SHARED');assert.equal(rows[0].action,'pflow-objectives-edit');
 const html=h.run('domainBriefDirectory()');assert.match(html,/Published v2/);assert.match(html,/data-action="pflow-shared-brief"/);assert.doesNotMatch(html,/pflow-objectives-edit/);assert.doesNotMatch(html,/Study the reporting interruption|pflow-brief-board/);
 h.c.state.domains.profiles[0].config.deliverable_types=[];assert.equal(h.run('domainBriefItems().length'),0);
});
test('unassigned private working brief and its shared version use one selectable item',()=>{
 const h=setup('lee');h.c.state.project_flow.requests=[];h.c.state.domains.active='design';h.c.state.domain_objectives=[{ref:{id:'PLAN',revision:2},current:true,body:{owner:'lee',include_design_brief:true,status:'completed'}}];
 h.c.records=kind=>kind==='project-design-brief'?[{kind:'project-design-brief',ref:{id:'SHARED',revision:1},body:{owner:'lee',domain:'Design',source_version:{id:'PLAN',revision:2}}}]:[];
 const rows=h.run('domainBriefItems()');assert.equal(rows.length,1);assert.equal(rows[0].action,'pflow-objectives-edit');assert.equal(rows[0].shared.ref.id,'SHARED');
});


test('the published Business Intent leads the collection and opens its exact released snapshot',async()=>{
 const h=setup('lee'),published={ref:{id:'INTCASE',revision:4},body:{status:'published',source_draft:{id:'INTAKE',revision:7},snapshot:{title:'Published direction',values:{value:'PUBLIC BASELINE'}}}};
 h.c.state.intake={published,cases:[published],draft:{body:{values:{value:'PRIVATE REVISION'}}}};h.c.intakeSnapshot=s=>'<article>'+s.values.value+'</article>';
 const before=JSON.stringify(h.c.state),rows=h.run('domainBriefItems()');assert.equal(rows[0].title,'Business Intent');assert.equal(rows[0].action,'pflow-business-brief');assert.equal(rows[0].id,'INTCASE|4');
 await h.run('projectFlowAction("pflow-business-brief","INTCASE|4")');assert.equal(h.modal()[0],'Business Intent');assert.equal(h.modal()[2],null);assert.match(h.modal()[1],/PUBLIC BASELINE/);assert.match(h.modal()[1],/does not approve requirements/);assert.doesNotMatch(h.modal()[1],/PRIVATE REVISION/);assert.equal(JSON.stringify(h.c.state),before);
});
test('a private or pending sponsor brief is not substituted for the published baseline',()=>{
 const h=setup('sam'),pending={ref:{id:'PENDING',revision:1},body:{status:'pending-review',source_draft:{revision:9},snapshot:{title:'Unpublished revision'}}};h.c.state.intake={published:null,cases:[pending],draft:{body:{title:'Private sponsor draft'}}};
 assert.equal(h.run('domainBriefItems().some(r=>r.type==="Business sponsor")'),false);assert.throws(()=>h.run('openBusinessDomainBrief("PENDING|1")'),/unavailable/);
 const old={ref:{id:'OLDER',revision:2},body:{status:'published',source_draft:{revision:1},snapshot:{title:'Earlier baseline'}}},current={ref:{id:'CURRENT',revision:3},body:{status:'published',source_draft:{revision:8},snapshot:{title:'Current baseline'}}};h.c.state.intake.published=current;h.c.state.intake.cases=[pending,current,old];h.c.intakeSnapshot=s=>s.title;
 h.run('openBusinessDomainBrief("OLDER|2")');assert.match(h.modal()[1],/Earlier published direction/);assert.match(h.modal()[1],/Earlier baseline/);assert.match(h.modal()[1],/CURRENT\|3/);assert.doesNotMatch(h.modal()[1],/Unpublished revision/);
});

test('no brief list or legacy action offers assignment creation even with older capability flags',async()=>{
 const h=setup('priya');h.c.state.project_flow.can_request=true;
 for(const html of [h.run('domainBriefDirectory()')])assert.doesNotMatch(html,/Send domain brief|pflow-request-new|Receiving domain/);
 assert.equal(h.run('typeof projectRequestForm'),'undefined');
 await h.run('projectFlowAction("pflow-request-new","")');assert.equal(h.modal(),undefined);
});


test('Working brief previews the current task guidance and keeps publication separate from editing',()=>{
 const h=setup('sam'),scoped=savedObjective(h,h.task),global={...scoped,ref:{id:'GLOBAL',revision:1},body:{...scoped.body,work_request:null,output:{summary:'UNRELATED GLOBAL GUIDANCE',objectives:[]}}};
 scoped.body.output.summary='TASK SPECIFIC PRIVATE GUIDANCE';scoped.body.output.objectives[0].title='Task-specific objective';h.c.state.domain_objectives=[global,scoped];h.c.chatThread=()=>({body:{work_request:h.task.ref}});
 const before=JSON.stringify(h.c.state),html=h.run('workingDomainBriefs()');assert.match(html,/TASK SPECIFIC PRIVATE GUIDANCE|Task-specific objective/);assert.doesNotMatch(html,/UNRELATED GLOBAL GUIDANCE|pflow-shared-brief|pflow-business-brief/);assert.match(html,/Edit plan/);assert.doesNotMatch(h.run('domainBriefNavigation()'),/TASK SPECIFIC PRIVATE GUIDANCE|pflow-objectives-edit/);h.run('projectBrief()');assert.equal(h.modal()[2],'Save objectives');assert.equal(JSON.stringify(h.c.state),before);
});

test('Business Intent is a read-only destination with safe shared-direction and empty-state fallbacks',async()=>{const h=setup('sam'),before=JSON.stringify(h.c.state);await h.run("projectFlowAction('pflow-business-intent','')");assert.equal(h.modal()[0],'Business Intent');assert.match(h.modal()[1],/Avoid lost reports/);assert.equal(h.modal()[2],null);assert.equal(JSON.stringify(h.c.state),before);h.c.state.project_flow.brief={};h.c.records=()=>[];h.run('openBusinessIntent()');assert.match(h.modal()[1],/No published Business Intent/);});

test('brief editor separates read-only incoming meaning from a named editable plan with a consistent heading hierarchy',()=>{const h=setup('lee');completeBrief(h);h.run('projectBrief()');const html=h.modal()[1];assert.match(html,/Incoming project requirements translated for your role/);assert.ok(html.indexOf('brief-domain-interpretation')<html.indexOf('brief-editing-window'));assert.match(html,/<h3 id="brief-plan-title">Work plan<\/h3>/);assert.match(html,/<h4 id="brief-objectives-title">Objectives<\/h4>/);assert.match(html,/<h4>Approach<\/h4>/);assert.match(html,/<h4>Evaluation criteria<\/h4>/);assert.match(html,/aria-label="Editable work plan"/);assert.match(html,/data-plan-group="approach"/);assert.equal(h.modal()[2],'Save working brief');});
test('stale brief editor keeps the hierarchy without adding editable fields or a save action',()=>{const h=setup('lee'),r=completeBrief(h);r.current=false;h.run('projectBrief()');assert.match(h.modal()[1],/Work plan/);assert.doesNotMatch(h.modal()[1],/<textarea/);assert.equal(h.modal()[2],null);});

test('configured hypotheses and guide use the common brief editor in either domain',()=>{
 for(const actor of ['sam','lee']){const h=setup(actor),r=completeBrief(h);h.c.domainProfile=()=>({config:{authors:[actor],brief_sections:['hypotheses','approach','discussion-guide']}});r.body.output.brief_sections.push(...['hypotheses','approach','discussion-guide'].map(kind=>({kind,title:kind==='hypotheses'?'Capture hypothesis':kind==='approach'?'Episode interviews':'Interview guide',text:'Editable suggested planning content.',rationale:'Test the value mechanism.',requirement_ids:[],basis_links:[]})));h.run('projectBrief()');const html=h.modal()[1];assert.match(html,/<h4>Business hypotheses/);assert.match(html,/<h4>Draft discussion guide/);assert.match(html,/maxlength="2400"/);assert.match(html,/Interview guide/);assert.equal(h.modal()[2],'Save working brief');}
});

test('changed brief inputs can be previewed and refreshed without a model call or automatic completion',async()=>{
 const h=setup('lee'),r=completeBrief(h),calls=[];r.current=false;r.editable=true;
 h.c.state.project={id:'Fictional',version:1};h.c.state.domains={active:'design'};h.c.busy=false;h.c.document.querySelector=()=>null;
 h.c.command=async(action,data)=>{calls.push({action,data});return action==='domain-brief-refresh-preview'?{expected:r.ref,signature:'refreshed-context',inputs:r.body.design_inputs,changes:[{title:'Research limitations',before:{id:'RESEARCH',revision:2},after:{id:'RESEARCH',revision:3}}],additional_pending_questions:0}:{id:r.ref.id};};
 h.run('projectBrief()');assert.match(h.modal()[1],/Review changed inputs/);assert.doesNotMatch(h.modal()[1],/name="brief-complete"/);
 await h.run('projectRefreshBriefInputs('+JSON.stringify(r.ref.id)+')');assert.equal(calls.length,1);assert.equal(calls[0].action,'domain-brief-refresh-preview');assert.match(h.modal()[1],/No model call or publication/);assert.match(h.modal()[1],/Research limitations/);assert.equal(h.modal()[2],'Refresh inputs');
 const result=await h.modal()[3]();assert.equal(calls[1].action,'domain-brief-refresh');assert.equal(calls[1].data.expected_signature,'refreshed-context');assert.equal(calls[1].data.confirm,true);assert.equal('complete' in calls[1].data,false);assert.equal(result.domainObjectives,true);
});
test('retained historical interpretations remain labelled after inputs become current',()=>{
 const h=setup('lee'),r=completeBrief(h);r.body.output.brief_sections[1].historical_interpretation=true;
 h.run('projectBrief()');assert.match(h.modal()[1],/Earlier interpretation\. Check evaluation criteria against current requirements\./);
 r.body.brief_sections=r.body.output.brief_sections;r.body.objectives=r.body.output.objectives;
 assert.match(h.run('projectSharedBriefBody(state.domain_objectives[0].body)'),/Earlier interpretation · historical/);
});

test('work request packet buttons use plain readable names and preserve exact action keys and optional source metadata',()=>{
 const h=setup();h.task.body.packet_refs=[{id:'PKT-INTERNAL-ONLY',revision:4}];const before=JSON.stringify(h.task);h.run('projectRequestDetail(projectTask("WORK"))');const html=h.modal()[1],action=html.match(/<button data-action="packet" data-id="PKT-INTERNAL-ONLY:4">([\s\S]*?)<\/button>/);
 assert.ok(action);assert.equal(action[1],'Inspect Context packet · v4');assert.doesNotMatch(action[1],/PKT-INTERNAL-ONLY|<details/);assert.match(html,/<details class="record-metadata"><summary>Source details<\/summary>[\s\S]*PKT-INTERNAL-ONLY:v4/);assert.equal(JSON.stringify(h.task),before);
});

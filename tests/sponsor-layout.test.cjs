const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(){const questions=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/workbench/config/sponsor_questions.json'))),answers=Object.fromEntries(questions.map(q=>[q.id,{items:['Saved '+q.id],roles:q.id==='q4'?[{name:'Receptionist',does:'Report friction',needs:'A response',where:'Front desk',often:'Per shift'}]:[],confirmed:false}]));
 const draft={ref:{id:'INTAKE-001',revision:7},body:{values:{value:'An actual saved value proposition',gains:'Fewer interruptions',why_now:'Growing process fragmentation',investment_case:'Uncertain estimate'},scaffold:[]}};
 const state={records:[],actor:'priya',project:{title:'<Private project>'},actors:{priya:{name:'Priya'}},sponsor:{questions,brief:{framing:{name:'<Private project>',statement:'A saved problem',context:'Existing context',summary:{problem:'More detail',solution:'A proposed response',risk:'A retained risk',options:'A retained alternative'}},answers}},intake:{draft,published:null,preflight:{packages:[]},gaps:[],scaffold_current:false},goals:{goals:[],measures:[]}};
 const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');const ctx={state,console,document:{addEventListener(){},querySelector(){return null;}},intakeNames:{},view:'intent',intakeStep:'context',intakeCaseId:null,selected:null,esc,button:(text,action,id='',cls='')=>`<button class="${cls}" data-action="${action}" data-id="${esc(id)}">${esc(text)}</button>`,coachInfo:()=>({sources:[],runs:[],model:{configured:false}}),sourceDraftSummary:()=>'',currentIntakeCase:()=>null,label:r=>r.id+'@'+r.revision,val:(t,v)=>`<div>${esc(t)}: ${esc(v||'')}</div>`,para:t=>`<p>${esc(t)}</p>`,tag:t=>esc(t),goalsRead:()=>'<div>Stored goals & measures</div>',areaRead:()=>'',intakeDrawerForm:()=>'<form id="intake-drawers-form">Actual connected scaffold form</form>',$:()=>null,pageDirty:false,render:()=>{},toast:()=>{},saveBeforeProjectChange:async()=>{},workspaceNavigation:()=>({intent:'Business Intent',planning:'Requirements'}),settingsNavigation:()=>'<details><summary>Settings</summary></details>',head:(t,d)=>`<h1>${esc(t)}</h1><p>${esc(d)}</p>`,ref:r=>`<span>${esc(r.id)}:v${r.revision}</span>`,statusTag:s=>esc(s),criterionList:s=>'<li>'+esc(s)+'</li>',linkedGoalsRead:()=>'',records:k=>state.records.filter(r=>r.kind===k),requirementDrawers:()=>'<div>Existing drawer browser</div>',projectConnectionShortcuts:()=>'<section>Saved connection shortcuts</section>',FormData:class{constructor(form){this.fields=form.fields;}get(k){const v=this.fields[k];return Array.isArray(v)?v[0]:v??null;}getAll(k){const v=this.fields[k];return v==null?[]:Array.isArray(v)?v:[v];}}};vm.createContext(ctx);require('./ui_reference_helpers.cjs')(ctx);const scaffold=fs.readFileSync(path.join(__dirname,'../src/workbench/static/scaffold.js'),'utf8');vm.runInContext(scaffold.slice(scaffold.indexOf('function scaffoldLeaves('),scaffold.indexOf('function criterionList(')),ctx);vm.runInContext(scaffold.slice(scaffold.indexOf('function requirementDrafts('),scaffold.indexOf('function requirementEntryControl(')),ctx);ctx.requirementsSwitch=()=>'<nav aria-label="Requirements view">Requirements · Team input &amp; reviews</nav>';vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/sponsor.js'),'utf8'),ctx);return {ctx,run:s=>vm.runInContext(s,ctx)};}
test('framing maps Core Value fields separately and retains historical risks and alternatives',()=>{const h=harness(),html=h.run('sponsorFraming()');for(const t of ['Core Value Statement','Benefits','Why now','A retained risk','A retained alternative','An actual saved value proposition'])assert.ok(html.includes(t),t);assert.doesNotMatch(html,/<Private project>/);assert.doesNotMatch(html,/10 MB|up to 7|Connected<|70 KB/);const fields={name:'Project',context:'Context',statement:'Problem','summary-problem':'Details','summary-solution':'Solution','summary-risk':'Risk','summary-options':'Options','fit-value':'Value','fit-gains':'Benefits','fit-why_now':'Priority'};h.ctx.$=()=>({dataset:{kind:'framing'},fields,querySelectorAll:()=>[]});const data=h.run('sponsorFormData()');assert.equal(data.framing.statement,'Problem');assert.equal(data.framing.summary.risk,'Risk');assert.equal(data.framing.summary.options,'Options');assert.equal(data.fit.value,'Value');assert.equal(data.fit.gains,'Benefits');assert.equal(data.fit.why_now,'Priority');});
test('individual answer items preserve multiline entries and q4 remains structured roles',()=>{const h=harness();h.ctx.$=()=>({dataset:{kind:'answer',question:'q10'},fields:{answer:['First line\nSecond line','Another item']}});const a=h.run('sponsorFormData().answers.q10');assert.deepEqual(Array.from(a.items),['First line\nSecond line','Another item']);assert.equal(a.confirmed,false);assert.equal(a.roles.length,0);const roles=h.run('sponsorRoles(sponsorInfo().brief.answers.q4)');for(const name of ['name','does','needs','where','often'])assert.ok(roles.includes('role-0-'+name));assert.match(roles,/Receptionist/);});
test('question resource rail, review outline and coverage preserve real states without a readiness score',()=>{const h=harness(),html=h.run('sponsorBrief()');assert.match(html,/Context resources/);assert.match(html,/AI partner/);assert.match(html,/How to approach this/);assert.doesNotMatch(html,/class="sponsor-prompt"/);assert.match(html,/Core Value Statement/);assert.match(html,/Q2–Q23/);assert.doesNotMatch(html,/Context readiness|pts|Previous|Next:/);h.run("sponsorResources='documents'");assert.match(h.run('sponsorBrief()'),/Add documents in Business Intent/);const review=h.run('sponsorReview()');for(const t of ['Business Intent outline','Review Business Intent','Response coverage','Share Business Intent for review','Requirements set up','A retained risk'])assert.ok(review.includes(t),t);assert.doesNotMatch(review,/Counts fully toward readiness|AI draft, not yet confirmed|Publish v1/);assert.match(review,/data-action="sponsor-share" class="primary" disabled/);});
test('sponsor stage navigation saves before moving and blocks navigation when saving fails',async()=>{const h=harness(),calls=[];h.ctx.saveBeforeProjectChange=async()=>calls.push('save');h.ctx.render=()=>calls.push('render');await h.run("sponsorAction('sponsor-step','planning')");assert.deepEqual(calls,['save','render']);assert.equal(h.ctx.view,'planning');calls.length=0;h.ctx.saveBeforeProjectChange=async()=>{throw Error('Offline');};await assert.rejects(h.run("sponsorAction('sponsor-step','review')"),/Offline/);assert.equal(h.ctx.view,'planning');assert.equal(calls.length,0);});

test('direction review keeps every sharing prerequisite and current packet inspection',()=>{
 const h=harness();h.ctx.preparedPacketButton=p=>`<button data-action="packet" data-id="${p.ref.id}">Inspect context packet</button>`;
 const panel=()=>h.run("sponsorDirectionReview(state.intake.draft,null,null,{ref:{id:'PACKET-current'}})");
 for(const missing of ['value','requirements','answer']){
  h.ctx.state.intake.value_checkpoint={current:missing!=='value'};h.ctx.state.intake.scaffold_current=missing!=='requirements';h.ctx.state.intake.gaps=missing==='answer'?['value']:[];
  assert.match(panel(),/data-action="sponsor-share" class="primary" disabled/);
 }
 h.ctx.state.intake.gaps=[];const before=JSON.stringify(h.ctx.state),html=panel();
 assert.match(html,/data-action="sponsor-share" class="primary" >/);assert.match(html,/data-action="packet" data-id="PACKET-current"/);assert.match(html,/Publishing direction does not approve requirements/);assert.equal(JSON.stringify(h.ctx.state),before);
});
test('document context keeps answered progress distinct from checked completion',()=>{
 const h=harness(),answers=h.ctx.state.sponsor.brief.answers;
 for(const q of h.ctx.state.sponsor.questions.slice(0,3))answers[q.id].completed=true;
 const before=JSON.stringify(h.ctx.state),html=h.run('sponsorReview()');
 assert.match(html,/<summary>Source details<\/summary>/);assert.match(html,/INTAKE-001@7/);assert.doesNotMatch(html,/<dt>Record<\/dt>/);assert.match(html,/<dt>Owner<\/dt><dd>Priya<\/dd>/);
 assert.match(html,/<dt>Answered<\/dt><dd>22 of 22<\/dd>/);assert.match(html,/Marked complete 3 of 22/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});
test('role reading retains structured, multiline and legacy answers without rewriting them',()=>{
 const h=harness(),role={name:'<Staff> & support',does:'First task\nSecond task',needs:'A named response',where:'Front desk <A>',often:'Not established'};
 h.ctx.role=role;const before=JSON.stringify(role),html=h.run('sponsorRoleRead(role)');
 for(const title of ['What they do','What they need','Where / when','How often'])assert.ok(html.includes(title));
 assert.match(html,/&lt;Staff> &amp; support/);assert.match(html,/First task\nSecond task/);assert.match(html,/Front desk &lt;A>/);assert.equal(JSON.stringify(role),before);
 h.ctx.role={name:'Legacy text\nKept together'};const legacy=h.run('sponsorRoleRead(role)');assert.match(legacy,/Legacy text\nKept together/);assert.equal((legacy.match(/Not supplied/g)||[]).length,4);
 h.ctx.state.sponsor.brief.answers.q4.roles=[role,h.ctx.role];const stateBefore=JSON.stringify(h.ctx.state),draft=h.run('sponsorReview()');
 h.ctx.snapshot={title:'Saved direction',sponsor_brief:h.ctx.state.sponsor.brief,values:h.ctx.state.intake.draft.body.values,goal_snapshot:{},scaffold:[]};h.ctx.valueFitSnapshot=()=>'';h.ctx.valuePreview=()=>'';
 const published=h.run('sponsorSharedSnapshot(snapshot)');
 for(const text of ['&lt;Staff> &amp; support','Legacy text\nKept together','What they need']){assert.ok(draft.includes(text));assert.ok(published.includes(text));}
 assert.equal(JSON.stringify(h.ctx.state),stateBefore);
});
test('answer status chips reflect only population and the saved personal completion marker',()=>{
 const h=harness();h.ctx.answer={items:['Saved answer'],roles:[],completed:false,confirmed:true};
 assert.match(h.run('sponsorAnswerStatus(answer)'),/Status: Started/);
 h.ctx.answer.completed=true;assert.match(h.run('sponsorAnswerStatus(answer)'),/Status: Completed/);
 h.ctx.answer.items=[];assert.match(h.run('sponsorAnswerStatus(answer)'),/Status: Not started/);
 assert.match(h.run('sponsorAnswerStatus(answer)'),/does not publish, validate or approve/);
});
test('earlier direction responses stay inspectable without appearing to assess the current draft',()=>{
 const h=harness();h.ctx.state.actors.sam={role:'Research'};h.ctx.state.actors.lee={role:'Design'};
 h.ctx.reviewCase={ref:{id:'CASE-1',revision:4},body:{source_draft:{id:'INTAKE-001',revision:3},status:'published',reviewers:['sam','lee']},ready:true,reviews:{sam:{body:{disposition:'ready-for-investigation'}},lee:{body:{disposition:'changes-requested'}}}};
 const panel=()=>h.run('sponsorDirectionReview(state.intake.draft,reviewCase,true,null)'),before=JSON.stringify(h.ctx.reviewCase),html=panel();
 assert.match(html,/<details class="direction-review-section direction-review-history">/);assert.match(html,/Reviewed Business Intent · Different from this draft/);assert.match(html,/Different from this draft/);assert.match(html,/<dt>Research<\/dt><dd>Ready to investigate within limits<\/dd>/);assert.match(html,/<dt>Design<\/dt><dd>Changes or clarification needed<\/dd>/);assert.match(html,/data-action="pflow-business-intent"/);assert.doesNotMatch(html,/data-action="intake-publish"/);assert.equal(JSON.stringify(h.ctx.reviewCase),before);
 h.ctx.reviewCase.body.status='reviewing';assert.match(panel(),/data-action="intake-publish" data-id="CASE-1"/);assert.doesNotMatch(panel(),/direction-review-history/);
 h.ctx.reviewCase.ready=false;h.ctx.reviewCase.body.source_draft.revision=7;assert.doesNotMatch(panel(),/Different from this draft|direction-review-history/);assert.match(panel(),/id="direction-review-shared"/);
});

test('rapid navigation cannot race a pending draft save',async()=>{const h=harness();let release;h.ctx.saveBeforeProjectChange=()=>new Promise(r=>release=r);const first=h.run("sponsorAction('sponsor-step','planning')");await h.run("sponsorAction('sponsor-step','review')");assert.equal(h.ctx.view,'intent');release();await first;assert.equal(h.ctx.view,'planning');assert.equal(h.run('sponsorActionPending'),false);});
test('document drop and browse use saved ingestion without launching model analysis',async()=>{const h=harness(),calls=[];h.ctx.btoa=s=>Buffer.from(s,'binary').toString('base64');h.ctx.saveSponsorDraft=async()=>calls.push('save');h.ctx.command=async(action,data)=>calls.push({action,data});h.ctx.load=async()=>calls.push('load');h.ctx.toast=t=>calls.push(t);await h.run("sponsorUploadFile({name:'fictional.txt',size:5,arrayBuffer:async()=>new Uint8Array([104,101,108,108,111]).buffer})");assert.equal(calls[0],'save');assert.equal(calls[1].action,'intake-source');assert.equal(calls[1].data.filename,'fictional.txt');assert.equal(calls[1].data.content,'aGVsbG8=');assert.equal(calls[1].data.role,'background');assert.ok(!calls.some(c=>c?.action==='intake-coach'));});
test('oversize documents stop before reading or ingestion',async()=>{const h=harness(),messages=[];h.ctx.saveSponsorDraft=async()=>{};h.ctx.command=()=>assert.fail('Must not ingest');h.ctx.toast=t=>messages.push(t);await h.run("sponsorUploadFile({size:6*1024*1024,arrayBuffer:()=>{throw Error('Must not read')}})");assert.deepEqual(messages,['Choose a document under 5 MB.']);});

test('a project without a sponsor draft has distinct brief and planning views without mutating records',()=>{
 const h=harness();h.ctx.state.sponsor=null;h.ctx.state.intake.draft=null;
 h.ctx.state.records=[{kind:'intent',ref:{id:'INT-1',revision:2},body:{text:'Protect the reporting workflow',intake:{why_now:'Prevent repeated interruptions'}}},{kind:'requirement',ref:{id:'REQ-1',revision:3},body:{title:'Retain report progress',text:'Preserve the local draft',status:'proposed',acceptance_criteria:'Resume after interruption'}},{kind:'requirement-drawer',ref:{id:'DRAWER-1',revision:1},body:{label:'Functional'}}];
 const before=JSON.stringify(h.ctx.state),brief=h.run('sponsorScreen()'),planning=h.run('sponsorRequirements()');
 assert.match(brief,/<h1>Business Intent<\/h1>/);assert.match(brief,/Protect the reporting workflow|Prevent repeated interruptions/);assert.match(brief,/Create Business Intent/);assert.doesNotMatch(brief,/Create sponsor draft/);
 for(const t of ['Requirements set up','Requirement drawers','Retain report progress','Resume after interruption','REQ-1@3'])assert.ok(planning.includes(t),t);
 assert.doesNotMatch(planning,/intake-start-form|Create Business Intent|Create sponsor draft/);assert.equal(JSON.stringify(h.ctx.state),before);
});
test('the consolidated hub retains requirements with no matching editable candidate',()=>{
 const h=harness();h.ctx.state.records=[{kind:'requirement',ref:{id:'REQ-shared',revision:4},body:{title:'Published requirement',text:'Saved shared condition',acceptance_criteria:'Saved shared criterion',status:'approved'}}];
 h.ctx.state.intake.draft.body.scaffold=[{key:'experience',label:'Experience',included:true,children:[]}];
 const before=JSON.stringify(h.ctx.state),html=h.run('sponsorRequirements()');
 assert.match(html,/Actual connected scaffold form/);
 assert.doesNotMatch(html,/Project records|Drawer definitions/);for(const text of ['Additional requirements','Published requirement','Saved shared criterion','REQ-shared@4'])assert.ok(html.includes(text),text);
 assert.equal(JSON.stringify(h.ctx.state),before);
});
test('shared goals and all KPIs remain visible even with no drawers or private intake',()=>{
 const h=harness();h.ctx.state.sponsor=null;h.ctx.state.intake.draft=null;
 h.ctx.state.records=[{kind:'goal',ref:{id:'G-one',revision:2},body:{title:'Recover reporting',outcome:'Less lost work'}},{kind:'success-measure',ref:{id:'M-one',revision:3},body:{name:'Report completion rate',target:'Fictional 90%',goal_ids:['G-one']}}];
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/goals.js'),'utf8'),h.ctx);
 const before=JSON.stringify(h.ctx.state),html=h.run('sponsorRequirements()');
 for(const t of ['Performance Indicators','Recover reporting','Report completion rate','Fictional 90%','Version 3','M-one@3'])assert.ok(html.includes(t),t);
 assert.equal(JSON.stringify(h.ctx.state),before);
});
test('Business Intent menu opens its named opening stage after planning or review',()=>{
 const h=harness(),app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');
 vm.runInContext(app.slice(app.indexOf('function selectWorkspaceView('),app.indexOf('function render(')),h.ctx);
 h.run("sponsorStage='review';intakeStep='review';intakeCaseId='OLD';selectWorkspaceView('planning');selectWorkspaceView('intent')");
 assert.equal(h.ctx.view,'intent');assert.equal(h.run('sponsorStage'),'framing');assert.equal(h.ctx.intakeStep,'rationale');assert.equal(h.ctx.intakeCaseId,null);assert.match(h.run('sponsorScreen()'),/Business Intent/);
});
test('an uninitialized project cannot override the selected sponsor page with a shared welcome screen',()=>{
 const h=harness(),app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');let html;
 Object.assign(h.ctx,{window:{scrollTo(){}},navigationCollapsed:false,projectPageIdentity:()=>'',projectStatusLine:()=>'',appHeader:()=>'',persistentProjectNavigation:()=>'',projectTaskNavigation:()=>'',syncNavigationButton:()=>{},projectControl:()=>'',accountHeader:()=>'',sponsorFlowActive:()=>false,$:()=>({set innerHTML(value){html=value;}})});
 h.ctx.state.initialized=false;h.ctx.sponsorRequirements=()=>'<h1>Planning destination</h1>';h.ctx.intakeScreen=()=>'<h1>Brief destination</h1>';
 for(const name of ['thoughtPartnerScreen','domainBriefsScreen','overview','deliveryScreen','requirements','domainScreen','preflightScreen','reviews','decisions','packetsScreen','projectsScreen'])h.ctx[name]=()=>'';
 vm.runInContext(app.match(/function lockedRequirementsSetup\(\)\{[^\n]+/)[0],h.ctx);vm.runInContext(app.slice(app.indexOf('function render('),app.indexOf('function head(')),h.ctx);
 h.ctx.view='planning';h.run('render()');assert.match(html,/Planning destination/);
 h.ctx.view='intent';h.run('render()');assert.match(html,/Brief destination/);
});
test('framing exposes connection shortcuts and leaves connector configuration in Settings',()=>{
 const h=harness(),html=h.run('sponsorFraming()');assert.match(html,/Saved connection shortcuts/);assert.doesNotMatch(html,/Bring in more context|Configure<|MCP to pull in|Workshop boards|Meeting recaps/);
});
test('sponsor workflow stays visible without embedding a workspace or settings dropdown',()=>{
 const h=harness(),html=h.run('sponsorWorkspaceBar()');assert.match(html,/Breadcrumb/);assert.doesNotMatch(html,/sponsor-steps|sponsor-area-title|sponsor-workspace-menu|<summary>Workspace|settings-navigation/);
});
test('creating an empty private brief does not hide the configured requirement categories',()=>{
 const h=harness(),before=JSON.stringify(h.ctx.state);const html=h.run('sponsorRequirements()');assert.match(html,/Requirement drawers/);assert.match(html,/Existing drawer browser/);assert.equal(JSON.stringify(h.ctx.state),before);
});


test('planning reads goals from Business Intent and shows missing information on drawer items without a separate alert panel',()=>{
 const h=harness(),draft=h.ctx.state.intake.draft.body;
 draft.scaffold=[{key:'experience',included:true,label:'Experience',children:[
  {key:'capture',included:true,label:'Capture',requirement:'Retain work',acceptance_criteria:''},
  {key:'unwritten',included:true,label:'Potential future area',requirement:''},
  {key:'excluded',included:false,label:'Excluded private option',requirement:'Draft only'}]}];
 h.ctx.state.intake.gaps=['value'];
 h.ctx.state.goals.goals=[{id:'G-one',body:{title:'Capture usable feedback',outcome:'Reduce reporting effort'}}];
 h.ctx.state.goals.measures=[
  {id:'M-one',body:{name:'Completion',baseline:'',target:'90%'}},
  {id:'M-inactive',body:{name:'Inactive KPI',active:false}}];
 Object.assign(h.ctx,{roleSelect:()=>'',requirementAgentControls:()=>'',drawerSource:()=>'',drawerEditField:(n,key,title,value)=>`<textarea id="drawer-${key}-${n}" name="${key}">${h.ctx.esc(value||'')}</textarea>`});
 for(const name of ['goals.js','scaffold.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/'+name),'utf8'),h.ctx);
 const before=JSON.stringify(h.ctx.state),html=h.run('sponsorRequirements()');
 // Goals and measures are edited with the Core Value Statement in Business Intent (step 1); planning reads them.
 assert.match(html,/data-action="sponsor-step" data-id="framing">Edit in Business Intent</);
 assert.doesNotMatch(html,/data-action="goals-add"/);assert.doesNotMatch(html,/data-goal-field=/);
 assert.match(html,/Capture usable feedback/);
 assert.match(html,/Needs acceptance criteria/);
 assert.match(html,/1 need criteria/);
 assert.match(html,/Complete these intake answers/);
 assert.doesNotMatch(html,/Needs your attention|planning-attention|kpi-gaps/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});

test('mapped requirements stay with their candidates rather than duplicating the shared list',()=>{
 const h=harness();h.ctx.state.intake.draft.body.scaffold=[{key:'experience',included:true,requirements:[{id:'REQ-shared',requirement:'Private candidate'}],children:[]}];
 h.ctx.state.records=[{kind:'requirement',ref:{id:'REQ-shared',revision:4},body:{title:'Shared record',text:'Approved wording',acceptance_criteria:'Approved criterion',status:'approved'}}];
 const before=JSON.stringify(h.ctx.state),html=h.run('sponsorRequirements()');assert.doesNotMatch(html,/Additional requirements/);assert.match(html,/Requirements set up/);assert.doesNotMatch(html,/aria-label="Requirements view"/);assert.equal(JSON.stringify(h.ctx.state),before);
});


test('routing guidance separates unresolved failure modes without clearing saved exclusions',()=>{
 const h=harness(),before=JSON.stringify(h.ctx.state.sponsor.brief.answers.q15);
 h.run("sponsorQuestion='q12'");const html=h.run('sponsorBrief()');
 for(const t of ['path is known but not available','technical step fails','Use existing answers and decisions first','Undecided is valid'])assert.ok(html.includes(t),t);
 assert.ok(html.includes('Saved q12'));assert.equal(JSON.stringify(h.ctx.state.sponsor.brief.answers.q15),before);
 const configured=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/workbench/config/sponsor_questions.json')));
 assert.equal(JSON.stringify(h.run('sponsorQuestionCatalog')),JSON.stringify(configured));
});

test('question circles distinguish content from completion without reinterpreting historical confirmation',()=>{
 const h=harness(),answers=h.ctx.state.sponsor.brief.answers;
 answers.q2={items:[],roles:[],confirmed:false,completed:false};
 answers.q3={items:['We do not yet know the accountable owner.'],roles:[],confirmed:false,completed:true};
 answers.q5.confirmed=true;
 const before=JSON.stringify(h.ctx.state),html=h.run('sponsorBrief()');
 assert.match(html,/Q2<\/span>[\s\S]*?aria-label="Not started"/);
 assert.match(h.run('sponsorStateMark(sponsorInfo().brief.answers.q3)'),/is-complete.*aria-label="Completed"/);
 assert.match(h.run('sponsorStateMark(sponsorInfo().brief.answers.q5)'),/is-started.*aria-label="Started"/);
 assert.match(h.run('sponsorProgress()'),/aria-label="Completed">1 of 22/);
 assert.match(html,/name="completed"[^>]*disabled/);
 assert.doesNotMatch(html,/name="confirmed"|I have reviewed this response|meter[^>]*Confirmed|To confirm/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});
test('saving unchanged wording retains historical confirmation while edits do not inherit it',()=>{
 const h=harness(),answer=h.ctx.state.sponsor.brief.answers.q2;
 answer.confirmed=true;
 const form={dataset:{kind:'answer',question:'q2'},fields:{answer:answer.items.slice(),completed:'on'}};
 h.ctx.$=()=>form;
 assert.equal(h.run('sponsorFormData().answers.q2.confirmed'),true);
 assert.equal(h.run('sponsorFormData().answers.q2.completed'),true);
 form.fields.answer=['A revised answer'];
 assert.equal(h.run('sponsorFormData().answers.q2.confirmed'),false);
 assert.equal(answer.confirmed,true);
});
test('checking completion saves the answer, while save failure leaves it started and retains the text',async()=>{
 const h=harness(),marks=[{}],progress={},status={},checkbox={checked:true,disabled:false},form={dataset:{kind:'answer',question:'q2'},fields:{answer:['An explicitly unresolved question']}};
 h.ctx.state.sponsor.brief.answers.q2={items:[],roles:[],confirmed:false,completed:false};
 h.ctx.$=selector=>selector==='#sponsor-editor'?form:selector==='#sponsor-save-status'?status:selector==='#sponsor-editor [name=completed]'?checkbox:null;
 h.ctx.FormData=class{get(name){return name==='completed'&&checkbox.checked?'on':null;}getAll(name){return form.fields[name]||[];}};
 h.ctx.document.querySelectorAll=()=>marks;
 h.ctx.document.querySelector=selector=>selector==='.sponsor-heading-actions'?progress:null;
 h.ctx.load=async()=>{};
 h.ctx.render=()=>{throw Error('Completion must not redraw the page');};
 h.ctx.command=async()=>{throw Error('Offline');};
 await assert.rejects(h.run("sponsorAction('sponsor-complete')"),/Offline/);
 assert.equal(h.ctx.pageDirty,true);
 assert.equal(checkbox.checked,false);
 assert.equal(status.textContent,'Not saved');
 assert.match(marks[0].outerHTML,/aria-label="Started"/);
 assert.equal(form.fields.answer[0],'An explicitly unresolved question');
 checkbox.checked=true;
 h.ctx.command=async(action,data)=>{assert.equal(action,'sponsor-save');h.ctx.state.sponsor.brief.answers.q2=JSON.parse(JSON.stringify(data.answers.q2));};
 await h.run("sponsorAction('sponsor-complete')");
 assert.equal(h.ctx.pageDirty,false);
 assert.equal(status.textContent,'Draft saved');
 assert.match(marks[0].outerHTML,/aria-label="Completed"/);
 assert.match(progress.innerHTML,/aria-label="Completed">1 of 22/);
 assert.equal(h.ctx.state.sponsor.brief.answers.q2.completed,true);
 assert.equal(h.ctx.state.sponsor.brief.answers.q2.confirmed,false);
});
test('Business Intent Ask is advisory and Record assessment is a separate consented action',async()=>{
 const h=harness(),calls=[],dialogs=[],composer={value:'Challenge the business hypothesis.'};
 h.ctx.coachInfo=()=>({sources:[{ref:{id:'SOURCE',revision:2},body:{title:'Selected source'}}],runs:[],model:{configured:true}});
 h.ctx.$=selector=>selector==='#sponsor-framing-message'?composer:null;
 h.ctx.modal=(title,body,label,handler)=>dialogs.push({title,body,label,handler});
 h.ctx.command=async(action,data)=>{calls.push({action,data});return {ref:{id:'offline-fixture'}};};
 await h.run("sponsorAction('sponsor-ask')");assert.equal(calls.length,0);
 assert.equal(dialogs[0].label,'Ask');assert.match(dialogs[0].body,/advice, without a rating/);assert.doesNotMatch(dialogs[0].body,/analysis_scope|two model requests/);
 await dialogs[0].handler({getAll:()=>['SOURCE']});assert.equal(calls[0].action,'intake-coach');assert.equal(calls[0].data.skill,'review-value');assert.equal(calls[0].data.message,composer.value);assert.equal(calls[0].data.sources[0].revision,2);assert.equal(calls[0].data.consent,true);
 await h.run("sponsorAction('sponsor-analyze')");assert.match(dialogs[1].body,/two model requests/);assert.match(dialogs[1].body,/freeze the material claims/);assert.doesNotMatch(dialogs[1].body,/analysis_scope/);assert.equal(calls.length,1);
 await dialogs[1].handler({get:()=> 'question',getAll:()=>[]});assert.equal(calls[1].data.skill,'assess-business');assert.match(calls[1].data.message,/exact saved business argument/);assert.equal(calls[1].data.consent,true);
 const html=h.run('sponsorFraming()');assert.equal((html.match(/data-action="sponsor-analyze"/g)||[]).length,1);assert.match(html,/Record assessment/);assert.match(html,/data-action="sponsor-ask"/);assert.doesNotMatch(html,/Save &amp; analyze|Analyze saved documents/);
});

test('Business Intent completion saves the live form without rendering, including checkbox and text state',async()=>{
 const h=harness(),field={value:'A user-authored hypothesis'},checkbox={checked:true},status={dataset:{},style:{}},form={dataset:{kind:'framing'},fields:{name:'Existing name',context:'Context',statement:'Problem','summary-problem':'Detail','summary-solution':'Solution','summary-risk':'Risk','summary-options':'Options','fit-value':field.value,'fit-gains':'Gain','fit-why_now':'Timing'},querySelectorAll:()=>[{dataset:{framingComplete:'fit-value'},checked:checkbox.checked}]};
 h.ctx.$=selector=>selector==='#sponsor-editor'?form:selector==='#sponsor-save-status'?status:null;
 h.ctx.render=()=>{throw Error('Completion must not redraw the page');};h.ctx.load=async()=>{};
 h.ctx.command=async(action,data)=>{assert.equal(action,'sponsor-save');assert.equal(data.framing_completed['fit-value'],true);assert.equal(data.fit.value,field.value);};
 await h.run("sponsorAction('sponsor-framing-complete','',null)");
 assert.equal(checkbox.checked,true);assert.equal(field.value,'A user-authored hypothesis');assert.equal(status.dataset.saveState,'saved');assert.equal(h.ctx.pageDirty,false);
});

test('Business Intent offers Save and focused review without completion or publication controls',()=>{
 const h=harness(),html=h.run('sponsorFraming()');
 assert.doesNotMatch(html,/data-framing-complete|Check Complete|sponsor-framing-complete/);
 assert.equal((html.match(/data-action="sponsor-framing-save"/g)||[]).length,10);
 assert.equal((html.match(/data-action="sponsor-review-field"/g)||[]).length,9);
 assert.match(html,/data-action="sponsor-review-field" data-id="statement"/);
});
test('Business Intent field Save preserves the editor without redrawing or calling a model',async()=>{
 const h=harness(),calls=[];h.ctx.saveSponsorDraft=async()=>calls.push('save');h.ctx.render=()=>assert.fail('Must preserve the current editor');h.ctx.command=()=>assert.fail('No additional command');
 await h.run("sponsorAction('sponsor-framing-save','statement',null)");assert.deepEqual(calls,['save']);
});
test('Review this field copies live text into the composer without saving, publishing or calling a model',async()=>{
 const h=harness(),field={value:'An unsaved hypothesis'},composer={value:'My existing question',focus(){},setSelectionRange(){}},form={querySelector:()=>field};
 h.ctx.$=s=>s==='#sponsor-editor'?form:s==='#sponsor-framing-message'?composer:null;
 h.ctx.saveBeforeProjectChange=()=>assert.fail('Must not save');h.ctx.command=()=>assert.fail('Must not call a model or mutate workflow');
 await h.run("sponsorAction('sponsor-review-field','statement',null)");
 assert.equal(composer.value,'My existing question\n\nReview the Problem field:\nAn unsaved hypothesis');assert.equal(field.value,'An unsaved hypothesis');
 await h.run("sponsorAction('sponsor-review-field','statement',null)");assert.equal((composer.value.match(/An unsaved hypothesis/g)||[]).length,1);
 field.value='A different proposed solution';await h.run("sponsorAction('sponsor-review-field','summary-solution',null)");
 assert.equal(composer.value,'My existing question\n\nReview the Solution field:\nA different proposed solution');assert.doesNotMatch(composer.value,/Problem|unsaved hypothesis/);
 assert.equal(field.value,'A different proposed solution');
});

test('locked sponsor navigation keeps the shared route separate from the explicitly opened saved draft',async()=>{
 const h=harness();h.ctx.state.intake.setup_governance={enabled:true,editable:false,message:'Later changes use Decisions & Issues.'};
 h.ctx.saveBeforeProjectChange=async()=>{};h.ctx.render=()=>{};h.ctx.document.querySelector=()=>({focus(){}});
 h.ctx.requirements=()=>'<h1>Requirements</h1>';
 await h.run("sponsorAction('sponsor-step','planning')");assert.equal(h.ctx.view,'requirements');
 const before=JSON.stringify(h.ctx.state);
 await h.run("sponsorAction('sponsor-setup-draft','')");assert.equal(h.ctx.view,'planning');
 h.ctx.head=(title,description,actions='')=>`<h1>${title}</h1><p>${description}</p>${actions}`;
 h.ctx.intakeDrawerForm=options=>options.readOnly?'<div>Retained private draft, read only</div>':'<div>Editable</div>';
 const html=h.run('sponsorRequirements()');assert.match(html,/<h1>Saved setup draft/);assert.match(html,/Retained private draft, read only/);assert.match(html,/Back to Requirements/);assert.equal(JSON.stringify(h.ctx.state),before);
 await h.run("sponsorAction('sponsor-step','planning')");assert.equal(h.ctx.view,'requirements');assert.equal(h.run('setupDraftPreviewProject'),null);
});


test('guided sponsor route skips locked setup without altering saved answer state',()=>{
 const h=harness(),before=JSON.stringify(h.ctx.state.sponsor.brief.answers);
 assert.equal(h.run('sponsorNextStep().stage'),'planning');
 h.ctx.state.intake.setup_governance={enabled:true,editable:false};
 assert.equal(h.run('sponsorNextStep().stage'),'review');
 const html=h.run('sponsorBrief()');assert.match(html,/data-action="sponsor-step" data-id="review"/);assert.match(html,/Review &amp; publish|Review & publish/);
 assert.equal(JSON.stringify(h.ctx.state.sponsor.brief.answers),before);
});
test('sponsor guidance explains investigation and explicit action without promising automatic analysis',()=>{
 const h=harness(),html=h.run("sponsorGuidance('framing')+sponsorGuidance('brief')+sponsorGuidance('review')");
 assert.match(html,/without assuming the proposed solution is right/);assert.match(html,/analysis starts only when you choose it/);
 assert.match(html,/personal progress marker/);assert.match(html,/deliberately publish/);
 assert.doesNotMatch(html,/Save & analyze|project dashboard/);
});


test('sponsor reviewer draft spans stages but stays isolated by actor, account and project',()=>{
 const h=harness();h.ctx.state.project.id='P-one';h.ctx.state.auth={account:{id:'account-one'}};
 h.run("sponsorReviewerWrite('Keep my unsent question <safe>.')");
 for(const screen of ['sponsorFraming()','sponsorBrief()'])assert.match(h.run(screen),/Keep my unsent question &lt;safe>\./);
 h.run('sponsorFit=true');const fit=h.run('sponsorBrief()');assert.match(fit,/data-reviewer-draft="sponsor-intake"/);assert.match(fit,/data-action="sponsor-ask"/);assert.match(fit,/Keep my unsent question &lt;safe>\./);
 h.ctx.state.actor='lee';assert.equal(h.run('sponsorReviewerMessage()'),'');
 h.ctx.state.actor='priya';h.ctx.state.project.id='P-two';assert.equal(h.run('sponsorReviewerMessage()'),'');
 h.ctx.state.project.id='P-one';h.ctx.state.auth.account.id='account-two';assert.equal(h.run('sponsorReviewerMessage()'),'');
 h.ctx.state.auth.account.id='account-one';assert.equal(h.run('sponsorReviewerMessage()'),'Keep my unsent question <safe>.');
});
test('sponsor Ask refuses empty questions and a composer still bound to a different role or project',async()=>{
 const h=harness();h.ctx.coachInfo=()=>({sources:[],runs:[],model:{configured:true}});h.ctx.modal=()=>assert.fail('No consent dialog for an invalid question');
 const composer={value:'',dataset:{}};h.ctx.$=()=>composer;await assert.rejects(h.run("sponsorAction('sponsor-ask')"),/Enter a question/);
 composer.value='A question from the old project';composer.dataset.reviewerDraftKey='previous-project';await assert.rejects(h.run("sponsorAction('sponsor-ask')"),/project or role changed/);
 assert.equal(h.run('sponsorReviewerMessage()'),'');
});

test('Business Intent holds the goals and success measures editor beside the Core Value Statement',()=>{
 const h=harness();h.ctx.state.goals.goals=[{id:'G-one',body:{title:'Capture usable feedback',outcome:'Reduce effort'}}];h.ctx.state.goals.measures=[{id:'M-one',body:{name:'Completion',baseline:'',target:'90%'}}];
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/goals.js'),'utf8'),h.ctx);
 const html=h.run('sponsorGoalsPanel()');
 assert.match(html,/id="sponsor-goals-form"/);assert.match(html,/The proof of the promise/);assert.match(html,/data-action="goals-add" data-id="goals"/);assert.match(html,/data-action="goals-add" data-id="measures"/);assert.match(html,/data-action="goals-save-draft"/);assert.match(html,/Capture usable feedback/);assert.match(html,/Completion/);
 assert.equal(JSON.stringify(h.run('goalsFormPayload({querySelector:()=>null})')),'{}');
});

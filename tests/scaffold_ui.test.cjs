const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function harness(){
 const p=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/workbench/config/intake_profile.json')));
 const scaffold=p.drawers.map(d=>({...d,included:true,rationale:'Synthetic',requirement:'',acceptance_criteria:'',children:d.children.map(c=>({...c,included:true,requirement:'',acceptance_criteria:'',rationale:'Synthetic'}))}));
 const ctx={state:{actor:'priya',actors:{priya:{name:'Priya'},sam:{name:'Sam'},maya:{name:'Maya'},alex:{name:'Alex'}},intake:{draft:{body:{scaffold,values:{}}},profile:{body:p},gaps:[],scaffold_current:true}},esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,para:s=>`<p>${s}</p>`,val:(t,s)=>t+': '+s,roleSelect:()=>'',drawerEditField:()=>'',requirementAgentControls:()=>'',drawerSource:()=>'',document:{addEventListener:()=>{}}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/signals.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/scaffold.js'),'utf8'),ctx);
 return {ctx,run:s=>vm.runInContext(s,ctx)};
}
test('hierarchy starts collapsed while exposing named specialist areas and their criteria',()=>{const h=harness();const html=h.run('intakeDrawerForm()');assert.equal((html.match(/class="card drawer-edit"/g)||[]).length,6);assert.equal((html.match(/class="subdrawer-edit"/g)||[]).length,19);assert.match(html,/Accessibility/);assert.match(html,/Ease of use and learnability/);assert.match(html,/Review criteria/);assert.match(html,/Evidence to provide/);assert.match(html,/Reassess when/);assert.doesNotMatch(html,/<details class="(?:card drawer-edit|subdrawer-edit)"[^>]* open/);});
test('assistant selection uses category and child IDs and inherits parent exclusion',()=>{const h=harness();h.ctx.state.intake.draft.body.scaffold[1].included=false;const child=h.run("scaffoldLeaves().find(d=>d.key==='experience/accessibility')");assert.equal(child.included,false);assert.equal(child.category,'Experience and usability');});
test('SME settings show owned categories editable and other categories view-only',()=>{const h=harness();h.ctx.state.actor='sam';const html=h.run("state.intake.profile.body.drawers.map(categoryProfileRow).join('')");assert.equal((html.match(/data-editable="true"/g)||[]).length,2);assert.equal((html.match(/data-editable="false"/g)||[]).length,4);assert.match(html,/Methods or standards/);assert.match(html,/When to reassess/);});
test('criterion text is escaped and an exclusion never looks like passed validation',()=>{const h=harness();const html=h.run("areaRead({label:'Test',included:false,owner:'sam',question:'Question',criteria:'<script>bad</script>',evidence:'Evidence',revisit:'Change',exclusion_reason:'Outside scope'})");assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);assert.match(html,/Excluded/);assert.match(html,/Reason for exclusion/);assert.doesNotMatch(html,/Passed|Complete/);});

function browseHarness(){
 const setupHelper=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8').match(/function lockedRequirementsSetup\(\)\{[^\n]+/)[0];
 const h=harness();Object.assign(h.ctx,{records:kind=>(h.ctx.state.records||[]).filter(r=>r.kind===kind),
  tag:t=>`<span>${t}</span>`,head:(t,s,a='')=>`<h1>${t}</h1><p>${s}</p>${a}`,requirementsSwitch:()=>'<button>Scaffold</button>',
  selected:null,requirementsMode:'scaffold',get:()=>null});h.ctx.state.records=[];h.ctx.state.intake.cases=[];
 const app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');
 vm.runInContext(app.slice(app.indexOf('function ratifiedRequirementRows('),app.indexOf('let requirementNavigationPending=')),h.ctx);
 vm.runInContext(app.slice(app.indexOf('function requirements(){'),app.indexOf('function requirementDetail(')),h.ctx);
 vm.runInContext(setupHelper,h.ctx);return h;
}
test('Setup preview shows six saved draft categories and nineteen areas before publication',()=>{
 const h=browseHarness(),before=JSON.stringify(h.ctx.state);
 const html=h.run('requirementDrawers()');
 assert.equal((html.match(/class="card scaffold-preview-category"/g)||[]).length,6);
 assert.equal((html.match(/class="subdrawer-read"/g)||[]).length,19);
 assert.match(html,/Experience and usability/);assert.match(html,/Accessibility/);assert.match(html,/Ease of use and learnability/);
 assert.match(html,/Draft scaffold/);assert.match(html,/Edit scaffold/);assert.doesNotMatch(html,/The scaffold begins|Open sponsor intake/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});
test('configured taxonomy is visible with no prepared scaffold and creates no requirements',()=>{
 const h=browseHarness();h.ctx.state.intake.draft.body.scaffold=[];
 const html=h.run('requirementDrawers()');assert.match(html,/Configured categories/);assert.match(html,/Template/);
 assert.equal((html.match(/scaffold-preview-category/g)||[]).length,6);
 assert.doesNotMatch(html,/Proposed requirement|Active|Approved|Edit scaffold/);assert.equal(h.ctx.state.records.length,0);
});
test('non-sponsor preview never exposes private draft wording or goals',()=>{
 const h=browseHarness();h.ctx.state.actor='sam';h.ctx.state.intake.draft.body.scaffold[0].question='PRIVATE DRAFT QUESTION';
 h.ctx.state.intake.draft.body.scaffold[0].requirement='PRIVATE PROPOSAL';h.ctx.state.intake.draft.body.goal_snapshot={goals:[{title:'PRIVATE GOAL'}]};
 const html=h.run('requirements()');assert.match(html,/No published requirement areas\./);assert.doesNotMatch(html,/PRIVATE|Configured categories/);
});
test('unpublished review snapshots remain inspectable outside the ratified shared baseline',()=>{
 const h=browseHarness();h.ctx.state.actor='lee';
 h.ctx.state.intake.cases=[{ref:{id:'CASE-1',revision:1},stale:['Intake changed'],body:{status:'reviewing',snapshot:{scaffold:[{key:'shared',label:'Released area',question:'Shared question',included:true,children:[]}]}}}];
 h.ctx.state.intake.draft.body.scaffold[0].question='PRIVATE NEW WORDING';
 const publicView=h.run('requirementDrawers({sharedOnly:true})');assert.equal(publicView,'');
 const html=h.run('requirementDrawers()');assert.match(html,/Released area/);assert.match(html,/Shared for direction review/);assert.match(html,/needs reconsideration/);assert.doesNotMatch(html,/PRIVATE|Edit scaffold/);
 h.ctx.state.intake.cases[0].body.status='declined';assert.equal(h.run('requirementScaffoldSource().mode'),'template');
});
test('published drawers keep priority and exact records, despite a newer private scaffold',()=>{
 const h=browseHarness();h.ctx.state.records=[{kind:'requirement-drawer',ref:{id:'DRAWER-1',revision:2},body:{label:'Published category',question:'Published question',status:'active'}},{kind:'requirement',ref:{id:'REQ-ratified',revision:2},body:{drawer_id:'DRAWER-1',title:'Ratified requirement',text:'Preserve the ratified wording.',status:'approved'}}];
 const html=h.run('requirements()');assert.match(html,/Published category/);assert.match(html,/data-id="DRAWER-1"/);
 assert.doesNotMatch(html,/Draft scaffold|Configured categories|Accessibility/);
});
test('saved draft shows stale, exclusion and proposed wording without implying approval',()=>{
 const h=browseHarness();h.ctx.state.intake.scaffold_current=false;const d=h.ctx.state.intake.draft.body.scaffold[0];
 d.included=false;d.children[0].requirement='Proposed test condition';d.children[0].exclusion_reason='Outside the intended scope';
 const html=h.run('requirementDrawers()');assert.match(html,/Refresh and review/);assert.match(html,/Excluded/);assert.match(html,/Proposed test condition/);assert.match(html,/Outside the intended scope/);assert.doesNotMatch(html,/Approved/);
});
test('legacy flat profiles remain visible without inventing newer sub-drawers',()=>{
 const h=browseHarness();h.ctx.state.intake.draft.body.scaffold=[];
 h.ctx.state.intake.profile.body.drawers.forEach(d=>delete d.children);
 const html=h.run('requirementDrawers()');assert.equal((html.match(/scaffold-preview-category/g)||[]).length,6);
 assert.match(html,/0 sub-drawers/);assert.doesNotMatch(html,/Accessibility/);
});
test('scaffold preview escapes category and requirement text',()=>{
 const h=browseHarness();h.ctx.val=(label,s)=>label+': '+h.ctx.esc(s);h.ctx.para=s=>'<p>'+h.ctx.esc(s)+'</p>';
 const d=h.ctx.state.intake.draft.body.scaffold[0];d.label='<img src=x>';d.requirement='<script>bad</script>';d.question='<b>unsafe</b>';
 const html=h.run('requirementDrawers()');assert.doesNotMatch(html,/<img|<script>|<b>/);assert.match(html,/&lt;script>/);
});
test('saved goals and KPIs remain readable before draft drawers are prepared',()=>{
 const h=harness();h.ctx.state.intake.draft.body.scaffold=[];
 h.ctx.state.goals={goals:[{id:'G-one',body:{title:'Preserved outcome'}}],measures:[{id:'M-one',body:{name:'Preserved KPI'}}]};
 h.ctx.goalsRead=catalog=>catalog.goals.map(g=>g.body.title).join('')+catalog.measures.map(m=>m.body.name).join('');
 const before=JSON.stringify(h.ctx.state),html=h.run('intakeDrawerForm()');
 assert.match(html,/Preserved outcome/);assert.match(html,/Preserved KPI/);assert.doesNotMatch(html,/intake-drawers-form/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});
test('default categories remain templates without a saved intake profile or private draft',()=>{
 const h=browseHarness(),defaults=h.ctx.state.intake.profile.body.drawers;h.ctx.state.intake={draft:null,profile:null,scaffold_defaults:defaults,cases:[]};
 const before=JSON.stringify(h.ctx.state),html=h.run('requirementDrawers()');
 assert.equal((html.match(/scaffold-preview-category/g)||[]).length,6);assert.match(html,/Accessibility/);assert.match(html,/Template/);assert.doesNotMatch(html,/Approved|Edit scaffold/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});

test('planning exposes all category groups and area edit links while retaining definitions and drafts',()=>{
 const h=harness(),before=JSON.stringify(h.ctx.state),html=h.run('intakeDrawerForm({planning:true})');
 assert.equal((html.match(/class="drawer-edit planning-requirement-group"/g)||[]).length,6);
 assert.equal((html.match(/data-planning-detail="area-/g)||[]).length,19);
 assert.match(html,/aria-controls="drawer-settings-experience"/);
 assert.match(html,/data-id="area-requirements-experience--accessibility">Accessibility<\/a>/);
 assert.match(html,/Ease of use and learnability/);
 assert.match(html,/Definition &amp; ownership/);assert.match(html,/Intake basis/);
 assert.doesNotMatch(html,/<details class="card drawer-edit"/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});
test('planning preserves flat and category-level drafts and targets missing criteria directly',()=>{
 const h=harness(),d=h.ctx.state.intake.draft.body.scaffold[1];
 d.requirement='Preserve a category-level obligation';d.acceptance_criteria='Original category criterion';
 let html=h.run('intakeDrawerForm({planning:true})');assert.match(html,/Category-level requirements/);
 assert.match(html,/data-requirement-id="REQ-INTAKE-experience"/);
 d.children=[];d.acceptance_criteria='';html=h.run('intakeDrawerForm({planning:true})');
 assert.match(html,/data-id="draft-REQ-INTAKE-experience-acceptance_criteria"/);
 assert.match(html,/Needs acceptance criteria/);
});

test('an area renders independent requirement titles and criteria without mutating legacy or collection data',()=>{
 const h=harness(),path='experience/accessibility',area=h.ctx.state.intake.draft.body.scaffold[1].children[0];
 area.requirements=[{id:'REQ-INTAKE-'+path+'--'+'a'.repeat(12),title:'Keyboard access',requirement:'Operate without a pointer',acceptance_criteria:'Keyboard-only completion',included:true},{id:'REQ-INTAKE-'+path+'--'+'b'.repeat(12),title:'Visible focus',requirement:'See the active control',acceptance_criteria:'Focus remains visible',included:true}];
 const before=JSON.stringify(area),html=h.run('requirementEntryList('+JSON.stringify(area)+','+JSON.stringify(path)+')');
 for(const text of ['Keyboard access','Keyboard-only completion','Visible focus','Focus remains visible','Add requirement to Accessibility'])assert.ok(html.includes(text),text);
 assert.equal((html.match(/class="requirement-draft"/g)||[]).length,2);
 assert.equal((html.match(/data-requirement-field="acceptance_criteria"/g)||[]).length,2);
 assert.equal(JSON.stringify(area),before);
});


test('planning places update beside changed basis and retains save without a tools menu',()=>{
 const h=harness();h.ctx.intakeNames={};
 const before=JSON.stringify(h.ctx.state),fresh=h.run('intakeDrawerForm({planning:true})');
 assert.doesNotMatch(fresh,/Scaffold tools|planning-tools|Update from Business Intent/);assert.match(fresh,/Save draft/);
 assert.equal(JSON.stringify(h.ctx.state),before);
 h.ctx.state.intake.scaffold_current=false;
 const changed=h.run('intakeDrawerForm({planning:true})');assert.match(changed,/Business Intent or category criteria changed/);
 assert.equal((changed.match(/data-action="intake-build"/g)||[]).length,1);assert.match(changed,/Update from Business Intent/);
 h.ctx.state.intake.gaps=['value'];const incomplete=h.run('intakeDrawerForm({planning:true})');
 assert.match(incomplete,/Complete these intake answers/);assert.match(incomplete,/data-action="intake-build" disabled>Update from Business Intent/);
 h.ctx.state.intake.draft.body.scaffold=[];assert.match(h.run('intakeDrawerForm({planning:true})'),/Prepare draft drawers/);
});

test('a private candidate links to its shared version without replacing approved wording or criteria',()=>{
 const h=harness(),draft={id:'REQ-shared',title:'Retain progress',requirement:'Private revision',acceptance_criteria:'Private checks',included:true};
 h.ctx.state.records=[{kind:'requirement',ref:{id:'REQ-shared',revision:4},body:{title:'Retain progress',text:'Approved wording',acceptance_criteria:'Approved checks',status:'approved'}}];
 const before=JSON.stringify([h.ctx.state,draft]),html=h.run('requirementEntryRow('+JSON.stringify(draft)+',{label:"Ease of use",included:true},"experience/ease")');
 assert.match(html,/data-action="requirement" data-id="REQ-shared"/);assert.match(html,/Shared version · v4 · approved/);assert.match(html,/Private revision/);assert.match(html,/Private checks/);assert.match(html,/These edits are private/);assert.doesNotMatch(html,/in Published requirements/);assert.equal(JSON.stringify([h.ctx.state,draft]),before);
});

test('shared category definitions remain reachable within the consolidated planning area',()=>{
 const h=harness();h.ctx.state.records=[{kind:'requirement-drawer',ref:{id:'DRW-experience',revision:3},body:{key:'experience'}}];
 const before=JSON.stringify(h.ctx.state),html=h.run('planningDrawerCategory(state.intake.draft.body.scaffold.find(d=>d.key==="experience"),{})');
 assert.match(html,/data-action="open-drawer" data-id="DRW-experience"/);assert.match(html,/Shared definition · v3/);assert.equal(JSON.stringify(h.ctx.state),before);
});

test('a research reconsideration is visible beside the requirement name without changing draft wording',()=>{
 const h=harness(),draft={id:'REQ-shared',title:'Returned status',requirement:'Keep the recorded wording.',acceptance_criteria:'Keep these checks.',included:true};
 h.ctx.state.records=[{kind:'requirement',ref:{id:draft.id,revision:1},body:{title:draft.title,text:draft.requirement,acceptance_criteria:draft.acceptance_criteria,status:'proposed'}},{kind:'need-context',ref:{id:'NEED',revision:2},body:{review_items:[{target:{id:draft.id,revision:1}}]}}];
 h.ctx.needContextRequirementNotice=()=>'<p>Review proposed research changes</p>';
 const before=JSON.stringify([h.ctx.state,draft]);h.ctx.draft=draft;const html=h.run('requirementEntryRow(draft,{label:"System behavior",included:true},"technology/behavior")');
 assert.match(html,/<summary>[\s\S]*Research update[\s\S]*<\/summary>/);assert.match(html,/Review proposed research changes/);assert.match(html,/Keep the recorded wording\./);assert.match(html,/Keep these checks\./);assert.equal(JSON.stringify([h.ctx.state,draft]),before);
});

test('the sponsor shared page excludes private setup drafts and configured templates',()=>{
 const h=browseHarness();h.ctx.state.intake.draft.body.scaffold[0].question='PRIVATE SETUP QUESTION';
 const before=JSON.stringify(h.ctx.state),html=h.run('requirements()');
 assert.match(html,/No published requirement areas\./);assert.doesNotMatch(html,/PRIVATE SETUP QUESTION|Draft scaffold|Configured categories/);assert.equal(JSON.stringify(h.ctx.state),before);
});


test('published categories distinguish requirement areas from proposals while retaining exact navigation and source context',()=>{
 const h=browseHarness();h.ctx.state.records=[
 {kind:'requirement-drawer',ref:{id:'CAT-tech',revision:2},body:{label:'Technology & integration',question:'How should systems connect?',status:'active'}},
 {kind:'requirement-drawer',ref:{id:'AREA-handoff',revision:3},body:{parent_id:'CAT-tech',label:'Handoffs',question:'What crosses the boundary?',status:'active'}},
 {kind:'requirement',ref:{id:'REQ-child',revision:4},body:{drawer_id:'AREA-handoff',title:'Preserve context',text:'Carry the original context.',acceptance_criteria:'The receiving system can inspect it.',status:'proposed'}},
 {kind:'requirement',ref:{id:'REQ-parent',revision:1},body:{drawer_id:'CAT-tech',title:'Audit trail',text:'Retain decisions.',acceptance_criteria:'Inspect each recorded decision.',status:'approved'}}];
 const before=JSON.stringify(h.ctx.state),html=h.run('requirementDrawers()');
 assert.match(html,/class="card section workbench-record-module" data-category="CAT-tech"/);assert.match(html,/<h2>Technology &amp; integration<\/h2>/);
 assert.match(html,/class="[^"]*requirement-area-shell[^"]*" data-drawer="AREA-handoff"/);
 assert.match(html,/<span class="requirement-area-title">Handoffs<\/span>/);assert.doesNotMatch(html,/<span class="requirement-object-label">Requirement area<\/span>/);
 for(const id of ['CAT-tech','AREA-handoff','REQ-parent','REQ-child'])assert.ok(html.includes('data-id="'+id+'"'),id);
 for(const text of ['2 requirements','Inspect each recorded decision.','Confidence: Not rated','REQ-child:v4','REQ-parent:v1'])assert.ok(html.includes(text),text);
 for(const region of ['Requirement','Acceptance criteria','Assessment'])assert.match(html,new RegExp('<h4>'+region+'</h4>'));
 assert.match(html,/<section class="requirement-record-assessment"[^>]*><header><h4>Assessment<\/h4>[\s\S]*?Confidence: Not rated/);
 assert.match(html,/Carry the original context\./);assert.match(html,/The receiving system can inspect it\./);assert.doesNotMatch(html,/>Active</);
 assert.doesNotMatch(html,/<details[^>]* open/);assert.equal(JSON.stringify(h.ctx.state),before);
});
test('empty or retired categories retain a drawer and their original status without invented requirements',()=>{
 const h=browseHarness();h.ctx.state.records=[{kind:'requirement-drawer',ref:{id:'CAT-empty',revision:1},body:{label:'Empty area',question:'An open question',status:'retired'}}];
 const before=JSON.stringify(h.ctx.state),html=h.run('requirementDrawers()');
 assert.match(html,/Scope &amp; review criteria/);assert.match(html,/Retired/);assert.match(html,/No requirements defined/);assert.match(html,/data-id="CAT-empty"/);assert.equal(JSON.stringify(h.ctx.state),before);
});
test('shared map includes published proposals without promoting unpublished snapshots or inventing validation',()=>{
 const h=browseHarness();h.ctx.state.records=[{kind:'requirement-drawer',ref:{id:'CAT',revision:1},body:{label:'Legacy setup area',status:'active'}},{kind:'requirement',ref:{id:'PENDING',revision:1},body:{drawer_id:'CAT',title:'Pending obligation',text:'Legacy proposed text',status:'proposed'}}];
 h.ctx.state.intake.cases=[{body:{status:'pending-review',snapshot:{scaffold:[{label:'Unpublished area',requirement:'Not ratified'}]}}}];
 const before=JSON.stringify(h.ctx.state),html=h.run('requirementDrawers({sharedOnly:true})');assert.match(html,/Pending obligation/);assert.doesNotMatch(html,/requirement-object-label|Requirement proposal|Requirement proposals/);assert.match(html,/PENDING:v1 · Proposed · Validation not recorded/);assert.match(html,/<h4>Assessment<\/h4>[\s\S]*?Confidence: Not rated/);assert.match(html,/Validation not recorded/);assert.match(html,/PENDING:v1/);assert.match(html,/data-action="requirement" data-id="PENDING"/);assert.doesNotMatch(html,/Unpublished area|Not ratified|>Ratified</);assert.equal(JSON.stringify(h.ctx.state),before);
});
function ratifiedCategoriesHarness(){
 const h=browseHarness();h.ctx.view='requirements';h.ctx.state.project={id:'PROJECT',version:1};h.ctx.state.records=[
 {kind:'requirement-drawer',ref:{id:'CAT-A',revision:1},body:{label:'Baseline A',question:'Shared A',status:'active'}},
 {kind:'requirement-drawer',ref:{id:'AREA-A',revision:1},body:{parent_id:'CAT-A',label:'Ratified area',status:'active'}},
 {kind:'requirement-drawer',ref:{id:'CAT-B',revision:1},body:{label:'Baseline B',question:'Shared B',status:'active'}},
 {kind:'requirement-drawer',ref:{id:'SHELL',revision:1},body:{label:'Empty shell',question:'Do not show empty metadata',status:'active'}},
 {kind:'requirement-drawer',ref:{id:'PENDING-CAT',revision:1},body:{label:'Candidate category',question:'Do not show candidate metadata',status:'active'}},
 {kind:'requirement-drawer',ref:{id:'PENDING-AREA',revision:1},body:{parent_id:'PENDING-CAT',label:'Candidate area',status:'active'}},
 {kind:'requirement',ref:{id:'RATIFIED-A',revision:2},body:{drawer_id:'AREA-A',title:'First ratified obligation',text:'Keep A.',status:'approved'}},
 {kind:'requirement',ref:{id:'RATIFIED-B',revision:3},body:{drawer_id:'CAT-B',title:'Second ratified obligation',text:'Keep B.',status:'approved'}},
 {kind:'requirement',ref:{id:'PENDING',revision:1},body:{drawer_id:'PENDING-AREA',title:'Candidate obligation',text:'Keep pending outside the baseline.',status:'proposed'}}];
 return h;
}
test('ratified ancestry remains separate while the published map includes proposals and empty shells',()=>{
 const h=ratifiedCategoriesHarness(),before=JSON.stringify(h.ctx.state),ids=h.run('ratifiedRequirementDrawerRows().map(d=>d.ref.id)');
 assert.deepEqual(Array.from(ids),['CAT-A','AREA-A','CAT-B']);
 const html=h.run('requirementDrawers({sharedOnly:true})'),control=h.run('ratifiedRequirementCategoryControl()');
 assert.match(html,/First ratified obligation|Second ratified obligation/);assert.match(control,/All categories/);assert.match(control,/Baseline A/);assert.match(control,/Baseline B/);
 for(const text of ['Empty shell','Candidate category','Candidate area','Candidate obligation','No requirements defined'])assert.ok((html+control).includes(text),text);assert.equal(JSON.stringify(h.ctx.state),before);
 h.ctx.state.records.find(r=>r.ref.id==='RATIFIED-B').body.status='proposed';assert.match(h.run('ratifiedRequirementCategoryControl()'),/Baseline B/);
});
test('category filtering changes only existing row visibility and preserves an unsent reviewer question',()=>{
 const h=ratifiedCategoriesHarness(),question={value:'Keep this exact unsent question.'},rows=[{dataset:{ratifiedCategory:'CAT-A'},hidden:false},{dataset:{ratifiedCategory:'CAT-B'},hidden:false}];
 h.ctx.document.querySelector=s=>s==='#main'?{querySelectorAll:()=>rows}:s==='#field-coach-question'?question:null;
 h.ctx.render=()=>assert.fail('Category filtering must not redraw the page');h.ctx.paintFieldCoach=()=>assert.fail('Category filtering must not redraw the reviewer');
 const before=JSON.stringify(h.ctx.state);assert.equal(h.run("filterRatifiedRequirementCategory('CAT-A')"),'CAT-A');assert.equal(rows[0].hidden,false);assert.equal(rows[1].hidden,true);assert.equal(question.value,'Keep this exact unsent question.');
 assert.match(h.run("ratifiedRequirementCategoryAttributes('CAT-B')"),/ hidden/);assert.equal(h.run("filterRatifiedRequirementCategory('NOT-PUBLISHED')"),'');assert.equal(rows[0].hidden,false);assert.equal(rows[1].hidden,false);assert.equal(JSON.stringify(h.ctx.state),before);
});
test('published drawer detail preserves proposals and routes changes to Accountability without editing',()=>{
 const h=browseHarness();h.ctx.view='requirements';h.ctx.state.actor='alex';h.ctx.state.records=[{kind:'requirement-drawer',ref:{id:'CAT',revision:1},body:{label:'Published area',question:'Source context',status:'active',owner:'alex'}},{kind:'requirement',ref:{id:'RATIFIED',revision:2},body:{drawer_id:'CAT',title:'Governing obligation',text:'Keep this version.',status:'approved'}},{kind:'requirement',ref:{id:'PENDING',revision:1},body:{drawer_id:'CAT',title:'Pending obligation',text:'Keep in Accountability.',status:'proposed'}}];
 h.ctx.get=id=>h.ctx.state.records.find(r=>r.ref.id===id);h.ctx.ref=()=>'';h.ctx.statusTag=s=>s;const before=JSON.stringify(h.ctx.state),html=h.run("drawerPage('CAT')");
 assert.match(html,/Governing obligation/);assert.match(html,/data-nav="review"/);assert.match(html,/Pending obligation/);assert.match(html,/RATIFIED:v2 · Ratified · Validation not recorded/);assert.match(html,/PENDING:v1 · Proposed · Validation not recorded/);assert.doesNotMatch(html,/requirement-object-label/);assert.match(html,/<h4>Assessment<\/h4>[\s\S]*?Confidence: Not rated/);for(const region of ['Requirement','Acceptance criteria','Assessment'])assert.match(html,new RegExp('<h4>'+region+'</h4>'));for(const id of ['RATIFIED','PENDING'])assert.match(html,new RegExp('data-action="requirement" data-id="'+id+'"'));for(const exact of ['RATIFIED:v2','PENDING:v1'])assert.ok(html.includes(exact));assert.doesNotMatch(html,/drawer-requirement|Add requirement/);assert.equal(JSON.stringify(h.ctx.state),before);
});

test('the shared page explains Business development provenance to every role and offers private draft access only to its sponsor',()=>{
 const h=browseHarness();h.ctx.state.intake.setup_governance={enabled:true,editable:false};
 for(const actor of ['priya','sam','lee','alex']){
  h.ctx.state.actor=actor;const before=JSON.stringify(h.ctx.state),html=h.run('requirements()');
  assert.match(html,/Business Intent/);
  assert.match(html,/Decisions & Issues/);
  if(actor==='priya')assert.match(html,/data-action="sponsor-setup-draft"/);else assert.doesNotMatch(html,/sponsor-setup-draft/);
  assert.equal(JSON.stringify(h.ctx.state),before);
 }
});

test('published map excludes explicit private scopes and keeps an unworded shell and its exact public context',()=>{
 const h=ratifiedCategoriesHarness();h.ctx.state.records.push(
 {kind:'requirement-drawer',scope:'actor:priya',ref:{id:'PRIVATE-CAT',revision:1},body:{label:'PRIVATE CATEGORY',question:'PRIVATE BASIS',status:'active'}},
 {kind:'requirement',scope:'actor:priya',ref:{id:'PRIVATE-REQ',revision:1},body:{drawer_id:'CAT-A',title:'PRIVATE WORDING',status:'proposed'}},
 {kind:'requirement-drawer',scope:'project:demo',ref:{id:'PUBLIC-SHELL',revision:1},body:{label:'Public investigation shell',question:'Which uncertainty matters?',criteria:'Exact source criterion',status:'active'}});
 const before=JSON.stringify(h.ctx.state),html=h.run('requirementDrawers({sharedOnly:true})'),control=h.run('ratifiedRequirementCategoryControl()');
 assert.match(html,/Public investigation shell/);assert.match(html,/Which uncertainty matters/);assert.match(html,/Exact source criterion/);assert.match(html,/No requirements defined/);assert.doesNotMatch(html+control,/PRIVATE CATEGORY|PRIVATE BASIS|PRIVATE WORDING|PRIVATE-REQ/);assert.equal(JSON.stringify(h.ctx.state),before);
});
test('definition completeness reports actual wording and criteria without a confidence or validation inference',()=>{
 const h=browseHarness(),record={kind:'requirement',scope:'project:demo',ref:{id:'CHECK',revision:2},body:{title:'A bounded proposal',text:'Actual wording',acceptance_criteria:'',status:'proposed'}};h.ctx.sample=record;
 const before=JSON.stringify(record),html=h.run('publishedRequirementRead(sample)');
 for(const text of ['Confidence: Not rated','Wording: Supplied','Acceptance criteria: Missing','Definition completeness does not establish evidence confidence or validation.','Validation not recorded','CHECK:v2'])assert.ok(html.includes(text),text);
 for(const region of ['Requirement','Acceptance criteria','Assessment'])assert.match(html,new RegExp('<h4>'+region+'</h4>'));assert.match(html,/<section class="requirement-record-assessment"[^>]*><header><h4>Assessment<\/h4>[\s\S]*?Confidence: Not rated/);assert.match(html,/data-action="requirement" data-id="CHECK"/);
 assert.doesNotMatch(html,/Confidence: (Low|Moderate|High)|>Validated</);assert.equal(JSON.stringify(record),before);
 record.body.status='approved';const approved=h.run('publishedRequirementRead(sample)');assert.match(approved,/CHECK:v2 · Ratified · Validation not recorded/);assert.doesNotMatch(approved,/requirement-object-label/);assert.match(approved,/<h4>Assessment<\/h4>[\s\S]*?Confidence: Not rated/);assert.match(approved,/Validation not recorded/);assert.doesNotMatch(approved,/>Validated</);
});
test('requirement drawer roles remain visible in rows and tiles without relabeling an empty investigation area',()=>{
 const h=browseHarness();h.ctx.sample={kind:'requirement',scope:'project:demo',ref:{id:'REQ-ROLE',revision:7},body:{title:'Preserve exact history',text:'Retain prior events.',acceptance_criteria:'An event remains traceable.',status:'proposed'}};
 const before=JSON.stringify(h.ctx.sample);
 for(const preview of [false,true]){
  const html=h.run(`publishedRequirementRead(sample,{preview:${preview}})`),summary=html.match(/<summary>([\s\S]*?)<\/summary>/)[1];
  assert.equal((summary.match(/class="workbench-object-type">Requirement<\/span>/g)||[]).length,1);
  assert.ok(summary.indexOf('workbench-object-type')<summary.indexOf('requirement-record-title'));
  assert.match(summary,/Preserve exact history/);assert.doesNotMatch(summary,/>Goal<|>Success measure</);
  assert.match(html,/REQ-ROLE:v7/);assert.match(html,/data-action="requirement" data-id="REQ-ROLE"/);
  assert.equal(JSON.stringify(h.ctx.sample),before);
 }
 h.ctx.area={kind:'requirement-drawer',ref:{id:'AREA-ONLY',revision:2},body:{label:'Investigate recovery',question:'Which interruptions matter?',status:'active'}};
 const shell=h.run('publishedAreaDrawer(area,[area],[])');assert.match(shell,/No requirements defined/);assert.doesNotMatch(shell,/workbench-object-type/);
});
test('editable requirement role does not replace its title target or saved wording',()=>{
 const h=harness();h.ctx.sample={id:'REQ-DRAFT',title:'Visible focus',requirement:'Show the active control.',acceptance_criteria:'Keyboard focus remains visible.',included:true};
 const before=JSON.stringify(h.ctx.sample),html=h.run('requirementEntryRow(sample,{label:"Accessibility"},"experience/accessibility")'),summary=html.match(/<summary>([\s\S]*?)<\/summary>/)[1];
 assert.match(summary,/<span class="workbench-object-heading"><span class="workbench-object-type">Requirement<\/span><a class="planning-text-link"/);
 assert.match(summary,/data-action="sponsor-planning-focus" data-id="draft-REQ-DRAFT-requirement">Visible focus<\/a>/);
 assert.match(html,/data-requirement-id="REQ-DRAFT"/);assert.match(html,/Show the active control\./);assert.match(html,/Keyboard focus remains visible\./);
 assert.doesNotMatch(html,/<details[^>]+ open/);assert.equal(JSON.stringify(h.ctx.sample),before);
});
test('requirement activity comes from the latest explicit open review rather than publication or evidence counts',()=>{
 const h=harness(),r={kind:'requirement',scope:'project:demo',ref:{id:'REQ',revision:4},body:{status:'proposed',published_at:'2026-11-21',requirement_refs:[{id:'REPORT',revision:9}]}},make=(id,status,target='REQ')=>({ref:{id,revision:1},body:{status,target:{id:target,revision:4}},stale:[]});h.ctx.sample=r;
 h.ctx.state.cases=[make('CLOSED','approved'),make('OTHER','pending-review','UNRELATED'),make('LATEST','pending-review'),make('OLDER','deferred')];
 const before=JSON.stringify([h.ctx.state,r]),activity=h.run('requirementReviewActivity(sample)');assert.equal(activity.case,h.ctx.state.cases[2]);assert.equal(activity.label,'In review');assert.equal(activity.tone,'attention');assert.equal(JSON.stringify([h.ctx.state,r]),before);
 h.ctx.state.cases=[make('WAIT','deferred')];assert.equal(h.run('requirementReviewActivity(sample).label'),'Awaiting response');assert.equal(h.run('requirementReviewActivity(sample).tone'),'reference');
 h.ctx.state.cases=[make('APPROVED','approved'),make('REJECTED','rejected'),make('UNKNOWN','working'),make('OTHER','pending-review','UNRELATED')];assert.equal(h.run('requirementReviewActivity(sample)'),null);
 delete h.ctx.state.cases;assert.equal(h.run('requirementReviewActivity(sample)'),null);
});
test('changed exact requirement versions or review bases signal refresh without changing review or requirement state',()=>{
 for(const cause of ['target-version','stale-review','changed-review','changed-requirement-basis']){
  const h=harness(),r={ref:{id:'REQ',revision:4},body:{status:'approved'}},review={ref:{id:'CASE',revision:3},body:{status:'deferred',target:{id:'REQ',revision:4}},stale:[]};h.ctx.sample=r;h.ctx.state.cases=[review];
  if(cause==='target-version')review.body.target.revision=3;
  if(cause==='stale-review')review.stale=[{previous:{id:'SOURCE',revision:1},current:{id:'SOURCE',revision:2}}];
  if(cause==='changed-review')review.changed=[{id:'SOURCE',revision:2}];
  if(cause==='changed-requirement-basis')h.ctx.state.requirement_impacts={REQ:[{previous:{id:'SOURCE',revision:1},current:{id:'SOURCE',revision:2}}]};
  const before=JSON.stringify([h.ctx.state,r]),activity=h.run('requirementReviewActivity(sample)');assert.equal(activity.case,review,cause);assert.equal(activity.label,'Review needs refresh',cause);assert.equal(activity.tone,'advisory',cause);assert.equal(JSON.stringify([h.ctx.state,r]),before,cause);
 }
});

const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const code=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');
function summary(rows,canReview=true,items={}){
 const before=JSON.stringify(rows),recordRows=rows.map((r,i)=>({ref:{id:'REQ-'+i,revision:1},...r})),context={state:{requirement_assessments:{items}},records:kind=>kind==='requirement'?recordRows:[],esc:String,workspaceNavigation:()=>canReview?{review:'Decisions & Issues'}:{}};
 vm.createContext(context);
 vm.runInContext(code.slice(code.indexOf('function ratifiedRequirementRows('),code.indexOf('let requirementNavigationPending=')),context);
 vm.runInContext(code.slice(code.indexOf('function requirementAuthoritySummary('),code.indexOf('function requirementDetail(')),context);
 const html=vm.runInContext('requirementAuthoritySummary()',context);
 assert.equal(JSON.stringify(rows),before);return html;
}
test('published requirements have one count without manufacturing evidence or ratification',()=>{
 const html=summary([{body:{status:'proposed'}},{body:{status:'proposed'}}]);
 assert.match(html,/2 requirements/);assert.doesNotMatch(html,/Requirement ratings not recorded|0 with recorded assessments/);assert.doesNotMatch(html,/\d+ ratified|\d+ proposed|with recorded assessments/);
 assert.doesNotMatch(html,/Resolve gaps and changes in Decisions & Issues/);assert.doesNotMatch(html,/data-action=".*approve|validated|100%/);
});
test('one requirement map retains different underlying authority states without separate stage buckets',()=>{
 const html=summary([{body:{status:'approved'}},{body:{status:'proposed'}}]);
 assert.match(html,/2 requirements/);assert.doesNotMatch(html,/Requirement ratings not recorded|0 with recorded assessments/);assert.doesNotMatch(html,/\d+ ratified|\d+ proposed/);
 assert.doesNotMatch(html,/data-action="bridge-requirement-view"/);
});
test('empty and restricted views do not invent approval or expose an unavailable route',()=>{
 const html=summary([],false);assert.match(html,/0 requirements/);assert.doesNotMatch(html,/Requirement ratings not recorded|0 with recorded assessments/);
 assert.doesNotMatch(html,/data-action="bridge-requirement-view"/);
});
test('recorded assessment counts do not imply confidence, currency or permission',()=>{
 const html=summary([{body:{status:'approved'}},{body:{status:'proposed'}}],true,{'REQ-0':{uses:{implementation:{current:{ref:{id:'ASSESS',revision:1}},status:'needs-reassessment'}}}});
 assert.match(html,/2 requirements/);assert.match(html,/1 with recorded assessments/);assert.doesNotMatch(html,/Confidence: High|Suitable|Ready|validated|100%/);
});
test('private setup access remains sponsor-only and separate from published view navigation',()=>{
 const context={state:{actor:'priya',intake:{draft:{ref:{id:'INTAKE',revision:2}}}},lockedRequirementsSetup:()=>true,requirementsSwitch:()=>'<div class="requirements-switch requirements-tabstrip">Requirements · Team input & reviews</div>'};
 vm.createContext(context);vm.runInContext(code.slice(code.indexOf('function requirementsToolbar('),code.indexOf('function requirementAuthoritySummary(')),context);
 const before=JSON.stringify(context.state),render=()=>vm.runInContext('requirementsToolbar()',context),html=render();
 assert.match(html,/requirements-toolbar/);assert.match(html,/Private/);assert.match(html,/data-action="sponsor-setup-draft"/);assert.match(html,/separate from the published requirements/);assert.equal(JSON.stringify(context.state),before);
 for(const actor of ['sam','lee','alex']){context.state.actor=actor;assert.doesNotMatch(render(),/sponsor-setup-draft|Private/);}
 context.state.actor='priya';context.lockedRequirementsSetup=()=>false;assert.doesNotMatch(render(),/sponsor-setup-draft/);
});
test('ratification membership remains separate from the visible proposed map without changing records',()=>{
 const rows=[{kind:'requirement',ref:{id:'REQ-A'},body:{status:'approved',drawer_id:'AREA-A'}},{kind:'requirement',ref:{id:'REQ-P'},body:{status:'proposed',drawer_id:'AREA-P'}},{kind:'requirement-drawer',ref:{id:'AREA-A'},body:{parent_id:'ROOT-A'}},{kind:'requirement-drawer',ref:{id:'ROOT-A'},body:{}},{kind:'requirement-drawer',ref:{id:'AREA-P'},body:{}}];
 const context={records:k=>rows.filter(r=>r.kind===k)};vm.createContext(context);vm.runInContext(code.slice(code.indexOf('function ratifiedRequirementRows('),code.indexOf('let requirementNavigationPending=')),context);
 const before=JSON.stringify(rows);assert.deepEqual(Array.from(context.ratifiedRequirementRows(),r=>r.ref.id),['REQ-A']);assert.deepEqual(Array.from(context.pendingRequirementRows(),r=>r.ref.id),['REQ-P']);
 assert.equal(JSON.stringify(rows),before);
});

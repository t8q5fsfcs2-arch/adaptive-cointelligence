const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function ctx(cases){
 const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const c={esc,head:(t,s)=>`<h1>${esc(t)}</h1><p>${esc(s)}</p>`,records:k=>k==='intent'?[{ref:{id:'INT-001',revision:3}}]:[],
  sponsorQuestionCatalog:[{id:'q2',section:'Project Goals',title:'Problems to solve',prompt:'Which problems?'},{id:'q4',section:'Users',title:'Define users',prompt:'Who uses it?'},{id:'q19',section:'Constraints & Limits',title:'Operational limits',prompt:'What limits?'}],
  sponsorSectionTitle:t=>t==='Project Goals'?'Product Goals':t,
  state:{actors:{priya:{name:'Dana Okafor'}},intake:{cases}}};
 vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/context.js'),'utf8'),c);return c;
}
const scaffold=[{key:'operations',label:'Operations and support',basis_fields:['constraints','in_scope']},{key:'needs',label:'Customer and user needs',basis_fields:['beneficiaries']},{key:'measurement',label:'Outcomes and measurement',basis_fields:['business_challenge']}];
const pub=(answers,rev=1)=>({ref:{id:'INTREV',revision:rev},body:{status:'published',decision_owner:'priya',snapshot:{scaffold,sponsor_brief:{answers}}}});
test('Context shows every published answer openly, grouped by section, with the requirement areas it shapes',()=>{
 const c=ctx([pub({q2:{items:['Patients cannot cancel easily.']},q4:{roles:[{name:'Front desk',does:'Schedules visits'}]},q19:{items:['Routine visits only.']}})]);
 const html=vm.runInContext('contextScreen()',c);
 assert.match(html,/<h1>Context<\/h1>/);assert.match(html,/3<\/strong> of 3 answered/);assert.match(html,/With Business Intent v3/);
 assert.match(html,/<h2>Product Goals<\/h2>/);assert.match(html,/Patients cannot cancel easily\./);assert.match(html,/Front desk · Schedules visits/);
 assert.match(html,/Routine visits only\.[\s\S]*data-action="open-drawer" data-id="DRW-operations">Operations and support/);
 assert.match(html,/Shapes <strong>3<\/strong> requirement areas/);assert.doesNotMatch(html,/<details/);
 assert.doesNotMatch(html,/<textarea|<input|<select/);
});
test('unanswered questions say so and changes from the previous published version are marked',()=>{
 const c=ctx([pub({q2:{items:['New wording']},q4:{items:[]}},2),pub({q2:{items:['Old wording']},q4:{items:[]}},1)]);
 const html=vm.runInContext('contextScreen()',c);
 assert.match(html,/Problems to solve <span class="ac-state ac-state-edited">Changed<\/span>/);assert.match(html,/Not answered/);assert.doesNotMatch(html,/Define users <span class="ac-state/);
});
test('before publication Context explains it arrives with Business Intent',()=>{
 const c=ctx([]);assert.match(vm.runInContext('contextScreen()',c),/published together with Business Intent/);
});
test('answers are escaped',()=>{
 const c=ctx([pub({q2:{items:['<img src=x>']}})]);assert.doesNotMatch(vm.runInContext('contextScreen()',c),/<img/);
});
test('readers see what the shared effort is validating, from the published values',()=>{
 const p=pub({q2:{items:['x']}});p.body.snapshot.values={research_question:'Why do patients miss?',assumptions:'They know ahead.',operations_question:'Which visits can move?',approach:'An assistant.'};
 const c=ctx([p]);const html=vm.runInContext('contextScreen()',c);
 assert.match(html,/What the shared effort is validating/);assert.match(html,/The problem[\s\S]*Why do patients miss\?[\s\S]*They know ahead\./);assert.match(html,/The solution[\s\S]*Which visits can move\?[\s\S]*An assistant\./);
});
test('the sponsor validation steps edit only existing fields through the existing save and show the context they draw on',()=>{
 const p=pub({});const c=ctx([p]);
 Object.assign(c,{sponsorText:(n,t,v)=>`<label><span>${t}</span><textarea name="${n}">${c.esc(v)}</textarea></label>`,button:(t,a)=>`<button data-action="${a}">${t}</button>`,sponsorInfo:()=>({brief:{answers:{q2:{items:['Cannot cancel easily']}}}}),sponsorReviewerComposer:()=>'<textarea id="sponsor-coach-message"></textarea>'});
 c.state.actors={priya:{name:'Dana',role:'Sponsor'},sam:{name:'Jordan',role:'Research'}};c.state.intake.draft={body:{values:{research_question:'Why?',assumptions:'',assumption_owner:'sam',operations_question:'',approach:'An assistant.'}}};
 let html=vm.runInContext("contextValidationEditor('problem')",c);
 assert.match(html,/data-kind="fit"/);assert.match(html,/name="research_question"/);assert.match(html,/name="assumptions"/);assert.match(html,/<option value="sam" selected>/);assert.match(html,/Q2 · Problems to solve[\s\S]*Cannot cancel easily/);assert.match(html,/data-action="sponsor-save"/);
 html=vm.runInContext("contextValidationEditor('solution')",c);assert.match(html,/name="operations_question"/);assert.match(html,/An assistant\./);assert.match(html,/data-action="sponsor-fit"/);assert.doesNotMatch(html,/name="approach"/);
 const nav=vm.runInContext("contextValidationNav('problem')",c);assert.match(nav,/Validation plan/);assert.match(nav,/data-id="problem" aria-current="true"/);assert.match(nav,/is-started/);
 assert.match(vm.runInContext("contextValidationCoach('solution')",c),/Advice only/);
});

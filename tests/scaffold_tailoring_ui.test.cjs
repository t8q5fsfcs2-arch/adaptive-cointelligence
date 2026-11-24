const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function harness(){const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');const ctx={state:{scaffold_tailoring:{stale_areas:['experience/accessibility']},intake:{draft:{ref:{id:'I',revision:2}}}},esc,para:s=>`<p>${esc(s)}</p>`,val:(n,s)=>`<p>${esc(n)}: ${esc(s)}</p>`,label:r=>r.id+':v'+r.revision,intakeNames:{need:'Unmet need'},criterionList:s=>`<ul>${esc(s)}</ul>`,drawerEditField:(n,k,l,v)=>`<textarea name="${k}">${esc(v)}</textarea>`,areaCriteria:()=>'<section>SME criteria</section>',document:{querySelectorAll:()=>[]},modal:(...args)=>ctx.dialog=args};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/scaffold-tailoring.js'),'utf8'),ctx);return {ctx,run:s=>vm.runInContext(s,ctx)};}
test('project focus shows exact saved basis and unresolved gaps without claiming validation',()=>{const h=harness();h.ctx.focus={question:'Resume a task?',rationale:'Prevent lost input',checks:'Preserve input',gaps:'Retention unknown',relevance:'uncertain',basis:{id:'I',revision:1},basis_values:{need:'Keep <script> source text'},requirement_basis:[]};const html=h.run("projectFocus({project_focus:focus},'experience/accessibility')");assert.match(html,/Needs reassessment/);assert.match(html,/Still to resolve/);assert.match(html,/I:v1/);assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);assert.match(html,/Inclusion remains a separate human choice/);});
test('generated project guidance can be edited in line',()=>{const h=harness();h.ctx.focus={question:'Question',rationale:'Reason',checks:'Check',gaps:'Gap'};const html=h.run("focusEditor({project_focus:focus},'experience--accessibility')");for(const n of ['question','rationale','checks','gaps'])assert.match(html,new RegExp('name="project_'+n+'"'));});
test('stale proposal has no apply handler',()=>{const h=harness();h.ctx.state.scaffold_tailoring.runs=[{ref:{id:'R',revision:1},current:false,body:{basis:{id:'I',revision:1},applied:null,context:{areas:[],values:{},requirements:[]},output:{summary:'Stale',areas:[],uncovered_needs:[]}}}];h.run("openScaffoldProposal('R')");assert.equal(h.ctx.dialog[3],null);assert.match(h.ctx.dialog[1],/project basis changed/);});


function planningHarness(){
 const h=harness();h.ctx.state.actor='priya';h.ctx.view='planning';h.ctx.pageDirty=false;
 h.ctx.state.intake.draft.body={scaffold:[{included:true,label:'Experience'}]};h.ctx.state.intake.scaffold_current=true;
 h.ctx.state.scaffold_tailoring={runs:[],stale_areas:[]};h.ctx.date=v=>v;
 h.ctx.button=(text,action,id='')=>`<button data-action="${action}" data-id="${h.ctx.esc(id)}">${h.ctx.esc(text)}</button>`;
 return h;
}
test('AI partner offers review only for current unapplied guidance while retaining history',()=>{
 const h=planningHarness();h.ctx.state.scaffold_tailoring.runs=[
  {ref:{id:'NEW',revision:1},current:true,body:{applied:null,at:'Today'}},
  {ref:{id:'OLDER',revision:1},current:false,body:{applied:null,at:'Yesterday'}},
  {ref:{id:'USED',revision:2},current:true,body:{applied:{},at:'Last week'}}];
 const before=JSON.stringify(h.ctx.state),html=h.run('planningProjectGuidance()');
 assert.match(html,/Suggest project guidance/);assert.match(html,/data-id="NEW">Review suggested guidance/);
 assert.equal((html.match(/>Review suggested guidance</g)||[]).length,1);
 assert.match(html,/Earlier guidance \(2\)/);assert.match(html,/data-id="OLDER">View earlier suggestion/);
 assert.match(html,/data-id="USED">View applied guidance/);assert.match(html,/Basis changed/);
 assert.equal(JSON.stringify(h.ctx.state),before);
 h.ctx.state.scaffold_tailoring.runs[0].current=false;
 assert.doesNotMatch(h.run('planningProjectGuidance()'),/>Review suggested guidance</);
});
test('project guidance controls stay in sponsor planning and expose each pending proposal',()=>{
 const h=planningHarness();assert.match(h.run('planningProjectGuidance()'),/Suggest project guidance/);
 h.ctx.state.actor='sam';assert.equal(h.run('planningProjectGuidance()'),'');
 h.ctx.state.actor='priya';h.ctx.view='requirements';assert.equal(h.run('planningProjectGuidance()'),'');
 h.ctx.view='planning';h.ctx.state.intake.draft.body.scaffold=[];assert.equal(h.run('planningProjectGuidance()'),'');
 h.ctx.state.intake.draft.body.scaffold=[{}];h.ctx.state.scaffold_tailoring.runs=['A','B'].map(id=>({ref:{id},current:true,body:{applied:null,at:id}}));
 const html=h.run('planningProjectGuidance()');assert.match(html,/data-id="A">Review suggested guidance/);assert.match(html,/data-id="B">Review suggested guidance/);
});
test('guidance preserves dirty and stale guards and requests a model only after explicit preparation',async()=>{
 const h=planningHarness(),calls=[];h.ctx.command=async(a,d)=>{calls.push({a,d});return {ref:{id:'RESULT',revision:1}};};
 h.ctx.pageDirty=true;await assert.rejects(h.run("scaffoldTailoringAction('scaffold-tailor')"),/Save your draft/);
 h.ctx.pageDirty=false;h.ctx.state.intake.scaffold_current=false;
 await assert.rejects(h.run("scaffoldTailoringAction('scaffold-tailor')"),/Update from Business Intent/);assert.equal(calls.length,0);
 h.ctx.state.intake.scaffold_current=true;await h.run("scaffoldTailoringAction('scaffold-tailor')");
 assert.equal(h.ctx.dialog[0],'Suggest project guidance');assert.equal(calls.length,0);
 await h.ctx.dialog[3]({get:()=>''});assert.equal(calls[0].a,'scaffold-tailor');assert.equal(calls[0].d.expected.revision,2);assert.equal(calls[0].d.consent,true);
});

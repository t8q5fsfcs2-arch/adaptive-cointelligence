const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
function harness(){
 const listeners={},ctx={console,Set,Object,setInterval:()=>1,clearInterval:()=>{},window:{addEventListener:()=>{}},document:{addEventListener:(n,f)=>{(listeners[n]??=[]).push(f);}},
  state:{actors:{sam:{role:'Research',name:'Sam'}},intake:{draft:{ref:{id:'D',revision:1},body:{values:{business_challenge:'A problem',value:'Reduce repeated effort',work_kind:'digital'}}},value_checkpoint:{current:false,missing:[],history:[]}},coaching:{runs:[],sources:[],guidance:{},model:{configured:true}}},
  esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),val:(l,s)=>l+': '+(s||''),para:s=>'<p>'+s+'</p>',tag:s=>s,button:(l,a,id)=>`<button data-action="${a}" data-id="${id}">${l}</button>`,date:s=>s,label:()=>'',busy:false,$:()=>null,toast:()=>{},render:()=>{},
  FormData:class{constructor(f){return Object.entries(f.fields||{})[Symbol.iterator]();}}
 };
 vm.createContext(ctx);
 for(const name of ['value','coaching','intake','scaffold'])vm.runInContext(fs.readFileSync(path.join(__dirname,`../src/workbench/static/${name}.js`),'utf8'),ctx);
 return {ctx,listeners,run:s=>vm.runInContext(s,ctx)};
}
test('each value and context question has a review action without duplicate next navigation',()=>{
 const h=harness();
 for(const field of h.run('valueQuestionKeys()')){
  h.ctx.field=field;h.run('valueFocus=field');
  const html=h.run('valueQuestions(state.intake.draft.body.values)');
  assert.match(html,/Ask your AI partner/);assert.match(html,new RegExp('data-id="'+field+'"'));
  assert.doesNotMatch(html,/Continue to|name="next"/);
 }
 for(const field of h.run('contextGroups.flatMap(g=>g[1])')){
  h.ctx.field=field;h.run('coachedField=field;valueFocus=field');
  const html=h.run("coachedIntakeScreen('context')");
  assert.match(html,/Ask your AI partner/);assert.doesNotMatch(html,/Continue to What|name="next"/);
  if(field==='work_kind')assert.match(html,/<select id="coached-kind" name="work_kind"/);
 }
 assert.match(h.run('valueCoach()'),/class="coach-ask reviewer-composer"/);
 assert.doesNotMatch(h.run('valueCoach()'),/Get feedback/);
});
function responseHarness(context=false){
 const h=harness(),calls=[],error={textContent:''},trigger={textContent:'Coach this response'};
 const form={fields:context?{constraints:'New operational constraint'}:{measures:'New benefit-linked measure',value:'The current editable proposition'},elements:{namedItem:()=>null}};
 let duringSave=()=>{},duringModel=()=>{};
 h.ctx.document.querySelector=()=>trigger;
 h.ctx.$=selector=>({'#value-proposition-form':context?null:form,'#coached-field-form':context?form:null,'#value-proposition-form .error':error,'#coached-field-form .error':error}[selector]||null);
 h.ctx.command=async(action,data)=>{calls.push({action,data:JSON.parse(JSON.stringify(data))});if(action==='intake-save'){
  Object.assign(h.ctx.state.intake.draft.body.values,form.fields);h.ctx.state.intake.draft.ref.revision++;
  await duringSave();
 }if(action==='intake-coach')await duringModel();return {message:'Feedback ready'};};
 h.ctx.load=async()=>{};h.run("focusCoachFeedback=()=>{};intakeStep='context';coachedField='constraints';valueFocus='measures';valueCoachMode='whole'");
 return {h,calls,form,error,trigger,save:f=>duringSave=f,model:f=>duringModel=f};
}
test('Coach this response saves current edits then requests the selected expert and never adopts or advances',async()=>{
 for(const context of [false,true]){
  const {h,calls,form,trigger}=responseHarness(context),field=context?'constraints':'measures';
  await h.run(`coachingAction('coach-response','${field}')`);
  assert.deepEqual(calls.map(x=>x.action),['intake-save','intake-coach']);
  const req=calls[1].data;
  assert.equal(req.field,field);assert.equal(req.skill,'coach-field');assert.equal(req.expected.revision,2);
  assert.match(req.message,/Evaluate the quality/);assert.match(req.message,/context of this initiative/);
  assert.equal(h.ctx.state.intake.draft.body.values[field],form.fields[field]);
  assert.equal(h.run('coachedField'),field);assert.equal(h.run('valueFocus'),'measures');
  if(!context)assert.equal(h.run('valueCoachMode'),'question');
  assert.equal(trigger.disabled,false);assert.equal(h.ctx.busy,false);
 }
});
test('new typing during save prevents sending an older answer',async()=>{
 const {h,calls,form,error,save}=responseHarness();
 save(async()=>{form.fields.measures='Typed during save';h.run("valueWorking.measures='Typed during save'");});
 await h.run("coachingAction('coach-response','measures')");
 assert.deepEqual(calls.map(x=>x.action),['intake-save']);
 assert.match(error.textContent,/New edits arrived/);assert.equal(h.run('valueWorking.measures'),'Typed during save');
});
test('provider failure keeps the saved answer and restores the review action',async()=>{
 const {h,calls,error,trigger,model}=responseHarness();model(async()=>{throw Error('Model unavailable');});
 await h.run("coachingAction('coach-response','measures')");
 assert.equal(h.ctx.state.intake.draft.body.values.measures,'New benefit-linked measure');
 assert.match(error.textContent,/Model unavailable/);assert.equal(trigger.disabled,false);
 assert.equal(calls.some(x=>x.action==='intake-coach-apply'),false);
});
test('guide is outside the placeholder and escapes user-visible template text',()=>{
 const h=harness();h.ctx.state.coaching={runs:[],sources:[],guidance:{},model:{configured:true},expertise:{why_now:{hint:'Why prioritize?',answer_shape:['Reason'],starter:'<script>bad()</script>'}}};
 const html=h.run("questionGuide('why_now')");
 assert.match(html,/id="guide-why_now"/);assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);
});
test('success measures keeps a collapsed value reference beside one editable response and its coach',()=>{
 const h=harness();h.run("intakeStep='success';valueFocus='measures'");
 h.ctx.state.intake.draft.body.values.measures='Track repeated entry per request.';
 const html=h.run('valuePropositionScreen()');
 assert.match(html,/intake-response-workspace/);
 assert.match(html,/<details class="measurement-reference"><summary>Value proposition to measure/);
 assert.match(html,/Reduce repeated effort/);
 assert.match(html,/Add metric/);assert.match(html,/data-metric-input/);assert.match(html,/name="measures"/);
 assert.equal((html.replace(/<input[^>]*type="hidden"[^>]*>/g,'').match(/Track repeated entry per request\./g)||[]).length,1);
 assert.doesNotMatch(html,/Value to measure|intake-section-summary|class="card value-output"|name="value"/);
 assert.match(html,/Save draft/);assert.match(html,/Ask your AI partner/);
});

function adviceFixture(h){
 h.ctx.state.coaching.expertise_version='1';h.ctx.state.coaching.agent_version='9';
 const r={ref:{id:'COACH-1',revision:1},body:{agent_version:'9',expertise_version:'1',skill:'coach-field',field:'business_challenge',values:{...h.ctx.state.intake.draft.body.values},applied:{},output:{reply:'One focused point.',suggestions:[],questions:[]}}};
 h.ctx.state.coaching.runs=[r];h.ctx.advice=r;return r;
}
test('only advice from the current answers and coach version leads the panel',()=>{
 const h=harness(),r=adviceFixture(h);
 assert.equal(h.run('currentCoachAdvice(advice)'),true);
 r.body.agent_version='8';assert.equal(h.run('currentCoachAdvice(advice)'),false);
 const html=h.run('valueCoach()');
 assert.doesNotMatch(html,/data-current-coach/);assert.match(html,/Earlier feedback \(1\)/);
 assert.match(html,/One focused point/); // preserved in the collapsed history
 r.body.agent_version='9';r.body.values.value='Different earlier value';
 assert.equal(h.run('currentCoachAdvice(advice)'),false);
});
test('fresh suggested wording is disclosed and stale history offers no adoption action',()=>{
 const h=harness(),r=adviceFixture(h);
 r.body.output.suggestions=[{field:'business_challenge',text:'A qualified proposed answer.',rationale:'Keep uncertainty explicit.',basis:'hypothesis',citations:[]}];
 let html=h.run('valueCoach()');assert.match(html,/<details class="coach-wording">/);assert.match(html,/Review and use wording/);
 assert.doesNotMatch(html,/value-coach-tabs/);
 r.body.agent_version='8';html=h.run('valueCoach()');
 assert.match(html,/A qualified proposed answer/);assert.doesNotMatch(html,/data-action="coach-apply"/);
});
test('editing closes previous feedback without changing the answer or sending a request',()=>{
 const h=harness();const summary={textContent:'Latest feedback'},feedback={open:true,querySelector:()=>summary};
 h.ctx.document.querySelector=()=>feedback;
 h.ctx.changeEvent={target:{closest:()=>true}};
 h.run('markCoachEdits(changeEvent)');
 assert.equal(feedback.open,false);assert.equal(summary.textContent,'Feedback before these edits');
 assert.equal(h.ctx.state.intake.draft.body.values.business_challenge,'A problem');
});

test('document drafting fills empty fields only after generation and focuses a drafted question',async()=>{
 const h=harness(),calls=[];h.run('pageDirty=false');
 h.ctx.command=async(action,data)=>{calls.push({action,data:structuredClone(data)});return action==='intake-coach'?{ref:{id:'SRC-DRAFT',revision:1}}:{filled:['value','need']};};
 await h.run('draftSourceAnswers()');
 assert.deepEqual(calls.map(c=>c.action),['intake-coach','intake-coach-fill-empty']);
 assert.equal(calls[1].data.run_id,'SRC-DRAFT');assert.equal(calls[1].data.confirm,true);
 assert.deepEqual(calls[1].data.expected,{id:'D',revision:1});
 assert.equal(h.run('valueFocus'),'need');assert.equal(h.run('valueCoachMode'),'question');assert.equal(h.run('sourcesOpen'),false);
});
test('typing or a provider failure during document drafting prevents filling fields',async()=>{
 for(const failure of [false,true]){
  const h=harness(),calls=[];h.run('pageDirty=false');
  h.ctx.command=async action=>{calls.push(action);if(failure)throw Error('Provider unavailable');h.run('pageDirty=true');return {ref:{id:'SRC-DRAFT',revision:1}};};
  await assert.rejects(h.run('draftSourceAnswers()'),failure?/Provider unavailable/:/New edits arrived/);
  assert.deepEqual(calls,['intake-coach']);
 }
});
test('source basis accompanies editable questions and escapes document text',()=>{
 const h=harness();h.ctx.state.intake.draft.body.field_provenance={business_challenge:{origin:'drafted-from-sources',status:'ai-proposed-draft',rationale:'A limited study.',citations:[{quote:'<script>source text</script>',source_title:'<Document>'}]}};
 const html=h.run('valueQuestions(state.intake.draft.body.values)');
 assert.match(html,/AI draft from material/);assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);
 assert.match(html,/Ask your AI partner/);assert.match(html,/<textarea/);
});
test('document proposals stay available beside the material and preserve replacement review',()=>{
 const h=harness();h.ctx.state.coaching.runs=[{ref:{id:'S',revision:2},body:{skill:'seed-value',values:{...h.ctx.state.intake.draft.body.values},applied:{},output:{reply:'Two observations.',suggestions:[{field:'business_challenge',text:'Candidate wording.',rationale:'From the source.',basis:'source-supported',citations:[]}],questions:[]}}}];
 const html=h.run('sourceShelf()');
 assert.match(html,/>Upload</);assert.doesNotMatch(html,/Bring what you already have|Briefs, notes|Suggest answers|Draft answers from material/);assert.match(html,/Document proposals · 1 to review/);assert.match(html,/Candidate wording/);assert.match(html,/Use this wording/);
});

function documentHarness(){
 const h=harness(),calls=[],status={innerHTML:''};let failure=null,duringModel=()=>{};
 h.ctx.state.intake.draft.body.values.value='';
 h.run(fs.readFileSync(path.join(__dirname,'../src/workbench/static/document-changes.js'),'utf8'));
 h.run('pageDirty=false');h.ctx.load=async()=>{};
 h.ctx.$=selector=>selector==='#modal'?{close:()=>{}}:selector==='#document-status'?status:null;
 h.ctx.command=async(action,data)=>{
  calls.push({action,data:structuredClone(data)});
  if(action===failure)throw Error('Connection interrupted');
  if(action==='intake-source'){
   const source={ref:{id:'NEW',revision:1},body:{title:data.title||data.filename,role:'background'}};
   h.ctx.state.coaching.sources.push(source);return {ref:source.ref};
  }
  if(action==='intake-coach'||action==='intake-change-assess'){await duringModel();return {ref:{id:'RESULT',revision:1}};}
  if(action==='intake-coach-fill-empty')return {filled:['need'],message:'Draft ready'};
 };
 return {h,calls,status,fail:a=>failure=a,model:f=>duringModel=f};
}
test('upload automatically reads only the new document and prepares editable drafts',async()=>{
 const {h,calls,model}=documentHarness();
 h.ctx.state.coaching.sources.push({ref:{id:'OLD',revision:1},body:{title:'Earlier private file',role:'background'}});
 h.run("chosenSources.add('OLD')");
 model(async()=>assert.match(h.run('documentStatus()'),/Reading Notes/));
 await h.run("uploadDocument({title:'Notes',text:'Fictional content',role:'background'})");
 assert.deepEqual(calls.map(c=>c.action),['intake-source','intake-coach','intake-coach-fill-empty']);
 assert.deepEqual(calls[1].data.sources,[{id:'NEW',revision:1}]);
 assert.equal(h.run('documentWork.phase'),'complete');assert.match(h.run('documentStatus()'),/1 draft answer ready/);
});
test('a failed drafting call retains the upload and Retry does not upload again',async()=>{
 const {h,calls,fail}=documentHarness();fail('intake-coach');
 await h.run("uploadDocument({title:'Notes',text:'Fictional content'})");
 assert.equal(h.run('documentWork.phase'),'failed');assert.match(h.run('documentStatus()'),/Document saved/);assert.match(h.run('documentStatus()'),/>Retry</);
 assert.equal(h.ctx.state.coaching.sources.length,1);
 fail(null);await h.run("prepareDocumentDraft({id:'NEW',revision:1},'Notes')");
 assert.equal(calls.filter(c=>c.action==='intake-source').length,1);assert.equal(h.run('documentWork.phase'),'complete');
});
test('failed upload never invokes a model and concurrent typing blocks automatic filling',async()=>{
 const failed=documentHarness();failed.fail('intake-source');
 await assert.rejects(failed.h.run("uploadDocument({title:'Notes',text:'Fictional content'})"),/Connection interrupted/);
 assert.deepEqual(failed.calls.map(c=>c.action),['intake-source']);
 const typing=documentHarness();typing.model(async()=>typing.h.run("pageDirty=true;valueWorking.need='New human wording'"));
 await typing.h.run("uploadDocument({title:'Notes',text:'Fictional content'})");
 assert.equal(typing.calls.some(c=>c.action==='intake-coach-fill-empty'),false);
 assert.equal(typing.h.run('valueWorking.need'),'New human wording');
 assert.equal(typing.h.run('documentWork.phase'),'failed');
});
test('document processing status is scoped to the current draft and escapes filenames',async()=>{
 const {h}=documentHarness();await h.run("uploadDocument({title:'<script>name</script>',text:'Fictional content'})");
 h.run("documentWork.phase='reading'");
 assert.match(h.run('documentStatus()'),/role="status" aria-live="polite"/);
 assert.match(h.run('documentStatus()'),/&lt;script>/);assert.doesNotMatch(h.run('documentStatus()'),/<script>/);
 h.ctx.state.intake.draft.ref.id='OTHER';assert.equal(h.run('documentStatus()'),'');
});

test('long document requests keep visible progress and stop the timer on success or failure',async()=>{
 for(const failed of [false,true]){
  const {h,model}=documentHarness();let tick,cleared;
  h.ctx.setInterval=(callback,ms)=>{assert.equal(ms,1000);tick=callback;return 42;};
  h.ctx.clearInterval=id=>cleared=id;
  model(async()=>{
   h.run('documentWork.startedAt=Date.now()-65000');tick();
   assert.match(h.run('documentStatus()'),/Still drafting answers/);
   assert.match(h.run('documentStatus()'),/1m 5s/);
   assert.doesNotMatch(h.run('documentStatus()'),/>Retry</);
   if(failed)throw Error('Model request timed out');
  });
  await h.run("uploadDocument({title:'Long notes',text:'Fictional content'})");
  assert.equal(cleared,42);assert.doesNotMatch(h.run('documentStatus()'),/document-elapsed|document-spinner/);
 }
});

test('Business Intent separates the four draft sections with no acceptance lock',()=>{
 const h=harness();h.ctx.state.intake.has_draft=true;h.ctx.state.actor='priya';h.ctx.head=()=>'';
 h.run("intakeStep='context'");
 const html=h.run('intakeScreen()');
 for(const title of ['Business rationale','Value proposition','Context','Success measures'])assert.match(html,new RegExp(title));
 assert.equal(h.run('intakeStep'),'context');
 assert.doesNotMatch(html,/Review and accept the value proposition first|Ready to explore context/);
 assert.equal(h.run("questionSection('measures')"),'success');
 assert.equal(h.run("questionSection('why_now')"),'rationale');
});
test('context shows one editable response beside its coach without duplicating answers',()=>{
 const h=harness();h.run("intakeStep='context';valueFocus='handoffs'");
 h.ctx.state.intake.draft.body.values.handoffs='Coordinator passes details to dispatch.';
 const html=h.run('valuePropositionScreen()');
 assert.match(html,/intake-response-workspace/);
 assert.doesNotMatch(html,/Working context|context-summary-group|intake-section-summary/);
 assert.equal((html.match(/Coordinator passes details to dispatch\./g)||[]).length,1);
 assert.match(html,/Coordinator passes details/);
 assert.match(html,/Save draft/);assert.match(html,/Ask your AI partner/);
 assert.doesNotMatch(html,/name="value"/);
});
test('a failed section save preserves location and releases the busy guard',async()=>{
 const h=harness();h.ctx.document.querySelector=()=>({});
 h.run("intakeStep='context';valueFocus='handoffs';pageDirty=true;saveCoachedField=async()=>{throw Error('Save failed')}");
 await assert.rejects(h.run("intakeAction('intake-step','success')"),/Save failed/);
 assert.equal(h.run('intakeStep'),'context');assert.equal(h.ctx.busy,false);
 assert.equal(h.run('pageDirty'),true);
});
test('section navigation waits for a successful save and stays when newer edits arrive',async()=>{
 const h=harness();h.ctx.document.querySelector=()=>({});
 h.run("intakeStep='context';pageDirty=true;saveCoachedField=async()=>{pageDirty=false}");
 await h.run("intakeAction('intake-step','success')");assert.equal(h.run('intakeStep'),'success');
 h.run("pageDirty=true;saveCoachedField=async()=>{}");
 await h.run("intakeAction('intake-step','value')");assert.equal(h.run('intakeStep'),'success');
});


test('a later upload compares all saved documents and never fills or overwrites existing answers',async()=>{
 const {h,calls}=documentHarness();h.ctx.state.intake.draft.body.values.value='Existing proposition';
 h.ctx.state.coaching.sources.push({ref:{id:'OLD',revision:1},body:{title:'Earlier material',role:'hypothesis'}});
 const result=await h.run("uploadDocument({title:'New findings',text:'Fictional new findings'})");
 assert.deepEqual(calls.map(x=>x.action),['intake-source','intake-change-assess']);
 assert.deepEqual(calls[1].data.sources,[{id:'OLD',revision:1},{id:'NEW',revision:1}]);
 assert.equal(calls[1].data.trigger_source.id,'NEW');assert.equal(result.changeResult,'RESULT');
 assert.equal(h.ctx.state.intake.draft.body.values.value,'Existing proposition');
 assert.match(h.run('documentStatus()'),/Impact assessment ready/);
});
test('new typing during change assessment is retained and does not open an adoption form',async()=>{
 const {h,model}=documentHarness();h.ctx.state.intake.draft.body.values.value='Existing proposition';
 model(async()=>h.run("pageDirty=true;valueWorking.value='Newer unsaved wording'"));
 const result=await h.run("uploadDocument({title:'New findings',text:'Fictional new findings'})");
 assert.equal(result.changeResult,null);assert.equal(h.run('valueWorking.value'),'Newer unsaved wording');
 assert.match(result.message,/Save your newer edits/);
});

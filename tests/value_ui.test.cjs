// Pure state-contract tests; visual/browser interaction is checked separately.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/workbench/static/value.js'),'utf8');
function harness(value=''){
 const calls=[],nodes={'#value-save-status':{},'#value-freshness':{}},listeners={};
 const server={ref:{id:'INTAKE-001',revision:1},body:{values:{business_challenge:'A stated challenge',why_now:'',value}}};
 const form={fields:{business_challenge:'A stated challenge',value},elements:{namedItem:()=>null}};
 nodes['#value-proposition-form']=form;
 let onModel=()=>{},onSave=()=>{};
 const ctx={console,structuredClone,Set,Object,window:{addEventListener:()=>{}},FormData:class{constructor(f){this.fields=f.fields;}*[Symbol.iterator](){yield* Object.entries(this.fields);}get(key){return this.fields[key]??null;}},
  document:{addEventListener:(n,f)=>listeners[n]=f},$:s=>nodes[s],pageDirty:false,
  state:{intake:{draft:structuredClone(server)}},selectedSourceRefs:()=>[],
  command:async(action,data)=>{calls.push({action,data:structuredClone(data)});
   if(action==='intake-save'){for(const k of ['business_challenge','why_now','value'])if(k in data)server.body.values[k]=data[k];server.ref.revision++;await onSave();}
   if(action==='intake-coach'){await onModel();return {ref:{id:'GEN-1',revision:1}};}
   if(action==='intake-coach-apply'){server.body.values.value='Generated wording';server.ref.revision++;}
   return {};
  },load:async()=>{ctx.state.intake.draft=structuredClone(server);}
 };
 vm.createContext(ctx);vm.runInContext(source,ctx);
 return {ctx,form,server,calls,nodes,listeners,run:s=>vm.runInContext(s,ctx),model:f=>onModel=f,save:f=>onSave=f};
}
test('first generation populates empty center output and leaves answers intact',async()=>{
 const h=harness();await h.run('generateValue()');
 assert.equal(h.server.body.values.value,'Generated wording');
 assert.equal(h.server.body.values.business_challenge,'A stated challenge');
 assert.deepEqual(h.calls.map(c=>c.action),['intake-coach','intake-coach-apply']);
});
test('refresh leaves existing user wording untouched until adoption',async()=>{
 const h=harness('User edited words');await h.run('generateValue()');
 assert.equal(h.server.body.values.value,'User edited words');
 assert.deepEqual(h.calls.map(c=>c.action),['intake-coach']);
});
test('typing during generation is preserved and prevents automatic adoption',async()=>{
 const h=harness();h.model(async()=>{h.form.fields.value='Typed while waiting';h.run("valueWorking.value='Typed while waiting';pageDirty=true");});
 await h.run('generateValue()');
 assert.equal(h.form.fields.value,'Typed while waiting');
 assert.equal(h.run('valueWorking.value'),'Typed while waiting');
 assert.deepEqual(h.calls.map(c=>c.action),['intake-coach']);
});
test('all cached question edits and visible output are saved together',async()=>{
 const h=harness('Draft');h.run("valueWorking.why_now='A new reason'");h.form.fields.value='Edited draft';
 await h.run('saveValueProposition()');
 assert.equal(h.server.body.values.why_now,'A new reason');
 assert.equal(h.server.body.values.value,'Edited draft');
 assert.equal(h.ctx.pageDirty,false);
});
test('new typing during save is retained and generation waits for a fresh save',async()=>{
 const h=harness();h.form.fields.value='Before save';
 h.save(async()=>{h.form.fields.value='After save began';h.run("valueWorking.value='After save began';pageDirty=true");});
 await assert.rejects(h.run('generateValue()'),/New edits arrived/);
 assert.equal(h.run('valueWorking.value'),'After save began');
 assert.equal(h.calls.some(c=>c.action==='intake-coach'),false);
});
test('generation failure does not apply or clear the current draft',async()=>{
 const h=harness('Keep my words');h.model(async()=>{throw Error('Model unavailable');});
 await assert.rejects(h.run('generateValue()'),/Model unavailable/);
 assert.equal(h.server.body.values.value,'Keep my words');
 assert.equal(h.calls.some(c=>c.action==='intake-coach-apply'),false);
});

test('context questions belong to their own accessible section',()=>{
 const h=harness();
 assert.equal(h.run("questionSection('user_situation')"),'context');
 assert.equal(h.run("valueSections.some(g=>g[2].includes('user_situation'))"),false);
});
test('an edited pending refresh is preserved until used or dismissed',async()=>{
 const h=harness('Current draft');h.run("valueCandidateEdits['GEN-1']='My edited refresh'");
 await assert.rejects(h.run('generateValue()'),/Use the edited refresh/);
 assert.equal(h.calls.length,0);
});

test('metric entries preserve legacy prose and separate only explicit paragraphs',()=>{
 const h=harness();
 const old='Candidate signals: time; error rate; adoption.\nTargets unknown.';
 h.ctx.old=old;
 assert.deepEqual(Array.from(h.run('metricEntries(old)')),[old]);
 assert.equal(h.run('metricText(metricEntries(old))'),old);
 h.ctx.multiple='One complete metric.\n\nAnother metric, with target unknown.';
 assert.equal(h.run('metricEntries(multiple).length'),2);
 assert.equal(h.run('metricText(metricEntries(multiple))'),h.ctx.multiple);
 assert.equal(h.run("metricText(['First metric','','Second metric'])"),'First metric\n\nSecond metric');
 assert.equal(h.run("questionSection('measure_review')"),'success');
});

test('editing a metric updates the canonical answer and retains typing during save',async()=>{
 const h=harness();let items=[{value:'First metric'},{value:'Second metric'}];
 const hidden={name:'measures',value:'',closest:()=>h.form};
 h.form.querySelectorAll=()=>items;h.form.elements.namedItem=k=>k==='measures'?hidden:null;
 Object.defineProperty(h.form.fields,'measures',{enumerable:true,get:()=>hidden.value});
 h.ctx.metricForm=h.form;
 h.run('syncMetricInputs(metricForm)');
 assert.equal(hidden.value,'First metric\n\nSecond metric');
 assert.equal(h.run('valueWorking.measures'),hidden.value);
 h.save(async()=>{items[1].value='New typing during save';h.run('syncMetricInputs(metricForm)');});
 await h.run('saveValueProposition()');
 assert.equal(h.calls[0].data.step,'success');
 assert.equal(h.calls[0].data.measures,'First metric\n\nSecond metric');
 assert.equal(h.run('valueWorking.measures'),'First metric\n\nNew typing during save');
 assert.equal(h.ctx.pageDirty,true);
});

function valueQuestionHarness(){
 const h=harness('Saved proposition'),drafts=new Map();h.ctx.state.actor='priya';h.ctx.state.project={id:'PROJECT-A',version:1};
 h.ctx.reviewerDraftKey=()=>JSON.stringify(['priya',h.ctx.state.actor,h.ctx.state.project.id,'intake-coach']);
 const bound=h.ctx.reviewerDraftKey(),error={textContent:''},button={textContent:'Ask',disabled:false,hasAttribute:()=>false};
 const form={id:'value-coach-form',fields:{message:''},querySelector:selector=>selector==='.error'?error:selector==='textarea[name="message"]'?composer:button};
 const composer={dataset:{reviewerDraftKey:bound},get value(){return form.fields.message;},set value(text){form.fields.message=text;}};
 h.ctx.reviewerDraftWriteKey=(key,text)=>{drafts.set(key,text);if(key===bound)composer.value=text;};h.ctx.reviewerDraftRead=()=>drafts.get(h.ctx.reviewerDraftKey())||'';
 h.ctx.render=()=>{};h.ctx.coachInfo=()=>({model:{configured:true}});h.ctx.busy=false;
 h.submit=()=>h.listeners.submit({target:form,submitter:button,preventDefault(){}});
 return {...h,questionForm:form,composer,error,button,drafts,bound};
}
test('restored value question is submitted from the visible form without another input event',async()=>{
 const h=valueQuestionHarness();h.run("valueMessage='Invisible old question'");h.questionForm.fields.message='Restored visible question';
 await h.submit();const sent=h.calls.find(c=>c.action==='intake-coach');assert.equal(sent.data.message,'Restored visible question');assert.equal(sent.data.consent,true);assert.equal(sent.data.field,'business_challenge');
 assert.equal(h.ctx.reviewerDraftRead(),'Restored visible question');assert.equal(h.composer.value,'Restored visible question');
});
test('a value question mounted in another project is rejected before saving or model submission',async()=>{
 const h=valueQuestionHarness();h.questionForm.fields.message='Project A private question';h.ctx.state.project.id='PROJECT-B';await h.submit();
 assert.match(h.error.textContent,/project or role changed/i);assert.equal(h.calls.length,0);assert.equal(h.drafts.size,0);
});
test('value question stops before model submission if its project changes during saving',async()=>{
 const h=valueQuestionHarness();h.questionForm.fields.message='Original project question';h.form.fields.value='New saved wording';h.save(async()=>{h.ctx.state.project.id='PROJECT-B';});
 await h.submit();assert.match(h.error.textContent,/project or role changed/i);assert.equal(h.calls.filter(c=>c.action==='intake-coach').length,0);assert.equal(h.drafts.get(h.bound),'Original project question');
});
test('next value question typed while awaiting a response survives successful completion',async()=>{
 const h=valueQuestionHarness();h.questionForm.fields.message='First question';h.model(async()=>{h.ctx.reviewerDraftWriteKey(h.bound,'Next question typed while waiting');});
 await h.submit();assert.equal(h.calls.find(c=>c.action==='intake-coach').data.message,'First question');assert.equal(h.ctx.reviewerDraftRead(),'Next question typed while waiting');assert.equal(h.composer.value,'Next question typed while waiting');
});
test('value review failure preserves the visible question and does not replace it with a fallback',async()=>{
 const h=valueQuestionHarness();h.run("valueMessage='Old global text'");h.questionForm.fields.message='Question to retry';h.model(async()=>{throw Error('Connection interrupted');});
 await h.submit();assert.match(h.error.textContent,/Connection interrupted/);assert.equal(h.calls.find(c=>c.action==='intake-coach').data.message,'Question to retry');assert.equal(h.ctx.reviewerDraftRead(),'Question to retry');assert.equal(h.composer.value,'Question to retry');
});
test('value review completion cannot load old results into a newly selected project',async()=>{
 const h=valueQuestionHarness();h.questionForm.fields.message='Project A question';let loads=0;h.ctx.load=async()=>{loads++;};h.model(async()=>{h.ctx.state.project.id='PROJECT-B';});
 await h.submit();assert.equal(h.calls.find(c=>c.action==='intake-coach').data.message,'Project A question');assert.equal(loads,0);assert.equal(h.drafts.get(h.bound),'Project A question');
});

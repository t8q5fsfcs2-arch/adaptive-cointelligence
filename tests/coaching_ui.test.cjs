const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(){
 const calls=[],events={},storage=new Map(),c={
  state:{auth:{account:{id:'account-one'}},actor:'priya',project:{id:'project-one'},intake:{draft:{ref:{id:'DRAFT',revision:2},body:{values:{business_challenge:'A bounded need',measures:'Unmeasured'}}}},coaching:{sources:[],runs:[],guidance:{},expertise:{},expertise_version:'v1',agent_version:'v1',model:{configured:true}}},
  document:{addEventListener:(type,fn)=>(events[type]??=[]).push(fn),querySelectorAll:()=>[]},window:{addEventListener(){}},sessionStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value)},
  intakeNames:{business_challenge:'Business challenge',measures:'Measures'},pageDirty:false,busy:false,esc:v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
  $:()=>null,para:v=>`<p>${c.esc(v)}</p>`,val:(key,value)=>`<label>${key}</label>${c.esc(value)}`,button:(label,action)=>`<button data-action="${action}">${label}</button>`,date:v=>v,label:r=>r.id+'@'+r.revision,
  command:async(action,data)=>{calls.push({action,data});return {message:'Saved advice'};},load:async()=>{},render:()=>{},toast:()=>{},modelSetup:()=>assert.fail('Model already configured')
 };
 vm.createContext(c);for(const name of ['reviewer-ui.js','coaching.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static',name),'utf8'),c);
 return {c,calls,events,run:code=>vm.runInContext(code,c)};
}
test('a reviewer question persists across intake fields and modes without leaking across accounts, roles or projects',()=>{
 const h=harness();h.run("intakeReviewerWrite('Keep my question <private>.')");
 for(const field of ['business_challenge','measures']){
  h.c.field=field;const html=h.run("focusedCoachPanel({field,formId:'coach-message-form',message:'',runs:[]})");
  assert.match(html,/Keep my question &lt;private>\./);assert.match(html,/data-reviewer-draft="intake-coach"/);assert.match(html,/rows="5"/);assert.match(html,/>You<\/label>/);assert.match(html,/>Ask<\/button>/);
 }
 h.c.state.actor='lee';assert.equal(h.run('intakeReviewerMessage()'),'');h.c.state.actor='priya';h.c.state.project.id='project-two';assert.equal(h.run('intakeReviewerMessage()'),'');
 h.c.state.project.id='project-one';h.c.state.auth.account.id='account-two';assert.equal(h.run('intakeReviewerMessage()'),'');h.c.state.auth.account.id='account-one';assert.equal(h.run('intakeReviewerMessage()'),'Keep my question <private>.');
});
test('request completion preserves the reviewer draft and uses the existing advisory path',async()=>{
 const h=harness();h.run("intakeReviewerWrite('Which evidence is missing?')");const before=JSON.stringify(h.c.state);await h.run("requestCoaching('coach-field','Which evidence is missing?')");
 assert.equal(h.calls.length,1);assert.equal(h.calls[0].action,'intake-coach');assert.equal(h.calls[0].data.skill,'coach-field');assert.equal(h.calls[0].data.message,'Which evidence is missing?');assert.equal(h.calls[0].data.consent,true);
 assert.equal(h.run('intakeReviewerMessage()'),'Which evidence is missing?');assert.equal(JSON.stringify(h.c.state),before);
});
test('current model advice identifies AI partner while the composer remains You',()=>{
 const h=harness();h.c.run={body:{basis:h.c.state.intake.draft.ref,values:{...h.c.state.intake.draft.body.values},applied:{},expertise_version:'v1',agent_version:'v1',output:{reply:'Private advisory reply',suggestions:[],questions:[]}}};
 const html=h.run("focusedCoachPanel({field:'business_challenge',formId:'coach-message-form',runs:[run]})");assert.match(html,/<summary>AI partner<\/summary>/);assert.match(html,/Private advisory reply/);assert.match(html,/>You<\/label>/);assert.match(html,/>Ask<\/button>/);assert.doesNotMatch(html,/>Ask coach<|>Get a review</);
});

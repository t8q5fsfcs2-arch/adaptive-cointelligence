const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(editable=true){
 const dialogs=[],commands=[],requests=[],nodes={};
 const data={ref:{id:'PROJECT-DECISION-RIGHTS',revision:2},project:{id:'P',version:4,title:'A named project'},can_edit:editable,kinds:{requirement:'Requirements',intent:'Business direction',coordination:'Coordination issues'},members:[{actor:'alex',name:'Alex Example',role:'Requirement owner'},{actor:'sam',name:'Sam Example',role:'Research'},{actor:'lee',name:'Lee Example',role:'Design'},{actor:'priya',name:'Priya Example',role:'Sponsor'}],rules:{},history:[],boundary:'Project membership and delivery remain separate',defaults:false};
 for(const kind of Object.keys(data.kinds))data.rules[kind]={decider:'alex',reviewers:['sam','lee'],delegates:['priya'],escalation_path:['sam']};
 const ctx={URLSearchParams,state:{actor:'alex',csrf:'CSRF',project:{id:'P'},actors:{alex:{name:'Alex'},sam:{name:'Sam'},lee:{name:'Lee'},priya:{name:'Priya'}},auth:{},cases:[],intake:{cases:[]},bridge:{issues:[]}},dirty:false,document:{addEventListener:(name,cb)=>nodes[name]=cb},
  esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,para:t=>`<p>${t}</p>`,recordedDate:(l,a)=>l+' '+a,
  modal:(...a)=>dialogs.push(a),saveBeforeProjectChange:async()=>{},load:async()=>{},toast(){},fetch:async(url,opts)=>{requests.push({url,opts});return {ok:true,json:async()=>opts?{message:'Saved'}:data};},command:async(a,d)=>{commands.push({a,d});return {message:'Saved'};}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/decision-rights.js'),'utf8'),ctx);return {ctx,data,dialogs,commands,requests,run:s=>vm.runInContext(s,ctx)};
}
test('project settings use named members and send an exact policy and project generation',async()=>{
 const h=harness();await h.run('openDecisionRights()');let html=h.dialogs[0][1];assert.match(html,/Named decider/);assert.match(html,/Required reviewers/);assert.match(html,/Alex Example/);assert.match(html,/Delegates and escalation/);assert.match(html,/does not grant approval authority/);
 const fd={get:n=>n==='rights-reason'?'Agreed human accountability':n.endsWith('-decider')?'alex':n.endsWith('-escalation-0')?'sam':'',getAll:n=>n.endsWith('-reviewer')?['sam','lee']:['priya']};await h.dialogs[0][3](fd);
 const call=h.requests.find(r=>r.opts);const body=JSON.parse(call.opts.body);assert.equal(call.opts.headers['X-Workbench-Project'],'P');assert.equal(call.opts.headers['X-Workbench-Version'],'4');assert.equal(call.opts.headers['X-CSRF-Token'],'CSRF');assert.equal(body.expected.revision,2);assert.equal(body.rules.requirement.delegates[0],'priya');assert.equal(body.reason,'Agreed human accountability');assert.equal(body.admin,undefined);
});
test('ordinary project members can inspect rights without a configuration submit action',async()=>{
 const h=harness(false);await h.run('openDecisionRights()');assert.match(h.dialogs[0][1],/<fieldset[^>]* disabled>/);assert.equal(h.dialogs[0][3],null);assert.match(h.dialogs[0][1],/An administrator manages these settings/);
});
test('authority panel offers only server-permitted actions and names the next escalation contact',()=>{
 const h=harness();h.ctx.record={ref:{id:'CASE',revision:3},kind:'decision-case',body:{}};h.ctx.rights={snapshot:{kind:'requirement',people:{},reviewers:['sam','lee'],delegates:['priya'],escalation_path:['sam','lee']},primary:'alex',active_decider:'alex',blockers:[],can_delegate:true,can_escalate:true};
 let html=h.run('decisionRightsPanel(record,rights)');assert.match(html,/rights-delegate/);assert.match(html,/Escalate to Sam/);assert.doesNotMatch(html,/rights-review|rights-respond|rights-refresh|Approve/);
 h.ctx.rights.can_delegate=false;h.ctx.rights.can_escalate=false;h.ctx.rights.can_respond=true;h.ctx.rights.escalation={status:'open',owner:'sam',position:0,reason:'Resolve a conflict'};html=h.run('decisionRightsPanel(record,rights)');assert.match(html,/Respond to escalation/);assert.doesNotMatch(html,/rights-delegate|rights-escalate/);
});
test('delegation is an explicit action for the selected current review, with reason and exact revision',async()=>{
 const h=harness();h.ctx.state.cases=[{ref:{id:'CASE',revision:7},kind:'decision-case',body:{},rights:{snapshot:{kind:'requirement',delegates:['priya'],people:{}}}}];await h.run("decisionRightsAction('rights-delegate','CASE')");assert.match(h.dialogs[0][1],/primary decider remains accountable/);
 await h.dialogs[0][3]({get:n=>n==='delegate'?'priya':'Cover this bounded decision'});assert.equal(h.commands[0].a,'decision-rights-action');assert.equal(h.commands[0].d.expected.revision,7);assert.equal(h.commands[0].d.delegate,'priya');assert.equal(h.commands[0].d.action,'delegate');assert.equal(h.commands[0].d.actor,undefined);
});
test('a changed user cannot display a prior policy fetch result',async()=>{
 const h=harness();let resolve;h.ctx.fetch=()=>new Promise(r=>resolve=r);const pending=h.run('openDecisionRights()');await new Promise(r=>setImmediate(r));h.ctx.state.actor='lee';resolve({ok:true,json:async()=>h.data});await pending;assert.equal(h.dialogs.length,0);
});

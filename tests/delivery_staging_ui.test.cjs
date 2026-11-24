const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(){
 const requirements=[{kind:'requirement',ref:{id:'REQ-A',revision:2},body:{title:'Capture feedback',text:'Allow feedback capture.',status:'proposed'}},{kind:'requirement',ref:{id:'REQ-B',revision:1},body:{title:'Explain evidence status',text:'Show pending evidence.',status:'approved'}}];
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const events=[],c={state:{actor:'priya',project:{id:'clinic',version:1},delivery:{drafts:[],types:{jira:['Story']},mapping:[],write_status:'No connector is configured.'}},selected:null,view:'planning',document:{addEventListener(){}},records:()=>requirements,get:id=>requirements.find(r=>r.ref.id===id),esc,label:r=>r.id+':v'+r.revision,ref:r=>r.id,head:(title,description)=>`<h1>${title}</h1><p>${description}</p>`,tag:esc,val:()=>'',para:()=>'',button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${esc(t)}</button>`,$:()=>null,saveBeforeProjectChange:async()=>events.push('saved'),render:()=>events.push('rendered'),command:async()=>{events.push('command');throw Error('Navigation must not stage a transaction.');}};
 vm.createContext(c);require('./ui_reference_helpers.cjs')(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/delivery.js'),'utf8'),c);
 return {c,requirements,events,run:s=>vm.runInContext(s,c),draft:(id='DRAFT-A',revision=2,changed=[])=>({ref:{id,revision:1},changed,body:{requirements:[{id:'REQ-A',revision}],target:'jira',destination:'CLINIC',items:[]}})};
}
test('a shared requirement has an explicit staging destination without claiming it is already staged',()=>{
 const h=harness();h.c.record=h.requirements[0];const html=h.run('requirementDeliveryStaging(record)');
 assert.match(html,/Shared v2 · Not staged here/);assert.match(html,/data-action="delivery-stage-requirement" data-id="REQ-A"/);assert.match(html,/>Stage Jira \/ ADO<\/a>/);
 h.c.record=null;assert.equal(h.run('requirementDeliveryStaging(record)'),'');
 h.c.record=h.requirements[0];h.c.state.actor='sam';assert.equal(h.run('requirementDeliveryStaging(record)'),'');
});
test('staging status distinguishes exact saved versions from stale or partly stale transactions',()=>{
 const h=harness();h.c.record=h.requirements[0];h.c.state.delivery.drafts=[h.draft()];
 assert.match(h.run('requirementDeliveryStaging(record)'),/Staged · not sent/);
 h.c.state.delivery.drafts=[h.draft('OLD',1)];assert.match(h.run('requirementDeliveryStaging(record)'),/Needs refresh · not sent/);
 h.c.state.delivery.drafts=[h.draft('PARTIAL',2,[{previous:{id:'REQ-B',revision:1},current:{id:'REQ-B',revision:2}}])];
 assert.match(h.run('requirementDeliveryStaging(record)'),/Needs refresh · not sent/);
 h.c.state.delivery.drafts.push(h.draft('CURRENT'));
 assert.equal(h.run('requirementDeliveryDraft(record).ref.id'),'CURRENT');
});
test('source link saves current work and preselects only that source without preparing a transaction',async()=>{
 const h=harness();await h.run('deliveryAction("delivery-stage-requirement","REQ-A")');
 assert.deepEqual(h.events,['saved','rendered']);assert.equal(h.c.view,'delivery');assert.equal(h.c.selected,null);
 const html=h.run('deliveryScreen()');assert.match(html,/<h1>Handoff<\/h1>/);assert.match(html,/value="REQ-A" checked/);assert.doesNotMatch(html,/value="REQ-B" checked/);
 assert.match(html,/No transactions staged yet/);assert.match(html,/Staging only · nothing sent/);
});
test('source selection cannot carry into another project, reset generation or actor',async()=>{
 const h=harness();await h.run('deliveryAction("delivery-stage-requirement","REQ-A")');
 h.c.state.project.id='other-project';assert.doesNotMatch(h.run('deliveryScreen()'),/value="REQ-A" checked/);
 h.c.state.project.id='clinic';h.c.state.project.version=2;assert.doesNotMatch(h.run('deliveryScreen()'),/value="REQ-A" checked/);
 h.c.state.project.version=1;h.c.state.actor='alex';assert.doesNotMatch(h.run('deliveryScreen()'),/value="REQ-A" checked/);
});
test('source link reopens the exact current staged transaction and rejects unavailable sources',async()=>{
 const h=harness();h.c.state.delivery.drafts=[h.draft('OLD',1,[{previous:{id:'REQ-A',revision:1},current:{id:'REQ-A',revision:2}}]),h.draft('CURRENT')];
 await h.run('deliveryAction("delivery-stage-requirement","REQ-A")');assert.equal(h.c.selected,'CURRENT');
 const html=h.run('deliveryScreen()');assert.match(html,/Staged transactions/);assert.match(html,/CLINIC · Needs refresh · not sent/);assert.match(html,/Staged transaction<\/h2>/);assert.match(html,/<button disabled>Send to Jira<\/button>/);assert.match(html,/Live connector not configured/);
 await assert.rejects(h.run('deliveryAction("delivery-stage-requirement","MISSING")'),/Publish this requirement/);
 assert.ok(!h.events.includes('command'));
});

test('delivery choices retain exact requirement values and keep internal references within optional details',()=>{
 const h=harness(),before=JSON.stringify(h.requirements),html=h.run('deliveryScreen()'),choice=html.match(/<label class="checkbox selectable">([\s\S]*?)<\/label>/)[1];
 assert.match(choice,/value="REQ-A"/);assert.match(choice,/Capture feedback/);assert.match(choice,/Version 2/);assert.doesNotMatch(choice.replace(/<[^>]+>/g,''),/REQ-A/);assert.doesNotMatch(choice,/<details/);assert.match(html,/<details><summary>Requirement & criteria<\/summary>[\s\S]*REQ-A:v2/);assert.equal(JSON.stringify(h.requirements),before);assert.equal(h.events.length,0);
});

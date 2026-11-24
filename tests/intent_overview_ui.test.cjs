const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function harness(){
 const src=fs.readFileSync(path.join(__dirname,'../src/workbench/static/intake.js'),'utf8');
 const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const v1={ref:{id:'INT-001',revision:1},kind:'intent',body:{text:'Value',intake:{business_challenge:'Patients forget.',approach:'Send reminders.',value:'Use clinician time',beneficiaries:'Patients',assumption_owner:'sam'}}};
 const v2={ref:{id:'INT-001',revision:2},kind:'intent',body:{text:'Value',intake:{business_challenge:'Patients know but cannot change.',approach:'Easy rescheduling.',value:'Use clinician time',beneficiaries:'Patients',assumption_owner:'sam'}}};
 const data={intent:[v2],'intent-refinement':[{ref:{id:'ICR',revision:3},body:{status:'incorporated',requested_by:'sam',result_intent:{id:'INT-001',revision:2}}}],goal:[{ref:{id:'G',revision:2},body:{title:'Shorten waits'}}],'success-measure':[{ref:{id:'M-old',revision:2},body:{name:'Missed rate',baseline:'',target:''}},{ref:{id:'M-new',revision:1},body:{name:'Refill rate',baseline:'',target:'',outcome_status:'not-evaluated'}}]};
 const c={state:{actors:{priya:{name:'Dana Okafor',role:'Business sponsor'},sam:{name:'Jordan Reyes',role:'Research evidence reviewer'},lee:{name:'Mei Chen',role:'Design reviewer'}},intake:{cases:[{body:{status:'published',base_intent:{id:'INT-001',revision:1},decision_owner:'priya'},reviews:{sam:{body:{}},lee:{body:{}}}}]},packets:[{id:'PKT-INTENT',revision:1,records:[v1,{ref:{id:'M-old',revision:1},kind:'success-measure',body:{}}]}]},esc,records:k=>data[k]||[]};
 vm.createContext(c);vm.runInContext(src.slice(src.indexOf('// Published intent overview')),c);return {c,run:s=>vm.runInContext(s,c)};
}
test('published intent shows the current version, what changed from the previous one and its basis, without writing',()=>{
 const h=harness(),before=JSON.stringify(h.c.state),html=h.run('intentOverview()');
 assert.match(html,/Version 2 · decided by Dana Okafor/);assert.match(html,/What changed in version 2/);assert.match(html,/Problem changed/);assert.match(html,/Proposed approach changed/);assert.doesNotMatch(html,/Who benefits changed/);assert.match(html,/Measure added: refill rate/);
 assert.match(html,/Requested by Jordan Reyes · decided by Dana Okafor · reviewed by Research and Design/);
 assert.match(html,/Patients know but cannot change\.<\/p><div class="intent-previous"><span class="intent-previous-label">Version 1<\/span><p class="pre">Patients forget\./);
 assert.match(html,/Refill rate <span class="ac-state ac-state-edited">New<\/span><\/td><td data-label="Baseline">To confirm<\/td><td data-label="Target">To confirm<\/td><td data-label="Status">Not evaluated/);assert.match(html,/Assumptions owner: Jordan Reyes/);assert.match(html,/Version 2 · current/);assert.match(html,/Starting direction/);
 assert.equal(JSON.stringify(h.c.state),before);
});
test('the change credits the source work and names a different requester',()=>{
 const h=harness();h.run("records=(k=>{const base=records;return q=>q==='intent-refinement'?[{ref:{id:'ICR',revision:3},body:{status:'incorporated',requested_by:'priya',source:{id:'CON-1',revision:1},result_intent:{id:'INT-001',revision:2}}}]:base(q)})()");h.c.get=id=>id==='CON-1'?{body:{owner:'sam',domain:'Research'}}:null;
 const html=h.run('intentOverview()');assert.match(html,/From Jordan Reyes’s Research work · requested by Dana Okafor · decided by Dana Okafor/);assert.doesNotMatch(html,/’s finding/);
});
test('a first version shows no change markers and escapes content',()=>{
 const h=harness();h.c.state.packets=[];h.run("records=k=>k==='intent'?[{ref:{id:'INT-001',revision:1},body:{intake:{business_challenge:'<b>x</b>',value:'V'}}}]:[]");const html=h.run('intentOverview()');assert.doesNotMatch(html,/Changed|What changed|Version history/);assert.match(html,/&lt;b>x&lt;\/b>/);
});

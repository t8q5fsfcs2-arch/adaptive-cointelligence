const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function harness(actor='lee'){
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const packet={id:'PKT',revision:1,title:'Fictional Research',purpose:'Research finding',records:[]},evidence={ref:{id:'FINDING',revision:1},field:'observation',quote:'Three fictional sessions paused.'},req={ref:{id:'REQ',revision:1},body:{title:'Reliable capture'}};
 const report={ref:{id:'INTERP',revision:1},kind:'domain-interpretation',current:true,body:{domain:actor==='sam'?'research':'design',owner:actor,packet,profile:{ref:{id:'DOMAIN',revision:2},fingerprint:'123456789abcdef'},knowledge:[{id:'evidence_standard',title:'Evidence standards',text:'Preserve sample limits.'},{id:'vocabulary',title:'Vocabulary',text:'Finding differs from hypothesis.'}],mode:'simulated',at:'2026-11-09T12:00:00Z',bridge_links:{},output:{summary:'Preserve the evidence limit.',applications:[{knowledge_id:'evidence_standard',application:'Do not extrapolate.',evidence:[evidence]}],findings:[{kind:'conflict',title:'Confirmation before storage?',detail:'Proposed feedback may imply success too early.',question:'What state is confirmed?',knowledge_ids:['evidence_standard'],evidence:[evidence],requirement_ids:['REQ'],route:'requirement'}],limitations:'Fictional and untested.'}}};
 const ctx={records:()=>[],state:{actor,project:{id:'demo',version:1},domains:{active:actor==='sam'?'research':'design'},domain_interpretation:{packets:[packet],reports:[report]}},Map,Date,document:{addEventListener:()=>{}},get:id=>id==='REQ'?req:null,domainProfile:()=>({key:actor==='sam'?'research':'design',ref:{id:'DOMAIN',revision:2},config:{label:actor==='sam'?'Research':'Design',criteria:['Test states'],expertise:'Professional methods',evidence_standard:'Preserve sample limits.',vocabulary:'Define terms',downstream_questions:'What is unresolved?'}}),domainInfo:()=>({model:{provider:'Configured provider'}}),packetKey:p=>p.id+'|'+p.revision,packetTitle:p=>p.title||p.purpose,label:r=>r.id+':v'+r.revision,esc,date:s=>s,para:v=>`<p>${esc(v)}</p>`,val:(t,v)=>`<strong>${esc(t)}</strong><p>${esc(v)}</p>`,button:(t,a,id='',css='')=>`<button data-action="${a}" data-id="${id}" class="${css}">${t}</button>`,modal:(...args)=>ctx.lastModal=args,settingSelector:(id,title,options,name)=>`<label>${title}<select id="${id}" name="${name}">${options}</select></label>`,bridgeInfo:()=>({boards:{'research-design':'Research · Design'},actors:['sam','lee','alex']}),bridgePerson:a=>a,command:async(a,d)=>{ctx.sent={a,d};return {};},$:id=>({value:id==='#interpretation-route'?'requirement':'',addEventListener:()=>{},close:()=>{}})};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-interpretation.js'),'utf8'),ctx);
 return {ctx,packet,report,req,run:s=>vm.runInContext(s,ctx)};
}
test('Research and Design share one collapsed panel; rendering never assesses automatically',()=>{
 for(const a of ['sam','lee']){const h=harness(a),html=h.run('interpretationPanel()');assert.match(html,/<details class="domain-interpretation-panel"\s*>/);assert.match(html,/Domain interpretation/);assert.match(html,/Examine interpretation/);assert.match(html,/Original content stays intact/);assert.equal(h.ctx.sent,undefined);}
});
test('applied knowledge has evidence and exact profile version; unused guidance is not labeled applied',()=>{
 const h=harness(),html=h.run('interpretationSavedContent(interpretationReport("INTERP"))');assert.match(html,/Knowledge applied \(1\)/);assert.match(html,/Evidence standards/);assert.match(html,/DOMAIN:v2/);assert.match(html,/FINDING:v1/);assert.doesNotMatch(html,/Finding differs from hypothesis/);assert.match(html,/not certified compliance/);assert.match(html,/Potential conflict/);
});
test('stale interpretations retain evidence but cannot send a new bridge issue',()=>{
 const h=harness();h.report.current=false;h.run('openInterpretation("INTERP")');const html=h.ctx.lastModal[1];assert.match(html,/Inputs changed/);assert.match(html,/Assess current inputs/);assert.doesNotMatch(html,/data-action="interpretation-bridge"/);assert.match(html,/Three fictional sessions/);
});
test('bridge publication explicitly confirms the selected finding and exact requirement',async()=>{
 const h=harness();h.run('interpretationBridge("INTERP",0)');assert.match(h.ctx.lastModal[1],/Other private findings remain private/);assert.match(h.ctx.lastModal[1],/name="confirm"/);
 const values={route:'requirement',target:'REQ',owner:'lee',confirm:'on'};await h.ctx.lastModal[3]({get:k=>values[k],getAll:()=>['research-design']});assert.equal(h.ctx.sent.a,'domain-interpretation-bridge');assert.equal(h.ctx.sent.d.expected.id,'INTERP');assert.equal(h.ctx.sent.d.index,0);assert.equal(h.ctx.sent.d.target.revision,1);assert.equal(h.ctx.sent.d.confirm,true);assert.equal(h.ctx.sent.d.actor,undefined);
});
test('simulated examples are labeled and all assessment text is escaped',()=>{
 const h=harness();h.report.body.output.summary='<script>unsafe()</script>';h.run('openInterpretation("INTERP")');assert.match(h.ctx.lastModal[1],/Fictional demonstration/);assert.match(h.ctx.lastModal[1],/&lt;script>/);assert.doesNotMatch(h.ctx.lastModal[1],/<script>/);
});
test('shared receipt links open its bridge instead of creating duplicate actions',()=>{
 const h=harness();h.report.body.bridge_links={'0':{issue:{id:'ISSUE',revision:1}}};const html=h.run('interpretationSavedContent(interpretationReport("INTERP"))');assert.match(html,/data-action="interpretation-issue" data-id="ISSUE"/);assert.doesNotMatch(html,/data-action="interpretation-bridge"/);
});
test('unassessed packet shows a clear action and configured model disclosure',()=>{
 const h=harness();h.ctx.state.domain_interpretation.reports=[];h.ctx.state.packets=[h.packet];assert.match(h.run('interpretationPanel()'),/Not assessed/);h.run('interpretationAssess("PKT|1")');assert.match(h.ctx.lastModal[1],/the configured model/);assert.doesNotMatch(h.ctx.lastModal[1],/Configured provider|OpenAI|Anthropic/);assert.match(h.ctx.lastModal[1],/assessment stays private/);assert.equal(h.ctx.sent,undefined);
});

test('changing the selected packet keeps disclosure open within its own role and project',()=>{
 const h=harness();h.run("interpretationSelections.set('demo|1|lee||rail','PKT|1')");assert.match(h.run('interpretationPanel()'),/domain-interpretation-panel" open>/);h.ctx.state.project.version=2;assert.doesNotMatch(h.run('interpretationPanel()'),/domain-interpretation-panel" open>/);
});

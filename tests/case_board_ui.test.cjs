const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const read=f=>fs.readFileSync(path.join(__dirname,'../src/workbench/static',f),'utf8');
const drawer=(id,label,extra={})=>({ref:{id,revision:1},body:{label,status:'active',included:true,...extra}});
function ctx({evidence={},measures=[],issues=[],intents=1,contributions=[],refinements=[]}={}){
 const data={'requirement-drawer':[drawer('DRW-needs','Customer and user needs'),drawer('DRW-needs/jobs','Jobs'),drawer('DRW-needs/pains','Pains'),drawer('DRW-experience','Experience and usability'),drawer('DRW-experience/ease','Ease of use'),drawer('DRW-experience/access','Accessibility'),drawer('DRW-experience/old','Excluded',{included:false})],
  'success-measure':measures,goal:[{ref:{id:'G',revision:1},body:{title:'Shorten waits',basis_values:{value:'Reduce missed appointments.'}}}],contribution:contributions,'intent-refinement':refinements,
  intent:Array.from({length:intents},(_,i)=>({ref:{id:'INT',revision:i+1},body:{}}))};
 const c={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),state:{requirement_evidence:evidence,bridge:{issues},actors:{priya:{name:'Dana Okafor'}},intake:{cases:[{body:{status:'published',requested_by:'priya',snapshot:{values:{value:'Reduce missed appointments.',research_question:'Why do patients miss?',operations_question:'Which visits need staff?'}}}}]},cases:[]},
  records:k=>data[k]||[],projectHomeLatest:k=>data[k]||[],projectHomeNav:t=>`data-nav="${t}"`,document:{addEventListener(){}},window:{},renders:0};
 c.render=()=>{c.renders++;};vm.createContext(c);vm.runInContext(read('case.js'),c);return c;
}
const ev=(level,extra={})=>({level,contributions:2,on_current:1,teams:['Design'],current_teams:['Design'],open_contradictions:0,open_gaps:0,...extra});
test('areas follow the D007 rule: empty, low if any part is low, high only when every part is high',()=>{
 let c=ctx();assert.deepEqual(JSON.parse(vm.runInContext("JSON.stringify(caseAreas().map(a=>[a.key,a.level,a.parts.length,a.side]))",c)),[['needs','empty',2,'problem'],['experience','empty',2,'solution']]);
 c=ctx({evidence:{'REQ-INTAKE-experience/ease':ev('high')}});assert.equal(vm.runInContext("caseAreas()[1].level",c),'moderate');assert.equal(vm.runInContext("caseAreas()[1].next",c),'1 part needs evidence');
 c=ctx({evidence:{'REQ-INTAKE-experience/ease':ev('high'),'REQ-INTAKE-experience/access':ev('high')}});assert.equal(vm.runInContext("caseAreas()[1].level",c),'high');
 c=ctx({evidence:{'REQ-INTAKE-experience/ease':ev('high'),'REQ-INTAKE-experience/access':ev('low',{open_contradictions:1})}});assert.equal(vm.runInContext("caseAreas()[1].level",c),'low');assert.equal(vm.runInContext("caseAreas()[1].next",c),'Resolve at the table');
});
test('the board shows level three ways, numbered sections and locked targets, and changes no state',()=>{
 const c=ctx({evidence:{'REQ-INTAKE-experience/ease':ev('moderate')},measures:[{ref:{id:'M1'},body:{name:'Missed-appointment rate',target:''}},{ref:{id:'M2'},body:{name:'Reply rate',target:'60%'}}]});
 const before=JSON.stringify(c.state),html=vm.runInContext('caseBoard()',c);
 for(const s of ['01 · Mission','02 · Win conditions','03 · Case strength','06 · Milestones'])assert.ok(html.includes(s),s);
 assert.match(html,/Reduce missed appointments\./);assert.match(html,/Why do patients miss\?/);assert.match(html,/Which visits need staff\?/);
 assert.match(html,/case-glyph lv-moderate/);assert.match(html,/case-bar lv-moderate/);assert.match(html,/case-row-level">Moderate/);
 assert.match(html,/1\/2 set/);assert.match(html,/Missed-appointment rate<\/span><span class="case-measure-target ">/);
 assert.match(html,/data-action="case-area" data-id="DRW-experience"/);assert.match(html,/data-action="case-ready"/);
 assert.doesNotMatch(html,/<input|<textarea|style="/);assert.equal(JSON.stringify(c.state),before);
});
test('milestones are earned only from recorded events',()=>{
 let c=ctx();let ms=JSON.parse(vm.runInContext('JSON.stringify(caseMilestones(caseAreas()).map(m=>m.earned))',c));assert.deepEqual(ms,[false,false,false,false,false,false]);
 c=ctx({intents:2,refinements:[{ref:{id:'ICR',revision:1},body:{}}],contributions:[{ref:{id:'CON-1',revision:1},body:{domain:'Research',status:'published-for-review'}}],issues:[{ref:{id:'I'},body:{type:'dependency',status:'resolved',owner:'priya'}}],evidence:{'REQ-INTAKE-experience/ease':ev('moderate',{teams:['Design','Research']})}});
 ms=JSON.parse(vm.runInContext('JSON.stringify(caseMilestones(caseAreas()).map(m=>m.earned))',c));assert.deepEqual(ms,[true,true,true,true,false,false]);
});
test('opening an area lists its included parts and each part opens its existing requirement page',async()=>{
 const c=ctx({evidence:{'REQ-INTAKE-experience/ease':ev('high')}});c.$=()=>null;c.window.scrollTo=()=>{};c.projectHome=()=>'home';
 assert.equal(await vm.runInContext("caseAction('case-area','DRW-experience')",c),true);assert.equal(c.renders,1);
 const html=vm.runInContext('caseAreaScreen()',c);assert.match(html,/Experience and usability/);assert.match(html,/data-action="open-drawer" data-id="DRW-experience\/ease"/);assert.doesNotMatch(html,/Excluded/);
 assert.match(html,/data-action="case-back"/);assert.equal(await vm.runInContext("caseAction('case-back','')",c),true);assert.equal(vm.runInContext('caseOpenArea',c),null);
});
test('people without the decision right see the checks and a route to the table, never a form',async()=>{
 const c=ctx();let shown=null;c.modal=(t,b,label,handler)=>{shown={t,b,label,handler};};
 await vm.runInContext("caseAction('case-ready','')",c);assert.equal(shown.t,'Ready to build?');assert.equal(shown.handler,null);
 assert.match(shown.b,/The board informs the call; people make it/);assert.match(shown.b,/data-action="case-table"/);assert.doesNotMatch(shown.b,/<input|<textarea|<form/);
});
test('theme: light and dark tokens exist, stylesheets carry no stray hard-coded colours, the toggle is a local preference',()=>{
 const theme=read('theme.css');assert.match(theme,/--ac-accent:#D4FF3A/);assert.match(theme,/:root\[data-theme="dark"\]\{[^}]*--ac-ground:#0E1330/);
 const js=read('theme.js');assert.match(js,/localStorage\.setItem\('ac-theme'/);assert.doesNotMatch(js,/fetch\(|command\(/);
 const html=read('index.html');assert.ok(html.indexOf('/theme.js')<html.indexOf('/style.css'));assert.ok(html.indexOf('/theme.css')>html.indexOf('/alignment.css'));
 for(const f of fs.readdirSync(path.join(__dirname,'../src/workbench/static')).filter(f=>f.endsWith('.css')&&f!=='theme.css')){
  const body=read(f).replace(/^:root\{[\s\S]*?\n\}/gm,'').replace(/url\([^)]*\)/g,'').replace(/\/\*[\s\S]*?\*\//g,'');
  const stray=(body.match(/(?<![\w-])#[0-9A-Fa-f]{3,6}(?![\w-])/g)||[]).filter(h=>!/^#0+$/.test(h)&&!/^#000/i.test(h));
  assert.deepEqual(stray,[],f);
 }
});
test('the decider records a call through one command with explicit confirmation, and the board shows it',async()=>{
 const c=ctx();c.projectHomeDate=()=>'Nov 23';c.state.actors.priya={name:'Dana Okafor'};
 c.state.readiness={ref:{id:'PROJECT-READINESS',revision:1},can_decide:true,deciders:['priya'],basis_changed:true,outcomes:{ready:'Ready to build','ready-with-conditions':'Ready with conditions','not-yet':'Not yet'},
  current:{outcome:'not-yet',label:'Not yet',reason:'Problem side is empty.',conditions:'',actor:'priya',at:'2026-11-23'},history:[{outcome:'not-yet',label:'Not yet',reason:'Problem side is empty.',actor:'priya',at:'2026-11-23'}]};
 let shown=null,sent=null;c.modal=(t,b,label,handler)=>{shown={b,label,handler};};c.command=async(a,d)=>{sent={a,d};return {message:'ok'};};
 await vm.runInContext("caseAction('case-ready','')",c);
 assert.equal(shown.label,'Record the call');assert.match(shown.b,/name="outcome" value="ready-with-conditions"/);assert.match(shown.b,/name="confirm" required/);assert.match(shown.b,/Basis changed since/);assert.match(shown.b,/It stands until it is reconsidered/);
 const fd=new Map([['outcome','ready'],['reason','Enough evidence.'],['confirm','on']]);await shown.handler({get:k=>fd.get(k)??null});
 assert.equal(sent.a,'readiness-decide');assert.equal(sent.d.confirm,true);assert.deepEqual(JSON.parse(JSON.stringify(sent.d.expected)),{id:'PROJECT-READINESS',revision:1});assert.equal(sent.d.basis,undefined);
 const board=vm.runInContext('caseBoard()',c);assert.match(board,/case-call lv-low/);assert.match(board,/<b>Not yet<\/b>/);
});
test('the board credits the intent revision and keeps the handoff summary',()=>{
 const c=ctx({intents:2,refinements:[{ref:{id:'ICR',revision:1},body:{requested_by:'priya',source:{id:'CON-R'}}}]});
 c.get=id=>id==='CON-R'?{body:{owner:'sam',domain:'Research'}}:null;c.state.actors.sam={name:'Jordan Reyes'};
 c.state.cases=[{kind:'decision-case',body:{status:'approved'}}];c.state.demo_delivery={mode:'simulated',previews:[1,2]};
 const html=vm.runInContext('caseBoard()',c);
 assert.match(html,/Intent v2 from Jordan’s finding/);
 assert.match(html,/<b>1<\/b> requirement approved/);assert.match(html,/<b>2<\/b> items staged for Jira and Azure DevOps · simulated, nothing sent/);assert.match(html,/data-nav="delivery">Open handoff/);
});

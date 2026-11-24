const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const read=f=>fs.readFileSync(path.join(__dirname,'../src/workbench/static',f),'utf8');
const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
function fn(file,name,extra={}){const src=read(file);const i=src.indexOf('function '+name+'(');const j=src.indexOf('\nfunction',i+5);const c={esc,...extra};vm.createContext(c);vm.runInContext(src.slice(i,j<0?undefined:j),c);return c;}
test('automatic goal save drops blank new rows but keeps saved and filled ones',()=>{
 const c=fn('goals.js','sponsorGoalsWithoutBlankRows',{state:{goals:{goals:[{id:'G-1'}],measures:[]}}});
 const out=vm.runInContext("sponsorGoalsWithoutBlankRows({goals:[{id:'G-1',title:''},{id:'G-new',title:'',outcome:''},{id:'G-new2',title:'New goal'}],measures:[{id:'M-new',name:'',baseline:'',target:''}]})",c);
 assert.equal(JSON.stringify(out.goals.map(g=>g.id||g.title)),JSON.stringify(['G-1','G-new2']));assert.equal(out.measures.length,0);
});
test('sponsor decisions are titled by what happened and use short dates',()=>{
 const c=fn('intake.js','intakeDecisionHistory',{date:x=>'RAW '+x,projectHomeDate:()=>'Nov 23',ref:()=>'',sourceDetails:()=>'',para:t=>`<p>${t}</p>`,val:(a,b)=>`${a}:${b}`,button:t=>`<button>${t}</button>`,intakeNames:{},
  state:{intake:{decisions:[{ref:{id:'D1',revision:1},body:{at:'2026-11-23',disposition:'publish-for-investigation',rationale:'first',case:{id:'C1'}}},{ref:{id:'D2',revision:1},body:{at:'2026-11-23',disposition:'publish-for-investigation',rationale:'second',changes:{business_challenge:{before:'a',after:'b'}},case:{id:'C2'}}},{ref:{id:'D3',revision:1},body:{at:'2026-11-23',disposition:'publish-for-investigation',rationale:'x',changes:{name:{before:'',after:'P'}},case:{id:'C3'}}}]}}});
 const html=vm.runInContext('intakeDecisionHistory()',c);
 assert.equal((html.match(/Published the starting direction/g)||[]).length,2);assert.match(html,/Revised Business Intent/);assert.match(html,/Decision: publish for investigation/);assert.match(html,/Nov 23 · Business sponsor/);assert.doesNotMatch(html,/RAW/);
});
test('the updates feed offers Mark all read only when more than one update is new',()=>{
 const make=n=>fn('project-flow.js','projectUpdateFeed',{button:(t,a)=>`<button data-action="${a}">${t}</button>`,state:{domain_updates:Array.from({length:3},(_,i)=>({ref:{id:'U'+i},title:'T'+i,new:i<n}))}});
 assert.match(vm.runInContext('projectUpdateFeed()',make(2)),/data-action="pflow-updates-read">Mark all read/);
 assert.doesNotMatch(vm.runInContext('projectUpdateFeed()',make(1)),/Mark all read/);
});

const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const config={components:{actor:{label:'Actor',holds:'Who it is about'},situation:{label:'Situation',holds:'When or where it applies'},claim:{label:'Claim',holds:'What is said'},strength:{label:'Strength',holds:'How sure'},status:{label:'Status',holds:'Open, resolved, approved'}},categories:{}};
function ctx(structure){const c={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),state:{knowledge_system:{config,structure}},knowledgeCardInfo:()=>({types:{finding:{label:'Finding'}}})};vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/knowledge-system.js'),'utf8'),c);return c;}
test('D014: system checks report differences by kind and leave judgment to people',()=>{
 const c=ctx({differences:[{title:'Most knew in advance',kinds:['scope-differs'],messages:['Scope differs between groups: check applicability.'],next:'A reviewer judges whether this is compatible, unsupported or contradictory. Material consequences go to the decision owner.',groups:[{group:'Research',links:[{relation:'supports',conditions:'Shift workers',revision:1}]},{group:'Design',links:[{relation:'informs',conditions:'',revision:1}]}]}],challenge_reach:[],stale_pins:[],category_gaps:[]});
 const html=vm.runInContext('knowledgeSystemChecks()',c);
 assert.match(html,/System checks <span class="caption">1/);assert.match(html,/check applicability/);assert.match(html,/no scope stated/);assert.match(html,/reviewer judges/);
 assert.doesNotMatch(html,/data-action=|<button|Conflict/);
});
test('D014: scope leads, other differences fold away, and relations read as words',()=>{
 const c=ctx({differences:[{title:'Finding',kinds:['scope-differs','relation-differs','use-differs'],messages:['Scope differs between groups: check applicability.','Groups link to it with different relations.','Groups use it differently.'],next:'A reviewer judges.',groups:[{group:'Design',links:[{relation:'supported-by',conditions:'All patients',revision:1}]}]}],challenge_reach:[],stale_pins:[],category_gaps:[]});
 const html=vm.runInContext('knowledgeSystemChecks()',c);
 assert.match(html,/<p>Scope differs between groups: check applicability\.<\/p>/);assert.match(html,/<summary>Also differs<\/summary><p class="caption">Groups link to it with different relations\. Groups use it differently\./);
 assert.match(html,/Design: supported by · All patients/);assert.doesNotMatch(html,/supported-by/);
});
test('D014: challenge reach names each piece of work once and stays short',()=>{
 const deps=['A','A','B','C','D','E','F','G'].map((t,i)=>({id:'X'+i,title:t,depth:1}));
 const html=vm.runInContext('knowledgeSystemChecks()',ctx({differences:[],stale_pins:[],category_gaps:[],challenge_reach:[{title:'Challenge',issue:{id:'I'},dependents:deps,packets:[{},{}]}]}));
 assert.match(html,/Depends on it: A, B, C, D, E and 2 more/);assert.match(html,/Held in 2 packets/);
});
test('D014: an empty structure says there is nothing to look at',()=>{
 assert.match(vm.runInContext('knowledgeSystemChecks()',ctx({differences:[],challenge_reach:[],stale_pins:[],category_gaps:[]})),/Nothing needs a look/);
});
test('D014: older packet pins are folded and not counted as needing attention',()=>{
 const html=vm.runInContext('knowledgeSystemChecks()',ctx({differences:[],challenge_reach:[],category_gaps:[],stale_pins:[{purpose:'Design handoff',changed:[{},{}]}]}));
 assert.match(html,/System checks <span class="caption">0/);assert.match(html,/<details class="page-about"><summary>Packets pinned to older versions \(1\)/);assert.match(html,/2 items have/);
});
test('D014: a block shows what it carries, what it lacks and whether it counts',()=>{
 const c=ctx(null);const m={system:{type:'finding',components:['actor','claim','status'],missing:['situation','strength'],links:[{eligibility:{eligible:false,counts:false,coaching:'Add when or where it applies and it can count toward Customer and user needs.'}}]}};
 const html=vm.runInContext('knowledgeBlockSystem({ref:{id:"CARD-1"}},m)',Object.assign(c,{m}));
 assert.match(html,/Carries: Actor, Claim, Status/);assert.match(html,/also needs when or where it applies, how sure/);assert.match(html,/Not yet/);assert.match(html,/Eligible is not counted/);
});

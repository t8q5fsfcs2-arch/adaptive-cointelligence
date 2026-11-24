const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function ctx(){const c={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),state:{domain_knowledge:{domains:[],kinds:{},reach:{project:'This project',domain:'This team’s domain','named-domains':'Named domains',enterprise:'Enterprise'},lead_reach:['domain','project']}},document:{addEventListener(){}}};
 vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-knowledge.js'),'utf8'),c);return c;}
test('a concept shows its boundaries and a four-step reach ladder, read-only',()=>{
 const c=ctx();c.e={kind:'term',includes:'Confirmed visits.',excludes:'Cancellations.',not_confused_with:'Late <cancellation>',reach:'domain'};
 const html=vm.runInContext('knowledgeMeaning(e)',c);
 assert.match(html,/knowledge-bound-plus"><strong>Includes<\/strong> Confirmed visits\./);assert.match(html,/Late &lt;cancellation>/);
 assert.equal((html.match(/<li class="/g)||[]).length,7);assert.match(html,/class="is-included"><span>This project/);assert.match(html,/class="is-current" aria-current="true"><span>This team’s domain/);
 assert.match(html,/needs an approved proposal/);assert.doesNotMatch(html,/<input|<textarea|<select|data-action=|style="/);
});
test('entries saved before boundaries existed read as project reach with nothing set; rules and relationships carry none',()=>{
 const c=ctx();c.e={kind:'term'};const html=vm.runInContext('knowledgeMeaning(e)',c);
 assert.match(html,/No boundaries set yet/);assert.match(html,/class="is-current" aria-current="true"><span>This project/);
 c.e={kind:'standard'};assert.equal(vm.runInContext('knowledgeMeaning(e)',c),'');
});
test('the entry form offers only the reach a lead may set and sends boundaries for concepts only',()=>{
 const src=fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-knowledge.js'),'utf8');
 assert.match(src,/domainKnowledgeInfo\(\)\.lead_reach/);assert.match(src,/for\(const k of \['includes','excludes','not_confused_with','reach'\]\)delete updated\[k\];if\(\['term','category'\]\.includes\(kind\)\)/);
});

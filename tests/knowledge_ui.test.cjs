const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function harness(canEdit=true){
 const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const entry=(id,kind,title,extra={})=>({id,kind,title,definition:title+' meaning',aliases:[],parent_id:'',subject_id:'',predicate:'',object_id:'',source:'Synthetic',status:'active',...extra});
 const entries=[entry('O','term','Observation'),entry('F','term','Finding',{aliases:['insight']}),entry('R','relationship','Observation informs Finding',{subject_id:'O',predicate:'informs',object_id:'F'}),entry('M','category','Research methods'),entry('I','category','Interviews',{parent_id:'M'}),entry('D','term','Draft term',{status:'draft'}),entry('A','term','Old term',{status:'archived'})];
 const c={state:{domains:{active:'research'},domain_knowledge:{domains:[{key:'research',label:'Research',ref:{id:'DK',revision:2},can_edit:canEdit,entries,history:[{ref:{id:'DK',revision:1},entries:entries.slice(0,3)},{ref:{id:'DK',revision:2},entries}]},{key:'design',label:'Design',ref:null,can_edit:false,entries:[],history:[]}],kinds:{}}},
  esc,tag:t=>esc(t),button:(t,a,id='',cls='')=>`<button data-action="${esc(a)}" data-id="${esc(id)}" class="${cls}">${esc(t)}</button>`,head:(t,s,a='')=>`<h1>${esc(t)}</h1><p>${esc(s)}</p>${a}`,document:undefined};
 vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-knowledge.js'),'utf8').replace(/document\.addEventListener\([\s\S]*?\}\)\(\);\}\);/,''),c);
 return {c,run:s=>vm.runInContext(s,c)};
}
test('knowledge is a browsable glossary and taxonomy with relationships visible',()=>{
 const h=harness();h.run("knowledgeEntry='F'");const html=h.run('knowledgeScreen()');
 assert.match(html,/Research knowledge · version 2 · 6 entries/);assert.match(html,/Terms<\/span><span class="knowledge-count">3/);assert.match(html,/Categories<\/span><span class="knowledge-count">2/);
 assert.match(html,/knowledge-tree[\s\S]*Research methods[\s\S]*<ul><li>[\s\S]*Interviews/);assert.match(html,/Also called: insight/);assert.match(html,/Observation<\/button><span class="knowledge-edge-label">informs<\/span><span class="knowledge-self">Finding/);assert.match(html,/Added in version 1 · current version 2/);
 assert.match(html,/Draft · not used yet/);assert.match(html,/Archived \(1\)/);assert.match(html,/data-action="knowledge-edit" data-id="research\|F"/);
});
test('knowledge editing appears only where the backend grants it, and filters do not change entries',()=>{
 const h=harness(false),before=JSON.stringify(h.c.state);h.run("knowledgeType='relationship'");const html=h.run('knowledgeScreen()');assert.doesNotMatch(html,/knowledge-edit|Add entry|Team setup/);assert.match(html,/read only/);assert.match(html,/Observation informs Finding/);assert.doesNotMatch(html,/knowledge-card-title">Finding</);assert.equal(JSON.stringify(h.c.state),before);
 h.run("knowledgeDomain='design';knowledgeType='all'");assert.match(h.run('knowledgeScreen()'),/No entries yet/);
});

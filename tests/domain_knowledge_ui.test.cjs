const {test}=require('node:test');const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(admin=true){
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const term={id:'KN-000000000001',kind:'term',title:'Local draft',definition:'Local work is not a server submission.',aliases:[],parent_id:'',subject_id:'',predicate:'',object_id:'',source:'Fictional local definition v1',status:'active'},d={key:'support',label:'Support',purpose:'Support readiness',leaders:['sam'],members:['sam','lee'],runtime:'available',definition_ref:{id:'DEF',revision:2},ref:{id:'KNOWLEDGE',revision:3},entries:[term],history:[],can_edit:true};
 const ctx={selectorChevron:()=>'<svg></svg>',state:{actor:'sam',actors:{sam:{name:'Sam',role:'Research'},lee:{name:'Lee',role:'Design'}},domain_knowledge:{domains:[d],kinds:{term:'Glossary term',category:'Taxonomy category',relationship:'Concept relationship',standard:'Standard or rule',practice:'Best practice'},can_add:admin,can_manage_users:admin,available:['support'],active:'support'}},document:{addEventListener:()=>{}},crypto:{randomUUID:()=> '000000000003-aaaa'},domainText:(name,title,value)=>`<textarea name="${name}" aria-label="${title}">${esc(value)}</textarea>`,settingInput:(name,title,value)=>`<input name="${name}" aria-label="${title}" value="${esc(value)}">`,settingSelector:(id,title,options,name='')=>`<label>${title}<select id="${id}" name="${name}">${options}</select></label>`,esc,label:r=>r.id+':v'+r.revision,date:v=>v,bridgePerson:a=>a,tag:t=>`<span>${esc(t)}</span>`,button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,modal:(...args)=>ctx.modal=args,command:async(a,data)=>{ctx.sent={a,data};return {};},$:id=>({value:'term',addEventListener:()=>{}})};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-knowledge.js'),'utf8'),ctx);return {ctx,d,term,run:s=>vm.runInContext(s,ctx)};
}
test('domain setup supports name purpose assigned users and domain leaders',async()=>{
 const h=harness();await h.run('domainSetupForm("support")');const html=h.ctx.modal[1];assert.match(html,/Domain name/);assert.match(html,/Assigned project users/);assert.match(html,/Domain leaders/);assert.match(html,/name="confirm" required/);assert.match(html,/private workbench/);
 const data={label:'Support renamed',purpose:'A narrower support purpose',reason:'Clarify ownership'};await h.ctx.modal[3]({get:k=>data[k],getAll:k=>k==='member'?['sam','lee']:['sam']});assert.equal(h.ctx.sent.a,'domain-update');assert.equal(h.ctx.sent.data.expected.revision,2);assert.deepEqual(h.ctx.sent.data.members,['sam','lee']);
});
test('domain leader editing cannot turn disabled membership controls into access grants',async()=>{
 const h=harness(false);await h.run('domainSetupForm("support")');assert.match(h.ctx.modal[1],/name="member"[^>]*disabled/);await h.ctx.modal[3]({get:k=>({label:'Support',purpose:'Purpose',reason:'Clarify'})[k],getAll:()=>['attacker']});assert.deepEqual(h.ctx.sent.data.members,['sam','lee']);assert.deepEqual(h.ctx.sent.data.leaders,['sam']);
});
test('knowledge editor exposes type definitions source review status and change rationale',()=>{
 const h=harness();h.run('domainKnowledgeEdit("support","KN-000000000001")');const html=h.ctx.modal[1];for(const text of ['Entry type','Meaning, rule or practice','Source or local rationale','Review status','Why this change?','Save knowledge version'])assert.match(h.ctx.modal.join(' '),new RegExp(text.replace('?','\\?')));assert.match(html,/does not certify compliance/);assert.match(html,/name="confirm_active"/);
});
test('knowledge map preserves explicit concepts direction and relation meaning',()=>{
 const h=harness(),b={...h.term,id:'KN-000000000002',title:'Server submission'},r={...h.term,id:'KN-000000000003',kind:'relationship',title:'Different states',subject_id:h.term.id,object_id:b.id,predicate:'differs-from'};h.d.entries.push(b,r);const html=h.run('knowledgeMap(domainKnowledgeProfile("support"))');assert.match(html,/Local draft/);assert.match(html,/differs-from/);assert.match(html,/Server submission/);assert.match(html,/not inferred equivalence/);
});
test('workspace selector offers only assigned domains and preserves project-role access',()=>{
 const h=harness();h.ctx.state.domain_knowledge.domains.push({...h.d,key:'restricted',label:'Restricted'});const html=h.run('domainWorkspaceControl()');assert.match(html,/Support/);assert.doesNotMatch(html,/Restricted/);assert.match(html,/Project role/);
});
test('domain knowledge is editable from settings with source and version history',()=>{
 const h=harness();h.run('openDomainKnowledge("support")');const html=h.ctx.modal[1];assert.match(html,/Edit domain setup/);assert.match(html,/Add knowledge entry/);assert.match(html,/History & archived entries/);assert.match(html,/Source & identity/);assert.match(html,/KNOWLEDGE/);
});
test('knowledge text and domain labels are escaped',()=>{
 const h=harness();h.d.label='<script>bad</script>';h.term.definition='<img src=x>';h.run('openDomainKnowledge("support")');assert.match(h.ctx.modal[1],/&lt;script>/);assert.match(h.ctx.modal[1],/&lt;img/);assert.doesNotMatch(h.ctx.modal[1],/<script>/);
});

const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(domain='research'){
 const actor=domain==='research'?'sam':'lee',work={ref:{id:'D',revision:1},kind:'contribution-draft',body:{owner:actor,domain_key:domain,chassis:1,title:'Fictional work',source_refs:[],requirement_refs:[],input_refs:[]}},thread={ref:{id:'CHAT',revision:1},body:{draft_id:'D'},plan:[]},calls=[],listeners={};
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const c={state:{actor,project:{id:'P',version:1},domains:{active:domain,sources:[],reports:[],handoffs:[],deliverables:{}},domain_chat:{threads:[thread],turns:[],reports:[],working_history:[],implications:[],submissions:[],objectives:[]}},selected:'D',view:'contributions',busy:false,Map,Date,crypto:{randomUUID:()=> 'evaluation-cycle-test'},setTimeout:()=>1,clearTimeout:()=>{},document:{addEventListener:(n,f)=>(listeners[n]??=[]).push(f),getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[]},domainInfo:()=>c.state.domains,domainProfile:()=>({key:domain,config:{label:domain==='research'?'Research':'Design',descriptor:'Domain expertise'}}),domainInputOptions:()=>[],domainFieldLabels:{},records:k=>k==='contribution-draft'?[work]:[],get:id=>id==='D'?work:null,label:r=>r?.id+':v'+r?.revision,esc,para:v=>`<p>${esc(v)}</p>`,val:(t,v)=>`<h4>${esc(t)}</h4><p>${esc(v)}</p>`,date:v=>v||'',button:(t,a)=>`<button data-action="${a}">${t}</button>`,render:()=>{},toast:()=>{},load:async()=>{},command:async(action,data)=>{calls.push({action,data});return {ref:{id:'SUB',revision:1}};}};
 vm.createContext(c);require('./ui_reference_helpers.cjs')(c);for(const f of ['domain-chat.js','working-report.js','domain-development.js','knowledge-cards.js','knowledge-dossier.js','integrity-gaps.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static',f),'utf8'),c);return {c,work,thread,calls,listeners,run:s=>vm.runInContext(s,c)};
}

function addCard(h,id='CARD-1',type='finding',title='Shift handoff',conversation='CHAT',status='held'){
 const row={ref:{id,revision:1},kind:'domain-implication',current:true,body:{owner:h.c.state.actor,domain:h.c.state.domains.active,conversation,status,card:{type,fields:{},relations:[]},payload:{kind:'open-question',title,statement:'A bounded working observation.',rationale:'Fictional example.',targets:[],evidence:[]}}};h.c.state.domain_chat.implications.push(row);return row;
}
test('collection shows trading cards with real stats and a summary, without writes',()=>{
 const h=harness();const r=addCard(h,'CARD-1','hypothesis','Text cancellation refills slots');addCard(h,'CARD-2','note','Loose idea');
 const html=h.run('knowledgeCardList()');assert.match(html,/kc-card kc-fam-open/);assert.match(html,/HYPOTHESIS|Hypothesis/);assert.match(html,/data-action="kc-open" data-id="CARD-1"/);assert.match(html,/0 src/);assert.match(html,/0 links/);
 assert.match(html,/kc-card kc-fam-note needs-care/);
 const panel=h.run('knowledgeCardsPanel()');assert.match(panel,/<strong>2<\/strong> blocks/);assert.match(panel,/<strong>1<\/strong> to look after/);assert.equal(h.calls.length,0);
});
test('opening a card shows its dossier; Edit opens the existing editor; nothing is saved',async()=>{
 const h=harness();addCard(h,'CARD-1','finding','Shift handoff');
 await h.run("knowledgeCardAction('kc-open','CARD-1')");let html=h.run('knowledgeCardsPanel()');
 assert.match(html,/kc-dossier/);assert.match(html,/Completeness 2\/5/);assert.match(html,/data-action="kc-edit"/);assert.doesNotMatch(html,/id="knowledge-card-editor"/);
 assert.match(html,/data-action="kc-select"/);assert.match(html,/data-action="kc-assess"/);assert.match(html,/data-action="kc-archive"/);
 await h.run("knowledgeCardAction('kc-edit','CARD-1')");html=h.run('knowledgeCardsPanel()');assert.match(html,/id="knowledge-card-editor"/);
 assert.equal(h.calls.filter(c=>c.action==='knowledge-card-save').length,0);
});
test('dossier tabs show sources, links and history from the saved block',async()=>{
 const h=harness();const r=addCard(h,'CARD-1','finding','Knew a day ahead');r.body.payload.evidence=[{source:'SRC-1:v1',quote:'9 of 12 knew ahead',page:null}];r.body.created_at='2026-11-20';r.body.at='2026-11-22';r.ref.revision=3;
 h.c.state.domain_chat.knowledge_cards={types:h.run('knowledgeCardInfo().types'),relations:{supports:'Supports'},catalogue:[{ref:r.ref,type:'finding',relations:[{relation:'supports',ref:{id:'CARD-9',revision:1},title:'Other block',changed:true,rationale:'Because.'}],backlinks:[],shared:null}],targets:[{ref:{id:'SRC-1',revision:1},title:'Interview notes',source:true}]};
 await h.run("knowledgeCardAction('kc-open','CARD-1')");
 h.run("knowledgeCardView().dossierTab='sources'");assert.match(h.run('knowledgeCardsPanel()'),/Interview notes<\/strong>[\s\S]*9 of 12 knew ahead/);
 h.run("knowledgeCardView().dossierTab='connections'");let html=h.run('knowledgeCardsPanel()');assert.match(html,/Supports<\/span>[\s\S]*Other block/);assert.match(html,/Newer version/);
 h.run("knowledgeCardView().dossierTab='care'");html=h.run('knowledgeCardsPanel()');assert.match(html,/A linked item has a newer version/);assert.match(html,/data-action="kc-edit-section" data-id="CARD-1\|links"/);assert.match(html,/not whether it is right/);
 h.run("knowledgeCardView().dossierTab='history'");html=h.run('knowledgeCardsPanel()');assert.match(html,/Added by hand/);assert.match(html,/version 3/);assert.match(html,/data-action="kc-history"/);
});
test('a care fix opens the editor at that section',async()=>{
 const h=harness();addCard(h,'CARD-1','finding');await h.run("knowledgeCardAction('kc-open','CARD-1')");
 await h.run("knowledgeCardAction('kc-edit-section','CARD-1|evidence')");const html=h.run('knowledgeCardsPanel()');
 assert.match(html,/id="knowledge-card-editor"/);assert.match(html,/data-knowledge-disclosure="evidence" open/);
});
test('carrying a passage or unsaved edits keep the editor instead of the dossier',async()=>{
 const h=harness();const row=addCard(h,'CARD-1','finding');await h.run("knowledgeCardAction('kc-open','CARD-1')");
 h.c.row=row;h.run("knowledgeCardDraft(row).dirty=true");assert.match(h.run('knowledgeCardsPanel()'),/id="knowledge-card-editor"/);
});
test('block text is escaped on cards and in the dossier',async()=>{
 const h=harness();addCard(h,'CARD-1','finding','<img src=x onerror=1>');assert.doesNotMatch(h.run('knowledgeCardList()'),/<img/);
 await h.run("knowledgeCardAction('kc-open','CARD-1')");assert.doesNotMatch(h.run('knowledgeCardsPanel()'),/<img/);
});
test('D014: the block overview and "How this block counts" give one reading',()=>{
 const h=harness();const row={ref:{id:'CARD-1',revision:1},body:{status:'held',payload:{title:'T',statement:'S',evidence:[]},card:{type:'finding',fields:{},relations:[]}}};
 const m={type:'finding',relations:[],backlinks:[],system:{missing:['basis','strength'],links:[{eligibility:{eligible:false,coaching:'Add how sure and it can count toward Customer and user needs.'}},{eligibility:{eligible:true,coaching:'Eligible.'}}]}};
 Object.assign(h.c,{row,m});const care=h.run('kcCare(row,m)').map(t=>t.text);
 assert.equal(care.length,2);assert.match(care[0],/A complete finding also needs basis, strength\./);assert.match(care[1],/count toward Customer and user needs/);
 m.system={missing:[],links:[]};assert.equal(h.run('kcCare(row,m)').length,0);
});

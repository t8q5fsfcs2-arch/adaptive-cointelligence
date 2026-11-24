const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function ctx(o={}){
 const panels=new Map();
 const c={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),state:{actor:'sam',domains:{active:'research'},domain_updates:[{new:true},{new:false}],...o.state},
  CASE_LEVEL_WORD:{empty:'Empty',low:'Low',moderate:'Moderate',high:'High'},caseGlyph:l=>`<i class="g-${l}"></i>`,
  caseAreas:()=>[{id:'DRW-needs',label:'Customer needs',side:'problem',level:'moderate',next:'2nd team → High'},{id:'DRW-out',label:'Outcomes',side:'problem',level:'empty',next:'Needs evidence'},{id:'DRW-x',label:'Experience',side:'solution',level:'empty',next:'x'},{id:'DRW-h',label:'Held',side:'problem',level:'high',next:'Holding'}],
  casePublishedValues:()=>({research_question:'Why do patients <miss>?',operations_question:'Which visits?'}),
  projectHomeNeeds:()=>o.needs||[],chatContextChanged:()=>!!o.changed,chatWork:()=>({}),chatTaskGuidance:()=>({next:{action:'dchat-review-work',title:'Review selected file',why:'notes.txt'}}),
  chatReports:()=>o.reports||[],chatBatchName:()=>'Text 1–200',projectHomeDate:()=>'Nov 24',chatAlignmentRows:()=>[],chatAlignmentGroups:()=>[],projectImplicationsPanel:()=>'',knowledgeCards:()=>[1,2],
  domainPanels:panels,chatKey:()=>'k',domainPanel:()=>panels.get('k')??null,renders:0,saved:0};
 c.renderDomainChat=()=>{c.renders++;};c.saveWorkingReport=async()=>{c.saved++;};
 vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/cockpit.js'),'utf8'),c);return c;}
test('the heads-up strip shows the next step, the weakest area on this team\'s side and the validation question',()=>{
 let html=vm.runInContext('cockpitHud()',ctx());
 assert.match(html,/Next: Review selected file/);assert.match(html,/data-action="cockpit-area" data-id="DRW-out"/);assert.match(html,/Outcomes<\/span>/);assert.match(html,/Empty · Needs evidence/);
 assert.match(html,/Why do patients &lt;miss>\?/);assert.match(html,/data-action="dchat-review-work"/);assert.doesNotMatch(html,/Inputs changed|Experience|style="/);
 html=vm.runInContext('cockpitHud()',ctx({changed:true}));assert.match(html,/Inputs changed since you started/);
});
test('the rail keeps every existing workbench tool and adds Next moves, Reviews and Updates with counts',()=>{
 const c=ctx({needs:[{label:'Decide',title:'A proposal',detail:'Why',attrs:'data-nav="knowledge"'}],reports:[{ref:{id:'R1'},current:true,body:{batch:{}}}]});
 const html=vm.runInContext('cockpitRail()',c);
 for(const a of ['cockpit-next','cockpit-suggest','cockpit-reviews','dchat-guidance-context','dev-implications','dchat-sharing-panel','cockpit-updates'])assert.ok(html.includes(`data-action="${a}"`),a);
 assert.match(html,/Next moves<\/span><span class="workbench-count is-gold">1</);assert.match(html,/Building blocks<\/span><span class="workbench-count">2</);assert.match(html,/Updates<\/span><span class="workbench-count">1</);
 assert.match(html,/Outcomes report/);assert.match(html,/aria-label="Workbench instruments"/);assert.doesNotMatch(html,/is-on/);
});
test('an instrument opens beside the conversation, toggles closed, and saves the report draft first',async()=>{
 const c=ctx();assert.equal(await vm.runInContext("cockpitAction('cockpit-next','')",c),true);assert.equal(c.domainPanels.get('k'),'next');assert.equal(c.saved,1);assert.equal(c.renders,1);
 assert.match(vm.runInContext('cockpitRail()',c),/cockpit-instrument is-on" data-action="cockpit-next" aria-pressed="true"/);
 await vm.runInContext("cockpitAction('cockpit-next','')",c);assert.equal(c.domainPanels.get('k'),null);
 await vm.runInContext("cockpitAction('cockpit-updates','')",c);assert.equal(c.domainPanels.get('k'),'updates');
});
test('Next moves lists what others need first, then your own next step and where work counts; nothing is invented',()=>{
 const c=ctx({changed:true,needs:[{label:'Decide',title:'Finding is distinct from Offered slot',detail:'They differ',attrs:'data-nav="knowledge"'}]});
 const html=vm.runInContext('cockpitNextPanel()',c);
 const order=['Inputs changed since you started','Finding is distinct from Offered slot','Review selected file','Outcomes · Empty','Customer needs · Moderate'].map(s=>html.indexOf(s));
 assert.ok(order.every(i=>i>=0),JSON.stringify(order));assert.deepEqual([...order].sort((a,b)=>a-b),order);
 assert.match(html,/data-nav="knowledge">Open/);assert.match(html,/No saved review of this work yet/);assert.match(html,/data-action="dchat-panel-none"/);
 assert.doesNotMatch(html,/Suggested|Experience|Held/);
});
test('Reviews lists saved reviews only and says a review runs when asked',()=>{
 let html=vm.runInContext('cockpitReviewsPanel()',ctx());assert.match(html,/No reviews saved yet/);assert.match(html,/A review runs only when you ask for one/);
 html=vm.runInContext('cockpitReviewsPanel()',ctx({reports:[{ref:{id:'R1'},current:false,body:{batch:{}}}]}));assert.match(html,/Inputs changed since/);assert.match(html,/data-action="dchat-report" data-id="R1"/);
});
const rep=(id,current,items)=>({ref:{id},current,body:{batch:{},output:{suggestions:items}}});
test('quiet suggestions come only from current saved replies, skip dismissed ones, cap at three and respect the off switch',()=>{
 const items=[{issue:'One <source>',question:'Which others?'},{issue:'No method',question:'How many?'}];
 let c=ctx({reports:[rep('R1',true,items),rep('R0',false,[{issue:'Old',question:'x'}]),rep('R2',true,[{issue:'C',question:''},{issue:'D',question:'d'}])],state:{quiet_suggestions:{enabled:true,ref:null,dismissed:[{report:'R1',index:1}]}}});
 assert.equal(JSON.stringify(vm.runInContext('cockpitSuggestions().map(s=>s.report+s.index)',c)),JSON.stringify(['R10','R20','R21']));
 assert.match(vm.runInContext('cockpitRail()',c),/Suggest<\/span><span class="workbench-count is-accent">3</);
 const html=vm.runInContext('cockpitSuggestPanel()',c);
 assert.match(html,/Suggested · AI partner/);assert.match(html,/One &lt;source>/);assert.match(html,/data-action="cockpit-suggest-ask" data-id="R1\|0"/);assert.match(html,/data-action="cockpit-suggest-dismiss" data-id="all"/);
 assert.doesNotMatch(html,/Old|No method/);assert.equal((html.match(/cockpit-suggest-ask/g)||[]).length,2);   // no "Ask" where there is no question
 c=ctx({reports:[rep('R1',true,items)],state:{quiet_suggestions:{enabled:false,ref:{id:'P',revision:1},dismissed:[]}}});
 assert.equal(vm.runInContext('cockpitSuggestions().length',c),0);assert.doesNotMatch(vm.runInContext('cockpitRail()',c),/is-accent/);
 assert.match(vm.runInContext('cockpitSuggestPanel()',c),/Quiet suggestions are off/);assert.match(vm.runInContext('cockpitSuggestPanel()',c),/>Turn on</);
});
test('with no model connected the panel says so and shows nothing in its place',()=>{
 const c=ctx();c.chatModelUnavailable=()=>true;const html=vm.runInContext('cockpitSuggestPanel()',c);
 assert.match(html,/AI partner unavailable/);assert.doesNotMatch(html,/cockpit-suggestion"|Suggested ·/);
});
test('dismiss and the switch send only ids and the expected version; Ask fills the composer without sending',async()=>{
 const items=[{issue:'One source',question:'Which others?'},{issue:'No method',question:'How many?'}];
 const c=ctx({reports:[rep('R1',true,items)],state:{quiet_suggestions:{enabled:true,ref:{id:'P',revision:2},dismissed:[]}}});const sent=[];
 c.command=async(a,d)=>{sent.push([a,JSON.parse(JSON.stringify(d))]);return {message:'ok'};};c.load=async()=>{};c.toast=()=>{};const draft={text:'',revision:0};c.chatDraft=()=>draft;c.document={getElementById:()=>null};
 await vm.runInContext("cockpitAction('cockpit-suggest-dismiss','R1|1')",c);await vm.runInContext("cockpitAction('cockpit-suggest-dismiss','all')",c);await vm.runInContext("cockpitAction('cockpit-suggest-toggle','')",c);
 assert.deepEqual(sent[0],['suggestions-dismiss',{expected:{id:'P',revision:2},items:[{report:'R1',index:1}]}]);assert.equal(sent[1][1].items.length,2);assert.deepEqual(sent[2],['suggestions-toggle',{expected:{id:'P',revision:2},enabled:false}]);
 await vm.runInContext("cockpitAction('cockpit-suggest-ask','R1|0')",c);assert.equal(draft.text,'Which others?');assert.equal(sent.length,3);
});

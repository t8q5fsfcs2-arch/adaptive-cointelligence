const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(domain='research'){
 const actor=domain==='research'?'sam':'lee',work={ref:{id:'D',revision:1},kind:'contribution-draft',body:{owner:actor,domain_key:domain,chassis:1,title:'Fictional work',source_refs:[],requirement_refs:[],input_refs:[]}},thread={ref:{id:'CHAT',revision:1},body:{draft_id:'D'},plan:[]},calls=[],listeners={};
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const c={state:{actor,project:{id:'P',version:1},domains:{active:domain,sources:[],reports:[],handoffs:[],deliverables:{}},domain_chat:{threads:[thread],turns:[],reports:[],working_history:[],implications:[],submissions:[],objectives:[]}},selected:'D',view:'contributions',busy:false,Map,Date,crypto:{randomUUID:()=> 'evaluation-cycle-test'},setTimeout:()=>1,clearTimeout:()=>{},document:{addEventListener:(n,f)=>(listeners[n]??=[]).push(f),getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[]},domainInfo:()=>c.state.domains,domainProfile:()=>({key:domain,config:{label:domain==='research'?'Research':'Design',descriptor:'Domain expertise'}}),domainInputOptions:()=>[],domainFieldLabels:{},records:k=>k==='contribution-draft'?[work]:[],get:id=>id==='D'?work:null,label:r=>r?.id+':v'+r?.revision,esc,para:v=>`<p>${esc(v)}</p>`,date:v=>v||'',button:(t,a)=>`<button data-action="${a}">${t}</button>`,render:()=>{},toast:()=>{},load:async()=>{},command:async(action,data)=>{calls.push({action,data});return {ref:{id:'SUB',revision:1}};}};
 vm.createContext(c);require('./ui_reference_helpers.cjs')(c);for(const f of ['domain-chat.js','working-report.js','domain-development.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static',f),'utf8'),c);return {c,work,thread,calls,listeners,run:s=>vm.runInContext(s,c)};
}
test('all domains open with the AI partner and reveal implications only on request',async()=>{
 for(const domain of ['research','design']){const h=harness(domain);let html=h.run('domainChatScreen()');assert.match(html,/AI partner/);assert.match(html,/[Bb]uilding blocks/);assert.equal((html.match(/id="domain-chat-composer"/g)||[]).length,1);assert.doesNotMatch(html,/id="project-implications-panel"|id="domain-context-panel"|id="submission-document"/);
  await h.run("domainDevelopmentAction('dev-implications','')");html=h.run('domainChatScreen()');assert.match(html,/id="project-implications-panel"/);assert.match(html,new RegExp(domain==='research'?'Research objectives':'Design objectives'));
  await h.run("domainChatAction('dchat-panel-close','')");assert.doesNotMatch(h.run('domainChatScreen()'),/id="project-implications-panel"/);
 }
});
test('whole-document submission and evaluation are confined to Prepare to share',async()=>{
 const h=harness();await h.run("domainChatAction('dchat-sharing-panel','')");const html=h.run('domainChatScreen()');assert.match(html,/id="submission-document" maxlength="120000"/);assert.match(html,/Word document or FigJam PDF export/);assert.match(html,/Evaluate Outcomes report/);assert.match(html,/Preview publication/);assert.doesNotMatch(html,/id="project-implications-panel"/);assert.equal(h.calls.length,0);
});
test('source-backed implications and uncited hunches are distinct and escaped',()=>{
 const h=harness();h.c.state.domain_chat.implications=[{ref:{id:'IMP',revision:1},current:true,body:{conversation:'CHAT',status:'suggested',human_reviewed:false,at:'now',payload:{kind:'new-requirement',title:'<script>title</script>',statement:'A bounded need.',rationale:'Needs confirmation.',targets:[],evidence:[]}}}];const html=h.run('projectImplicationsPanel()');assert.match(html,/Hunch · no cited evidence/);assert.match(html,/Hold for submission/);assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>title/);
});
test('submission text remains isolated by domain project and account',()=>{
 const h=harness();h.run("submissionDraft().text='Private research';submissionDraft().dirty=true");h.c.state.project.id='other';assert.equal(h.run('submissionDraft().text'),'');h.c.state.project.id='P';assert.equal(h.run('submissionDraft().text'),'Private research');h.c.state.actor='lee';assert.equal(h.run('submissionDraft().text'),'');
});
test('private text saves through the deterministic submission command without model evaluation',async()=>{
 const h=harness();h.run("submissionDraft().text='The complete editable text.';submissionDraft().dirty=true");await h.run('saveSubmission()');assert.equal(h.calls.length,1);assert.equal(h.calls[0].action,'domain-submission-save');assert.equal(h.calls[0].data.text,'The complete editable text.');assert.equal(h.run('hasUnsavedSubmission()'),false);
});
test('partial PDF evaluation resumes only uncompleted parts of its existing cycle',async()=>{
 const h=harness(),sub={ref:{id:'SUB',revision:1},body:{text:'Fictional PDF content',source_refs:[],implication_refs:[],primary_source:null,review_mode:'text'}};
 h.c.state.domain_chat.submissions=[{conversation:'CHAT',submission:sub,plan:[{mode:'visual',pages:[1,2,3,4,5,6]},{mode:'visual',pages:[7,8]}],evaluations:[{ref:{id:'SEVAL',revision:1},current:true,body:{cycle:'saved-cycle',batch_index:0,parts_total:2,output:{objective_review:[],implications:[],limitations:[],summary:'Earlier part.'}}}]}];
 await h.run('evaluateSubmission()');assert.equal(h.calls.length,1);assert.equal(h.calls[0].action,'domain-submission-evaluate');assert.equal(h.calls[0].data.batch,1);assert.equal(h.calls[0].data.cycle,'saved-cycle');
});

test('objective coverage uses the latest current assessment and exposes its exact evidence',()=>{
 const h=harness();h.c.state.domain_chat.objectives=[{conversation:'CHAT',objectives:[{id:'OBJ',title:'Understand the task',question:'What interrupts it?'}]}];
 h.c.state.domain_chat.submissions=[{conversation:'CHAT',evaluations:[{current:true,body:{at:'2026-11-10',output:{objective_review:[{objective_id:'OBJ',assessment:'addressed',rationale:'Older assessment.',next_step:'',evidence:[]}]}}}]}];
 h.c.state.domain_chat.reports=[{ref:{id:'REVIEW',revision:1},current:true,body:{conversation:'CHAT',at:'2026-11-11',output:{objective_review:[{objective_id:'OBJ',assessment:'not-addressed',rationale:'New evidence shows a gap.',next_step:'Recruit a counterexample.',evidence:[{source:'SOURCE:v1',quote:'Observed interruption.',page:null}]}]}}}];
 const html=h.run('objectiveCoverage()');assert.match(html,/1 unanswered/);assert.match(html,/New evidence shows a gap/);assert.match(html,/Observed interruption/);assert.doesNotMatch(html,/Older assessment/);
});

test('implications show distinct criterion and challenge types with quiet evidence status',()=>{
 const h=harness(),row={ref:{id:'IMP',revision:1},current:true,body:{conversation:'CHAT',status:'suggested',payload:{kind:'new-criterion',title:'Confirm storage',statement:'Confirm only after storage.',rationale:'Avoid false confirmation.',targets:[],evidence:[]}}};
 h.c.state.domain_chat.implications=[row];const html=h.run('projectImplicationsPanel()');assert.match(html,/New acceptance criterion/);assert.match(html,/Needs evidence/);assert.match(html,/Challenge to requirement/);assert.match(html,/Review evidence/);assert.doesNotMatch(html,/Decision approved/);
});
test('evidence review is explicit, claim-bound and saves with an existing submission',async()=>{
 const h=harness();h.c.state.domain_chat.implications=[{ref:{id:'IMP',revision:2},current:true,evidence_state:{status:'limited',support:{assessment:'limited',basis:'Observed task.',scope:'One bounded episode.',corroboration:'Not corroborated.',counterevidence:'Alternative explanations remain.',gaps:['Additional observation.']}},body:{conversation:'CHAT',status:'held',payload:{kind:'new-requirement',title:'Resume',statement:'Allow resumption.',rationale:'Recovery matters.',targets:[],evidence:[]}}}];
 h.c.state.domain_chat.submissions=[{conversation:'CHAT',submission:{ref:{id:'SUB',revision:1},body:{text:'Submission',source_refs:[],implication_refs:[{id:'IMP',revision:2}],primary_source:null,review_mode:'text'}},evaluations:[],plan:[]}];
 let handler,markup;h.c.domainText=(n,t,v)=>`<label>${t}<textarea name="${n}" maxlength="20000">${v}</textarea></label>`;h.c.modal=(t,c,label,fn)=>{handler=fn;markup=c;};
 await h.run("domainDevelopmentAction('dev-implication-evidence','IMP')");assert.match(markup,/Corroboration or source authority/);assert.match(markup,/name="confirmed" required/);assert.match(markup,/maxlength="1500"/);assert.equal(h.calls.length,0);
 h.c.busy=true;const data={assessment:'limited',basis:'Observed task.',scope:'One bounded episode.',corroboration:'Not corroborated.',counterevidence:'Alternative explanations remain.',gaps:'Additional observation.',confirmed:'on'};
 await handler({get:k=>data[k]});assert.equal(h.calls[0].action,'domain-implication-save');assert.equal(h.calls[0].data.confirm_evidence,true);assert.equal(h.calls[0].data.expected.revision,2);assert.equal(h.calls[0].data.evidence_review.assessment,'limited');assert.equal(h.calls[1].action,'domain-submission-save');
});

test('tool imports sit beside document and discussion inputs while configuration stays in Settings',async()=>{
 const h=harness();h.c.state.domain_chat.import_tools=['figjam','figma','lucid'].map(provider=>({provider,label:provider==='figjam'?'FigJam':provider==='figma'?'Figma':'Lucid',status:'Authorization needed'}));
 await h.run("domainChatAction('dchat-sharing-panel','')");const html=h.run('domainChatScreen()');assert.match(html,/Connected tools/);assert.match(html,/Upload document/);assert.match(html,/Draft from discussion/);assert.doesNotMatch(html,/name="tool"/);
 const settings=h.run('toolImportSettings()');for(const label of ['FigJam','Figma','Lucid'])assert.match(settings,new RegExp(label));assert.match(settings,/Authorization needed/);
});
test('saved coach replies expose selection provenance without treating user messages as coach content',()=>{
 const h=harness(),html=h.run("chatTurn({ref:{id:'TURN-1',revision:1},body:{role:'assistant',message:'A bounded idea.'}})");assert.match(html,/data-chat-turn-id="TURN-1"/);assert.match(html,/from-coach/);
 const user=h.run("chatTurn({ref:{id:'TURN-2',revision:1},body:{role:'user',message:'A user message.'}})");assert.doesNotMatch(user,/from-coach/);
});

test('refining wording or linking a parent preserves existing goal and requirement references',()=>{
 const h=harness();h.c.row={body:{payload:{targets:['GOAL:v1','REQ:v2']}}};
 const unchanged=h.run("implicationPatch(row,{target:'',statement:'Clearer wording'})");assert.deepEqual(Array.from(unchanged.targets),['GOAL:v1','REQ:v2']);
 const added=h.run("implicationPatch(row,{target:'OTHER:v3'})");assert.deepEqual(Array.from(added.targets),['GOAL:v1','REQ:v2','OTHER:v3']);
});

test('Design uses the same chassis with discoverable brief and alternatives; Research has no irrelevant prototype controls',()=>{
 for(const domain of ['research','design']){const h=harness(domain);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-prototypes.js'),'utf8'),h.c);const html=h.run('chatWorkspaceActions()');assert.doesNotMatch(html,/data-action="pflow-briefs"/);assert.doesNotMatch(html,/>Working brief<|>Developer brief</);if(domain==='design')assert.match(html,/Prototype alternatives/);else assert.doesNotMatch(html,/Prototype alternatives/);assert.match(html,/[Bb]uilding blocks/);assert.match(html,/Outcomes report/);}
});
test('prototype receipt distinguishes staged from confirmed and offers no retry after an uncertain write',()=>{
 const h=harness('design');vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-prototypes.js'),'utf8'),h.c);h.c.row={ref:{id:'PLAN',revision:2},exports:[{ref:{id:'EXP',revision:1},body:{plan:{id:'PLAN',revision:2},url:'https://www.figma.com/design/TEST',status:'staged',at:'now'}}]};let html=h.run('prototypeExportStatus(row)');assert.match(html,/Staged · nothing sent/);assert.match(html,/Review &amp; create|Review & create/);h.c.row.exports[0].body.status='outcome-unknown';html=h.run('prototypeExportStatus(row)');assert.match(html,/inspect Figma before retrying/);assert.doesNotMatch(html,/data-action="proto-send"/);
});

test('prototype export history unfolds beneath the latest receipt without discarding earlier outcomes',()=>{
 const h=harness('design');vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-prototypes.js'),'utf8'),h.c);h.c.row={ref:{id:'PLAN',revision:2},exports:[{body:{plan:{id:'PLAN',revision:2},url:'https://www.figma.com/design/TEST',status:'sent',at:'now'}},{body:{plan:{id:'PLAN',revision:1},url:'https://www.figma.com/design/TEST',status:'staged',at:'before'}}]};const html=h.run('prototypeExportStatus(row)');assert.match(html,/<details><summary>Earlier export attempts \(1\)<\/summary>/);assert.ok(html.indexOf('Figma confirmed creation')<html.indexOf('<details>'));assert.match(html,/Staged · nothing sent/);
});


test('a reply with project assessments does not open a panel or replace the user’s chosen panel',async()=>{
 for(const domain of ['research','design']){
  const h=harness(domain);h.c.state.domain_chat.alignment=[{conversation:'CHAT',review:{id:'REV'}}];h.c.command=async()=>({chatReport:'REV'});
  h.run("chatDraft().text='Help me think through an approach'");await h.run('chatSend({preventDefault(){}})');assert.equal(h.run('domainPanel()'),null);
  await h.run("domainChatAction('dchat-context-panel','')");assert.equal(h.run('domainPanel()'),null);assert.equal(h.run("chatDisclosure('brief-inputs')"),'open');
  h.run("chatDraft().text='Explore another possibility'");await h.run('chatSend({preventDefault(){}})');assert.equal(h.run('domainPanel()'),null);assert.equal(h.run("chatDisclosure('brief-inputs')"),'open');
  await h.run("domainChatAction('dchat-panel-close','')");h.run("chatDraft().text='Review this work';chatDraft().purpose='review'");await h.run('chatSend({preventDefault(){}})');assert.equal(h.run('domainPanel()'),null);
 }
});
test('opening optional context does not submit a request and panel choices stay with their work',async()=>{
 const h=harness();await h.run("domainChatAction('dchat-context-panel','')");assert.equal(h.run('domainPanel()'),null);assert.equal(h.run("chatDisclosure('brief-inputs')"),'open');assert.equal(h.calls.length,0);
 h.c.state.project.id='OTHER';assert.equal(h.run('domainPanel()'),null);assert.equal(h.run("chatDisclosure('brief-inputs')"),'');h.c.state.project.id='P';assert.equal(h.run('domainPanel()'),null);assert.equal(h.run("chatDisclosure('brief-inputs')"),'open');
 h.c.state.auth={account:{id:'another-account'}};assert.equal(h.run('domainPanel()'),null);assert.equal(h.run("chatDisclosure('brief-inputs')"),'');
});


test('the editable domain brief stacks before the AI partner and keeps its disclosure separate from output panels',()=>{
 for(const domain of ['research','design']){const h=harness(domain);let html=h.run('domainChatScreen()');assert.ok(html.indexOf('id="domain-working-brief"')<html.indexOf('aria-label="Work with your AI partner"'));assert.match(html,/Received context:/);assert.doesNotMatch(h.run('chatWorkspaceActions()'),/data-action="dchat-context-panel"/);assert.match(html,/<details id="domain-working-brief"[^>]* open/);h.run("chatDraft().text='Unsent exploration'");for(const listener of h.listeners.toggle||[])listener({target:{isConnected:true,open:false,hasAttribute:()=>false,dataset:{chatDisclosure:'working-brief'}}});html=h.run('domainChatScreen()');assert.doesNotMatch(html,/<details id="domain-working-brief"[^>]* open/);   // the person's own choice stands once made
assert.equal(h.run('domainPanel()'),null);assert.equal(h.run('chatDraft().text'),'Unsent exploration');assert.equal(h.calls.length,0);}
});


test('incoming brief inputs open in the plan without replacing outgoing implications or unsent work',async()=>{
 for(const domain of ['research','design']){const h=harness(domain);h.run("domainPanels.set(chatKey(),'implications');chatDraft().text='Unsent work'");await h.run("domainChatAction('dchat-context-panel','')");const html=h.run('domainChatScreen()');assert.equal(h.run('domainPanel()'),'implications');assert.equal(h.run("chatDisclosure('brief-inputs')"),'open');assert.equal(h.run('chatDraft().text'),'Unsent work');assert.match(html,/id="project-implications-panel"/);assert.doesNotMatch(html,/id="domain-context-panel"|Close requirements and context/);assert.ok(html.indexOf('id="domain-brief-inputs"')<html.indexOf('aria-label="Work with your AI partner"'));assert.equal(h.calls.length,0);}
});
test('legacy context-panel state resolves into incoming brief inputs rather than a right-rail destination',()=>{
 const h=harness();h.run("domainPanels.set(chatKey(),'context')");const html=h.run('domainChatScreen()');assert.equal(h.run('domainPanel()'),null);assert.equal(h.run("chatDisclosure('brief-inputs')"),'open');assert.doesNotMatch(html,/id="domain-context-panel"/);
});

test('brief updates stay editable proposals until reviewed and explicitly saved',async()=>{
 const h=harness(),plan={ref:{id:'PLAN',revision:3},current:true};let save,markup;h.c.currentWorkingDomainPlan=()=>plan;
 h.c.modal=(title,html,label,fn)=>{save=fn;markup=html;};h.c.command=async(action,data)=>{h.calls.push({action,data});return {ref:{id:'PROPOSAL',revision:1},changes:[{target:'objective:0:question',label:'Objective',before:'Before',after:'Proposed',why:'Observable.',limit:400}]};};
 h.run("chatDraft().text='Make this objective observable'");await h.run("updateBriefFromDiscussion(null,'Make this objective observable')");
 assert.deepEqual(h.calls.map(c=>c.action),['domain-brief-refine-prepare']);assert.match(markup,/Proposed wording/);assert.match(markup,/maxlength="400"/);assert.equal(h.run('chatDraft().text'),'Make this objective observable');
 await save(new Map([['brief-change-0','Author refinement']]));assert.equal(h.calls[1].action,'domain-brief-refine-apply');assert.equal(h.calls[1].data.edits['objective:0:question'],'Author refinement');assert.equal(h.calls[1].data.confirm,true);assert.equal(h.run('chatDraft().text'),'');
 h.run("chatDraft().text='Keep my change'");h.c.command=async()=>{throw Error('Model unavailable')};await assert.rejects(h.run("updateBriefFromDiscussion(null,'Keep my change')"),/Model unavailable/);assert.equal(h.run('chatDraft().text'),'Keep my change');
});

test('assistant replies contain ordinary text without drawers, destination menus or embedded commands',()=>{const h=harness();const turn={ref:{id:'TURN',revision:1},body:{role:'assistant',message:'Brief recommendation: make the recovery objective observable.'}};const html=h.run('chatTurn('+JSON.stringify(turn)+')');assert.match(html,/Brief recommendation:/);assert.doesNotMatch(html,/<details|<summary|<button|chat-response-use|dev-use-response/);assert.equal(h.calls.length,0);});
test('selected-text actions are transient flat controls rather than another drawer',()=>{const source=fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-development.js'),'utf8');assert.match(source,/data-thought-selection="brief"/);assert.doesNotMatch(source,/thought-selection-use|thought-use-choices|function thoughtResponseActions/);});

test('work plan assessment names evidence and next steps without implying approval',()=>{
 const h=harness();h.c.review={body:{evaluated_plan:{sections:[{id:'S',title:'Task recovery'}]},output:{plan_review:[{section_id:'S',assessment:'partial',rationale:'Recovery is described; it has not been observed.',next_step:'Observe a realistic interrupted task.',evidence:[]}]}}};const html=h.run('submissionPlanCoverage(review)');
 assert.match(html,/Task recovery/);assert.match(html,/Partially supported/);assert.match(html,/Observe a realistic interrupted task/);assert.match(html,/No supporting source cited/);assert.doesNotMatch(html,/Approved|Ready to publish/);
});
test('each saved AI reply offers Save as building block through the same confirm-first capture, and never for your own messages',async()=>{
 const h=harness(),uses=[];h.c.openKnowledgeCapture=()=>{};h.c.knowledgeCards=()=>[{body:{status:'held'}}];h.c.useThoughtPassage=async(capture,action)=>uses.push({capture,action});
 h.c.state.domain_chat.turns=[{ref:{id:'T1',revision:1},body:{conversation:'CHAT',role:'user',message:'My question'}},{ref:{id:'T2',revision:1},body:{conversation:'CHAT',role:'assistant',message:'Look for counterexamples.'}}];
 const reply=h.run('chatTurn(state.domain_chat.turns[1])'),mine=h.run('chatTurn(state.domain_chat.turns[0])');
 assert.match(reply,/data-action="dchat-turn-block" data-id="T2:v1\|new">Save as building block</);assert.match(reply,/data-id="T2:v1\|add">Add to a block</);assert.match(reply,/Saved wording, not evidence/);assert.doesNotMatch(mine,/dchat-turn-block/);
 await h.run("domainChatAction('dchat-turn-block','T2:v1|new')");assert.equal(uses.length,1);assert.equal(uses[0].action,'card-new');assert.equal(uses[0].capture.text,'Look for counterexamples.');assert.deepEqual(JSON.parse(JSON.stringify(uses[0].capture.turn)),{id:'T2',revision:1});assert.equal(h.calls.length,0);
 h.c.state.domain_chat.turns[1].body.message='x'.repeat(4001);assert.doesNotMatch(h.run('chatTurn(state.domain_chat.turns[1])'),/dchat-turn-block/);
});

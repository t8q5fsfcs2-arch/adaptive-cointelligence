const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(actor='sam'){
 const key=actor==='sam'?'research':'design',source={ref:{id:'SRC-'+actor,revision:2},body:{title:'Fictional.txt',text:'Source observation only.'}},work={ref:{id:'D-'+actor,revision:3},kind:'contribution-draft',body:{owner:actor,chassis:1,title:'Fictional '+key,source_refs:[source.ref],requirement_refs:[{id:'REQ',revision:2}],input_refs:[]}},req={ref:{id:'REQ',revision:2},kind:'requirement',body:{title:'Preserve reporting',text:'Submit without a photo.',acceptance_criteria:'Show evidence pending.',rationale:'Avoid abandoned reporting.',status:'approved'}},thread={ref:{id:'CHAT-'+actor,revision:1},body:{owner:actor,draft_id:work.ref.id,focus_source:source.ref,pending:null},plan:[{mode:'text',start:0,end:24}]};
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const items=[work,req],listeners={};
 const ctx={view:'contributions',state:{actor,domains:{active:key},project:{id:'one',version:1},domain_chat:{threads:[thread],turns:[],reports:[]},design_visual:{reports:[]}},selected:null,busy:false,Map,Date,date:value=>value,crypto:{randomUUID:()=> 'synthetic-request'},document:{addEventListener:(event,fn)=>{const prior=listeners[event];listeners[event]=prior?e=>{prior(e);fn(e);}:fn;},getElementById:()=>null,querySelector:()=>null},records:kind=>items.filter(r=>r.kind===kind),get:id=>items.find(r=>r.ref.id===id),domainInfo:()=>({sources:[source],reports:[],model:{provider:'TEST DOUBLE'}}),domainProfile:()=>({key,config:{label:key,descriptor:key+' expertise'}}),domainInputOptions:()=>[],domainFieldLabels:{interpretation:'Interpretation'},label:r=>r.id+':v'+r.revision,esc,para:v=>`<p>${esc(v)}</p>`,val:(t,v)=>`<strong>${esc(t)}</strong><p>${esc(v)}</p>`,button:(t,a,id='',css='')=>`<button class="${css}" data-action="${a}" data-id="${id}">${t}</button>`,render:()=>{},toast:()=>{},load:async()=>{},command:async()=>({}),FormData:class {}};
 vm.createContext(ctx);require('./ui_reference_helpers.cjs')(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-chat.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/working-report.js'),'utf8'),ctx);return {ctx,work,source,req,thread,items,listeners,run:s=>vm.runInContext(s,ctx)};
}
test('Research and Design use the same workspace composer and reference components',()=>{
 for(const actor of ['sam','lee']){const h=harness(actor),html=h.run('domainChatScreen()');assert.match(html,/domain-chat-composer/);assert.match(html,/aria-label="Add a file"/);assert.match(html,/Received context: 1 requirement · 1 file/);assert.doesNotMatch(html,/>Project context</);assert.doesNotMatch(html,/>Reports<|Deliverable & sharing/);assert.match(html,/Ask your AI partner/);assert.doesNotMatch(html,/Create a requirement|New deliverable/);}
});
test('review scope links to requirements without repeating canonical wording or criteria',()=>{
 const h=harness(),html=h.run('chatReference()');assert.match(html,/<summary>Review scope · 1 requirement/);assert.match(html,/data-nav="requirements"/);assert.match(html,/name="requirement" value="REQ" checked/);assert.match(html,/not shared wording/);assert.doesNotMatch(html,/Show evidence pending|class="chat-requirement"|<h4>Acceptance criteria/);
});
test('private unsent composer state is separated by project generation role and work',()=>{
 const h=harness();h.run("chatDraft().text='Private Research question'");h.ctx.state.actor='lee';assert.equal(h.run('chatDraft().text'),'');h.ctx.state.actor='sam';h.ctx.state.project.version=2;assert.equal(h.run('chatDraft().text'),'');h.ctx.state.project.version=1;assert.equal(h.run('chatDraft().text'),'Private Research question');
});
test('model responses are escaped and evidence stays behind disclosure',()=>{
 const h=harness();h.ctx.state.domain_chat.turns=[{ref:{id:'T',revision:1},body:{conversation:h.thread.ref.id,role:'assistant',message:'<script>unsafe</script>'}}];const html=h.run('chatConversation()');assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);
});
test('existing visual reviews remain available without manufacturing a new result',()=>{
 const h=harness('lee');h.ctx.state.design_visual.reports=[{ref:{id:'VIS',revision:1},current:true,basis_records:[],body:{draft:h.work.ref,source:h.source.ref,pages:[{page:2}],output:{summary:'Actual earlier review',findings:[]}}}];assert.equal(h.run('chatReports()[0].ref.id'),'VIS');assert.equal(h.run('chatReports()[0].body.legacy'),true);
});
test('long passage coverage is explicit and citations carry source locations',()=>{
 const h=harness();h.ctx.state.domain_chat.reports=[{ref:{id:'REV',revision:1},current:true,body:{conversation:h.thread.ref.id,draft:h.work.ref,source:h.source.ref,format:'text',mode:'simulated',batch:{mode:'text',start:0,end:24},locations:[{page:2,source:h.source.ref,start:0}],output:{suggestions:[{issue:'A bounded concern',question:'What was observed?',quote:'Source observation',basis:h.source.ref.id,requirement_ids:['REQ'],edit:{field:'',text:''}}]}}}];const html=h.run('chatReportView()');assert.match(html,/1 of 1 text parts reviewed/);assert.match(html,/View page 2/);assert.match(html,/<summary>Evidence & requirement basis/);assert.match(html,/simulated/);
});

test('batch review can pause after a completed part without submitting the next',async()=>{
 const h=harness(),calls=[];h.thread.plan.push({mode:'text',start:24,end:48});h.run("chatDraft().text='Review this fictional work'");
 h.ctx.command=async(action,data)=>{calls.push({action,data});h.run('domainChatPause=true');return {chatReport:'REV'};};
 await h.run('chatSend({preventDefault(){}})');assert.equal(calls.length,1);assert.equal(calls[0].data.batch,0);assert.equal(calls[0].data.consent,true);assert.equal(h.ctx.busy,false);
});
test('role or project changes stop additional batches from using the wrong workspace',async()=>{
 const h=harness(),calls=[];h.thread.plan.push({mode:'text',start:24,end:48});h.run("chatDraft().text='Private Research question'");
 h.ctx.command=async(action,data)=>{calls.push({action,data});h.ctx.state.project.id='another-project';return {chatReport:'REV'};};
 await h.run('chatSend({preventDefault(){}})');assert.equal(calls.length,1);assert.equal(h.run('chatDraft().text'),'');
});

test('resume reviews only parts without a current result',async()=>{
 const h=harness(),calls=[];h.thread.plan.push({mode:'text',start:24,end:48});h.ctx.state.domain_chat.reports=[{current:true,body:{conversation:h.thread.ref.id,draft:h.work.ref,source:h.source.ref,batch:h.thread.plan[0]}}];h.run("chatDraft().text='Continue the review';domainChatOnlyRemaining=true");
 h.ctx.command=async(action,data)=>{calls.push({action,data});return {};};await h.run('chatSend({preventDefault(){}})');assert.equal(calls.length,1);assert.equal(calls[0].data.batch,1);
});
test('selecting a saved file updates the backend review focus',async()=>{
 const h=harness(),calls=[];h.ctx.command=async(action,data)=>{calls.push({action,data});return {};};await h.run("domainChatAction('dchat-source','SRC-sam')");assert.equal(calls[0].action,'domain-chat-focus');assert.equal(calls[0].data.source.id,'SRC-sam');
});

test('unsent text is isolated when the authenticated account changes',()=>{
 const h=harness();h.ctx.state.auth={account:{id:'first'}};h.run("chatDraft().text='Private unsent message'");h.ctx.state.auth.account.id='second';assert.equal(h.run('chatDraft().text'),'');
});

test('an explicitly unavailable model disables submission without saving uploading or changing a private draft',async()=>{
 const h=harness(),info=h.ctx.domainInfo(),calls=[];h.ctx.domainInfo=()=>({...info,model:{configured:false}});
 h.run("chatDraft().text='Keep this private draft';chatDraft().file={name:'Unsent.txt',size:25};chatDraft().purpose='review';chatDraft().briefDevelopment=true;domainChatOnlyRemaining=true");
 const before=h.run('JSON.stringify(chatDraft())');
 h.ctx.saveWorkingReport=async()=>calls.push('save');h.ctx.chatEnsure=async()=>calls.push('start');h.ctx.visualFileContentForChat=async()=>calls.push('upload');h.ctx.command=async()=>calls.push('command');
 const html=h.run('chatConversation()');assert.match(html,/<button type="submit" class="primary" disabled>Ask/);
 assert.doesNotMatch(html,/<textarea[^>]*disabled/);assert.match(html,/data-action="dchat-file" aria-label="Add a file" >/);assert.match(html,/data-action="dchat-review-work" >Ask for a review/);
 assert.match(html,/AI partner is unavailable. You can keep drafting./);
 await h.run('chatSend({preventDefault(){}})');assert.deepEqual(calls,[]);assert.equal(h.run('JSON.stringify(chatDraft())'),before);assert.equal(h.run('domainChatOnlyRemaining'),true);assert.equal(h.ctx.busy,false);
 h.ctx.domainInfo=()=>({...info,model:{configured:true}});assert.doesNotMatch(h.run('chatConversation()'),/<button type="submit" class="primary" disabled/);
 h.ctx.domainInfo=()=>({...info,model:{}});assert.doesNotMatch(h.run('chatConversation()'),/<button type="submit" class="primary" disabled/);
});

test('unavailable Retry preserves the current draft while prefilling and deterministic recovery remain available',async()=>{
 const h=harness(),info=h.ctx.domainInfo(),calls=[];h.ctx.domainInfo=()=>({...info,model:{configured:false}});
 h.ctx.state.domain_chat.turns=[{body:{conversation:h.thread.ref.id,role:'user',message:'Earlier request',request_id:'old'}},{body:{conversation:h.thread.ref.id,role:'error',message:'No model connection is assigned.',request_id:'old'}}];
 h.run("chatDraft().text='New private draft';chatDraft().file={name:'New.txt'};chatDraft().purpose='explore'");const before=h.run('JSON.stringify(chatDraft())');
 h.ctx.command=async(action)=>{calls.push(action);return {}};
 const html=h.run('chatConversation()');assert.match(html,/data-action="dchat-retry" data-id="old" disabled/);assert.match(html,/No model connection is assigned/);assert.doesNotMatch(html,/You can keep drafting/);
 await h.run("domainChatAction('dchat-retry','old')");assert.equal(h.run('JSON.stringify(chatDraft())'),before);assert.equal(h.run('domainChatOnlyRemaining'),false);assert.deepEqual(calls,[]);
 await h.run("domainChatAction('dchat-review-work','')");assert.equal(h.run('chatDraft().text'),'New private draft');assert.equal(h.run('chatDraft().file.name'),'New.txt');assert.deepEqual(calls,[]);
 h.thread.body.pending={at:'2026-11-01T12:00:00Z'};const pending=h.run('chatConversation()');assert.match(pending,/data-action="dchat-recover"/);assert.doesNotMatch(pending,/<button[^>]*data-action="dchat-recover"[^>]*disabled/);
 await h.run("domainChatAction('dchat-recover','')");assert.deepEqual(calls,['domain-chat-recover']);assert.equal(h.run('chatDraft().text'),'New private draft');
});

test('failed requests offer compact retry by the composer while past errors stay in Chats in this project',()=>{
 const h=harness(),failure={body:{conversation:h.thread.ref.id,role:'error',message:'Unverified reply',at:'2026-11-09T12:00:00Z',request_id:'failed-request'}};
 h.ctx.state.domain_chat.turns=[failure];let main=h.run('chatConversation()');assert.match(main,/class="chat-retry-notice"/);assert.match(main,/data-action="dchat-retry"/);assert.doesNotMatch(main,/Earlier review attempt|chat-message chat-error/);
 h.ctx.state.domain_chat.turns.push({body:{conversation:h.thread.ref.id,role:'assistant',message:'A verified reply',at:'2026-11-09T12:01:00Z'}});
 main=h.run('chatConversation()');assert.match(main,/A verified reply/);assert.doesNotMatch(main,/Unverified reply|dchat-retry/);
 const library=h.run('chatLibrary()');assert.match(library,/<summary>Review history \(1\)/);assert.match(library,/Unverified reply/);assert.doesNotMatch(library,/chat-attempt-history" open|dchat-retry/);
});

test('expanded findings stay open when their page preview is opened',()=>{
 const h=harness();h.run("domainChatDisclosures.set(chatKey()+'|finding:REV:0',true)");assert.equal(h.run("chatDisclosure('finding:REV:0')"),'open');h.ctx.state.actor='lee';assert.equal(h.run("chatDisclosure('finding:REV:0')"),'');
});

test('repeated failures retain all details in one collapsed history and only one current Retry',()=>{
 const h=harness(),early={body:{conversation:h.thread.ref.id,role:'error',message:'Earlier validation failed.',at:'2026-11-12T12:00:00Z',request_id:'early'}},latest={body:{conversation:h.thread.ref.id,role:'error',message:'Later request timed out.',at:'2026-11-12T12:01:00Z',request_id:'latest'}};h.ctx.state.domain_chat.turns=[early,latest];
 const main=h.run('chatConversation()');assert.match(main,/Later request timed out/);assert.doesNotMatch(main,/Earlier validation failed|Earlier review attempt/);assert.equal((main.match(/data-action="dchat-retry"/g)||[]).length,1);
 const library=h.run('chatLibrary()');assert.match(library,/<summary>Review history \(2\)/);assert.match(library,/Earlier validation failed/);assert.match(library,/Later request timed out/);assert.equal((library.match(/class="chat-attempt-history"/g)||[]).length,1);
 h.ctx.state.domain_chat.turns.push({body:{conversation:'OTHER',role:'error',message:'Other private error',at:'2026-11-12T12:02:00Z'}});assert.doesNotMatch(h.run('chatLibrary()'),/Other private error/);
 h.ctx.busy=true;assert.doesNotMatch(h.run('chatConversation()'),/data-action="dchat-retry"/);h.ctx.busy=false;h.thread.body.pending={at:'2026-11-12T12:03:00Z'};assert.doesNotMatch(h.run('chatConversation()'),/data-action="dchat-retry"/);
});


test('project chats and per-thread files live in the rail, outside the workbench toolbar',()=>{
 for(const actor of ['sam','lee']){
  const h=harness(actor),before=JSON.stringify(h.items),toolbar=h.run('chatWorkspaceActions()'),rail=h.run('domainChatNavigation()');
  assert.doesNotMatch(toolbar,/Chats in this project|work-files-menu/);assert.match(rail,/data-domain-chat-navigation open/);assert.match(rail,/aria-label="New project chat"/);assert.match(rail,/data-action="dchat-open"/);assert.match(rail,/data-chat-files=/);assert.match(rail,/Fictional.txt/);assert.equal(JSON.stringify(h.items),before);
 }
});
test('the rail excludes other owners, other domains and submission-only records',()=>{
 const h=harness();for(const body of [{owner:'lee',title:'Other private chat'},{owner:'sam',domain_key:'design',title:'Other domain chat'},{owner:'sam',submission_of:'D-sam',title:'Submission copy'}])h.items.push({...h.work,ref:{id:body.title,revision:1},body:{...h.work.body,...body}});
 const html=h.run('domainChatNavigation()');assert.doesNotMatch(html,/Other private chat|Other domain chat|Submission copy/);
 h.work.body.title='<script>untrusted title</script>';assert.match(h.run('domainChatNavigation()'),/&lt;script>/);
});
test('opening a rail thread saves the current editor and preserves each unsent message',async()=>{
 const h=harness(),next={...h.work,ref:{id:'D-next',revision:1},body:{...h.work.body,title:'Second work'}};h.items.push(next);const calls=[];h.ctx.saveBeforeProjectChange=async()=>calls.push('save');h.ctx.view='review';h.run("chatDraft().text='Unsent original question'");
 await h.run("domainChatAction('dchat-open','D-next')");assert.equal(h.ctx.view,'contributions');assert.equal(h.ctx.selected,'D-next');assert.deepEqual(calls,['save']);assert.equal(h.run('chatDraft().text'),'');h.run("chatDraft().text='Second unsent question'");
 await h.run("domainChatAction('dchat-open','D-sam')");assert.equal(h.run('chatDraft().text'),'Unsent original question');
 h.ctx.saveBeforeProjectChange=async()=>{throw Error('Save failed');};await assert.rejects(h.run("domainChatAction('dchat-open','D-next')"),/Save failed/);assert.equal(h.ctx.selected,'D-sam');
 await assert.rejects(h.run("domainChatAction('dchat-open','Unknown')"),/unavailable/);
});
test('a file in the rail opens its owning chat before focusing the existing backend source',async()=>{
 const h=harness(),calls=[];h.ctx.view='review';h.ctx.saveBeforeProjectChange=async()=>calls.push('save');h.ctx.command=async(action,data)=>{calls.push({action,data});return {};};
 await h.run("domainChatAction('dchat-nav-source','D-sam|SRC-sam')");assert.equal(h.ctx.view,'contributions');assert.equal(h.ctx.selected,'D-sam');assert.equal(calls[1].action,'domain-chat-focus');assert.equal(calls[1].data.conversation.id,'CHAT-sam');assert.equal(calls[1].data.source.id,'SRC-sam');assert.equal(h.run('domainChatPreview.source.id'),'SRC-sam');
 await assert.rejects(h.run("domainChatAction('dchat-nav-source','D-sam|Missing')"),/unavailable/);
});
test('rail expansion and remembered thread selection are isolated by project and identity',async()=>{
 const h=harness();h.run("domainChatNavOpen.set(chatSession(),false);domainChatSelection.set(chatSession(),'D-sam')");assert.doesNotMatch(h.run('domainChatNavigation()'),/data-domain-chat-navigation open/);h.ctx.state.project.id='second';assert.match(h.run('domainChatNavigation()'),/data-domain-chat-navigation open/);h.ctx.state.auth={account:{id:'another'}};assert.equal(h.run('domainChatNavOpen.has(chatSession())'),false);
});


test('New project chat is one compact plus beside the Chats and files disclosure',()=>{
 for(const actor of ['sam','lee']){
  const h=harness(actor),html=h.run('domainChatNavigation()'),library=h.run('chatLibrary()');assert.equal((html.match(/data-action="dchat-new"/g)||[]).length,1);assert.match(html,/<\/details><button[^>]*navigation-chat-add[^>]*data-action="dchat-new"[^>]*>＋<\/button>/);assert.doesNotMatch(library,/dchat-new|New chat/);assert.match(html,/aria-label="New project chat"/);
 }
});

test('brief coaching uses the existing composer without submitting or replacing a drafted message',async()=>{const h=harness();let focused=0,calls=0;h.ctx.command=async()=>{calls++};h.ctx.document.getElementById=()=>({value:'My unfinished question',focus(){focused++}});await h.run("domainChatAction('dchat-brief-coach','')");assert.equal(h.run('chatDraft().text'),'My unfinished question');assert.equal(calls,0);assert.equal(focused,1);});

test('ordinary discussion and content review have no permanent brief-update command in the composer',()=>{for(const actor of ['sam','lee']){const h=harness(actor),html=h.run('chatConversation()');assert.match(html,/>Ask</);assert.match(html,/>Ask for a review</);assert.doesNotMatch(html,/dchat-update-brief|>Update brief</);assert.equal((html.match(/id="domain-chat-composer"/g)||[]).length,1);}});

test('review recommendations remain readable as prose while full evidence lives in requested review details',()=>{const h=harness();h.ctx.state.domain_chat.reports=[{ref:{id:'REV',revision:1},current:true,body:{conversation:h.thread.ref.id,format:'visual',batch:{mode:'visual',pages:[2]},output:{findings:[{page:2,area:'Retry',recommendation:'Preserve entered text.',uncertainty:'Static screens do not establish storage.'}],limitations:'Human testing is still required.'}}}];const html=h.run('chatTurnRecommendations("REV")');assert.match(html,/Preserve entered text/);assert.match(html,/Static screens/);assert.match(html,/Human testing/);assert.match(html,/Page 2/);assert.doesNotMatch(html,/<details|<summary|<button|<select/);assert.match(h.run('chatAttemptHistory()'),/data-action="dchat-report"/);assert.equal(h.run('chatPriorRecommendations()'),'');});
test('opening a saved review is an explicit reader outside the response canvas and does not write',async()=>{const h=harness();let opened,commands=0;h.ctx.modal=(...args)=>opened=args;h.ctx.chatReportView=()=>'<p>Exact retained evidence.</p>';h.ctx.command=async()=>{commands++};await h.run("domainChatAction('dchat-report','REV')");assert.equal(opened[0],'Review details');assert.match(opened[1],/Exact retained evidence/);assert.equal(commands,0);});
test('the common dialogue boundary surrounds both the response transcript and the input composer',()=>{const h=harness(),html=h.run('chatConversation()');assert.ok(html.indexOf('class="chat-console"')<html.indexOf('id="chat-messages"'));assert.ok(html.indexOf('id="chat-messages"')<html.indexOf('id="domain-chat-composer"'));assert.match(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-chat.css'),'utf8'),/box-shadow:inset 0 2px 8px/);});

test('historical review coverage describes its saved pages instead of reporting zero reviewed pages',()=>{const h=harness();h.ctx.state.domain_chat.reports=[{ref:{id:'OLD',revision:1},current:false,body:{conversation:h.thread.ref.id,source:h.source.ref,draft:h.work.ref,format:'visual',mode:'simulated',batch:{mode:'visual',pages:[1,2]},output:{findings:[],limitations:'Earlier review.'}}}];const html=h.run('chatReportView("OLD")');assert.match(html,/Pages 1, 2 · Saved review/);assert.doesNotMatch(html,/0 of .*pages reviewed/);});

test('brief coaching uses the main chat and offers an update only for concrete plan advice',async()=>{
 const h=harness(),calls=[];h.run("chatDraft().text='Refine the plan';chatDraft().briefDevelopment=true");assert.match(h.run('chatConversation()'),/Leave brief development/);h.ctx.command=async(action,data)=>{calls.push({action,data});return {};};await h.run('chatSend({preventDefault(){}})');assert.equal(calls.length,1);assert.equal(calls[0].data.brief_development,true);assert.equal(h.run('chatDraft().briefDevelopment'),undefined);
 const report={ref:{id:'R',revision:1},body:{conversation:h.thread.ref.id,output:{brief_changes:[{target:'objective:0:question',value:'A suggestion',why:'A reason'}]}}};h.ctx.state.domain_chat.reports=[report];const turn={ref:{id:'T',revision:1},body:{role:'assistant',message:'Brief recommendation: try a counterexample.',report:report.ref}};h.ctx.turn=turn;assert.match(h.run('chatTurn(turn)'),/Review brief update/);report.body.output.brief_changes=[];assert.doesNotMatch(h.run('chatTurn(turn)'),/Review brief update/);
});

test('domain guidance describes selected saved context without inventing readiness or changing work',()=>{
 for(const actor of ['sam','lee']){
  const h=harness(actor),before=JSON.stringify(h.items);let calls=0;h.ctx.command=async()=>{calls++};
  const html=h.run('chatBriefStack()+chatWorkspaceActions()');assert.match(html,/1 requirement · 1 file/);assert.match(html,/Read what was handed over/);assert.match(html,/What was handed over/);
  assert.doesNotMatch(html,/approved|confirmed|\d+%|Submit without a photo|source observation/i);assert.equal(JSON.stringify(h.items),before);assert.equal(calls,0);
  h.work.body.requirement_refs=[];h.work.body.source_refs=[];h.thread.body.focus_source=null;
  assert.match(h.run('chatBriefStack()+chatWorkspaceActions()'),/No requirements, published inputs or files selected/);assert.match(h.run('chatBriefStack()+chatWorkspaceActions()'),/Read what was handed over/);
 }
});

test('guidance reuses the collapsed brief summary and existing toolbar without another panel above the composer',()=>{
 const h=harness(),html=h.run('domainChatScreen()');
 assert.doesNotMatch(html,/domain-task-guidance|<section[^>]*aria-label="Guidance for this work"/);
 assert.match(html,/data-chat-disclosure="working-brief" open><summary>/);   // no plan and no conversation yet: the handed-over context leadsassert.match(html,/caption domain-brief-guidance/);assert.match(html,/Received context: 1 requirement · 1 file/);
 const toolbar=html.slice(html.indexOf('aria-label="Workbench actions"'),html.indexOf('class="domain-chat-layout'));
 assert.equal((toolbar.match(/domain-guidance-next/g)||[]).length,1);assert.match(toolbar,/Next: Read what was handed over/);assert.equal((html.match(/id="domain-chat-composer"/g)||[]).length,1);
 h.req.ref.revision=3;assert.match(h.run('chatBriefStack()'),/domain-brief-guidance has-changed-inputs/);
 const css=fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-chat.css'),'utf8');assert.match(css,/domain-brief-guidance:not\(\.has-changed-inputs\) \.domain-brief-check/);
});

test('only changed inputs receive the visible warning signal while ordinary guidance stays inside the brief',()=>{
 const h=harness();let calls=0;h.ctx.command=async()=>{calls++};
 const before=JSON.stringify(h.items),current=h.run('chatBriefStack()'),currentSummary=current.split('</summary>')[0];
 assert.doesNotMatch(currentSummary,/domain-brief-check|domain-brief-warning-icon|has-changed-basis/);
 assert.match(current,/domain-brief-detail-guidance/);assert.match(current,/Check the selected context and evidence needed for this work/);
 h.ctx.state.domain_chat.alignment=[{conversation:h.thread.ref.id,target:h.req.ref,current:true,title:'Routing remains uncertain',gaps:['Unknown route needs clarification']}];
 const gap=h.run('chatBriefStack()+chatWorkspaceActions()');assert.match(gap.split('</summary>')[0],/Unknown route needs clarification/);
 assert.doesNotMatch(gap,/domain-brief-warning-icon|has-changed-basis|disabled|signal-critical/);
 h.req.ref.revision=3;const changed=h.run('chatBriefStack()+chatWorkspaceActions()'),summary=changed.split('</summary>')[0];
 assert.match(summary,/has-changed-basis/);assert.match(summary,/domain-brief-warning-icon" aria-hidden="true">!/);assert.match(summary,/Selected inputs changed/);
 assert.doesNotMatch(changed,/disabled|signal-critical/);assert.equal(calls,0);
 h.req.ref.revision=2;assert.equal(JSON.stringify(h.items),before);
});

test('guidance uses only current gaps belonging to this conversation and escapes their text',()=>{
 const h=harness();h.ctx.state.domain_chat.alignment=[
  {conversation:h.thread.ref.id,target:h.req.ref,current:false,title:'Old concern',gaps:['Historical gap']},
  {conversation:'OTHER',target:h.req.ref,current:true,title:'Other private concern',gaps:['Other private gap']},
  {conversation:h.thread.ref.id,target:h.req.ref,current:true,title:'Selected concern',gaps:['<script>Confirm the recovery evidence</script>']}
 ];
 const html=h.run('chatBriefStack()+chatWorkspaceActions()');assert.match(html,/&lt;script>Confirm the recovery evidence/);assert.match(html,/Inspect recorded gap/);assert.match(html,/Selected concern/);
 assert.doesNotMatch(html,/Historical gap|Other private gap|<script>/);
});

test('changed inputs take priority over saved gaps and never present earlier reviews as the next current review',()=>{
 const h=harness();h.req.ref.revision=3;h.ctx.state.domain_chat.alignment=[{conversation:h.thread.ref.id,target:h.req.ref,current:true,title:'Old question',gaps:['Earlier advice']}];
 let html=h.run('chatBriefStack()+chatWorkspaceActions()');assert.match(html,/Selected inputs changed/);assert.match(html,/Review changed inputs/);assert.doesNotMatch(html,/Earlier advice|Inspect recorded gap/);
 h.req.ref.revision=2;h.ctx.currentWorkingDomainPlan=()=>({current:false,body:{objectives:[]}});assert.match(h.run('chatBriefStack()+chatWorkspaceActions()'),/Review changed inputs/);
 h.ctx.currentWorkingDomainPlan=()=>null;h.ctx.state.domain_chat.alignment=[];
 h.ctx.state.domain_chat.reports=[{ref:{id:'OLD',revision:1},current:true,selection_current:false,body:{conversation:h.thread.ref.id}}];
 assert.doesNotMatch(h.run('chatBriefStack()+chatWorkspaceActions()'),/Inspect saved review/);
 h.ctx.state.domain_chat.reports[0].selection_current=true;html=h.run('chatBriefStack()+chatWorkspaceActions()');assert.match(html,/Inspect saved review/);assert.match(html,/data-action="dchat-report" data-id="OLD"/);
});

test('opening guidance context preserves the existing DOM, private draft and selected output panel without a command',async()=>{
 const h=harness(),brief={open:false,querySelector:()=>({focus(){brief.focused=true}}),scrollIntoView(){}},inputs={open:false};let calls=0,renders=0;
 h.ctx.document.getElementById=id=>id==='domain-working-brief'?brief:id==='domain-brief-inputs'?inputs:null;
 h.ctx.command=async()=>{calls++};h.ctx.render=()=>{renders++};h.run("chatDraft().text='Unsent private thought';chatDraft().file={name:'Unsent.txt'};domainPanels.set(chatKey(),'sharing')");
 await h.run("domainChatAction('dchat-guidance-context','')");
 assert.equal(brief.open,true);assert.equal(inputs.open,true);assert.equal(brief.focused,true);assert.equal(h.run('chatDraft().text'),'Unsent private thought');assert.equal(h.run('chatDraft().file.name'),'Unsent.txt');assert.equal(h.run('domainPanel()'),'sharing');assert.equal(calls,0);assert.equal(renders,0);
 assert.equal(h.run("chatDisclosure('working-brief')"),'open');assert.equal(h.run("chatDisclosure('brief-inputs')"),'open');
});

test('saved private plan questions guide work without a new plan object or approval step',()=>{
 const h=harness(),plan={current:true,body:{objectives:[{title:'Compare existing-tool alternatives'}],brief_sections:[{title:'Which operating condition is missing?',disposition:'question'}]}};
 h.ctx.currentWorkingDomainPlan=()=>plan;const before=JSON.stringify(plan),html=h.run('chatBriefStack()+chatWorkspaceActions()');assert.match(html,/Which operating condition is missing/);assert.match(html,/Review open plan question/);assert.doesNotMatch(html,/>[^<]*(?:approve|submit|confidence)[^<]*</i);assert.equal(JSON.stringify(plan),before);
 plan.body.brief_sections=[];h.thread.body.focus_source=null;assert.match(h.run('chatBriefStack()+chatWorkspaceActions()'),/Compare existing-tool alternatives/);assert.match(h.run('chatBriefStack()+chatWorkspaceActions()'),/Discuss next step/);
});

test('large chat history keeps five recent chats and an older selected chat visible while retaining every earlier action',()=>{
 const h=harness();for(let i=1;i<646;i++)h.items.push({...h.work,ref:{id:'D-'+i,revision:1},body:{...h.work.body,title:'Historical fictional chat '+i}});
 h.ctx.selected='D-645';h.run("chatDraft().text='Unsent work in the selected older chat'");let calls=0;h.ctx.command=async()=>{calls++};const before=JSON.stringify(h.items);
 let html=h.run('chatLibrary()'),[visible,earlier]=html.split('<details class="navigation-chat-earlier"');
 assert.equal((visible.match(/data-action="dchat-open"/g)||[]).length,6);assert.match(visible,/data-id="D-645" aria-current="page"/);assert.match(visible,/Historical fictional chat 645/);
 assert.match(earlier,/^ data-chat-earlier="[^"]+" ><summary>Earlier chats \(640\)<\/summary>/);
 assert.match(earlier,/data-action="dchat-open" data-id="D-400"/);assert.match(earlier,/data-action="dchat-nav-source" data-id="D-400\|SRC-sam"/);
 assert.equal((html.match(/data-action="dchat-open"/g)||[]).length,646);assert.equal((html.match(/aria-current="page"/g)||[]).length,1);
 h.listeners.toggle({target:{isConnected:true,dataset:{chatEarlier:h.run('chatSession()')},open:true}});
 html=h.run('chatLibrary()');assert.match(html,/navigation-chat-earlier" data-chat-earlier="[^"]+" open><summary>Earlier chats \(640\)/);assert.match(html,/Historical fictional chat 400/);
 assert.equal(h.ctx.selected,'D-645');assert.equal(h.run('chatDraft().text'),'Unsent work in the selected older chat');assert.equal(JSON.stringify(h.items),before);assert.equal(calls,0);
});

test('earlier chat disclosure persists across thread selection and is isolated by account project and domain',()=>{
 const h=harness();for(let i=1;i<8;i++)h.items.push({...h.work,ref:{id:'D-'+i,revision:1},body:{...h.work.body,title:'Fictional chat '+i}});
 const session=h.run('chatSession()');h.listeners.toggle({target:{isConnected:true,dataset:{chatEarlier:session},open:true}});
 const isOpen=()=>/navigation-chat-earlier" data-chat-earlier="[^"]+" open>/.test(h.run('chatLibrary()'));
 assert.equal(isOpen(),true);h.ctx.selected='D-7';assert.equal(isOpen(),true);
 h.ctx.state.project.id='other';assert.equal(isOpen(),false);h.ctx.state.project.id='one';assert.equal(isOpen(),true);
 h.ctx.state.auth={account:{id:'other-account'}};assert.equal(isOpen(),false);delete h.ctx.state.auth;assert.equal(isOpen(),true);
 h.ctx.state.domains.active='design';assert.equal(isOpen(),false);h.ctx.state.domains.active='research';assert.equal(isOpen(),true);
 h.listeners.toggle({target:{isConnected:false,dataset:{chatEarlier:session},open:false}});assert.equal(isOpen(),true);
 h.listeners.toggle({target:{isConnected:true,dataset:{chatEarlier:session},open:false}});assert.equal(isOpen(),false);
});
function commonAlignment(h,level='low'){
 const dimensions=Object.fromEntries(['logical-rigor','material-coverage','evidence-quality','applicability','independent-patterns','counterevidence'].map(key=>[key,{judgment:'limited',rationale:'The selected observation has bounded support.',passage_ids:key==='evidence-quality'?['EV1']:[],limits:'Other contexts remain untested.'}])),raw={framework:'evidence-reasoning-v1',standard:{id:'EVIDENCE-REASONING-STANDARD',revision:1},level,claim:'The observed interruption affects this task.',scope:'The bounded supplied task only.',rationale:'One observation cannot establish a general pattern.',limits:'Runtime and delivered outcomes remain untested.',patterns:{status:'single-line',families:[{key:'family-one',passage_ids:['EV1'],relationship:'unknown',rationale:'Only one underlying source is selected.'}],recurrence:'One observation is supplied.',exceptions:'Alternative explanations remain open.',population_limits:'No wider inference is established.'},dimensions};
 return {key:'REVIEW:v1|0',review:{id:'REVIEW',revision:1},index:0,conversation:h.thread.ref.id,target:h.req.ref,target_kind:'requirement',title:'Preserve reporting',criterion:'Show evidence pending.',assessment:'gap',rationale:'The stated gap needs verification.',evidence:[{source:'SRC-sam:v2',quote:'Source observation only.',page:null}],confidence_values:raw,confidence:{...raw,dimensions:Object.fromEntries(Object.entries(dimensions).map(([key,value])=>[key,{...value,citations:key==='evidence-quality'?[{source:'SRC-sam:v2',quote:'Source observation only.',page:null}]:[]}]))},assessor_type:'model',gaps:['Test the interruption in context.'],current:true,confirmed:false,human:null,edit_ref:null,batch:{mode:'text',start:0,end:24},at:'2026-11-21T15:00:00Z'};
}
test('new domain assessments display scoped ordinal confidence and all six reasoning dimensions without numerical scoring',()=>{
 const h=harness(),row=commonAlignment(h);h.ctx.state.domain_chat.alignment=[row];const before=JSON.stringify(row),html=h.run('chatAlignmentPanel()');
 for(const text of ['Confidence: Low · Model proposal','Pattern basis','Evidence family 1','Population limits','Logical rigor','Material coverage','Evidence quality','Applicability','Independent patterns','Counterevidence','Claim being assessed','The bounded supplied task only.','Supporting passages'])assert.ok(html.includes(text),text);
 assert.doesNotMatch(html,/\/100|participant_count|Equal-weight|value="appears-met" selected/);assert.match(html,/value="low" selected/);assert.match(html,/EVIDENCE-REASONING-STANDARD:v1/);assert.equal(JSON.stringify(row),before);row.mode='simulated';assert.match(h.run('chatAlignmentPanel()'),/Confidence: Low · Scripted example/);
 const ungraded=commonAlignment(h,'not-rated');h.ctx.state.domain_chat.alignment=[ungraded];const raw=h.run('chatAlignmentPanel()');assert.match(raw,/Confidence: Not rated/);assert.match(raw,/value="not-rated" selected/);assert.doesNotMatch(raw,/value="low" selected/);
});
test('legacy domain confidence stays explicitly historical and is never mapped to current ordinal labels',()=>{
 const h=harness(),row=commonAlignment(h);row.confidence_values={grounding:2,corroboration:0,coverage:1,applicability:1,participant_count:1};row.confidence={framework:'evidence-v1',score:33,basis:'Original uncalibrated heuristic',participant_count:1};h.ctx.state.domain_chat.alignment=[row];const before=JSON.stringify(row),html=h.run('chatAlignmentPanel()');
 assert.match(html,/Legacy evidence-v1 · 33\/100 · Historical rubric/);assert.match(html,/has not been converted to the current confidence framework/);assert.doesNotMatch(html,/Confidence: (?:Low|Moderate|High)|name="grounding"|name="participant_count"|name="confidence_level"/);assert.equal(JSON.stringify(row),before);
});
test('human ordinal refinements preserve exact claim scope standard and passage lineage without averaging or changing evidence',()=>{
 const h=harness(),row=commonAlignment(h);h.ctx.state.domain_chat.alignment=[row];const values=new Map([['assessment','gap'],['note','Keep the remaining gap explicit.'],['confirmed','on'],['confidence_level','not-rated'],['confidence_claim','A scoped interpretation of the interruption.'],['confidence_scope','One bounded task observation.'],['confidence_rationale','More evidence is needed before a defensible rating.'],['confidence_limits','Other users and contexts remain unobserved.']]);for(const key of Object.keys(row.confidence_values.dimensions)){values.set('confidence_'+key,'limited');values.set('confidence_'+key+'_rationale','This aspect remains bounded by the selected evidence.');values.set('confidence_'+key+'_limits','Independent verification is still needed.');}
 values.set('confidence_pattern_status','single-line');values.set('confidence_pattern_recurrence','One bounded observation is supplied.');values.set('confidence_pattern_exceptions','Alternative explanations remain open.');values.set('confidence_pattern_population_limits','No wider population inference.');values.set('confidence_family_0_relationship','unknown');values.set('confidence_family_0_rationale','The source relationship remains unverified.');
 h.ctx.FormData=class{constructor(form){this.values=form.values;}get(key){return this.values.get(key)||null;}};h.ctx.form={dataset:{alignmentEditor:row.key},values};const before=JSON.stringify(row),out=h.run('alignmentFormValues(form)');assert.equal(out.confidence.level,'not-rated');assert.equal(out.confidence.scope,'One bounded task observation.');assert.equal(out.confidence.framework,'evidence-reasoning-v1');assert.equal(out.confidence.standard.id,'EVIDENCE-REASONING-STANDARD');assert.equal(out.confidence.dimensions['evidence-quality'].passage_ids[0],'EV1');assert.equal(out.confidence.dimensions['evidence-quality'].judgment,'limited');assert.equal(out.confidence.patterns.families[0].passage_ids[0],'EV1');assert.equal(out.confidence.patterns.families[0].relationship,'unknown');assert.equal(out.confidence.score,undefined);assert.equal(out.confirmed,true);assert.equal(JSON.stringify(row),before);
});


test('the domain composer remains editable while pending but serializes Ask',async()=>{
 const h=harness();h.ctx.busy=true;let html=h.run('chatConversation()');assert.match(html,/<label class="reviewer-composer-label"[^>]*>You<\/label>/);assert.match(html,/<textarea[^>]*rows="4"/);assert.doesNotMatch(html,/<textarea[^>]*disabled/);assert.match(html,/<button type="submit" class="primary" disabled>Ask/);
 h.ctx.busy=false;h.thread.body.pending={at:new Date().toISOString()};h.run("chatDraft().text='Next question'");const calls=[];h.ctx.command=async action=>calls.push(action);html=h.run('chatConversation()');assert.doesNotMatch(html,/<textarea[^>]*disabled/);assert.match(html,/<button type="submit" class="primary" disabled>Ask/);await h.run('chatSend({preventDefault(){}})');assert.deepEqual(calls,[]);assert.equal(h.run('chatDraft().text'),'Next question');
});

test('a next domain question survives successful and failed in-flight completion',async()=>{
 for(const failure of [false,true]){
  const h=harness();let release,fail,started;const ready=new Promise(resolve=>started=resolve),response=new Promise((resolve,reject)=>{release=resolve;fail=reject;});h.run("chatDraft().text='Original question';chatDraft().briefDevelopment=true");h.ctx.command=async(action,data)=>{assert.equal(action,'domain-chat-send');assert.equal(data.message,'Original question');started();return response;};
  const pending=h.run('chatSend({preventDefault(){}})');await ready;h.listeners.input({target:{id:'domain-chat-message',value:'Next private question'}});h.run("chatDraft().purpose='review';chatDraft().briefDevelopment=true");
  if(failure)fail(Error('Synthetic failure'));else release({});await pending;assert.equal(h.run('chatDraft().text'),'Next private question');assert.equal(h.run('chatDraft().purpose'),'review');assert.equal(h.run('chatDraft().briefDevelopment'),true);assert.equal(h.run('domainChatSending'),null);
 }
});

test('draft preparation serializes sends and cannot clear a question typed while saving',async()=>{
 const h=harness(),calls=[];let release,started;const ready=new Promise(resolve=>started=resolve),saved=new Promise(resolve=>release=resolve);h.ctx.saveWorkingReport=()=>{started();return saved;};h.ctx.command=async(action,data)=>{calls.push({action,data});return {};};h.run("chatDraft().text='First question'");const pending=h.run('chatSend({preventDefault(){}})');await ready;
 h.listeners.input({target:{id:'domain-chat-message',value:'Second question'}});await h.run('chatSend({preventDefault(){}})');assert.equal(calls.length,0);release();await pending;assert.equal(calls.length,1);assert.equal(calls[0].data.message,'First question');assert.equal(h.run('chatDraft().text'),'Second question');
});

test('switching chats during a response preserves the new private draft and stops later batches',async()=>{
 const h=harness(),next={...h.work,ref:{id:'D-next',revision:1},body:{...h.work.body,title:'Next private chat'}},calls=[];h.items.push(next);h.thread.plan.push({mode:'text',start:24,end:48});let release,started;const ready=new Promise(resolve=>started=resolve);h.ctx.command=async(action,data)=>{calls.push({action,data});started();return new Promise(resolve=>release=resolve);};h.run("chatDraft().text='Review the original work';chatDraft().purpose='review'");const pending=h.run('chatSend({preventDefault(){}})');await ready;
 h.ctx.selected='D-next';h.listeners.input({target:{id:'domain-chat-message',value:'Keep this new chat private'}});release({});await pending;assert.equal(calls.length,1);assert.equal(h.ctx.selected,'D-next');assert.equal(h.run('chatDraft().text'),'Keep this new chat private');
});

test('changed selected evidence stops later batches without refreshing the frozen scope',async()=>{
 const h=harness(),calls=[],notices=[];h.thread.plan.push({mode:'text',start:24,end:48});h.run("chatDraft().text='Review this work';chatDraft().purpose='review'");h.ctx.toast=text=>notices.push(text);h.ctx.command=async(action,data)=>{calls.push({action,data});h.thread.body.focus_source={...h.source.ref,revision:99};return {};};const basis=JSON.stringify(h.work.body.requirement_refs);await h.run('chatSend({preventDefault(){}})');assert.equal(calls.length,1);assert.equal(calls[0].action,'domain-chat-send');assert.equal(JSON.stringify(h.work.body.requirement_refs),basis);assert.ok(notices.some(text=>text.includes('Review inputs changed')));
});

test('async chat creation cannot move a private draft into a changed role',async()=>{
 const h=harness();h.ctx.state.domain_chat.threads=[];h.run("chatDraft().text='Private Research draft'");let release,loads=0;h.ctx.command=()=>new Promise(resolve=>release=resolve);h.ctx.load=async()=>loads++;const pending=h.run('chatEnsure()');h.ctx.state.actor='lee';h.ctx.state.domains.active='design';release({id:'CREATED'});await assert.rejects(pending,/workspace changed/);assert.equal(loads,0);assert.equal(h.run('chatDraft().text'),'');h.ctx.state.actor='sam';h.ctx.state.domains.active='research';assert.equal(h.run('chatDraft().text'),'Private Research draft');
});

test('a role switch while reading an attached file prevents transmission to the new workspace',async()=>{
 const h=harness(),calls=[];let release,started;const ready=new Promise(resolve=>started=resolve);h.ctx.visualFileContentForChat=()=>{started();return new Promise(resolve=>release=resolve);};h.ctx.command=async action=>calls.push(action);h.run("chatDraft().text='Review this file';chatDraft().file={name:'Private.txt',size:20}");const pending=h.run('chatSend({preventDefault(){}})');await ready;h.ctx.state.actor='lee';h.ctx.state.domains.active='design';release('PRIVATE');await pending;assert.deepEqual(calls,[]);assert.equal(h.run('chatDraft().text'),'');assert.equal(h.run('chatDraft().file'),null);h.ctx.state.actor='sam';h.ctx.state.domains.active='research';assert.equal(h.run('chatDraft().file.name'),'Private.txt');
});

test('domain completion rerenders preserve composer focus and caret only within the same chat',()=>{
 const h=harness(),events=[];let current={selectionStart:3,selectionEnd:8};h.ctx.document.activeElement=current;h.ctx.document.getElementById=id=>id==='domain-chat-message'?current:null;h.ctx.render=()=>{current={focus:options=>events.push(options),setSelectionRange:(a,b)=>events.push([a,b])};};h.run('renderDomainChat()');assert.equal(events[0].preventScroll,true);assert.deepEqual(events[1],[3,8]);
 events.length=0;h.ctx.document.activeElement=current;current.selectionStart=1;current.selectionEnd=1;h.ctx.render=()=>{h.ctx.selected='different';h.ctx.state.project.version=9;current={focus:()=>events.push('wrong chat focus')};};h.run('renderDomainChat()');assert.deepEqual(events,[]);
});

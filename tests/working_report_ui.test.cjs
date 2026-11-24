const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(){
 const work={ref:{id:'D',revision:1},kind:'contribution-draft',body:{owner:'sam',domain_key:'research',chassis:1,title:'Fictional work',source_refs:[],requirement_refs:[],input_refs:[]}},thread={ref:{id:'CHAT',revision:1},body:{draft_id:'D'},plan:[]},calls=[],timers=[],listeners={},nodes={};let renders=0;
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const c={state:{actor:'sam',project:{id:'P',version:1},domains:{active:'research',sources:[],reports:[],handoffs:[],deliverables:{}},domain_chat:{threads:[thread],turns:[],reports:[],working_history:[]}},selected:'D',view:'contributions',bridgeSection:'boards',dirty:false,busy:false,Map,Date,crypto:{randomUUID:()=>"synthetic-request"},setTimeout:fn=>{timers.push(fn);return timers.length},clearTimeout:id=>{timers[id-1]=null},document:{addEventListener:(name,fn)=>(listeners[name]??=[]).push(fn),getElementById:id=>nodes[id]||null,querySelector:()=>null},domainInfo:()=>c.state.domains,domainProfile:()=>({key:'research',config:{label:'Research',descriptor:'Research expertise'}}),domainInputOptions:()=>[],domainFieldLabels:{},records:kind=>kind==='contribution-draft'?[work]:[],get:id=>id==='D'?work:null,label:r=>r?.id+':v'+r?.revision,esc,para:v=>`<p>${esc(v)}</p>`,val:(t,v)=>`<strong>${esc(t)}</strong><p>${esc(v)}</p>`,date:v=>v||'',button:(t,a,id='',css='')=>`<button data-action="${a}" data-id="${id}" class="${css}">${t}</button>`,render:()=>renders++,toast:()=>{},load:async()=>{},command:async(action,data)=>{calls.push({action,data});if(action==='domain-findings-save'){work.ref={id:'D',revision:work.ref.revision+1};work.body.working_report={format:'document',entries:data.document?[{id:'DOC',heading:'Findings',text:data.document}]:[]};}return {ref:{...work.ref}};}};
 vm.createContext(c);require('./ui_reference_helpers.cjs')(c);for(const name of ['domain-chat.js','working-report.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static',name),'utf8'),c);
 return {c,work,thread,calls,timers,nodes,listeners,renders:()=>renders,run:s=>vm.runInContext(s,c)};
}
test('AI partner is the default surface with no compulsory document or parallel composer',()=>{
 const h=harness(),html=h.run('domainChatScreen()');assert.equal((html.match(/id="domain-chat-composer"/g)||[]).length,1);assert.doesNotMatch(html,/id="findings-document"|id="domain-sharing-panel"|>Conversation<|Your deliverable/);assert.match(html,/>AI partner</);assert.match(html,/data-action="dchat-sharing-panel"/);assert.match(html,/data-chat-disclosure="brief-inputs"/);
});
test('context and sharing unfold separately in the same shared surface for any configured domain',async()=>{
 const h=harness();h.c.state.domains.active='custom-domain';h.c.domainProfile=()=>({key:'custom-domain',config:{label:'Custom domain',descriptor:'Local vocabulary and standards'}});
 await h.run("domainChatAction('dchat-context-panel','')");let html=h.run('domainChatScreen()');assert.match(html,/Custom domain workbench/);assert.match(html,/id="domain-brief-inputs"/);assert.doesNotMatch(html,/id="domain-context-panel"/);assert.equal(h.run("chatDisclosure('brief-inputs')"),'open');assert.match(html,/Domain interpretation/);assert.doesNotMatch(html,/id="findings-document"/);
 await h.run("domainChatAction('dchat-sharing-panel','')");html=h.run('domainChatScreen()');assert.match(html,/Edit Outcomes report/);assert.doesNotMatch(html,/id="domain-context-panel"/);await h.run("domainChatAction('dchat-panel-close','')");assert.doesNotMatch(h.run('domainChatScreen()'),/id="findings-document"/);assert.equal(h.calls.length,0);
});
test('earlier structured findings immediately populate the editable document without changing saved data',()=>{
 const h=harness();h.work.body.observation='An earlier observation';h.work.body.interpretation='An earlier interpretation';const before=JSON.stringify(h.work),html=h.run('workingReportEditor()');assert.match(html,/An earlier observation/);assert.match(html,/An earlier interpretation/);assert.doesNotMatch(html,/>Edit findings<\/button>|Add finding<|Section actions/);assert.equal(JSON.stringify(h.work),before);assert.equal(h.calls.length,0);
});
test('empty scaffolding and deliberately removed findings are not repopulated',()=>{
 const h=harness();h.work.body.observation='Working material; conclusions have not yet been authored.';assert.equal(h.run('findingsText()'),'');h.work.body.observation='A real earlier observation';h.work.body.working_report={entries:[]};assert.equal(h.run('findingsText()'),'');assert.match(h.run('workingReportEditor()'),/data-action="wreport-share" disabled/);
});
test('legacy sections and a modern document reopen with their saved wording',()=>{
 const h=harness();h.work.body.working_report={entries:[{heading:'A',text:'First'},{heading:'B',text:'Second'}]};assert.equal(h.run('findingsText()'),'A\nFirst\n\nB\nSecond');h.work.body.working_report={format:'document',entries:[{heading:'Findings',text:'One coherent document'}]};assert.equal(h.run('findingsText()'),'One coherent document');
});
test('findings edits save through one deterministic document command without rerendering or a model call',async()=>{
 const h=harness();h.run("reportDraft().document='An editable finding';reportDraft().dirty=true");await h.run('saveWorkingReport()');assert.deepEqual(h.calls.map(x=>x.action),['domain-findings-save']);assert.equal(h.calls[0].data.document,'An editable finding');assert.equal(h.run('hasUnsavedWorkingReport()'),false);assert.equal(h.renders(),0);
});
test('typing while saving retains new text and advances the expected revision for the next save',async()=>{
 const h=harness();h.run("reportDraft().document='First edit';reportDraft().dirty=true");h.c.command=async(action,data)=>{h.calls.push({action,data});h.work.ref={id:'D',revision:2};h.work.body.working_report={format:'document',entries:[{text:data.document}]};h.run("reportDraft().document='New typing'");return {ref:h.work.ref};};await assert.rejects(h.run('saveWorkingReport()'),/New text arrived/);assert.equal(h.run('reportDraft().document'),'New typing');assert.equal(h.run('reportDraft().expected.revision'),2);assert.equal(h.run('hasUnsavedWorkingReport()'),true);assert.equal(h.renders(),0);
});
test('autosave is debounced and a background save does not steal editing focus',async()=>{
 const h=harness();h.run("reportDraft().document='Draft one';reportEdited();reportDraft().document='Draft two';reportEdited()");assert.equal(h.timers.filter(Boolean).length,1);await h.timers.filter(Boolean)[0]();await new Promise(resolve=>setImmediate(resolve));assert.equal(h.calls.length,1);assert.equal(h.calls[0].data.document,'Draft two');assert.equal(h.renders(),0);
});
test('failed saves preserve text and expose retry instead of claiming Saved',async()=>{
 const h=harness();h.run("reportDraft().document='Keep me';reportDraft().dirty=true");h.c.command=async()=>{throw Error('Offline')};await assert.rejects(h.run('saveWorkingReport()'),/Offline/);assert.equal(h.run('reportDraft().document'),'Keep me');assert.match(h.run('workingReportEditor()'),/Not saved · Offline/);assert.match(h.run('workingReportEditor()'),/Retry save/);assert.equal(h.run('hasUnsavedWorkingReport()'),true);
});
test('unsaved documents remain isolated by project generation, account and domain',()=>{
 const h=harness();h.run("reportDraft().document='Private draft';reportDraft().dirty=true");h.c.state.project.id='Other';assert.equal(h.run('hasUnsavedWorkingReport()'),false);h.c.state.project.id='P';h.c.state.auth={account:{id:'Other'}};assert.equal(h.run('hasUnsavedWorkingReport()'),false);delete h.c.state.auth;assert.equal(h.run('reportDraft().document'),'Private draft');
});
test('navigation waits for an in-flight save and never drops the newer text',async()=>{
 const h=harness();h.run("reportDraft().document='Before leaving';reportDraft().dirty=true");let finish;h.c.command=async()=>new Promise(resolve=>finish=()=>resolve({ref:{id:'D',revision:2}}));const first=h.run('saveWorkingReport({background:true})');const second=h.run("saveWorkingReportBeforeAction('projects-home')");finish();await Promise.all([first,second]);assert.equal(h.run('hasUnsavedWorkingReport()'),false);
});
test('findings and citations are escaped, and evidence stays under one disclosure',()=>{
 const h=harness();h.work.body.working_report={format:'document',entries:[{heading:'Findings',text:'<script>bad</script>',citations:[{quote:'<img>',ref:{id:'S',revision:1}}]}]};const html=h.run('workingReportEditor()');assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>|<img>/);assert.match(html,/<summary>Sources & history/);assert.match(html,/&lt;img>/);
});
test('manual selections and a parallel draft wording editor are absent from the conversation',()=>{
 const h=harness();h.c.state.domain_chat.reports=[{ref:{id:'REV',revision:1},current:true,body:{conversation:'CHAT',draft:h.work.ref,format:'text',mode:'simulated',batch:{mode:'text',start:0,end:10},output:{suggestions:[{issue:'Check recovery',question:'Test interrupted recovery',basis:'observation',quote:'A quote',edit:{field:'interpretation',text:'Proposed interpretation'},requirement_ids:[]}]}}}];h.c.state.domain_chat.turns=[{body:{conversation:'CHAT',role:'assistant',message:'Examine interruption',report:{id:'REV',revision:1}}}];const html=h.run('chatConversation()');assert.match(html,/Test interrupted recovery/);assert.match(html,/Suggested wording: <span[^>]*>Proposed interpretation<\/span>/);assert.doesNotMatch(html,/<details class="chat-turn-recommendations"|chat-finding|chat-response-use/);assert.doesNotMatch(html,/Add to findings|Save wording to draft|chat-suggested-edit|domain-work-tabs/);
});
test('the Share action flushes edits then opens the exact prepared packet without publishing',async()=>{
 const h=harness();h.run("reportDraft().document='Saved findings';reportDraft().dirty=true");h.c.command=async(action,data)=>{h.calls.push({action,data});if(action==='domain-findings-save'){h.work.ref={id:'D',revision:2};return {ref:h.work.ref};}return {domainHandoff:'H'};};h.c.domainHandoff=id=>h.calls.push({opened:id});await h.run("workingReportAction('wreport-share','')");assert.deepEqual(h.calls.map(x=>x.action||'open'),['domain-findings-save','domain-findings-prepare','open']);assert.equal(h.calls[1].data.expected.revision,2);assert.equal(h.calls[2].opened,'H');
});
test('Undo is offered only for an exact current AI update and saves via the existing owned context',async()=>{
 const h=harness();h.work.body.working_report={format:'document',entries:[{text:'Draft'}],conversation_update:{before:{id:'D',revision:0},after:h.work.ref}};assert.match(h.run('findingsUndo()'),/Undo last update/);h.run("reportDraft().document='Human edit';reportDraft().dirty=true");assert.equal(h.run('findingsUndo()'),'');h.run('reportDraft().dirty=false');await h.run("workingReportAction('wreport-undo','')");assert.equal(h.calls[0].action,'domain-findings-undo');assert.equal(h.calls[0].data.expected.revision,1);
});
test('shared work editing returns to the same side-by-side workbench without starting a conversation',async()=>{
 const h=harness();h.c.state.domain_chat.threads=[];h.c.chatEnsure=async()=>{throw Error('Viewing must not create a thread')};await h.run("openWorkbenchReport('D')");assert.equal(h.c.view,'contributions');assert.equal(h.c.selected,'D');assert.equal(h.calls.length,0);h.work.body.owner='lee';await assert.rejects(h.run("openWorkbenchReport('D')"),/own workbench/);
});
test('published findings links open the shared work, not an issue',async()=>{
 const h=harness();h.c.records=k=>k==='contribution'?[{ref:{id:'PUB'}}]:k==='contribution-draft'?[h.work]:[];await h.run("openSharedReport('PUB')");assert.equal(h.c.view,'review');assert.equal(h.c.bridgeSection,'work');assert.equal(h.run("reportIsFocused('PUB')"),true);assert.equal(h.calls.length,0);
});
test('earlier findings, published output and packet inspection stay available in Sources and history',()=>{
 const h=harness();h.c.state.domains.deliverables.D={published:{id:'PUB',revision:1}};h.c.state.domains.handoffs=[{body:{draft:h.work.ref,packet:{id:'PKT',revision:1}}}];h.c.state.domain_chat.working_history=[{ref:{id:'D',revision:0},section_count:2}];const html=h.run('findingsReferences()');assert.match(html,/working-report-history/);assert.match(html,/data-action="packet" data-id="PKT\|1"/);assert.match(html,/Published version/);
});

test('scope preserves requirement version metadata and routes original wording to the shared view',()=>{
 const h=harness(),q={kind:'requirement',ref:{id:'REQ',revision:2},body:{title:'Preserve the task',text:'Keep entered content.',acceptance_criteria:'1. Retain entered text.\n2. Show a retry path.'}};h.work.body.requirement_refs=[{id:'REQ',revision:1}];h.c.records=k=>k==='requirement'?[q]:k==='contribution-draft'?[h.work]:[];const html=h.run('chatReference()');assert.match(html,/REQ:v2/);assert.match(html,/Open Requirements/);assert.doesNotMatch(html,/Keep entered content\.|Retain entered text\.|<h4>Business Intent/);
});

test('a failed automatic save exposes the existing retry control without rerendering the editor',async()=>{
 const h=harness();h.nodes['findings-save-retry']={hidden:true};h.nodes['findings-extra-actions']={hidden:true};h.run("reportDraft().document='Retain this';reportDraft().dirty=true");h.c.command=async()=>{throw Error('Offline')};await assert.rejects(h.run('saveWorkingReport({background:true})'),/Offline/);assert.equal(h.nodes['findings-save-retry'].hidden,false);assert.equal(h.nodes['findings-extra-actions'].hidden,false);assert.equal(h.renders(),0);
});
test('Send retains the unsent message if its preceding findings save fails',async()=>{
 const h=harness();h.run("chatDraft().text='Review this carefully'");h.c.saveWorkingReport=async()=>{throw Error('Save not finished')};await h.run('chatSend({preventDefault(){}})');assert.equal(h.run('chatDraft().text'),'Review this carefully');assert.equal(h.calls.length,0);assert.equal(h.c.busy,false);
});

test('typing into an empty document enables Share without a rerender',()=>{
 const h=harness(),share={disabled:true};h.c.document.querySelector=s=>s==='[data-action="wreport-share"]'?share:null;h.run("reportDraft().document='An authored finding';reportEdited()");assert.equal(share.disabled,false);h.run("reportDraft().document='';reportEdited()");assert.equal(share.disabled,true);assert.equal(h.renders(),0);
});
test('Share review leads with Findings and retains exact packet and source-release guards under disclosure',async()=>{
 const h=harness();h.work.body.working_report={format:'document',entries:[{heading:'Findings',text:'The actual saved finding'}]};h.work.body.source_refs=[{id:'SRC',revision:1}];h.c.state.domains.profiles=[{key:'research',config:{label:'Research'}}];h.c.state.domains.sources=[{ref:{id:'SRC',revision:1},scope:'domain:research',body:{title:'Fictional source',text:'Exact source material'}}];h.c.state.domains.handoffs=[{ref:{id:'H',revision:1},current:true,body:{draft:h.work.ref,basis:[],handoff:{}}}];h.c.modal=(title,body,submit,callback)=>h.c.dialog={title,body,submit,callback};h.c.preparedPacketPanel=()=>'<p>EXACT PACKET</p>';
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domains.js'),'utf8'),h.c);h.c.contributionRequirementLinks=()=>'';h.c.domainSelectedInputs=()=>'';h.run("domainHandoff('H')");assert.equal(h.c.dialog.title,'Share with project');assert.equal(h.c.dialog.submit,'Share');assert.ok(h.c.dialog.body.indexOf('The actual saved finding')<h.c.dialog.body.indexOf('EXACT PACKET'));assert.match(h.c.dialog.body,/<summary>Sources & packet/);assert.match(h.c.dialog.body,/name="release_sources" required/);assert.match(h.c.dialog.body,/name="confirm" required/);assert.doesNotMatch(h.c.dialog.body,/Not specified|Preflight system checks|Edit deliverable|Your deliverable/);
 await h.c.dialog.callback(new Map([['confirm','on'],['release_sources','on']]));assert.equal(h.calls[0].action,'domain-publish');assert.equal(h.calls[0].data.preflight.id,'H');assert.equal(h.calls[0].data.expected.revision,1);assert.equal(h.calls[0].data.release_sources,true);
});

test('an unchanged shared version signals Shared and cannot be accidentally sent again',()=>{
 const h=harness();h.work.body.working_report={format:'document',entries:[{text:'A shared finding'}]};h.c.state.domains.deliverables.D={state:'published',preview_outdated:false,published:{id:'PUB',revision:1}};assert.equal(h.run('findingsSaveLabel()'),'Shared');assert.match(h.run('workingReportEditor()'),/data-action="wreport-share" disabled/);h.run("reportDraft().document='A revised finding';reportDraft().dirty=true");assert.equal(h.run('findingsAlreadyShared()'),false);assert.doesNotMatch(h.run('workingReportEditor()'),/data-action="wreport-share" disabled/);
});

test('Ask for a review offers an editable prompt without calling a model or changing findings',async()=>{
 const h=harness();await h.run("domainChatAction('dchat-review-work','')");assert.match(h.run('chatDraft().text'),/what challenges the current direction/);assert.equal(h.run('chatDraft().purpose'),'review');assert.equal(h.calls.length,0);
});
test('ordinary chat sends exploration purpose and does not start file-wide batch analysis',async()=>{
 const h=harness();h.thread.plan=[{mode:'text',start:0,end:24000},{mode:'text',start:24000,end:48000}];h.run("chatDraft().text='Help me think about the problem'");await h.run('chatSend({preventDefault(){}})');assert.equal(h.calls.length,1);assert.equal(h.calls[0].data.purpose,'explore');
});
test('preparing a sharing draft is explicit and retains an unsent message',async()=>{
 const h=harness();h.thread.plan=[{mode:'text',start:0,end:5}];h.run("chatDraft().text='Do not replace this question'");await h.run("domainChatAction('dchat-draft-sharing','')");assert.equal(h.run('chatDraft().text'),'Do not replace this question');assert.equal(h.calls.length,0);
 h.run("chatDraft().text=''");await h.run("domainChatAction('dchat-draft-sharing','')");assert.equal(h.calls.length,1);assert.equal(h.calls[0].data.purpose,'prepare-sharing');assert.match(h.calls[0].data.message,/draft only/);assert.equal(h.run('chatDraft().purpose'),'explore');
});
function alignmentRow(){return {key:'REV:v1|0',review:{id:'REV',revision:1},index:0,conversation:'CHAT',target:{id:'REQ',revision:1},target_kind:'requirement',title:'Capture usable feedback',criterion:'Allow initial reporting.',assessment:'gap',rationale:'One invented observation.',evidence:[{source:'SRC:v1',quote:'One fictional participant.',page:null}],confidence:{score:49,basis:'Initial product heuristic, not probability.',participant_count:1},confidence_values:{grounding:3,corroboration:1,coverage:1,applicability:3,participant_count:1},gaps:['Probe interrupted work in more interviews.'],current:true,confirmed:false,human:null,edit_ref:null,at:'2026-11-11T12:00:00Z',batch:{mode:'text',start:0,end:100}};}
test('alignment emerges only with actual assessments and retains historical legacy score, gaps and human review',()=>{
 const h=harness();assert.doesNotMatch(h.run('chatWorkspaceActions()'),/Alignment \(/);h.c.state.domain_chat.alignment=[alignmentRow()];const html=h.run('chatAlignmentPanel()');assert.match(html,/Legacy evidence-v1 · 49\/100 · Historical rubric/);assert.doesNotMatch(html,/49\/100 · Provisional|Confidence: (Low|Moderate|High)/);assert.match(html,/Needs your review/);assert.match(html,/One reported participant limits generalization/);assert.match(html,/Confirm this working assessment/);assert.match(html,/project approval is separate/);assert.match(h.run('chatWorkspaceActions()'),/Alignment <span class="workbench-count">1</);
});
test('alignment next steps prepare an editable coaching prompt and do not start another dialogue',async()=>{
 const h=harness();h.c.state.domain_chat.alignment=[alignmentRow()];await h.run("domainChatAction('dchat-alignment-gaps','REV:v1|0')");assert.match(h.run('chatDraft().text'),/discussion guide/);assert.match(h.run('chatDraft().text'),/Probe interrupted work/);assert.equal(h.calls.length,0);assert.equal(h.run('chatDraft().purpose'),'explore');
});
test('earlier basis cannot be confirmed in the alignment panel and history remains visible',()=>{
 const h=harness(),row=alignmentRow();row.current=false;h.c.state.domain_chat.alignment=[row,{...row,key:'REV0:v1|0',at:'2026-11-10T12:00:00Z'}];const html=h.run('chatAlignmentPanel()');assert.match(html,/Earlier basis/);assert.match(html,/Earlier assessments \(1\)/);assert.doesNotMatch(html,/data-alignment-editor=/);assert.match(html,/Review the current work before confirming/);
});

test('updated requirements open context and refresh only the existing selected requirement scope',async()=>{
 const h=harness();h.work.body.requirement_refs=[{id:'REQ',revision:1}];const req={ref:{id:'REQ',revision:2},kind:'requirement',body:{title:'Updated requirement',text:'Updated wording'}};h.c.get=id=>id==='REQ'?req:id==='D'?h.work:null;h.c.records=kind=>kind==='requirement'?[req]:kind==='contribution-draft'?[h.work]:[];
 await h.run("domainChatAction('dchat-review-work','')");assert.equal(h.run('domainPanel()'),null);assert.equal(h.run("chatDisclosure('brief-inputs')"),'open');assert.match(h.run('chatReference()'),/Use updated requirements/);assert.equal(h.calls.length,0);
 await h.run("domainChatAction('dchat-refresh-scope','')");assert.equal(h.calls[0].action,'domain-chat-context');assert.equal(h.calls[0].data.requirement_ids.join(','),'REQ');assert.equal(h.calls[0].data.input_refs.length,0);
});

test('report citation identity stays within the source disclosure without rewriting authored quotations',()=>{
 const h=harness(),entry={text:'The authored claim is retained.',citations:[{ref:{id:'SRC-INTERNAL',revision:2},quote:'Keep this authored citation: REQ-ORIGINAL.'}],requirement_refs:[{id:'REQ-EXACT',revision:3}]};h.c.sample=entry;const before=JSON.stringify(entry),html=h.run('reportCitations(sample)');
 assert.match(html,/^<details class="report-evidence"><summary>Sources & origin<\/summary>/);assert.match(html,/SRC-INTERNAL:v2/);assert.match(html,/REQ-EXACT:v3/);assert.match(html,/Keep this authored citation: REQ-ORIGINAL\./);assert.equal(JSON.stringify(entry),before);assert.equal(h.calls.length,0);
});

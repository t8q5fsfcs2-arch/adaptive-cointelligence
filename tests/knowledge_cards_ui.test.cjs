const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(domain='research'){
 const actor=domain==='research'?'sam':'lee',work={ref:{id:'D',revision:1},kind:'contribution-draft',body:{owner:actor,domain_key:domain,chassis:1,title:'Fictional work',source_refs:[],requirement_refs:[],input_refs:[]}},thread={ref:{id:'CHAT',revision:1},body:{draft_id:'D'},plan:[]},calls=[],listeners={};
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const c={state:{actor,project:{id:'P',version:1},domains:{active:domain,sources:[],reports:[],handoffs:[],deliverables:{}},domain_chat:{threads:[thread],turns:[],reports:[],working_history:[],implications:[],submissions:[],objectives:[]}},selected:'D',view:'contributions',busy:false,Map,Date,crypto:{randomUUID:()=> 'evaluation-cycle-test'},setTimeout:()=>1,clearTimeout:()=>{},document:{addEventListener:(n,f)=>(listeners[n]??=[]).push(f),getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[]},domainInfo:()=>c.state.domains,domainProfile:()=>({key:domain,config:{label:domain==='research'?'Research':'Design',descriptor:'Domain expertise'}}),domainInputOptions:()=>[],domainFieldLabels:{},records:k=>k==='contribution-draft'?[work]:[],get:id=>id==='D'?work:null,label:r=>r?.id+':v'+r?.revision,esc,para:v=>`<p>${esc(v)}</p>`,val:(t,v)=>`<h4>${esc(t)}</h4><p>${esc(v)}</p>`,date:v=>v||'',button:(t,a)=>`<button data-action="${a}">${t}</button>`,render:()=>{},toast:()=>{},load:async()=>{},command:async(action,data)=>{calls.push({action,data});return {ref:{id:'SUB',revision:1}};}};
 vm.createContext(c);require('./ui_reference_helpers.cjs')(c);for(const f of ['domain-chat.js','working-report.js','domain-development.js','knowledge-cards.js','integrity-gaps.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static',f),'utf8'),c);return {c,work,thread,calls,listeners,run:s=>vm.runInContext(s,c)};
}

function addCard(h,id='CARD-1',type='finding',title='Shift handoff',conversation='CHAT',status='held'){
 const row={ref:{id,revision:1},kind:'domain-implication',current:true,body:{owner:h.c.state.actor,domain:h.c.state.domains.active,conversation,status,card:{type,fields:{},relations:[]},payload:{kind:'open-question',title,statement:'A bounded working observation.',rationale:'Fictional example.',targets:[],evidence:[]}}};h.c.state.domain_chat.implications.push(row);return row;
}
test('domain names and optional sidecar reuse the same Research and Design chassis',async()=>{
 for(const domain of ['research','design']){const h=harness(domain);assert.doesNotMatch(h.run('domainChatScreen()'),/id="project-implications-panel"/);await h.run("domainDevelopmentAction('dev-implications','')");const html=h.run('domainChatScreen()');assert.match(html,new RegExp((domain==='research'?'Research':'Design')+' building blocks'));assert.equal((html.match(/id="domain-chat-composer"/g)||[]).length,1);assert.equal(h.calls.length,0);}
});
test('catalogue spans own chats and hides unchosen model suggestions by default',()=>{
 const h=harness();addCard(h,'CARD-1','finding','First finding');addCard(h,'CARD-2','user-flow','Another chat flow','OTHER');addCard(h,'CARD-3','challenge','Automatic suggestion','CHAT','suggested');let html=h.run('knowledgeCardList()');assert.match(html,/First finding/);assert.match(html,/Another chat flow/);assert.doesNotMatch(html,/Automatic suggestion/);h.run("knowledgeCardView().type='user-flow'");assert.doesNotMatch(h.run('knowledgeCardList()'),/First finding/);h.run("knowledgeCardView().type='';knowledgeCardView().search='OTHER NOT FOUND'");assert.match(h.run('knowledgeCardList()'),/No blocks match/);
});
test('new card is local until explicitly saved and can be discarded without backend writes',async()=>{
 const h=harness();await h.run('createKnowledgeCard()');assert.equal(h.calls.length,0);const html=h.run('knowledgeCardsPanel()');assert.match(html,/Not saved yet/);assert.match(html,/data-action="kc-discard"/);assert.doesNotMatch(html,/data-action="kc-select"/);await h.run("knowledgeCardAction('kc-discard','')");assert.equal(h.calls.length,0);assert.doesNotMatch(h.run('knowledgeCardsPanel()'),/id="knowledge-card-editor"/);
});
test('types include flows stories and prototype artifacts with optional structured context',()=>{
 const h=harness();for(const type of ['user-flow','user-story','artifact'])assert.ok(h.run('knowledgeCardInfo().types')[type]);const row=addCard(h,'CARD-1','artifact','Variant B');row.body.card.fields={artifact_type:'Prototype',version_label:'v2',review_status:'Not tested'};h.c.row=row;const list=h.run('knowledgeCardRow(row)');assert.match(list,/Artifact · Prototype/);assert.match(list,/Saved · v1/);assert.doesNotMatch(list.replace(/<[^>]*>/g,''),/CARD-1/);h.run("knowledgeCardView().open='CARD-1'");const html=h.run('knowledgeCardsPanel()');assert.match(html,/Version or variant/);assert.match(html,/Review or testing status/);assert.match(html,/Select for deliverable/);assert.match(html,/<details class="record-metadata"><summary>Source details<\/summary>[\s\S]*CARD-1:v1/);assert.doesNotMatch(html.replace(/<details class="record-metadata">[\s\S]*?<\/details>/g,'').replace(/<[^>]*>/g,''),/CARD-1/);assert.doesNotMatch(html,/Approved/);
});
test('cards preserve entered text, context and account isolation without exposing markup',()=>{
 const h=harness();h.c.row=addCard(h,'CARD-1','finding','<script>unsafe</script>');h.run("knowledgeCardView().open='CARD-1';knowledgeCardDraft(row).statement='Unsent refinement';knowledgeCardDraft(row).dirty=true");let html=h.run('knowledgeCardsPanel()');assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>unsafe/);assert.match(html,/Unsent refinement/);assert.equal(h.run('hasUnsavedKnowledgeCards()'),true);h.c.state.project.id='OTHER';assert.equal(h.run('hasUnsavedKnowledgeCards()'),false);h.c.state.project.id='P';assert.equal(h.run('hasUnsavedKnowledgeCards()'),true);h.c.state.auth={account:{id:'OTHER'}};assert.equal(h.run('hasUnsavedKnowledgeCards()'),false);
});
test('selection is explicit and uses the current card version without model or publish calls',async()=>{
 const h=harness();addCard(h);await h.run("knowledgeCardAction('kc-select','CARD-1')");assert.equal(h.calls.length,1);assert.equal(h.calls[0].action,'domain-submission-save');assert.equal(h.calls[0].data.implication_refs[0].id,'CARD-1');assert.equal(h.calls[0].data.implication_refs[0].revision,1);
});
test('packet reader uses exact in-packet relationships and evidence rather than latest context',()=>{
 const h=harness();h.c.card={ref:{id:'SHARED-CARD',revision:1},kind:'knowledge-card',body:{type:'finding',statement:'Older accepted contribution.',relations:[{relation:'informs',ref:{id:'REQ',revision:1},rationale:'Applies to this version.',conditions:'At shift change'}],evidence:[{ref:{id:'SRC',revision:1},quote:'Exact observed text',page:null}]}};h.c.packet={records:[{ref:{id:'REQ',revision:1},body:{title:'Historical requirement'}},{ref:{id:'SRC',revision:1},body:{title:'Historical source'}}]};const html=h.run('knowledgePacketContent(card,packet)');assert.match(html,/Historical requirement/);assert.match(html,/REQ:v1/);assert.match(html,/Exact observed text/);assert.match(html,/does not approve a requirement/);assert.match(html,/<details class="record-metadata"><summary>Source details<\/summary>[\s\S]*REQ:v1/);const ordinary=html.replace(/<details class="record-metadata">[\s\S]*?<\/details>/g,'').replace(/<[^>]*>/g,'');assert.match(ordinary,/Historical requirement · v1/);assert.doesNotMatch(ordinary,/REQ:v1|SRC:v1/);
});

test('link and evidence sections retain disclosure state while the editor updates',()=>{
 const h=harness();addCard(h);h.run("knowledgeCardView().open='CARD-1'");for(const listener of h.listeners.toggle||[])listener({target:{dataset:{knowledgeDisclosure:'links'},isConnected:true,open:true}});assert.match(h.run('knowledgeCardsPanel()'),/data-knowledge-disclosure="links" open/);h.run("knowledgeCardDraft(knowledgeCards()[0]).relations.push({relation:'informs',ref:null,rationale:'',conditions:''})");assert.match(h.run('knowledgeCardsPanel()'),/data-knowledge-disclosure="links" open/);h.c.state.project.id='OTHER';assert.equal(h.run("knowledgeCardDisclosure('links')"),'');
});

test('classification explains the selected type and links remain progressive rather than invented',()=>{
 const h=harness();addCard(h,'CARD-1','note');h.run("knowledgeCardView().open='CARD-1'");const html=h.run('knowledgeCardsPanel()');assert.match(html,/Choose a more specific type/);assert.match(html,/No links yet/);assert.match(html,/data-knowledge-disclosure="links"/);assert.doesNotMatch(html,/Automatically linked|Approved/);
});

test('relationship links open the exact referenced version rather than silently using latest',()=>{
 const h=harness();const r=addCard(h);h.c.row=r;h.c.state.domain_chat.knowledge_cards={types:h.run('knowledgeCardDefaults'),relations:{informs:'Informs'},catalogue:[{ref:r.ref,type:'finding',relations:[{relation:'informs',ref:{id:'REQ',revision:2},title:'Earlier requirement',rationale:'Bounded relationship',conditions:'',changed:true}],backlinks:[]}],targets:[]};const html=h.run('knowledgeCardRelated(row)');assert.match(html,/data-id="REQ:v2"/);assert.match(html,/>Earlier requirement · v2<\/a>/);assert.match(html,/updated/);assert.doesNotMatch(html.replace(/<[^>]*>/g,''),/REQ:v2/);
});

test('category tiles show saved counts, retain empty archetypes and filter without writes',async()=>{
 const h=harness();addCard(h);addCard(h,'CARD-2','finding');addCard(h,'CARD-3','finding','Unchosen suggestion','CHAT','suggested');let html=h.run('knowledgeCardTypeGrid()');assert.match(html,/aria-label="Finding, 2 saved blocks"/);assert.match(html,/aria-label="User flow, 0 saved blocks"/);assert.match(html,/<svg/);await h.run("knowledgeCardAction('kc-filter-type','finding')");assert.equal(h.run('knowledgeCardView().type'),'finding');assert.equal(h.calls.length,0);await h.run("knowledgeCardAction('kc-filter-type','user-flow')");assert.match(h.run('knowledgeCardList()'),/Use ＋ to add one/);await h.run('createKnowledgeCard()');assert.equal(h.run('knowledgeCardView().newCard.body.card.type'),'user-flow');assert.equal(h.calls.length,0);
});


test('a finding holds its implications while standalone implication cards stay accessible',()=>{
 const h=harness();assert.doesNotMatch(h.run('knowledgeCardTypeGrid()'),/data-id="implication"/);
 assert.equal(h.run("knowledgeCardTypeChoices().some(([key])=>key==='implication')"),false);
 const finding=addCard(h,'CARD-F','finding','Routing observation');finding.body.card.fields={implications:'Distinguish routed from accepted.'};h.c.finding=finding;
 assert.match(h.run('knowledgeCardEditor(finding)'),/Implications/);
 assert.match(h.run('knowledgeCardEditor(finding)'),/Distinguish routed from accepted/);
 const existing=addCard(h,'IMP-OLD','implication','Consequence retained');h.c.existing=existing;
 assert.match(h.run('knowledgeCardTypeGrid()'),/data-id="implication"/);
 assert.match(h.run('knowledgeCardList()'),/Consequence retained/);
 assert.match(h.run('knowledgeCardEditor(existing)'),/value="implication" selected/);
});

test('capture from a review previews a chosen finding section and writes only after Save card',async()=>{
 const h=harness('design'),row=addCard(h,'CARD-F','finding','Ownership finding');row.body.card.fields={implications:'Existing implication.',limits:'One screen.'};
 let dialog;h.c.modal=(title,html,submit,handler)=>{dialog={title,html,submit,handler};};h.c.document.getElementById=()=>({addEventListener(){}});
 h.run("chatDraft().text='Unsent exploration'");h.c.capture={key:h.run('chatKey()'),review:{id:'REVIEW',revision:1},path:['findings',0,'recommendation'],text:'Check the acceptance event.'};
 h.run('openKnowledgeCapture(capture,true)');assert.equal(h.calls.length,0);assert.equal(dialog.title,'Add to block');assert.match(dialog.html,/Section/);
 h.c.fd={get:k=>({card:'CARD-F',section:'fields.implications'}[k])};h.run('knowledgeCaptureReview(fd)');
 assert.equal(h.calls.length,0);assert.match(dialog.html,/Existing implication/);assert.match(dialog.html,/Check the acceptance event/);assert.equal(dialog.submit,'Save block');
 await dialog.handler({get:k=>k==='text'?'Existing implication.\n\nRefine the acceptance test.':''});
 assert.equal(h.calls.length,1);const call=h.calls[0];assert.equal(call.action,'knowledge-card-capture');assert.equal(call.data.section,'fields.implications');assert.equal(call.data.expected.revision,1);assert.equal(call.data.selection.review.id,'REVIEW');assert.equal(call.data.confirm,true);assert.equal(call.data.text,'Existing implication.\n\nRefine the acceptance test.');assert.equal(h.run('chatDraft().text'),'Unsent exploration');assert.equal(h.run('knowledgeCardView().open'),'SUB');
});
test('new card capture does not save on open or preview and exposes evidence notes without promoting a citation',async()=>{
 const h=harness(),forms=[];let dialog;h.c.modal=(title,html,submit,handler)=>{dialog={title,html,submit,handler};forms.push(dialog);};h.c.document.getElementById=()=>({addEventListener(){}});
 h.c.capture={key:h.run('chatKey()'),turn:{id:'TURN',revision:1},text:'One person described a missed handoff.'};h.run('openKnowledgeCapture(capture,false)');assert.equal(h.calls.length,0);
 h.c.fd={get:k=>({type:'finding',title:'Bounded handoff finding',section:'fields.evidence_notes'}[k])};h.run('knowledgeCaptureReview(fd)');
 assert.match(dialog.html,/add independent source citations/);assert.match(dialog.html,/name="summary" required/);assert.equal(h.calls.length,0);
 await dialog.handler({get:k=>({text:'A discussion note awaiting source validation.',summary:'A possible handoff gap.'}[k]||'')});
 assert.equal(h.calls[0].data.expected,null);assert.equal(h.calls[0].data.type,'finding');assert.equal(h.calls[0].data.statement,'A possible handoff gap.');assert.deepEqual(Object.keys(h.calls[0].data.selection),['turn','text']);
});
test('capture protects unsaved card edits and context changes before a write',()=>{
 const h=harness();let dialog;h.c.modal=(title,html)=>{dialog={title,html};};h.c.document.getElementById=()=>({addEventListener(){}});const row=addCard(h,'CARD-1','finding','Open finding');h.c.row=row;
 h.c.capture={key:h.run('chatKey()'),turn:{id:'TURN',revision:1},text:'A selected passage.'};h.run("knowledgeCardDraft(row).dirty=true;openKnowledgeCapture(capture,true)");h.c.fd={get:k=>({card:'CARD-1',section:'statement'}[k])};
 assert.throws(()=>h.run('knowledgeCaptureReview(fd)'),/open edits/);assert.equal(h.calls.length,0);h.c.state.project.id='OTHER';assert.throws(()=>h.run('knowledgeCaptureChoose()'),/original chat/);assert.equal(h.calls.length,0);
});
test('review prose and review history expose retained response fields as selectable text without permanent controls',()=>{
 const h=harness();h.c.review={ref:{id:'REVIEW',revision:2},current:true,body:{format:'visual',output:{findings:[{recommendation:'Test acceptance.',uncertainty:'Untested.'}],limitations:'Static screen.'}}};const html=h.run('chatReviewProse(review)');
 assert.match(html,/data-card-origin/);assert.match(html,/&quot;review&quot;/);assert.match(html,/&quot;path&quot;:\[&quot;findings&quot;,0,&quot;recommendation&quot;\]/);assert.doesNotMatch(html,/<button|<select|<details/);
 const turn=h.run("chatTurn({ref:{id:'TURN',revision:3},body:{role:'user',message:'A saved user passage.'}})");assert.match(turn,/data-card-origin/);assert.match(turn,/&quot;turn&quot;/);
});
test('highlighting a retained review passage reveals transient New card and Add to card actions',()=>{
 const h=harness();addCard(h);h.c.review={ref:{id:'REV',revision:1},body:{conversation:'CHAT'}};h.c.state.domain_chat.reports.push(h.c.review);
 const passage={dataset:{cardOrigin:JSON.stringify({review:h.c.review.ref,path:['findings',0,'recommendation']})}};const node={nodeType:1,closest:()=>passage};let bar;
 h.c.window={innerWidth:1000,getSelection:()=>({isCollapsed:false,rangeCount:1,toString:()=> 'A selected review recommendation.',getRangeAt:()=>({startContainer:node,endContainer:node,getBoundingClientRect:()=>({left:200,top:200})})})};h.c.document.createElement=()=>bar={style:{},setAttribute(){},remove(){}};h.c.document.body={appendChild(){}};
 h.run('showThoughtSelection()');assert.match(bar.innerHTML,/>Save as building block</);assert.match(bar.innerHTML,/>Add to a block</);assert.doesNotMatch(bar.innerHTML,/Save as card|Create implication/);
});

test('picked-up text browses categories and drops into a section through the same review in every domain',async()=>{
 for(const domain of ['research','design']){
  const h=harness(domain),row=addCard(h,'CARD-1','finding','A bounded finding');row.body.card.fields={implications:'Existing consequence.'};let dialog;
  h.c.document.body={classList:{toggle(){},remove(){}}};h.c.document.getElementById=id=>id==='modal-form'?{addEventListener(){}}:null;h.c.modal=(title,html,submit,handler)=>dialog={title,html,submit,handler};
  h.c.capture={key:h.run('chatKey()'),turn:{id:'TURN',revision:1},text:'A newly observed consequence.'};h.run("chatDraft().text='Keep my unsent thought';knowledgeCarryPick(capture)");
  assert.equal(h.calls.length,0);assert.match(h.run('knowledgeCardsPanel()'),/Picked up/);assert.equal(h.run('domainPanel()'),'implications');
  await h.run("knowledgeCardAction('kc-open','CARD-1')");assert.match(h.run('knowledgeCardsPanel()'),/Place picked-up text in Implications/);assert.equal(h.calls.length,0);
  await h.run("knowledgeCardAction('kc-carry-drop','fields.implications')");assert.equal(dialog.title,'Review block change');assert.match(dialog.html,/Existing consequence/);assert.equal(h.calls.length,0);
  await dialog.handler({get:k=>k==='text'?'Existing consequence.\n\nA newly observed consequence.':''});assert.equal(h.calls[0].action,'knowledge-card-capture');assert.equal(h.calls[0].data.section,'fields.implications');assert.equal(h.run('knowledgeCarryState()'),null);assert.equal(h.run('chatDraft().text'),'Keep my unsent thought');
 }
});
test('carry cancellation and context changes remove temporary targets without saving or changing the clipboard',async()=>{
 const h=harness();addCard(h);h.c.document.body={classList:{toggle(){},remove(){}}};h.c.capture={key:h.run('chatKey()'),turn:{id:'TURN',revision:1},text:'Keep this private.'};h.run('knowledgeCarryPick(capture)');h.c.state.project.id='OTHER';assert.equal(h.run('knowledgeCarryState()'),null);assert.equal(h.calls.length,0);
 h.c.state.project.id='P';h.run('knowledgeCarryPick(capture)');await h.run("knowledgeCardAction('kc-carry-cancel','')");assert.equal(h.run('knowledgeCarryState()'),null);assert.equal(h.calls.length,0);
});
test('a suggested destination skips choosing again but still reviews before writing',async()=>{
 const h=harness();addCard(h,'CARD-1','finding','Ownership');let dialog;h.c.modal=(title,html,submit,handler)=>dialog={title,html,submit,handler};
 h.c.p={id:'P1',origin:{review:{id:'REV',revision:1},path:['findings',0,'recommendation']},quote:'Test the next shift.',text:'Test the next shift.',target:{id:'CARD-1',revision:1},type:'finding',title:'Ownership',section:'fields.implications',reason:'It qualifies this same finding.'};
 h.run('knowledgePlacementReview(p)');assert.equal(dialog.title,'Review block change');assert.match(dialog.html,/It qualifies this same finding/);assert.equal(h.calls.length,0);
 await dialog.handler({get:k=>k==='text'?'Test the next shift.':''});assert.equal(h.calls[0].data.expected.id,'CARD-1');assert.equal(h.calls[0].data.section,'fields.implications');assert.equal(h.calls[0].data.confirm,true);
});
test('advisory passage highlights are sparse escaped and preserve native selection with no permanent response controls',()=>{
 const h=harness();h.c.state.domain_chat.knowledge_cards={...h.run('knowledgeCardInfo()'),placements:[{id:'P1',origin:{review:{id:'REV',revision:1},path:['summary']},quote:'Useful <detail>',target:null,type:'finding',section:'statement',title:'New concept'}]};
 const html=h.run("knowledgePrimeText({review:{id:'REV',revision:1},path:['summary']},'Before. Useful <detail>. After.')");assert.match(html,/Before/);assert.match(html,/<mark/);assert.match(html,/Useful &lt;detail>/);assert.match(html,/<button type="button" class="knowledge-prime-action"/);assert.match(html,/aria-label="Suggested block placement: New Finding"/);assert.doesNotMatch(html,/<select|<details|<detail>/);
 assert.doesNotMatch(h.run("knowledgePrimeText({review:{id:'OTHER',revision:1},path:['summary']},'Useful <detail>')"),/<mark/);
});
test('Copy remains available during pick-up and never saves a card',async()=>{
 const h=harness();let copied;h.c.navigator={clipboard:{writeText:async text=>{copied=text;}}};h.c.capture={key:h.run('chatKey()'),turn:{id:'TURN',revision:1},text:'Copy this unchanged.'};h.run('knowledgeCarryPick(capture);thoughtPartnerSelection=capture');
 for(const listener of h.listeners.click||[])await listener({target:{closest:s=>s==='[data-thought-selection]'?{dataset:{thoughtSelection:'copy'}}:null}});
 assert.equal(copied,'Copy this unchanged.');assert.equal(h.calls.length,0);assert.equal(h.run('knowledgeCarryState().text'),'Copy this unchanged.');
});
test('Assess card prepares one editable request in the existing AI partner for Research and Design',async()=>{
 for(const domain of ['research','design']){
  const h=harness(domain),row=addCard(h);h.c.document.getElementById=()=>({focus(){}});h.c.row=row;
  assert.match(h.run('knowledgeCardEditor(row)'),/>Assess block</);h.run("chatDraft().text='My existing question.'");await h.run("knowledgeCardAction('kc-assess','CARD-1')");
  assert.equal(h.calls.length,0);assert.match(h.run('chatDraft().text'),/^My existing question/);assert.match(h.run('chatDraft().text'),/Assess the block/);assert.equal(h.run('chatDraft().assessmentCard.id'),'CARD-1');assert.match(h.run('chatConversation()'),/Assess block · Shift handoff/);
  const question=h.run('chatDraft().text');await h.run("knowledgeCardAction('kc-assess','CARD-1')");assert.equal(h.run('chatDraft().text'),question);
  h.run('knowledgeCardDraft(row).dirty=true');await assert.rejects(h.run("knowledgeCardAction('kc-assess','CARD-1')"),/Save this block/);assert.equal(h.calls.length,0);
 }
});

function addGap(h){const c={key:'key-one',assessment:{id:'IR',revision:1},title:'Resolution requires a note <script>',missing:'Supply the transition rule.',scope:'domain:research',purpose:'historical',status:'uncertain',evidence_level:'documentary-alignment',occurrences:[{key:'G1',packet_ref:'P:v1',part_ref:'C/P1'}],reasoning:'Notification does not prove a prerequisite.',interpretation:{reading:'The note precedes resolution.'},source:{full_clause:'Resolution requires a note.'},evidence_quotes:[],sources:[],responses:[],expected:null,basis_boundary:'Historical analysis only.'};h.c.state.integrity_gaps=[c];h.c.state.actors={sam:{name:'Sam'}};return c;}
test('gap thumbnails coexist with ordinary knowledge cards and filter without a new page',()=>{
 const h=harness();addCard(h);addGap(h);const all=h.run('knowledgeCardList()');assert.match(all,/Shift handoff/);assert.match(all,/Information needed/);assert.doesNotMatch(all,/<script>/);h.run("knowledgeCardView().type='gap'");assert.doesNotMatch(h.run('knowledgeCardList()'),/Shift handoff/);assert.match(h.run('knowledgeCardTypeGrid()'),/Gap cards, 1/);h.run("knowledgeCardView().status='dismissed'");assert.doesNotMatch(h.run('knowledgeCardList()'),/Supply the transition/);assert.equal(h.calls.length,0);
});
test('opening a gap keeps the reviewer adjacent and makes only a saved-review read',async()=>{
 const h=harness(),c=addGap(h);h.c.command=async(action,data)=>{h.calls.push({action,data});return c;};await h.run("integrityGapAction('gap-open','IR:v1|key-one')");const html=h.run('domainChatScreen()');assert.match(html,/Saved AI partner reply for selected gap/);assert.match(html,/id="project-implications-panel"/);assert.match(html,/id="integrity-gap-response"/);assert.match(html,/New information on the adjacent card has not been assessed/);assert.equal((html.match(/id="domain-chat-composer"/g)||[]).length,1);assert.deepEqual(h.calls.map(x=>x.action),['integrity-gap-read']);assert.equal(h.c.view,'contributions');
});
test('gap drafts stay with their project, account and domain and survive panel navigation',async()=>{
 const h=harness(),c=addGap(h);h.c.command=async()=>c;await h.run("integrityGapAction('gap-open','IR:v1|key-one')");h.run("integrityGapDraft(integrityGapCurrent()).note='Unsaved draft';integrityGapDraft(integrityGapCurrent()).dirty=true");await h.run("integrityGapAction('gap-back','')");assert.equal(h.run('integrityGapCurrent()'),undefined);await h.run("integrityGapAction('gap-open','IR:v1|key-one')");assert.equal(h.run('integrityGapDraft(integrityGapCurrent()).note'),'Unsaved draft');h.c.state.actor='lee';h.c.state.domains.active='design';assert.equal(h.run('integrityGapCurrent()'),undefined);
});
test('supplied information stays amber and awaiting review without changing judgment',()=>{
 const h=harness(),c=addGap(h);c.response_count=1;c.collection_status='information-supplied';h.c.c=c;assert.match(h.run('integrityGapThumbnail(c)'),/Follow-up saved · awaiting review/);assert.equal(c.status,'uncertain');assert.doesNotMatch(h.run('integrityGapThumbnail(c)'),/Resolved|Approved/);
});

test('saving gap evidence sends an exact native command and keeps the judgment unchanged',async()=>{
 const h=harness(),c=addGap(h);h.c.command=async(action,data)=>{h.calls.push({action,data});return c;};await h.run("integrityGapAction('gap-open','IR:v1|key-one')");
 const values={kind:'evidence',mode:'new',note:'Test support explanation',title:'Synthetic policy',text:'A note is required.',source_locator:'Fictional policy v1, p1'};
 h.c.FormData=class extends Map{constructor(){super(Object.entries(values));}};h.c.document.getElementById=id=>id==='integrity-gap-response'?{}:null;
 await h.run('saveIntegrityGapResponse()');const sent=h.calls.find(x=>x.action==='integrity-gap-respond');assert.equal(sent.data.assessment.id,'IR');assert.equal(sent.data.expected,null);assert.equal(sent.data.evidence.source_locator,values.source_locator);assert.equal(sent.data.note,values.note);assert.equal(c.status,'uncertain');assert.equal(h.run('hasUnsavedIntegrityGaps()'),false);assert.deepEqual(h.calls.map(x=>x.action),['integrity-gap-read','integrity-gap-respond','integrity-gap-read']);
 c.sources=[{ref:{id:'SRC-opaque',revision:3},title:'Saved policy',fields:{text:'A note is required.'}}];Object.assign(values,{mode:'existing',source:'SRC-opaque:v3',field:'text',quote:'A note is required.'});h.c.c=c;h.c.d=values;const options=h.run('integrityGapEvidenceForm(d,c)');assert.match(options,/<option value="SRC-opaque:v3" selected>Saved policy · v3<\/option>/);await h.run('saveIntegrityGapResponse()');const existing=h.calls.filter(x=>x.action==='integrity-gap-respond').at(-1);assert.equal(existing.data.evidence.ref.id,'SRC-opaque');assert.equal(existing.data.evidence.ref.revision,3);assert.equal(existing.data.evidence.quote,values.quote);assert.equal(c.status,'uncertain');
});
test('a failed gap save retains text and retry identity instead of discarding the draft',async()=>{
 const h=harness(),c=addGap(h);h.c.command=async()=>c;await h.run("integrityGapAction('gap-open','IR:v1|key-one')");const values={kind:'clarification',note:'Retain this draft'};h.c.FormData=class extends Map{constructor(){super(Object.entries(values));}};h.c.document.getElementById=id=>id==='integrity-gap-response'?{}:null;const sent=[];h.c.command=async(action,data)=>{sent.push(data);throw Error('Another response was saved.');};await h.run('saveIntegrityGapResponse()');assert.equal(h.run('integrityGapDraft(integrityGapCurrent()).note'),values.note);assert.equal(h.run('hasUnsavedKnowledgeCards()'),true);assert.match(h.run('integrityGapDetail()'),/Another response was saved/);await h.run('saveIntegrityGapResponse()');assert.equal(sent[0].request_id,sent[1].request_id);
});

test('card suggestions and follow-up types separate hunches from evidence and assignments',async()=>{
 const h=harness(),c=addGap(h);h.c.command=async()=>c;await h.run("integrityGapAction('gap-open','IR:v1|key-one')");const html=h.run('integrityGapDetail()');assert.match(html,/Suggested next action/);assert.match(html,/not an assigned task/);assert.match(html,/Hunch to test/);assert.match(html,/does not prove execution/);h.run("integrityGapDraft(integrityGapCurrent()).kind='hunch'");assert.match(h.run('integrityGapDetail()'),/A hunch is not evidence/);assert.doesNotMatch(h.run('integrityGapDetail()'),/name="source_locator"/);h.run("integrityGapDraft(integrityGapCurrent()).kind='next-action'");assert.match(h.run('integrityGapDetail()'),/does not assign work/);
});

test('diagnostic clarification uses the adjacent gap flow without inventing an answer',async()=>{
 const h=harness(),c=addGap(h);c.record_kind='integrity-gap-review';c.provenance={summary:'One saved diagnostic judgment; other outputs disagreed. Not a complete assessment.'};c.clarification_request={question:'Does a clear category with no matching route reach central intake?',first_owner:'Design/source owner with intake operations',known_fact:'Ambiguous items reach central intake.',unresolved_connection:'Coverage of no matching rule.',evidence_threshold:'Source-bound documentary coverage; no execution claim.'};
 h.c.command=async(action,data)=>{h.calls.push({action,data});return c;};await h.run("integrityGapAction('gap-open','IR:v1|key-one')");
 const html=h.run('domainChatScreen()');assert.match(html,/Focused diagnostic for selected gap/);assert.match(html,/Clarification to pursue/);assert.match(html,/clear category with no matching route/);assert.match(html,/Prepared offline/);assert.match(html,/other outputs disagreed/);assert.match(html,/Design\/source owner with intake operations/);assert.match(html,/uncertain/);assert.match(html,/id="project-implications-panel"/);
 assert.equal(h.run('integrityGapDraft(integrityGapCurrent()).kind'),'clarification');assert.equal(h.run('integrityGapDraft(integrityGapCurrent()).note'),'');assert.equal(h.run('hasUnsavedIntegrityGaps()'),false);assert.deepEqual(h.calls.map(x=>x.action),['integrity-gap-read']);
});

test('D013: block types are grouped by family, the team\'s types lead and every other type stays reachable',()=>{
 const h=harness('design'),types={observation:{label:'Observation',family:'evidence',fields:{source_basis:'Where',applies_time:'Applies to · time or period'}},finding:{label:'Finding',family:'evidence',fields:{}},'design-decision':{label:'Design decision',family:'direction',fields:{alternatives:'Alternatives considered',applies_people:'Applies to · people or role',applies_confidence:'How sure, and why'}},lesson:{label:'Lesson',family:'direction',fields:{}},question:{label:'Open question',family:'open',fields:{}},note:{label:'Working note',family:'outputs',fields:{}}};
 h.c.state.domain_chat.knowledge_cards={types,families:{evidence:'Evidence',direction:'Direction',open:'Open',outputs:'Outputs'},preferred:['design-decision','lesson','note'],relations:{},catalogue:[],targets:[]};
 let html=h.run('knowledgeOrdinaryTypeGrid()');
 assert.ok(html.indexOf('>Direction</h4>')>-1&&html.indexOf('>Direction</h4>')<html.indexOf('data-id="design-decision"'));assert.match(html,/>Outputs<\/h4>/);assert.doesNotMatch(html.slice(0,html.indexOf('knowledge-more-types')),/data-id="observation"|>Evidence<\/h4>/);
 assert.match(html,/<details class="knowledge-more-types"><summary>More types \(3\)<\/summary>[\s\S]+data-id="observation"[\s\S]+data-id="finding"[\s\S]+data-id="question"/);
 assert.deepEqual(JSON.parse(JSON.stringify(h.run('knowledgeCardTypeChoices().map(e=>e[0])'))),['design-decision','lesson','note','observation','finding','question']);
 addCard(h,'CARD-9','finding');html=h.run('knowledgeOrdinaryTypeGrid()');                 // a type that holds a block is shown in its family
 assert.match(html.slice(0,html.indexOf('knowledge-more-types')),/>Evidence<\/h4>[\s\S]*data-id="finding"/);
 const fields=h.run("knowledgeCardFields({type:'design-decision',fields:{applies_people:'Front <desk>'}})");
 assert.ok(fields.indexOf('card-field-alternatives')<fields.indexOf('<fieldset class="knowledge-applies">'));assert.match(fields,/<legend>Where this applies<\/legend>[\s\S]+card-field-applies_people[\s\S]+Front &lt;desk>[\s\S]+card-field-applies_confidence/);
 h.c.state.domain_chat.knowledge_cards.families={};h.c.state.domain_chat.knowledge_cards.preferred=[];assert.doesNotMatch(h.run('knowledgeOrdinaryTypeGrid()'),/knowledge-family|knowledge-more-types/);   // older state still renders
});

'use strict';
let domainChatReportId=null,domainChatSending=null;
let domainChatRail='requirements',domainChatPreview=null,domainChatPause=false,domainChatOnlyRemaining=false;
const domainChatDrafts=new Map(),domainChatDisclosures=new Map(),domainPanels=new Map(),domainChatSelection=new Map(),domainChatNavOpen=new Map(),domainChatNavFiles=new Map(),domainChatNavEarlier=new Map();
function domainPanel(){return domainPanels.get(chatKey())??null;}
function chatDisclosure(key){return domainChatDisclosures.get(chatKey()+'|'+key)?'open':'';}
function chatInfo(){return state.domain_chat||{threads:[],turns:[],reports:[]};}
function chatWorks(){return records('contribution-draft').filter(r=>r.body.chassis&&!r.body.submission_of&&r.body.owner===state.actor&&(!r.body.domain_key||r.body.domain_key===state.domains?.active));}
function chatWork(){const drafts=chatWorks();return drafts.find(r=>r.ref.id===selected)||drafts.find(r=>r.ref.id===domainChatSelection.get(chatSession()))||drafts[0];}
function chatThread(){const work=chatWork();return chatInfo().threads.find(t=>t.body.draft_id===work?.ref.id);}
function chatKey(){return [state.project.id,state.project.version,state.auth?.account?.id||'development',state.actor,state.domains?.active,chatWork()?.ref.id||'new'].join('|');}
function chatDraft(){const key=chatKey();if(!domainChatDrafts.has(key))domainChatDrafts.set(key,{text:'',file:null,revision:0});return domainChatDrafts.get(key);}
function chatSource(raw){return domainInfo().sources.find(s=>label(s.ref)===label(raw));}
function chatReports(){const thread=chatThread(),current=chatInfo().reports.filter(r=>r.body.conversation===thread?.ref.id);if(current.length)return current;const work=chatWork();if(!work)return [];return [...(state.design_visual?.reports||[]).filter(r=>r.body.draft.id===work.ref.id).map(r=>({...r,body:{...r.body,format:'visual',batch:{mode:'visual',pages:r.body.pages.map(p=>p.page)},citation_records:r.basis_records,legacy:true}})),...(domainInfo().reports||[]).filter(r=>r.body.draft.id===work.ref.id).map(r=>({...r,body:{...r.body,format:'text',batch:{mode:'text',start:0,end:0},legacy:true}}))];}
function chatOutputReport(){return chatReports()[0];}
function chatBatchName(batch){return batch?.mode==='visual'?'Pages '+batch.pages.join(', '):batch?.end?'Text '+(batch.start+1)+'–'+batch.end:'Project context';}
function chatPending(){const p=chatThread()?.body.pending;return p&&Date.now()-Date.parse(p.at)>300000;}
function chatModelUnavailable(){return domainInfo()?.model?.configured===false;}
function chatHeader(){const p=domainProfile(),work=typeof chatWork==='function'?chatWork():null,intents=typeof records==='function'?records('intent'):[],intentRev=intents.length?Math.max(...intents.map(r=>r.ref.revision)):0,reqs=work?.body?.requirement_refs||[];
 const basis=[intentRev?`Intent v${intentRev}`:'',...reqs.slice(0,2).map(r=>{const rec=typeof get==='function'?get(r.id):null;return String(rec?.body?.title||'Requirement').replace(/ · initial requirement$/,'');}),reqs.length>2?`${reqs.length-2} more`:''].filter(Boolean);
 return `<header class="chat-page-head workbench-head"><div><h1 tabindex="-1">${esc(p.config.label)} workbench</h1><p class="workbench-privacy">Private to you until you share${basis.length?` · <span class="workbench-basis">Working from ${esc(basis.join(' · '))}</span>`:''}</p></div><button type="button" class="primary" data-action="dchat-sharing-open" aria-controls="domain-sharing-panel">Prepare to share</button></header>`;}
function chatContextChanged(){return [...(chatWork()?.body.requirement_refs||[]),...(chatWork()?.body.input_refs||[])].some(raw=>{const current=get(raw.id);return current&&current.ref.revision!==raw.revision;});}
// Orientation describes the selected saved basis, never an inferred readiness score.
function chatTaskGuidance(){
 const work=chatWork(),plan=typeof currentWorkingDomainPlan==='function'?currentWorkingDomainPlan():null;
 const requirements=work?.body.requirement_refs||[],inputs=work?.body.input_refs||[],files=work?.body.source_refs||[];
 const received=[requirements.length?`${requirements.length} requirement${requirements.length===1?'':'s'}`:'',inputs.length?`${inputs.length} published input${inputs.length===1?'':'s'}`:'',files.length?`${files.length} file${files.length===1?'':'s'}`:''].filter(Boolean).join(' · ');
 const changed=chatContextChanged()||plan?.current===false;
 const objectives=plan?.body.objectives||plan?.body.output?.objectives||[];
 const objective=objectives.find(o=>o.disposition!=='omit'&&(o.title||o.question));
 const gap=chatAlignmentRows().find(r=>r.current&&r.gaps?.length);
 const question=(plan?.body.brief_sections||plan?.body.output?.brief_sections||[]).find(s=>s.disposition==='question'&&(s.title||s.text));
 const focus=chatThread()?.body.focus_source,source=focus&&chatSource(focus);
 const review=chatReports().find(r=>r.selection_current??r.current);
 const check=changed?'Selected inputs changed. Review the earlier basis before reusing this work.':gap?gap.gaps[0]:question?(question.title||question.text):review?'Inspect the saved review’s evidence and limits. No recorded gap is summarized here.':objective?'Check what evidence is needed for: '+(objective.title||objective.question):'Check the selected context and evidence needed for this work.';
 const next=changed?{action:'dchat-guidance-context',title:'Review changed inputs',why:'Keep saved work; inspect what changed.'}:gap?{action:'dchat-alignment-panel',title:'Inspect recorded gap',why:gap.title}:question?{action:'dchat-guidance-plan',title:'Review open plan question',why:'Keep the uncertainty visible in your plan.'}:review?{action:'dchat-report',id:review.ref.id,title:'Inspect saved review',why:'Evidence, scope and review limits.'}:!plan?{action:'dchat-guidance-plan',title:'Read what was handed over',why:'Then set up your plan.'}:source?{action:'dchat-review-work',title:'Ask for a review of your file',why:source.body.title}:{action:'dchat-brief-coach',title:'Discuss next step',why:objective?.title||objective?.question||'Use your current Working brief.'};
 return {received:received||'No requirements, published inputs or files selected.',check,changed,showCheck:Boolean(changed||gap||question),next};
}
function chatHandedOver(){
 const work=chatWork();if(!work)return '';
 const quest=typeof cockpitQuest==='function'?cockpitQuest():'',values=typeof casePublishedValues==='function'?casePublishedValues():{},mission=String(values.value||'').trim();
 const intents=records('intent'),rev=intents.length?Math.max(...intents.map(r=>r.ref.revision)):0;
 const reqs=(work.body.requirement_refs||[]).map(raw=>get(raw.id)).filter(Boolean),inputs=(work.body.input_refs||[]).map(raw=>get(raw.id)).filter(Boolean);
 const weak=typeof cockpitAreas==='function'?cockpitAreas():[];
 const row=(label,body)=>body?`<div class="brief-handover-row"><dt>${esc(label)}</dt><dd>${body}</dd></div>`:'';
 const out=row('The question for your team',quest?esc(quest):'')+row(`Business intent${rev?' · version '+rev:''}`,mission?esc(mission):'')
  +row('Requirements you are working from',reqs.length?`<ul class="brief-handover-list">${reqs.map(r=>`<li><span>${esc(String(r.body.title||'Requirement').replace(/ · initial requirement$/,''))}</span>${typeof requirementEvidenceChip==='function'?requirementEvidenceChip(r.ref.id):''}</li>`).join('')}</ul>`:'')
  +row('Shared by other teams',inputs.length?`<ul class="brief-handover-list">${inputs.map(r=>`<li><span>${esc(r.body.title||r.ref.id)}</span><span class="caption">${esc(state.domains?.domains?.find(d=>d.key===r.body.domain)?.label||r.body.domain||'')}</span></li>`).join('')}</ul>`:'')
  +row('Where evidence is thin',weak.length?`<ul class="brief-handover-list">${weak.map(a=>`<li><span>${esc(a.label)}</span><span class="caption">${esc((typeof CASE_LEVEL_WORD==='object'?CASE_LEVEL_WORD[a.level]:a.level)+' · '+a.next)}</span></li>`).join('')}</ul>`:'');
 return out?`<section class="brief-handover" aria-label="What was handed over"><h3>What was handed over</h3><dl>${out}</dl></section>`:'';
}
function chatBriefStack(){
 const title='Working brief',plan=typeof currentWorkingDomainPlan==='function'?currentWorkingDomainPlan():null,status=typeof workingDomainPlanStatus==='function'?workingDomainPlanStatus(plan):'Draft plan',guidance=chatTaskGuidance();
 // Until a plan exists and before any conversation, the handed-over context leads; afterwards the person's own choice stands.
 const key=chatKey()+'|working-brief',fresh=!plan&&!chatTurns().length,open=domainChatDisclosures.has(key)?chatDisclosure('working-brief'):fresh?'open':'';
 const quest=typeof cockpitQuest==='function'?cockpitQuest():'';
 return `<details id="domain-working-brief" class="domain-brief-stack workbench-created-surface${guidance.changed?' has-changed-basis':''}" data-chat-disclosure="working-brief" ${open}><summary><span class="workbench-created-heading"><span class="domain-brief-stack-title">${esc(title)}</span></span><span class="caption domain-brief-guidance${guidance.changed?' has-changed-inputs':''}"><span>${quest?'Handed over: '+esc(quest)+' · ':'Received context: '+esc(guidance.received)+' · '}${esc(status)}</span>${guidance.showCheck?`<span class="domain-brief-check" title="${esc(guidance.check)}">${guidance.changed?'<span class="domain-brief-warning-icon" aria-hidden="true">!</span>':''}${esc(guidance.check)}</span>`:''}</span></summary><div class="domain-brief-stack-body">${chatHandedOver()}${!guidance.showCheck?`<p class="domain-brief-detail-guidance">${esc(guidance.check)}</p>`:''}${chatBriefInputs()}${typeof workingDomainBriefs==='function'?workingDomainBriefs():'<p>Define the scope and objectives for this work within the domain.</p>'}</div></details>`;
}
function chatWorkspaceActions(){
 if(typeof cockpitRail==='function')return cockpitRail();
 const {next}=chatTaskGuidance(),panel=domainPanel();
 return `<section class="chat-workspace-actions domain-working-actions" aria-label="Workbench actions"><div class="domain-next-action"><button type="button" class="compact-text-action domain-guidance-next" data-action="${next.action}" data-id="${esc(next.id||'')}" title="${esc(next.why)}" ${busy?'disabled':''}>Next: ${esc(next.title)}</button></div><div class="domain-reference-actions"><div class="domain-material-actions workbench-sections" role="group" aria-label="Working materials"><button type="button" class="workbench-section" data-action="dchat-panel-none" aria-pressed="${!panel}">AI partner</button>${typeof projectImplicationsPanel==='function'?`<button type="button" class="workbench-section" data-action="dev-implications" aria-pressed="${panel==='implications'}" aria-expanded="${panel==='implications'}" aria-controls="project-implications-panel">Building blocks <span class="workbench-count">${typeof knowledgeCards==='function'?knowledgeCards().length:0}</span></button>`:chatAlignmentRows().length?`<button type="button" class="workbench-section" data-action="dchat-alignment-panel" aria-pressed="${panel==='alignment'}" aria-expanded="${panel==='alignment'}" aria-controls="domain-alignment-panel">Alignment <span class="workbench-count">${chatAlignmentGroups().length}</span></button>`:''}${typeof domainFlowActions==='function'&&typeof flowInfo==='function'&&flowInfo().enabled?`<button type="button" class="workbench-section" data-action="flow-open" aria-haspopup="dialog">User flows <span class="workbench-count">${(flowInfo().flows||[]).length}</span></button>`:''}${typeof domainPrototypeActions==='function'&&state.domains?.active==='design'?`<button type="button" class="workbench-section" data-action="proto-open" aria-haspopup="dialog">Prototype alternatives</button>`:''}<button type="button" class="workbench-section prepare-sharing-action workbench-document-link" data-action="dchat-sharing-panel" aria-pressed="${panel==='sharing'}" aria-expanded="${panel==='sharing'}" aria-controls="domain-sharing-panel">Outcomes report</button></div></div><div class="domain-output-actions" role="group" aria-label="Project updates and outgoing work">${typeof projectUpdateFeed==='function'?projectUpdateFeed():''}</div></section>`;
}
function chatOpenBriefInputs(){
 domainChatDisclosures.set(chatKey()+'|working-brief',true);
 domainChatDisclosures.set(chatKey()+'|brief-inputs',true);
}
function chatBriefInputs(){
 return `<details id="domain-brief-inputs" class="domain-brief-inputs" data-chat-disclosure="brief-inputs" ${chatDisclosure('brief-inputs')}><summary>Domain interpretation</summary><div class="domain-brief-inputs-body">${chatBriefInputContent()}</div></details>`;
}
function chatBriefInputContent(){
 const plan=typeof currentWorkingDomainPlan==='function'?currentWorkingDomainPlan():null;
 return `<div class="brief-incoming-context">${typeof projectDomainInterpretation==='function'?projectDomainInterpretation(plan):'<p class="caption">Domain interpretation is not yet prepared.</p>'}${typeof interpretationPanel==='function'?interpretationPanel(null,'Packet assessment'):''}${chatReference()}<details class="domain-context-section"><summary>Tools</summary>${typeof projectToolLinks==='function'&&projectToolLinks()?`<div class="domain-tool-links">${projectToolLinks()}</div>`:'<p class="caption">Set up project file links and connections in Settings → Integrations.</p>'}</details></div>`;
}
function domainChatNavigation(){
 if(!state.domains?.active||!state.domain_chat||!domainProfile())return '';
 const open=domainChatNavOpen.get(chatSession())??view==='contributions';
 return `<div class="project-chat-navigation"><details class="navigation-chats" data-domain-chat-navigation ${open?'open':''}><summary>Chats in this project</summary>${chatLibrary()}</details><button type="button" class="compact-text-action navigation-chat-add" data-action="dchat-new" aria-label="New project chat" title="New project chat">＋</button></div>`;
}
function chatLibrary(){
 const work=chatWork(),works=chatWorks(),recent=works.slice(0,5);
 if(work&&!recent.some(r=>r.ref.id===work.ref.id))recent.push(work);
 const shown=new Set(recent.map(r=>r.ref.id)),earlier=works.filter(r=>!shown.has(r.ref.id)),session=chatSession();
 return `<div class="navigation-chat-library"><nav aria-label="Project chats"><div class="navigation-chat-recent">${recent.map(r=>chatLibraryItem(r,work)).join('')||'<p class="caption">No project chats yet.</p>'}</div>${earlier.length?`<details class="navigation-chat-earlier" data-chat-earlier="${esc(session)}" ${domainChatNavEarlier.get(session)?'open':''}><summary>Earlier chats (${earlier.length})</summary>${earlier.map(r=>chatLibraryItem(r,work)).join('')}</details>`:''}</nav>${chatAttemptHistory()}</div>`;
}
function chatLibraryItem(r,work){
 const files=r.body.source_refs||[],current=r.ref.id===work?.ref.id,fileKey=chatSession()+'|'+r.ref.id;
 return `<div class="navigation-chat-item"><a href="#main" class="item-title-link navigation-chat-title" data-action="dchat-open" data-id="${esc(r.ref.id)}" ${view==='contributions'&&current?'aria-current="page"':''} title="${esc(r.body.title||'Untitled chat')}">${esc(r.body.title||'Untitled chat')}</a>${files.length?`<details class="navigation-chat-files" data-chat-files="${esc(r.ref.id)}" ${domainChatNavFiles.get(fileKey)?'open':''}><summary>Files (${files.length})</summary>${files.map(raw=>{const src=chatSource(raw);return `<a href="#main" class="item-title-link navigation-file-title document-name-link" data-action="dchat-nav-source" data-id="${esc(r.ref.id+'|'+raw.id)}">${esc(src?.body.title||raw.id)}</a>`;}).join('')}</details>`:''}</div>`;
}
async function chatOpenWork(id){
 if(!chatWorks().some(r=>r.ref.id===id))throw Error('This chat is unavailable in the current project and domain.');
 if(typeof saveBeforeProjectChange==='function')await saveBeforeProjectChange();else await saveWorkingReport();
 if(!chatWorks().some(r=>r.ref.id===id))throw Error('This chat is no longer available.');
 document.querySelector('#modal.navigation-dialog[open]')?.close();
 selected=id;domainChatSelection.set(chatSession(),id);view='contributions';domainChatPreview=null;domainChatReportId=null;
 if(typeof domainWorkMode!=='undefined')domainWorkMode='conversation';
}

function chatArtifact(){
 const thread=chatThread(),raw=domainChatPreview?.source||thread?.body.focus_source,source=raw&&chatSource(raw);if(!source)return '';
 const page=domainChatPreview?.page||1;
 if(source.body.visual_pdf)return `<details class="chat-artifact" ${domainChatPreview?'open':''}><summary>Preview · ${esc(source.body.title)}</summary><label class="chat-page-selector">Review as <select id="chat-review-mode" data-source="${source.ref.id}"><option value="text" ${(thread?.body.review_mode||domainProfile().config.pdf_review_mode||'text')==='text'?'selected':''}>Document text</option><option value="visual" ${(thread?.body.review_mode||domainProfile().config.pdf_review_mode||'text')==='visual'?'selected':''}>PDF pages</option></select></label><label class="chat-page-selector">Page <select id="chat-preview-page" data-source="${source.ref.id}">${Array.from({length:source.body.visual_pdf.page_count},(_,i)=>`<option value="${i+1}" ${page===i+1?'selected':''}>${i+1}</option>`).join('')}</select> of ${source.body.visual_pdf.page_count}</label><figure><img src="${esc(visualPageUrl(source.ref,page))}" alt="${esc(source.body.title)} · PDF page ${page}"><figcaption>Page ${page} · static screen · <a href="${esc(visualPageUrl(source.ref,page))}" target="_blank" rel="noopener">Open full-size page</a></figcaption></figure></details>`;
 const quote=domainChatPreview?.quote,offset=domainChatPreview?.start||0,text=quote?source.body.text.slice(Math.max(0,offset-250),offset+quote.length+400):source.body.text.slice(0,4500);
 return `<details class="chat-artifact" ${domainChatPreview?'open':''}><summary>${esc(source.body.title)}${domainChatPreview?.page?' · page '+domainChatPreview.page:''}</summary><pre>${esc(text)}</pre><p class="caption">${quote?'Source passage around the cited quote.':'Extracted text preview. The review processes this file in bounded passages.'}</p></details>`;
}
function chatTurns(){const thread=chatThread();return thread?chatInfo().turns.filter(r=>r.body.conversation===thread.ref.id):[];}
function chatAttemptHistory(){
 const errors=chatTurns().filter(r=>r.body.role==='error'),reviews=chatReports();if(!errors.length&&!reviews.length)return '';
 return `<details class="chat-attempt-history"><summary>Review history (${errors.length+reviews.length})</summary>${reviews.map(r=>`<p><a href="#main" class="item-title-link" data-action="dchat-report" data-id="${esc(r.ref.id)}">${esc(r.body.question?.slice(0,80)||(r.body.format==='visual'?'Prototype review':'Work review'))}</a><br><small>${esc(chatBatchName(r.body.batch))}${!r.current&&!r.selection_current?' · Earlier inputs':''}</small></p>`).join('')}${errors.length?'<p class="caption">Earlier requests that did not complete. Your files and messages remain saved.</p>':''}${errors.map(r=>{const at=new Date(r.body.at),time=Number.isFinite(at.valueOf())?at.toLocaleString():'Date not recorded';return `<article><p class="caption">${esc(time)}</p><p>${esc(r.body.message)}</p></article>`;}).join('')}</details>`;
}
function chatRetryNotice(){
 if(busy||chatThread()?.body.pending)return '';
 const last=chatTurns().filter(r=>['user','assistant','error'].includes(r.body.role)).at(-1);
 if(last?.body.role!=='error')return '';
 return `<div class="chat-retry-notice" role="status"><p>${esc(last.body.message)}</p><button type="button" class="compact-text-action" data-action="dchat-retry" data-id="${esc(last.body.request_id)}" ${chatModelUnavailable()?'disabled title="Your AI partner is unavailable"':''}>Retry</button></div>`;
}
function chatTurn(turn){const b=turn.body;if(b.role==='batch'||b.role==='attachment'||b.role==='error')return b.role==='attachment'?`<p class="chat-file-receipt">${esc(b.message)}</p>`:'';const assistant=b.role==='assistant';return `<article data-chat-turn-id="${esc(turn.ref?.id||'')}" data-chat-turn-revision="${esc(turn.ref?.revision||'')}" class="chat-message ${assistant?'from-coach':'from-user'}"><strong${assistant?' class="thought-partner-title"':''}>${assistant?'AI partner':'You'}</strong><p class="pre" data-card-origin="${esc(JSON.stringify({turn:turn.ref}))}">${typeof knowledgePrimeText==='function'&&b.report?knowledgePrimeText({review:b.report,path:['summary']},b.message):esc(b.message)}</p>${b.batch&&assistant?`<small>${esc(chatBatchName(b.batch))} · ${b.mode==='live'?'Live AI':b.mode==='simulated'?'Simulated test':'Not connected'}</small>`:''}${b.report?chatTurnRecommendations(b.report.id):''}${assistant&&b.message&&b.message.length<=4000&&typeof openKnowledgeCapture==='function'?`<div class="chat-turn-actions" role="group" aria-label="Use this reply"><button type="button" class="compact-text-action" data-action="dchat-turn-block" data-id="${esc(label(turn.ref))}|new">Save as building block</button>${typeof knowledgeCards==='function'&&knowledgeCards().some(r=>r.body.status==='held')?`<button type="button" class="compact-text-action" data-action="dchat-turn-block" data-id="${esc(label(turn.ref))}|add">Add to a block</button>`:''}<span class="caption">Saved wording, not evidence. Nothing is shared.</span></div>`:''}${assistant&&b.report&&chatReports().find(r=>label(r.ref)===label(b.report))?.body.output.brief_changes?.length?`<button type="button" class="compact-text-action brief-response-action" data-action="dev-brief-review" data-id="${esc(b.report.id)}">Review brief update</button>`:''}</article>`;}
function chatReviewText(report,path,text){return `<span data-card-origin="${esc(JSON.stringify({review:report.ref,path}))}">${typeof knowledgePrimeText==='function'?knowledgePrimeText({review:report.ref,path},text||''):esc(text||'')}</span>`;}
function chatReviewValue(report,path,title,text){return `<h4>${esc(title)}</h4><p class="pre">${chatReviewText(report,path,text)}</p>`;}
function chatReviewProse(report){
 const b=report.body,out=b.output,items=out.findings||out.suggestions||[],branch=out.findings?'findings':'suggestions';
 const earlier=!report.current&&!report.selection_current?'<p class="caption">This review used earlier inputs.</p>':'';
 return earlier+items.map((f,i)=>b.format==='visual'?`<p><strong>Recommendation:</strong> ${chatReviewText(report,[branch,i,'recommendation'],f.recommendation)}${f.uncertainty?' '+chatReviewText(report,[branch,i,'uncertainty'],f.uncertainty):''}<small>Page ${esc(f.page)} · ${esc(f.area)}</small></p>`:`<p><strong>${chatReviewText(report,[branch,i,'issue'],f.issue)}.</strong> ${chatReviewText(report,[branch,i,'question'],f.question)}${f.edit?.text?`<br>Suggested wording: ${chatReviewText(report,[branch,i,'edit','text'],f.edit.text)}`:''}</p>`).join('')+(out.limitations?`<p class="caption">${chatReviewText(report,['limitations'],out.limitations)}</p>`:'');
}
function chatTurnRecommendations(id){const report=chatReports().find(r=>r.ref.id===id);return report?chatReviewProse(report):'';}
function chatPriorRecommendations(){return '';}
function chatConversation(){
 const t=chatThread(),turns=chatInfo().turns.filter(r=>r.body.conversation===t?.ref.id),draft=chatDraft(),modelUnavailable=chatModelUnavailable(),retryNotice=chatRetryNotice();
 return `<section class="chat-console" aria-label="Work with your AI partner"><header><h2 class="thought-partner-title">AI partner</h2><p class="caption">Private</p></header><div class="chat-scroll" id="chat-messages">${typeof integrityGapReviewerContext==='function'?integrityGapReviewerContext():''}${chatArtifact()}${turns.length?turns.map(chatTurn).join(''):''}${chatPriorRecommendations()}</div><form id="domain-chat-composer"><label class="reviewer-composer-label" for="domain-chat-message">You</label><textarea id="domain-chat-message" class="integrity-review-input" name="message" rows="4" aria-label="Ask your AI partner" placeholder="Ask your AI partner" maxlength="3000">${esc(draft.text)}</textarea>${draft.file?`<div class="chat-attachment-chip"><span>${esc(draft.file.name)}</span><button type="button" class="quiet icon" data-action="dchat-remove-file" aria-label="Remove attached file">✕</button></div>`:''}${draft.briefDevelopment?`<div class="chat-attachment-chip"><span>Working brief</span><button type="button" class="quiet icon" data-action="dchat-clear-brief-focus" aria-label="Leave brief development">✕</button></div>`:''}${draft.assessmentCard?`<div class="chat-attachment-chip"><span>Assess block · ${esc(draft.assessmentTitle)}</span><button type="button" class="quiet icon" data-action="dchat-clear-card-assessment" aria-label="Remove block from assessment">✕</button></div>`:""}<div class="chat-composer-actions"><div><input id="domain-chat-file" type="file" accept=".pdf,.txt,.md,.csv,.json,.docx,.pptx" hidden><button type="button" class="chat-add" data-action="dchat-file" aria-label="Add a file" ${busy?'disabled':''}>＋</button><button type="button" class="compact-text-action" data-action="dchat-review-work" ${busy?'disabled':''}>Ask for a review</button></div><button type="submit" class="primary" ${busy||domainChatSending||t?.body.pending||modelUnavailable?'disabled':''}>Ask</button></div>${retryNotice}<p class="chat-status" id="domain-chat-status" role="status" aria-live="polite">${busy?'Working…':modelUnavailable&&!retryNotice?'Your AI partner is unavailable. You can keep drafting.':''}</p>${t?.body.pending?`<p class="caption">A saved request is ${chatPending()?'interrupted or overdue':'processing'}.</p>${chatPending()?button('Recover interrupted review','dchat-recover','','small'):''}`:''}<button type="button" id="domain-chat-pause" class="quiet small" ${busy?'':'hidden'}>Pause after this part</button></form></section>`;
}
function chatCriteria(text){const lines=String(text||'').split(/\n/).map(s=>s.trim()).filter(Boolean);return lines.length>1&&lines.every(s=>/^\d+[.)]\s/.test(s))?'<ol>'+lines.map(s=>'<li>'+esc(s.replace(/^\d+[.)]\s*/,''))+'</li>').join('')+'</ol>':para(text||'Not defined yet');}
function chatReference(){
 const work=chatWork(),requirements=records('requirement'),linked=new Set((work?.body.requirement_refs||[]).map(r=>r.id)),inputs=records('contribution').filter(r=>r.body.domain_key!==state.domains?.active),selectedInputs=new Set((work?.body.input_refs||[]).map(label));
 return `<div class="chat-reference">${chatContextChanged()?'<p class="caption">Project inputs changed. Check Requirements and the current interpretation before updating this work.</p><button type="button" class="compact-text-action" data-action="dchat-refresh-scope">Use updated requirements</button>':''}${typeof projectDependencies==='function'?projectDependencies(work,true):''}<details class="chat-context"><summary>Review scope · ${linked.size} requirement${linked.size===1?'':'s'}</summary><p class="caption">Select which published requirements and findings inform this work. This changes review scope, not shared wording.</p><p><a class="item-title-link" href="#main" data-nav="requirements">Open Requirements</a></p><form id="domain-chat-context">${requirements.map(r=>`<label class="chat-check"><input type="checkbox" name="requirement" value="${esc(r.ref.id)}" ${linked.has(r.ref.id)?'checked':''}>${esc(r.body.title||r.ref.id)} <small>${esc(label(r.ref))}</small></label>`).join('')}<h4>Published findings</h4>${inputs.map(r=>`<label class="chat-check"><input type="checkbox" name="upstream" value="${esc(label(r.ref))}" ${selectedInputs.has(label(r.ref))?'checked':''}>${esc(r.body.title||r.ref.id)}</label>`).join('')}<button type="submit" class="small">Use selected context</button></form></details></div>`;
}

function chatReportView(reportId=null,embedded=false){
 const reports=chatReports(),report=reports.find(r=>r.ref.id===(reportId||domainChatReportId))||reports[0];
 if(!report)return '<p class="chat-report-empty">Your review findings will appear here after you send a file or question.</p>';
 const b=report.body,items=b.output.findings||b.output.suggestions,thread=chatThread(),same=reports.filter(r=>(r.current||r.selection_current)&&JSON.stringify(r.body.source)===JSON.stringify(b.source)),done=new Set(same.flatMap(r=>r.body.batch.mode==='visual'?r.body.batch.pages:[r.body.batch.start])),total=b.parts_total||thread?.plan?.length||1,coverage=!report.current&&!report.selection_current?`${chatBatchName(b.batch)} · Saved review`:b.format==='visual'?`${done.size} of ${chatSource(b.source)?.body.visual_pdf?.page_count||'?'} pages reviewed`:`${done.size} of ${total} text parts reviewed`;
 return `<div class="chat-report"><p class="caption">${esc(chatSource(b.source||{})?.body.title||'Project context')} · ${esc(coverage)}${!report.current&&!report.selection_current?' · Earlier inputs':''}</p>${!report.current&&!report.selection_current?'<p class="banner signal-notice signal-advisory">The reviewed work or source context changed. Inspect the earlier basis before using these findings.</p>':''}${report.current&&new Set(same.map(r=>JSON.stringify(r.body.batch))).size<total?button('Review remaining parts','dchat-remaining',report.ref.id,'small'):''}${!embedded&&reports.length>1?`<details class="chat-review-history"><summary>Review history (${reports.length})</summary><label class="form-field"><span>Choose an exchange</span><select id="domain-chat-report">${reports.map(r=>`<option value="${r.ref.id}" ${r.ref.id===report.ref.id?'selected':''}>${esc((r.body.question||'Review').slice(0,38))} · ${esc(chatBatchName(r.body.batch))} · ${r.current?'Current inputs':'Earlier inputs'}</option>`).join('')}</select></label></details>`:''}${items.map((f,i)=>`<details class="chat-finding" data-chat-disclosure="finding:${report.ref.id}:${i}" ${chatDisclosure('finding:'+report.ref.id+':'+i)}><summary>${b.format==='visual'?'Page '+f.page+' · '+esc(f.area):esc(f.issue)}</summary>${b.format==='visual'?`${chatReviewValue(report,['findings',i,'observation'],'Visible observation',f.observation)}${chatReviewValue(report,['findings',i,'rationale'],'Why it matters',f.rationale)}${chatReviewValue(report,['findings',i,'recommendation'],'Recommendation',f.recommendation)}${f.uncertainty?chatReviewValue(report,['findings',i,'uncertainty'],'Uncertainty',f.uncertainty):''}${button('View page '+f.page,'dchat-locate',report.ref.id+'|'+i,'quiet small')}`:`${chatReviewValue(report,['suggestions',i,'question'],'Question',f.question)}${b.locations?.[i]?button('View '+(b.locations[i].page?'page '+b.locations[i].page:'source passage'),'dchat-locate',report.ref.id+'|'+i,'quiet small'):''}`}
 <details><summary>Evidence & requirement basis</summary>${b.format==='visual'?f.context_links.map(link=>{const record=b.citation_records.find(r=>label(r.ref)===label(link.ref));return `<p><strong>${esc(record?.body.title||record?.kind||link.ref.id)}</strong></p><blockquote>${esc(link.quote)}</blockquote><small>${esc(label(link.ref))}</small>`;}).join(''):`<blockquote>${esc(f.quote)}</blockquote><small>${esc(f.basis)}</small>${(f.requirement_ids||[]).map(id=>`<p class="caption">${esc(get(id)?.body.title||id)}</p>`).join('')}`}</details>${typeof findingReportButton==='function'?findingReportButton(report,i):''}${b.format==='text'&&f.edit?.text?`<details><summary>Suggested wording</summary>${chatReviewText(report,['suggestions',i,'edit','text'],f.edit.text)}</details>`:''}</details>`).join('')||'<p>No additional findings were proposed in this part.</p>'}<details><summary>Review limits & history</summary><p>${b.output.limitations?chatReviewText(report,['limitations'],b.output.limitations):esc('This is advisory analysis of the supplied text, not validated research or requirement approval.')}</p><small>${esc(b.mode)} · ${esc(label(b.draft))}</small><p class="caption">Only displayed scope and the current file part were reviewed. Unrelated and private upstream work is excluded.</p></details></div>`;
}
const alignmentEditDrafts=new Map();
const alignmentStatusLabels={'appears-met':'Appears met',gap:'Gap','not-demonstrated':'Not yet demonstrated'};
const alignmentDimensions={grounding:'Grounding in evidence',corroboration:'Independent corroboration',coverage:'Coverage of the claim',applicability:'Currency & applicability'};
function chatAlignmentRows(){return (chatInfo().alignment||[]).filter(r=>r.conversation===chatThread()?.ref.id);}
function chatAlignmentGroups(){const groups=new Map();for(const row of chatAlignmentRows()){const key=label(row.target)+'|'+row.criterion;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}return [...groups.values()];}
function alignmentDraft(row){return alignmentEditDrafts.get(chatKey()+'|'+row.key)||{assessment:row.assessment,note:row.human?.note||row.rationale,confirmed:row.confirmed,confidence:row.confidence_values};}
const alignmentReasoningDimensions={'logical-rigor':'Logical rigor','material-coverage':'Material coverage','evidence-quality':'Evidence quality',applicability:'Applicability','independent-patterns':'Independent patterns',counterevidence:'Counterevidence'};
const alignmentDimensionJudgments={adequate:'Adequate',limited:'Limited',missing:'Missing',contradicted:'Contradicted','not-applicable':'Not applicable'};
function alignmentUsesCommon(row){return row.confidence_values?.framework==='evidence-reasoning-v1'||row.confidence?.framework==='evidence-reasoning-v1';}
function alignmentConfidenceLabel(level){return typeof confidenceLabel==='function'?confidenceLabel(level):({'not-rated':'Not rated',low:'Low',moderate:'Moderate',high:'High'})[level]||'Not rated';}
function alignmentConfidenceCaption(row,historical=false){
 if(!alignmentUsesCommon(row))return `Legacy evidence-v1 · ${row.confidence.score}/100 · Historical rubric`;
 return `${historical||!row.current?'Earlier confidence':'Confidence'}: ${alignmentConfidenceLabel(row.confidence.level)} · ${row.assessor_type==='human'?'Author judgment':row.mode==='simulated'?'Scripted example':'Model proposal'}`;
}
function alignmentPassageRead(citation){
 const match=String(citation.source||'').match(/^(.*):v(\d+)$/),raw=citation.ref||match&&{id:match[1],revision:Number(match[2])};
 return `<blockquote>${esc(citation.quote||'Assessed PDF page '+citation.page)}</blockquote><p class="caption">${raw?esc(referenceText(raw)):'Selected source passage'}${citation.page?' · Page '+esc(citation.page):''}</p>${raw?sourceDetails(raw):''}`;
}
const alignmentPatternStatuses={unknown:'Unknown','single-line':'Single evidence line','recurring-with-limits':'Recurring within limits','independently-corroborated':'Independently corroborated',contested:'Contested','not-applicable':'Not applicable'};
function alignmentPatternFields(row,values){
 const patterns=values.patterns;if(!patterns)return '<p class="caption">This older assessment did not record a structured pattern basis.</p>';
 return `<details class="alignment-pattern-basis"><summary>Pattern basis · ${esc(alignmentPatternStatuses[patterns.status]||patterns.status)}</summary><label><span>Pattern judgment</span><select name="confidence_pattern_status">${Object.entries(alignmentPatternStatuses).map(([key,label])=>`<option value="${key}" ${patterns.status===key?'selected':''}>${label}</option>`).join('')}</select></label>${[['recurrence','Recurrence'],['exceptions','Exceptions and counterexamples'],['population_limits','Population limits']].map(([key,title])=>`<label><span>${title}</span><textarea name="confidence_pattern_${key}" maxlength="1200" required>${esc(patterns[key])}</textarea></label>`).join('')}${patterns.families.map((family,index)=>`<details><summary>Evidence family ${index+1}</summary><label><span>Relationship to other evidence</span><select name="confidence_family_${index}_relationship">${[['independent','Independent'],['same-underlying-basis','Same underlying basis'],['unknown','Unknown']].map(([key,title])=>`<option value="${key}" ${family.relationship===key?'selected':''}>${title}</option>`).join('')}</select></label><label><span>Reason for this relationship</span><textarea name="confidence_family_${index}_rationale" maxlength="1200" required>${esc(family.rationale)}</textarea></label>${(row.confidence.patterns?.families?.[index]?.citations||[]).map(alignmentPassageRead).join('')}</details>`).join('')}<p class="caption">Source relationships are reviewable judgments. Repeated passages or a family count do not establish independence.</p></details>`;
}
function alignmentConfidenceFields(row,edit){
 const values=edit.confidence;
 if(!alignmentUsesCommon(row))return `<details class="alignment-confidence-basis"><summary>Legacy confidence basis</summary><p class="caption">Legacy evidence-v1 · ${row.confidence.score}/100. This historical rubric is preserved; it has not been converted to the current confidence framework. Request a new review to assess current confidence.</p><p class="caption">${esc(row.confidence.basis||'')}</p></details>`;
 return `<details class="alignment-confidence-basis"><summary>Confidence basis</summary><p class="caption">A scoped judgment under the recorded reasoning standard, separate from project approval.</p><label><span>Confidence</span><select name="confidence_level">${['not-rated','low','moderate','high'].map(level=>`<option value="${level}" ${values.level===level?'selected':''}>${esc(alignmentConfidenceLabel(level))}</option>`).join('')}</select></label>${[['claim','Claim being assessed'],['scope','Scope'],['rationale','Reason for confidence'],['limits','Limits and unknowns']].map(([key,title])=>`<label><span>${title}</span><textarea name="confidence_${key}" maxlength="${key==='claim'?800:key==='scope'?1000:1200}" required>${esc(values[key]||'')}</textarea></label>`).join('')}<div class="alignment-confidence-grid">${Object.entries(alignmentReasoningDimensions).map(([key,title])=>{const dimension=values.dimensions[key],recorded=row.confidence.dimensions?.[key];return `<details><summary>${title} · ${esc(alignmentDimensionJudgments[dimension.judgment]||dimension.judgment)}</summary><label><span>Judgment</span><select name="confidence_${key}">${Object.entries(alignmentDimensionJudgments).map(([value,label])=>`<option value="${value}" ${dimension.judgment===value?'selected':''}>${label}</option>`).join('')}</select></label><label><span>Reason</span><textarea name="confidence_${key}_rationale" maxlength="1200" required>${esc(dimension.rationale)}</textarea></label><label><span>Limits</span><textarea name="confidence_${key}_limits" maxlength="1200" required>${esc(dimension.limits)}</textarea></label>${recorded?.citations?.length?`<details><summary>Supporting passages</summary>${recorded.citations.map(alignmentPassageRead).join('')}</details>`:'<p class="caption">No source passage is selected for this dimension.</p>'}</details>`;}).join('')}</div><p class="caption">These judgments retain the exact evidence selected in this review. Request a new review to assess additional sources.</p>${alignmentPatternFields(row,values)}${sourceDetails(values.standard)}</details>`;
}
function chatAlignmentPanel(){const groups=chatAlignmentGroups();return `<aside id="domain-alignment-panel" class="domain-context-panel alignment-panel" aria-label="Alignment"><header class="domain-panel-header"><h2>Alignment</h2><button type="button" class="quiet icon" data-action="dchat-panel-close" aria-label="Close alignment">✕</button></header><div class="domain-context-body"><p class="caption">Working assessments. Unlisted items have not been assessed; project approval is separate.</p>${groups.map(([row,...history])=>{const edit=alignmentDraft(row);return `<details class="alignment-row" data-chat-disclosure="alignment:${esc(row.key)}" ${chatDisclosure('alignment:'+row.key)}><summary><span class="alignment-item-title">${esc(row.title)}</span><span class="alignment-item-status">${esc(alignmentStatusLabels[row.assessment])} · ${row.current?row.confirmed?'Reviewed by '+esc(state.actors?.[row.human.owner]?.name||'Author'):'Needs your review':'Earlier basis'}</span><span class="alignment-score">${esc(alignmentConfidenceCaption(row))}</span></summary><div class="alignment-row-body">${row.criterion?`<h4>Acceptance criterion</h4><blockquote>${esc(row.criterion)}</blockquote>`:''}<p>${esc(row.human?.note||row.rationale)}</p>${row.gaps.length?`<h4>What would strengthen this</h4><ul>${row.gaps.map(g=>`<li>${esc(g)}</li>`).join('')}</ul>`:''}<button type="button" class="compact-text-action" data-action="dchat-alignment-gaps" data-id="${esc(row.key)}">Explore next steps</button><details><summary>Evidence & scope</summary><p class="caption">${esc(referenceText(row.target))} · ${esc(date(row.at))} · ${esc(chatBatchName(row.batch))}</p>${row.evidence.map(alignmentPassageRead).join('')||'<p class="caption">No cited evidence. This has not been demonstrated.</p>'}${!alignmentUsesCommon(row)&&row.confidence.participant_count===1?'<p>One reported participant limits generalization. Confirm the sample and investigate how widely the issue occurs.</p>':''}</details>${row.current?`<details class="alignment-human-review"><summary>${row.human?'Edit assessment':'Review assessment'}</summary><form data-alignment-editor="${esc(row.key)}"><label><span>Assessment</span><select name="assessment">${Object.entries(alignmentStatusLabels).map(([key,title])=>`<option value="${key}" ${edit.assessment===key?'selected':''}>${title}</option>`).join('')}</select></label><label><span>Rationale or refinement</span><textarea name="note" maxlength="2000" required>${esc(edit.note)}</textarea></label>${alignmentConfidenceFields(row,edit)}<label class="checkbox"><input type="checkbox" name="confirmed" ${edit.confirmed?'checked':''}><span>Confirm this working assessment</span></label><button type="submit" class="small">Save assessment</button></form></details>`:'<p class="banner signal-notice signal-advisory">The assessed work or context changed. Review the current work before confirming.</p>'}${history.length?`<details><summary>Earlier assessments (${history.length})</summary>${history.map(h=>`<p>${esc(alignmentStatusLabels[h.assessment])} · ${esc(alignmentConfidenceCaption(h,true))} · ${esc(date(h.at))}${h.human?' · Human assessment retained':''}</p>${para(h.human?.note||h.rationale)}`).join('')}</details>`:''}</div></details>`;}).join('')}</div></aside>`;}
function alignmentFormValues(form){
 const fd=new FormData(form),row=chatAlignmentRows().find(r=>r.key===form.dataset.alignmentEditor),original=row?alignmentDraft(row).confidence:null;if(!original)throw Error('Reopen the recorded assessment before saving.');
 const confidence=alignmentUsesCommon(row)?{...original,level:fd.get('confidence_level'),claim:fd.get('confidence_claim'),scope:fd.get('confidence_scope'),rationale:fd.get('confidence_rationale'),limits:fd.get('confidence_limits'),patterns:original.patterns?{...original.patterns,status:fd.get('confidence_pattern_status'),recurrence:fd.get('confidence_pattern_recurrence'),exceptions:fd.get('confidence_pattern_exceptions'),population_limits:fd.get('confidence_pattern_population_limits'),families:original.patterns.families.map((family,index)=>({...family,relationship:fd.get('confidence_family_'+index+'_relationship'),rationale:fd.get('confidence_family_'+index+'_rationale')}))}:undefined,dimensions:Object.fromEntries(Object.keys(alignmentReasoningDimensions).map(key=>[key,{...original.dimensions[key],judgment:fd.get('confidence_'+key),rationale:fd.get('confidence_'+key+'_rationale'),limits:fd.get('confidence_'+key+'_limits')}]))}:original;
 return {assessment:fd.get('assessment'),note:fd.get('note'),confirmed:fd.get('confirmed')==='on',confidence};
}
async function saveAlignmentForm(form){const row=chatAlignmentRows().find(r=>r.key===form.dataset.alignmentEditor);if(!row)return;const key=chatKey()+'|'+row.key,values=alignmentFormValues(form);alignmentEditDrafts.set(key,values);try{await command('domain-alignment-save',{conversation:chatThread().ref,review:row.review,index:row.index,expected:row.edit_ref,...values});await load();alignmentEditDrafts.delete(key);renderDomainChat();toast('Working assessment saved.');}catch(error){toast(error.message);}}
document.addEventListener('submit',e=>{if(e.target.matches?.('[data-alignment-editor]')){e.preventDefault();saveAlignmentForm(e.target);}});
for(const event of ['input','change'])document.addEventListener(event,e=>{const form=e.target.closest?.('[data-alignment-editor]');if(form)alignmentEditDrafts.set(chatKey()+'|'+form.dataset.alignmentEditor,alignmentFormValues(form));});
function domainChatScreen(){let panel=domainPanel();if(panel==='context'){chatOpenBriefInputs();domainPanels.set(chatKey(),null);panel=null;}if(typeof cockpitRail==='function')return `${chatHeader()}${cockpitHud()}<div class="cockpit"><div class="cockpit-main">${chatBriefStack()}<div class="domain-chat-layout domain-working-layout${panel?' has-panel':''}"${panel?domainSplitStyle(panel):''}>${chatConversation()}${panel?domainSplitHandle(panel):''}${panel==='alignment'?chatAlignmentPanel():panel==='sharing'?workingReportEditor():panel==='developer-brief'&&typeof developerBriefPanel==='function'?developerBriefPanel():panel==='implications'?projectImplicationsPanel():typeof cockpitPanel==='function'?cockpitPanel(panel):''}</div></div>${chatWorkspaceActions()}</div>`;
 return `${chatHeader()}${chatBriefStack()}${chatWorkspaceActions()}<div class="domain-chat-layout domain-working-layout${panel?' has-panel':''}"${panel?domainSplitStyle(panel):''}>${chatConversation()}${panel?domainSplitHandle(panel):''}${panel==='alignment'?chatAlignmentPanel():panel==='sharing'?workingReportEditor():panel==='developer-brief'&&typeof developerBriefPanel==='function'?developerBriefPanel():panel==='implications'?projectImplicationsPanel():typeof cockpitPanel==='function'?cockpitPanel(panel):''}</div>`;}
async function chatChooseSource(raw,mode){await chatEnsure();await command('domain-chat-focus',{conversation:chatThread().ref,source:raw,...(mode?{mode}:{})});await load();}
async function chatEnsure(){
 let thread=chatThread();
 if(!thread){
  const session=chatSession(),selection=selected,oldKey=chatKey(),working=chatDraft();
  const out=await command('domain-chat-start',chatWork()?{draft:chatWork().ref}:{});
  if(chatSession()!==session||selected!==selection)throw Error('The workspace changed. Reopen the original workbench to continue.');
  await load();
  if(chatSession()!==session||selected!==selection)throw Error('The workspace changed. Reopen the original workbench to continue.');
  selected=out.id;domainChatDrafts.set(chatKey(),working);
  if(domainPanels.has(oldKey))domainPanels.set(chatKey(),domainPanels.get(oldKey));
  if(oldKey!==chatKey())domainChatDrafts.delete(oldKey);thread=chatThread();
 }
 return thread;
}
function renderDomainChat(){
 const input=document.getElementById('domain-chat-message'),focused=!!input&&document.activeElement===input,key=chatKey(),start=input?.selectionStart,end=input?.selectionEnd;
 render();
 if(focused&&chatKey()===key){const next=document.getElementById('domain-chat-message');next?.focus({preventScroll:true});if(Number.isInteger(start)&&Number.isInteger(end))next?.setSelectionRange?.(start,end);}
}
function mountDomainChat(){mountDomainSplit();const el=document.getElementById('chat-messages');if(el)el.scrollTop=domainChatPreview?0:el.scrollHeight;}
function chatScrollLatest(){const el=document.getElementById('chat-messages');if(el)el.scrollTop=el.scrollHeight;}
function chatStatus(message){const el=document.getElementById('domain-chat-status');if(el)el.textContent=message;}
function chatSession(){return [state.project.id,state.project.version,state.actor,state.domains?.active,state.auth?.account?.id||'development'].join('|');}
function chatRequestBasis(){const work=chatWork(),thread=chatThread();return JSON.stringify({requirements:work?.body.requirement_refs||[],inputs:work?.body.input_refs||[],source:thread?.body.focus_source,mode:thread?.body.review_mode});}
async function chatSend(event){
 event.preventDefault();if(busy||domainChatSending||chatThread()?.body.pending||chatModelUnavailable())return;
 const session=chatSession(),working=chatDraft(),question=working.text.trim(),revision=working.revision||0,file=working.file,purpose=working.purpose||(file||domainChatOnlyRemaining?'review':'explore');
 if(!question&&!file)return;
 const sameScope=()=>chatSession()===session&&domainChatDrafts.get(chatKey())===working;
 let briefDevelopment=working.briefDevelopment===true,assessmentCard=working.assessmentCard;
 const sending={session,working};domainChatSending=sending;busy=true;domainChatPause=false;domainChatPreview=null;renderDomainChat();chatStatus(file?'Saving your file…':'Preparing project context…');
 try{
  if(typeof saveWorkingReport==='function')await saveWorkingReport();
  if(!sameScope())throw Error('The workspace changed. Reopen the original workbench to continue.');
  let thread=await chatEnsure();
  if(!sameScope())throw Error('The workspace changed. Reopen the original workbench to continue.');
  if(file){
   const content=await visualFileContentForChat(file);
   if(!sameScope())throw Error('The workspace changed. The file was not sent to another workbench.');
   await command('domain-chat-attach',{conversation:thread.ref,expected:chatWork().ref,filename:file.name,content});
   if(working.file===file)working.file=null;
   await load();if(!sameScope())throw Error('The workspace changed. Reopen the original workbench to see its result.');thread=chatThread();
  }
  const basis=chatRequestBasis(),plan=purpose==='review'?thread.plan:thread.plan.slice(0,1),group=crypto.randomUUID(),onlyRemaining=domainChatOnlyRemaining,covered=new Set(chatInfo().reports.filter(r=>(r.selection_current??r.current)&&r.body.conversation===thread.ref.id&&JSON.stringify(r.body.source)===JSON.stringify(thread.body.focus_source)).map(r=>JSON.stringify(r.body.batch)));
  domainChatOnlyRemaining=false;if((working.revision||0)===revision)working.text='';if(typeof domainWorkMode!=='undefined')domainWorkMode='conversation';
  for(let i=0;i<plan.length;i++){
   if(onlyRemaining&&covered.has(JSON.stringify(plan[i])))continue;
   if(!sameScope())throw Error('The account, role, project or chat changed. The earlier review remains in its original workbench.');
   if(chatRequestBasis()!==basis)throw Error('Review inputs changed. Earlier results are retained; review the selected context before continuing.');
   thread=chatThread();renderDomainChat();chatStatus(purpose==='prepare-sharing'?'Preparing a private sharing draft…':purpose==='review'?`Reviewing ${chatBatchName(plan[i]).toLowerCase()} · part ${i+1} of ${plan.length}…`:'Thinking…');
   const result=await command('domain-chat-send',{conversation:thread.ref,expected:chatWork().ref,message:question,consent:true,request_id:group+':'+i,batch:i,purpose,brief_development:briefDevelopment,card_assessment:assessmentCard});
   await load();if(!sameScope())throw Error('The account, role, project or chat changed. Reopen the original workbench to see its result.');domainChatReportId=result.chatReport||domainChatReportId;renderDomainChat();chatScrollLatest();
   if(result.chat_error){if(assessmentCard&&(working.revision||0)===revision)working.text=question;chatStatus('');break;}
   if((working.revision||0)===revision){delete working.briefDevelopment;delete working.assessmentCard;delete working.assessmentTitle;}
   briefDevelopment=false;assessmentCard=undefined;
   if(domainChatPause){chatStatus(`Paused after part ${i+1} of ${plan.length}. Completed feedback is saved.`);break;}
   chatStatus(i+1===plan.length?result.findings_updated?'Sharing draft prepared.':'Reply saved.':'Continuing to the next part…');
  }
 }catch(error){
  if((working.revision||0)===revision)working.text=question;
  if(sameScope()){await load().catch(()=>{});renderDomainChat();chatStatus(error.message);toast(error.message);}
 }finally{
  if(domainChatSending===sending){domainChatSending=null;busy=false;}if((working.revision||0)===revision)working.purpose='explore';
  const status=sameScope()?document.getElementById('domain-chat-status')?.textContent:null;renderDomainChat();
  if(sameScope()){if(status)chatStatus(status);chatScrollLatest();document.querySelector('#domain-chat-message')?.focus();}
 }
}
async function visualFileContentForChat(file){if(!file?.size||file.size>5*1024*1024)throw Error('Choose a supported file under 5 MB.');return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Could not read this file.'));reader.readAsDataURL(file);});}
async function domainChatAction(action,id){
 if(typeof action!=='string'||!action.startsWith('dchat-'))return false;
 if(action==='dchat-guidance-context'||action==='dchat-guidance-plan'){
  domainChatDisclosures.set(chatKey()+'|working-brief',true);
  if(action==='dchat-guidance-context')chatOpenBriefInputs();
  // Open the existing disclosure in place, preserving unsaved editors and chat.
  const brief=document.getElementById('domain-working-brief'),inputs=document.getElementById('domain-brief-inputs');
  if(brief){brief.open=true;if(inputs&&action==='dchat-guidance-context')inputs.open=true;brief.querySelector?.('summary')?.focus();brief.scrollIntoView?.({block:'nearest'});}
 }
 if(action==='dchat-clear-card-assessment'){delete chatDraft().assessmentCard;delete chatDraft().assessmentTitle;renderDomainChat();}
 if(action==='dchat-alignment-panel'){await saveWorkingReport();domainPanels.set(chatKey(),domainPanel()==='alignment'?null:'alignment');renderDomainChat();}
 if(action==='dchat-alignment-gaps'){const row=chatAlignmentRows().find(r=>r.key===id);if(!row)return true;if(chatDraft().text.trim()){toast('Send or clear the current message first.');return true;}chatDraft().text='Help me strengthen '+row.title+'. '+row.gaps.join(' ')+' What should I do next? If more interviews would help, draft questions for my discussion guide.';chatDraft().purpose='explore';renderDomainChat();document.getElementById('domain-chat-message')?.focus();}
 if(action==='dchat-context-panel'){await saveWorkingReport();chatOpenBriefInputs();renderDomainChat();}
 if(action==='dchat-sharing-panel'){await saveWorkingReport();domainPanels.set(chatKey(),domainPanel()==='sharing'?null:'sharing');renderDomainChat();}
 if(action==='dchat-panel-close'){await saveWorkingReport();domainPanels.set(chatKey(),null);renderDomainChat();}
 if(action==='dchat-refresh-scope'){await saveWorkingReport();await chatEnsure();await command('domain-chat-context',{conversation:chatThread().ref,expected:chatWork().ref,requirement_ids:chatWork().body.requirement_refs.map(r=>r.id),input_refs:chatWork().body.input_refs||[]});await load();chatOpenBriefInputs();renderDomainChat();toast('Review scope updated. Existing work is retained.');}

 if(action==='dchat-clear-brief-focus'){delete chatDraft().briefDevelopment;renderDomainChat();}
 if(action==='dchat-brief-coach'){chatDraft().briefDevelopment=true;chatDraft().purpose='explore';const node=document.getElementById('domain-chat-message');if(node)chatDraft().text=node.value;if(!chatDraft().text)chatDraft().text='Help me refine the brief’s objectives, approach and evaluation criteria using the accepted inputs and domain guidance.';renderDomainChat();document.getElementById('domain-chat-message')?.focus();}
 if(action==='dchat-review-work'){delete chatDraft().briefDevelopment;if(chatContextChanged())chatOpenBriefInputs();if(!chatDraft().text)chatDraft().text='Review this work against the project goals, requirements, acceptance criteria and applicable domain guidance. What is supported, what challenges the current direction, and what needs evidence or a human decision?';chatDraft().purpose='review';renderDomainChat();document.getElementById('domain-chat-message')?.focus();}
 if(action==='dchat-draft-sharing'){if(chatDraft().text.trim()||chatDraft().file){toast('Send or clear the current message before drafting for sharing.');return true;}chatDraft().purpose='prepare-sharing';chatDraft().text='Prepare an editable sharing draft from this discussion and the selected work. State the learning, its source and limits, what it supports or challenges in the project, and proposed requirement, acceptance-criteria or goal changes and open decisions. Preserve contradictory evidence. Include only the selected, supported substance; private conversation must remain private. This prepares a draft only.';await chatSend({preventDefault(){}});}
 if(action==='dchat-rail'){if(id==='report')await openWorkbenchReport(chatWork()?.ref.id);else{domainChatRail='requirements';renderDomainChat();}}
 if(action==='dchat-open'){await chatOpenWork(id);renderDomainChat();}
 if(action==='dchat-new'){if(typeof saveBeforeProjectChange==='function')await saveBeforeProjectChange();else await saveWorkingReport();const out=await command('domain-chat-start',{});await load();await chatOpenWork(out.id);renderDomainChat();}
 if(action==='dchat-nav-source'){const [workId,sourceId]=id.split('|'),work=chatWorks().find(r=>r.ref.id===workId),raw=work?.body.source_refs.find(r=>r.id===sourceId);if(!raw)throw Error('This file is unavailable in the selected chat.');await chatOpenWork(workId);await chatChooseSource(raw);domainChatPreview={source:raw,page:chatSource(raw)?.body.visual_pdf?1:null};renderDomainChat();}
 if(action==='dchat-file')document.getElementById('domain-chat-file').click();
 if(action==='dchat-remove-file'){chatDraft().file=null;renderDomainChat();}
 if(action==='dchat-report'){domainChatReportId=id;modal('Review details',chatReportView(id),null,null,{className:'settings-dialog review-details-dialog'});}
 if(action==='dchat-sharing-open'){await saveWorkingReport();domainPanels.set(chatKey(),'sharing');renderDomainChat();document.getElementById('domain-sharing-panel')?.scrollIntoView({block:'nearest'});return true;}
 if(action==='dchat-panel-none'){await saveWorkingReport();domainPanels.set(chatKey(),null);renderDomainChat();return true;}
 if(action==='dchat-turn-block'){if(busy)return true;const [key,mode]=String(id).split('|'),turn=chatInfo().turns.find(t=>label(t.ref)===key);if(!turn||turn.body.role!=='assistant')throw Error('This reply is no longer available.');await useThoughtPassage({turn:turn.ref,text:turn.body.message,key:chatKey()},mode==='add'?'card-add':'card-new');return true;}
 if(action==='dchat-retry'){if(chatModelUnavailable())return true;const prior=chatInfo().turns.find(t=>t.body.conversation===chatThread()?.ref.id&&['user','batch'].includes(t.body.role)&&t.body.request_id===id);if(!chatDraft().text)chatDraft().text=prior?.body.message||'Review the current file against the displayed context.';chatDraft().purpose=prior?.body.purpose||'review';chatDraft().briefDevelopment=prior?.body.brief_development===true;domainChatOnlyRemaining=true;await chatSend({preventDefault(){}});}
 if(action==='dchat-recover'){await command('domain-chat-recover',{conversation:chatThread().ref});await load();renderDomainChat();}
 if(action==='dchat-source'){const work=chatWork(),source=chatSource(work.body.source_refs.find(r=>r.id===id));await chatChooseSource(source.ref);domainChatPreview={source:source.ref,page:source.body.visual_pdf?1:null};renderDomainChat();}
 if(action==='dchat-locate'){
  const [reportId,index]=id.split('|'),report=chatReports().find(r=>r.ref.id===reportId),b=report.body,i=Number(index);
  domainChatPreview=b.format==='visual'?{source:b.source,page:b.output.findings[i].page}:b.locations[i];if(chatWork().body.source_refs.some(r=>label(r)===label(domainChatPreview.source)))await chatChooseSource(domainChatPreview.source);renderDomainChat();
 }
 if(action==='dchat-remaining'){const report=chatReports().find(r=>r.ref.id===id);if(report?.body.source)await chatChooseSource(report.body.source);domainChatOnlyRemaining=true;if(!chatDraft().text)chatDraft().text='Continue reviewing the remaining parts against the selected project context.';await chatSend({preventDefault(){}});}
 if(action==='dchat-apply'){const [reportId,index]=id.split('|'),r=chatReports().find(r=>r.ref.id===reportId),text=document.getElementById('chat-edit-'+index).value;await command('domain-chat-apply',{conversation:chatThread().ref,expected:chatWork().ref,report:r.ref,index:Number(index),text,confirm:true});await load();renderDomainChat();toast('Draft wording saved.');}
 return true;
}
document.addEventListener('input',e=>{if(e.target.id==='domain-chat-message'){const draft=chatDraft();draft.text=e.target.value;draft.revision=(draft.revision||0)+1;}});
document.addEventListener('submit',e=>{if(e.target.id==='domain-chat-composer')chatSend(e);if(e.target.id==='domain-chat-context'){e.preventDefault();(async()=>{try{const fd=new FormData(e.target);await chatEnsure();await command('domain-chat-context',{conversation:chatThread().ref,expected:chatWork().ref,requirement_ids:fd.getAll('requirement'),input_refs:fd.getAll('upstream').map(value=>domainInputOptions(chatWork().body).find(r=>label(r.ref)===value).ref)});await load();renderDomainChat();toast('Review context saved.');}catch(error){toast(error.message);}})();}});
document.addEventListener('change',e=>{
 if(e.target.id==='domain-chat-file'){chatDraft().file=e.target.files[0]||null;renderDomainChat();}
 if(e.target.id==='chat-review-mode'){const source=chatWork().body.source_refs.find(r=>r.id===e.target.dataset.source);chatChooseSource(source,e.target.value).then(()=>render()).catch(error=>toast(error.message));}
 if(e.target.id==='domain-chat-report'){domainChatReportId=e.target.value;renderDomainChat();}
 if(e.target.id==='chat-preview-page'){domainChatPreview={source:chatWork().body.source_refs.find(r=>r.id===e.target.dataset.source),page:Number(e.target.value)};renderDomainChat();}
});
document.addEventListener('click',e=>{if(e.target.closest('#domain-chat-pause')){domainChatPause=true;chatStatus('Pausing after the current part finishes…');}});

document.addEventListener('toggle',e=>{if(e.target.isConnected!==false&&e.target.hasAttribute?.('data-domain-chat-navigation'))domainChatNavOpen.set(chatSession(),e.target.open);if(e.target.isConnected!==false&&e.target.dataset?.chatFiles)domainChatNavFiles.set(chatSession()+'|'+e.target.dataset.chatFiles,e.target.open);if(e.target.isConnected!==false&&e.target.dataset?.chatEarlier)domainChatNavEarlier.set(e.target.dataset.chatEarlier,e.target.open);const key=e.target.dataset?.chatDisclosure;if(key&&e.target.isConnected)domainChatDisclosures.set(chatKey()+'|'+key,e.target.open);},true);

// A personal layout preference only; no project content or workflow is changed.
const domainSplitPreferences=new Map();
let domainSplitDrag=null;
function domainSplitKey(){return 'workbench-domain-split:v1:'+encodeURIComponent(state.auth?.account?.id||'development')+':'+encodeURIComponent(state.actor);}
function domainSplitPreference(){
 const key=domainSplitKey();if(domainSplitPreferences.has(key))return domainSplitPreferences.get(key);
 let value=null;try{const raw=localStorage.getItem(key),n=Number(raw);if(raw!==null&&Number.isFinite(n)&&n>=30&&n<=75)value=n;}catch{}
 domainSplitPreferences.set(key,value);return value;
}
function domainSplitValue(panel){return domainSplitPreference()??(panel==='sharing'?43:65);}
function domainSplitStyle(panel){const n=domainSplitValue(panel);return ` style="--domain-main:${n}fr;--domain-side:${100-n}fr"`;}
function domainSplitHandle(panel){const n=domainSplitValue(panel);return `<div class="domain-panel-resize" role="separator" tabindex="0" aria-label="Resize AI partner and sidecar" aria-orientation="vertical" aria-valuemin="30" aria-valuemax="75" aria-valuenow="${n}" aria-valuetext="AI partner ${n} percent" data-default-split="${panel==='sharing'?43:65}" title="Drag to resize · double-click to reset"><span aria-hidden="true"></span><span class="sr-only">Use left and right arrows to resize. Double-click to reset.</span></div>`;}
function domainSplitBounds(handle){
 const box=handle.parentElement.getBoundingClientRect(),width=Math.max(1,box.width-24);
 return {box,width,min:Math.max(30,Math.min(50,320/width*100)),max:Math.min(75,Math.max(50,100-300/width*100))};
}
function domainSplitApply(handle,value){
 const bounds=domainSplitBounds(handle),n=Math.round(Math.max(bounds.min,Math.min(bounds.max,value))*10)/10;
 handle.parentElement.style.setProperty('--domain-main',n+'fr');handle.parentElement.style.setProperty('--domain-side',(100-n)+'fr');
 handle.setAttribute('aria-valuenow',String(n));handle.setAttribute('aria-valuemin',String(Math.ceil(bounds.min)));handle.setAttribute('aria-valuemax',String(Math.floor(bounds.max)));handle.setAttribute('aria-valuetext','AI partner '+Math.round(n)+' percent');return n;
}
function domainSplitSave(value){const key=domainSplitKey();domainSplitPreferences.set(key,value);try{localStorage.setItem(key,String(value));}catch{}}
function mountDomainSplit(){const handle=document.querySelector('.domain-panel-resize');if(handle)domainSplitApply(handle,domainSplitPreference()??Number(handle.dataset.defaultSplit));}
function domainSplitFinish(commit){
 const drag=domainSplitDrag;if(!drag)return;domainSplitDrag=null;document.body.classList.remove('domain-panel-resizing');
 if(drag.handle.isConnected!==false){if(commit)domainSplitSave(Number(drag.handle.getAttribute('aria-valuenow')));else domainSplitApply(drag.handle,drag.original);}
 try{drag.handle.releasePointerCapture?.(drag.pointer);}catch{}
}
document.addEventListener('pointerdown',e=>{
 const handle=e.target.closest?.('.domain-panel-resize');if(!handle||e.button!==0)return;
 const bounds=domainSplitBounds(handle);if(!bounds.box.width)return;e.preventDefault();handle.focus();
 domainSplitDrag={handle,pointer:e.pointerId,original:Number(handle.getAttribute('aria-valuenow'))};document.body.classList.add('domain-panel-resizing');
 try{handle.setPointerCapture?.(e.pointerId);}catch{}
});
document.addEventListener('pointermove',e=>{
 const drag=domainSplitDrag;if(!drag||drag.pointer!==e.pointerId)return;if(drag.handle.isConnected===false){domainSplitFinish(false);return;}
 const b=domainSplitBounds(drag.handle);e.preventDefault();domainSplitApply(drag.handle,(e.clientX-b.box.left-12)/b.width*100);
});
document.addEventListener('pointerup',e=>{if(domainSplitDrag?.pointer===e.pointerId)domainSplitFinish(true);});
document.addEventListener('pointercancel',e=>{if(domainSplitDrag?.pointer===e.pointerId)domainSplitFinish(false);});
document.addEventListener('keydown',e=>{
 if(e.key==='Escape'&&domainSplitDrag){e.preventDefault();domainSplitFinish(false);return;}
 const handle=e.target.closest?.('.domain-panel-resize');if(!handle)return;const b=domainSplitBounds(handle),old=Number(handle.getAttribute('aria-valuenow')),step=e.shiftKey?10:2;
 const n=e.key==='ArrowLeft'?old-step:e.key==='ArrowRight'?old+step:e.key==='Home'?b.min:e.key==='End'?b.max:null;
 if(n!==null){e.preventDefault();domainSplitSave(domainSplitApply(handle,n));}
});
document.addEventListener('dblclick',e=>{
 const handle=e.target.closest?.('.domain-panel-resize');if(!handle)return;e.preventDefault();domainSplitFinish(false);
 const key=domainSplitKey();domainSplitPreferences.set(key,null);try{localStorage.removeItem(key);}catch{}domainSplitApply(handle,Number(handle.dataset.defaultSplit));
});
if(typeof window!=='undefined'){
 window.addEventListener?.('resize',mountDomainSplit);
 window.addEventListener?.('blur',()=>domainSplitFinish(false));
}

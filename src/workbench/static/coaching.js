// UI sends task intent. The server-side agent owns context, skills and model prompts.
let coachedField='business_challenge', chosenSources=new Set(), sourcesOpen=false, coachingMessages={}, coachingWorking={};
const intakeReviewerDrafts=new Map();
function intakeReviewerKey(){return typeof reviewerDraftKey==='function'?reviewerDraftKey('intake-coach'):[state.auth?.account?.id||'',state.actor||'',state.project?.id||state.intake?.draft?.ref?.id||''].join('|');}
function intakeReviewerMessage(){return typeof reviewerDraftRead==='function'?reviewerDraftRead('intake-coach'):intakeReviewerDrafts.get(intakeReviewerKey())||'';}
function intakeReviewerWrite(text){if(typeof reviewerDraftWrite==='function')reviewerDraftWrite('intake-coach',text);else intakeReviewerDrafts.set(intakeReviewerKey(),String(text||''));}
let documentWork=null;
const valueGroups=[['Business rationale',['business_challenge','strategic_relevance','why_now']],['Value proposition',['beneficiaries','jobs','need','gains','approach','job_support','pain_relievers','gain_creators','value']],['Success measures',['measures','measure_review']]];
const contextGroups=[['People and flow',['supporting_users','user_situation','user_actions','bottlenecks','tools','handoffs','desired_outputs']],['Scope and dependencies',['work_kind','in_scope','out_scope','constraints','dependencies']],['Evidence and investigation',['evidence','sources','assumptions','assumption_owner','open_questions','research_question','operations_question']]];
function coachInfo(){return state.coaching||{sources:[],runs:[],guidance:{},model:{configured:false}};}

function questionExpert(k){return coachInfo().expertise?.[k]||{};}
function shortQuestion(k){return questionExpert(k).short_label||intakeNames[k];}
function questionGuide(k){const p=questionExpert(k);return `<p class="answer-hint" id="guide-${k}">${esc(p.hint||coachInfo().guidance[k]||'Describe what you know so far.')}</p>${p.starter?`<details class="answer-starter"><summary>Help me get started</summary><p class="caption">${p.answer_shape.map(esc).join(' · ')}</p><p>${esc(p.starter)}</p><small>Use this as a structure. Include only what is true for your initiative.</small></details>`:''}`;}
function questionConnections(k){const p=questionExpert(k),v=state.intake.draft.body.values,keys=(p.connections||[]).filter(x=>v[x]);return keys.length?`<details class="expert-connections"><summary>Answers this AI partner connects</summary>${keys.map(x=>val(intakeNames[x],v[x])).join('')}</details>`:'';}
function expertCoachIntro(k){const p=questionExpert(k);return `<div class="expert-focus"><strong>${esc(p.expert_role||'Business Intent AI partner')}</strong><p>${esc(p.quality_checks?.[0]||'Connect your answer to the purpose of this initiative.')}</p></div>`;}
function initiativeSelect(v){return `<div class="form-field"><label for="coached-kind">Your selection</label><select id="coached-kind" name="work_kind" aria-describedby="guide-work_kind">${[['digital','Digital product or system'],['operational','Operational improvement'],['market','Market or new venture'],['other','Other inquiry']].map(([id,t])=>`<option value="${id}" ${v.work_kind===id?'selected':''}>${t}</option>`).join('')}</select></div>`;}
function coachAdviceAge(run){return !matchingCoachSettings(run)||run.body.expertise_version!==coachInfo().expertise_version?'<p class="caption">Earlier AI partner advice · ask again to use the updated question guidance.</p>':!validRun(run)?'<p class="caption">Earlier advice · your answers have since changed.</p>':'';}
function focusIntakeQuestion(){const heading=$('.value-question-current h2')||$('.field-editor h2');if(heading){heading.setAttribute('tabindex','-1');heading.focus({preventScroll:true});}}
function selectedSourceRefs(){return coachInfo().sources.filter(s=>chosenSources.has(s.ref.id)).map(s=>s.ref);}
function fieldRun(k){return [...coachInfo().runs].reverse().find(r=>r.body.skill==='coach-field'&&r.body.field===k);}
function matchingCoachSettings(r){return !coachInfo().configuration_fingerprint||r.body.configuration_fingerprint===coachInfo().configuration_fingerprint||(!r.body.configuration_fingerprint&&!coachInfo().settings?.ref);}
function validRun(r){if(!matchingCoachSettings(r))return false;const expected={...r.body.values,...r.body.applied},v=state.intake.draft.body.values;return Object.keys(v).every(k=>v[k]===expected[k])&&Object.keys(expected).every(k=>v[k]===expected[k]);}
function coachAnswerBasis(run){
 const field=run.body.skill==='review-value'?'value':run.body.field;
 const answer=run.body.working_answer||{field,text:run.body.values[field]||'',basis:run.body.basis};
 return `<details class="section coach-answer-basis"><summary>Working answer sent with this request</summary>${para(answer.text||'No answer yet — help getting started requested.')}<p class="caption">${esc(intakeNames[answer.field])} · ${esc(label(answer.basis))}</p></details>`;
}
function citationsHtml(cs){return cs.length?`<details class="source-basis"><summary>Inspect source basis (${cs.length})</summary>${cs.map(c=>`<blockquote>${esc(c.quote)}<footer>${esc(c.source_title)} · ${esc(label(c.source_ref))}</footer></blockquote>`).join('')}<small>Quotation matched to stored text. The interpretation still needs your review.</small></details>`:'';}
function coachingProvenancePreview(body){const entries=Object.entries(body.field_provenance||{});return entries.length?`<details class="section"><summary>Source excerpts accompanying adopted wording</summary>${entries.map(([k,p])=>`<div class="rule"><strong>${esc(intakeNames[k])}</strong><p class="caption">${esc(p.status.replaceAll('-',' '))} · ${esc(p.basis)}</p>${val('Wording originally adopted',p.text)}${val('Why this wording',p.rationale)}${citationsHtml(p.citations)}</div>`).join('')}</details>`:'';}
function sourceDraftBasis(field){
 const p=state.intake.draft.body.field_provenance?.[field];
 if(!p||p.origin!=='drafted-from-sources')return '';
 return `<details class="source-draft-basis"><summary>${p.status==='ai-proposed-draft'?'AI draft from material':p.status==='sponsor-adopted-draft'?'Draft from material':'Edited draft'} · source basis</summary><p class="caption">${esc(p.rationale)}</p>${p.citations.map(c=>`<blockquote>${esc(c.quote)}<footer>${esc(c.source_title)}</footer></blockquote>`).join('')}<p class="caption">Source-informed wording for you to review and refine.</p></details>`;
}
function sourceDraftSummary(){
 if(typeof changeInfo==='function'&&(changeInfo().pending_sources.length||changeInfo().reviews.length))return '';
 const r=coachInfo().runs.filter(r=>r.body.skill==='seed-value').at(-1);if(!r)return '';
 const pending=r.body.output.suggestions.filter(s=>!Object.hasOwn(r.body.applied,s.field));
 return `<details class="source-draft-summary"><summary>Document proposals${pending.length?' · '+pending.length+' to review':''}</summary>${para(r.body.output.reply)}${pending.map(s=>coachSuggestion(r,s)).join('')}${r.body.output.questions.map(q=>`<div class="rule"><strong>${esc(shortQuestion(q.field))}</strong>${para(q.question)}</div>`).join('')}<p class="caption">${Object.keys(r.body.applied).length} answers used as drafts. Unsupported questions stay open.</p></details>`;
}
async function draftSourceAnswers(sources=selectedSourceRefs(),onPhase=()=>{}){
 const expected=state.intake.draft.ref;
 const r=await command('intake-coach',{expected,skill:'seed-value',field:coachedField,message:'Read the selected documents and draft supported answers across business rationale, value proposition, context and success measures. Keep the value statement concise and connect benefits to candidate measures.',sources,consent:true});
 if(pageDirty)throw Error('New edits arrived while drafting. They are preserved; save them before reviewing the document proposals.');
 onPhase('applying');
 const result=await command('intake-coach-fill-empty',{expected,run_id:r.ref.id,confirm:true});
 if(result.filled?.length)sourcesOpen=false;
 const first=result.filled?.find(k=>k!=='value');if(first){valueFocus=first;coachedField=first;valueCoachMode='question';}
 return result;
}
function coachSuggestion(r,s){const used=Object.hasOwn(r.body.applied,s.field);return `<article class="coach-suggestion ac-suggestion${used?' is-edited':''}">${typeof acSuggestionHead==='function'?acSuggestionHead(s.basis==='source-supported'?'From your AI partner, informed by your sources':'From your AI partner · a hypothesis to test',used?'used':'suggested'):''}<div class="card-head"><strong>${esc(intakeNames[s.field])}</strong></div>${para(s.text)}<p class="caption">${esc(s.rationale)}</p>${citationsHtml(s.citations)}${used?'':button(validRun(r)?'Use this wording':'Review against current draft','coach-apply',r.ref.id+'|'+s.field,'small')}${!used&&!validRun(r)?'<p class="caption">The intake has changed. Request fresh advice before using this suggestion.</p>':''}</article>`;}
// One current response; supporting detail stays available on request.
function currentCoachAdvice(run){
 const c=coachInfo();
 return validRun(run)&&run.body.expertise_version===c.expertise_version&&run.body.agent_version===c.agent_version;
}
function coachWording(run,suggestion){
 const used=Object.hasOwn(run.body.applied,suggestion.field);
 return `<details class="coach-wording"><summary>${used?'Wording you used':'Suggested answer'}</summary><div class="coach-wording-body"><p class="caption">${suggestion.basis==='source-supported'?'Source-informed · check the interpretation':'Proposed wording · still a hypothesis'}</p>${para(suggestion.text)}${used?'':button('Review and use wording','coach-apply',run.ref.id+'|'+suggestion.field,'small')}${used?'<p class="caption">Already used in your draft.</p>':''}<p class="caption">${esc(suggestion.rationale)}</p>${citationsHtml(suggestion.citations)}</div></details>`;
}
function coachHistory(runs){
 return runs.length?`<details class="coach-secondary coach-history"><summary>Earlier feedback (${runs.length})</summary>${[...runs].reverse().map(r=>`<article class="coach-history-entry"><p class="caption">${esc(date(r.body.at))}${currentCoachAdvice(r)?'':' · Earlier answers or guidance'}</p>${r.body.user_message?val('You',r.body.user_message):''}<p class="reviewer-speaker">AI partner</p>${para(r.body.output.reply)}${r.body.output.suggestions.map(s=>`<details><summary>Suggested answer · ${esc(shortQuestion(s.field))}</summary>${para(s.text)}${para(s.rationale)}${citationsHtml(s.citations)}</details>`).join('')}${r.body.output.questions.length?`<details><summary>Follow-up questions</summary>${r.body.output.questions.map(q=>`${para(q.question)}<p class="caption">${esc(q.reason)}</p>`).join('')}</details>`:''}${coachAnswerBasis(r)}${r.body.instructions?`<details class="settings-detail"><summary>AI partner configuration used</summary><p class="caption">${r.body.configuration?'Saved version '+r.body.configuration.revision:'Default configuration'}</p><pre class="settings-instructions">${esc(r.body.instructions)}</pre></details>`:''}</article>`).join('')}</details>`:'';
}
const responseReviewRequest='Evaluate the quality of my current response using the expertise for this question and the context of this initiative. Identify the most important strength or gap, and the single most useful improvement if needed. Offer revised wording only if it helps. If the response is already adequate, say so without inventing work.';
function focusCoachFeedback(){
 const heading=$('.coach-panel [data-current-coach]>summary')||$('.coach-panel h2');
 if(heading){heading.setAttribute('tabindex','-1');heading.focus({preventScroll:true});heading.scrollIntoView({block:'nearest'});}
}
function focusedCoachPanel({field,whole=false,formId,message,runs,valueStage=false}){
 const c=coachInfo(),last=runs.at(-1),current=last&&currentCoachAdvice(last)?last:null;
 const history=current?runs.slice(0,-1):runs,p=questionExpert(field),q=current?.body.output.questions[0];
 const connected=(p.connections||[]).filter(k=>state.intake.draft.body.values[k]);
 const questionLink=q&&q.field!==field&&(valueStage?valueQuestionKeys().includes(q.field):contextGroups.flatMap(g=>g[1]).includes(q.field))?button('Go to '+shortQuestion(q.field)+' →',valueStage?'value-focus':'coach-field',q.field,'quiet small'):'';
 return `<aside class="card intake-coach coach-panel ${valueStage?'value-coach':''}" aria-label="AI partner"><h2 class="thought-partner-title">AI partner</h2><div class="reviewer-scroll"><p class="coach-context">${whole?'Review the proposition · how the whole case fits together':esc(shortQuestion(field))}</p>${whole?button('← Back to this question','value-coach-mode','question','quiet small coach-return'):''}
 ${current?`<details class="coach-current" data-current-coach ${pageDirty?'':'open'}><summary>${pageDirty?'AI partner · before edits':'AI partner'}</summary><div class="coach-feedback">${para(current.body.output.reply)}</div>${current.body.output.suggestions.map(s=>coachWording(current,s)).join('')}${q?`<details class="coach-next coach-secondary"><summary>One question to consider</summary>${para(q.question)}${questionLink}</details>`:''}${current.body.output.questions.length>1?`<details class="coach-secondary"><summary>Other review questions</summary>${current.body.output.questions.slice(1).map(q=>`${para(q.question)}<p class="caption">${esc(q.reason)}</p>${valueStage?valueQuestionLink(q):''}`).join('')}</details>`:''}</details>`:`<div class="coach-start"><h3>A useful starting point</h3><p>${esc(p.quality_checks?.[0]||'Connect your answer to the purpose of this initiative.')}</p></div>`}

 ${!c.model.configured?`<p class="caption">Connect a model to ask your AI partner.</p>${button('Connect model','coach-setup','','small')}`:''}
 <details class="coach-secondary"><summary>Context and sources</summary><p class="caption">AI partner configuration: ${c.settings?.ref?'version '+esc(c.settings.ref.revision):'default'}. Applies to your next request.</p><p class="caption">${esc(p.expert_role||'Business Intent AI partner')}. Uses the full intake, your current answer, selected material and recent conversation. Advice does not change your draft until you choose to use it.</p>${connected.map(k=>val(shortQuestion(k),state.intake.draft.body.values[k])).join('')}<p class="caption">${chosenSources.size} selected source${chosenSources.size===1?'':'s'}.</p>${q?`<h3>Why this follow-up?</h3><p class="caption">${esc(q.reason)}</p>`:''}${current?coachAnswerBasis(current):''}</details>${coachHistory(history)}</div><form id="${formId}" class="coach-ask reviewer-composer"><div class="error" role="alert"></div><label for="${formId==='coach-message-form'?'coach-message':formId+'-message'}">You</label><textarea id="${formId==='coach-message-form'?'coach-message':formId+'-message'}" name="message" rows="5" maxlength="20000" class="integrity-review-input" data-reviewer-draft="intake-coach" data-reviewer-scope="" aria-label="Ask your AI partner" placeholder="Ask your AI partner">${esc(intakeReviewerMessage())}</textarea><button type="submit" class="primary" ${c.model.configured?'':'disabled'}>Ask</button><p class="coach-sharing">Your answers and selected material go to the configured model.</p></form></aside>`;
}
function markCoachEdits(e){
 if(!e.target.closest('#value-proposition-form,#coached-field-form'))return;
 const feedback=document.querySelector('[data-current-coach]');
 if(feedback){feedback.open=false;feedback.querySelector(':scope>summary').textContent='Feedback before these edits';}
}
document.addEventListener('input',markCoachEdits);
document.addEventListener('change',markCoachEdits);

function documentWorkVisible(){return documentWork&&documentWork.draftId===state.intake.draft.ref.id&&coachInfo().sources.some(s=>s.ref.id===documentWork.source.id);}
function documentStatus(){
 if(!documentWorkVisible())return '';
 const w=documentWork,working=['reading','applying'].includes(w.phase);
 const seconds=Math.max(0,Math.floor((Date.now()-w.startedAt)/1000));
 const elapsed=seconds>=60?`${Math.floor(seconds/60)}m ${seconds%60}s`:`${seconds}s`;
 const message=w.mode==='change'?(w.phase==='reading'?'Comparing documents and value claims…':w.phase==='failed'?'Document saved · assessment needs attention':'Impact assessment ready'):w.phase==='reading'?(seconds>=45?'Still drafting answers…':'Reading '+w.title+'…'):w.phase==='applying'?'Preparing editable drafts…':w.phase==='complete'?(w.count?`${w.count} draft answer${w.count===1?'':'s'} ready`:'Document reviewed · existing answers kept'):'Document saved · drafting needs attention';
 return `<span class="document-status ${w.phase==='failed'?'document-status-error':''}" role="status" aria-live="polite">${working?'<span class="document-spinner" aria-hidden="true"></span>':''}${esc(message)}${working?` <span class="document-elapsed" aria-hidden="true">· ${elapsed}</span>`:''}</span>${w.phase==='failed'?button('Retry','coach-retry-source',w.source.id,'small'):''}`;
}
function refreshDocumentStatus(){const node=$('#document-status');if(node)node.innerHTML=documentStatus();}
function sourceShelf(){
 const c=coachInfo();
 return (typeof documentChangeNotice==='function'?documentChangeNotice():'')+`<section class="source-shelf document-shelf" aria-label="Documents"><div class="document-toolbar"><details class="document-list" ${sourcesOpen?'open':''}><summary>Documents${c.sources.length?' ('+c.sources.length+')':''}</summary><div class="document-list-body">${c.sources.length?c.sources.map(s=>`<div class="source-row"><label class="checkbox"><input type="checkbox" data-coach-source="${esc(s.ref.id)}" ${chosenSources.has(s.ref.id)?'checked':''} aria-label="Use ${esc(s.body.title)} with your AI partner"><span class="sr-only">Use ${esc(s.body.title)} with your AI partner</span></label><div class="source-file-identity"><a href="#main" class="document-name-link" data-action="coach-read-source" data-id="${esc(s.ref.id)}">${esc(s.body.title)}</a><small>${esc(s.body.role)}</small></div><div class="actions">${button(state.intake.draft.body.values.value?'Review impact':'Retry',state.intake.draft.body.values.value?'document-change-start':'coach-retry-source',s.ref.id,'quiet small')}</div></div>`).join(''):'<p class="caption">No documents uploaded.</p>'}${sourceDraftSummary()}</div></details><div id="document-status">${documentStatus()}</div><button type="button" data-action="coach-add-source" class="small document-upload" ${documentWorkVisible()&&['reading','applying'].includes(documentWork.phase)?'disabled':''}>Upload</button></div>${documentWorkVisible()&&documentWork.phase==='failed'?`<p class="caption document-error">${esc(documentWork.error)}</p>`:''}</section>`;
}
async function prepareDocumentDraft(source,title){
 chosenSources.add(source.id);
 await load();
 documentWork={draftId:state.intake.draft.ref.id,source,title,phase:'reading',mode:state.intake.draft.body.values.value?.trim()?'change':'draft',startedAt:Date.now()};
 $('#modal')?.close();render();
 const ticker=setInterval(refreshDocumentStatus,1000);
 try{
  if(documentWork.mode==='change'){
   const result=await assessDocumentChange(source);documentWork.phase='complete';documentWork.count=0;return result;
  }
  const result=await draftSourceAnswers([source],phase=>{documentWork.phase=phase;refreshDocumentStatus();});
  documentWork.phase='complete';documentWork.count=result.filled.length;
  return result;
 }catch(error){
  documentWork.phase='failed';documentWork.error=error.message;
  return {message:'Document saved. Drafting needs attention.'};
 }finally{clearInterval(ticker);refreshDocumentStatus();}
}
async function uploadDocument(data){
 const result=await command('intake-source',data);
 return prepareDocumentDraft(result.ref,data.filename||data.title||'your document');
}

function coachedIntakeScreen(stage){intakeStep=stage;return valuePropositionScreen();}
async function saveCoachedField(){
 if($('#value-proposition-form'))return saveValueProposition();
 const f=$('#coached-field-form');if(!f)return;
 const data=Object.fromEntries(new FormData(f)),field=coachedField,localKey=state.intake.draft.ref.id+'|'+field;
 if(!Object.entries(data).some(([k,v])=>v!==(state.intake.draft.body.values[k]||''))){pageDirty=false;return;}
 await command('intake-save',{...data,step:intakeStep,value_model:'jobs-pains-gains-v1',expected:state.intake.draft.ref});
 // Preserve any newer typing made while the save was in flight.
 if(coachingWorking[localKey]===data[field])delete coachingWorking[localKey];
 await load();
 for(const [k,v] of Object.entries(data)){const input=f.elements.namedItem(k);if(input&&input.value===v)input.value=state.intake.draft.body.values[k]||'';}
 const active=$('#coached-field-form');
 pageDirty=!!active&&Object.entries(Object.fromEntries(new FormData(active))).some(([k,v])=>v!==(state.intake.draft.body.values[k]||''));
 const status=$('#answer-status');if(status)status.textContent=pageDirty?'Unsaved changes':'Saved in your private draft';
}
async function requestCoaching(skill,message){if(!coachInfo().model.configured){modelSetup();return;}await saveCoachedField();if(pageDirty)throw Error('New edits arrived while saving. Ask again to include them.');const result=await command('intake-coach',{expected:state.intake.draft.ref,skill,field:coachedField,message,sources:selectedSourceRefs(),consent:true});await load();render();toast(result.message);if(result.changeResult)openDocumentChange(result.changeResult);}
function modelSetup(){modal('Connect your AI partner model',`<p>The AI partner uses a configurable model connection. Ask your administrator to connect an approved, supported model on the Workbench server.</p><ol><li>Set the connection type and model in the server configuration.</li><li>Store its credentials securely on the server.</li><li>Restart the Workbench server to load the connection.</li></ol><p>Keep credentials out of chat and project documents.</p><p class="caption">Available capabilities depend on the configured adapter. Imported material stays local until you ask your AI partner.</p>`);}
async function coachingAction(action,id){
 if(!action.startsWith('coach-'))return false;if(busy)return true;
 if(action==='coach-setup'){modelSetup();return true;}
 if(action==='coach-read-source'){const s=coachInfo().sources.find(x=>x.ref.id===id);modal(s.body.title,`${tag(s.body.role)}${para(s.body.text)}<p class="caption">Saved extracted text · available downloads are listed in My files</p>`);return true;}
 if(action==='coach-add-source'){
  await saveCoachedField();if(pageDirty)throw Error('Save your latest edits before uploading.');
  modal('Upload document',`<div class="form-field"><label for="source-file">Document</label><input id="source-file" type="file" accept=".txt,.md,.csv,.json,.docx,.pptx,.pdf"><small>Word, PDF, PowerPoint or text · up to 5 MB</small></div><p class="caption">The configured model reads the upload with your saved material. It drafts initial answers or assesses changes to an existing proposition.</p><details class="section"><summary>Paste text instead</summary><label class="form-field"><span>Title</span><input name="title" maxlength="250"></label><label class="form-field"><span>Text</span><textarea name="text" maxlength="120000"></textarea></label></details><details class="section"><summary>Document type</summary><label class="form-field"><span>Treat this material as</span><select name="role"><option value="background">Background</option><option value="evidence">Evidence to assess</option><option value="policy">Policy or governing reference</option><option value="hypothesis">Hypothesis or proposal</option></select></label></details>`,'Upload',async fd=>{
   const file=$('#source-file').files[0];let data={...Object.fromEntries(fd)};
   if(file){if(file.size>5*1024*1024)throw Error('Use a file under 5 MB or paste a relevant excerpt');const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));data={filename:file.name,content:btoa(binary),role:data.role};}
   return uploadDocument(data);
  },{busyLabel:'Uploading…'});return true;
 }
 if(action==='coach-retry-source'){
  const source=coachInfo().sources.find(s=>s.ref.id===id);if(!source)return true;
  await saveCoachedField();if(pageDirty)throw Error('Save your latest edits before retrying.');
  busy=true;
  try{const result=await prepareDocumentDraft(source.ref,source.body.title);await load();render();toast(result.message);if(result.changeResult)openDocumentChange(result.changeResult);}
  finally{busy=false;}return true;
 }
 if(action==='coach-questions'){
  if(!coachInfo().model.configured){modelSetup();return true;}
  await saveCoachedField();if(pageDirty)throw Error('Save your latest edits before preparing questions.');
  modal('Focus the context questions',`<p>Use the working proposition and selected material to identify what to explore next.</p><p class="caption">Your saved intake and ${selectedSourceRefs().length} selected sources will be sent to the configured model.</p>`,'Ask the AI partner',()=>command('intake-coach',{expected:state.intake.draft.ref,skill:'context-questions',field:coachedField,message:'What context questions should I answer next, based on this value proposition?',sources:selectedSourceRefs(),consent:true}));return true;
 }
 if(action==='coach-apply'){
  const [runId,k]=id.split('|'),r=coachInfo().runs.find(x=>x.ref.id===runId),s=r.body.output.suggestions.find(x=>x.field===k);if(!validRun(r)){toast('This advice used an earlier draft. Ask the AI partner again with your current answers.');return true;}
  if(pageDirty){toast('Save your current edits before applying a suggestion.');return true;}
  modal('Use this wording in your draft',`${val('Field',intakeNames[k])}${val('Current answer',state.intake.draft.body.values[k])}${r.body.skill==='seed-value'?field('edited_text','Proposed answer',s.text):val('Proposed answer',s.text)}${citationsHtml(s.citations)}<p class="caption">This creates a new draft revision. It does not validate evidence, publish intent or approve a requirement.</p>`,'Use this wording',async fd=>{const edited=String(fd.get('edited_text')||'');const result=await command('intake-coach-apply',{expected:state.intake.draft.ref,run_id:runId,field:k,...(r.body.skill==='seed-value'?{edited_text:edited}:{}),confirm:true});delete coachingWorking[state.intake.draft.ref.id+'|'+k];return result;});return true;
 }
 if(action==='coach-response'){
  const field=$('#value-proposition-form')?valueFocus:coachedField;
  if(id!==field)return true;
  const trigger=document.querySelector('[data-action="coach-response"]'),error=$('#value-proposition-form .error')||$('#coached-field-form .error');
  busy=true;const prior=trigger?.textContent;
  try{
   if(error)error.textContent='';
   if(trigger){trigger.disabled=true;trigger.textContent='AI partner is reviewing…';}
   if($('#value-proposition-form'))valueCoachMode='question';
   coachedField=field;
   await requestCoaching('coach-field',responseReviewRequest);
   focusCoachFeedback();
  }catch(e){if(error)error.textContent=e.message;else toast(e.message);}
  finally{busy=false;if(trigger){trigger.disabled=false;trigger.textContent=prior;}}
  return true;
 }
 busy=true;
 try{
  if(action==='coach-field'){await saveCoachedField();if(pageDirty)throw Error('New edits arrived while saving. Choose the question again to include them.');if(intakeQuestionSections[intakeStep]){intakeStep=questionSection(id)||intakeStep;valueFocus=id;valueReview=false;valueOpen=new Set(['reason','people','validation']);}coachedField=id;render();focusIntakeQuestion();}
  else if(action==='coach-stage'){await saveCoachedField();if(pageDirty)throw Error('Save your latest edits before continuing.');if(id==='context'&&coachInfo().model.configured)await requestCoaching('context-questions','What context questions should I answer next, based on this value proposition?');intakeStep=id;render();}
  else if(action==='coach-review'){const el=$('#coach-message-form');el.querySelector('.error').textContent='';await requestCoaching('coach-field','Review this answer against the full intake and selected sources. Identify what matters most to improve; offer wording if useful.');}
 }catch(e){const error=$('#coach-message-form .error')||$('#coached-field-form .error');if(error)error.textContent=e.message;else toast(e.message);}finally{busy=false;}
 return true;
}
document.addEventListener('toggle',e=>{if(e.target.matches?.('.document-list'))sourcesOpen=e.target.open;},true);
document.addEventListener('change',e=>{if(e.target.matches('[data-coach-source]')){e.target.checked?chosenSources.add(e.target.dataset.coachSource):chosenSources.delete(e.target.dataset.coachSource);}if(e.target.closest('#coached-field-form')){pageDirty=true;if(e.target.name)coachingWorking[state.intake.draft.ref.id+'|'+e.target.name]=e.target.value;}});
document.addEventListener('input',e=>{if(e.target.id==='coached-answer'){pageDirty=true;coachingWorking[state.intake.draft.ref.id+'|'+coachedField]=e.target.value;$('#answer-status').textContent='Unsaved changes';}if(e.target.matches?.('[data-reviewer-draft="intake-coach"]')&&typeof reviewerDraftWrite!=='function')intakeReviewerWrite(e.target.value);});
document.addEventListener('submit',async e=>{
 if(!['coached-field-form','coach-message-form'].includes(e.target.id))return;e.preventDefault();if(busy)return;busy=true;const b=e.submitter||e.target.querySelector('button[type=submit]'),prior=b.textContent;b.disabled=true;b.textContent=e.target.id==='coach-message-form'?'AI partner is responding…':'Saving…';const error=e.target.querySelector('.error');error.textContent='';
 try{if(e.target.id==='coached-field-form'){await saveCoachedField();if(pageDirty)throw Error('New edits arrived while saving. Save again to include them.');render();focusIntakeQuestion();toast('Answer saved.');}else {const message=String(new FormData(e.target).get('message')||'').trim();await requestCoaching('coach-field',message);}}catch(err){error.textContent=err.message;}finally{busy=false;b.disabled=false;b.textContent=prior;}
});

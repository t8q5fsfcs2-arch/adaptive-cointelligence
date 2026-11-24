// One contextual sidecar. Local explanations do not make a model call.
let fieldCoachSelection=null, fieldCoachAdvice=null, fieldCoachPending=false, fieldCoachEpoch=0,fieldCoachRequest=0;
const fieldCoachSessions=new Map();
function fieldCoachSessionKey(){return typeof reviewerDraftKey==='function'?reviewerDraftKey('field-coach'):[state.auth?.account?.id,state.actor,state.project?.id].join(':');}
let fieldCoachMountedKey=null;
function fieldCoachQuestion(){const el=document.querySelector('#field-coach-question');if(el&&(!el.dataset?.reviewerDraftKey||el.dataset.reviewerDraftKey===fieldCoachSessionKey()))return el.value;return typeof reviewerDraftRead==='function'?reviewerDraftRead('field-coach'):'';}
function fieldCoachKeepQuestion(){const value=fieldCoachQuestion();if(typeof reviewerDraftWrite==='function')reviewerDraftWrite('field-coach',value);return value;}
function coachPagePayload(){
 if(view==='planning'&&state.actor==='priya'&&state.intake?.draft)return {mode:'draft-page',field:'question',expected:state.intake.draft.ref};
 const kinds=new Set(['intent','policy','goal','success-measure','requirement','requirement-drawer']);
 const rows=(state.records||[]).filter(r=>r.scope==='project:demo'&&kinds.has(r.kind)).sort((a,b)=>a.ref.id<b.ref.id?-1:a.ref.id>b.ref.id?1:0);
 return {mode:'project',field:'question',basis:rows.map(r=>r.ref)};
}
function coachLibrary(){return state.field_guidance?.groups||{};}
function coachRecordKind(r){return ({goal:'goal','success-measure':'measure',requirement:'requirement'})[r?.kind];}
function coachRecordOptions(){
 return (state.records||[]).filter(r=>r.scope==='project:demo'&&coachRecordKind(r));
}
function coachRecordLabel(r){const title=r.body.title||r.body.name||referenceText(r.ref,r);return r.kind==='success-measure'&&typeof measureDisplayTitle==='function'?measureDisplayTitle(title):title;}
function coachBrowseItems(){
 const shared=coachRecordOptions().map(r=>({key:r.ref.id,label:coachRecordLabel(r),record:r,kind:coachRecordKind(r)}));
 if((typeof view!=='undefined'&&view==='requirements')||state.actor!=='priya'||!state.intake?.draft)return shared;
 const goals=(state.goals?.goals||[]).map(r=>({key:'draft:'+r.id,label:r.body.title||'Untitled goal',kind:'goal',id:r.id,saved:r.body}));
 const measures=(state.goals?.measures||[]).map(r=>({key:'draft:'+r.id,label:typeof measureDisplayTitle==='function'?measureDisplayTitle(r.body.name||'Untitled measure'):r.body.name||'Untitled measure',kind:'measure',id:r.id,saved:r.body}));
 const areas=typeof scaffoldLeaves==='function'?scaffoldLeaves().filter(r=>r.included).flatMap(r=>{const entries=typeof requirementDrafts==='function'?requirementDrafts(r,r.key):[];return entries.length?entries.map(x=>({key:'draft:'+x.id,label:x.title||r.label,kind:'requirement',id:r.key,requirement_id:x.id,saved:{...x,goal_ids:r.goal_ids||[]}})):[{key:'draft:'+r.key,label:(r.category?r.category+' / ':'')+r.label,kind:'requirement',id:r.key,saved:r}];}):[];
 return [...goals,...measures,...areas,...shared];
}
function fieldCoachShell(){return '<aside id="field-coach" class="card field-coach" aria-labelledby="field-coach-title"></aside>';}
function mountFieldCoach(){
 const key=fieldCoachSessionKey();if(fieldCoachMountedKey&&fieldCoachMountedKey!==key){fieldCoachSessions.set(fieldCoachMountedKey,{advice:fieldCoachAdvice});fieldCoachAdvice=fieldCoachSessions.get(key)?.advice||null;}
 fieldCoachMountedKey=key;fieldCoachSelection=null;fieldCoachEpoch++;
 const form=document.querySelector('#intake-drawers-form'),main=document.querySelector('#main');
 if(!form&&!['requirements','planning'].includes(view))return;
 if(!form&&view==='requirements'&&!coachRecordOptions().length&&(state.records||[]).some(r=>r.scope&&r.scope!=='project:demo'))return;
 const layout=document.createElement('div');layout.className='field-coach-layout';
 if(form){form.before(layout);layout.append(form);}else{
  const content=document.createElement('div');content.className='field-coach-work';
  Array.from(main.children).forEach(el=>{if(!el.matches('.project-page-header,.page-head,.breadcrumb,.workspace-switch,.project-page-identity,.project-status-line,.requirements-toolbar,.requirements-switch,.setup-draft-access,.requirement-authority-summary'))content.append(el);});
  main.append(layout);layout.append(content);
 }
 layout.insertAdjacentHTML('beforeend',fieldCoachShell());
 if(view==='requirements'&&coachRecordKind(get(selected)))selectCoachRecord(selected);
 else paintFieldCoach();
}
function coachSelectionFromElement(el){
 const row=el.closest('.goal-record'),area=el.closest('.scaffold-fields,.requirement-fields');
 if(row){const field=el.dataset.goalField||(el.hasAttribute('data-measure-goal')?'goal_ids':el.hasAttribute('data-coach-basis')||el.hasAttribute('data-basis-field')?'basis_fields':null),kind=row.dataset.group==='goals'?'goal':'measure';if(!coachLibrary()[kind]?.[field])return null;return {mode:'draft',kind,id:row.dataset.goalId,field,el,row};}
 if(area){const field=el.hasAttribute('data-area-goal')?'goal_ids':el.name;if(!coachLibrary().requirement?.[field])return null;return {mode:'draft',kind:'requirement',id:area.dataset.coachPath,requirement_id:area.dataset.requirementId,field,el,row:area};}
 return null;
}
function coachWorking(s){
 const out={};
 if(s.saved){for(const k of Object.keys(coachLibrary()[s.kind]||{}))if(k in s.saved)out[k]=s.saved[k];return out;}
 if(s.kind==='goal'||s.kind==='measure')s.row.querySelectorAll('[data-goal-field]').forEach(el=>out[el.dataset.goalField]=el.value);
 else s.row.querySelectorAll('input[name],textarea[name],select[name]').forEach(el=>{if(coachLibrary().requirement?.[el.name]&&el.type!=='hidden')out[el.name]=el.value;});
 const links=s.kind==='measure'?'[data-measure-goal]:checked':s.kind==='requirement'?'[data-area-goal]:checked':null;
 const linkScope=s.requirement_id?[...document.querySelectorAll('.scaffold-fields')].find(x=>x.dataset.coachPath===s.id):s.row;
 if(links)out.goal_ids=Array.from((linkScope||s.row).querySelectorAll(links)).map(el=>el.dataset.measureGoal||el.dataset.areaGoal);
 if(s.kind==='goal'||s.kind==='measure')out.basis_fields=Array.from(s.row.querySelectorAll('[data-basis-field]:checked')).map(el=>el.dataset.basisField).sort();
 return out;
}
function coachPayload(s=fieldCoachSelection){
 if(!s)return coachPagePayload();
 return {mode:s.mode,kind:s.kind,id:s.id,field:s.field,expected:s.mode==='draft'?state.intake.draft.ref:s.record.ref,...(s.mode==='draft'?{working:coachWorking(s),...(s.requirement_id?{requirement_id:s.requirement_id}:{})}:{})};
}
function coachStamp(s=fieldCoachSelection){const payload=coachPayload(s);return JSON.stringify({payload,...(s?.field==='basis_fields'?{answers:state.intake.draft.body.values}:{} )});}
function coachAdviceCurrent(){return !!fieldCoachAdvice&&fieldCoachAdvice.stamp===coachStamp();}
function selectFieldCoach(s){
 if(fieldCoachSelection?.el)fieldCoachSelection.el.classList.remove('coach-selected-field');
 fieldCoachKeepQuestion();
 fieldCoachSelection=s;fieldCoachEpoch++;
 if(s?.el)s.el.classList.add('coach-selected-field');paintFieldCoach();
}
function selectCoachRecord(id){
 const item=coachBrowseItems().find(r=>r.key===id);if(!item){selectFieldCoach(null);return;}
 const {kind,record}=item;
 selectFieldCoach(record?{mode:'record',kind,id,record,field:kind==='requirement'?'text':kind==='goal'?'outcome':'definition'}:
 {mode:'draft',kind,id:item.id,requirement_id:item.requirement_id,saved:item.saved,field:kind==='requirement'?(item.requirement_id?'requirement':'question'):kind==='goal'?'outcome':'definition'});
}
function coachBasisSuggestions(s,o,stale){
 if(!o.basis_suggestions)return '';
 if(!o.basis_suggestions.length)return '<p class="caption">No supporting intake answers found. You can refine this item or add the missing information to intake.</p>';
 const existing=new Set(coachWorking(s).basis_fields||[]),canUse=s.row&&s.mode==='draft';
 return `<div class="basis-suggestions">${o.basis_suggestions.map(x=>`<div class="basis-suggestion"><label class="checkbox"><input type="checkbox" data-basis-suggestion="${esc(x.field)}" ${existing.has(x.field)?'disabled':'checked'} ${stale?'disabled':''}><span><strong>${esc(intakeAnswerLabel(x.field))}</strong>${existing.has(x.field)?' <span class="caption">Already linked</span>':''}<span class="basis-reason">${esc(x.reason)}</span></span></label><details><summary>Read saved answer</summary><p class="pre caption">${esc(x.source_answer)}</p></details></div>`).join('')}
 ${canUse&&o.basis_suggestions.some(x=>!existing.has(x.field))?`<button type="button" data-action="field-coach-use-links" ${stale?'disabled':''}>Use selected connections</button>`:!canUse?'<p class="caption">Open the scaffold editor to change these connections.</p>':''}
 <p class="caption">Links explain the connection to intent; they do not validate the underlying claims.</p></div>`;
}
function coachAdviceBody(s,o,stale){
 if(s?.field==='basis_fields')return `<h3>Suggested connections</h3>${coachBasisSuggestions(s,o,stale)}`;
 return `<h3>${esc(o.assessment)}</h3><p>${esc(o.why_it_matters)}</p>${o.next_question?`<p><strong>Consider:</strong> ${esc(o.next_question)}</p>`:''}`;
}
function paintFieldCoach(){
 const panel=document.querySelector('#field-coach');if(!panel)return;
 const s=fieldCoachSelection,g=s?coachLibrary()[s.kind]?.[s.field]:null;
 const question=fieldCoachKeepQuestion(),active=document.activeElement,focusId=active?.closest?.('#field-coach')?active.id:null,caret=focusId==='field-coach-question'?{start:active.selectionStart,end:active.selectionEnd}:null;
 const contextOpen=!!panel.querySelector('.reviewer-context-details')?.open,guideOpen=!!panel.querySelector('.coach-guidance')?.open;
 const publishedReview=view==='requirements';
 const recordPicker=publishedReview?`<details class="reviewer-context-details" ${contextOpen?'open':''}><summary>Context & sources</summary><section class="published-review-choice"><div class="form-field"><label for="field-coach-item">Discuss an item</label><div class="ui-selector-wrap"><select id="field-coach-item" class="ui-selector"><option value="">Select an item</option>${coachBrowseItems().map(r=>`<option value="${esc(r.key)}" ${(s?.mode==='draft'?'draft:'+(s.requirement_id||s.id):s?.id)===r.key?'selected':''}>${esc(r.label)}</option>`).join('')}</select>${selectorChevron()}</div></div><p>Ask about meaning, evidence or open questions.</p><p>Review does not edit or approve.</p><a href="#main" data-nav="review">Decisions & Issues →</a>${s?.mode==='record'&&s.kind==='requirement'?'<p><button type="button" data-action="field-coach-handoff">Carry concern to Decisions & Issues</button></p>':''}</section></details>`:'';
 const method=g?state.field_guidance?.methods?.[g.method]:null;
 const sourceTitle=s?(s.mode==='record'?coachRecordLabel(s.record):coachWorking(s).title||coachWorking(s).name||coachWorking(s).label):'',title=s?.kind==='measure'&&typeof measureDisplayTitle==='function'?measureDisplayTitle(sourceTitle):sourceTitle;
 const o=fieldCoachAdvice?.output,stale=o&&!coachAdviceCurrent(),connections=s?.field==='basis_fields';
 panel.innerHTML=`<h2 id="field-coach-title" class="thought-partner-title">${publishedReview?'Explain these requirements':'AI partner'}</h2><div class="reviewer-scroll">${recordPicker}${!g?`<p class="muted">${publishedReview?'Choose a goal, measure or requirement to have its meaning, evidence and open questions explained. Nothing here edits or approves.':'Ask about the work on this page.'}</p>`:`
 <p class="caption coach-item-name">${esc(title||'Working draft')}</p><h3 class="coach-field-title">${esc(g.title)}</h3>
 <details class="coach-guidance" ${guideOpen?'open':''}><summary>Review guidance</summary>${(s.mode==='record'||s.saved)?`<label class="form-field"><span>Field</span><select id="field-coach-field">${Object.entries(coachLibrary()[s.kind]).filter(([k])=>k in (s.record?.body||s.saved)&&(s.mode!=='record'||k!=='basis_fields')).map(([k,v])=>`<option value="${k}" ${s.field===k?'selected':''}>${esc(v.title)}</option>`).join('')}</select></label>`:''}
 <p class="coach-what">${esc(g.what)}</p><p class="coach-why"><strong>Why it matters</strong> ${esc(g.why)}</p>
 <details><summary>Example & method</summary><div class="details-body"><p class="caption">Fictional example</p><p>${esc(g.example)}</p>${method?`<p class="caption">${method.source.url?`<a href="${esc(method.source.url)}" target="_blank" rel="noopener noreferrer">${esc(method.source.title)}</a>`:esc(method.name)}</p><p class="caption">${esc(method.limits)}</p>`:''}</div></details>
 </details>
 `}<div id="field-coach-response" role="status" aria-live="polite">${fieldCoachPending?'<p role="status">Reviewing…</p>':''}${fieldCoachAdvice?.error?`<p class="error">${esc(fieldCoachAdvice.error)}</p>`:''}${o?`${fieldCoachAdvice.question?`<article class="reviewer-human-message"><p class="reviewer-speaker">You</p><p class="pre">${esc(fieldCoachAdvice.question)}</p></article>`:''}<section class="reviewer-ai-message"><p class="reviewer-speaker reviewer-speaker-ai">AI partner${fieldCoachAdvice.mode==='simulated'?' · Simulated':''}</p>${coachAdviceBody(s,o,stale)}${o.suggested_wording&&s?`<div class="ac-suggestion">${typeof acSuggestionHead==='function'?acSuggestionHead('From your AI partner · nothing changes until you use it and save'):''}<p class="ac-suggestion-label">Suggested wording</p><p class="pre">${esc(o.suggested_wording)}</p>${s.mode==='draft'&&s.el&&!['goal_ids','basis_fields'].includes(s.field)?`<button type="button" data-action="field-coach-use" ${stale?'disabled':''}>Use suggestion</button>`:'<p class="caption">Proposed changes go through Decisions & Issues.</p>'}</div>`:''}${stale?'<p class="caption">Context changed. Review this advice before using it.</p>':''}</section>`:''}${fieldCoachAdvice?.applied?'<p>Connections added. Save draft to keep them.</p>':''}</div>${typeof planningProjectGuidance==='function'?planningProjectGuidance():''}</div><div class="coach-request reviewer-composer"><label class="form-field" for="field-coach-question"><span class="reviewer-speaker">You</span><textarea id="field-coach-question" rows="4" maxlength="1200" data-reviewer-draft="field-coach" aria-label="${publishedReview?'Ask for an explanation':'Ask your AI partner'}" class="integrity-review-input" placeholder="${publishedReview?'Ask what a requirement means or rests on':'Ask your AI partner'}">${esc(question)}</textarea></label><button type="button" class="primary" data-action="field-coach-review" ${fieldCoachPending||state.coaching?.model?.configured===false?'disabled':''}>${fieldCoachPending?'Reviewing…':'Ask'}</button></div>`;
 if(typeof mountReviewerUI==='function')mountReviewerUI(panel);
 if(focusId){const replacement=panel.querySelector('#'+focusId);replacement?.focus?.({preventScroll:true});if(caret)replacement?.setSelectionRange?.(caret.start,caret.end);}


}

async function fieldCoachAction(action,id,options={}){
 if(!action.startsWith('field-coach-'))return false;
 if(action==='field-coach-handoff'){
  const s=fieldCoachSelection;
  if(!s||s.mode!=='record'||s.kind!=='requirement')throw Error('Choose a published requirement to carry into Decisions & Issues.');
  const question=document.querySelector('#field-coach-question')?.value||'';
  const stamp=coachStamp(),epoch=fieldCoachEpoch;
  const h=await command('field-coach-concern-prepare',{requirement:s.record.ref,field:s.field,question,...(options.intended_use?{intended_use:options.intended_use}:{}),...(coachAdviceCurrent()&&fieldCoachAdvice?.ref?{advice:fieldCoachAdvice.ref}:{})});
  if(epoch!==fieldCoachEpoch||stamp!==coachStamp()||question!==(document.querySelector('#field-coach-question')?.value||''))throw Error('The selected requirement or question changed while preparing. Your prepared concern remains privately saved.');
  bridgeRaiseForm({handoff:h,title:h.title,question:h.question,consequence:h.consequence,kind:'challenge',route:'requirement',owner:state.actor});return true;
 }
 if(action==='field-coach-basis'){
  const row=Array.from(document.querySelectorAll('.goal-record')).find(el=>el.dataset.goalId===id);
  const el=row?.querySelector('[data-coach-basis]');if(!el)return true;
  selectFieldCoach(coachSelectionFromElement(el));
  return fieldCoachAction('field-coach-review');
 }
 if(action==='field-coach-area'){
  const target=id?.startsWith('{')?JSON.parse(id):{drawer:id};
  const selected=target.requirement_id?[...document.querySelectorAll('.requirement-fields')].find(x=>x.dataset.requirementId===target.requirement_id):null;
  const area=selected||Array.from(document.querySelectorAll('[data-coach-path]')).find(el=>el.dataset.coachPath===target.drawer);
  const el=area?.querySelector('textarea[name="requirement"],textarea[name="question"]');
  if(el){for(let p=el.parentElement;p&&p!==area.parentElement;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;el.focus();selectFieldCoach(coachSelectionFromElement(el));}
  return true;
 }
 const s=fieldCoachSelection;if(!s&&action!=='field-coach-review')return true;
 if(action==='field-coach-use-links'){
  if(s.field!=='basis_fields'||s.mode!=='draft'||!s.row?.isConnected||!coachAdviceCurrent())throw Error('The response changed. Request fresh connections before using them.');
  const chosen=Array.from(document.querySelectorAll('[data-basis-suggestion]:checked:not(:disabled)')).map(el=>el.dataset.basisSuggestion);
  if(!chosen.length)throw Error('Choose a connection to add.');
  const stamp=coachStamp(),epoch=fieldCoachEpoch,advice=fieldCoachAdvice;
  await command('field-coach-check',{...coachPayload(),question:advice.question||'',advice:advice.ref});
  if(epoch!==fieldCoachEpoch||stamp!==coachStamp()||!s.row.isConnected)throw Error('The response changed. Request fresh connections before using them.');
  const allowed=new Set(advice.output.basis_suggestions.map(x=>x.field));
  const controls=Array.from(s.row.querySelectorAll('[data-basis-field]'));
  if(chosen.some(key=>!allowed.has(key)||!controls.some(el=>el.dataset.basisField===key)))throw Error('The intake answers changed. Request fresh connections.');
  controls.forEach(el=>{if(chosen.includes(el.dataset.basisField))el.checked=true;});
  pageDirty=true;refreshBasisSummary(s.row);
  s.row.querySelector('[data-basis-status]').textContent='Connections added · save draft to keep them.';
  fieldCoachAdvice={...advice,output:null,applied:true};paintFieldCoach();toast('Connections added. Save draft to keep them.');return true;
 }
 if(action==='field-coach-use'){
  if(!coachAdviceCurrent()||s.mode!=='draft'||!s.el?.isConnected)throw Error('The response changed. Request fresh advice before using it.');
  s.el.value=fieldCoachAdvice.output.suggested_wording;s.el.dispatchEvent(new Event('input',{bubbles:true}));
  pageDirty=true;paintFieldCoach();toast('Wording added to your draft. You can edit it, then save.');return true;
 }
 if(action==='field-coach-review'){
  if(fieldCoachPending)return true;
  const payload=coachPayload(),stamp=coachStamp(),epoch=fieldCoachEpoch,question=fieldCoachKeepQuestion(),key=fieldCoachSessionKey(),request=++fieldCoachRequest;
  if(!s&&!question.trim()){document.querySelector('#field-coach-question')?.focus();throw Error('Enter a question to ask about this page.');}
  if(fieldCoachAdvice?.ref&&coachAdviceCurrent())payload.previous_advice=fieldCoachAdvice.ref;
  fieldCoachPending=true;paintFieldCoach();
  try{const result=await command('field-coach',{...payload,question,consent:true});fieldCoachSessions.set(key,{advice:{...result,stamp,question}});if(epoch===fieldCoachEpoch&&key===fieldCoachSessionKey()){fieldCoachAdvice={...result,stamp,question};}}
  catch(error){if(epoch===fieldCoachEpoch)fieldCoachAdvice={error:error.message,stamp};}
  finally{if(request===fieldCoachRequest){fieldCoachPending=false;if(key===fieldCoachSessionKey())paintFieldCoach();}}
  return true;
 }
 return true;
}
document.addEventListener('focusin',e=>{if(!document.querySelector('#field-coach')||e.target.closest('#field-coach'))return;const s=coachSelectionFromElement(e.target);if(s&&(s.id!==fieldCoachSelection?.id||s.requirement_id!==fieldCoachSelection?.requirement_id||s.field!==fieldCoachSelection?.field))selectFieldCoach(s);});
document.addEventListener('change',e=>{if(e.target.id==='field-coach-item')selectCoachRecord(e.target.value);if(e.target.id==='field-coach-field'&&fieldCoachSelection){selectFieldCoach({...fieldCoachSelection,field:e.target.value});}if(e.target.hasAttribute('data-basis-field')&&fieldCoachAdvice)paintFieldCoach();});
document.addEventListener('input',e=>{if(e.target.closest('#intake-drawers-form')&&fieldCoachAdvice)paintFieldCoach();});

document.addEventListener('toggle',event=>{const drawer=event.target;if(drawer.open&&drawer.matches?.('.requirement-record[data-requirement]')&&document.querySelector('#field-coach'))selectCoachRecord(drawer.dataset.requirement);},true);

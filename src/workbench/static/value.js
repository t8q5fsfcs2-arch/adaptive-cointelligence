// Questions are inputs; the proposition is a generated, editable output.
let valueReview=false,valueFocus='business_challenge',valueCoachMode='question',valueMessage='',valueWorking={},valueOpen=new Set(['reason']);
let valueCandidateEdits={},valueDismissed=new Set();
let valueNavigationOpen=true,valueNavigationFocus=null;
const intakeQuestionSections={
 rationale:[['reason','Business rationale',['business_challenge','strategic_relevance','why_now']]],
 value:[['people','People and needs',['beneficiaries','jobs','need','gains']],['fit','Proposed fit',['approach','job_support','pain_relievers','gain_creators']]],
 context:[['flow','People and flow',['supporting_users','user_situation','user_actions','bottlenecks','tools','handoffs','desired_outputs']],['scope','Scope and dependencies',['work_kind','in_scope','out_scope','constraints','dependencies']],['learning','Evidence and open questions',['evidence','sources','assumptions','assumption_owner','open_questions','research_question','operations_question']]],
 success:[['outcomes','Success measures',['measures','measure_review']]]
};
const valueSections=intakeQuestionSections.value;
const activeQuestionSections=()=>intakeQuestionSections[typeof intakeStep==='undefined'?'value':intakeStep]||valueSections;
const questionSection=k=>Object.keys(intakeQuestionSections).find(id=>intakeQuestionSections[id].some(g=>g[2].includes(k)))||(k==='value'?'value':null);
function ensureQuestionFocus(){if(!activeQuestionSections().some(g=>g[2].includes(valueFocus)))valueFocus=activeQuestionSections()[0][2][0];coachedField=valueFocus;}
const fitPairs=[['jobs','job_support'],['need','pain_relievers'],['gains','gain_creators']];
const valueQuestionKeys=()=>Object.values(intakeQuestionSections).flatMap(groups=>groups.flatMap(s=>s[2]));
const valueDraft=()=>({...state.intake.draft.body.values,...valueWorking});
function valueQuestionLink(q){return valueQuestionKeys().includes(q.field)||q.field==='value'?button('Work on this','value-focus',q.field,'small'):'<p class="caption">For the context stage</p>';}
function valueInput(k,v){return `<div class="value-input"><textarea id="value-${k}" name="${k}" maxlength="20000" aria-labelledby="question-${k}" aria-describedby="guide-${k}" placeholder="A few sentences are enough to start.">${esc(v[k]||'')}</textarea></div>`;}
function completeValuePreview(v){
 return `${val('Value proposition',v.value)}${val('Primary users',v.beneficiaries)}${val('Proposed offering',v.approach)}<div class="value-fit-head"><strong>User needs</strong><strong>Proposed response</strong></div>${fitPairs.map(([a,b])=>`<div class="value-fit-pair"><div>${val(shortQuestion(a),v[a])}</div><div>${val(shortQuestion(b),v[b])}</div></div>`).join('')}`;
}
function measurementReference(v){
 return `<details class="measurement-reference"><summary>Value proposition to measure</summary>${v.value?para(v.value):'<p class="caption">No value proposition drafted yet. Start with an intended benefit.</p>'}</details>`;
}
// Preserve old prose verbatim. Only explicit paragraph breaks create separate entries;
// never guess metrics from semicolons, sentences, or figures in an existing answer.
const metricEntries=text=>String(text||'').split('\n\n');
const metricText=items=>items.filter(x=>x.trim()).join('\n\n');
function metricRows(items){return items.map((text,i)=>`<div class="metric-entry"><div class="metric-entry-head"><label for="metric-${i}">Metric ${i+1}</label><button type="button" class="quiet small remove-control" data-metric-action="remove" data-index="${i}" aria-label="Remove metric ${i+1}" title="Remove metric ${i+1}"><span aria-hidden="true">×</span></button></div><textarea id="metric-${i}" data-metric-input maxlength="20000" aria-describedby="guide-measures" rows="3" placeholder="Reduce [measure] from [baseline] to [target] for [people or process]. State what is still unknown.">${esc(text)}</textarea></div>`).join('');}
function metricsInput(v){return `<div class="value-input metrics-editor"><input type="hidden" id="value-measures" name="measures" value="${esc(v.measures||'')}"><div class="metric-list">${metricRows(metricEntries(v.measures))}</div><button type="button" class="small" data-metric-action="add">Add metric</button></div>`;}
function readMetricInputs(form){return [...form.querySelectorAll('[data-metric-input]')].map(el=>el.value);}
function syncMetricInputs(form){
 const hidden=form.elements.namedItem('measures');hidden.value=metricText(readMetricInputs(form));
 rememberValueInput({target:hidden});
 // Adding or removing an entry must also age any feedback, just like typing.
 if(typeof markCoachEdits==='function')markCoachEdits({target:hidden});
}
document.addEventListener('click',e=>{
 const control=e.target.closest('[data-metric-action]');if(!control||busy)return;
 const form=control.closest('#value-proposition-form');if(!form)return;
 const items=readMetricInputs(form),adding=control.dataset.metricAction==='add';
 const index=Number(control.dataset.index);let focus;
 if(adding){items.push('');focus=items.length-1;}
 else{if(!Number.isInteger(index)||index<0||index>=items.length)return;items.splice(index,1);if(!items.length)items.push('');focus=Math.min(index,items.length-1);}
 form.querySelector('.metric-list').innerHTML=metricRows(items);
 if(!adding)syncMetricInputs(form);
 form.querySelectorAll('[data-metric-input]')[focus].focus();
});
// Keep navigation beside the workspace. Native disclosures never rerender an answer.
function valueQuestionNavigation(){
 if(state.actor==='priya'&&typeof sponsorScreen==='function')return '';
 if(view!=='intent'||!intakeQuestionSections[intakeStep]||state.actor!=='priya'||!state.intake.has_draft)return '';
 ensureQuestionFocus();
 const groups=activeQuestionSections(),v=valueDraft(),group=groups.find(s=>s[2].includes(valueFocus));
 if(valueNavigationFocus!==valueFocus){valueOpen.add(group[0]);valueNavigationFocus=valueFocus;}
 const title=intakeSteps.find(([key])=>key===intakeStep)[1];
 const questions=fields=>fields.map(k=>`<button type="button" class="${k===valueFocus?'selected':''}" data-action="value-focus" data-id="${k}" ${k===valueFocus?'aria-current="step"':''}><span class="question-mark" aria-hidden="true">${(v[k]||'').trim()?'✓':'○'}</span>${esc(shortQuestion(k))}</button>`).join('');
 const content=groups.length===1?`<div class="value-question-group">${questions(groups[0][2])}</div>`:groups.map(([id,label,fields])=>`<details data-value-section="${id}" ${valueOpen.has(id)?'open':''}><summary><span>${esc(label)}</span><span class="question-count" title="${fields.filter(k=>(v[k]||'').trim()).length} of ${fields.length} answered">${fields.filter(k=>(v[k]||'').trim()).length}/${fields.length}</span><span class="disclosure-chevron" aria-hidden="true"></span></summary>${questions(fields)}</details>`).join('');
 return `<details class="intent-question-drawer" ${valueNavigationOpen?'open':''}><summary><span>${esc(title)}</span><span class="disclosure-chevron" aria-hidden="true"></span></summary><div class="value-question-nav" aria-label="${esc(title)} questions">${content}</div></details>`;
}
document.addEventListener('toggle',e=>{
 const el=e.target;if(!el.isConnected)return;
 if(el.matches('.intent-question-drawer'))valueNavigationOpen=el.open;
 if(el.matches('[data-value-section]')){if(el.open)valueOpen.add(el.dataset.valueSection);else valueOpen.delete(el.dataset.valueSection);}
},true);
function questionDraftStatus(){return (valueDraft()[valueFocus]||'')!==(state.intake.draft.body.values[valueFocus]||'')?'Unsaved changes':'Draft saved';}
function questionResponseActions(field){return `<div class="value-actions"><button type="submit" value="stay" data-question-save>Save draft</button>${button('Ask your AI partner','coach-response',field,'primary')}<span id="question-save-status" class="caption" role="status">${questionDraftStatus()}</span></div>`;}
function valueQuestions(v){
 return `<section class="card value-questions" aria-labelledby="question-${valueFocus}"><div class="value-question-current"><div class="error" role="alert"></div><div class="eyebrow">Question</div><h2 id="question-${valueFocus}">${esc(shortQuestion(valueFocus))}</h2>${questionGuide(valueFocus)}${valueFocus==='measures'?measurementReference(v):''}${valueFocus==='assumption_owner'?roleSelect('assumption_owner','Investigation coordinator',v.assumption_owner):valueFocus==='work_kind'?initiativeSelect(v):valueFocus==='measures'?metricsInput(v):valueInput(valueFocus,v)}${questionResponseActions(valueFocus)}${sourceDraftBasis(valueFocus)}</div></section>`;
}
function valueCandidate(){
 const run=coachInfo().runs.filter(r=>r.body.skill==='compose-value').at(-1);
 return run&&!Object.hasOwn(run.body.applied,'value')&&!valueDismissed.has(run.ref.id)?run:null;
}
function valueFreshness(v){
 const p=state.intake.draft.body.field_provenance?.value;
 if(!v.value)return 'Ready to generate from your answers';
 if(!p?.answer_values)return 'Editable working draft';
 return Object.entries(p.answer_values).some(([k,text])=>(v[k]||'')!==text)?'Answers changed · refresh available':'Based on your current answers';
}
function valueOutput(v){
 const cp=state.intake.value_checkpoint,c=coachInfo(),candidate=valueCandidate(),suggestion=candidate?.body.output.suggestions[0];
 return `<section class="card value-output" aria-label="Value proposition"><div class="card-head"><div><div class="eyebrow">VALUE PROPOSITION</div><h2>The value we offer</h2></div>${tag(cp.current?'Reviewed':'Working draft',cp.current?'green':'amber')}</div><p class="caption">Who benefits, what they need, and how the offering helps.</p><div class="error" role="alert"></div><div class="value-generation-bar"><button type="button" data-action="value-generate" class="primary" ${c.model.configured?'':'disabled'}>${v.value?'Refresh from answers':'Generate draft from answers'}</button><span id="value-freshness" class="caption">${esc(valueFreshness(v))}</span></div>${!c.model.configured?`<div class="coach-connect">Connect your model to generate content. ${button('Connection instructions','coach-setup','','small')}</div>`:''}<label class="value-draft-label" for="value-value">${v.value?'Your editable proposition':'Your generated draft will appear here'}</label><textarea id="value-value" name="value" maxlength="20000" placeholder="Start with the questions on the left, then generate a draft. You can refine every word here.">${esc(v.value||'')}</textarea>${sourceDraftBasis('value')}<p class="caption">${v.value?'Edit directly. Refreshing proposes an update without replacing this wording.':'A partial set of answers is enough for a starting draft. Unknowns stay visible.'}</p>${candidate?`<div class="value-generated-update ac-suggestion">${typeof acSuggestionHead==='function'?acSuggestionHead('From your AI partner · edit it here; your current draft stays until you choose Use this draft'):''}<div class="card-head"><h3>${v.value?'Proposed refresh':'Generated draft'}</h3></div>${para(candidate.body.output.reply)}<label for="value-candidate">Edit the proposed wording</label><textarea id="value-candidate" maxlength="20000" data-run="${candidate.ref.id}">${esc(valueCandidateEdits[candidate.ref.id]??suggestion.text)}</textarea><p class="caption">${esc(suggestion.rationale)}</p>${citationsHtml(suggestion.citations)}<div class="actions">${button('Use this draft','value-use',candidate.ref.id,'primary small')}${button('Keep current draft','value-dismiss',candidate.ref.id,'small')}</div>${!validRun(candidate)?'<p class="caption">Answers changed after this generation. Generate again before using it.</p>':''}</div>`:''}<div class="value-actions"><button type="submit" name="next" value="stay">Save draft</button><button type="submit" name="next" value="review" class="small">Review value proposition →</button><span id="value-save-status" class="caption" role="status">${Object.keys(valueWorking).length?'Unsaved changes':'Saved privately'}</span></div><p class="caption value-model-note">Generation sends your answers, current draft and selected material to the configured model. Generated wording is a working hypothesis.</p>${valueReview?`<div class="value-checkpoint"><h3>Review the value proposition</h3><p class="caption">Review the proposition together with its supporting answers.</p>${cp.missing.length?`<div class="banner"><strong>Still to articulate</strong><p>${cp.missing.map(k=>esc(intakeNames[k])).join(' · ')}</p><p class="caption">State an unknown and how it will be investigated where an answer is not yet available.</p></div>`:''}<div class="actions">${button('Keep refining','value-edit','','small')}${button(cp.current?'Reviewed':'Mark proposition reviewed','value-accept','','primary small')}</div><p class="caption">This records your review of the wording. Evidence and fit still need testing.</p></div>`:''}<details class="value-answer-review" ${valueReview?'open':''}><summary>Supporting answers & proposed fit</summary>${completeValuePreview(v)}</details>${generatedValueQuestions()}</section>`;
}
function valueCoach(){
 const whole=valueCoachMode==='whole',runs=coachInfo().runs.filter(r=>whole?r.body.skill==='review-value':r.body.skill==='coach-field'&&r.body.field===valueFocus);
 return focusedCoachPanel({field:whole?'value':valueFocus,whole,formId:'value-coach-form',message:valueMessage,runs,valueStage:true});
}
function generatedValueQuestions(){
 const run=coachInfo().runs.filter(r=>r.body.skill==='compose-value').at(-1),questions=run?.body.output.questions||[];
 return questions.length?`<details class="value-answer-review"><summary>Questions from this draft (${questions.length})</summary>${!validRun(run)?'<p class="caption">These questions came from an earlier version.</p>':''}${questions.map(q=>`<div class="rule">${para(q.question)}<p class="caption">${esc(q.reason)}</p>${valueQuestionLink(q)}</div>`).join('')}</details>`:'';
}
function valuePropositionScreen(){
 ensureQuestionFocus();
 const cp=state.intake.value_checkpoint,v=valueDraft(),isValue=intakeStep==='value',isResponse=['rationale','context','success'].includes(intakeStep);
 return sourceShelf()+`<div class="value-workspace${isResponse?' intake-response-workspace':''}"><form id="value-proposition-form" class="${isResponse?'intake-response-form':'value-input-columns'}">${valueQuestions(v)}${isValue?valueOutput(v):''}</form>${valueCoach()}</div>`+(isValue&&cp.history.length?`<details class="card section"><summary>Proposition review history (${cp.history.length})</summary>${cp.history.map(r=>`<details><summary>Version ${r.ref.revision} · ${esc(date(r.body.at))}</summary>${para(r.body.rationale)}${completeValuePreview(r.body.values)}</details>`).join('')}</details>`:'');
}
async function saveValueProposition(){
 const form=$('#value-proposition-form');if(!form)return;
 const values={...valueWorking,...Object.fromEntries(new FormData(form))},before=state.intake.draft.body.values;
 if(!Object.entries(values).some(([k,v])=>v!==(before[k]||''))){pageDirty=false;valueWorking={};return;}
 const grouped={};
 for(const [k,v] of Object.entries(values)){const section=questionSection(k);if(section)(grouped[section]??={})[k]=v;}
 for(const [section,fields] of Object.entries(grouped)){
  if(!Object.entries(fields).some(([k,v])=>v!==(state.intake.draft.body.values[k]||'')))continue;
  await command('intake-save',{...fields,step:section,value_model:'jobs-pains-gains-v1',expected:state.intake.draft.ref});
  await load();
 }
 for(const [k,v] of Object.entries(values))if(valueWorking[k]===v)delete valueWorking[k];
 await load();
 for(const [k,v] of Object.entries(values)){const input=form.elements.namedItem(k);if(input&&input.value===v)input.value=state.intake.draft.body.values[k]||'';}
 pageDirty=Object.entries({...valueWorking,...Object.fromEntries(new FormData(form))}).some(([k,v])=>v!==(state.intake.draft.body.values[k]||''));
 if($('#value-save-status'))$('#value-save-status').textContent=pageDirty?'Unsaved changes':'Saved privately';
 if($('#question-save-status'))$('#question-save-status').textContent=questionDraftStatus();
}
async function generateValue(){
 if(Object.keys(valueCandidateEdits).length)throw Error('Use the edited refresh or choose Keep current draft before generating another.');
 await saveValueProposition();
 if(pageDirty)throw Error('New edits arrived while saving. Generate again to include them.');
 const hadDraft=!!state.intake.draft.body.values.value;
 const result=await command('intake-coach',{expected:state.intake.draft.ref,skill:'compose-value',field:'',message:'Generate an editable value proposition from my current answers. Preserve my edits to any existing proposition; explain substantive revisions.',sources:selectedSourceRefs(),consent:true});
 await load();
 // The explicit Generate action can populate an empty draft. Refreshes always need comparison.
 if(!hadDraft&&!pageDirty&&!Object.keys(valueWorking).length){
  await command('intake-coach-apply',{expected:state.intake.draft.ref,run_id:result.ref.id,field:'value',confirm:true});
  await load();
 }
 valueReview=false;
}
async function valueAction(action,id){
 if(!action.startsWith('value-'))return false;if(busy)return true;
 if(action==='value-accept'){
  if(pageDirty){toast('Save and review your latest edits first.');return true;}
  const cp=state.intake.value_checkpoint;
  if(cp.current){valueReview=false;render();return true;}
  if(cp.missing.length){toast('Articulate the missing parts or state what is unknown before accepting.');return true;}
  modal('Review this value proposition',`<p>Record that you have reviewed the needs and proposed fit. This does not validate the evidence or authorize delivery.</p>${cp.accepted?'<label class="form-field"><span>Why are you revising the starting proposition?</span><textarea name="rationale" required maxlength="20000"></textarea></label>':''}<label class="checkbox"><input type="checkbox" required><span>I have reviewed the needs, proposed fit, evidence and assumptions.</span></label>`,'Mark reviewed',async fd=>{const r=await command('intake-accept-value',{expected:state.intake.draft.ref,confirm:true,rationale:String(fd.get('rationale')||'')});valueReview=false;return r;});return true;
 }
 busy=true;const trigger=document.querySelector(`[data-action="${action}"][data-id="${CSS.escape(id||'')}"]`)||document.querySelector(`[data-action="${action}"]`),prior=trigger?.textContent;
 try{
  if(trigger){trigger.disabled=true;if(action==='value-generate')trigger.textContent='Generating your draft…';}
  if(action==='value-generate')await generateValue();
  else if(action==='value-use'){
   await saveValueProposition();
   if(pageDirty)throw Error('Save your latest edits before using this draft.');
   const r=valueCandidate();if(!r||r.ref.id!==id||!validRun(r))throw Error('Your answers changed. Refresh the proposition again to include them.');
   const text=$('#value-candidate').value;
   await command('intake-coach-apply',{expected:state.intake.draft.ref,run_id:id,field:'value',edited_text:text,confirm:true});
   delete valueCandidateEdits[id];await load();
  }else{
   await saveValueProposition();
   if(pageDirty)throw Error('New edits arrived while saving. Choose this action again to save them.');
   if(action==='value-edit')valueReview=false;
   if(action==='value-review'){intakeStep='value';valueReview=true;valueCoachMode='whole';}
   if(action==='value-dismiss'){valueDismissed.add(id);delete valueCandidateEdits[id];}
   if(action==='value-coach-mode')valueCoachMode=id;
   if(action==='value-focus'){
    if(id==='value'||!id){valueCoachMode='whole';}else{intakeStep=questionSection(id)||intakeStep;valueFocus=id;coachedField=id;valueCoachMode='question';}
    valueReview=false;
   }
  }
  render();if(action==='value-focus')focusIntakeQuestion();
 }catch(e){const error=$('#value-proposition-form .error');if(error)error.textContent=e.message;else toast(e.message);}
 finally{busy=false;if(trigger){trigger.disabled=false;trigger.textContent=prior;}}
 return true;
}
function rememberValueInput(e){
 if(e.target.matches?.('[data-metric-input]')){syncMetricInputs(e.target.closest('#value-proposition-form'));return;}
 if(e.target.id==='value-candidate'){valueCandidateEdits[e.target.dataset.run]=e.target.value;return;}
 if(e.target.closest('#value-proposition-form')&&e.target.name){valueWorking[e.target.name]=e.target.value;pageDirty=true;valueReview=false;if($('#value-save-status'))$('#value-save-status').textContent='Unsaved changes';if($('#question-save-status'))$('#question-save-status').textContent=questionDraftStatus();if($('#value-freshness'))$('#value-freshness').textContent=valueFreshness(valueDraft());}
 if(e.target.closest('#value-coach-form')&&e.target.name==='message')valueMessage=e.target.value;
}
document.addEventListener('input',rememberValueInput);
document.addEventListener('change',rememberValueInput);
document.addEventListener('submit',async e=>{
 if(!['value-proposition-form','value-coach-form'].includes(e.target.id))return;
 e.preventDefault();if(busy)return;busy=true;
 const b=e.submitter||e.target.querySelector('button[type=submit]'),prior=b.textContent,error=e.target.querySelector('.error');error.textContent='';b.disabled=true;
 const coaching=e.target.id==='value-coach-form';b.textContent=coaching?'AI partner is reviewing…':'Saving…';
 const questionSave=b.hasAttribute('data-question-save');if(questionSave&&$('#question-save-status'))$('#question-save-status').textContent='Saving…';
 const scopeKey=()=>typeof reviewerDraftKey==='function'?reviewerDraftKey('intake-coach'):JSON.stringify([state.auth?.account?.id||'',state.actor||'',state.project?.id||state.intake?.draft?.ref?.id||'']);
 const key=scopeKey(),composer=coaching?e.target.querySelector('textarea[name="message"]'):null;
 const whole=valueCoachMode==='whole',field=whole?'':valueFocus;
 let message='',sources=[];
 try{
  if(coaching){
   if(composer?.dataset?.reviewerDraftKey&&composer.dataset.reviewerDraftKey!==key)throw Error('The project or role changed. Reopen the AI partner before asking.');
   message=String(new FormData(e.target).get('message')||'');
   if(!message.trim())throw Error('Enter a question for your AI partner.');
   if(typeof coachInfo==='function'&&coachInfo().model.configured===false)throw Error('Connect a model before asking your AI partner.');
   if(typeof reviewerDraftWriteKey==='function')reviewerDraftWriteKey(key,message);
   else if(typeof intakeReviewerWrite==='function')intakeReviewerWrite(message);
   valueMessage=message;sources=selectedSourceRefs();
  }
  await saveValueProposition();
  if(coaching){
   if(scopeKey()!==key)throw Error('The project or role changed. Reopen the AI partner before asking.');
   if(pageDirty)throw Error('New edits arrived while saving. Send again to include them.');
   await command('intake-coach',{expected:state.intake.draft.ref,skill:whole?'review-value':'coach-field',field,message:message.trim(),sources,consent:true});
   if(scopeKey()!==key)return;
   await load();if(scopeKey()!==key)return;
  }else if(b.value==='review'){
   if(pageDirty)throw Error('New edits arrived while saving. Save again before reviewing.');
   valueReview=true;valueCoachMode='whole';
  }
  render();
 }catch(err){error.textContent=err.message;if(questionSave&&$('#question-save-status'))$('#question-save-status').textContent='Couldn’t save. Try again.';}finally{busy=false;b.disabled=false;b.textContent=prior;}
});

window.addEventListener('beforeunload',e=>{if(Object.keys(valueCandidateEdits).length){e.preventDefault();e.returnValue='';}});

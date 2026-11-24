// A document opens reconsideration; it does not silently replace existing answers.
const changeInfo=()=>state.document_changes||{reviews:[],pending_sources:[]};
const changeReview=id=>changeInfo().reviews.find(r=>r.ref.id===id);
const changeEffects={supports:'Still supported',refines:'Refinement',challenges:'Needs reconsideration','not-addressed':'Not addressed',uncertain:'Unclear'};
const evidenceKinds={'reported-finding':'Reported finding','design-proposal':'Design proposal','policy-claim':'Policy claim',mixed:'Mixed finding and proposal',background:'Background',none:'No supporting passage'};
function changeProposals(r){return Object.entries(r.body.output.assessments).map(([field,v])=>({field,...v})).concat(r.body.output.impacts).filter(i=>i.proposed_text!==null);}
function documentChangeNotice(){
 if(state.actor!=='priya')return '';
 const info=changeInfo(),pending=info.pending_sources.length;
 const latest=pending?info.reviews.find(r=>r.body.trigger_source.id===info.pending_sources.at(-1).id):info.reviews[0];
 if(!pending&&!latest)return '';
 const title=pending?'New material may change your proposition':'Document impact review';
 const message=pending?'Compare the evidence before updating the draft.':latest.body.status==='applied'?'Selected changes are saved in your draft.':latest.body.status==='kept'?'Current wording retained with your rationale.':'Assessment saved for your review.';
 const action=latest?'document-change-open':'document-change-start';
 const id=latest?latest.ref.id:info.pending_sources.at(-1)?.id;
 return `<div class="document-change-notice"><div><strong>${esc(title)}</strong><p class="caption">${esc(message)}</p></div>${button(latest?'Review impact':'Assess impact',action,id,'small')}</div>`;
}
async function assessDocumentChange(source){
 const result=await command('intake-change-assess',{expected:state.intake.draft.ref,trigger_source:source,
  sources:coachInfo().sources.map(s=>s.ref),consent:true});
 if(pageDirty)return {...result,message:'Assessment saved. Save your newer edits, then reassess.',changeResult:null};
 return {...result,changeResult:result.ref.id};
}
function changeAssessmentItem(field,item,current){
 return `<details class="change-assessment"><summary><strong>${esc(shortQuestion(field))}</strong> <span class="caption">${esc(changeEffects[item.effect])}</span></summary><div class="details-body">${para(item.reason)}${tag(evidenceKinds[item.evidence_kind],'purple')}${val('Limits',item.limitation)}${val('Current answer',current)}${item.proposed_text?val('Proposed wording',item.proposed_text):'<p class="caption">No wording change proposed.</p>'}${citationsHtml(item.citations)}</div></details>`;
}
function openDocumentChange(id){
 const r=changeReview(id);if(!r)return;const b=r.body,o=b.output,resolved=['applied','kept'].includes(b.status);
 const changed=changeProposals(r),candidate=o.assessments.value.proposed_text;
 const current=r.stale.length===0;
 const oldDocs=coachInfo().sources.filter(s=>b.sources.some(x=>x.id===s.ref.id)&&s.ref.id!==b.trigger_source.id);
 const decision=b.decisions.at(-1);
 modal('Document impact review',`<p class="caption">${esc(b.trigger_title)} · ${esc(label(b.basis))} · ${esc(b.mode)} assessment</p><h3>${esc({revise:'Revision recommended',retain:'Keep the current proposition',investigate:'Resolve the uncertainty first'}[o.recommendation])}</h3>${para(o.summary)}
 ${(r.quality_flags||[]).length?`<div class="banner signal-notice signal-advisory"><strong>Check before applying</strong>${r.quality_flags.map(i=>`<p><strong>${esc(i.field==='summary'?'Assessment wording':shortQuestion(i.field))}:</strong> ${esc(i.message)}</p>`).join('')}<p class="caption">These checks catch specific errors; they do not certify the assessment.</p></div>`:''}
 ${!current&&!resolved?`<div class="banner signal-notice signal-advisory"><strong>This assessment used an earlier basis.</strong>${r.stale.map(para).join('')}${button('Assess again','document-change-start',b.trigger_source.id,'small')}</div>`:''}
 <div class="change-comparison"><section><h3>Current proposition at assessment</h3>${para(b.values.value||'No proposition yet.')}</section><section><h3>${candidate?'Proposed revision':'Proposition wording'}</h3>${para(candidate||'No change to the proposition wording is proposed.')}</section></div>
 ${!resolved&&current?`<div class="actions change-decisions">${changed.length?`<div class="change-choice">${button('Review & apply changes','document-change-edit',id,'primary')}<span class="caption">Choose edits to save</span></div>`:''}<div class="change-choice">${button('Keep draft unchanged','document-change-keep',id)}<span class="caption">Close this review</span></div><div class="change-choice">${button('Decide later','document-change-defer',id)}<span class="caption">Leave this review open</span></div></div>`:''}
 ${decision?`<div class="banner"><strong>${esc({apply:'Selected changes applied to draft',keep:'Current wording retained',defer:'Review deferred'}[decision.disposition])}</strong>${para(decision.reason)}${decision.not_adopted?.length?`<p class="caption">Proposals not adopted: ${esc(decision.not_adopted.map(shortQuestion).join(', '))}.</p>`:''}<small>${esc(state.actors[decision.actor]?.name||decision.actor)} · ${esc(date(decision.at))} · ${esc(label(decision.result_draft))}</small></div>`:''}
 <details class="section"><summary>What holds and what changes · 9 value components</summary>${Object.entries(o.assessments).sort((a,b)=>Number(b[1].proposed_text!==null)-Number(a[1].proposed_text!==null)).map(([k,v])=>changeAssessmentItem(k,v,b.values[k])).join('')}</details>
 <details class="section"><summary>Related answers and measures · ${o.impacts.length} potential impacts</summary>${o.impacts.map(i=>changeAssessmentItem(i.field,i,b.values[i.field])).join('')||'<p class="caption">No additional answer changes identified in this assessment.</p>'}</details>
 <details class="section"><summary>Requirements and downstream work</summary>${o.requirements.map(i=>`<article class="rule"><strong>${esc(i.target)}</strong>${para(i.reason)}${citationsHtml(i.citations)}</article>`).join('')||`<p>${b.downstream.length?'No impacts were identified among the supplied requirements and drawers. This does not establish that no other work is affected.':'No requirement drawers or requirements exist in this project yet.'}</p>`}<p class="caption">These are proposed review impacts. Requirements, approvals and Jira remain unchanged. Only recorded work in this project was assessed.</p></details>
 ${o.questions.length?`<details class="section"><summary>Unresolved questions · ${o.questions.length}</summary>${o.questions.map(para).join('')}</details>`:''}
 <details class="section"><summary>Source and version record</summary><p>${esc(oldDocs.map(s=>s.body.title).join(', ')||'No earlier document')} compared with ${esc(b.trigger_title)}.</p><p class="caption">Document upload order does not establish authority. Quotations are matched to saved text; interpretations still need review.</p>${b.already_changed_fields.length?`<p>Answers already changed since this upload: ${esc(b.already_changed_fields.map(shortQuestion).join(', '))}. This assessment compares the current saved answers.</p>`:''}<p class="caption">AI partner v${esc(b.agent_version)} · Assessment contract v${esc(b.review_version)} · ${esc(date(b.at))}</p><p class="caption">Retained source versions: ${esc(b.sources.map(label).join(', '))}</p></details>
 ${changeInfo().reviews.length>1?`<details class="section"><summary>Earlier assessments</summary>${changeInfo().reviews.filter(x=>x.ref.id!==id).map(x=>`<div class="ui-action-row">${button(x.body.trigger_title,'document-change-open',x.ref.id,'small')}<span class="caption">${esc(date(x.body.at))} · ${esc(x.body.status)}</span></div>`).join('')}</details>`:''}`);
}
function documentChangeEdit(r){
 const proposals=changeProposals(r).sort((a,b)=>Number(b.field==='value')-Number(a.field==='value'));
 modal('Review & apply changes',`<p>Select the changes to apply. Edit the wording here or later in the intake.</p>${proposals.map(i=>`<details class="change-edit" ${i.field==='value'?'open':''}><summary>${esc(shortQuestion(i.field))}${(r.quality_flags||[]).some(f=>f.field===i.field)?' · Needs correction':''}</summary><div class="details-body">${(r.quality_flags||[]).filter(f=>f.field===i.field).map(f=>`<div class="banner signal-notice signal-advisory">${esc(f.message)}</div>`).join('')}<label class="checkbox"><input type="checkbox" name="selected" value="${esc(i.field)}"><span>Apply this change</span></label>${val('Current answer',r.body.values[i.field])}<label class="form-field"><span>Proposed ${esc(shortQuestion(i.field))}</span><textarea name="edit-${esc(i.field)}" maxlength="20000">${esc(i.proposed_text)}</textarea></label>${para(i.reason)}${citationsHtml(i.citations)}</div></details>`).join('')}${field('reason','Why are you making these changes?','','Record the reasoning that should travel with this version.')}<p class="caption">Saves a draft revision. Unselected proposals stay unchanged and are recorded as not adopted. Requirements and published decisions are preserved.</p>`,'Apply selected changes',async fd=>{
  const changes=Object.fromEntries(fd.getAll('selected').map(k=>[k,String(fd.get('edit-'+k))]));
  if(!Object.keys(changes).length)throw Error('Choose at least one edit to apply.');
  const result=await command('intake-change-resolve',{expected:state.intake.draft.ref,review:r.ref,disposition:'apply',reason:fd.get('reason'),changes,confirm:true});
  valueWorking={};return {...result,changeResult:r.ref.id};
 });
}
async function documentChangeAction(action,id){
 if(!action.startsWith('document-change-'))return false;
 if(pageDirty){await saveCoachedField();if(pageDirty)throw Error('Save your latest edits before reviewing document impact.');}
 if(action==='document-change-open'){openDocumentChange(id);return true;}
 if(action==='document-change-start'){
  await saveCoachedField();if(pageDirty)throw Error('Save your latest edits before assessing the document.');
  const source=coachInfo().sources.find(s=>s.ref.id===id);if(!source)return true;
  modal('Assess document impact',`<p>Compare <strong>${esc(source.body.title)}</strong> with the saved proposition and ${coachInfo().sources.length-1} earlier document${coachInfo().sources.length===2?'':'s'}.</p><p class="caption">The configured model receives these documents, saved intake and recorded requirements. Existing answers stay intact.</p>`,'Assess impact',()=>assessDocumentChange(source.ref),{busyLabel:'Comparing documents…'});return true;
 }
 const r=changeReview(id);if(!r)return true;
 if(action==='document-change-edit'){documentChangeEdit(r);return true;}
 if(action==='document-change-keep'||action==='document-change-defer'){
  const keep=action==='document-change-keep';
  modal(keep?'Keep draft unchanged':'Decide later',`${field('reason',keep?'Why keep the current draft?':'What needs to be resolved before deciding?')}<p class="caption">${keep?'Closes this document review without applying its recommendations.':'Leaves this document review open. You can return to it later.'}</p>`,keep?'Keep draft unchanged':'Save for later',async fd=>({...await command('intake-change-resolve',{expected:state.intake.draft.ref,review:r.ref,disposition:keep?'keep':'defer',reason:fd.get('reason'),confirm:true}),changeResult:r.ref.id}));return true;
 }
 return false;
}

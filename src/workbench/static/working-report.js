"use strict";
// One editable findings document alongside the existing conversation.
let domainWorkMode='conversation',workingReportSaving=false,sharedReportFocus=null,findingsSavePromise=null,findingsSaveTimer=null;
const workingReportDrafts=new Map();
function findingsText(work=chatWork()){
 const b=work?.body||{},report=b.working_report;
 if(report){const entries=report.entries||[];if(report.format==='document'&&entries.length===1)return entries[0].text;return entries.map(e=>e.heading+'\n'+e.text).join('\n\n');}
 if(!b.observation||/^Working material[;:]/.test(b.observation))return '';
 return Object.entries({observation:'Finding',interpretation:'Interpretation',recommendation:'Recommendation',limitation:'Limits and uncertainty'}).filter(([key])=>b[key]).map(([key,title])=>title+'\n'+b[key]).join('\n\n');
}
function reportDraft(){const key=chatKey(),work=chatWork(),old=workingReportDrafts.get(key);if(!old||!old.dirty&&label(old.expected||{})!==label(work?.ref||{}))workingReportDrafts.set(key,{expected:work?.ref?{...work.ref}:null,document:findingsText(work),dirty:false,error:null});return workingReportDrafts.get(key);}
function hasUnsavedWorkingReport(){return !!state?.project&&!!workingReportDrafts.get(chatKey())?.dirty;}
function domainWorkTabs(){return '';}
function reportCitations(entry){
 const citations=entry.citations||[],requirements=entry.requirement_refs||[];
 if(!citations.length&&!requirements.length&&!entry.origin&&!entry.origins?.length)return '';
 return `<details class="report-evidence"><summary>Sources & origin</summary>${entry.origins?.length?`<p class="caption">Developed through ${entry.origins.length} source-linked conversation finding${entry.origins.length===1?'':'s'}. Sources support the draft; this is not requirement approval.</p>`:''}${entry.origin?`<p class="caption">Selected AI partner suggestion · ${esc(entry.origin.mode)} · ${technicalRef(entry.origin.review)}${entry.origin.historical_confirmed?' · Earlier inputs reviewed by the author':''}</p>`:''}${citations.map(c=>`<div class="report-citation">${c.ref?`<strong>${esc(referenceText(c.ref,get(c.ref.id)))}</strong><small>${technicalRef(c.ref)}${c.page?' · page '+c.page:''}</small>`:`<small>${esc(domainFieldLabels[c.basis]||c.basis||'Draft excerpt')}</small>`}${c.quote?`<blockquote>${esc(c.quote)}</blockquote>`:''}</div>`).join('')}${requirements.length?`<p class="caption">Requirements: ${requirements.map(technicalRef).join(' · ')}</p>`:''}</details>`;
}
function workingReportRead(body,heading=true){const report=body.working_report;if(!report)return '';return `<section class="working-report-read workbench-created-surface">${heading?'<h2>Outcomes report</h2>':''}${report.entries.map(e=>`<article class="report-read-section">${report.format==='document'?'':`<h3>${esc(e.heading)}</h3>`}${para(e.text)}${reportCitations(e)}</article>`).join('')||'<p class="caption">No Outcomes report saved.</p>'}<p class="caption">${body.status==='published-for-review'?'Published Outcomes report':'Saved Outcomes report'} · ${esc(date(report.saved_at))}. Sharing is separate from requirement approval.</p></section>`;}
function reportHistoryControl(work){const history=(chatInfo().working_history||[]).filter(h=>h.ref.id===work?.ref.id&&h.ref.revision!==work.ref.revision);return history.length?`<details class="report-version-history"><summary>Earlier Outcomes reports (${history.length})</summary><p class="caption">Earlier versions are read only. Editing creates a new draft version.</p><label class="form-field"><span>Read an earlier version</span><select id="working-report-history"><option value="">Choose a saved version</option>${history.map(h=>`<option value="${h.ref.revision}">Version ${h.ref.revision} · ${h.section_count} finding${h.section_count===1?'':'s'} · ${esc(date(h.saved_at))}</option>`).join('')}</select></label></details>`:'';}

function findingsUndo(){const work=chatWork(),update=work?.body.working_report?.conversation_update;return !hasUnsavedWorkingReport()&&update&&label(update.after)===label(work.ref)?'<a class="item-title-link" href="#findings-document" data-action="wreport-undo">Undo last update</a>':'';}
function findingsAlreadyShared(){const fact=domainInfo().deliverables?.[chatWork()?.ref.id];return !hasUnsavedWorkingReport()&&fact?.state==='published'&&!fact.preview_outdated;}
function findingsSaveLabel(){const d=reportDraft();return d.error?'Not saved · '+d.error:workingReportSaving||d.dirty?'Saving…':findingsAlreadyShared()?'Shared':d.expected?'Saved':'Private draft';}
function findingsReferences(){const work=chatWork(),report=work?.body.working_report;return `<details class="findings-reference"><summary>Source lineage</summary><div class="findings-reference-body">${(report?.entries||[]).map(reportCitations).join('')}</div></details><details class="findings-reference"><summary>Sources & history</summary><div class="findings-reference-body">${(report?.entries||[]).map(reportCitations).join('')}${work?`<div class="workflow-card-actions">${button('Supporting details','wreport-details',work.ref.id,'small')}</div>${reportHistoryControl(work)}`:''}${work&&(domainInfo().deliverables?.[work.ref.id]?.published)?`<p><a class="item-title-link workbench-document-link" href="#main" data-action="wreport-bridge" data-id="${esc(domainInfo().deliverables[work.ref.id].published.id)}">Published version</a></p>`:''}${(domainInfo().handoffs||[]).filter(h=>h.body.draft.id===work?.ref.id&&h.body.packet).map(h=>`<p><a class="item-title-link" href="#main" data-action="packet" data-id="${esc(h.body.packet.id+'|'+h.body.packet.revision)}">Context packet</a> <span class="caption">${technicalRef(h.body.draft)}</span></p>`).join('')}</div></details>`;}
function workingReportEditor(){
 if(typeof submissionEditor==='function')return submissionEditor();
 const d=reportDraft();return `<aside id="domain-sharing-panel" class="chat-findings domain-sharing-panel workbench-created-surface" aria-label="Outcomes report"><header class="findings-header domain-panel-header"><div><h2>Outcomes report</h2><p id="working-report-status" class="caption" role="status" aria-live="polite">${esc(findingsSaveLabel())}</p></div><button type="button" class="quiet icon" data-action="dchat-panel-close" aria-label="Close Outcomes report">✕</button></header><div class="sharing-draft-actions"><button type="button" class="compact-text-action" data-action="dchat-draft-sharing" ${busy?'disabled':''}>Draft from this chat</button><p class="caption">Review and edit what the project should receive.</p></div><div id="findings-extra-actions" class="findings-save-row" ${findingsUndo()||d.error?'':'hidden'}><span id="findings-undo-control">${findingsUndo()}</span><button type="button" id="findings-save-retry" class="small" data-action="wreport-save" ${d.error?'':'hidden'}>Retry save</button></div><label class="sr-only" for="findings-document">Edit Outcomes report</label><textarea id="findings-document" class="findings-document" data-findings-document maxlength="20000" placeholder="Describe the results, evidence, open questions and project implications, or draft from this chat." ${busy&&!workingReportSaving?'disabled':''}>${esc(d.document)}</textarea><footer>${typeof downstreamDomainBriefs==='function'?downstreamDomainBriefs():''}<div class="sharing-preview-action"><button type="button" data-action="wreport-share" ${busy||!d.document.trim()||findingsAlreadyShared()?'disabled':''}>${findingsAlreadyShared()?'Shared':'Review sharing preview'}</button></div><details class="findings-reference"><summary>Sources & history</summary><div class="findings-reference-body">${(chatWork()?.body.working_report?.entries||[]).map(reportCitations).join('')}${chatWork()?reportHistoryControl(chatWork()):''}</div></details></footer></aside>`;
}
function reportIsFocused(id){return sharedReportFocus===id;}
function reportBridgeEditButton(r){const own=records('contribution-draft').find(d=>d.body.owner===state.actor&&d.body.published_id===r.ref.id);return own?button('Edit Outcomes report','wreport-edit',own.ref.id):'';}
async function openWorkbenchReport(id){
 await saveWorkingReport();let work=id?records('contribution-draft').find(r=>r.ref.id===id):chatWork();if(!work||work.body.owner!==state.actor||work.body.domain_key&&work.body.domain_key!==state.domains?.active)throw Error('Open the Outcomes report from your own workbench.');
 const dialog=document.querySelector('#modal');if(dialog?.open){if(dirty&&dialog.querySelector('textarea')){closeModal();if(dialog.open)return;}else{dialog.close();dirty=false;}}
 if(work.body.submission_of)work=records('contribution-draft').find(r=>r.ref.id===work.body.submission_of.draft_id)||work;
 view='contributions';selected=work.ref.id;domainPanels.set(chatKey(),'sharing');render();document.getElementById('findings-document')?.focus();
}
async function openSharedReport(id){await saveWorkingReport();if(!records('contribution').some(r=>r.ref.id===id))throw Error('This shared work is not available.');view='review';bridgeSection='work';selected=null;sharedReportFocus=id;render();}
function findingReportButton(){return '';}
function syncFindingsStatus(){const status=document.getElementById('working-report-status');if(status)status.textContent=findingsSaveLabel();const undo=document.getElementById('findings-undo-control');if(undo)undo.innerHTML=findingsUndo();const extra=document.getElementById('findings-extra-actions');if(extra)extra.hidden=!findingsUndo()&&!reportDraft().error;const retry=document.getElementById('findings-save-retry');if(retry)retry.hidden=!reportDraft().error;const share=document.querySelector('[data-action="wreport-share"]');if(share)share.disabled=busy||!reportDraft().document.trim()||findingsAlreadyShared();}
async function saveWorkingReport(options={}){
 if(typeof hasUnsavedDevelopmentEditors==='function'&&hasUnsavedDevelopmentEditors())await saveDevelopmentEditors();
 if(typeof hasUnsavedSubmission==='function'&&hasUnsavedSubmission())await saveSubmission();
 if(findingsSaveTimer){clearTimeout(findingsSaveTimer);findingsSaveTimer=null;}
 if(findingsSavePromise){await findingsSavePromise;if(!hasUnsavedWorkingReport())return;}
 const d=reportDraft();if(!d.dirty)return;if(busy&&!workingReportSaving)throw Error('Wait for the current reply. Your Outcomes report text is retained.');
 const session=chatSession(),snapshot=d.document;let key=chatKey();workingReportSaving=true;d.error=null;syncFindingsStatus();
 findingsSavePromise=(async()=>{
  try{
   if(!chatThread()){await chatEnsure();if(chatSession()!==session)throw Error('The workbench changed. Your Outcomes report text is retained.');if(chatKey()!==key){workingReportDrafts.delete(key);key=chatKey();workingReportDrafts.set(key,d);}d.expected={...chatWork().ref};}
   const result=await command('domain-findings-save',{conversation:chatThread().ref,expected:d.expected,document:snapshot});await load();
   if(chatSession()!==session||chatKey()!==key)throw Error('The workbench changed. The saved Outcomes report remains in their original project.');
   d.expected=result.ref;d.dirty=d.document!==snapshot;
  }catch(error){d.error=error.message;throw error;}
  finally{workingReportSaving=false;findingsSavePromise=null;syncFindingsStatus();}
 })();
 await findingsSavePromise;
 if(d.dirty){if(options.background)scheduleFindingsSave();else throw Error('New text arrived while saving. Your text is retained; try again when ready.');}
}
function scheduleFindingsSave(){if(findingsSaveTimer)clearTimeout(findingsSaveTimer);const key=chatKey();findingsSaveTimer=setTimeout(()=>{findingsSaveTimer=null;if(chatKey()===key)saveWorkingReport({background:true}).catch(()=>{});},900);}
function reportEdited(){const d=reportDraft();d.dirty=true;d.error=null;syncFindingsStatus();scheduleFindingsSave();}
async function saveWorkingReportBeforeAction(action){if(action.startsWith('kc-'))return;if(typeof hasUnsavedDevelopmentEditors==='function'&&hasUnsavedDevelopmentEditors())await saveDevelopmentEditors();if(typeof hasUnsavedSubmission==='function'&&hasUnsavedSubmission())await saveSubmission();if(hasUnsavedWorkingReport()&&!['app-menu','wreport-save'].includes(action))await saveWorkingReport();}
async function workingReportAction(action,id){
 if(!action.startsWith('wreport-'))return false;
 if(action==='wreport-edit'||action==='wreport-view')await openWorkbenchReport(action==='wreport-edit'?id:chatWork()?.ref.id);
 else if(action==='wreport-bridge')await openSharedReport(id);
 else if(action==='wreport-save'){await saveWorkingReport();render();}
 else if(action==='wreport-details'){await saveWorkingReport();domainEdit(chatWork());}
 else if(action==='wreport-undo'){await saveWorkingReport();await command('domain-findings-undo',{conversation:chatThread().ref,expected:chatWork().ref});await load();workingReportDrafts.delete(chatKey());render();}
 else if(['wreport-share','wreport-preflight','wreport-review'].includes(action)){
  await saveWorkingReport();if(!chatThread())await chatEnsure();const result=await command('domain-findings-prepare',{conversation:chatThread().ref,expected:chatWork().ref});await load();render();domainHandoff(result.domainHandoff);
 }
 return true;
}
document.addEventListener('input',e=>{if(e.target.matches?.('[data-findings-document]')){reportDraft().document=e.target.value;reportEdited();}});
document.addEventListener('focusout',e=>{if(e.target.matches?.('[data-findings-document]'))saveWorkingReport({background:true}).catch(()=>{});});
document.addEventListener('change',async e=>{if(e.target.id==='working-report-history'&&e.target.value){const version={id:chatWork().ref.id,revision:Number(e.target.value)},session=chatSession();e.target.value='';try{const h=await command('domain-report-read',{conversation:chatThread().ref,version});if(chatSession()!==session)return;modal('Earlier Outcomes reports',`<p class="caption">Outcomes report · Version ${h.ref.revision} · Read only</p>${sourceDetails([h.ref])}${workingReportRead({working_report:h.report})}`,null,null);}catch(error){toast(error.message);}}});

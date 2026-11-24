'use strict';
let deliverySource=null;
function deliverySourceSelection(){return deliverySource?.project===state.project.id&&deliverySource?.version===state.project.version&&deliverySource?.actor===state.actor?deliverySource.id:null;}
function requirementDeliveryDraft(record){
 const drafts=(state.delivery?.drafts||[]).filter(d=>d.body.requirements.some(r=>r.id===record.ref.id));
 return drafts.find(d=>!d.changed?.length&&d.body.requirements.some(r=>r.id===record.ref.id&&r.revision===record.ref.revision))||drafts[0];
}
function requirementDeliveryStaging(record){
 if(!record||!['priya','alex'].includes(state.actor))return '';
 const stage=requirementDeliveryDraft(record);
 const exact=stage&&stage.body.requirements.some(r=>r.id===record.ref.id&&r.revision===record.ref.revision)&&!stage.changed?.length;
 const status=stage?(exact?'Staged · not sent':'Needs refresh · not sent'):'Not staged here';
 return `<p class="delivery-staging-signal"><span class="caption">Jira / ADO · Shared v${esc(record.ref.revision)} · ${status}</span><a href="#delivery-staging" data-action="delivery-stage-requirement" data-id="${esc(record.ref.id)}">${stage?'Review staging':'Stage Jira / ADO'}</a></p>`;
}
function deliveryScreen(){
 const deliverySourceId=deliverySourceSelection(),info=state.delivery,requirements=records('requirement'),drafts=info.drafts||[],selectedDraft=drafts.find(d=>d.ref.id===selected)||(deliverySourceId?drafts.find(d=>d.body.requirements.some(r=>r.id===deliverySourceId)):drafts[0]);
 return head('Handoff','Review Jira or Azure DevOps changes before sending.')+
 `<div class="banner blue"><strong>Staging only · nothing sent</strong><p>${esc(info.write_status)} A live push requires destination metadata, authenticated access and authorization of the exact payload.</p></div><div class="grid cols section"><div><section class="card"><h2>Stage a transaction</h2><form id="delivery-form"><div class="error" role="alert"></div><div class="grid two"><label class="form-field"><span>Delivery tool</span><select name="target" id="delivery-target"><option value="jira">Jira</option><option value="ado">Azure DevOps</option></select></label><label class="form-field"><span>Existing project key or name</span><input name="destination" placeholder="e.g. CLINIC"></label><label class="form-field"><span>Work item type</span><select name="work_item_type" id="delivery-kind">${info.types.jira.map(t=>`<option>${esc(t)}</option>`).join('')}</select></label><label class="form-field"><span>Parent (optional)</span><input name="parent" placeholder="Jira key or full ADO work-item URL"></label></div><p class="caption">A requirement is not automatically a user story. Review it with the delivery owner.</p><h3>Source requirements</h3>${requirements.map(r=>`<div class="delivery-source-item"><label class="checkbox selectable"><input type="checkbox" name="requirements" value="${esc(r.ref.id)}" ${r.ref.id===deliverySourceId?'checked':''}><span><strong>${esc(r.body.title)}</strong><small>Version ${r.ref.revision} · ${esc(r.body.status)}</small></span></label><details><summary>Requirement & criteria</summary><div class="details-body">${para(r.body.text)}${val('Acceptance criteria',r.body.acceptance_criteria)}${technicalRef(r.ref)}</div></details></div>`).join('')||'<p>Publish requirement candidates from the Business Intent first.</p>'}<button type="submit" class="primary" ${requirements.length?'':'disabled'}>Stage transaction</button></form></section>${selectedDraft?deliveryPreview(selectedDraft):''}</div><aside><section class="card"><h2>Staged transactions</h2>${drafts.map(d=>`<div class="rule">${sourceDetails([d.ref])}<p>${esc(d.body.target==='jira'?'Jira':'Azure DevOps')} · ${esc(d.body.destination||'Destination not set')} · ${d.changed.length?'Needs refresh · not sent':'Not sent'}</p>${button('Review transaction','delivery-open',d.ref.id,'compact-text-action')}</div>`).join('')||'<p class="caption">No transactions staged yet. Select source requirements to begin.</p>'}</section><section class="card section"><h2>Delivery guidance</h2><details class="acx-disclosure"><summary>What maps where?</summary><div class="details-body">${info.mapping.map(m=>`<details><summary>${esc(m.source)}</summary><div class="details-body">${val('Jira',m.jira)}${val('Azure DevOps',m.ado)}${para(m.rule)}</div></details>`).join('')}</div></details><details class="acx-disclosure"><summary>Sending steps</summary><div class="details-body"><ol class="checklist"><li>Prepare and review the exact requirement/story and acceptance criteria.</li><li>Resolve destination issue types, required fields, parent relationships and duplicate mappings.</li><li>Authorize the exact payload, source versions and destination.</li><li>The connector creates or updates the item and records its external ID, URL and receipt.</li><li>Reconcile an uncertain write before retrying. Later requirement changes prepare a new reviewed update.</li></ol><p class="caption">This branch implements saved previews and local export. External authentication, writes, receipts and synchronization are not yet connected.</p></div></details></section></aside></div>`;
}
function deliveryPreview(d){const b=d.body;return `<section class="card section"><div class="card-head"><h2>Staged transaction</h2>${tag('Not sent')}</div>${val('Destination',b.target+' · '+(b.destination||'Not configured'))}${sourceDetails([d.ref])}${d.changed.length?'<p class="banner signal-notice signal-advisory">A source requirement has changed. Prepare a fresh preview before export.</p>':''}${b.items.map(i=>`<article class="rule"><div class="card-head"><h3>${esc(i.title)}</h3></div>${para(i.requirement)}<details open><summary>Acceptance criteria</summary>${para(i.acceptance_criteria||'Not yet specified')}</details>${i.warnings.map(w=>`<p class="caption">${esc(w)}</p>`).join('')}<details><summary>Payload & traceability</summary>${technicalRef(i.source)}<pre class="settings-instructions">${esc(JSON.stringify({source:i.source,goal_refs:i.goal_refs,measure_refs:i.measure_refs,drawer_id:i.drawer_id,method:i.method,endpoint:i.endpoint,content_type:i.content_type,payload:i.payload,idempotency_key:i.idempotency_key},null,2))}</pre></details></article>`).join('')}<div class="actions">${button('Export JSON','delivery-export',d.ref.id)}<button disabled>Send to ${esc(b.target==='jira'?'Jira':'Azure DevOps')}</button></div><p class="caption">Live connector not configured · export only, no ticket is created.</p></section>`;}
async function deliveryAction(action,id){
 if(!action.startsWith('delivery-'))return false;
 if(action==='delivery-stage-requirement'){
  await saveBeforeProjectChange();
  const requirement=get(id);if(requirement?.kind!=='requirement')throw Error('Publish this requirement before staging a transaction.');
  deliverySource={id,project:state.project.id,version:state.project.version,actor:state.actor};view='delivery';selected=requirementDeliveryDraft(requirement)?.ref.id||null;render();const heading=$('#main h1');if(heading){heading.tabIndex=-1;heading.focus();}return true;
 }
 if(action==='delivery-open'){view='delivery';selected=id;render();}
 else if(action==='delivery-export'){
  const d=state.delivery.drafts.find(d=>d.ref.id===id);
  // D014: the server rechecks access and basis just before export; open challenges need an acknowledgment.
  const download=result=>{const url=URL.createObjectURL(new Blob([JSON.stringify(result.export,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='workbench-'+d.ref.id+'.json';a.click();URL.revokeObjectURL(url);toast(result.message);};
  let result;
  try{result=await command('delivery-export',{expected:d.ref});}
  catch(error){if(!/Acknowledge/.test(error?.message||''))throw error;
   modal('Open challenges on this basis',`<p>${esc(error.message)}</p><label class="checkbox"><input type="checkbox" name="acknowledge" required><span>Export anyway; the challenges stay open in Decisions &amp; Issues.</span></label>`,'Export',async fd=>{const r=await command('delivery-export',{expected:d.ref,acknowledge_open_issues:fd.get('acknowledge')==='on'});download(r);return r;});
   return true;}
  download(result);
 }
 return true;
}
document.addEventListener('change',e=>{if(e.target.id==='delivery-target')$('#delivery-kind').innerHTML=state.delivery.types[e.target.value].map(t=>`<option>${esc(t)}</option>`).join('');});
document.addEventListener('submit',async e=>{
 if(e.target.id!=='delivery-form')return;e.preventDefault();const form=e.target,submit=e.submitter;submit.disabled=true;
 try{const fd=new FormData(form),result=await command('delivery-prepare',{target:fd.get('target'),destination:fd.get('destination'),parent:fd.get('parent'),work_item_type:fd.get('work_item_type'),requirements:fd.getAll('requirements').map(id=>get(id).ref)});await load();selected=result.id;render();toast(result.message);}catch(error){form.querySelector('.error').textContent=error.message;}finally{submit.disabled=false;}
});

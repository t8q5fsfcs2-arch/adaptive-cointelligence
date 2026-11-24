// Categories organize SME-owned areas; each area carries review criteria and its own draft.
function scaffoldLeaves(){return (state.intake.draft?.body.scaffold||[]).flatMap(d=>[d,...(d.children||[]).map(c=>({...c,key:d.key+'/'+c.key,included:d.included&&c.included,category:d.label}))]);}
function criterionList(text){return `<ul class="criteria-list">${String(text||'').split('\n').filter(x=>x.trim()).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;}
function areaCriteria(d){return d.criteria?`<section class="area-criteria"><h4>Review criteria</h4>${criterionList(d.criteria)}<details><summary>Evidence, references & reassessment</summary><div class="details-body">${val('Evidence to provide',d.evidence)}${val('Reassess when',d.revisit)}${d.references?val('Method or standard · confirm applicability',d.references):''}</div></details></section>`:'';}
function areaRead(d,catalog){return `<details class="subdrawer-read"><summary>${esc(d.label)}${!d.included?' · Excluded':''}</summary><div class="details-body">${para(d.question)}${typeof draftGoalLinksRead==='function'?draftGoalLinksRead(d,catalog):''}${typeof projectFocus==='function'?projectFocus(d):''}${areaCriteria(d)}${val('Investigation lead',state.actors[d.owner]?.name)}${d.included?`${requirementEntriesRead(d,d.key)||'<p class="caption">Requirement not yet drafted.</p>'}`:val('Reason for exclusion',d.exclusion_reason)}</div></details>`;}
function requirementDrafts(area,path){
 if(Array.isArray(area.requirements))return area.requirements;
 return area.requirement?.trim()||area.acceptance_criteria?.trim()?[{id:'REQ-INTAKE-'+path,title:area.label+' · initial requirement',requirement:area.requirement||'',acceptance_criteria:area.acceptance_criteria||'',included:true}]:[];
}
function requirementEntryControl(id,field){return 'draft-'+encodeURIComponent(id)+'-'+field;}
function requirementEntriesRead(area,path){return requirementDrafts(area,path).map(r=>`<section class="requirement-candidate"><h4>${esc(r.title||'Untitled requirement')}${r.included===false?' · Excluded':''}</h4>${val('Proposed requirement',r.requirement||'Not yet drafted')}${val('Acceptance criteria',r.acceptance_criteria||'Not yet defined')}</section>`).join('');}
function requirementEntryRow(r,area,path,transient=false){
 const focus=requirementEntryControl(r.id,r.requirement?.trim()&&!r.acceptance_criteria?.trim()?'acceptance_criteria':'requirement');
 const shared=(state.records||[]).find(x=>x.kind==='requirement'&&x.ref.id===r.id);
 const researchUpdate=shared&&(state.records||[]).some(v=>v.kind==='need-context'&&(v.body.review_items||[]).some(i=>i.target.id===shared.ref.id));
 const changed=shared&&(shared.body.text!==r.requirement||shared.body.acceptance_criteria!==r.acceptance_criteria||shared.body.title!==(r.title||area.label+' · initial requirement'));
 const status=r.included===false?'Excluded':changed?'Changes need review':shared?'Shared · '+shared.body.status:!r.requirement?.trim()?'Not yet drafted':!r.acceptance_criteria?.trim()?'Needs acceptance criteria':'Draft';
 const control=(field,title,help,multiline=true)=>{const id=requirementEntryControl(r.id,field);return `<label class="form-field" for="${esc(id)}"><span id="${esc(id)}-label">${title}</span><span class="field-help" id="${esc(id)}-help">${help}</span>${multiline?`<textarea id="${esc(id)}" name="${field}" data-requirement-field="${field}" aria-labelledby="${esc(id)}-label" aria-describedby="${esc(id)}-help" maxlength="20000">${esc(r[field]||'')}</textarea>`:`<input id="${esc(id)}" name="${field}" data-requirement-field="${field}" aria-labelledby="${esc(id)}-label" aria-describedby="${esc(id)}-help" maxlength="20000" value="${esc(r[field]||'')}">`}</label>`;};
 return `<details class="requirement-draft" data-requirement-id="${esc(r.id)}" data-area-path="${esc(path)}" data-planning-detail="candidate-${esc(r.id)}" ${transient?'data-transient="true"':''}><summary><span class="workbench-object-heading"><span class="workbench-object-type">Requirement</span><a class="planning-text-link" href="#${esc(encodeURIComponent(focus))}" data-action="sponsor-planning-focus" data-id="${esc(focus)}">${esc(r.title||'Untitled requirement')}</a></span><span class="caption">${status}${researchUpdate?' · Research update':''}</span></summary>
 <div class="requirement-entry-body">${shared?`<p class="caption"><a class="item-title-link" href="#main" data-action="requirement" data-id="${esc(shared.ref.id)}">Shared version · v${esc(shared.ref.revision)} · ${esc(shared.body.status||'Recorded')}</a></p>`:''}${shared&&typeof needContextRequirementNotice==='function'?needContextRequirementNotice(shared):''}${typeof requirementDeliveryStaging==='function'?requirementDeliveryStaging(shared):''}${changed?'<p class="caption">These edits are private. Open the shared version to review its current wording, criteria and approval history.</p>':''}<fieldset class="requirement-fields" data-coach-path="${esc(path)}" data-requirement-id="${esc(r.id)}"><legend class="sr-only">${esc(r.title||'Requirement draft')}</legend>
 ${control('title','Requirement name','Use a short name that distinguishes this requirement.',false)}
 ${control('requirement','What must be true?','Describe one required behavior or condition, including who or what it applies to.')}
 ${control('acceptance_criteria','Acceptance criteria','Describe observable checks that demonstrate this requirement is met. Use one check per line.')}
 <label class="checkbox"><input type="checkbox" data-requirement-field="included" ${r.included!==false?'checked':''}>Include in this direction</label></fieldset>
 ${typeof requirementAgentControls==='function'?requirementAgentControls({...area,key:path,requirement_id:r.id,requirement:r.requirement,included:area.included&&r.included!==false}):''}
 ${transient?button('Discard unsaved requirement','requirement-entry-discard',r.id,'compact-text-action'):''}</div></details>`;
}
function requirementEntryList(area,path,title='Requirements'){
 const rows=requirementDrafts(area,path);
 return `<section class="area-requirements" id="area-requirements-${esc(path.replaceAll('/','--'))}" tabindex="-1"><header class="planning-area-toolbar"><h4>${title}</h4><button type="button" class="compact-icon-action" data-action="requirement-entry-add" data-id="${esc(path)}" aria-label="Add requirement to ${esc(area.label)}" title="Add requirement"><svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M8 2v12M2 8h12"/></svg></button></header>
 <div class="requirement-list" data-requirement-list="${esc(path)}">${rows.map(r=>requirementEntryRow(r,area,path)).join('')}</div>${!rows.length?'<p class="caption requirement-empty">No requirements yet. Use + to add one.</p>':''}</section>`;
}
function updateRequirementAreaStatus(list){
 const summary=list.closest('.subdrawer-edit')?.querySelector(':scope > summary > .caption');if(!summary||summary.textContent==='Excluded')return;
 const rows=[...list.querySelectorAll('.requirement-draft')].filter(x=>x.querySelector('[data-requirement-field="included"]').checked);
 const missing=rows.filter(x=>x.querySelector('[data-requirement-field="requirement"]').value.trim()&&!x.querySelector('[data-requirement-field="acceptance_criteria"]').value.trim()).length;
 summary.textContent=!rows.length?'Not yet drafted':rows.length+' requirement'+(rows.length===1?'':'s')+(missing?' · Needs acceptance criteria':'');
}
async function requirementEntryAction(action,id){
 if(!action.startsWith('requirement-entry-'))return false;
 if(action==='requirement-entry-add'){
  const area=scaffoldLeaves().find(x=>x.key===id);if(!area)throw Error('Reload this requirement area.');
  const list=[...document.querySelectorAll('[data-requirement-list]')].find(x=>x.dataset.requirementList===id);if(!list)return true;
  if(list.children.length>=100)throw Error('Use at most one hundred requirements per area.');
  const r={id:'REQ-INTAKE-'+id+'--'+crypto.randomUUID().replaceAll('-','').slice(0,20),title:'',requirement:'',acceptance_criteria:'',included:true};
  list.insertAdjacentHTML('beforeend',requirementEntryRow(r,area,id,true));list.parentElement.querySelector('.requirement-empty')?.remove();
  const row=list.lastElementChild;row.open=true;row.querySelector('input[data-requirement-field="title"]').focus();updateRequirementAreaStatus(list);pageDirty=true;return true;
 }
 if(action==='requirement-entry-discard'){
  const row=[...document.querySelectorAll('.requirement-draft')].find(x=>x.dataset.requirementId===id);
  if(!row||row.dataset.transient!=='true')throw Error('Saved requirements are retained. Exclude them from direction instead.');
  if([...row.querySelectorAll('input[type="text"],input:not([type]),textarea')].some(x=>x.value.trim())&&!confirm('Discard this unsaved requirement?'))return true;
  const list=row.parentElement;row.remove();updateRequirementAreaStatus(list);pageDirty=true;list.closest('.area-requirements').querySelector('button').focus();return true;
 }
 return false;
}
document.addEventListener('input',event=>{
 if(!event.target.matches('[data-requirement-field]'))return;
 const row=event.target.closest('.requirement-draft');if(!row)return;
 if(event.target.dataset.requirementField==='title')row.querySelector('summary a').textContent=event.target.value||'Untitled requirement';
 const read=k=>row.querySelector(`[data-requirement-field="${k}"]`),status=row.querySelector('summary .caption');
 status.textContent=!read('included').checked?'Excluded':!read('requirement').value.trim()?'Not yet drafted':!read('acceptance_criteria').value.trim()?'Needs acceptance criteria':'Draft';
 updateRequirementAreaStatus(row.parentElement);
});
function drawerFields(d,path,child=false,categorySettings=false,multiple=false){
 const n=path.replaceAll('/','--');
 const metadata=`<div class="form-field"><label for="drawer-label-${n}">${child?'Sub-drawer':'Category'} name</label><input id="drawer-label-${n}" name="label" value="${esc(d.label)}" required maxlength="20000"></div>${roleSelect('owner','Investigation lead',d.owner).replaceAll('intake-owner','owner-'+n)}${drawerEditField(n,'question','Question to resolve',d.question,true)}${drawerEditField(n,'rationale','Why this area belongs',d.rationale,true)}`;
 return `<fieldset class="scaffold-fields" data-coach-path="${esc(path)}"><legend class="sr-only">${esc(d.label)}</legend><label class="checkbox"><input type="checkbox" name="included" ${d.included?'checked':''} ${d.configured_applicable===false?'disabled':''}>Include ${child?'this sub-drawer':'this category'}</label>${child?`<div class="form-field area-exclusion"><label for="exclude-${n}">Reason if excluded</label><input id="exclude-${n}" name="exclusion_reason" value="${esc(d.exclusion_reason||'')}" maxlength="20000"></div>`:''}${categorySettings?metadata:`<details class="area-metadata"><summary>Definition &amp; ownership</summary><div class="details-body">${metadata}</div></details>`}${typeof goalLinkEditor==='function'?goalLinkEditor(d):''}${typeof focusEditor==='function'?focusEditor(d,n):''}${!multiple&&(child||!d.children?.length||d.requirement||(categorySettings&&d.acceptance_criteria))?`<details class="area-draft" data-planning-detail="fields-${esc(path)}" ${d.requirement?'open':''}><summary>${d.requirement?'Draft requirement':'Write a draft requirement'}</summary><div class="details-body">${drawerEditField(n,'requirement','What must be true?',d.requirement)}${drawerEditField(n,'acceptance_criteria','Acceptance criteria',d.acceptance_criteria)}</div></details>`:`<input type="hidden" name="requirement" value="${esc(d.requirement||'')}"><input type="hidden" name="acceptance_criteria" value="${esc(d.acceptance_criteria||'')}">`}</fieldset>`;
}
function planningAreaStatus(d,parentIncluded=true,path=d.key){
 if(!parentIncluded||!d.included)return 'Excluded';
 const rows=requirementDrafts(d,path).filter(x=>x.included!==false),missing=rows.filter(x=>x.requirement?.trim()&&!x.acceptance_criteria?.trim()).length;
 return !rows.length?'Not yet drafted':`${rows.length} requirement${rows.length===1?'':'s'}${missing?' · Needs acceptance criteria':''}`;
}
function planningAreaLink(d,path,title=d.label){
 const target='area-requirements-'+path.replaceAll('/','--');
 return `<a class="planning-text-link" href="#${esc(encodeURIComponent(target))}" data-action="sponsor-planning-focus" data-id="${esc(target)}">${esc(title)}</a>`;
}
function sharedDrawerDefinition(path){
 const shared=(state.records||[]).find(r=>r.kind==='requirement-drawer'&&(r.body.key===path||r.ref.id==='DRW-'+path));
 return shared?`<p class="caption"><a class="item-title-link" href="#main" data-action="open-drawer" data-id="${esc(shared.ref.id)}">Shared definition · v${esc(shared.ref.revision)}</a></p>`:'';
}
function scaffoldArea(d,parent,planning=false){
 const path=parent.key+'/'+d.key;
 const guidance=(d.project_focus?projectFocus(d,path):para(d.question))+areaCriteria(d);
 return `<details class="subdrawer-edit" data-key="${esc(d.key)}" ${planning?`data-planning-detail="area-${esc(path)}"`:''}><summary>${planning?planningAreaLink(d,path):`<span>${esc(d.label)}</span>`}<span class="caption">${planning?planningAreaStatus(d,parent.included,path):!parent.included||!d.included?'Excluded':d.requirement?'Draft present':'Not yet drafted'}</span></summary><div class="subdrawer-body">${planning?requirementEntryList({...d,included:parent.included&&d.included},path)+`<details class="area-guidance"><summary>Area guidance &amp; ownership</summary>${sharedDrawerDefinition(path)}${guidance}${drawerFields(d,path,true,false,true)}</details>`:guidance+drawerFields(d,path,true)+requirementAgentControls({...d,key:path,included:parent.included&&d.included})}</div></details>`;
}
function planningDrawerCategory(d,values){
 const n=d.key.replaceAll('/','--'),settings='drawer-settings-'+n,heading='drawer-heading-'+n,summary='drawer-summary-'+n;
 return `<section class="drawer-edit planning-requirement-group" data-key="${esc(d.key)}" aria-labelledby="${esc(heading)}" aria-describedby="${esc(summary)}">
  <header class="planning-subsection-head"><h3 id="${esc(heading)}">${esc(d.label)}</h3>${!d.included?'<span class="caption">Excluded</span>':''}
   <button type="button" class="compact-text-action" data-action="sponsor-planning-toggle" data-id="${esc(settings)}" aria-controls="${esc(settings)}" aria-expanded="false" aria-label="${esc(d.label)} definition and ownership" title="Definition &amp; ownership">Definition</button>
  </header>
  <p id="${esc(summary)}" class="sr-only">${esc(draftCategorySummary(d))} · Lead: ${esc(state.actors[d.owner]?.name||'Not assigned')}</p>
  <div class="category-body">
   <details class="planning-category-settings" id="${esc(settings)}" data-planning-detail="settings-${esc(d.key)}"><summary hidden>Definition &amp; ownership</summary>
    ${sharedDrawerDefinition(d.key)}${drawerFields(d,d.key,false,true,true)}<details class="section"><summary>Intake basis</summary><div class="details-body">${drawerSource(d,values)}</div></details>
   </details>
   ${!d.children?.length||requirementDrafts(d,d.key).length?requirementEntryList(d,d.key,d.children?.length?'Category-level requirements':'Requirements'):''}
   ${d.children?.length?`<div class="subdrawer-list">${d.children.map(c=>scaffoldArea(c,d,true)).join('')}</div>`:''}
  </div>
 </section>`;
}
function intakeDrawerForm({planning=false,readOnly=false}={}){
 const i=state.intake,b=i.draft.body;
 const update=planning&&b.scaffold.length&&!i.scaffold_current?`<button type="button" class="compact-text-action" data-action="intake-build" ${i.gaps.length?'disabled':''}>Update from Business Intent</button>`:'';
 const warning=i.gaps.length?`<div class="banner signal-notice signal-advisory"><strong>Complete these intake answers before preparing drawers.</strong><p>${i.gaps.map(k=>esc(intakeNames[k]||k)).join(' · ')}</p>${update}</div>`:!i.scaffold_current&&b.scaffold.length?`<div class="banner signal-notice signal-advisory"><p>The Business Intent or category criteria changed. Update the basis before drafting or review. Your saved requirement wording will be retained.</p>${update}</div>`:'';
 const categoryRows=`<div class="scaffold-categories">${b.scaffold.map(d=>planning?planningDrawerCategory(d,b.values):`<details class="card drawer-edit" data-key="${esc(d.key)}" ${planning?`data-planning-detail="drawer-${esc(d.key)}"`: ''}><summary><span><strong>${esc(d.label)}</strong><span class="caption category-lead">Lead: ${esc(state.actors[d.owner]?.name)}</span></span><span class="caption">${planning?draftCategorySummary(d):d.children?.length?`${d.children.filter(c=>c.included).length} of ${d.children.length} sub-drawers included`:'Category requirement'}</span></summary><div class="category-body">${d.project_focus?projectFocus(d,d.key):para(d.question)}${drawerFields(d,d.key)}${d.children?.length?`<div class="subdrawer-list">${d.children.map(c=>scaffoldArea(c,d,planning)).join('')}</div>`:requirementAgentControls(d)}<details class="section"><summary>Intake basis</summary><div class="details-body">${drawerSource(d,b.values)}</div></details></div></details>`).join('')}</div>`;
 const tailor=!planning&&typeof tailoringControls==='function'?tailoringControls():'';
 const prepare=button(b.scaffold.length?'Refresh scaffold':'Prepare draft drawers','intake-build','',b.scaffold.length?'small':'primary');
 const save='<button type="submit" form="intake-drawers-form" class="primary" name="next" value="stay">Save draft</button>';
 const goals=planning&&typeof sponsorGoalsRead==='function'?sponsorGoalsRead():typeof goalsEditor==='function'?goalsEditor({planning}):'';
 const form=content=>`<form id="intake-drawers-form" ${planning?'class="planning-editor" aria-label="Edit goals, KPIs and requirements"':''}><div class="error" role="alert"></div><fieldset class="setup-governed-fields" ${readOnly?'data-setup-locked="true"':''}>${content}</fieldset></form>`;
 const savedGoals=typeof goalsRead==='function'?goalsRead(state.goals):'';
 if(planning){
  if(!b.scaffold.length)return `<section class="card planning-panel">${savedGoals}${prepare}<p class="caption">Prepare draft drawers from the saved brief to edit requirements, acceptance criteria, goals and KPIs.</p></section>`;
  return form(`${goals}<section class="card planning-panel planning-drawers" aria-labelledby="planning-drawers-title"><h2 id="planning-drawers-title">Requirement drawers</h2>${warning}${categoryRows}<footer class="planning-editor-actions">${save}</footer></section>`);
 }
 const notice=typeof tailoringNotice==='function'?tailoringNotice():'';
 return warning+notice+`<div class="card-head"><div><h2>Requirement scaffold</h2><p class="caption">Open a category to review its sub-drawers and draft requirements.</p></div><div class="actions">${tailor}${prepare}${b.scaffold.length?save:''}</div></div>`+
  (b.scaffold.length?form(`${goals}${categoryRows}<div class="intake-footer"><button type="submit" name="next" value="review" ${i.scaffold_current?'':'disabled'}>Save and preview direction</button></div>`):
   savedGoals+'<div class="empty">Prepare draft drawers from your saved Business Intent to edit goals, measures and requirements together.</div>');
}
function draftCategorySummary(d){
 if(!d.included)return 'Excluded';
 const areas=d.children?.length?d.children.filter(c=>c.included):[d];
 const entries=areas.flatMap(c=>requirementDrafts(c,c===d?d.key:d.key+'/'+c.key)).filter(x=>x.included!==false);
 const written=entries.filter(c=>c.requirement?.trim()).length;
 const missing=entries.filter(c=>c.requirement?.trim()&&!c.acceptance_criteria?.trim()).length;
 return (d.children?.length?`${areas.length} in scope · ${written} drafted`:written?'Requirement drafted':'No draft')+
  (missing?` · ${missing} need criteria`:'');
}
function readScaffoldItem(el){const container=el.querySelector(':scope > .category-body > .scaffold-fields,:scope > .category-body > .planning-category-settings > .scaffold-fields,:scope > .subdrawer-body > .scaffold-fields,:scope > .subdrawer-body > .area-guidance > .scaffold-fields');const out={key:el.dataset.key};container.querySelectorAll('input,textarea,select').forEach(i=>{if(!i.name)return;out[i.name]=i.type==='checkbox'?i.checked:i.value;});if(container.querySelector('.goal-area-links'))out.goal_ids=Array.from(container.querySelectorAll('[data-area-goal]:checked')).map(i=>i.dataset.areaGoal);const path=container.dataset.coachPath;if([...el.querySelectorAll('[data-requirement-list]')].some(x=>x.dataset.requirementList===path))out.requirements=[...el.querySelectorAll('.requirement-draft')].filter(x=>x.dataset.areaPath===path).map(row=>{const item={id:row.dataset.requirementId};row.querySelectorAll('[data-requirement-field]').forEach(x=>item[x.dataset.requirementField]=x.type==='checkbox'?x.checked:x.value);return item;});return out;}
function scaffoldFormValues(form){return Array.from(form.querySelectorAll('.drawer-edit')).map(el=>({...readScaffoldItem(el),children:Array.from(el.querySelectorAll('.subdrawer-edit')).map(readScaffoldItem)}));}
// The shared map contains published hypotheses and shells. Ratification is a
// separate authority state; neither publication nor approval proves validation.
function sharedRequirementPublicRecord(r){return !r.scope||String(r.scope).startsWith('project:');}
function sharedRequirementRows(){return records('requirement').filter(r=>sharedRequirementPublicRecord(r)&&['proposed','approved'].includes(r.body.status));}
function sharedRequirementDrawerRows(){return records('requirement-drawer').filter(sharedRequirementPublicRecord);}
function scaffoldRatifiedRequirements(){return sharedRequirementRows().filter(r=>r.body.status==='approved');}
function ratifiedRequirementDrawerRows(){
 const drawers=sharedRequirementDrawerRows(),byId=new Map(drawers.map(d=>[d.ref.id,d])),included=new Set();
 for(const requirement of scaffoldRatifiedRequirements()){
  let id=requirement.body.drawer_id;const seen=new Set();
  while(id&&byId.has(id)&&!seen.has(id)){seen.add(id);included.add(id);id=byId.get(id).body.parent_id;}
 }
 return drawers.filter(d=>included.has(d.ref.id));
}
function ratifiedRequirementCategoryRows(){const ds=sharedRequirementDrawerRows(),ids=new Set(ds.map(d=>d.ref.id));return ds.filter(d=>!d.body.parent_id||!ids.has(d.body.parent_id));}
function ratifiedRequirementCategoryId(drawerId){
 const ds=new Map(sharedRequirementDrawerRows().map(d=>[d.ref.id,d])),seen=new Set();let id=drawerId;
 while(id&&ds.has(id)&&!seen.has(id)){seen.add(id);const parent=ds.get(id).body.parent_id;if(!parent||!ds.has(parent))return id;id=parent;}
 return '';
}
let ratifiedRequirementCategory='',ratifiedRequirementCategoryScope='';
function syncRatifiedRequirementCategory(){
 const scope=[state.actor,state.project?.id,state.project?.version].join(':');
 if(scope!==ratifiedRequirementCategoryScope){ratifiedRequirementCategoryScope=scope;ratifiedRequirementCategory='';}
 const categories=ratifiedRequirementCategoryRows();
 if(categories.length<2||!categories.some(d=>d.ref.id===ratifiedRequirementCategory))ratifiedRequirementCategory='';
 return categories;
}
function ratifiedRequirementCategoryControl(){
 const categories=syncRatifiedRequirementCategory();if(categories.length<2)return '';
 return `<div class="ui-selector-field requirements-category-filter"><label class="ui-control-label" for="ratified-requirement-category">Category</label><div class="ui-selector-wrap"><select id="ratified-requirement-category" class="ui-selector"><option value="">All categories</option>${categories.map(d=>`<option value="${esc(d.ref.id)}" ${d.ref.id===ratifiedRequirementCategory?'selected':''}>${esc(d.body.label)}</option>`).join('')}</select>${typeof selectorChevron==='function'?selectorChevron():''}</div></div>`;
}
function ratifiedRequirementCategoryAttributes(drawerId){
 syncRatifiedRequirementCategory();const category=ratifiedRequirementCategoryId(drawerId);
 return `data-ratified-category="${esc(category)}"${ratifiedRequirementCategory&&category!==ratifiedRequirementCategory?' hidden':''}`;
}
function filterRatifiedRequirementCategory(value){
 const categories=syncRatifiedRequirementCategory();ratifiedRequirementCategory=categories.some(d=>d.ref.id===value)?value:'';
 const main=document.querySelector('#main')||document;
 main.querySelectorAll('[data-ratified-category]').forEach(node=>{node.hidden=!!ratifiedRequirementCategory&&node.dataset.ratifiedCategory!==ratifiedRequirementCategory;});
 return ratifiedRequirementCategory;
}
document.addEventListener('change',event=>{if(event.target.id==='ratified-requirement-category')event.target.value=filterRatifiedRequirementCategory(event.target.value);});
function requirementScaffoldSource({sharedOnly=false}={}){
 const i=state.intake;
 const published=sharedOnly?sharedRequirementDrawerRows():records('requirement-drawer');
 if(published.length){const ids=new Set(published.map(d=>d.ref.id));return {mode:'published',categories:published.filter(d=>!d.body.parent_id||!ids.has(d.body.parent_id))};}
 if(!sharedOnly&&state.actor==='priya'&&i.draft?.body.scaffold?.length)return {mode:'draft',categories:i.draft.body.scaffold,catalog:i.draft.body.goal_snapshot};
 const shared=!sharedOnly&&(i.cases||[]).find(c=>!['declined','published'].includes(c.body.status)&&c.body.snapshot?.scaffold?.length);
 if(shared)return {mode:'review',categories:shared.body.snapshot.scaffold,catalog:shared.body.snapshot.goal_snapshot,case:shared};
 return sharedOnly?{mode:'shared-empty',categories:[]}:{mode:'template',categories:i.profile?.body.drawers||i.scaffold_defaults||[]};
}
function scaffoldPreviewStatus(d,mode,parentIncluded=true){
 if(mode==='template')return d.when==='disabled'?'Disabled in settings':'Template';
 return !parentIncluded||d.included===false?'Excluded':mode==='draft'?'Draft':'In direction review';
}
function scaffoldPreviewBody(d,source,path){
 const template=source.mode==='template';
 return para(d.question)+(template?val('Configured for',({always:'All initiatives',digital:'Digital initiatives',operational:'Operational initiatives',market:'Market initiatives',other:'Other inquiry',disabled:'Not currently used'})[d.when]||'Not specified'):
  (typeof projectFocus==='function'?projectFocus(d,path):'')+
  (typeof draftGoalLinksRead==='function'?draftGoalLinksRead(d,source.catalog):'')+
  requirementEntriesRead(d,path)+
  (d.exclusion_reason?val('Reason for exclusion',d.exclusion_reason):''))+
  areaCriteria(d)+val('Investigation lead',state.actors[d.owner]?.name||'Not assigned');
}
function scaffoldPreview(source){
 const {mode,categories}=source;
 const copy=mode==='draft'?['Draft scaffold','Saved in business intake. These categories and proposed requirements are not published.']:
  mode==='review'?['Shared for direction review','This is the shared review snapshot. The direction has not been published.']:
  ['Configured categories','These are category definitions. Business intake establishes which apply to this project.'];
 const action=state.actor==='priya'?button(mode==='draft'?'Edit scaffold':'Open business intake','intake-step',mode==='draft'?'drawers':'rationale'):'';
 const stale=mode==='draft'&&!state.intake.scaffold_current?'<p class="caption">Business intake or category settings changed. Refresh and review this saved scaffold before using it.</p>':
  mode==='review'&&source.case.stale?.length?'<p class="caption">This review snapshot needs reconsideration because its basis changed.</p>':'';
 return `<div class="card-head"><div><strong>${copy[0]}</strong><p class="caption">${copy[1]}</p>${stale}</div>${action}</div>`+
  (source.catalog&&typeof goalsRead==='function'?goalsRead(source.catalog):'')+
  `<div class="grid two scaffold-preview">${categories.map(d=>`<details class="card scaffold-preview-category"><summary><span class="scaffold-category-title">${esc(d.label)}</span><span class="caption">${(d.children||[]).length} sub-drawers · ${scaffoldPreviewStatus(d,mode)}</span></summary><div class="details-body">${scaffoldPreviewBody(d,source,d.key)}${(d.children||[]).map(c=>`<details class="subdrawer-read"><summary>${esc(c.label)}<span class="caption"> · ${scaffoldPreviewStatus(c,mode,d.included!==false)}</span></summary><div class="details-body">${scaffoldPreviewBody(c,source,d.key+'/'+c.key)}</div></details>`).join('')}</div></details>`).join('')}</div>`;
}
function requirementReviewActivity(r){
 // Workspace cases arrive newest first; only an explicit open review is activity.
 const review=(state.cases||[]).find(c=>c.body?.target?.id===r.ref.id&&['pending-review','deferred'].includes(c.body.status));
 if(!review)return null;
 const changed=review.body.target.revision!==r.ref.revision||review.stale?.length||review.changed?.length||state.requirement_impacts?.[r.ref.id]?.length;
 if(changed)return {case:review,label:'Review needs refresh',tone:'advisory'};
 return review.body.status==='deferred'?{case:review,label:'Awaiting response',tone:'reference'}:{case:review,label:'In review',tone:'attention'};
}
function requirementMapCondition(r){
 const confidence=typeof requirementAssessmentConfidence==='function'?requirementAssessmentConfidence(r):typeof requirementConfidenceLabel==='function'?requirementConfidenceLabel():'Confidence: Not rated';
 return signalConditionChip((r.body.status==='approved'?'Ratified':'Proposed')+' · '+confidence,'reference');
}
function requirementDefinitionRead(b){
 const supplied=value=>Array.isArray(value)?value.some(v=>String(v||'').trim()):!!String(value||'').trim();
 return `<div class="requirement-definition"><h4>Definition completeness</h4><ul><li>Wording: ${supplied(b.text)?'Supplied':'Missing'}</li><li>Acceptance criteria: ${supplied(b.acceptance_criteria)?'Supplied':'Missing'}</li></ul><p class="caption">Definition completeness does not establish evidence confidence or validation.</p></div>`;
}
function requirementAssessmentFallbackRead(r){
 const confidence=typeof requirementConfidenceLabel==='function'?requirementConfidenceLabel():'Confidence: Not rated';
 return `<section class="requirement-record-assessment" aria-label="Assessment status"><header><h4>Assessment</h4>${signalConditionChip(confidence)}</header>${requirementDefinitionRead(r.body)}<dl class="requirement-validation"><div><dt>Validation</dt><dd>Not recorded</dd></div></dl></section>`;
}
function requirementContentRead(r){
 const b=r.body;
 return `<section class="requirement-record-section"><h4>Requirement</h4><p class="pre">${esc(b.text||'Not yet worded')}</p></section><section class="requirement-record-section"><h4>Acceptance criteria</h4><p class="pre">${esc(b.acceptance_criteria||'Not yet specified')}</p></section>${typeof requirementAssessmentRead==='function'?requirementAssessmentRead(r):requirementAssessmentFallbackRead(r)}`;
}
function publishedRequirementRead(r,{preview=false}={}){
 if(!sharedRequirementPublicRecord(r)||!['proposed','approved'].includes(r.body.status))return '';
 const b=r.body,activity=requirementReviewActivity(r);
 return `<details class="workbench-drawer requirement-record" data-requirement="${esc(r.ref.id)}" data-work="${activity?.tone||'none'}"><summary><span class="requirement-record-heading">${preview&&typeof requirementTileIcon==='function'?`<span class="requirement-cover-icon">${requirementTileIcon('requirement')}</span>`:''}<span class="workbench-object-type">Requirement</span><span class="requirement-record-title"${preview?` title="${esc(b.title||'Project requirement')}"`:''}>${preview&&typeof requirementCardTitle==='function'?requirementCardTitle(b.title||'Project requirement'):esc(b.title||'Project requirement')}</span>${activity?signalConditionChip(activity.label,activity.tone):''}</span>${preview&&b.text?.trim()&&b.text.trim()!==(b.title||'').trim()?`<span class="requirement-tile-preview">${esc(b.text)}</span>`:''}${preview?`<span class="requirement-cover-state"><span class="requirement-cover-authority">${b.status==='approved'?'Ratified':'Proposed'}</span>`:''}${typeof requirementAssessmentDrawerIndicator==='function'?requirementAssessmentDrawerIndicator(r,{compact:preview}):typeof requirementAssessmentSummary==='function'?requirementAssessmentSummary(r):''}${typeof requirementEvidenceChip==='function'?requirementEvidenceChip(r.ref.id):''}${preview?'</span>':''}</summary><div class="details-body requirement-record-body">${requirementContentRead(r)}${typeof requirementEvidenceSection==='function'?requirementEvidenceSection(r.ref.id):''}<footer class="requirement-record-footer"><div class="requirement-record-actions"><a href="#main" class="item-title-link" data-action="requirement" data-id="${esc(r.ref.id)}">Open requirement</a>${activity?`<a href="#main" class="item-title-link" data-action="case" data-id="${esc(activity.case.ref.id)}">Open review</a>`:''}</div><details class="record-metadata"><summary>Source details</summary><div class="metadata-content"><p class="caption">${esc(r.ref.id)}:v${esc(r.ref.revision)} · ${b.status==='approved'?'Ratified':'Proposed'} · Validation not recorded</p></div></details></footer></div></details>`;
}
function requirementMapCounts(reqs){return `${reqs.length} requirement${reqs.length===1?'':'s'}`;}
function requirementAreaRows(d,ds,reqs){
 const ids=new Set([d.ref.id]);let changed=true;
 while(changed){changed=false;for(const child of ds)if(ids.has(child.body.parent_id)&&!ids.has(child.ref.id)){ids.add(child.ref.id);changed=true;}}
 return reqs.filter(r=>ids.has(r.body.drawer_id));
}
function requirementShellCondition(){return signalConditionChip('No requirements defined','reference');}
function publishedAreaDrawer(d,ds,reqs,ancestors=new Set(),title=d.body.label){
 if(ancestors.has(d.ref.id))return '';
 const next=new Set([...ancestors,d.ref.id]),children=ds.filter(c=>c.body.parent_id===d.ref.id),linked=reqs.filter(r=>r.body.drawer_id===d.ref.id),b=d.body,all=requirementAreaRows(d,ds,reqs);
 return `<details class="workbench-drawer requirement-area-shell" data-drawer="${esc(d.ref.id)}"><summary><span class="requirement-area-heading"><span class="requirement-area-title">${esc(title)}</span></span>${b.status==='retired'?signalConditionChip('Retired','reference'):''}${all.length?signalConditionChip(requirementMapCounts(all)):requirementShellCondition()}</summary><div class="details-body requirement-area-body"><section class="requirement-area-guidance"><h3>What needs investigation</h3><p>${esc(b.question||'')}</p><details class="requirement-area-method"><summary>Review criteria & evidence to gather</summary><div class="details-body">${areaCriteria(b)}</div></details></section>${children.map(c=>publishedAreaDrawer(c,ds,reqs,next)).join('')}${linked.length?`<section class="requirement-area-proposals" aria-label="Requirements"><h3>Requirements</h3><div class="requirement-record-list">${linked.map(publishedRequirementRead).join('')}</div></section>`:''}<footer class="requirement-area-footer"><a href="#main" class="item-title-link" data-action="open-drawer" data-id="${esc(d.ref.id)}">View area details</a></footer></div></details>`;
}
function requirementDrawers({includeGoals=true,sharedOnly=false}={}){
 const source=requirementScaffoldSource({sharedOnly});
 if(source.mode!=='published')return source.categories.length?scaffoldPreview(source):'';
 const ds=sharedOnly?sharedRequirementDrawerRows():records('requirement-drawer'),roots=source.categories,reqs=sharedRequirementRows();
 return (includeGoals&&typeof publicGoalsRead==='function'?publicGoalsRead():'')+`<div class="requirements-module-list">${roots.map(d=>{
  const children=ds.filter(c=>c.body.parent_id===d.ref.id),linked=reqs.filter(r=>r.body.drawer_id===d.ref.id),all=requirementAreaRows(d,ds,reqs);
  return `<section class="card section workbench-record-module" data-category="${esc(d.ref.id)}" ${sharedOnly?ratifiedRequirementCategoryAttributes(d.ref.id):''}><header class="workbench-module-header"><div class="card-head"><h2>${esc(d.body.label)}</h2>${d.body.status==='retired'?signalConditionChip('Retired','reference'):''}</div><p class="caption">${esc(d.body.question||'')}</p>${all.length?`<div class="requirement-map-conditions">${signalConditionChip(requirementMapCounts(all))}</div>`:''}</header><div class="workbench-module-drawers">${children.map(c=>publishedAreaDrawer(c,ds,reqs,new Set([d.ref.id]))).join('')}${linked.map(publishedRequirementRead).join('')}${!children.length&&!linked.length?publishedAreaDrawer(d,ds,reqs,new Set(),'Scope & review criteria'):''}</div><footer class="workbench-module-footer"><a href="#main" class="item-title-link" data-action="open-drawer" data-id="${esc(d.ref.id)}">View category details</a></footer></section>`;
 }).join('')}</div>`;
}

function drawerPage(id){
 const d=get(id),b=d.body,drawers=typeof view!=='undefined'&&view==='requirements'?sharedRequirementDrawerRows():records('requirement-drawer'),children=drawers.filter(c=>c.body.parent_id===id),reqs=sharedRequirementRows(),linked=reqs.filter(r=>r.body.drawer_id===id);
 return `<div class="breadcrumb">${b.parent_id?button('← '+(get(b.parent_id)?.body.label||'Category'),'open-drawer',b.parent_id,'quiet'):button('← All categories','back-requirements','','quiet')}</div>`+head(b.label,b.question,b.status==='active'?'<button type="button" data-nav="review">Discuss a change</button>':'')+`<div class="grid cols"><div>${typeof projectFocus==='function'?projectFocus(b):''}${areaCriteria(b)}${children.map(c=>`<article class="card section"><div class="card-head"><h3 class="acx-item-title"><a href="#main" class="item-title-link" data-action="open-drawer" data-id="${esc(c.ref.id)}">${esc(c.body.label)}</a></h3>${c.body.status==='retired'?signalConditionChip('Retired','reference'):''}</div>${para(c.body.question)}${requirementAreaRows(c,drawers,reqs).length?signalConditionChip(requirementMapCounts(requirementAreaRows(c,drawers,reqs))):requirementShellCondition()}</article>`).join('')}${linked.map(publishedRequirementRead).join('')}${!children.length&&!linked.length?requirementShellCondition():''}</div><aside class="card readiness">${val('Investigation lead',state.actors[b.owner]?.name)}${val('Rationale',b.rationale)}${typeof linkedGoalsRead==='function'?linkedGoalsRead(b):''}<details><summary>Intake basis</summary><div class="details-body">${drawerSource(b,state.intake.cases.find(c=>c.ref.id===b.source_case?.id)?.body.snapshot.values||{})}${ref(b.intent)} · ${ref(b.profile)}</div></details><p class="caption">Criteria guide evaluation. Recorded evidence and human decisions establish whether a requirement is met.</p></aside></div>`;
}
function profileField(name,title,value,required=true){return `<label class="form-field"><span>${title}</span><textarea name="${name}" maxlength="20000" ${required?'required':''}>${esc(value||'')}</textarea></label>`;}
function profileSelects(d,category=false){return `<div class="grid two"><label class="form-field"><span>${category?'Category lead':'Investigation lead'}</span><select name="owner" ${category&&state.actor!=='priya'&&!state.auth?.settings_access?'disabled':''}>${Object.entries(state.actors).filter(([id])=>id!=='administrator').map(([id,a])=>`<option value="${id}" ${d.owner===id?'selected':''}>${esc(a.role)} · ${esc(a.name)}</option>`).join('')}</select></label><label class="form-field"><span>Include for</span><select name="when">${[['always','All initiatives'],['digital','Digital initiatives'],['operational','Operational initiatives'],['market','Market initiatives'],['other','Other inquiry'],['disabled','Not currently used']].map(([k,t])=>`<option value="${k}" ${d.when===k?'selected':''}>${t}</option>`).join('')}</select></label></div>`;}
function subProfileRow(d){return `<details class="sub-profile" data-key="${esc(d.key)}" data-fields="${esc(JSON.stringify(d.basis_fields))}"><summary>${esc(d.label||'New sub-drawer')}</summary><fieldset class="profile-fields">${profileField('label','Sub-drawer name',d.label)}${profileField('question','Question to resolve',d.question)}${profileField('criteria','Review criteria',d.criteria)}${profileField('evidence','Evidence to provide',d.evidence)}${profileField('revisit','When to reassess',d.revisit)}${profileField('references','Methods or standards · include version and scope',d.references,false)}${profileSelects(d)}</fieldset></details>`;}
function categoryProfileRow(d){const editable=(state.actor==='priya'||state.auth?.settings_access)||state.actor===d.owner;return `<details class="card profile-row" data-key="${esc(d.key)}" data-editable="${editable}" data-fields="${esc(JSON.stringify(d.basis_fields))}"><summary><strong>${esc(d.label)}</strong><span class="caption">${d.children?.length||0} sub-drawers · ${esc(state.actors[d.owner]?.name)}${editable?'':' · View only'}</span></summary><fieldset class="profile-fields" ${editable?'':'disabled'}>${profileField('label','Category name',d.label)}${profileField('question','Category purpose',d.question)}${profileSelects(d,true)}</fieldset><fieldset class="profile-children" ${editable?'':'disabled'}><legend>Sub-drawers</legend><div class="sub-profile-list">${(d.children||[]).map(subProfileRow).join('')}</div>${editable?'<button type="button" class="add-sub-profile small">Add sub-drawer</button>':''}</fieldset></details>`;}
function readProfileFields(el){return Object.fromEntries(Array.from(el.querySelector(':scope > .profile-fields').querySelectorAll('input,textarea,select')).map(i=>[i.name,i.value]));}
function intakeProfileForm(){const p=state.intake.profile;if(!p)return;
 modal('Intake settings',`<p class="caption">Category leads define sub-drawers, review criteria and evidence expectations. Each save creates a profile version.</p>${(state.actor==='priya'||state.auth?.settings_access)?`<details><summary>Profile name</summary>${field('name','Profile name',p.body.name,'','input')}</details>`:''}<div id="profile-rows">${p.body.drawers.map(categoryProfileRow).join('')}</div>${(state.actor==='priya'||state.auth?.settings_access)?'<button type="button" id="add-profile-category" class="small section">Add category</button>':''}`,'Save profile version',fd=>command('intake-configure',{expected:p.ref,name:(state.actor==='priya'||state.auth?.settings_access)?fd.get('name'):p.body.name,drawers:Array.from(document.querySelectorAll('#profile-rows > .profile-row')).map(el=>el.dataset.editable==='false'?p.body.drawers.find(d=>d.key===el.dataset.key):({key:el.dataset.key,basis_fields:JSON.parse(el.dataset.fields),...readProfileFields(el),children:Array.from(el.querySelectorAll('.sub-profile')).map(c=>({key:c.dataset.key,basis_fields:JSON.parse(c.dataset.fields),...readProfileFields(c)}))}))}),{className:'settings-dialog scaffold-settings'});
 const rows=$('#profile-rows');rows.addEventListener('click',e=>{const add=e.target.closest('.add-sub-profile');if(!add)return;const category=add.closest('.profile-row');const child={key:'area-'+crypto.randomUUID().slice(0,8),label:'',question:'',criteria:'',evidence:'',revisit:'',references:'',owner:category.querySelector(':scope > .profile-fields [name="owner"]').value,when:'always',basis_fields:JSON.parse(category.dataset.fields)};const list=category.querySelector('.sub-profile-list');list.insertAdjacentHTML('beforeend',subProfileRow(child));list.lastElementChild.open=true;dirty=true;});
 const add=$('#add-profile-category');if(add)add.addEventListener('click',()=>{rows.insertAdjacentHTML('beforeend',categoryProfileRow({key:'custom-'+crypto.randomUUID().slice(0,8),label:'New category',question:'',owner:state.actor,when:'always',basis_fields:['need','value','in_scope'],children:[]}));rows.lastElementChild.open=true;dirty=true;});
}

function lockSponsorSetupFields(){
 document.querySelectorAll('[data-setup-locked="true"]').forEach(group=>{
  group.querySelectorAll('input,textarea,select,button').forEach(control=>{
   if(control.matches('button[data-action="sponsor-planning-toggle"]'))return;
   control.disabled=true;
  });
 });
}

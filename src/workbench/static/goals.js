// One scaffold form saves goals, measures and area links atomically.
const goalLabels={title:'Goal',outcome:'What should improve?',beneficiary:'Who benefits?',rationale:'How does this support the value proposition?',owner:'Accountable owner'};
const measureLabels={name:'Measure',definition:'Calculation or observation',population:'Population and scope',baseline:'Baseline',target:'Target',timeframe:'Target date or evaluation period',data_source:'Data source',cadence:'Review frequency',owner:'Measurement owner',guardrail:'What must not get worse?',review_plan:'How will missing information be resolved?'};
// Reviewed reading labels. Exact matches preserve unfamiliar authored names and
// leave saved measurement definitions, identity and historical wording intact.
const measureTitleLabels=new Map([
 ['Status-chasing effort per operational issue','Time spent getting updates'],
 ['Time to accepted accountable ownership','Time until responsibility is accepted'],
 ['Claimed resolutions with inspectable outcome evidence','Reported resolutions with evidence']
]);
function measureDisplayTitle(title){return measureTitleLabels.get(String(title||''))||String(title||'');}
const goalFieldHelp={
 [goalLabels.title]:'Name the outcome you want this work to achieve.',
 [goalLabels.outcome]:'Describe the change people or the business should experience, rather than a feature to build.',
 [goalLabels.beneficiary]:'Identify the people or teams who should benefit from this outcome.',
 [goalLabels.rationale]:'Explain how achieving this outcome would deliver the value promised in the intake.',
 [goalLabels.owner]:'Name the person or role accountable for this outcome and briefly explain their responsibility. State if assignment is still proposed.',
 [measureLabels.name]:'Give the measure a short name that describes the result you will track.',
 [measureLabels.definition]:'Define what counts as success and how the result will be calculated or observed.',
 [measureLabels.population]:'Specify the people, locations and cases included, plus any exclusions.',
 [measureLabels.baseline]:'Enter the current result, its period and source, or state that it is not yet measured.',
 [measureLabels.target]:'State the desired result in the same unit as the baseline and identify any provisional target.',
 [measureLabels.timeframe]:'Specify when the target should be reached or the period used to evaluate it.',
 [measureLabels.data_source]:'Name the records or research that will supply the data, and note whether access is confirmed.',
 [measureLabels.cadence]:'Say how often the result will be checked and discussed.',
 [measureLabels.owner]:'Name the person responsible for collecting, checking and reporting the result.',
 [measureLabels.guardrail]:'Identify a quality, safety or fairness outcome that must not deteriorate as this measure improves.',
 [measureLabels.review_plan]:'List what is unknown, who will resolve it and by when.'
};
function indicatorObjectHeading(type,title,support=''){return `<span class="workbench-object-heading"><span class="workbench-object-type">${esc(type)}</span><span class="workbench-object-title">${title}</span>${support}</span>`;}
function indicatorGoalId(goal){return goal?.id||goal?.ref?.id||'';}
function indicatorSharedRecord(record){return !record?.scope||String(record.scope).startsWith('project:');}
function goalPinsMeasure(goal,measure){return !!measure.ref&&(goal.body.measure_refs||[]).some(raw=>raw.id===measure.ref.id&&raw.revision===measure.ref.revision);}
function measureGoalSupportRead(item,goals=[],{shared=false}={}){
 // Resolve names only within this rendering's supplied catalog. In particular,
 // public and historical readings never consult private drafts or latest names.
 const catalog=(Array.isArray(goals)?goals:[]).filter(goal=>!shared||indicatorSharedRecord(goal)),ids=[...new Set([...(Array.isArray(item.body.goal_ids)?item.body.goal_ids:[]),...catalog.filter(goal=>goalPinsMeasure(goal,item)).map(indicatorGoalId)].filter(Boolean))];
 const names=ids.map(id=>{const goal=catalog.find(row=>indicatorGoalId(row)===id),title=goal?.body?.title;return title?String(title)+(goal.body.active===false?' (Inactive)':''):null;}),missing=names.filter(name=>!name).length,parts=names.filter(Boolean).map(esc);
 if(missing)parts.push(missing===1?'Linked goal unavailable':missing+' linked goals unavailable');
 const text=parts.length?parts.join(' · '):'No goal linked';
 return `<span class="measure-goal-support">${names.some(Boolean)?`Supports ${ids.length>1?'goals':'goal'}: `:''}${text}</span>`;
}
function goalInput(key,label,value,id,required=false){
 const control=esc(id+'-'+key),help=goalFieldHelp[label];
 const attrs=`id="${control}" aria-labelledby="${control}-label" ${help?`aria-describedby="${control}-help"`:''} data-goal-field="${key}"`;
 return `<label class="form-field" for="${control}"><span id="${control}-label">${esc(label)}</span>${help?`<span id="${control}-help" class="field-help">${esc(help)}</span>`:''}${['outcome','beneficiary','rationale','definition','population','baseline','target','timeframe','data_source','guardrail','review_plan','owner'].includes(key)?`<textarea ${attrs} maxlength="5000" ${required?'required':''}>${esc(value||'')}</textarea>`:`<input ${attrs} value="${esc(value||'')}" maxlength="5000" ${required?'required':''} placeholder="${required?'':'Not yet specified'}">`}</label>`;
}
function measureGoalChoices(goals,selected,id){return `<legend>Goals measured</legend><p class="field-help" id="${esc(id)}-goals-help">${goals.length?'Select the outcomes this measure will show progress against.':'Add a goal above to connect this measure to an intended outcome.'}</p>${goalChoices(goals,selected,'data-measure-goal')}`;}
function intakeAnswerLabel(key){return typeof shortQuestion==='function'?shortQuestion(key):key;}
function basisAnswerPreview(key,value){return `<details class="basis-answer"><summary>${esc(intakeAnswerLabel(key))}</summary><p class="pre caption">${esc(value||'This answer is now empty.')}</p></details>`;}
function basisSummary(keys){const v=state.intake.draft.body.values;return keys.length?keys.map(k=>basisAnswerPreview(k,v[k])).join(''):'<p class="caption">No intake answers linked yet.</p>';}
function refreshBasisSummary(row){
 const keys=Array.from(row.querySelectorAll('[data-basis-field]:checked')).map(el=>el.dataset.basisField);
 row.querySelector('[data-basis-count]').textContent=keys.length?`${keys.length} linked`:'Not linked yet';
 row.querySelector('[data-basis-summary]').innerHTML=basisSummary(keys);
}
function goalSourceEditor(item){
 const b=item.body,v=state.intake.draft.body.values,keys=b.basis_fields||[];
 const choices=Array.from(new Set([...Object.keys(v).filter(k=>v[k]?.trim()),...keys]));
 return `<details class="goal-source"><summary data-coach-basis>Why this belongs <span class="caption" data-basis-count>${keys.length?`${keys.length} linked`:'Not linked yet'}</span></summary><div class="details-body">
 <p class="field-help">Let the AI partner find the intake answers that explain this goal or measure.</p>
 ${button('Suggest connections','field-coach-basis',item.id,'small')}
 <div data-basis-summary>${basisSummary(keys)}</div>
 <p class="caption" data-basis-status role="status"></p>
 <details><summary>Choose answers myself</summary><div class="details-body">${choices.map(k=>`<label class="checkbox"><input type="checkbox" data-basis-field="${esc(k)}" ${keys.includes(k)?'checked':''}><span><strong>${esc(intakeAnswerLabel(k))}</strong><small class="caption">${esc((v[k]||'This answer is now empty.').slice(0,180))}${v[k]?.length>180?'…':''}</small></span></label>`).join('')}</div></details>
 ${item.changed_fields?.length?`<div class="banner signal-notice signal-advisory"><p>These linked answers changed: ${item.changed_fields.map(k=>esc(intakeAnswerLabel(k))).join(', ')}.</p><label class="checkbox"><input type="checkbox" data-review-basis>I reviewed whether this goal or measure still fits the changed answers.</label></div>`:''}
 </div></details>`;
}
function goalChoices(goals,selected,attr){return goals.map(g=>`<label class="checkbox"><input type="checkbox" ${attr}="${esc(g.id)}" ${selected.includes(g.id)?'checked':''}>${esc(g.body.title||'Untitled goal')}${g.body.active===false?' · Inactive':''}</label>`).join('');}

// Read saved provenance; never infer a missing question connection from similar wording.
function indicatorSourceQuestion(item,key){
 const questions=state.intake?.source_questions||[];
 const direct=questions.find(q=>q.field===key);if(direct)return direct;
 const snap=(state.intake?.cases||[]).find(c=>c.ref.id===item.body.source_case?.id)?.body.snapshot;
 const value=item.body.basis_values?.[key];
 return questions.find(q=>{
  if(q.legacy_field!==key||typeof value!=='string'||snap?.values?.[key]!==value)return false;
  const answer=snap.sponsor_brief?.answers?.[q.id];
  return answer&&!answer.roles?.length&&(answer.items||[]).join('\n')===value;
 })||null;
}
function indicatorSourceLabel(item,key){const q=indicatorSourceQuestion(item,key);return q?`${q.id.toUpperCase()} · ${q.title}`:intakeAnswerLabel(key)||key;}
function indicatorSourceLinks(item){
 const keys=item.body.basis_fields||[];
 if(!keys.length)return '<p class="caption">Source intake questions have not been linked.</p>';
 if(!item.ref)return '<p class="caption">Source links become available after this indicator is saved.</p>';
 return `<details class="indicator-sources"><summary>Source intake questions <span class="caption">(${keys.length})</span></summary><div class="details-body"><p class="caption">Business development · saved answers used for this indicator</p>${keys.map(key=>{
  const token=encodeURIComponent(JSON.stringify({ref:item.ref,key,draft:!!item.id}));
  const direct=state.actor==='priya'&&state.sponsor&&(indicatorSourceQuestion(item,key)||(typeof sponsorFitLabels!=='undefined'&&Object.hasOwn(sponsorFitLabels,key)));
  return `<p class="indicator-source-row"><a href="#main" class="item-title-link indicator-source-link" data-action="${direct?'goals-source-current':'goals-source'}" data-id="${esc(token)}">${esc(indicatorSourceLabel(item,key))}</a>${direct?`<a href="#main" class="caption indicator-source-link" data-action="goals-source" data-id="${esc(token)}" aria-label="Saved answer for ${esc(indicatorSourceLabel(item,key))}">Saved answer</a>`:''}</p>`;
 }).join('')}</div></details>`;
}
function indicatorSourceRecord(token){
 const data=JSON.parse(decodeURIComponent(token));
 const item=data.draft?[...(state.goals?.goals||[]),...(state.goals?.measures||[])].find(r=>r.ref?.id===data.ref.id&&r.ref.revision===data.ref.revision):exactGoalRecord(data.ref);
 if(!item||!(item.body.basis_fields||[]).includes(data.key))throw Error('This saved indicator version is unavailable. Reopen the indicator to inspect its source links.');
 return {item,key:data.key};
}
function openIndicatorSource(token){
 const {item,key}=indicatorSourceRecord(token),b=item.body,q=indicatorSourceQuestion(item,key),saved=b.basis_values?.[key];
 const current=state.actor==='priya'?state.intake?.draft?.body.values?.[key]:undefined;
 const fit=typeof sponsorFitLabels!=='undefined'&&Object.hasOwn(sponsorFitLabels,key);
 const canOpen=state.actor==='priya'&&state.sponsor&&(q||fit);
 modal(indicatorSourceLabel(item,key),`<p class="caption">Business development intake · ${esc(referenceText(item.ref,item))}</p>${sourceDetails([item.ref,b.source_case])}${val('Answer used for this indicator',typeof saved==='string'?saved:'The original answer was not retained with this indicator. It has not been replaced with a current answer.')}${b.source_case?`<p class="caption">Published source review · v${b.source_case.revision}</p>`:'<p class="caption">Saved private indicator basis</p>'}${typeof current==='string'&&typeof saved==='string'&&current!==saved?'<p class="banner signal-notice signal-advisory">The current intake answer has changed. The saved answer above remains the basis of this indicator.</p>':''}${!q?'<p class="caption">This is a saved intake field. A specific numbered-question link is not recorded.</p>':''}${canOpen?`<button type="button" data-action="goals-source-current" data-id="${esc(token)}">Open current ${q?'question':'answer'}</button>`:''}`);
}
async function openCurrentIndicatorAnswer(token){
 const {item,key}=indicatorSourceRecord(token),q=indicatorSourceQuestion(item,key);
 if(state.actor!=='priya'||!state.sponsor)throw Error('The current private intake is available to the sponsor.');
 if(document.querySelector('#modal')?.open)closeModal();
 if(q){
  await sponsorAction('sponsor-question',q.id);
  const heading=document.querySelector('#sponsor-editor h2');
  if(heading){heading.tabIndex=-1;heading.focus();heading.scrollIntoView({block:'start'});}
 }
 else if(typeof sponsorFitLabels!=='undefined'&&Object.hasOwn(sponsorFitLabels,key)){
  await sponsorAction('sponsor-fit','');
  document.querySelector(`#sponsor-editor [name="${CSS.escape(key)}"]`)?.focus();
 }
}

function goalDraftRow(item,group,{planning=false}={}){
 const b=item.body,labels=group==='goals'?goalLabels:measureLabels,measure=group==='measures';
 const missing=planning&&measure&&b.active!==false?['baseline','target'].filter(key=>!String(b[key]??'').trim()):[];
 const status=b.active===false?'Inactive':item.changed_fields?.length?'Source changed':missing.length?
  (missing.length===2?'Baseline and target':measureLabels[missing[0]])+' needed':'Draft';
 const sourceTitle=b[measure?'name':'title']||('New '+(measure?'measure':'goal')),title=measure?measureDisplayTitle(sourceTitle):sourceTitle;
 const focus=item.id+'-'+(measure?(missing[0]||'name'):'title');
 const titleHtml=planning?
  `<a class="goal-record-title planning-text-link" href="#${esc(encodeURIComponent(focus))}" data-action="sponsor-planning-focus" data-id="${esc(focus)}">${esc(title)}</a>`:
  `<span class="goal-record-title">${esc(title)}</span>`;
 return `<details class="goal-record" data-goal-id="${esc(item.id)}" data-planning-detail="goal-${esc(item.id)}" data-group="${group}"><summary>${indicatorObjectHeading(measure?'Success measure':'Goal',titleHtml,measure?measureGoalSupportRead(item,state.goals?.goals||[]):'')}<span class="caption">${esc(status)}</span></summary><div class="details-body">${indicatorSourceLinks(item)}${goalInput(measure?'name':'title',measure?'Measure':'Goal',b[measure?'name':'title'],item.id,true)}${measure?`${goalInput('definition',labels.definition,b.definition,item.id)}${goalInput('population',labels.population,b.population,item.id)}<div class="grid two">${goalInput('baseline',labels.baseline,b.baseline,item.id)}${goalInput('target',labels.target,b.target,item.id)}</div><fieldset class="goal-choices" aria-describedby="${esc(item.id)}-goals-help">${measureGoalChoices(state.goals?.goals||[],b.goal_ids||[],item.id)}</fieldset><details><summary>Measurement plan</summary><div class="details-body">${['timeframe','data_source','cadence','owner','guardrail','review_plan'].map(k=>goalInput(k,labels[k],b[k],item.id)).join('')}</div></details>`:`${goalInput('outcome',labels.outcome,b.outcome,item.id,true)}${goalInput('beneficiary',labels.beneficiary,b.beneficiary,item.id)}${goalInput('rationale',labels.rationale,b.rationale,item.id)}${goalInput('owner',labels.owner,b.owner,item.id)}`}${goalSourceEditor(item)}<label class="checkbox section"><input type="checkbox" data-goal-active ${b.active!==false?'checked':''}>Include in this direction</label></div></details>`;}
function goalsEditor({planning=false}={}){const g=state.goals||{goals:[],measures:[],runs:[]};const pending=g.runs?.find(r=>r.current&&!r.body.applied);
 if(planning)return `<section class="card planning-panel planning-goals" aria-labelledby="planning-goals-title">
  <header class="planning-indicators-head"><h2 id="planning-goals-title">Performance Indicators</h2>
   <div class="planning-indicator-tools">
    ${pending?button('Review proposals','goals-result',pending.ref.id,'compact-text-action'):''}</div>
  </header>
  <p class="caption">These indicators are developed from answers to the Business development intake questions.</p>
  <section class="planning-indicator-group" aria-labelledby="planning-outcomes-title">
   <header class="planning-subsection-head"><h3 id="planning-outcomes-title">Goals</h3>
    <button type="button" class="compact-icon-action" data-action="goals-add" data-id="goals" aria-label="Add goal" title="Add goal"><svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M8 2v12M2 8h12"/></svg></button>
   </header>
   <div class="planning-subsection-body"><div id="goal-drafts">${g.goals.map(x=>goalDraftRow(x,'goals',{planning:true})).join('')}</div></div>
  </section>
  <section class="planning-indicator-group" aria-labelledby="planning-kpis-title">
   <header class="planning-subsection-head"><h3 id="planning-kpis-title">KPIs</h3>
    <button type="button" class="compact-icon-action" data-action="goals-add" data-id="measures" aria-label="Add KPI" title="Add KPI"><svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M8 2v12M2 8h12"/></svg></button>
   </header>
   <div class="planning-subsection-body"><div id="measure-drafts">${g.measures.map(x=>goalDraftRow(x,'measures',{planning:true})).join('')}</div></div>
  </section>
 </section>`;
 return `<section class="card goals-panel"><div class="card-head"><h2>Goals & success measures</h2></div>${!g.goals.length?'<p class="caption">Define the outcomes this work should achieve and how you will measure them.</p>':''}<div id="goal-drafts">${g.goals.map(x=>goalDraftRow(x,'goals')).join('')}</div>${button('Add goal','goals-add','goals','small')}<details class="goal-measures"><summary>Success measures <span class="caption">(${g.measures.length})</span></summary><div class="details-body"><div id="measure-drafts">${g.measures.map(x=>goalDraftRow(x,'measures')).join('')}</div>${button('Add measure','goals-add','measures','small')}</div></details>${pending?`<div class="actions">${button('Review prepared proposals','goals-result',pending.ref.id,'small')}</div>`:''}</section>`;}
function goalsFormValues(form){const out={goals:[],measures:[]};form.querySelectorAll('.goal-record[data-group]').forEach(el=>{const x={id:el.dataset.goalId,active:el.querySelector('[data-goal-active]').checked,basis_fields:Array.from(el.querySelectorAll('[data-basis-field]:checked')).map(i=>i.dataset.basisField),review_basis:el.querySelector('[data-review-basis]')?.checked||false};el.querySelectorAll('[data-goal-field]').forEach(i=>x[i.dataset.goalField]=i.value);if(el.dataset.group==='measures')x.goal_ids=Array.from(el.querySelectorAll('[data-measure-goal]:checked')).map(i=>i.dataset.measureGoal);out[el.dataset.group].push(x);});return out;}
function goalLinkEditor(d){const goals=state.goals?.goals||[];return `<details class="goal-area-links"><summary>Goals supported <span class="caption">(${(d.goal_ids||[]).length})</span></summary><div class="details-body"><div class="area-goal-choices">${goalChoices(goals,d.goal_ids||[],'data-area-goal')}</div><p class="caption">Link relevant outcomes. Policy and constraint requirements can stand independently.</p></div></details>`;}
function syncMeasureGoalSupport(form=document.querySelector('#intake-drawers-form')){if(!form)return;const values=goalsFormValues(form),goals=values.goals.map(body=>({id:body.id,body}));form.querySelectorAll('.goal-record[data-group="measures"]').forEach(row=>{const body=values.measures.find(item=>item.id===row.dataset.goalId),support=row.querySelector('summary .measure-goal-support');if(body&&support)support.outerHTML=measureGoalSupportRead({body},goals);});}
function syncGoalChoices(){const form=document.querySelector('#intake-drawers-form');if(!form)return;const gs=goalsFormValues(form).goals.map(x=>({id:x.id,body:x}));form.querySelectorAll('.area-goal-choices,.goal-choices').forEach(el=>{const measure=el.classList.contains('goal-choices'),attr=measure?'data-measure-goal':'data-area-goal',selected=Array.from(el.querySelectorAll('input:checked')).map(i=>i.getAttribute(attr));el.innerHTML=measure?measureGoalChoices(gs,selected,el.closest('.goal-record').dataset.goalId):goalChoices(gs,selected,attr);});syncMeasureGoalSupport(form);}
function goalCollectionCover(kind,title,preview,status,{support=''}={}){
 const icon=typeof requirementTileIcon==='function'?requirementTileIcon(kind):'',short=String(preview||'').replace(/\s+/g,' ').trim();
 return `<span class="requirement-collection-cover"><span class="collection-cover-heading"><span class="collection-cover-icon">${icon}</span><span class="workbench-object-type">${kind==='goal'?'Goal':'Success measure'}</span><span class="collection-cover-title" title="${esc(title)}">${typeof requirementCardTitle==='function'?requirementCardTitle(title):esc(title)}</span>${support}</span><span class="collection-cover-preview">${esc(short.length>180?short.slice(0,177)+'…':short)}</span><span class="collection-cover-status">${esc(status)}</span></span>`;
}
function measureRead(item,options={}){
 // Array.map passes an index as its second argument; it is never a catalog.
 const opts=options&&typeof options==='object'&&!Array.isArray(options)?options:{},b=item.body,title=measureDisplayTitle(b.name||b.title||b.text||'Unnamed measure'),rowTitle=esc(title)+(b.active===false?' · Inactive':''),support=measureGoalSupportRead(item,opts.goals||[],{shared:!!opts.shared||!!item.scope&&String(item.scope).startsWith('project:')});
 const baseline=b.baseline===undefined||b.baseline===null||b.baseline===''?'Baseline not specified':'Baseline: '+b.baseline,row=indicatorObjectHeading('Success measure',rowTitle,support);
 const summary=opts.tileCover?`<span class="collection-row-title">${row}</span>${goalCollectionCover('measure',title,b.definition||'Calculation or observation not yet specified',(b.active===false?'Inactive · ':'')+baseline,{support})}`:row;
 return `<details class="goal-measure-read"><summary>${summary}</summary><div class="details-body">${indicatorSourceLinks(item)}${Object.entries(measureLabels).filter(([k])=>k!=='name').map(([k,t])=>val(t,b[k]||'Not yet specified')).join('')}<p class="caption">${item.ref?'Version '+item.ref.revision+' · ':''}Outcome not yet evaluated</p>${item.ref?sourceDetails(item.ref):''}</div></details>`;
}
function goalsRead(catalog,title='Goals & success measures',headingLevel=2,shared=false,options={}){
 const heading=headingLevel===3?'h3':'h2',tileCovers=Boolean(options?.tileCovers),goals=(catalog?.goals||[]).filter(goal=>!shared||indicatorSharedRecord(goal)),measures=(catalog?.measures||[]).filter(measure=>!shared||indicatorSharedRecord(measure));
 const governed=Boolean(state.intake?.setup_governance?.enabled&&state.intake.setup_governance.baseline),provenance=shared?`<p class="caption">These indicators are developed from answers to the Business development intake questions and published through Requirements set up. ${governed?'Later changes go through Decisions & Issues, published Outcomes reports and an approved sponsor decision.':'This version is read only; draft changes appear here after Review &amp; publish.'}</p>${state.actor==='priya'?(governed?'<a href="#main" class="item-title-link workbench-module-origin" data-nav="review">Propose changes in Decisions & Issues</a>':'<a href="#main" class="item-title-link workbench-module-origin" data-nav="planning">Edit in Business development</a>'):''}`:'';
 const origin=tileCovers&&provenance?`<div class="collection-origin-rows">${provenance}</div><details class="collection-origin-tiles"><summary>Origin &amp; changes</summary><div class="details-body">${provenance}</div></details>`:provenance;
 if(!goals.length&&!measures.length)return '';
 const linked=(goal,measure)=>(measure.body.goal_ids||[]).includes(indicatorGoalId(goal))||goalPinsMeasure(goal,measure);
 return `<section class="card section workbench-record-module${tileCovers?' requirement-organization-goals':''}"><header class="workbench-module-header"><${heading}>${esc(title)}</${heading}>${tileCovers&&typeof requirementTileIcon==='function'?`<span class="collection-module-icon">${requirementTileIcon('goal')}</span>`:''}${origin}</header><div class="workbench-module-drawers">${goals.map(g=>{
  const associated=measures.filter(m=>linked(g,m)),rowTitle=esc(g.body.title)+(g.body.active===false?' · Inactive':''),row=indicatorObjectHeading('Goal',rowTitle),status=(g.body.active===false?'Inactive · ':'')+(associated.length?associated.length+(tileCovers?' ':' linked ')+(associated.length===1?'measure':'measures'):'No measures linked');
  const summary=tileCovers?`<span class="collection-row-title">${row}</span>${goalCollectionCover('goal',g.body.title,g.body.outcome||'Intended outcome not yet specified',status)}`:row;
  return `<details class="goal-read"><summary>${summary}</summary><div class="details-body">${indicatorSourceLinks(g)}${val('Intended outcome',g.body.outcome)}${val('Beneficiary',g.body.beneficiary||'Not yet specified')}${val('Value connection',g.body.rationale||'Not yet specified')}${val('Owner',g.body.owner||'Not yet specified')}${associated.map(m=>measureRead(m,{goals,shared})).join('')}${!associated.length?'<p class="caption">No measure linked yet.</p>':''}${g.ref?`<p class="caption">Version ${g.ref.revision}</p>${sourceDetails(g.ref)}`:''}</div></details>`;
 }).join('')}${measures.filter(m=>!goals.some(g=>linked(g,m))).map(m=>measureRead(m,{tileCover:tileCovers,goals,shared})).join('')}</div></section>`;
}
function publicGoalsRead(){return goalsRead({goals:records('goal'),measures:records('success-measure')},'Goals & success measures',2,true);}
function exactGoalRecord(raw,{kind,shared=false}={}){return [...(state.records||[]),...(state.packets||[]).flatMap(p=>p.records||[]),...(state.cases||[]).flatMap(c=>c.basis_records||[])].find(r=>r.ref.id===raw.id&&r.ref.revision===raw.revision&&(!kind||r.kind===kind)&&(!shared||indicatorSharedRecord(r)));}
function linkedGoalsRead(body){
 const refs=body.goal_refs||[];if(!refs.length)return '';
 const pinned=refs.map(raw=>({raw,record:exactGoalRecord(raw,{kind:'goal',shared:true})})),goals=pinned.map(item=>item.record).filter(Boolean);
 return `<section class="section"><h3>Goals supported</h3>${pinned.map(({raw,record:g})=>{
  const latest=get(raw.id),title=g?.body.title||'Goal unavailable';
  return `<details class="goal-read"><summary>${indicatorObjectHeading('Goal',esc(title))}${latest&&latest.ref.revision!==raw.revision?' <span class="caption">Newer version needs review</span>':''}</summary><div class="details-body">${g?indicatorSourceLinks(g)+val('Intended outcome',g.body.outcome):'<p>Exact goal version unavailable.</p>'}${sourceDetails(raw)}${(g?.body.measure_refs||[]).map(ref=>{const m=exactGoalRecord(ref,{kind:'success-measure',shared:true});return m?measureRead(m,{goals,shared:true}):'<p>Exact measure version unavailable.</p>';}).join('')}</div></details>`;
 }).join('')}</section>`;
}
function openGoalsResult(id){const r=state.goals?.runs.find(x=>x.ref.id===id);if(!r)throw Error('This proposal is no longer available. Prepare another from the current intake.');const o=r.body.output,byKey=Object.fromEntries(o.goals.map(g=>[g.key,g.title])),areas=scaffoldLeaves();const preview={goals:o.goals.map(g=>({id:g.key,body:{...g,active:true}})),measures:o.measures.map(m=>({body:{...m,active:true,goal_ids:m.goal_keys}}))};const fresh=r.current&&!r.body.applied,hasItems=o.goals.length||o.measures.length;modal('Review goals & measures',para(o.summary)+goalsRead(preview)+o.goals.filter(g=>g.area_paths.length).map(g=>val('Suggested areas for '+byKey[g.key],g.area_paths.map(p=>areas.find(a=>a.key===p)?.label||p).join(' · '))).join('')+(fresh?'<p class="caption">Use these as editable drafts. Sharing them requires the direction review.</p>':'<p class="caption">This proposal has been used or its inputs changed.</p>'),fresh&&hasItems?'Use these drafts':null,fresh&&hasItems?()=>command('goals-apply',{expected:state.intake.draft.ref,result:r.ref,confirm:true}):null,{className:'settings-dialog'});}
async function goalsAction(action,id){if(!action.startsWith('goals-'))return false;if(action==='goals-save-draft'){const form=document.getElementById('sponsor-goals-form');if(!form)return true;await command('goals-save',{expected:state.intake.draft.ref,...sponsorGoalsWithoutBlankRows(goalsFormValues(form))});sponsorGoalsDirty=false;await load();render();toast('Goals and success measures saved as drafts.');return true;}if(action==='goals-source'){openIndicatorSource(id);return true;}if(action==='goals-source-current'){await openCurrentIndicatorAnswer(id);return true;}if(action==='goals-add'){sponsorGoalsDirty=sponsorGoalsDirty||!!document.getElementById?.('sponsor-goals-form');const group=id==='measures'?'measures':'goals',item={id:(group==='goals'?'G-':'M-')+crypto.randomUUID().replaceAll('-','').slice(0,10),body:{active:true,basis_fields:[],goal_ids:[]}};const list=document.querySelector(group==='goals'?'#goal-drafts':'#measure-drafts');list.insertAdjacentHTML('beforeend',goalDraftRow(item,group,{planning:typeof view!=='undefined'&&view==='planning'}));list.lastElementChild.open=true;list.lastElementChild.querySelector('input').focus();pageDirty=true;syncGoalChoices();return true;}
 if(pageDirty)throw Error('Save the scaffold draft first so preparation uses your current goals and answers.');
 if(action==='goals-result'){openGoalsResult(id);return true;}
 if(action==='goals-prepare'){const model=state.coaching?.model||{};modal('Prepare goals & measures',`<p>Prepare proposed outcomes, measures and relevant scaffold links from the saved business intake.</p><p class="caption">Sends the saved intake, goals and area definitions to the configured model. Missing baselines and targets stay open.</p>`,'Prepare proposals',async()=>{const r=await command('goals-prepare',{expected:state.intake.draft.ref,consent:true});return {...r,goalsResult:r.ref.id};},{busyLabel:'Preparing proposals…'});return true;}return false;}
document.addEventListener('change',e=>{if(e.target.matches('[data-goal-field="title"],[data-goal-active]'))syncGoalChoices();const row=e.target.closest('.goal-record');if(row&&e.target.matches('[data-goal-field="title"],[data-goal-field="name"]')){const title=row.querySelector('.goal-record-title');title.textContent=(row.dataset.group==='measures'?measureDisplayTitle(e.target.value):e.target.value)||'Untitled';}});

function draftGoalLinksRead(area,catalog){if(!area.goal_ids?.length||!catalog?.goals)return '';return val('Goals supported',area.goal_ids.map(id=>catalog.goals.find(g=>g.id===id)?.body.title||id).join(' · '));}

document.addEventListener('change',e=>{if(e.target.matches('[data-basis-field]')){refreshBasisSummary(e.target.closest('.goal-record'));}});

document.addEventListener('change',e=>{if(e.target.matches('[data-measure-goal]'))syncMeasureGoalSupport();});
// Goals & success measures in the sponsor's Business Intent step: the proof of the Core Value Statement's promise.
function goalsFormPayload(form){return form?.querySelector?.('.goal-record[data-group]')?{goals_catalog:goalsFormValues(form)}:{};}
function sponsorGoalsPanel(){const g=state.goals||{goals:[],measures:[],runs:[]},pending=g.runs?.find(r=>r.current&&!r.body.applied);
 return `<form id="sponsor-goals-form" class="sponsor-panel sponsor-goals-panel" aria-labelledby="sponsor-goals-title"><div class="sponsor-panel-body"><p class="sponsor-goals-kicker">The proof of the promise</p><h2 id="sponsor-goals-title">Goals &amp; success measures</h2><p class="caption">Goals say what must become true; measures show whether it has.</p>
 <section class="sponsor-goals-group"><div class="sponsor-goals-head"><h3>Goals</h3>${button('Add goal','goals-add','goals','quiet small')}</div><div id="goal-drafts">${g.goals.map(x=>goalDraftRow(x,'goals')).join('')||''}</div>${g.goals.length?'':'<p class="caption">No goals yet. Name an outcome the value statement promises.</p>'}</section>
 <section class="sponsor-goals-group"><div class="sponsor-goals-head"><h3>Success measures</h3>${button('Add measure','goals-add','measures','quiet small')}</div><div id="measure-drafts">${g.measures.map(x=>goalDraftRow(x,'measures')).join('')}</div>${g.measures.length?'':'<p class="caption">No measures yet. Say how you would know a goal is met.</p>'}</section>
 <div class="sponsor-actions">${button('Save goals & measures','goals-save-draft','','primary small')}${pending?button('Review prepared proposals','goals-result',pending.ref.id,'quiet small'):''}<span class="caption" id="sponsor-goals-status" role="status">Private draft until you share for direction review</span></div></div></form>`;}
function sponsorGoalsRead(){return `<section class="card planning-panel planning-goals"><header class="planning-indicators-head"><h2>Goals &amp; success measures</h2><button type="button" class="compact-text-action" data-action="sponsor-step" data-id="framing">Edit in Business Intent</button></header><p class="caption">Set in step 1 with the Core Value Statement. Requirements link to them here.</p>${typeof goalsRead==='function'?goalsRead(state.goals,'Current goals and measures',3):''}</section>`;}
let sponsorGoalsDirty=false;
if(typeof document!=='undefined'&&typeof document.addEventListener==='function'){document.addEventListener('input',e=>{if(e.target.closest?.('#sponsor-goals-form')){sponsorGoalsDirty=true;const s=document.getElementById('sponsor-goals-status');if(s)s.textContent='Unsaved changes';}});}
// Save unsaved goal edits before leaving the step, like the rest of the sponsor workspace. An incomplete row stops navigation with its message.
function sponsorGoalsWithoutBlankRows(v){const g=typeof state!=='undefined'?state.goals:null,saved=new Set([...(g?.goals||[]),...(g?.measures||[])].map(x=>x.id));const blank=x=>!saved.has(x.id)&&!['title','outcome','name','baseline','target','definition'].some(k=>String(x[k]||'').trim());return {goals:v.goals.filter(x=>!blank(x)),measures:v.measures.filter(x=>!blank(x))};}
async function sponsorGoalsSaveIfDirty(){const form=document.getElementById?.('sponsor-goals-form');if(!form||!sponsorGoalsDirty)return;const v=sponsorGoalsWithoutBlankRows(goalsFormValues(form));sponsorGoalsDirty=false;if(!v.goals.length&&!v.measures.length)return;try{await command('goals-save',{expected:state.intake.draft.ref,...v});await load();}catch(e){sponsorGoalsDirty=true;throw e;}}

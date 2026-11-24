'use strict';
// A reading hierarchy over published objects; no classifications or records change.
const requirementLayoutPreferences=new Map();
// Editorial navigation labels, not replacement requirement wording. Match only
// reviewed exact titles; unfamiliar wording stays intact rather than being cut.
const requirementCardLabels=new Map([
 ['Show evidence and limits of returned status','Status sources & limits'],
 ['One durable record and audit history','Record & audit trail'],
 ['Measure benefit beyond ticket activity','Outcome measurement'],
 ['Identity and permitted access','Identity & access'],
 ['Separate recovery, resolution and closure','Recovery, resolution & closure'],
 ['Accountable routing and reassignment','Accountable routing & reassignment'],
 ['Carry context across shifts and dependent responder work','Context across handoffs'],
 ['Visible lifecycle and resolution note','Lifecycle & resolution'],
 ['Low-effort mobile submission','Mobile submission'],
 ['Submit without knowing the owner','No owner lookup'],
 ['Reduce repeated coordination and duplicate work','Reduce repeated coordination'],
 ['Know who is acting and what happens next','Ownership & next action']
]);
function requirementCardTitle(title){
 const full=String(title||''),brief=requirementCardLabels.get(full);
 return brief?`<span class="card-title-full">${esc(full)}</span><span class="card-title-brief">${esc(brief)}</span>`:esc(full);
}
function requirementLayoutKey(){return ['adaptive-cointelligence','requirement-layout',state.project?.id||'project',state.actor||''].join(':');}
function requirementLayout(){
 const key=requirementLayoutKey();if(requirementLayoutPreferences.has(key))return requirementLayoutPreferences.get(key);
 try{const saved=localStorage.getItem(key);if(saved==='tiles'||saved==='rows')return saved;}catch{}
 return 'tiles';
}
function requirementLayoutControl(){return `<label class="requirement-layout-control"><span>Layout</span><select id="requirement-layout" aria-label="Requirement layout"><option value="tiles" ${requirementLayout()==='tiles'?'selected':''}>Tiles</option><option value="rows" ${requirementLayout()==='rows'?'selected':''}>Rows</option></select></label>`;}
document.addEventListener('change',event=>{
 if(event.target.id!=='requirement-layout')return;
 const layout=event.target.value==='rows'?'rows':'tiles',key=requirementLayoutKey();
 requirementLayoutPreferences.set(key,layout);try{localStorage.setItem(key,layout);}catch{}
 // Change only the presentation: keep open drawers, unsent reviewer text and focus.
 document.querySelectorAll('.requirement-organization,.requirement-organization-requirements').forEach(node=>{node.dataset.requirementLayout=layout;});
});
function requirementTileIcon(kind){
 const paths={
  goal:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="m12 12 8-8M16 4h4v4"/>',
  measure:'<path d="M4 4v16h16M8 16v-4m5 4V8m5 8V5"/>',
  requirement:'<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2h6v2M9 9h6M9 13h6M9 17h4"/>',
  scope:'<circle cx="12" cy="12" r="9"/><path d="m16 8-2 6-6 2 2-6Z"/>',
  constraints:'<path d="m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6Z"/><path d="M8 12h8"/>',
  dependencies:'<path d="m10 14 4-4M8 15l-1 1a3 3 0 0 1-4-4l4-4a3 3 0 0 1 4 0m2 8a3 3 0 0 0 4 0l4-4a3 3 0 0 0-4-4l-1 1"/>',
  assumptions:'<path d="M9 17v-2a6 6 0 1 1 6 0v2M9 18h6m-5 3h4"/><path d="M12 8v3"/>',
  technology:'<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8m-4-4v4m-3-12-3 2 3 2m6-4 3 2-3 2"/>',
  operations:'<rect x="2" y="8" width="6" height="8" rx="1"/><rect x="16" y="8" width="6" height="8" rx="1"/><path d="M8 12h8m-3-3 3 3-3 3"/>',
  experience:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 8h18M9 8v13m3-9h5m-5 4h3"/>',
  people:'<circle cx="9" cy="7" r="3"/><path d="M3 21v-2a6 6 0 0 1 12 0v2m2-17a3 3 0 0 1 0 6m2 11v-2a6 6 0 0 0-2-4"/>',
  risks:'<path d="m12 3 10 18H2Z"/><path d="M12 9v5m0 3h.01"/>'
 };
 return `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths[kind]||paths.requirement}</svg>`;
}
function requirementCategoryType(title){return ({'Technology and integration':'technology','Outcomes and measurement':'measure','Policy, access and boundaries':'constraints','Operations and support':'operations','Experience and usability':'experience','Customer and user needs':'people'})[title]||'requirement';}
function requirementCategoryIcon(title){return requirementTileIcon(requirementCategoryType(title));}
function requirementOrganizationShared(r){return !!r&&(!r.scope||String(r.scope).startsWith('project:'));}
function requirementOrganizationRows(reqs){
 const latest=new Map();
 for(const r of reqs){if(r?.kind!=='requirement'||!r.ref?.id||!requirementOrganizationShared(r)||!['proposed','approved'].includes(r.body?.status))continue;const prior=latest.get(r.ref.id);if(!prior||r.ref.revision>prior.ref.revision)latest.set(r.ref.id,r);}
 return [...latest.values()];
}
function requirementOrganizationCategories(rows){
 const categories=typeof ratifiedRequirementCategoryRows==='function'?ratifiedRequirementCategoryRows():[],byId=new Map(categories.map(r=>[r.ref.id,r])),groups=new Map();
 for(const r of rows){
  const categoryId=typeof ratifiedRequirementCategoryId==='function'?ratifiedRequirementCategoryId(r.body.drawer_id):'',category=byId.get(categoryId),title=category?.body.label||r.body.drawer||'',key=categoryId||'label:'+title;
  if(!groups.has(key))groups.set(key,{categoryId,drawerId:category?.ref.id||r.body.drawer_id||'',title,rows:[]});
  groups.get(key).rows.push(r);
 }
 // Keep the established canonical category order; unassigned records retain their order.
 const order=new Map(categories.map((r,i)=>[r.ref.id,i]));
 return [...groups.values()].sort((a,b)=>(order.get(a.categoryId)??categories.length)-(order.get(b.categoryId)??categories.length));
}
function requirementOrganizationAreasRead(){
 const drawers=typeof sharedRequirementDrawerRows==='function'?sharedRequirementDrawerRows():[];
 if(!drawers.length)return '';
 const byId=new Map(drawers.map(r=>[r.ref.id,r])),roots=drawers.filter(r=>!r.body.parent_id||!byId.has(r.body.parent_id));
 const link=r=>`<a href="#main" class="item-title-link" data-action="open-drawer" data-id="${esc(r.ref.id)}">${esc(r.body.label||'Published area')}</a>`;
 return `<details class="requirement-organization-areas"><summary>Investigation areas & review guidance</summary><div class="requirement-organization-area-list">${roots.map(root=>`<section ${typeof ratifiedRequirementCategoryAttributes==='function'?ratifiedRequirementCategoryAttributes(root.ref.id):''}><h3>${link(root)}</h3>${drawers.some(r=>r.body.parent_id===root.ref.id)?`<ul>${drawers.filter(r=>r.body.parent_id===root.ref.id).map(child=>`<li>${link(child)}</li>`).join('')}</ul>`:''}</section>`).join('')}</div></details>`;
}
function requirementOrganizationRequirementsRead(reqs){
 const rows=requirementOrganizationRows(reqs),groups=requirementOrganizationCategories(rows),hasAssessment=rows.some(r=>Object.values(typeof requirementAssessmentItem==='function'?requirementAssessmentItem(r)?.uses||{}:{}).some(use=>use.current));
 const legend=hasAssessment?'<div class="requirement-coverage-legend" aria-label="Evidence coverage legend"><span><i class="coverage-supported" aria-hidden="true"></i>Supported</span><span><i class="coverage-unresolved" aria-hidden="true"></i>Unresolved</span><span><i class="coverage-contradicted" aria-hidden="true"></i>Contradicted</span><span><i class="coverage-unchecked" aria-hidden="true"></i>Unchecked</span></div>':'';
 return `<section class="card section workbench-record-module requirement-assessment-map requirement-organization-requirements" data-requirement-layout="${requirementLayout()}" aria-labelledby="organized-requirements-title"><header class="workbench-module-header"><h2 id="organized-requirements-title">Requirements</h2><span class="collection-module-icon">${requirementTileIcon('requirement')}</span>${legend}</header><div class="workbench-module-drawers requirement-category-grid">${groups.map((group,index)=>`<section class="requirement-organization-category" data-wayfinding-category="${requirementCategoryType(group.title)}" data-category-size="${Math.min(3,group.rows.length)}" ${typeof ratifiedRequirementCategoryAttributes==='function'?ratifiedRequirementCategoryAttributes(group.drawerId):''}${group.title?` aria-labelledby="requirement-category-${index}"`:''}>${group.title?`<header class="requirement-organization-category-heading"><h3 id="requirement-category-${index}">${esc(group.title)}</h3><span class="requirement-category-icon">${requirementCategoryIcon(group.title)}</span><span class="caption">${group.rows.length} requirement${group.rows.length===1?'':'s'}</span></header>`:''}<div class="requirement-record-list">${group.rows.map(r=>publishedRequirementRead(r,{preview:true})).join('')}</div></section>`).join('')}${rows.length?'':'<p class="caption">No requirement wording has been published yet.</p>'}</div>${requirementOrganizationAreasRead()}</section>`;
}
function requirementOrganizationPublishedIntent(){return records('intent').filter(requirementOrganizationShared).sort((a,b)=>(b.ref?.revision||0)-(a.ref?.revision||0))[0]||null;}
function requirementOrganizationPolicy(intent){
 if(intent){
  const packet=(state.packets||[]).find(p=>p.id==='PKT-INTENT'&&(p.records||[]).some(r=>r.kind==='intent'&&r.ref.id===intent.ref.id&&r.ref.revision===intent.ref.revision));
  const pinned=packet?.records?.find(r=>r.kind==='policy'&&requirementOrganizationShared(r));
  if(pinned)return {record:pinned,pinned:true};
 }
 const current=records('policy').filter(requirementOrganizationShared)[0];
 return current?{record:current,pinned:false}:null;
}
function requirementOrganizationIntentFactorsRead(){
 const intent=requirementOrganizationPublishedIntent(),values=intent?.body.intake||{},policy=requirementOrganizationPolicy(intent),factorDefinitions=[
  ['Scope',[['in_scope','Included work'],['out_scope','Outside scope']]],
  ['Constraints',[['constraints','Rules and limits'],['operating_limits','Operating limits'],['project_limits','Project limits']]],
  ['Dependencies',[['dependencies','Dependencies'],['handoffs','Handoffs'],['tools','Existing systems and tools']]],
  ['Assumptions',[['assumptions','Assumptions']]],
  ['Risks & open decisions',[['project_risks','Risks'],['open_questions','Open questions'],['scope_unknowns','Unsettled scope']]]
 ];
 const factors=factorDefinitions.map(([title,fields])=>{const seen=new Set(),items=fields.filter(([key])=>typeof values[key]==='string'&&values[key].trim()).filter(([key])=>{const value=values[key].trim();if(seen.has(value))return false;seen.add(value);return true;}).map(([key,label])=>({label,text:values[key]}));return {title,items,refs:intent?[intent.ref]:[]};}).filter(f=>f.items.length);
 if(policy&&typeof policy.record.body.text==='string'&&policy.record.body.text.trim()){
  const combined=[values.constraints,values.out_scope?'Outside scope: '+values.out_scope:''].filter(Boolean).join('\n');
  if(policy.pinned&&policy.record.body.text.trim()===combined.trim()&&factors.some(f=>f.title==='Constraints'))factors.find(f=>f.title==='Constraints').refs.push(policy.record.ref);
  else factors.push({title:policy.pinned?'Published policy & limits':'Current project policy & limits',items:[{label:policy.record.body.status==='user-declared-boundary'?'User-declared boundary':'Recorded policy',text:policy.record.body.text}],refs:[policy.record.ref]});
 }
 if(!factors.length)return '';
 return `<section class="card section workbench-record-module requirement-organization-intent" aria-labelledby="intent-factors-title"><header class="workbench-module-header"><h2 id="intent-factors-title">Intent factors</h2><span class="collection-module-icon">${requirementTileIcon('scope')}</span><p class="caption">${intent?'From published Business Intent · v'+esc(intent.ref.revision):'Published project limits'}</p></header><div class="workbench-module-drawers">${factors.map(factor=>{const icon=({'Scope':'scope','Constraints':'constraints','Dependencies':'dependencies','Assumptions':'assumptions','Risks & open decisions':'risks'})[factor.title]||'constraints';return `<details class="requirement-intent-factor"><summary><span class="collection-row-title">${esc(factor.title)}</span><span class="requirement-collection-cover"><span class="collection-cover-heading"><span class="collection-cover-icon">${requirementTileIcon(icon)}</span><span class="collection-cover-title">${esc(factor.title)}</span></span><span class="collection-cover-preview">${esc(factor.items[0].text)}</span></span></summary><div class="details-body">${factor.items.map(item=>val(item.label,item.text)).join('')}${sourceDetails(factor.refs)}</div></details>`;}).join('')}</div></section>`;
}
function requirementOrganizationRead(reqs=[]){
 const goals=records('goal').filter(requirementOrganizationShared),measures=records('success-measure').filter(requirementOrganizationShared);
 const indicators=typeof goalsRead==='function'?goalsRead({goals,measures},'Goals and measures',2,true,{tileCovers:true}):'';
 return `<div class="requirement-organization" data-requirement-layout="${requirementLayout()}">${indicators}${requirementOrganizationRequirementsRead(reqs)}${requirementOrganizationIntentFactorsRead()}</div>`;
}
// Measure rendered, closed covers at the user's actual column width. Presentation
// only: preserve the same nodes, disclosure state, focus and reviewer draft.
let requirementTileLayoutRoot=null,requirementTileResize=null,requirementTileMutations=null;
function mountRequirementTileLayout(){
 if(typeof ResizeObserver==='undefined'||typeof requestAnimationFrame==='undefined')return;
 const root=document.querySelector('.requirement-organization');
 if(root===requirementTileLayoutRoot)return;
 requirementTileResize?.disconnect();requirementTileMutations?.disconnect();requirementTileLayoutRoot=root;
 if(!root)return;
 let queued=false,lastWidth=-1;
 const schedule=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{
  queued=false;if(!root.isConnected)return;
  root.style.removeProperty('--requirement-tile-height');
  if(root.dataset.requirementLayout!=='tiles')return;
  const covers=[...root.querySelectorAll('.requirement-record:not([open])>summary,.workbench-module-drawers>.goal-read:not([open])>summary,.workbench-module-drawers>.goal-measure-read:not([open])>summary,.workbench-module-drawers>.requirement-intent-factor:not([open])>summary')].filter(node=>node.getBoundingClientRect().width>0);
  const height=Math.ceil(Math.max(0,...covers.map(node=>node.getBoundingClientRect().height)));
  if(height)root.style.setProperty('--requirement-tile-height',height+'px');
 });};
 requirementTileResize=new ResizeObserver(entries=>{const width=entries[0]?.contentRect.width;if(width!==lastWidth){lastWidth=width;schedule();}});requirementTileResize.observe(root);
 if(typeof MutationObserver!=='undefined'){
  requirementTileMutations=new MutationObserver(schedule);
  requirementTileMutations.observe(root,{childList:true,subtree:true,attributes:true,attributeFilter:['data-requirement-layout','hidden']});
 }
 root.addEventListener('toggle',event=>{if(!event.target.open)schedule();},true);
 document.fonts?.ready.then(schedule);schedule();
}

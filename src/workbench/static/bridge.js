'use strict';
let bridgeBoard='research-design',bridgeSection='overview';
let bridgeRequirementBucket='candidates',bridgeRequirementCategory='';
const bridgeStatuses={open:'Open',investigating:'Investigating','awaiting-decision':'Awaiting decision',deferred:'Deferred',resolved:'Resolved'};
const bridgeRoutes={requirement:'Requirement change',intent:'Business Intent',coordination:'Coordination'};
function bridgeInfo(){return state.bridge||{boards:{'business-research':'Sponsor · Research','business-design':'Sponsor · Design','research-design':'Research · Design'},kinds:{},issues:[],actors:[]};}
function bridgeIssue(id=selected){return bridgeInfo().issues.find(i=>i.ref.id===id);}
function bridgePerson(id){return state.actors[id]?.name||id||'Unassigned';}
function bridgeDecisionReady(issue,review){
 return review.ready&&!issue.changed.length&&issue.body.information_request?.status!=='open'&&!bridgeOtherHolds(review).length;
}
function bridgeCanManage(i){return i.body.owner===state.actor||(i.rights?.can_decide??i.body.decision_owner===state.actor)||(i.body.status==='resolved'&&state.actor===(state.decision_rights?.rules?.[i.body.route]?.decider||i.body.decision_owner));}
function bridgePublicPackets(selected=[]){
 const all=(state.packets||[]).filter(p=>p.audience_scopes.length===1&&p.audience_scopes[0]==='project:demo'),chosen=new Set(selected.map(packetKey)),latest=new Map();
 for(const p of all)if(!latest.has(p.id)||latest.get(p.id).revision<p.revision)latest.set(p.id,p);
 return all.filter(p=>latest.get(p.id)===p||chosen.has(packetKey(p)));
}
const bridgePrimarySections=[['overview','Overview'],['boards','Issues'],['timeline','Timeline']];
const bridgeDetailSections=[['work','Published work'],['activity','Teams & Agents'],['reviews','Requirement reviews']];
function bridgeTabs(){
 return `<nav class="bridge-sections" aria-label="Decisions & Issues sections">${bridgePrimarySections.map(([key,title])=>
  `<button type="button" class="bridge-tab" data-action="bridge-section" data-id="${key}" ${bridgeSection===key?'aria-current="page"':''}>${esc(title)}</button>`
 ).join('')}</nav>`;
}
function bridgeWayfindingIcon(kind){return typeof navigationWayfindingIcon==='function'?`<span class="surface-wayfinding-icon">${navigationWayfindingIcon(kind)}</span>`:'';}
function bridgeRailSection(key,summary,content){
 const title=bridgeDetailSections.find(([id])=>id===key)[1],active=bridgeSection===key;
 const action={work:'View published work',activity:'View teams & agents',reviews:'View all reviews'}[key],destination=key==='reviews'?'bridge-requirement-view':'bridge-section';
 return `<section data-wayfinding-section="${key}" class="card accountability-rail-panel${active?' is-current':''}" aria-labelledby="accountability-rail-${key}">
  <header><h2 id="accountability-rail-${key}">${esc(title)}</h2>${bridgeWayfindingIcon(key==='activity'?'collaboration':key==='work'?'files':'work')}<p class="accountability-rail-summary">${esc(summary)}</p></header>${content}
  <footer class="accountability-rail-action"><button type="button" class="accountability-rail-workspace-action" data-action="${destination}" data-id="${key}" ${active?'aria-current="page"':''}>${esc(action)}<span aria-hidden="true">→</span></button></footer></section>`;
}
function bridgePublishedWork(){return [...records('contribution')].sort((a,b)=>(b.body.published_at||'').localeCompare(a.body.published_at||''));}
function bridgeProjectUpdate(published=bridgePublishedWork(),items=[...bridgeTimelineStatus({includeAccepted:true}),...bridgeSponsorGates()]){
 const latest=published.slice(0,2),needsResponse=items.filter(item=>item.attention!==false).sort(accountabilityItemPriority);
 const mine=needsResponse.filter(item=>(Array.isArray(item.owner)?item.owner:[item.owner]).includes(state.actor)),next=mine[0]||needsResponse[0];
 const publicationTitle=latest.length?latest.map((record,index)=>(index===0?'Latest: ':'Previous: ')+(record.body.title||'Domain contribution')).join('\n'):'Nothing published yet.';
 const responseTitle=next?'Next response: '+next.title+'\nDue date not set.':'No pending responses.';
 return `<nav class="accountability-update-summary" aria-label="Project update summary"><div class="accountability-update-links">
  <a href="#main" class="item-title-link" data-action="bridge-section" data-id="work" title="${esc(publicationTitle)}">${latest.length?'Last '+latest.length+' published':'Nothing published'}</a><span aria-hidden="true">·</span>
  <a href="#main" class="item-title-link" data-action="bridge-section" data-id="activity" title="${esc(responseTitle)}">${mine.length?mine.length+' awaiting you':needsResponse.length?needsResponse.length+' open responses':'No responses pending'}</a>
 </div></nav>`;
}
function bridgeUpdatesControl(){
 const snapshot=bridgeProjectUpdate();
 const feed=typeof projectUpdateFeed==='function'?projectUpdateFeed():'<details class="project-update-feed"><summary>Updates</summary><div class="project-update-items"></div></details>';
 // One existing Updates disclosure retains event/read actions as well as the
 // publication and response destinations. Routine activity is not a warning.
 return feed.replace('<div class="project-update-items">','<div class="project-update-items">'+snapshot);
}
function bridgeRequirementShellRecords(){return typeof records==='function'?records('requirement-drawer'):[];}
function bridgeRequirementCandidates(){return typeof pendingRequirementRows==='function'?pendingRequirementRows():typeof records==='function'?records('requirement').filter(r=>r.body.status!=='approved'):[];}
function bridgeProjectRail(){
 const published=bridgePublishedWork();
 const latest=published[0];
 const publishedPreview=latest?`<div class="accountability-rail-preview">
  <a href="#main" class="item-title-link" data-action="read-contribution" data-id="${esc(latest.ref.id)}">${esc(latest.body.title||'Domain contribution')}</a>
  <p class="accountability-rail-meta">${esc(latest.body.domain||'Domain')}${latest.body.owner?' · '+esc(bridgePerson(latest.body.owner)):''} · v${latest.ref.revision}</p></div>`:'<p class="accountability-rail-empty">Nothing published yet.</p>';
 const items=[...bridgeTimelineStatus({includeAccepted:true}),...bridgeSponsorGates()],owners=new Map();
 for(const item of items){
  const assigned=[...new Set((Array.isArray(item.owner)?item.owner:[item.owner]).filter(Boolean))];
  for(const owner of assigned.length?assigned:[''])owners.set(owner,(owners.get(owner)||0)+1);
 }
 const people=[...owners].sort(([a,countA],[b,countB])=>!a?-1:!b?1:countB-countA||bridgePerson(a).localeCompare(bridgePerson(b)));
 const activityPreview=items.length?`<ul class="accountability-rail-owners">${people.slice(0,4).map(([owner,count])=>`<li><span>${owner?esc(bridgePerson(owner)):'Next responder unassigned'}</span><span>${count} item${count===1?'':'s'}</span></li>`).join('')}</ul>${people.length>4?`<p class="accountability-rail-meta">And ${people.length-4} more ${people.length===5?'person':'people'}</p>`:''}`:'<p class="accountability-rail-empty">No open assignments or requests.</p>';
 const candidates=bridgeRequirementCandidates(),shells=bridgeRequirementShellRecords(),cases=state.cases||[],open=cases.filter(c=>['pending-review','deferred'].includes(c.body.status)),review=open[0]||cases[0];
 const target=review&&(typeof get==='function'?get(review.body.target?.id):null)||review?.target_record;
 const activity=review&&target&&typeof requirementReviewActivity==='function'?requirementReviewActivity(target):null;
 const sameActivity=activity&&review&&activity.case?.ref?.id===review.ref.id;
 const stale=review&&!['approved','rejected'].includes(review.body.status)&&(review.stale?.length||review.rights?.changed);
 const reviewLabel=stale?'Review needs refresh':sameActivity?activity.label:({'pending-review':'Pending review',deferred:'Awaiting response',approved:'Approved',rejected:'Rejected'})[review?.body.status]||'Recorded';
 const reviewTone=stale?'advisory':sameActivity?activity.tone:'reference';
 const current=review?`<section class="requirement-rail-group requirement-rail-current"><h3>${open.length?'Current review':'Latest review'}</h3><div class="requirement-rail-review-item"><a href="#main" class="item-title-link" data-action="case" data-id="${esc(review.ref.id)}">${esc(review.target_record?.body.title||target?.body.title||'Requirement review')}</a>${signalConditionChip(reviewLabel,reviewTone)}</div></section>`:candidates.length||shells.length?'':'<p class="accountability-rail-empty">No recorded reviews.</p>';
 const browse=shells.length||candidates.length?`<section class="requirement-rail-group requirement-rail-browse"><h3>Browse requirements</h3><ul>${shells.length?`<li><a href="#main" class="item-title-link" data-action="bridge-requirement-view" data-id="shells">Requirement areas</a><span>${shells.length}</span></li>`:''}${candidates.length?`<li><a href="#main" class="item-title-link" data-action="bridge-requirement-view" data-id="candidates">Requirements in development</a><span>${candidates.length}</span></li>`:''}</ul></section>`:'';
 const reviewPreview=current+browse;
 return `<aside class="accountability-project-rail" aria-label="Project work and reviews">
  ${bridgeRailSection('work',published.length+' published item'+(published.length===1?'':'s'),publishedPreview)}
  ${bridgeRailSection('activity',items.length+' open work item'+(items.length===1?'':'s'),activityPreview)}
  ${bridgeRailSection('reviews',open.length+' open review'+(open.length===1?'':'s'),reviewPreview)}
 </aside>`;
}
function bridgeBoardControl(){const info=bridgeInfo(),action=bridgeSection==='assignments'?'pflow-brief-board':'bridge-board';return `<label class="bridge-board-control"><span class="workspace-action-label">Board</span><select id="bridge-board-filter" data-bridge-select="${action}" aria-label="${bridgeSection==='assignments'?'Brief board':'Issue board'}">${Object.entries(info.boards).map(([key,title])=>`<option value="${esc(key)}" ${bridgeBoard===key?'selected':''}>${esc(title)}${bridgeSection==='boards'?' · '+info.issues.filter(i=>i.body.boards.includes(key)&&i.body.status!=='resolved').length+' open':''}</option>`).join('')}</select></label>`;}
function bridgeToolbar(raised){
 if(['overview','assignments','timeline','work','reviews','activity'].includes(bridgeSection))return `<div class="bridge-controls accountability-controls"><div class="accountability-toolbar-primary">${bridgeTabs()}${bridgeSection==='assignments'?'':raised}</div>
  <div class="accountability-controls-actions">${bridgeUpdatesControl()}</div>
 </div>`;
 const actions=raised;return `<section class="bridge-controls" aria-label="Decisions & Issues controls">${bridgeTabs()}<div class="workspace-action-bar bridge-action-bar">${['boards','assignments'].includes(bridgeSection)?bridgeBoardControl():''}${actions?`<div class="workspace-action-group" role="group" aria-label="Actions"><span class="workspace-action-label">Actions</span><div class="workspace-action-buttons">${actions}</div></div>`:''}<div class="workspace-action-group workspace-activity">${bridgeUpdatesControl()}</div></div></section>`;}
function mountAccountabilityHeader(){
 const intro=$('.accountability-page-intro');if(!intro)return;
 const main=$('#main'),identitySlot=intro.querySelector('[data-accountability-identity]'),statusSlot=intro.querySelector('[data-accountability-status]');
 if(!main||!identitySlot||!statusSlot)return;
 const identity=main.querySelector(':scope > .project-page-identity'),status=main.querySelector(':scope > .project-status-line');
 if(identity)identitySlot.append(identity);
 if(status)statusSlot.append(status);
}
function bridgeScreen(){
 if(bridgeSection==='developer-briefs')bridgeSection='assignments';
 const info=bridgeInfo();if(selected&&bridgeIssue())return bridgeDetail(bridgeIssue());
 const raised=info.actors.includes(state.actor)?button('Raise an issue','bridge-new','','quiet'):'';
 let content='';
 if(bridgeSection==='overview')content=accountabilityOverview()+(typeof knowledgeSystemChecks==='function'?knowledgeSystemChecks():'');
 else if(bridgeSection==='assignments')content=typeof domainBriefDirectory==='function'?domainBriefDirectory():'';
 else if(bridgeSection==='work')content=sharedDomainReleases();
 else if(bridgeSection==='reviews')content=bridgeReviewQueue();
 else if(bridgeSection==='timeline')content=bridgeTimelineScreen();
 else if(bridgeSection==='activity')content=bridgeActivityScreen();
 else{
  if(!info.boards[bridgeBoard])bridgeBoard='research-design';
  const issues=info.issues.filter(i=>i.body.boards.includes(bridgeBoard));
  content=`<p class="caption bridge-board-caption">${esc(info.boards[bridgeBoard])} · Questions, evidence needs and decisions.</p>`+
  (issues.length?`<div class="bridge-columns">${[['To investigate',['open','investigating']],['Waiting or decision',['awaiting-decision','deferred']],['Resolved',['resolved']]].map(([title,statuses])=>{const cards=issues.filter(i=>statuses.includes(i.body.status));return `<section class="bridge-lane"><h2>${esc(title)} <span class="caption">${cards.length}</span></h2><div class="list">${cards.map(bridgeCard).join('')||'<p class="caption">No issues.</p>'}</div></section>`;}).join('')}</div>`:`<section class="empty section"><h2>No issues on this board</h2><p>Raise a question from published context and assign follow-up.</p></section>`);
 }
 return `<div class="accountability-page-intro project-page-header has-status"><div class="accountability-title-area project-title-area"><div data-accountability-identity></div>`+head('Decisions & Issues','What the teams owe each other, what is disputed, and who decides.')+`</div><div class="accountability-status-area project-status-area"><div data-accountability-status></div></div></div>`+bridgeToolbar(raised)+(['overview','assignments','activity'].includes(bridgeSection)?'':intakeReviewNotice())+`<div class="accountability-layout${bridgeSection==='overview'?' is-overview':''}"><div class="accountability-main"><div class="bridge-content">${content}</div></div>${bridgeSection==='overview'?'':bridgeProjectRail()}</div>`;
}
function bridgeItemIndication(item,{showPersonal=true,showOpen=true}={}){
 const owners=(Array.isArray(item.owner)?item.owner:[item.owner]).filter(Boolean),names=owners.map(bridgePerson).join(', '),mine=item.attention!==false&&owners.includes(state.actor),
  caution=Boolean(item.alert)||['Decision rights changed','Escalation response needed','Brief context changed','Review blocked','Direction context changed'].includes(item.status),title=signalItemTitle(item.title),simulation=title!==String(item.title||'');
 const chips=(mine&&showPersonal?signalConditionChip('For you','attention','accountability-for-you'):'')+(showOpen||item.status!=='Open'?signalConditionChip(item.status||'Recorded',caution&&!item.alert?'advisory':'reference',caution&&!item.alert?'accountability-item-alert':''):'')+(item.alert?signalConditionChip(item.alert,'advisory','accountability-item-alert'):'')+(simulation?signalConditionChip('Simulation'):'');
 return {owners,names,mine,caution,title,chips};
}
function bridgeCard(i){
 const b=i.body,closed=b.status==='resolved',item=(!closed&&bridgeTimelineStatus({includeAccepted:true}).find(item=>item.kind==='issue'&&item.id===i.ref.id))||{title:b.title,status:bridgeStatuses[b.status]||b.status,attention:!closed,owner:closed?null:b.next_owner,next:b.next_question||b.question,requestLabel:'Next action',alert:!closed&&i.changed?.length?'Context changed · review needed':''},indication=bridgeItemIndication(item);
 return `<article class="card bridge-card"><h3 class="acx-item-title"><a href="#main" class="item-title-link" data-action="bridge-open" data-id="${esc(i.ref.id)}">${esc(indication.title)}</a></h3><div class="card-head bridge-item-indicators">${signalConditionChip(bridgeInfo().kinds[b.kind]||b.kind||'Issue')}${indication.chips}</div><p class="pre bridge-item-task"><span class="bridge-item-task-label">${esc(closed?'Question':item.requestLabel||'Next action')}: </span>${esc(closed?b.question:item.next||b.question)}</p><p class="caption">${recordedDate('Submitted',b.created_at)}${closed?' · '+recordedDate('Resolved',b.resolution?.at):''}</p><p class="caption">${closed?'Decided by '+esc(bridgePerson(b.resolution?.actor)):esc(item.ownerLabel||'Next response')+' · '+esc(indication.names||'Owner unassigned')}</p><p class="caption">${b.packet_refs.length} packet${b.packet_refs.length===1?'':'s'} · ${b.requirement_refs.length} affected requirement${b.requirement_refs.length===1?'':'s'}</p></article>`;
}
function bridgeCandidateEvidenceReports(candidate){
 const shared=typeof records==='function'?bridgePublishedWork():[],exact=new Map();
 for(const report of shared){
  if(report.kind!=='contribution'||(typeof report.scope==='string'&&!report.scope.startsWith('project:')))continue;
  const links=report.body.requirement_refs;
  if(Array.isArray(links)&&links.some(link=>link&&link.id===candidate.ref.id&&typeof link.revision==='number'&&link.revision===candidate.ref.revision))exact.set(report.ref.id+'|'+report.ref.revision,report);
 }
 return [...exact.values()];
}
function bridgeRequirementCandidate(r){
 const b=r.body,active=(state.cases||[]).find(c=>c.body.target.id===r.ref.id&&!['approved','rejected'].includes(c.body.status)),mayPrepare=typeof canPrepareRequirement==='function'?canPrepareRequirement():state.actor==='alex',reports=bridgeCandidateEvidenceReports(r);
 const evidence=reports.length?`${reports.length} linked report${reports.length===1?'':'s'}`:'Not linked here';
 return `<details class="pending-requirement" id="candidate-${esc(r.ref.id)}"><summary><span class="workbench-object-heading"><span class="workbench-object-type">Requirement</span><span>${esc(b.title||'Untitled requirement')}</span></span>${typeof requirementAssessmentSummary==='function'?requirementAssessmentSummary(r):signalConditionChip('Candidate wording · Awaiting ratification')+signalConditionChip('Evidence: '+evidence,'reference','pending-requirement-evidence')}</summary><div class="details-body">${val('Requirement',b.text)}${val('Acceptance criteria',b.acceptance_criteria)}${val('Rationale',b.rationale)}${val('Conditions',b.conditions)}${reports.length?`<section class="pending-requirement-reports"><h3>Linked published reports</h3><ul>${reports.map(report=>`<li><a href="#main" class="item-title-link" data-action="read-contribution" data-id="${esc(report.ref.id)}">${esc(report.body.title||'Domain report')}</a></li>`).join('')}</ul><p class="caption">Recorded links do not establish validation.</p></section>`:'<p class="caption">No published report is linked to this exact version here.</p>'}<div class="actions">${active?button('Open review','case',active.ref.id,'small'):mayPrepare?button('Prepare proposal','proposal',r.ref.id,'small'):''}</div><details class="requirement-source-details"><summary>Source details</summary><div class="details-body"><p class="caption">Requirement version · ${technicalRef(r.ref)} · ${b.status==='approved'?'Ratified':'Proposed'}</p>${reports.length?`<ul class="caption">${reports.map(report=>`<li>${esc(report.body.title||'Domain report')} · ${technicalRef(report.ref)}</li>`).join('')}</ul>`:''}</div></details></div></details>`;
}
function bridgeRequirementShellQueue(candidates,shells=bridgeRequirementShellRecords()){
 const rendered=new Set();
 const areaIds=(row,seen=new Set())=>{if(seen.has(row.ref.id))return seen;seen.add(row.ref.id);for(const child of shells.filter(r=>r.body.parent_id===row.ref.id))areaIds(child,seen);return seen;};
 const render=row=>{
  if(rendered.has(row.ref.id))return '';rendered.add(row.ref.id);
  const b=row.body,children=shells.filter(r=>r.body.parent_id===row.ref.id),ids=areaIds(row),count=candidates.filter(r=>ids.has(r.body.drawer_id)).length,linked=candidates.filter(r=>r.body.drawer_id===row.ref.id);
  return `<details class="requirement-shell" id="shell-${esc(row.ref.id)}"><summary><span>${esc(b.label||'Unnamed requirement area')}</span>${signalConditionChip((b.status==='retired'?'Retired area · ':'')+(count?count+' requirement'+(count===1?'':'s'):'No requirements defined'))}</summary><div class="details-body">${val('Scope / question',b.question)}${val('Review criteria',b.criteria)}${b.evidence?val('Evidence to collect',b.evidence):''}${linked.length?`<div class="requirement-shell-candidates"><h3>Requirements</h3><ul>${linked.map(r=>`<li><a href="#main" class="item-title-link" data-action="requirement" data-id="${esc(r.ref.id)}">${esc(r.body.title||'Untitled requirement')}</a></li>`).join('')}</ul></div>`:''}${children.map(render).join('')}<details class="requirement-source-details"><summary>Source details</summary><div class="details-body"><p class="caption">Area version · ${technicalRef(row.ref)}</p></div></details></div></details>`;
 };
 const roots=shells.filter(r=>!r.body.parent_id||!shells.some(p=>p.ref.id===r.body.parent_id)),content=roots.map(render).join('')+shells.filter(r=>!rendered.has(r.ref.id)).map(render).join('');
 return `<section class="section requirement-shells"><h2>Requirement areas</h2><p class="caption">Areas organize the questions and criteria for related requirements. They do not establish evidence confidence.</p>${content?`<div class="list">${content}</div>`:'<div class="empty">No published areas.</div>'}</section>`;
}
function bridgeRequirementAreaIds(id,shells=bridgeRequirementShellRecords(),seen=new Set()){
 if(!id||seen.has(id))return seen;seen.add(id);
 for(const child of shells.filter(r=>r.body.parent_id===id))bridgeRequirementAreaIds(child.ref.id,shells,seen);
 return seen;
}
function bridgeRequirementCategories(shells=bridgeRequirementShellRecords()){return shells.filter(r=>!r.body.parent_id||!shells.some(p=>p.ref.id===r.body.parent_id));}
function bridgeRequirementFilter(kind,value){
 if(kind==='bucket'&&['candidates','shells','reviews'].includes(value))bridgeRequirementBucket=value;
 else if(kind==='category')bridgeRequirementCategory=bridgeRequirementCategories().some(r=>r.ref.id===value)?value:'';
 bridgeSection='reviews';selected=null;view='review';render();
}
function bridgeRequirementReviewCases(rows){return `<section class="section"><h2>Requirement reviews</h2><p class="caption">Governing reviews and decisions. Issues can link to a review.</p>${rows.length?`<div class="list">${rows.map(c=>`<article class="card"><div class="card-head"><h3 class="acx-item-title"><a href="#main" class="item-title-link" data-action="case" data-id="${esc(c.ref.id)}">${esc(c.body.proposal.text.slice(0,110))}${c.body.proposal.text.length>110?'…':''}</a></h3>${statusTag(c.body.status)}</div><p class="caption">${ref(c.body.target)}</p>${sourceDetails([c.ref,c.body.target])}<p class="caption">${recordedDate('Submitted',c.body.created_at)}</p><details><summary>Proposed wording</summary>${para(c.body.proposal.text)}</details></article>`).join('')}</div>`:'<div class="empty">No requirement reviews yet. Raise a requirement issue or prepare a proposal from a requirement dossier.</div>'}</section>`;}
function bridgeReviewQueue(){
 const allCandidates=bridgeRequirementCandidates(),allShells=bridgeRequirementShellRecords(),categories=bridgeRequirementCategories(allShells);
 if(!['candidates','shells','reviews'].includes(bridgeRequirementBucket))bridgeRequirementBucket='candidates';
 if(bridgeRequirementCategory&&!categories.some(r=>r.ref.id===bridgeRequirementCategory))bridgeRequirementCategory='';
 const ids=bridgeRequirementCategory?bridgeRequirementAreaIds(bridgeRequirementCategory,allShells):null,
  candidates=allCandidates.filter(r=>!ids||ids.has(r.body.drawer_id)),shells=allShells.filter(r=>!ids||ids.has(r.ref.id)),
  requirements=typeof records==='function'?records('requirement'):[],cases=(state.cases||[]).filter(c=>{const r=requirements.find(r=>r.ref.id===c.body.target.id)||c.target_record;return !ids||ids.has(r?.body.drawer_id);}),
  counts={candidates:candidates.length,shells:shells.length,reviews:cases.length};
 const filters=`<div class="requirement-review-filters" role="group" aria-label="Requirement review filters"><label class="requirement-review-filter" for="bridge-requirement-bucket"><span>Type</span><div class="ui-selector-wrap"><select id="bridge-requirement-bucket" class="ui-selector">${[['candidates','Requirements in development'],['shells','Requirement areas'],['reviews','Decision reviews']].map(([key,title])=>`<option value="${key}" ${bridgeRequirementBucket===key?'selected':''}>${title} (${counts[key]})</option>`).join('')}</select>${typeof selectorChevron==='function'?selectorChevron():''}</div></label><label class="requirement-review-filter" for="bridge-requirement-category"><span>Category</span><div class="ui-selector-wrap"><select id="bridge-requirement-category" class="ui-selector"><option value="">All categories</option>${categories.map(r=>`<option value="${esc(r.ref.id)}" ${bridgeRequirementCategory===r.ref.id?'selected':''}>${esc(r.body.label||'Requirement area')}</option>`).join('')}</select>${typeof selectorChevron==='function'?selectorChevron():''}</div></label></div>`;
 const content=bridgeRequirementBucket==='shells'?bridgeRequirementShellQueue(candidates,shells):bridgeRequirementBucket==='reviews'?bridgeRequirementReviewCases(cases):`<section class="section requirement-candidates"><h2>Requirements in development</h2><p class="caption">Work on unresolved questions and wording here. The shared requirement map keeps the same items and their assessment history.</p>${candidates.length?`<div class="list">${candidates.map(bridgeRequirementCandidate).join('')}</div>`:'<div class="empty">No requirements in development.</div>'}</section>`;
 return `<section class="card requirement-review-workspace"><h2>Requirement development</h2>${filters}${content}</section>`;
}
if(typeof document!=='undefined')document.addEventListener('change',event=>{
 const kind=event.target.id==='bridge-requirement-bucket'?'bucket':event.target.id==='bridge-requirement-category'?'category':null;if(!kind)return;
 if(typeof busy!=='undefined'&&busy){event.target.value=kind==='bucket'?bridgeRequirementBucket:bridgeRequirementCategory;return;}
 bridgeRequirementFilter(kind,event.target.value);document.getElementById('bridge-requirement-'+kind)?.focus();
});

function bridgeReceiptDelivery(i){
 const d=i.decision_receipt?.delivery;if(!d)return '';
 if(!d.applicable)return `<section class="receipt-delivery"><h3>Jira / Azure DevOps</h3>${para(d.message)}</section>`;
 const states={'not-staged':'No shared transaction recorded',staged:'Staged · not sent',simulated:'Simulated · no external update'};
 const transaction=t=>`<article class="rule"><p class="caption">${esc(t.mode==='demo'?'Demo preview':'Payload preview')} · ${esc(t.destination||'Destination not set')} · ${esc(t.status==='simulated'?'Simulation recorded':'Staged · not sent')} · ${technicalRef(t.ref)}</p><a href="#main" class="item-title-link" data-action="${t.kind==='demo-delivery-preview'?'demo-delivery-preview':'bridge-receipt-stage'}" data-id="${esc(t.ref.id)}">View staged transaction</a>${t.unverified_external_references?'<p class="caption">External references are unverified; they do not confirm a send.</p>':''}</article>`;
 return `<section class="receipt-delivery"><h3>Jira / Azure DevOps</h3>${d.targets.map(t=>`<div class="receipt-delivery-target"><p><strong>${t.target==='jira'?'Jira':'Azure DevOps'}</strong> · ${esc(states[t.status]||'Status unavailable')}</p>${t.stories.length?`<p><a href="#main" class="item-title-link" data-action="demo-delivery-item" data-id="${esc(t.stories[0].receipt.id)}">${esc(t.stories[0].key)} · local simulated story</a></p>`:''}${t.transactions.length||t.stories.length>1?`<details><summary>Saved transactions (${t.transactions.length})</summary><div class="details-body">${t.transactions.map(transaction).join('')}${t.stories.length>1?`<h4>Earlier simulated results</h4>${t.stories.slice(1).map(s=>`<p><a href="#main" class="item-title-link" data-action="demo-delivery-item" data-id="${esc(s.receipt.id)}">${esc(s.key)} · local simulated story</a><span class="caption"> · ${technicalRef(s.receipt)}</span></p>`).join('')}`:''}</div></details>`:''}</div>`).join('')}<p><strong>Actually sent</strong> · Not confirmed</p><p class="caption">${esc(d.message)} Status is for this approved version’s shared records.</p>${d.warning?`<p class="caption" role="status">${esc(d.warning)}</p>`:''}</section>`;
}
function bridgeReceiptStage(id){
 const i=bridgeIssue(),d=i?.decision_receipt?.delivery,stage=d?.targets.flatMap(t=>t.transactions).find(t=>t.kind==='delivery-draft'&&t.ref.id===id);
 if(!stage)throw Error('This shared staged transaction is unavailable. Reopen the Decision receipt.');
 modal('Staged transaction · '+(stage.target==='jira'?'Jira':'Azure DevOps'),`<p><strong>Staged · not sent</strong></p>${val('Destination',stage.destination||'Not set')}<p class="caption">${ref(stage.source)}</p>${sourceDetails([stage.ref,stage.source])}${stage.items.map(item=>`<section class="rule"><h3>${esc(item.title)}</h3>${val('Requirement',item.requirement)}${val('Acceptance criteria',item.acceptance_criteria||'Not recorded')}<details><summary>Exact staged payload</summary><pre class="settings-instructions">${esc(JSON.stringify({method:item.method,endpoint:item.endpoint,payload:item.payload,idempotency_key:item.idempotency_key},null,2))}</pre></details></section>`).join('')}<p class="caption">This saved preview is not proof that an external story exists or was updated. Private previews and other requirement versions are excluded.</p>`,null,null,{className:'settings-dialog'});
}
function bridgeReceiptTime(at){
 if(!at||Number.isNaN(new Date(at).getTime()))return recordedDate('Recorded',null);
 const text=new Date(at).toLocaleString(undefined,{year:'numeric',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
 return `<span>Recorded <time datetime="${esc(at)}">${esc(text)}</time></span>`;
}
function bridgeReceiptName(actor,r){return r.authority?.policy?.people?.[actor]?.name||(r.decider?.id===actor?r.decider.name:null)||r.reviews?.find(v=>v.reviewer?.id===actor)?.reviewer.name||actor||'Not recorded';}
function bridgeReceiptEvidence(item){
 if(item.unavailable)return `<p class="caption">${technicalRef(item.ref)} · This exact record is unavailable in shared context.</p>`;
 const f=item.fields||{},kindNames={'project-context':'Project context','intent':'Business direction','policy':'Project constraints','success-measure':'Performance indicator','human-review':'Assessment','requirement-drawer':'Requirement area','decision-case':'Proposal under review','intake-case':'Business direction review'};return `<article class="rule"><strong>${esc(f.title||kindNames[item.kind]||item.kind.replaceAll('-',' '))}</strong><p class="caption">${technicalRef(item.ref)}${f.at?' · '+recordedDate('Recorded',f.at):''}</p>${f.disposition?val('Assessment',f.disposition.replaceAll('-',' ')):''}${f.text&&f.text!==f.observation?para(f.text):''}${f.observation?val('Observation',f.observation):''}${f.interpretation?val('Interpretation',f.interpretation):''}${f.limitation?val('Limits',f.limitation):''}${f.rationale?val('Rationale',f.rationale):''}${f.source?val('Source reference',f.source):''}</article>`;
}
function bridgeDecisionReceipt(i){
 const r=i.decision_receipt;
 if(!r?.available)return `<section class="card section decision-receipt" aria-label="Decision receipt"><h2>Decision receipt</h2><p role="status">${esc(r?.message||'The saved decision record is unavailable. No approved wording can be verified.')}</p>${r?.decision?`<p class="caption">${ref(r.decision)}</p>`:''}</section>`;
 const names={approve:'Requirement change approved',reject:'Proposal rejected','no-governing-change':'Closed without a governing change','publish-for-investigation':'Business direction published for investigation',declined:'Proposed change declined',incorporated:'Business direction updated'},a=r.authority,p=a?.policy,approved=r.approved;
 const wording=approved?`${approved.field?val(typeof intakeNames==='object'?intakeNames[approved.field]||approved.field:approved.field,approved.text):para(approved.text)}<p class="caption">${approved.kind==='requirement'?'Requirement':'Business direction'} · ${ref(approved.ref)}</p>${(()=>{if(approved.kind!=='requirement'||!approved.ref||approved.ref.revision<2)return '';const same=x=>x.ref.id===approved.ref.id&&x.ref.revision===approved.ref.revision-1,prev=(state.records||[]).find(same)||(state.packets||[]).flatMap(p=>p.records||[]).find(same);const text=prev?.body?.text||prev?.body?.statement||prev?.body?.requirement||'';return `<p class="receipt-change"><span class="evidence-change">Changed</span> ${esc(prev?.body?.title||'Requirement')} <span class="evidence-version">v${approved.ref.revision-1} → v${approved.ref.revision}</span></p>${text?`<details class="receipt-replaced"><summary>Version ${approved.ref.revision-1} (replaced)</summary><div class="details-body">${para(text)}</div></details>`:''}`;})()}${approved.acceptance_criteria||approved.conditions?`<details><summary>Acceptance criteria and conditions</summary><div class="details-body">${approved.acceptance_criteria?val('Acceptance criteria',approved.acceptance_criteria):''}${approved.conditions?val('Conditions',approved.conditions):''}</div></details>`:''}`:para(r.wording_message);
 return `<section class="card section decision-receipt" aria-label="Decision receipt"><h2>Decision receipt</h2><p class="receipt-outcome"><strong>${esc(names[r.outcome]||r.outcome?.replaceAll('-',' ')||'Outcome not recorded')}</strong></p><p class="caption">${r.response_only?'Responded':'Decided'} by ${esc(r.decider.name)} · ${bridgeReceiptTime(r.at)} · ${ref(r.decision)}</p>${val('Why',r.rationale||'Rationale not recorded')}<section class="receipt-wording"><h3>${approved?'Approved wording':'Effect on requirements and business direction'}</h3>${wording}</section>${r.ratified_interpretation?`<section class="receipt-wording"><h3>Ratified interpretation</h3>${para(r.ratified_interpretation.text)}<p class="caption">${ref(r.ratified_interpretation.ref)} · Governing requirements unchanged</p></section>`:''}${bridgeReceiptDelivery(i)}<details class="receipt-evidence"><summary>Evidence and reviews (${r.evidence.length+r.reviews.length})</summary><div class="details-body">${r.evidence.map(bridgeReceiptEvidence).join('')}${r.reviews.map(v=>`<section class="rule"><h3>${esc(v.reviewer.name)}’s review</h3>${bridgeReceiptEvidence(v)}</section>`).join('')}${!r.evidence.length&&!r.reviews.length?'<p class="caption">No additional evidence or assessments were recorded.</p>':''}</div></details><details class="receipt-authority"><summary>Authority at the time of decision</summary><div class="details-body">${a?`${val('Acted as',a.authorized_as==='delegate'?'Activated delegate':'Named decider')}${val('Primary decider',bridgeReceiptName(p?.decider,r))}<p class="caption">${p?.policy?'Policy '+technicalRef(p.policy):'Existing workflow roles · No named project policy was configured.'}</p>${val('Required reviewers',(p?.reviewers||[]).map(id=>bridgeReceiptName(id,r)).join(', ')||'None recorded')}${a.principal?val('Recorded account',a.principal):'<p class="caption">Account identity not recorded; local workflow identity retained.</p>'}${a.delegation?`${val('Delegated by',bridgeReceiptName(a.delegation.by,r))}${val('Delegation reason',a.delegation.reason)}<p class="caption">${recordedDate('Delegated',a.delegation.at)}</p>`:''}${a.escalation?`${val('Escalation contact',bridgeReceiptName(a.escalation.owner,r))}${val('Escalation reason',a.escalation.reason)}${a.escalation.response?val('Escalation response',a.escalation.response):''}<p class="caption">${recordedDate('Escalated',a.escalation.at)}${a.escalation.responded_at?' · '+recordedDate('Responded',a.escalation.responded_at):''}</p>`:''}`:'<p>No decision-authority snapshot was recorded by this earlier workflow. Current policy has not been substituted.</p>'}${para(r.boundary)}</div></details>${sourceDetails([r.decision,approved?.ref,r.ratified_interpretation?.ref].filter(Boolean))}</section>`;
}
function bridgeDetail(i){
 const b=i.body,info=bridgeInfo(),closed=b.status==='resolved',request=b.information_request,caseRecord=b.linked?.kind==='requirement'?findCase(b.linked.ref.id):null;
 return `<div class="workflow-backlink">${button(({'overview':'← Overview','timeline':'← Project timeline','activity':'← Teams & Agents'})[bridgeSection]||'← Issue boards','bridge-back','','quiet')}</div>`+head(b.title,[info.kinds[b.kind]||b.kind,b.created_by?'Raised by '+bridgePerson(b.created_by):'',b.boards.map(k=>info.boards[k]).join(' / ')].filter(Boolean).join(' · '),tag(bridgeStatuses[b.status],closed?'green':'blue'))+`<p class="caption">${recordedDate('Submitted',b.created_at)}</p>`+
 (i.changed.length&&!closed?'<div class="banner signal-notice signal-advisory"><strong>The issue context changed.</strong><p>Review its packet versions before authorizing a change. Earlier context and responses remain available.</p>'+ (bridgeCanManage(i)?button('Review context','bridge-refresh',i.ref.id):'')+'</div>':'')+
 `<div class="grid cols"><div>${closed?bridgeDecisionReceipt(i):''}${i.integrity?'':`<section class="card accent">${tag(info.kinds[b.kind]||b.kind)}<h2 class="section">Question to resolve</h2>${para(b.question)}${val('Why this matters',b.consequence)}${request?.status==='open'?`<div class="banner blue"><strong>Information needed from ${esc(bridgePerson(request.owner))}</strong>${para(request.question)}${state.actor===request.owner?button('Answer this request','bridge-answer',i.ref.id):''}</div>`:''}${b.next_question&&!closed?val('Next response · '+bridgePerson(b.next_owner),b.next_question):''}</section>`}
 ${bridgeIntegrityPanel(i)}${caseRecord&&!closed?bridgeRequirementPanel(i,caseRecord):''}
 <section class="card section"><h2>Context for this issue</h2>${(i.basis_records||[]).filter(r=>r.kind==='review-concern').map(r=>`<article class="rule"><h3>Carried review concern</h3><p class="caption">${esc(r.body.boundary)}</p>${r.body.historical_context?'<p class="caption">Original review used historical context.</p>':''}${r.body.source_review?ref(r.body.source_review):'<p class="caption">Human-raised concern</p>'}${r.body.review_excerpt?Object.entries(r.body.review_excerpt).filter(([,v])=>v).map(([k,v])=>val(k.replaceAll('_',' '),v)).join(''):''}</article>`).join('')}${typeof needContextLink==='function'?(b.basis||[]).filter(raw=>get(raw.id)?.kind==='need-context').map(raw=>needContextLink(raw)).join(''):''}<div class="list">${b.packet_refs.map(raw=>{const p=(state.packets||[]).find(p=>packetKey(p)===packetKey(raw));return `<div class="rule"><a href="#main" class="item-title-link" data-action="packet" data-id="${esc(packetKey(raw))}">${esc(p?packetTitle(p):'Published context')}</a><p class="caption">Version ${esc(raw.revision)} · Exact shared version</p>${sourceDetails(raw)}</div>`;}).join('')}</div>${b.requirement_refs.length?`<details><summary>Affected requirements (${b.requirement_refs.length})</summary><div class="details-body">${b.requirement_refs.map(r=>`<div class="rule">${ref(r)} ${esc(get(r.id)?.body.title||'Requirement')} ${button('Open requirement','requirement',r.id,'small')}</div>`).join('')}</div></details>`:''}<details><summary>Recorded and observed versions</summary><pre class="settings-instructions">${esc(JSON.stringify({packet_refs:b.packet_refs,basis:b.basis,observed_versions:b.observed_versions,observed_packets:b.observed_packets},null,2))}</pre><p class="caption">Historical selections remain exact. Observed versions record what was available when the context was reviewed; formal approval checks still apply.</p></details></section>
 <section class="card section"><div class="card-head"><h2>Responses and history</h2>${!closed&&info.actors.includes(state.actor)?button('Add a response','bridge-respond',i.ref.id):''}</div>${i.events.slice(-5).reverse().map(bridgeEvent).join('')}${i.events.length>5?`<details><summary>Earlier responses (${i.events.length-5})</summary>${i.events.slice(0,-5).reverse().map(bridgeEvent).join('')}</details>`:''}</section></div>
 <aside class="card readiness bridge-decision-rail"><h2>${closed?'Related actions':'Decision and next action'}</h2>${!closed?val('Issue owner',bridgePerson(b.owner))+val('Decision authority',bridgePerson(b.decision_owner)+' · '+(i.integrity?'Interpretation for shared use':bridgeRoutes[b.route]))+(typeof decisionRightsPanel==='function'?decisionRightsPanel(caseRecord||i,caseRecord?.rights||i.rights):''):''}<div class="bridge-decision-actions">${bridgeDecisionPanel(i,caseRecord)}</div>${bridgeDecisionReviewEntry(i,caseRecord)}${!i.integrity&&typeof demoDeliveryPanel==='function'?demoDeliveryPanel(i):''}<hr class="subtle-line"><p class="caption">Packet publication and issue discussion do not approve a requirement, change Business Intent or authorize delivery.</p></aside></div>`;
}
function bridgeEvent(e){return `<article class="rule"><strong>${esc(bridgePerson(e.body.actor))}</strong><p class="caption">${esc(e.body.action.replaceAll('-',' '))} · ${esc(date(e.body.at))}</p>${para(e.body.note)}${e.body.linked?`<p class="caption">${ref(e.body.linked)}</p>${sourceDetails(e.body.linked)}`:''}</article>`;}
function bridgeRequirementPanel(i,c){const b=c.body;return `<section class="card section"><div class="card-head"><h2>Linked requirement review</h2>${statusTag(b.status)}</div><div class="grid two comparison"><div>${val('Requirement at review',c.target_record.body.text)}${ref(c.target_record.ref)}${sourceDetails([c.ref,c.target_record.ref])}</div><div>${val('Proposed wording',b.proposal.text)}${val('Acceptance criteria',b.proposal.acceptance_criteria)}${val('Conditions',b.proposal.conditions)}</div></div><details><summary>Domain responses and exact review basis</summary><div class="details-body">${Object.keys(b.required_reviews||{}).map(a=>`<div class="rule">${val(bridgePerson(a),c.reviews[a]?.body.rationale||'Response needed')}${c.reviews[a]?`<p class="caption">${recordedDate('Submitted',c.reviews[a].body.at)}</p>`:''}</div>`).join('')}${b.basis.map(technicalRef).join(' · ')}</div></details><footer class="workflow-card-actions">${button('Open full review','case',c.ref.id,'small')}</footer></section>`;}
function bridgeOtherHolds(c){return bridgeInfo().issues.filter(i=>i.body.status!=='resolved'&&['requirement','intent'].includes(i.body.route)&&(i.body.requirement_refs.some(r=>r.id===c.body.target.id)||(i.body.route==='intent'&&!i.body.requirement_refs.length))&&!(i.body.linked?.kind==='requirement'&&i.body.linked.ref.id===c.ref.id));}
function bridgeDecisionPanel(i,c){
 const b=i.body,authority=c?(c.rights?.can_decide??state.actor===b.decision_owner):(i.rights?.can_decide??state.actor===b.decision_owner),request=b.information_request;
 if(i.integrity)return bridgeIntegrityActions(i);
 if(b.status==='resolved')return `${c?button('Open full review','case',c.ref.id):''}${b.resolution?.packet?button('Inspect resulting packet','packet',packetKey(b.resolution.packet)):''}${bridgeCanManage(i)?button('Reopen with reviewed context','bridge-reopen',i.ref.id):''}`;
 let result=(!b.linked&&i.integrity_available&&authority)?button('Prepare AI partner review','bridge-integrity-assess',i.ref.id):'';
 if(c){
  result+=`<p class="caption">${c.ready?'Domain responses support a decision.':'Domain review responses are still needed or concerns remain.'}</p>`;
  if(bridgeOtherHolds(c).length)result+='<p class="caption">Other governing issues affecting this requirement still need a response or a linked decision.</p>';
  if(c.stale.length)result+='<p class="caption">The linked review basis changed. The requirement owner must revise the proposal.</p>';
  if(Object.keys(c.body.required_reviews||{}).includes(state.actor)&&!c.stale.length&&!c.rights?.changed)result+=button('Record my domain response','review-form',c.ref.id);
  if(authority)result+=`<div class="actions">${button('Record requirement decision','bridge-decide',i.ref.id,'primary')}${button('Revise proposed change','bridge-propose',i.ref.id)}</div>`;
 }else if(b.linked?.kind==='intent'){
  const r=state.intake.refinements.find(r=>r.ref.id===b.linked.ref.id);
  result+=`<p class="caption">Sponsor response: ${esc(r?.body.status||'Open')}</p>${r?val('Requested intent wording',r.body.proposed_value):''}`;
  if(state.actor==='priya'&&r&&!state.intake.draft)result+=button('Start sponsor intake','bridge-sponsor-intake',i.ref.id);
  if(state.actor==='priya'&&r&&state.intake.draft)result+=`<div class="actions">${button('Prepare sponsor response','intent-adopt',r.ref.id,'primary')}${button('Defer or decline','intent-dispose',r.ref.id)}${r.body.status==='drafted'?button('Continue intake and preflight','bridge-sponsor-intake',i.ref.id):''}</div><p class="caption">Adding wording to the private draft leaves this issue open. Reviewed direction must be published before the change is incorporated.</p>`;
 }else if(b.route==='requirement'){
  if(authority){const existing=state.cases.find(c=>c.body.target.id===b.target.id&&!['approved','rejected'].includes(c.body.status));result+=existing?button('Link existing requirement review','bridge-link',i.ref.id,'primary'):button('Prepare requirement change','bridge-propose',i.ref.id,'primary');}
  else result+='<p class="caption">The requirement owner prepares a proposal after the domain implications are clear.</p>';
 }else if(b.route==='intent')result+=button('Propose intent wording','bridge-intent',i.ref.id,'primary');
 if(request?.status==='open'){
  result+='<p class="caption">An information request remains open. It must be answered or explicitly withdrawn before approving a change.</p>';
  if(authority)result+=button('Withdraw information request','bridge-withdraw',i.ref.id);
 }
 if(bridgeCanManage(i))result+=`<div class="actions section">${button('Assign or request evidence','bridge-respond',i.ref.id)}${button('Review context','bridge-refresh',i.ref.id)}</div>`;
 if(authority&&(!b.linked||(state.decision_rights?.ref&&b.linked.kind==='intent'&&state.intake.refinements.find(r=>r.ref.id===b.linked.ref.id)?.body.status==='declined')))result+=button('Close without governing change','bridge-close',i.ref.id);
 return result;
}
function bridgeSelectionFields(i){
 const b=i?.body||{},selectedPackets=new Set((b.packet_refs||[]).map(packetKey)),affected=new Set((b.requirement_refs||[]).map(r=>r.id));
 const packets=bridgePublicPackets(b.packet_refs||[]);
 return `<fieldset class="requirement-links"><legend>Published evidence trail</legend><p class="caption">Choose the exact versions that explain this issue. Private preflight packets cannot be shared here.</p>${packets.map(p=>`<label class="checkbox selectable"><input type="checkbox" name="packet" value="${esc(packetKey(p))}" ${selectedPackets.has(packetKey(p))?'checked':''}><span><strong>${esc(packetTitle(p))}</strong><small>Version ${esc(p.revision)} · ${p.records.length} records · ${esc(p.purpose)}</small></span></label>`).join('')||'<p>No packets have been published. Complete preflight and explicitly release the relevant work first.</p>'}</fieldset><details><summary>Affected requirements</summary><div class="details-body">${records('requirement').map(r=>`<label class="checkbox"><input type="checkbox" name="affected" value="${esc(r.ref.id)}" ${affected.has(r.ref.id)?'checked':''}><span>${esc(r.body.title||r.body.text)}</span></label>`).join('')||'<p>No requirements have been published yet.</p>'}</div></details><label class="form-field" id="bridge-target-wrap"><span>Requirement to decide</span><select name="target" id="bridge-target"><option value="">Choose a requirement</option>${records('requirement').map(r=>`<option value="${esc(r.ref.id)}" ${b.target?.id===r.ref.id?'selected':''}>${esc(r.body.title||r.body.text)}</option>`).join('')}</select><small>The decision target is included among the affected requirements automatically.</small></label>`;
}
function bridgeSelectionValues(fd){const id=String(fd.get('target')||''),target=id?get(id)?.ref:null,affected=fd.getAll('affected').map(id=>get(id).ref);if(target&&!affected.some(r=>r.id===target.id))affected.push(target);return {packet_refs:fd.getAll('packet').map(k=>{const [id,revision]=k.split('|');return {id,revision:Number(revision)};}),requirement_refs:affected,target};}
function bridgeReviewConcernContext(h){
 const r=h.requirement_record;
 return `<section class="section"><h3>Context carried with this concern</h3><p class="caption">A flagged concern is not validated evidence or an approved change.</p>${h.historical_context?'<p class="banner signal-notice signal-advisory">This review used earlier context. Its original versions will be carried as historical context.</p>':''}<details><summary>${esc(r.body.title||'Published requirement')} · v${r.ref.revision}</summary><div class="details-body">${val(r.body.status==='approved'?'Published requirement':'Published candidate',r.body.text)}${val('Acceptance criteria',r.body.acceptance_criteria||'Not specified')}${val('Conditions',r.body.conditions||'Not specified')}</div></details><details><summary>Exact published context (${h.context.length} records)</summary><div class="details-body">${h.context.map(c=>`<div class="rule">${technicalRef(c.ref)}${para(c.body.title||c.body.name||c.kind)}</div>`).join('')}</div></details>${h.review_excerpt?`<details open><summary>Review excerpt to share</summary><div class="details-body">${Object.entries(h.review_excerpt).filter(([,v])=>v).map(([k,v])=>val(({assessment:'Review observation',why_it_matters:'Why it matters',next_question:'Follow-up question',suggested_wording:'Suggested wording · not approved'})[k],v)).join('')}</div></details>`:'<p class="caption">Human-raised concern; no model review is attached.</p>'}${h.user_question?val('Your concern or question',h.user_question):''}<input type="hidden" name="affected" value="${esc(r.ref.id)}"><div id="bridge-target-wrap"><input id="bridge-target" type="hidden" name="target" value="${esc(r.ref.id)}"></div><label class="checkbox"><input type="checkbox" name="confirm_handoff" required><span>Share this concern${h.review_excerpt?', the shown review excerpt':''} and the shown published context with the project.</span></label></section>`;
}
function bridgeRaiseForm(defaults={}){const info=bridgeInfo();modal(defaults.handoff?'Carry concern to Decisions & Issues':'Raise an issue',`${field('title','Issue title',defaults.title||'','Name the specific tension, dependency or missing information.','input')}${settingSelector('bridge-kind','What kind of challenge?',Object.entries(info.kinds).map(([k,t])=>`<option value="${k}">${esc(t)}</option>`).join(''),'kind')}${domainText('question','What needs to be resolved?',defaults.question||'',true,'State the question in a way the receiving team can answer.')}${domainText('consequence','Why does it matter?',defaults.consequence||'',true,'Explain what could fail, change or be delayed. Keep uncertainty explicit.')}<fieldset class="requirement-links"><legend>Issue boards</legend>${Object.entries(info.boards).map(([k,t])=>`<label class="checkbox"><input type="checkbox" name="board" value="${k}" ${k===bridgeBoard?'checked':''}><span>${esc(t)}</span></label>`).join('')}</fieldset>${settingSelector('bridge-route','What might need to change?',Object.entries(bridgeRoutes).map(([k,t])=>`<option value="${k}">${t}</option>`).join(''),'route')}${settingSelector('bridge-owner','Who owns follow-up?',info.actors.map(a=>`<option value="${a}" ${a===state.actor?'selected':''}>${esc(bridgePerson(a))} · ${esc(state.actors[a].role)}</option>`).join(''),'owner')}${defaults.handoff?bridgeReviewConcernContext(defaults.handoff):bridgeSelectionFields()}`,'Raise issue',async fd=>{const result=await command(defaults.handoff?'field-coach-concern-publish':'bridge-raise',{...Object.fromEntries(fd),...(defaults.handoff?{expected:defaults.handoff.ref,confirm:fd.get('confirm_handoff')==='on'}:{}),boards:fd.getAll('board'),...bridgeSelectionValues(fd)});view='review';selected=result.id;bridgeBoard=fd.getAll('board')[0]||bridgeBoard;return result;},{className:'settings-dialog'});
 if(defaults.kind)$('#bridge-kind').value=defaults.kind;
 if(defaults.route)$('#bridge-route').value=defaults.route;if(defaults.owner)$('#bridge-owner').value=defaults.owner;
 const update=()=>{const req=$('#bridge-route').value==='requirement';$('#bridge-target-wrap').hidden=!req;$('#bridge-target').required=req;};$('#bridge-route').addEventListener('change',update);update();
}
function bridgeResponseForm(i,action='comment'){
 const b=i.body,can=bridgeCanManage(i),options=[['comment','Add a response'],...(can?[['investigate','Assign an investigation'],['request-evidence','Request evidence'],...(!b.linked?[['assign','Change issue owner']]:[])]:[]),...(state.actor===b.decision_owner&&!b.linked?[['defer','Defer with a next step']]:[])];
 const informationAction=action==='answer-request'||action==='withdraw-request';
 if(informationAction)options.splice(0,options.length,[action,action==='answer-request'?'Answer the information request':'Withdraw the information request']);
 modal('Respond to this issue',`${val('Question',informationAction?b.information_request?.question||b.question:b.question)}${settingSelector('bridge-response','Response type',options.map(([k,t])=>`<option value="${k}" ${k===action?'selected':''}>${t}</option>`).join(''),'action')}${domainText('note',action==='withdraw-request'?'Why is this request no longer needed?':'Your response or rationale','',true)}<div id="bridge-next-fields">${settingSelector('bridge-next','Who responds next?',bridgeInfo().actors.map(a=>`<option value="${a}" ${a===b.next_owner?'selected':''}>${esc(bridgePerson(a))}</option>`).join(''),'next_owner')}${domainText('next_question','What must they answer?','',true)}</div>`,'Save response',fd=>command('bridge-respond',{...Object.fromEntries(fd),expected:i.ref}));
 const update=()=>{const next=['investigate','request-evidence','assign','defer'].includes($('#bridge-response').value);$('#bridge-next-fields').hidden=!next;$('#bridge-next-fields textarea').required=next;};$('#bridge-response').addEventListener('change',update);update();
}
function bridgeRefreshForm(i,reopen=false){modal(reopen?'Reopen with reviewed context':'Review issue context',`<p>Choose the packet and requirement versions that should inform the next response. Previous selections and decisions remain in history.</p>${bridgeSelectionFields(i)}${domainText('note','What changed, and why use this context?','',true)}${reopen?'<label class="checkbox"><input name="confirm" type="checkbox" required><span>Reopen this issue; retain the earlier outcome in history.</span></label>':''}`,'Save reviewed context',fd=>command('bridge-refresh',{expected:i.ref,...bridgeSelectionValues(fd),note:fd.get('note'),confirm:fd.get('confirm')==='on'}),{className:'settings-dialog'});$('#bridge-target-wrap').hidden=i.body.route!=='requirement';$('#bridge-target').required=i.body.route==='requirement';}
function bridgeIntentForm(i){const sources=i.basis_records.filter(r=>r.kind==='contribution'),intent=records('intent')[0];if(!sources.length||!intent){modal('Published finding needed','<p>A proposed intent change needs a published domain contribution and an existing business direction. You can request evidence on this issue first.</p>');return;}
 modal('Propose business-intent wording',`${settingSelector('bridge-intent-source','Published contribution',sources.map(r=>`<option value="${esc(label(r.ref))}">${esc(r.body.domain)} · ${esc(referenceText(r.ref,r))}</option>`).join(''),'source')}${settingSelector('bridge-intent-field','Which part of the intent?',Object.keys(intakeNames).filter(k=>!['work_kind','assumption_owner'].includes(k)).map(k=>`<option value="${k}">${esc(intakeNames[k])}</option>`).join(''),'field')}<div id="bridge-current-intent"></div>${domainText('proposed_value','Proposed wording','',true)}${domainText('rationale','Why should the intent change?','',true)}<p class="caption">This requests a sponsor response. It does not change the published intent.</p>`,'Send for sponsor response',async fd=>{const result=await command('bridge-intent-propose',{expected_issue:i.ref,source:sources.find(r=>label(r.ref)===fd.get('source')).ref,field:fd.get('field'),proposed_value:fd.get('proposed_value'),rationale:fd.get('rationale')});selected=i.ref.id;view='review';return result;});
 const update=()=>{$('#bridge-current-intent').innerHTML=val('Current published wording',state.intake.baseline_values[$('#bridge-intent-field').value]);};$('#bridge-intent-field').addEventListener('change',update);update();
}
function bridgeDecisionHistory(){const outcomes=bridgeInfo().outcomes||[];return outcomes.length?`<details class="section"><summary>Linked issue outcomes (${outcomes.length})</summary><div class="acx-record-list details-body">${outcomes.map(o=>`<article class="card"><h3 class="acx-item-title"><a class="item-title-link" href="#main" data-action="bridge-open" data-id="${esc(o.issue.id)}">${esc(o.title)}</a></h3><p class="caption">${esc(bridgePerson(o.actor))} · ${esc(date(o.at))}</p>${val('Recorded outcome',o.disposition.replaceAll('-',' '))}${para(o.rationale)}${ref(o.decision)}</article>`).join('')}</div></details>`:'';}
async function bridgeAction(action,id){
 if(!action.startsWith('bridge-'))return false;if(!abandonIntakeEdits())return true;
 if(action==='bridge-requirement-view'){bridgeRequirementCategory='';bridgeRequirementFilter('bucket',id);return true;}
 if(action==='bridge-section'){
  if(id==='timeline'){
   busy=true;
   try{await load();}finally{busy=false;}
  }
  if(['assignments','developer-briefs'].includes(id)){await openDomainBriefDirectory();return true;}bridgeSection=id;selected=null;view='review';render();return true;
 }
 if(action==='bridge-overview-more'&&['mine','other'].includes(id)){
  const group=$('#accountability-extra-'+id);
  if(group){group.hidden=false;group.querySelector('summary')?.focus();}
  document.querySelector(`[data-action="bridge-overview-more"][data-id="${id}"]`)?.remove();
  return true;
 }
 if(action==='bridge-decision-source'){const entry=document.getElementById(id);if(entry&&entry.closest('#modal')){entry.open=true;const group=entry.parentElement.closest('details');if(group)group.open=true;entry.scrollIntoView({block:'nearest'});entry.querySelector('summary')?.focus();}return true;}
 if(action==='bridge-timeline-earlier'){await bridgeLoadEarlierTimeline();return true;}
 if(action==='bridge-board'){bridgeBoard=id;bridgeSection='boards';selected=null;view='review';render();return true;}
 if(action==='bridge-receipt-stage'){bridgeReceiptStage(id);return true;}
 if(action==='bridge-new'){bridgeRaiseForm();return true;}
 if(action==='bridge-back'){if(!['overview','timeline','activity'].includes(bridgeSection))bridgeSection='boards';selected=null;render();return true;}
 if(action==='bridge-open'){view='review';selected=id;const issue=bridgeIssue(id);if(issue&&!issue.body.boards.includes(bridgeBoard))bridgeBoard=issue.body.boards[0];render();return true;}
 const i=bridgeIssue(id);if(!i)throw Error('Reload the issue before continuing.');
 if(action.startsWith('bridge-integrity-'))return bridgeIntegrityAction(action,i);
 if(action==='bridge-decision-inline-ask')await askDecisionInline(i);
 else if(action==='bridge-decision-review')await openDecisionReview(i);
 else if(action==='bridge-decision-recover'){await command('decision-integrity-recover',{expected:i.ref});await openDecisionReview(i);}
 else if(action==='bridge-respond')bridgeResponseForm(i);
 else if(action==='bridge-answer')bridgeResponseForm(i,'answer-request');
 else if(action==='bridge-withdraw')bridgeResponseForm(i,'withdraw-request');
 else if(action==='bridge-refresh'||action==='bridge-reopen')bridgeRefreshForm(i,action==='bridge-reopen');
 else if(action==='bridge-propose'){const c=i.body.linked?.kind==='requirement'?findCase(i.body.linked.ref.id):null;proposalForm(get(i.body.target.id),c,undefined,i);}
 else if(action==='bridge-decide'){const c=findCase(i.body.linked.ref.id);decisionForm({...c,ready:bridgeDecisionReady(i,c)});}
 else if(action==='bridge-link'){const c=state.cases.find(c=>c.body.target.id===i.body.target.id&&!['approved','rejected'].includes(c.body.status));modal('Link existing requirement review',`${val('Proposal',c.body.proposal.text)}${domainText('note','Why does this review address the issue?','',true)}`,'Link review',fd=>command('bridge-link-review',{expected:i.ref,case:c.ref,note:fd.get('note')}));}
 else if(action==='bridge-intent')bridgeIntentForm(i);
 else if(action==='bridge-sponsor-intake'){view='intent';intakeStep='drawers';intakeCaseId=null;selected=null;render();}
 else if(action==='bridge-close')modal('Close without governing change',`${val('Issue',i.body.question)}${domainText('rationale','Why is no requirement or intent change needed?','',true)}<label class="checkbox"><input name="confirm" type="checkbox" required><span>Close this issue only. Existing requirements and Business Intent remain unchanged.</span></label>`,'Record issue disposition',fd=>command('bridge-close',{expected:i.ref,rationale:fd.get('rationale'),confirm:fd.get('confirm')==='on'}));
 return true;
}

let earlierTimeline = null;

function bridgeTimelineStatus({includeAccepted=false}={}){
 const issues=bridgeInfo().issues.filter(issue=>issue.body.status!=='resolved');
 const linkedCases=new Set(issues.filter(issue=>issue.body.linked?.kind==='requirement').map(issue=>issue.body.linked.ref.id));
 const items=issues.map(({ref,body,changed,waiting_since,rights})=>({
  kind:'issue',id:ref.id,attention:true,
  title:body.title,
  status:rights?.changed?'Decision rights changed':rights?.escalation?.status==='open'?'Escalation response needed':body.information_request?.status==='open'?'Information requested':bridgeStatuses[body.status]||body.status,
  next:rights?.changed?'Refresh the review to the current decision policy.':rights?.escalation?.status==='open'?rights.escalation.reason:body.information_request?.status==='open'?body.information_request.question:body.next_question||body.question,
  owner:rights?.changed?rights.current_decider||state.decision_rights?.rules?.[body.route]?.decider:rights?.escalation?.status==='open'?rights.escalation.owner:body.information_request?.status==='open'?body.information_request.owner:body.status==='awaiting-decision'?rights?.active_decider||body.next_owner:body.next_owner,
  requestLabel:rights?.changed||rights?.escalation?.status==='open'?'Requested response':body.information_request?.status==='open'?'Requested information':body.status==='awaiting-decision'?'Requested decision':'Next action',
  waitingReason:rights?.changed?'The recorded decision policy changed; this review needs to be refreshed.':rights?.escalation?.status==='open'?'An escalation response is still needed.':body.information_request?.status==='open'?'An information request is open. Approval waits for an answer or explicit withdrawal.':changed?.length?'Shared source versions changed; review the decision basis before approving a change.':body.status==='deferred'?body.next_question:body.status==='awaiting-decision'?'The issue is awaiting an explicit human decision.':'',
  boundary:'A response or acknowledgement records input. Publication shares work; neither action approves a requirement or authorizes delivery.',
  submitted_at:body.created_at,
  since:waiting_since,
  alert:changed?.length?'Context changed · review needed':'',
  where:body.boards.map(key=>bridgeInfo().boards[key]).filter(Boolean).join(' / ')||'Issue boards',
  gate:body.status==='awaiting-decision'||body.information_request?.status==='open',
  action:button('Open issue','bridge-open',ref.id,'small'),
 }));
 for(const request of state.project_flow?.requests||[]){
  const {ref,body,changed,published_outputs}=request;
  const accepted=body.status==='accepted';
  if(body.status!=='requested'&&!(includeAccepted&&accepted&&!published_outputs?.length))continue;
  const stale=changed?.length>0;
  items.push({
   kind:'brief',id:ref.id,attention:stale||!accepted,
   title:body.title,
   status:stale?'Brief context changed':accepted?'Accepted assignment':'Awaiting brief acceptance',
   next:stale?'Send a brief with current context.':accepted?body.expected_output:'Review the assigned brief and choose whether to accept the assignment.',
   requestLabel:accepted&&!stale?'Expected output':'Requested response',
   waitingReason:stale?'The brief refers to changed project context.':accepted?'':'The recorded recipient has not accepted this assignment.',
   boundary:accepted?'Assignment accepted; no published output is linked yet. Acceptance does not approve requirements.':'Accepting a brief takes on the assignment. It does not publish work or approve requirements.',
   owner:stale?body.requested_by:body.recipient,
   ownerLabel:accepted&&!stale?'Assigned to':'Next',
   since:stale||accepted?null:body.at,
   where:'Working briefs',
   gate:stale||!accepted,
   action:button('Open brief','pflow-request',ref.id,'small'),
  });
 }
 for(const review of state.cases||[]){
  const {ref,body,target_record,stale,intent_blockers,ready}=review;
  if(linkedCases.has(ref.id)||!['pending-review','deferred'].includes(body.status))continue;
  const blocked=stale?.length||intent_blockers?.length||bridgeOtherHolds(review).length;
  const required=body.required_reviews||{};
  const pending=Object.keys(required).filter(actor=>review.reviews?.[actor]?.body.disposition!==required[actor]);
  const title=target_record?.body.title||'Requirement review';
  const item={kind:'requirement-review',id:ref.id,attention:true,title,submitted_at:body.created_at,where:'Requirement reviews',gate:true,boundary:'Domain responses inform the decision. Only the recorded requirement decision approves or rejects the proposed change.',action:button('Open review','case',ref.id,'small')};
  if(review.rights?.changed)items.push({...item,status:'Decision rights changed',requestLabel:'Requested response',next:'Refresh the review to the current policy.',waitingReason:'The recorded decision policy changed.',owner:review.rights.current_decider||state.decision_rights?.rules?.requirement?.decider});
  else if(review.rights?.escalation?.status==='open')items.push({...item,status:'Escalation response needed',requestLabel:'Requested response',next:review.rights.escalation.reason,waitingReason:'An escalation response is still needed.',owner:review.rights.escalation.owner});
  else if(blocked)items.push({...item,status:'Review blocked',next:'Review the changed context or open dependencies.',waitingReason:stale?.length?'The requirement review refers to changed source versions.':intent_blockers?.length?'An open business direction issue affects this proposal.':'Other governing issues affecting this requirement remain open.'});
  else if(body.status==='deferred')items.push({...item,status:'Deferred',requestLabel:'Requested response',next:body.next_question,waitingReason:body.next_question,owner:body.next_owner});
  else if(ready)items.push({...item,status:'Awaiting decision',requestLabel:'Requested decision',next:'Decide whether to approve, revise, reject or defer the proposed requirement change.',waitingReason:'The required domain responses are recorded; a human decision is still needed.',owner:review.rights?.active_decider||body.decision_owner});
  else items.push({...item,status:'Awaiting domain review',requestLabel:'Requested response',next:'Record the outstanding domain reviews.',waitingReason:pending.length?'Required responses from '+pending.map(bridgePerson).join(', ')+' have not yet cleared this review.':'The review is not ready for a requirement decision. Open it to inspect the recorded blockers.',owner:pending});
 }
 return items;
}

function bridgeStatusRow(item,showWhere=false){
 const indication=bridgeItemIndication(item);
 return `<li class="timeline-status-row">
  <div><h3>${esc(indication.title)}</h3><div class="bridge-item-indicators">${indication.chips}</div>${showWhere&&item.where?`<p class="caption">${esc(item.where)}</p>`:''}
  ${Object.hasOwn(item,'submitted_at')?`<p class="caption">${recordedDate('Submitted',item.submitted_at)}</p>`:''}${item.next?`<p class="pre bridge-item-task"><span class="bridge-item-task-label">${esc(item.requestLabel||'Next action')}: </span>${esc(item.next)}</p>`:''}
  <p class="caption">${indication.names?esc(item.ownerLabel||'Next')+' · '+esc(indication.names):'Next owner not assigned'}${item.since?' · Waiting since '+esc(date(item.since)):''}</p></div>
  ${item.action}
 </li>`;
}
function bridgeStatusNowRow(item){
 const indication=bridgeItemIndication(item),names=indication.names;
 const when=(label,at,full=false)=>{
  const parsed=typeof at==='string'&&at.trim()?new Date(at):null;
  const value=parsed&&Number.isFinite(parsed.getTime())?`<time datetime="${esc(at)}" title="${esc(parsed.toLocaleString(undefined,{timeZoneName:'short'}))}">${esc(full?date(at):parsed.toLocaleDateString(undefined,{year:'numeric',month:'short',day:'numeric'}))}</time>`:'<span>Date not recorded</span>';
  return `<div><dt>${esc(label)}</dt><dd>${value}</dd></div>`;
 };
 return `<li class="timeline-status-row status-now-row"><div class="status-now-main">
  <div class="status-now-heading"><h3>${esc(indication.title)}</h3><div class="status-now-state bridge-item-indicators">${indication.chips}</div></div>
  ${item.next?`<div class="status-now-next"><p class="status-now-label">${esc(item.requestLabel||'Next action')}</p>${para(item.next)}</div>`:''}
  <dl class="status-now-facts">
   <div><dt>${esc(item.ownerLabel||'Next response')}</dt><dd>${esc(names||'Not assigned')}</dd></div>
   ${Object.hasOwn(item,'submitted_at')?when('Submitted',item.submitted_at):''}
   ${item.since?when('Waiting since',item.since,true):''}
  </dl>
 </div><div class="status-now-action">${item.action}</div></li>`;
}

const timelineDate = new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'});

function bridgeTimelineEntry(event){
 const packet=(state.packets||[]).find(p=>event.packet&&p.id===event.packet.id&&p.revision===event.packet.revision);
 return `<li class="timeline-event"><details>
  <summary><time datetime="${esc(event.at)}">${esc(timelineDate.format(new Date(event.at)))}</time>
  <span class="history-event-summary"><strong>${esc(event.category)}</strong>${event.subject?`<span class="timeline-subject">${esc(event.subject)}</span>`:''}</span></summary>
  <div class="timeline-event-detail">
   ${event.detail?`<div class="history-event-description">${para(event.detail)}</div>`:''}
   <dl class="history-event-facts">
    ${event.actor?`<div><dt>Recorded by</dt><dd>${esc(bridgePerson(event.actor))}</dd></div>`:''}
    ${event.recipient?`<div><dt>Sent to</dt><dd>${esc(bridgePerson(event.recipient))}</dd></div>`:''}
    <div><dt>Recorded version</dt><dd>${technicalRef(event.ref)}</dd></div>
    ${event.issue||event.linked?`<div><dt>Related versions</dt><dd>${[event.issue,event.linked].filter(Boolean).map(technicalRef).join(" · ")}</dd></div>`:''}
   </dl>
   <div class="workflow-card-actions">
    ${packet?button('Inspect published packet','packet',packetKey(packet),'small'):''}
    ${event.design_brief?`<a href="#main" class="workbench-document-link" data-action="pflow-shared-brief" data-id="${esc(packetKey(event.design_brief))}">Shared Working brief</a>`:''}
    ${event.issue?button('Open current issue','bridge-open',event.issue.id,'small'):''}
    ${event.work_request?button('Open current brief','pflow-request',event.work_request,'small'):''}
    ${event.case?button('Open requirement review','case',event.case.id,'small'):''}
    ${event.decision_rights?button('View decision rights','settings-decision-rights','','compact-text-action'):''}
    ${event.intake_case?button('Open direction review','intake-case',event.intake_case.id,'small'):''}
    ${event.demo_receipt?button('Open simulated receipt','demo-delivery-receipt',event.demo_receipt,'small'):''}
   </div>
  </div>
 </details></li>`;
}

function bridgeTimelineScreen(){
 const items=bridgeTimelineStatus();
 const page=bridgeInfo().timeline||{entries:[]};
 const extra=earlierTimeline?.page===page?earlierTimeline:null;
 const entries=[...page.entries,...(extra?.entries||[])];
 const before=extra?extra.before:page.before;
 return `<section class="card timeline-panel" aria-labelledby="project-timeline-title">
  <div class="card-head"><h2 id="project-timeline-title">Project timeline</h2></div>
  ${typeof projectTeamTimeline==='function'?projectTeamTimeline():''}
 </section>
 <section class="card timeline-panel timeline-status-panel" aria-labelledby="project-status-title">
  <div class="card-head"><h2 id="project-status-title">Status now</h2>${button('Refresh','refresh','','small')}</div>
  ${items.length?`<ul class="timeline-status-list">${items.slice(0,4).map(bridgeStatusNowRow).join('')}</ul>`:'<p class="status-now-empty">No open issues, pending brief acceptances, or open requirement reviews.</p>'}
  ${items.length>4?`<details><summary>More open items (${items.length-4})</summary><ul class="timeline-status-list">${items.slice(4).map(bridgeStatusNowRow).join('')}</ul></details>`:''}
 </section>
 <section class="card timeline-panel recorded-history-panel" aria-labelledby="recorded-history-title"><div class="card-head"><h2 id="recorded-history-title">Recorded event history</h2></div>
 ${entries.length?`<ol class="timeline-events">${entries.map(bridgeTimelineEntry).join('')}</ol>`:'<p class="caption">No recorded events.</p>'}
 ${before?button('Show earlier events','bridge-timeline-earlier','','small'):''}
 </section>`;
}

async function bridgeLoadEarlierTimeline(){
 const page=bridgeInfo().timeline;
 const prior=earlierTimeline?.page===page?earlierTimeline:null;
 const before=prior?prior.before:page?.before;
 if(!before)return;
 busy=true;
 try{
  const result=await command('project-timeline',{before});
  if(bridgeInfo().timeline!==page)return;
  const entries=prior?.entries||[];
  earlierTimeline={page,entries:[...entries,...result.entries],before:result.before};
  render();
  document.querySelectorAll('.timeline-event summary')[page.entries.length+entries.length]?.focus();
 }finally{busy=false;}
}

function bridgeSponsorGates(){
 return (state.intake?.cases||[]).filter(c=>['pending-review','deferred'].includes(c.body.status)).map(c=>{
  const pending=(c.body.reviewers||[]).filter(actor=>c.reviews?.[actor]?.body.disposition!=='ready-for-investigation');
  const item={kind:'direction-review',id:c.ref.id,attention:true,title:c.body.snapshot.title||'Business direction',where:'Business Intent',gate:true,
   boundary:'Publishing business direction establishes a basis for investigation. It does not approve requirements or authorize development.',action:button('Open direction review','intake-case',c.ref.id,'small')};
  if(c.rights?.changed)return {...item,status:'Decision rights changed',owner:c.rights.current_decider||state.decision_rights?.rules?.intent?.decider,requestLabel:'Requested response',next:'Refresh the direction review to the current policy.',waitingReason:'The recorded decision policy changed.'};
  if(c.rights?.escalation?.status==='open')return {...item,status:'Escalation response needed',owner:c.rights.escalation.owner,requestLabel:'Requested response',next:c.rights.escalation.reason,waitingReason:'An escalation response is still needed.'};
  if(c.stale?.length)return {...item,status:'Direction context changed',owner:c.body.requested_by,requestLabel:'Requested response',next:'Refresh the direction review against current inputs.',waitingReason:'The direction review refers to changed source versions.'};
  if(c.body.status==='deferred')return {...item,status:'Deferred',owner:c.body.next_owner,requestLabel:'Requested response',next:c.body.next_question,waitingReason:c.body.next_question};
  if(c.ready)return {...item,status:'Awaiting direction decision',owner:c.rights?.active_decider||c.body.decision_owner,requestLabel:'Requested decision',next:'Decide whether to publish the reviewed direction.',waitingReason:'The required domain responses are recorded; a direction decision is still needed.'};
  return {...item,status:'Awaiting domain review',owner:pending,requestLabel:'Requested response',next:'Record the outstanding domain reviews.',waitingReason:pending.length?'Required responses from '+pending.map(bridgePerson).join(', ')+' have not yet cleared this review.':'The direction review is not ready. Open it to inspect the recorded blockers.'};
 });
}

function bridgeActivityList(items,empty){
 const rows=values=>values.map(item=>bridgeStatusRow(item,true)).join('');
 return items.length?`<ul class="timeline-status-list">${rows(items.slice(0,4))}</ul>
  ${items.length>4?`<details><summary>Show ${items.length-4} more</summary><ul class="timeline-status-list">${rows(items.slice(4))}</ul></details>`:''}`
  :`<p class="caption">${empty}</p>`;
}

function bridgeActivityScreen(){
 const items=[...bridgeTimelineStatus({includeAccepted:true}),...bridgeSponsorGates()];
 const gates=items.filter(item=>item.gate), assigned=items.filter(item=>!item.gate);
 return `<div class="bridge-activity-layout">
  <div><section class="card timeline-panel" aria-labelledby="activity-humans">
   <div class="card-head"><h2 id="activity-humans">Human action needed</h2>${button('Refresh assignments','refresh','','small')}</div>
   ${bridgeActivityList(gates,'No pending decisions, reviews or input requests.')}
  </section>
  <section class="card timeline-panel" aria-labelledby="activity-assignments">
   <h2 id="activity-assignments">Human assignments</h2>
   ${bridgeActivityList(assigned,'No open assignments.')}
  </section></div>
  <section class="card timeline-panel" aria-labelledby="activity-agents">
   <h2 id="activity-agents">Agent work</h2>
   <div id="project-agent-activity"><p class="caption" role="status">Loading agent activity…</p></div>
  </section>
 </div>`;
}

const agentActivityStatuses={running:'In progress',succeeded:'Result prepared',failed:'Run failed',stale:'Inputs changed',unknown:'Outcome unconfirmed'};

function bridgeAgentWorkRow(run){
 const assignment=run.assignment;
 const brief=assignment&&(state.project_flow?.requests||[]).find(r=>r.ref.id===assignment.ref.id);
 const when=run.finished_at||run.started_at;
 return `<li class="agent-activity-row">
  <div class="card-head"><h4>${esc(run.agent)}</h4>${tag(agentActivityStatuses[run.status]||run.status,run.status==='running'?'blue':'')}</div>
  <p class="caption">${esc(run.where)}${run.mode==='simulated'?' · Simulated':''}</p>
  <p>${esc(run.task)}</p>
  ${assignment?`<p class="caption">Shared assignment · ${esc(assignment.title)} · ${ref(assignment.ref)}</p>`:''}
  <p class="caption">Requested by ${esc(bridgePerson(run.requester))}${when?' · '+esc(timelineDate.format(new Date(when))):''}</p>
  ${brief?button('Open current brief','pflow-request',brief.ref.id,'small'):''}
 </li>`;
}

let agentActivityTimer;
function mountBridgeAgentActivity(){
 clearTimeout(agentActivityTimer);
 const panel=$('#project-agent-activity');
 const overview=$('#accountability-overview');
 const target=panel||(overview?.querySelector('[data-accountability-assignment]')?overview:null);
 if(!target)return;
 const query=new URLSearchParams({project:state.project.id,generation:state.project.version});
 const isCurrent=()=>panel?$('#project-agent-activity')===panel:$('#accountability-overview')===overview;
 let lastContent='', lastData=null;

 async function refresh(){
  let retry=true;
  if(!isCurrent())return;
  try{
   if(document.hidden)return;
   const response=await fetch('/api/project-agent-activity?'+query);
   const data=await response.json();
   if(!isCurrent())return;
   if(!response.ok){
    retry=![401,403,409].includes(response.status);
    if(!retry)lastData=null;
    throw Error(data.error);
   }
   lastData=data;
   show(data);
  }catch(error){
   if(isCurrent())show(lastData?{active:[],recent:lastData.recent}:null,error.message||'Agent activity is temporarily unavailable.');
  }finally{
   if(retry&&isCurrent())agentActivityTimer=setTimeout(refresh,4000);
  }
 }
 function show(data,error){
  if(overview){accountabilityAgentSummary(overview,error?null:data);return;}
  const active=data?.active||[],recent=data?.recent||[];
  const content=`${error?`<p class="caption" role="status">${lastData?'Last recorded snapshot. ':''}${esc(error)}</p>`:''}
   <h3>In progress</h3>${active.length?`<ul class="agent-activity-list">${active.map(bridgeAgentWorkRow).join('')}</ul>`:
     '<p class="caption">'+(data&&!error?'No active agent runs.':'Run status unavailable.')+'</p>'}
   <h3>Recent activity</h3>${recent.length?`<ul class="agent-activity-list">${recent.slice(0,3).map(bridgeAgentWorkRow).join('')}</ul>`:
     '<p class="caption">'+(data?'No recorded workflow runs.':'Activity history unavailable.')+'</p>'}
   ${recent.length>3?`<details class="agent-earlier-runs"><summary>Earlier runs (${recent.length-3})</summary><ul class="agent-activity-list">${recent.slice(3).map(bridgeAgentWorkRow).join('')}</ul></details>`:''}`;
  if(content===lastContent)return;
  panel.innerHTML=content;
  lastContent=content;
 }
 void refresh();
}

function accountabilityItemPriority(a,b){return Number(b.gate)-Number(a.gate)||String(a.since||'').localeCompare(String(b.since||''));}
let accountabilityIssueFilter='all';
function accountabilityDate(at){const t=new Date(at);return isNaN(t)?'':t.toLocaleDateString(undefined,{day:'numeric',month:'short'});}
function accountabilityOverview(){
 const info=bridgeInfo(),items=[...bridgeTimelineStatus({includeAccepted:true}),...bridgeSponsorGates()];
 const isMine=item=>item.attention&&(Array.isArray(item.owner)?item.owner:[item.owner]).includes(state.actor);
 const mine=items.filter(isMine).sort(accountabilityItemPriority),others=items.filter(i=>!isMine(i)).sort(accountabilityItemPriority);
 const issues=info.issues||[],open=issues.filter(i=>i.body.status!=='resolved'),resolved=issues.length-open.length;
 const requests=issues.map(i=>({issue:i,request:i.body.information_request})).filter(x=>x.request),answered=requests.filter(x=>x.request.status!=='open').sort((a,b)=>String(b.request.responded_at).localeCompare(String(a.request.responded_at)));
 const cases=state.cases||[],openReviews=cases.filter(c=>['pending-review','deferred'].includes(c.body.status)),approved=cases.filter(c=>c.body.status==='approved');
 const latest=new Map();for(const r of bridgePublishedWork())if(!latest.has(r.ref.id))latest.set(r.ref.id,r);const work=[...latest.values()],authors=new Set(work.map(r=>r.body.owner).filter(Boolean));
 const stat=(label,value,sub,section)=>`<button type="button" class="accountability-stat" data-action="bridge-section" data-id="${section}"><span class="accountability-stat-label">${esc(label)}</span><span class="accountability-stat-value">${value}</span><span class="accountability-stat-sub">${esc(sub)}</span></button>`;
 const status=i=>i.body.status==='resolved'?`Resolved${i.body.resolution?.disposition?' · '+(i.body.resolution.disposition==='approve'?'approved':i.body.resolution.disposition):''}`:(i.rights?.changed?'Decision rights changed':i.body.information_request?.status==='open'?'Information requested':bridgeStatuses[i.body.status]||i.body.status);
 const mineIssue=i=>i.body.status!=='resolved'&&(i.body.next_owner===state.actor||i.body.information_request?.status==='open'&&i.body.information_request.owner===state.actor||i.body.status==='awaiting-decision'&&(i.rights?.active_decider||i.body.decision_owner)===state.actor);
 const shown=issues.filter(i=>accountabilityIssueFilter==='open'?i.body.status!=='resolved':accountabilityIssueFilter==='mine'?mineIssue(i):true);
 const seenTeam=new Set(),teamItems=[...(info.team_timeline?.items||[])].sort((a,b)=>String(b.end_at||b.start_at).localeCompare(String(a.end_at||a.start_at))).filter(t=>{const k=(t.title||'')+'|'+(t.owner||'');if(seenTeam.has(k))return false;seenTeam.add(k);return true;});
 return `<div id="accountability-overview" class="accountability-overview">
  <section class="accountability-stats" aria-label="Summary">${stat('Open issues',open.length,`${resolved} resolved`,'boards')}${stat('Waiting on someone',items.length,answered.length?'Last request answered '+accountabilityDate(answered[0].request.responded_at):'No requests yet','overview')}${stat('Reviews open',openReviews.length,approved.length?'Latest approved':'None decided yet','reviews')}${stat('Shared work',work.length,`From ${authors.size} ${authors.size===1?'person':'people'}`,'work')}</section>
  ${mine.length?`<section class="card accountability-panel accountability-attention-panel" aria-labelledby="accountability-attention-title"><h2 id="accountability-attention-title">Needs your attention</h2>${accountabilityList(mine,'mine','Nothing pending for you.')}</section>`:''}
  <section class="card accountability-panel" aria-labelledby="accountability-commitments-title"><h2 id="accountability-commitments-title">Commitments and requests</h2><p class="caption">Who owes what, across teams.</p>
   ${others.length?accountabilityList(others,'others',''):`<p class="caption accountability-empty">Nothing is open${mine.length?' for others':''}.</p>`}
   ${answered.length?`<ul class="accountability-requests">${answered.slice(0,4).map(({issue,request})=>`<li><span class="accountability-request-main"><strong>${esc(request.question)}</strong><span class="caption">Requested by ${esc(bridgePerson(request.raised_by))} · for ${esc(String(issue.body.title||'').replace(/\s*\(synthetic\)$/i,''))}</span></span><span class="accountability-request-who"><span>${esc(bridgePerson(request.responded_by||request.owner))}</span><span class="caption">Answered ${esc(accountabilityDate(request.responded_at))}</span></span><span class="ac-state ac-state-validated">Done</span></li>`).join('')}</ul>`:''}
  </section>
  <section class="card accountability-panel" aria-labelledby="accountability-issues-title"><div class="accountability-panel-head"><h2 id="accountability-issues-title">Issues</h2><div class="evidence-filters" role="group" aria-label="Filter issues">${[['all','All'],['open','Open'],['mine','Waiting on me']].map(([k,l])=>`<button type="button" class="ac-chip" data-action="accountability-issue-filter" data-id="${k}" aria-pressed="${accountabilityIssueFilter===k}">${l}</button>`).join('')}</div></div>
   ${shown.length?`<div class="accountability-table-wrap"><table class="accountability-table"><thead><tr><th scope="col">Issue</th><th scope="col">Type</th><th scope="col">Teams</th><th scope="col">Decides</th><th scope="col">Status</th></tr></thead><tbody>${shown.map(i=>`<tr><td><a href="#main" class="item-title-link" data-action="bridge-open" data-id="${esc(i.ref.id)}">${esc(String(i.body.title||'').replace(/\s*\(synthetic\)$/i,''))}</a><span class="caption">Raised by ${esc(bridgePerson(i.body.created_by))} · ${(i.events||[]).length} response${(i.events||[]).length===1?'':'s'}</span></td><td data-label="Type">${esc(info.kinds?.[i.body.kind]||i.body.kind)}</td><td data-label="Teams">${esc((i.body.boards||[]).map(k=>info.boards?.[k]||k).join(', '))}</td><td data-label="Decides">${esc(bridgePerson(i.rights?.active_decider||i.body.decision_owner)||'Not set')}</td><td data-label="Status"><span class="accountability-status ${i.body.status==='resolved'?'is-resolved':'is-open'}">${esc(status(i))}</span></td></tr>`).join('')}</tbody></table></div>`:`<p class="caption accountability-empty">${accountabilityIssueFilter==='mine'?'No issues are waiting on you.':'No issues yet. Raise one from published work when teams disagree, depend on each other or lack information.'}</p>`}
  </section>
  <div class="accountability-two">
   <section class="card accountability-panel" aria-labelledby="accountability-team-title"><div class="accountability-panel-head"><h2 id="accountability-team-title">Recent shared actions</h2>${button('Full timeline','bridge-section','timeline','quiet small')}</div>${teamItems.length?`<ol class="home-changes">${teamItems.slice(0,6).map(t=>`<li><span class="home-change-date">${esc(accountabilityDate(t.end_at||t.start_at))}</span><span class="home-change-body"><button type="button" class="home-change-title" data-action="${esc(t.action||'')}" data-id="${esc(t.action_id||'')}">${esc(String(t.title||'').replace(/\s*\(synthetic\)$/i,''))}</button><span class="home-change-meta">${esc([t.team_label,t.owner_name,t.status].filter(Boolean).join(' · '))}</span></span></li>`).join('')}</ol>`:'<p class="caption">Shared assignments, published work and decisions will appear here.</p>'}</section>
   <section class="card accountability-panel" aria-labelledby="accountability-work-title"><div class="accountability-panel-head"><h2 id="accountability-work-title">Shared work</h2>${button('All shared work','bridge-section','work','quiet small')}</div>${work.length?`<ul class="accountability-work">${work.slice(0,5).map(r=>`<li><a href="#main" class="item-title-link" data-action="read-contribution" data-id="${esc(r.ref.id)}">${esc(String(r.body.title||'Shared work').replace(/\s*\(synthetic\)$/i,''))}</a><span class="caption">${esc([r.body.domain,bridgePerson(r.body.owner),'version '+r.ref.revision].filter(Boolean).join(' · '))}</span></li>`).join('')}</ul>`:'<p class="caption">Nothing shared yet.</p>'}</section>
  </div>
 </div>`;
}
function accountabilityList(items,group,empty){
 if(!items.length)return `<p class="caption accountability-empty">${esc(empty)}</p>`;
 const visible=items.slice(0,3), extra=items.slice(3);
 return `<ul class="accountability-items">${visible.map(accountabilityRow).join('')}</ul>
  ${extra.length?`<ul class="accountability-items" id="accountability-extra-${group}" hidden>${extra.map(accountabilityRow).join('')}</ul>
   ${button('Show '+extra.length+' more','bridge-overview-more',group,'quiet small')}`:''}`;
}

function accountabilityRow(item){
 const indication=bridgeItemIndication(item,{showPersonal:false,showOpen:false}),{names,mine,caution}=indication;
 return `<li><details class="accountability-item${mine?' is-for-you':''}" name="accountability-work" data-signal="${caution?'advisory':mine?'attention':'reference'}">
  <summary><strong>${esc(indication.title)}</strong>
   ${indication.chips?`<span class="accountability-item-meta">${indication.chips}</span>`:''}
   ${item.attention!==false&&item.next?`<span class="accountability-item-task"><span class="accountability-preview-label">${esc(item.requestLabel||'Next action')}</span><span>${esc(item.next)}</span></span>`:''}
   <span class="accountability-item-facts">${!mine?`<span>${esc(item.ownerLabel||'Next response')} · ${esc(names||'Owner unassigned')}</span>`:''}${Object.hasOwn(item,'submitted_at')?`<span>${recordedDate('Submitted',item.submitted_at)}</span>`:''}</span>
  </summary>
  <div class="accountability-detail">
   <dl class="accountability-detail-facts"><div><dt>${esc(item.ownerLabel||'Next response')}</dt><dd>${esc(names||'Owner unassigned')}</dd></div></dl>
   <p class="caption">${esc(item.where)}${item.since?' · Waiting since '+esc(timelineDate.format(new Date(item.since))):''}</p>
   ${item.next?`<div class="accountability-next-action"><p class="accountability-detail-label">${esc(item.requestLabel||'Next action')}</p>${para(item.next)}</div>`:''}
   ${item.waitingReason?`<div class="accountability-next-action"><p class="accountability-detail-label">Why this is waiting</p>${para(item.waitingReason)}</div>`:''}
   ${item.boundary?`<p class="caption">${esc(item.boundary)}</p>`:''}
   ${accountabilityContext(item)}
  </div>
 </details></li>`;
}

function accountabilityContext(item){
 if(item.kind==='issue'){
  const issue=bridgeIssue(item.id), body=issue.body;
  const review=body.linked?.kind==='requirement'?findCase(body.linked.ref.id):null;
  const waiting=body.information_request?.status==='open'&&body.information_request.owner===state.actor;
  const canDecide=review&&body.status==='awaiting-decision'&&(review.rights?.can_decide??issue.rights?.can_decide??body.decision_owner===state.actor)&&!review.rights?.changed&&!issue.rights?.changed&&bridgeDecisionReady(issue,review);
  const action=waiting?button('Answer request','bridge-answer',item.id):
   canDecide?button('Review decision','bridge-decide',item.id):item.action;
  const packets=(body.packet_refs||[]).map(packet=>{
   const saved=(state.packets||[]).find(p=>packetKey(p)===packetKey(packet));
   const title=saved?'Inspect '+packetTitle(saved):'Inspect published context v'+packet.revision;
   return button(title,'packet',packetKey(packet),'quiet small');
  }).join('');
  const related=[...new Map((body.requirement_refs||[]).map(r=>[r.id,r])).values()];
  const requirements=related.length?`<details><summary>Related requirements (${related.length})</summary><div class="details-body">${related.map(r=>`<p><a href="#main" class="item-title-link" data-action="requirement" data-id="${esc(r.id)}">${esc(get(r.id)?.body.title||'Requirement')}</a></p>`).join('')}</div></details>`:'';
  return `${body.consequence?val('Why it matters',body.consequence):''}
   ${review?accountabilityComparison(review):''}${typeof decisionRightsPanel==='function'?decisionRightsPanel(review||issue,review?.rights||issue.rights):''}
   <div class="workflow-card-actions">${action}
   ${waiting||canDecide?button('Open full issue','bridge-open',item.id,'quiet small'):''}
   ${packets}</div>${requirements}`;
 }
 if(item.kind==='brief'){
  const brief=(state.project_flow?.requests||[]).find(r=>r.ref.id===item.id);
  const body=brief.body;
  return `${body.objective?val('Objective',body.objective):''}
   ${body.expected_output&&body.expected_output!==item.next?val('Expected output',body.expected_output):''}
   <p class="caption" data-accountability-assignment="${esc(packetKey(brief.ref))}" hidden></p>
   <div class="workflow-card-actions">${item.action}</div>`;
 }
 if(item.kind==='requirement-review'){
  const review=findCase(item.id);
  const ready=review.ready&&!review.rights?.changed&&!bridgeOtherHolds(review).length&&(review.rights?.can_decide??state.actor===review.body.decision_owner);
  return accountabilityComparison(review)+`<div class="workflow-card-actions">
   ${ready?button('Review decision','decision-form',item.id):''}${item.action}</div>`;
 }
 return `<div class="workflow-card-actions">${item.action}</div>`;
}

function accountabilityComparison(review){
 const b=review.body;
 return `<div class="accountability-comparison">
  <div>${val('Requirement at review',review.target_record.body.text)}<p class="caption">${ref(review.target_record.ref)}</p>${sourceDetails([review.ref,review.target_record.ref])}</div>
  <div>${val('Proposed wording',b.proposal.text)}<p class="caption">Review v${esc(review.ref.revision)}</p></div>
 </div>${b.proposal.acceptance_criteria?val('Proposed acceptance criteria',b.proposal.acceptance_criteria):''}
 ${b.proposal.conditions?val('Conditions',b.proposal.conditions):''}`;
}

function accountabilityAgentSummary(overview,data){
 const runs=new Map();
 for(const run of [...(data?.active||[]),...(data?.recent||[])]){
  if(!run.assignment?.ref)continue;
  const key=packetKey(run.assignment.ref);
  if(!runs.has(key))runs.set(key,run);
 }
 for(const element of overview.querySelectorAll('[data-accountability-assignment]')){
  const run=runs.get(element.dataset.accountabilityAssignment);
  const summary=run?`${run.agent} · ${agentActivityStatuses[run.status]||run.status} · Requested by ${bridgePerson(run.requester)}${run.mode==='simulated'?' · Simulated':''}`:'';
  if(element.textContent!==summary)element.textContent=summary;
  element.hidden=!summary;
 }
}


// Opt-in integrity review stays beside the issue and its decision, not a new destination.
function bridgeIntegrityText(i,text){
 const v=i.integrity,catalog=v.trace.citation_catalog||{};
 return `<p>${String(text||'').split(/(C-[a-f0-9]{16})/g).map(part=>{
  const c=catalog[part];if(!c)return esc(part);
  const record=v.trace.records.find(r=>r.ref.id===c.id&&r.ref.revision===c.revision);
  const label=record?.kind==='requirement'?'Requirement':record?.body.label||record?.body.title||'Source';
  return `<a class="item-title-link" href="#main" data-action="bridge-integrity-evidence-${part}" data-id="${esc(i.ref.id)}" title="Inspect the exact cited source">${esc(label)} v${esc(c.revision)}</a>`;
 }).join('')}</p>`;
}
function bridgeIntegrityDecision(i){
 const d=i.integrity?.decision_trace;if(!d)return '';
 const r=d.recommendation,chosen=d.options.find(o=>o.id===r.preferred_option);
 return `${val('Requested decision',r.requested_decision)}${val('Why this next step',r.why)}${val('Decision authority',bridgePerson(r.authority?.decider))}
 ${r.conditions.length?`<h3>What remains unproven</h3>${r.conditions.map(para).join('')}`:''}
 <details><summary>Compare options and what would change the recommendation</summary><div class="details-body">
 ${d.options.map((o,n)=>`<section class="rule"><h4>${esc(o.id)} · ${esc(o.action)}</h4><p class="caption">${esc(o.hard_gate==='passes'?'Admissible next action':o.hard_gate==='blocked'?'Blocked under the current basis':'Requires a separate governing decision')} · Owner: ${esc(bridgePerson(o.owner))}${chosen?.id===o.id?' · Recommended next step':''}</p>
 ${o.gate_reasons.map(para).join('')}${o.declared_condition_results?.length?`<details><summary>Declared conditions checked</summary><div class="details-body">${o.declared_condition_results.map(c=>val(c.rule,c.result+' · '+JSON.stringify(c.values))).join('')}</div></details>`:''}${['fidelity','evidence','workability','risk_and_change','effort_and_cost'].map(k=>val(({fidelity:'Requirement fidelity',evidence:'Evidence',workability:'Workability',risk_and_change:'Risks and scope',effort_and_cost:'Effort and cost'})[k],o.comparison[k])).join('')}
 ${o.dependencies.length?val('Dependencies',o.dependencies.join('\n')):''}${o.uncertainties.length?val('Remaining uncertainty',o.uncertainties.join('\n')):''}
 ${bridgeIntegrityText(i,o.evidence_refs.join(' '))}${i.integrity.option_responses?.[o.id]?val('Recorded response',i.integrity.option_responses[o.id].disposition.replaceAll('-',' '))+val('Rationale',i.integrity.option_responses[o.id].rationale)+val('Recorded by',bridgePerson(i.integrity.option_responses[o.id].actor))+val('Recorded at',date(i.integrity.option_responses[o.id].at))+(i.integrity.option_responses[o.id].proposed_correction?val('Proposed modification',i.integrity.option_responses[o.id].proposed_correction):''):''}
 ${i.rights?.can_decide&&i.body.status!=='resolved'&&!i.integrity.stale.length?`<a class="item-title-link" href="#main" data-action="bridge-integrity-option-${n}" data-id="${esc(i.ref.id)}">Record response to this option</a>`:''}</section>`).join('')}
 <h3>Evidence or decisions that would change this recommendation</h3>${r.would_change_if.map(para).join('')}
 <p class="caption">An admissible next action is not approval, verified compliance or permission to change a requirement.</p></div></details>`;
}
function bridgeIntegrityMeaning(part){
 const m=part.interpretation;if(!m)return '<p class="caption">This earlier review did not record a separate meaning disposition.</p>';
 return `${val('Meaning disposition',m.state)}${val('Reading',m.reading)}${val('Basis',m.basis)}${m.alternatives.map(a=>val('Material alternative',a.reading)+val('Effect',a.consequence)).join('')}${m.clarification?val('Clarification needed',m.clarification.question)+val('Responsible role',m.clarification.owner_role)+val('Action awaiting clarification',m.clarification.dependent_action)+val('Release condition',m.clarification.release_condition):''}<p class="caption">Model interpretation and clarification request. No human answer or ratification is implied.</p>`;
}
function bridgeIntegrityBasis(b){
 if(!b)return '<p class="caption">Earlier review: purpose was not recorded. Check current evidence before use.</p>';
 return `${val('Review purpose',b.purpose)}${b.evidence_currency?val('Evidence versions',b.evidence_currency.replaceAll('-',' ')):''}${para(b.boundary)}${b.reason?val('Why retain these versions',b.reason):''}${(b.superseded||[]).map(x=>`<div class="label-value"><label>Superseded input</label><p>${ref(x.selected)} → ${ref(x.current)}</p>${sourceDetails([x.selected,x.current])}</div>`).join('')}`;
}
function openIntegrityReview(r){
 const i={ref:r.ref,integrity:{trace:r.context,decision_trace:r.decision_trace}};
 modal('Earlier AI partner reply',`${bridgeIntegrityBasis(r.review_basis_now)}${para(r.summary)}${bridgeIntegrityTrace(i)}<p class="caption">Saved as ${ref(r.ref)}. This review is retained for comparison and is not attached to the current decision.</p>`);
}
function bridgeIntegrityReferenceName(i,raw,fallback='Selected context'){
 const trace=i.integrity?.trace||{},isExact=r=>r&&(typeof raw==='string'?label(r)===raw:r.id===raw?.id&&r.revision===raw?.revision);
 const record=(trace.records||[]).find(r=>isExact(r.ref)),packet=(trace.packets||[]).find(isExact);
 return record?referenceText(record.ref,record):packet?referenceText(packet):typeof raw==='object'&&raw?referenceText(raw):fallback;
}
function bridgeIntegrityTrace(i){
 const d=i.integrity?.decision_trace;if(!d)return '';
 return `<h3>Source obligations and interpretations</h3>${d.obligations.map(o=>`<details><summary>${esc(bridgeIntegrityReferenceName(i,o.source,'Source obligation'))} · ${esc(o.source.field)}</summary><div class="details-body">${technicalRef(o.source)}<blockquote>${esc(o.source.quote)}</blockquote>${['actor','action','object','timing','scope','condition','threshold','authority','exception','acceptance_criterion'].filter(k=>o.elements[k]).map(k=>{const e=o.elements[k];return val(k.replaceAll('_',' '),e.status==='unspecified'?'Unspecified in this clause':e.status+': '+e.quote+(e.interpretation&&e.interpretation!==e.quote?' — '+e.interpretation:''));}).join('')}<p class="caption">Interpretation is provisional; source wording governs.</p></div></details>`).join('')}
 <h3>Each packet against each applicable obligation</h3>${d.packet_findings.map(f=>`<section class="rule"><h4>${esc(bridgeIntegrityReferenceName(i,f.packet_ref,'Selected packet'))} · ${esc(f.status)}</h4>${bridgeIntegrityText(i,f.obligation_ref)}${para(f.reasoning)}${bridgeIntegrityText(i,f.evidence_refs.join(' '))}${(f.parts||[]).map(p=>`<details><summary>${esc(p.source?.meaning||p.claim_interpretation||'Material condition')} · ${esc(p.status)}</summary><div class="details-body">${bridgeIntegrityMeaning(p)}${val('Evidence judgment',p.reasoning)}${p.part_ref?`<details class="record-metadata"><summary>Source details</summary><div class="metadata-content">${esc(p.part_ref)}</div></details>`:''}${p.remaining_gap?val('Evidence still needed',p.remaining_gap):''}</div></details>`).join('')}<details class="record-metadata"><summary>Source details</summary><div class="metadata-content">${esc(f.packet_ref)}</div></details><p class="caption">Evidence support is a model judgment for human review. Absent means not supplied in this packet.</p></section>`).join('')}
 <h3>Consequential differences</h3>${d.differences.map(f=>`<section class="rule"><h4>${esc(f.classification)}</h4>${para(f.consequence)}${val('Would resolve or disprove this',f.would_disprove)}${bridgeIntegrityText(i,[f.obligation_ref,...f.evidence_refs].join(' '))}</section>`).join('')}
 ${val('Intended use',d.intended_use)}${para(d.support_boundary)}`;
}
function bridgeIntegrityPanel(i){
 const v=i.integrity;
 if(!v)return '';
 const material=v.findings.filter(f=>f.material),p=v.proposal?.body;
 return `<section class="card section integrity-review" aria-label="Decision basis"><h2>Decision basis</h2>
 ${v.semantic_evaluated?`<h3>Model recommendation</h3>${bridgeIntegrityText(i,v.summary)}`:para(v.summary)}
 ${bridgeIntegrityBasis(v.review_basis_now||v.trace.review_basis)}${bridgeIntegrityDecision(i)}
 ${p?`<details><summary>Recommendation under review · Human proposal</summary><div class="details-body">${para(p.text)}${val('Why it matters',p.rationale)}</div></details>`:''}
 ${v.trace.requirements.map(q=>{const r=v.trace.records.find(x=>x.ref.id===q.id&&x.ref.revision===q.revision);return val('Governing requirement',r?.body.text||'Requirement text unavailable');}).join('')}
 <details><summary>Compare domain expressions</summary><div class="details-body">${v.trace.records.filter(r=>r.kind==='integrity-expression').map(r=>`<section class="rule">${val(r.body.label,r.body.expression)}<p class="caption">Domain author’s expression · ${ref(r.ref)}</p></section>`).join('')}</div></details>
 <p class="caption">${v.semantic_evaluated?(v.execution_receipt?.mode==='live'?'Live model response and declared-condition checks':v.execution_receipt?.mode==='simulated'?'Scripted test response and declared-condition checks':'Model interpretation and declared-condition checks'):'Declared-condition checks · Language judgment not evaluated'} · ${ref(v.assessment)}</p>
 ${v.stale.length?'<div class="banner signal-notice signal-advisory"><strong>Inputs changed. This review needs reassessment.</strong></div>':''}
 <h3>What needs a decision</h3>${material.length?material.map(f=>`<article class="rule"><h4>${esc(f.title)}</h4>${para(f.effect)}${val('Suggested next action',f.action)}<p class="caption">${f.origin==='model'?'AI interpretation':'Explicit condition check'} · Evidence support: ${esc(f.support)} · ${f.disposition?esc(f.disposition.body.disposition.replaceAll('-',' ')):'Disposition needed'}</p>${f.disposition?val('Decision rationale',f.disposition.body.rationale)+(f.disposition.body.proposed_correction?val('Proposed correction',f.disposition.body.proposed_correction):'')+val('Recorded by',bridgePerson(f.disposition.body.actor))+val('Recorded at',date(f.disposition.body.at)):''}
 <details><summary>Evidence and limits</summary><div class="details-body">${f.citations.map(c=>`<blockquote>${esc(c.quote)}</blockquote><p class="caption">${ref(c)} · ${esc(c.field)}</p>`).join('')||'<p>The missing information has no supporting passage. Do not infer it.</p>'}</div></details>
 ${i.rights?.can_decide&&i.body.status!=='resolved'?`<a href="#main" data-action="bridge-integrity-dispose-${material.indexOf(f)}" data-id="${esc(i.ref.id)}">Record disposition: ${esc(f.title)}</a>`:''}</article>`).join(''):'<p>No material gap is reported within these declared conditions. This is not a compliance certificate.</p>'}
 <details><summary>Trace the recommendation</summary><div class="details-body">
 ${bridgeIntegrityTrace(i)}
 <h3>Governing requirements</h3>${v.trace.requirements.map(q=>{const r=v.trace.records.find(x=>x.ref.id===q.id&&x.ref.revision===q.revision);return `<section class="rule">${val(r?.body.title||'Governing requirement',r?.body.text||'Not available')}<p class="caption">Source requirement · ${ref(q)}</p></section>`;}).join('')}
 <h3>Domain expressions and evidence</h3>${v.trace.records.filter(r=>['integrity-expression','contribution','source','integrity-conditions','integrity-association'].includes(r.kind)).map(r=>`<details><summary>${esc(referenceText(r.ref,r))}</summary><div class="details-body">${technicalRef(r.ref)}<p class="caption">${esc(r.kind==='integrity-expression'?'Domain author’s interpretation':r.kind==='integrity-conditions'?'Owner-declared checks':r.kind==='integrity-association'?'Recorded relationship':'Source material')}</p><pre class="settings-instructions">${esc(JSON.stringify(r.body,null,2))}</pre></div></details>`).join('')}
 <h3>Local approvals and reconciliation</h3>${v.local_approvals.map(a=>`<section class="rule"><p>${ref(a.packet)} · ${esc(a.disposition)}</p>${a.receipt?val('Local reviewer',bridgePerson(a.receipt.actor))+val('Rationale',a.receipt.rationale):''}</section>`).join('')}
 <h3>Authorized decisions in the selected context</h3>${v.trace.records.filter(r=>r.kind==='decision'||r.kind==='bridge-issue-decision').map(r=>`<details><summary>Recorded decision · v${esc(r.ref.revision)}</summary>${technicalRef(r.ref)}<pre class="settings-instructions">${esc(JSON.stringify(r.body,null,2))}</pre></details>`).join('')||'<p class="caption">No prior decision record is selected in this bounded context.</p>'}
 <h3>Predecessors and review history</h3>${v.trace.predecessors.map(r=>`<details><summary>Earlier domain expression · v${esc(r.ref.revision)}</summary>${technicalRef(r.ref)}<pre class="settings-instructions">${esc(JSON.stringify(r.body,null,2))}</pre></details>`).join('')||'<p class="caption">No predecessor is selected for these expressions.</p>'}
 ${(v.history_records||[]).map(h=>`<details><summary>Earlier review · v${esc(h.assessment.revision)}</summary><div class="details-body">${technicalRef(h.assessment)}${bridgeIntegrityBasis(h.review_basis_now)}${para(h.summary)}${h.decision_trace?`<details><summary>Earlier options and recommendation</summary><div class="details-body">${val('Recommended option',h.decision_trace.recommendation.preferred_option||'Unresolved')}${val('Why',h.decision_trace.recommendation.why)}${h.decision_trace.options.map(o=>`<section class="rule">${val(o.id,o.action)}${val('Gate',o.hard_gate)}${['fidelity','evidence','workability','risk_and_change','effort_and_cost'].map(k=>val(k.replaceAll('_',' '),o.comparison[k])).join('')}</section>`).join('')}${Object.entries(h.option_responses||{}).map(([id,r])=>`<section class="rule">${val('Option '+id,r.disposition)}${val('Rationale',r.rationale)}${r.proposed_correction?val('Proposed modification',r.proposed_correction):''}${val('Recorded by',bridgePerson(r.actor))}${val('Recorded at',date(r.at))}</section>`).join('')}</div></details>`:''}${h.at?`<p class="caption">${esc(date(h.at))}</p>`:''}${(h.findings||[]).filter(f=>f.material).map(f=>`<section class="rule"><h4>${esc(f.title)}</h4>${para(f.effect)}</section>`).join('')}${Object.entries(h.dispositions||{}).map(([key,d])=>`<section class="rule"><h4>${esc((h.findings||[]).find(f=>f.key===key)?.title||key)}</h4>${val('Recorded disposition',d.disposition?.replaceAll('-',' ')||'Not recorded')}${d.rationale?val('Why',d.rationale):''}${d.resolution_assessment?`<p class="caption">Addressed in ${ref(d.resolution_assessment)}</p>`:''}</section>`).join('')}<details><summary>Exact input versions</summary><p class="caption">${(h.inputs||[]).map(technicalRef).join(' · ')}</p></details></div></details>`).join('')}
 ${v.execution_receipt?`<details><summary>Model execution receipt</summary><div class="details-body">${val('Execution',v.execution_receipt.mode+' · '+v.execution_receipt.status)}${val('Model',v.model?.resolved_model||v.execution_receipt.model)}${v.model?.response_id?val('Response ID',v.model.response_id):''}<p class="caption">${technicalRef(v.execution_receipt.ref)} · ${esc(v.execution_receipt.finished_at||'')}</p><details><summary>Request settings and contract</summary><pre class="settings-instructions">${esc(JSON.stringify({settings:v.model?.settings,usage:v.execution_receipt.usage,prompt:v.trace.prompt_version,instructions:v.trace.instruction_fingerprint,schema:v.trace.response_schema_fingerprint},null,2))}</pre></details></div></details>`:''}
 <h3>Review boundary</h3>${para(v.trace.manifest.boundary)}${val('Omitted dependencies',String(v.trace.manifest.omitted.length))}${val('Unavailable dependencies',String(v.trace.manifest.unavailable.length))}
 ${v.trace.manifest.excluded_packets?.length?val('Explicitly excluded packets',v.trace.manifest.excluded_packets.map(x=>referenceText(x.packet)+' — '+x.reason).join('\n')):''}
 <p class="caption">${v.model?'Model: '+esc(v.model.resolved_model||v.model.model||'Recorded in review'):'No model call in this assessment.'} · Matching IDs establish a relationship, not equivalent meaning.</p>
 </div></details></section>`;
}
function bridgeIntegrityActions(i){
 const v=i.integrity,b=i.body,ready=!Object.values(v.option_responses||{}).some(r=>['modify','defer'].includes(r.disposition))&&!v.stale.length&&v.domain_approval==='recorded'&&v.reconciliation==='recorded'&&!v.findings.some(f=>f.material&&!(f.origin==='model'&&f.disposition?.body.disposition==='reject-with-rationale'));
 if(b.status==='resolved')return `${button('Inspect resulting packet','packet',packetKey(b.resolution.packet))}${bridgeCanManage(i)?button('Prepare authorized reuse','bridge-integrity-promote',i.ref.id):''}`;
 return `<p class="caption">Local domain approval: ${esc(v.domain_approval)}<br>Cross-domain reconciliation: ${esc(v.reconciliation)}<br>Shared-use ratification: pending</p>
 <div class="actions">${v.trace.packets.map((p,n)=>v.local_approvals[n]?.can_approve?button('Review my domain input','bridge-integrity-local-'+n,i.ref.id,'small'):'').join('')}
 ${v.can_reconcile?button('Record my reconciliation','bridge-integrity-reconcile',i.ref.id):''}
 ${i.rights?.can_decide?button(v.stale.length?'Reassess changed inputs':'Revise recommendation','bridge-integrity-assess',i.ref.id)+(ready?button('Review ratification','bridge-integrity-ratify',i.ref.id):'<p class="caption">Resolve material findings and required reviewer responses before ratification.</p>'):''}</div>`;
}
async function bridgeIntegrityAction(action,i){
 const v=i.integrity;
 if(action.startsWith('bridge-integrity-evidence-')){
  const key=action.slice('bridge-integrity-evidence-'.length),c=v.trace.citation_catalog?.[key];
  if(!c)throw Error('This source is not in the assessed evidence catalog.');
  const record=v.trace.records.find(r=>r.ref.id===c.id&&r.ref.revision===c.revision);
  modal('Evidence source',`${val('Source',record?.body.label||record?.body.title||record?.kind||'Evidence source')}<blockquote>${esc(c.quote)}</blockquote><p class="caption">${technicalRef(c)} · ${esc(c.field)} · Exact assessed version</p>${record?.body.limitation?val('Limits',record.body.limitation):''}${record?.body.limitations?val('Limits',record.body.limitations):''}<p class="caption">A valid citation locates the passage. Its support for the recommendation remains a reviewable judgment.</p>`);
 }else if(action==='bridge-integrity-assess'){
  const old=v?.proposal;
  const preview=await command('integrity-preflight',{packets:i.body.packet_refs,evaluation_scope:'cross-domain',mode:'advisory',review_purpose:'current'});
  modal('Review the recommendation',`${bridgeIntegrityBasis(preview)}${settingSelector('integrity-purpose','Review purpose','<option value="current">Current evidence for this decision</option><option value="historical">Historical comparison of selected versions</option>','review_purpose')}${domainText('historical_reason','Reason for historical comparison, if selected','',false)}${domainText('text','Proposed interpretation',old?.body.text||i.body.question,true)}${domainText('rationale','Why this preserves the governing intent',old?.body.rationale||'',true)}<label class="checkbox"><input type="checkbox" name="semantic"><span>Ask the model to interpret these selected published packets and sources. The model cannot approve them.</span></label>`,'Prepare AI partner review',async fd=>{
   const historical=fd.get('review_purpose')==='historical';
   const data={packets:i.body.packet_refs,evaluation_scope:'cross-domain',mode:historical?'advisory':'formal',confirm:!historical,review_purpose:historical?'historical':'current',historical_reason:historical?fd.get('historical_reason'):'',semantic:fd.get('semantic')==='on',consent:fd.get('semantic')==='on'};
   const associations=(state.records||[]).filter(r=>r.kind==='integrity-association'&&r.body.status==='approved'&&r.body.packets.every(p=>i.body.packet_refs.some(q=>q.id===p.id&&q.revision===p.revision))).map(r=>r.ref);
   if(!historical){
    const check=await command('integrity-preflight',{...data,mode:'advisory'});
    if(!check.current_use_eligible)throw Error('These selected inputs are not current. Publish current versions or explicitly choose a historical comparison.');
    const proposal=await command('integrity-proposal',{packets:i.body.packet_refs,text:fd.get('text'),rationale:fd.get('rationale'),expected:old?.ref});data.proposal=proposal.ref;
   }
   const a=await command('integrity-assess',{...data,associations});
   if(historical)return {message:'Historical review saved; current decision unchanged.',integrityReview:await command('integrity-review-read',{assessment:a.ref})};
   return command('integrity-attach',{expected:i.ref,assessment:a.ref});
  });
 }else if(action.startsWith('bridge-integrity-local-')){
  const p=v.trace.packets[Number(action.split('-').pop())];
  const a=await command('integrity-assess',{packets:[p],evaluation_scope:'within-domain',mode:'formal',confirm:true});
  const record={body:a};
  modal('Local domain review',`${para(record.body.summary)}${a.findings.map(f=>`<section class="rule"><h3>${esc(f.title)}</h3>${para(f.effect)}${f.citations.map(c=>`<blockquote>${esc(c.quote)}</blockquote><p class="caption">${ref(c)}</p>`).join('')}</section>`).join('')}<p>Local approval retains any limits. It does not reconcile domains or ratify shared use.</p>${domainText('rationale','Local assessment and remaining limits','',true)}`,'Approve locally with limits',fd=>command('integrity-approve-domain',{assessment:a.ref,disposition:'approved-with-limits',rationale:fd.get('rationale')}));
 }else if(action.startsWith('bridge-integrity-option-')){
  const o=v.decision_trace?.options[Number(action.split('-').pop())];if(!o)throw Error('Reopen the current options.');
  modal('Respond to this option',`${para(o.action)}<p class="caption">This records a planning response. Ratification and requirement changes remain separate.</p>${settingSelector('option-disposition','Response',`${o.hard_gate==='passes'?'<option value="accept-next-step">Accept as the next planning step</option>':''}<option value="reject">Reject</option><option value="modify">Propose a modification</option><option value="defer">Defer</option>`,'disposition')}${domainText('rationale','Rationale','',true)}${domainText('proposed_correction','Proposed modification if selected','',false)}`,'Record response',fd=>command('integrity-option-response',{expected:i.ref,option:o.id,disposition:fd.get('disposition'),rationale:fd.get('rationale'),proposed_correction:fd.get('proposed_correction')}));
 }else if(action==='bridge-integrity-reconcile'){
  modal('Record reconciliation',`${para(v.summary)}${domainText('rationale','How the domain expressions work together, and what remains unresolved','',true)}`,'Record response',fd=>command('integrity-reconcile',{expected:i.ref,clear:true,rationale:fd.get('rationale')}));
 }else if(action==='bridge-integrity-ratify'){
  modal('Ratify the interpretation',bridgeIntegrityPanel(i)+`${domainText('rationale','Decision rationale','',true)}<label class="checkbox"><input type="checkbox" name="confirm" required><span>Authorize only this reviewed interpretation for the stated project scope. Governing requirements remain unchanged.</span></label>`,'Record ratification',fd=>command('bridge-close',{expected:i.ref,rationale:fd.get('rationale'),confirm:fd.get('confirm')==='on'}));
 }else if(action==='bridge-integrity-promote'){
  return command('integrity-promote',{expected:i.ref});
 }else if(action.startsWith('bridge-integrity-dispose')){
  // The item title in this compact selector is also available to keyboard users.
  const findings=v.findings.filter(f=>f.material),chosen=Number(action.split('-').pop())||0;
  modal('Disposition of a material finding',`${settingSelector('integrity-finding','Finding',findings.map(f=>`<option value="${esc(f.key)}" ${findings.indexOf(f)===chosen?'selected':''}>${esc(f.title)}</option>`).join(''),'finding')}${settingSelector('integrity-disposition','Decision',`<option value="investigate-and-defer">Investigate and defer this decision</option><option value="reject-with-rationale">Challenge the finding with rationale</option><option value="modify-with-rationale">Propose a correction with rationale</option>`,'disposition')}${domainText('rationale','Evidence, rationale and consequences','',true)}${domainText('proposed_correction','Proposed correction if selected','',false)}<p class="caption">To accept and address a finding, correct the affected input and reassess it. Approval cannot erase a deterministic gap.</p>`,'Record disposition',fd=>command('integrity-dispose',{expected:i.ref,finding:fd.get('finding'),disposition:fd.get('disposition'),rationale:fd.get('rationale'),proposed_correction:fd.get('proposed_correction')}));
 }
 return true;
}


function bridgeDecisionReviewEntry(i,c){
 const rights=c?.rights||i.rights;
 if(!(rights?.can_decide||rights?.can_review||rights?.can_refresh))return '';
 const scope=i.ref.id,key=bridgeDecisionDraftKey(scope),saved=bridgeDecisionInlineReviews.get(key),configured=state.coaching?.model?.configured??saved?.data?.configured;
 const pending=bridgeDecisionReviewSending.has(key)||saved?.data?.messages?.some(message=>message.status==='pending');
 return `<section id="decision-inline-review" class="decision-review-entry" data-decision-review-key="${esc(key)}"><h3 class="thought-partner-title">AI partner</h3><p class="caption">Private support for this decision.</p><div class="decision-inline-response" aria-live="polite">${bridgeDecisionInlineResponse(i,saved)}</div><label class="form-field reviewer-composer" for="decision-inline-question"><span>You</span><textarea id="decision-inline-question" class="integrity-review-input" data-reviewer-draft="decision" data-reviewer-scope="${esc(scope)}" data-reviewer-draft-key="${esc(key)}" aria-label="Ask your AI partner" rows="4" maxlength="4000" placeholder="Ask your AI partner">${esc(bridgeDecisionDraftRead(scope))}</textarea></label><button type="button" class="primary" data-action="bridge-decision-inline-ask" data-id="${esc(scope)}" ${pending||configured===false?'disabled':''}>Ask</button><p class="caption">Uses this issue’s shared evidence, history and decision rights. Asking does not approve or change anything.</p><a href="#main" class="item-title-link" data-action="bridge-decision-review" data-id="${esc(scope)}">Conversation &amp; evidence</a></section>`;
}
// A private composer draft is presentation state, never a saved decision or basis.
const bridgeDecisionReviewDrafts=new Map(),bridgeDecisionReviewSending=new Set(),bridgeDecisionInlineReviews=new Map();
let bridgeDecisionReviewOpenEpoch=0;
function bridgeDecisionDraftKey(scope){return typeof reviewerDraftKey==='function'?reviewerDraftKey('decision',scope):JSON.stringify([state.project?.id||'',state.project?.version||'',state.actor||'',scope]);}
function bridgeDecisionDraftRead(scope){return typeof reviewerDraftRead==='function'?reviewerDraftRead('decision',scope):bridgeDecisionReviewDrafts.get(bridgeDecisionDraftKey(scope))||'';}
function bridgeDecisionDraftWrite(scope,text,key=bridgeDecisionDraftKey(scope)){
 const value=String(text||'');bridgeDecisionReviewDrafts.set(key,value);
 if(typeof reviewerDraftWriteKey==='function')reviewerDraftWriteKey(key,value);
 else if(key===bridgeDecisionDraftKey(scope)&&typeof reviewerDraftWrite==='function')reviewerDraftWrite('decision',value,scope);
}
function clearSentDecisionDraft(scope,text,key){
 if(bridgeDecisionDraftKey(scope)!==key||bridgeDecisionDraftRead(scope)!==text)return;
 bridgeDecisionDraftWrite(scope,'',key);
 for(const selector of ['#decision-review-question','#decision-inline-question']){
  const input=$(selector);if(input?.getAttribute?.('data-reviewer-draft-key')===key&&input.value===text)input.value='';
 }
}
function captureDecisionReviewDraft(){
 if(typeof reviewerDraftCapture==='function'){reviewerDraftCapture();return;}
 const input=typeof document!=='undefined'?document.querySelector?.('#decision-review-question'):null;
 if(input?.dataset?.reviewerDraft==='decision')bridgeDecisionDraftWrite(input.dataset.reviewerScope,input.value,input.dataset.reviewerDraftKey);
}
function bridgeDecisionMessagesRead(messages,{inline=false}={}){
 const prefix=inline?'decision-inline-evidence':'decision-evidence';
 const source=(m,c,n)=>{const raw=m.catalog?.[c];return raw?`<details id="${prefix}-${n}-${esc(c)}"><summary>${esc(m.source_labels?.[c]||'Source')} · v${raw.revision}</summary><blockquote>${esc(raw.quote)}</blockquote><p class="caption">${technicalRef(raw)} · ${esc(raw.field)} · Exact response basis</p></details>`:'';};
 const reply=(m,n)=>`<p>${String(m.reply||'').split(/(C-[a-f0-9]{16})/g).map(part=>m.catalog?.[part]?(inline?esc((m.source_labels?.[part]||'Source')+' v'+m.catalog[part].revision):`<a class="item-title-link" href="#main" data-action="bridge-decision-source" data-id="${prefix}-${n}-${esc(part)}">${esc(m.source_labels?.[part]||'Source')} v${m.catalog[part].revision}</a>`):esc(part)).join('')}</p>`;
 return messages.map((m,n)=>`<article class="personal-chat-message user"><h3>You</h3>${para(m.question)}</article><article class="personal-chat-message ${m.status==='failed'?'chat-error':'assistant'}"><h3 class="integrity-review-name">AI partner${m.mode==='simulated'?' · Simulated':''}</h3>${m.status==='pending'?'<p>Responding…</p>':reply(m,n)}${m.stale?'<p class="caption">Decision context has changed since this response. Earlier wording remains historical.</p>':''}${m.citations?.length?`<details><summary>Evidence (${m.citations.length})</summary>${[...new Set([...m.citations,...Object.keys(m.catalog||{}).filter(c=>m.reply?.includes(c))])].map(c=>source(m,c,n)).join('')}</details>`:''}${!inline&&m.model?`<details><summary>Response receipt</summary><p class="caption">${esc(m.mode)} · ${esc(m.model)} · ${esc(m.finished_at||m.at)}</p>${m.response_id?`<p class="caption">${esc(m.response_id)}</p>`:''}</details>`:''}</article>`).join('');
}
function bridgeDecisionInlineResponse(issue,saved){
 if(!saved)return '';
 const stale=saved.expected.revision!==issue.ref.revision,messages=(saved.data?.messages||[]).slice(-1).map(message=>stale?{...message,stale:true}:message);
 return bridgeDecisionMessagesRead(messages,{inline:true})+(saved.pending&&!messages.some(m=>m.status==='pending')?'<p role="status">Reviewing…</p>':'')+(saved.error?`<p class="error" role="alert">${esc(saved.error)}</p>`:'');
}
function paintDecisionInlineReview(issue,key){
 if(bridgeDecisionDraftKey(issue.ref.id)!==key)return;
 const panel=typeof document!=='undefined'?document.querySelector?.('#decision-inline-review'):null;
 if(!panel||panel.dataset.decisionReviewKey!==key)return;
 const saved=bridgeDecisionInlineReviews.get(key),response=panel.querySelector('.decision-inline-response'),ask=panel.querySelector('[data-action="bridge-decision-inline-ask"]');
 if(response)response.innerHTML=bridgeDecisionInlineResponse(issue,saved);
 if(ask)ask.disabled=bridgeDecisionReviewSending.has(key)||(state.coaching?.model?.configured??saved?.data?.configured)===false||Boolean(saved?.data?.messages?.some(m=>m.status==='pending'));
}
async function askDecisionInline(i){
 const scope=i.ref.id,key=bridgeDecisionDraftKey(scope),expected={...i.ref},input=$('#decision-inline-question');
 const current=()=>bridgeDecisionDraftKey(scope)===key&&selected===scope&&bridgeIssue(scope)?.ref.revision===expected.revision;
 if(!current()||input?.getAttribute?.('data-reviewer-draft-key')!==key)throw Error('The review context changed. Reopen this decision before asking.');
 if(bridgeDecisionReviewSending.has(key))return;
 const question=String(input.value||'');if(!question.trim()){input.focus?.();return;}
 bridgeDecisionDraftWrite(scope,question,key);bridgeDecisionReviewSending.add(key);
 const saved=bridgeDecisionInlineReviews.get(key)||{expected};saved.pending=true;saved.error='';bridgeDecisionInlineReviews.set(key,saved);paintDecisionInlineReview(i,key);
 let sent=false;
 try{
  const data=await command('decision-integrity-read',{expected});if(!current())return;
  saved.data=data;saved.expected=expected;
  if(!data.configured)throw Error('Connect a model in Settings.');
  if(data.messages.some(message=>message.status==='pending'))throw Error('A response is still pending. You can keep drafting; open Conversation & evidence to check it.');
  await command('decision-integrity-send',{expected,thread:data.thread,question,request_id:crypto.randomUUID(),consent:true});sent=true;
  if(!current())return;
  clearSentDecisionDraft(scope,question,key);
  const dataAfter=await command('decision-integrity-read',{expected});if(!current())return;
  saved.data=dataAfter;saved.expected=expected;
 }catch(error){
  if(current())saved.error=sent?'Response saved. Open Conversation & evidence to inspect it.':error.message||'Review unavailable. Your question is retained.';
 }finally{
  saved.pending=false;bridgeDecisionReviewSending.delete(key);if(current())paintDecisionInlineReview(i,key);
 }
}
if(typeof document!=='undefined')document.addEventListener('input',event=>{
 const input=event.target;if(input.id==='decision-inline-question')bridgeDecisionDraftWrite(input.dataset.reviewerScope,input.value,input.dataset.reviewerDraftKey);
});
async function openDecisionReview(i){
 if(!i)throw Error('Reopen the issue before reviewing this decision.');
 captureDecisionReviewDraft();
 const scope=i.ref.id,key=bridgeDecisionDraftKey(scope),expected={...i.ref},epoch=++bridgeDecisionReviewOpenEpoch;
 const d=await command('decision-integrity-read',{expected});
 if(epoch!==bridgeDecisionReviewOpenEpoch||bridgeDecisionDraftKey(scope)!==key)return;
 bridgeDecisionInlineReviews.set(key,{expected,data:d,pending:false,error:''});paintDecisionInlineReview(i,key);
 const turns=bridgeDecisionMessagesRead(d.messages);
 const pending=d.messages.some(m=>m.status==='pending'),question=bridgeDecisionDraftRead(scope);
 const ask=async fd=>{
  if(bridgeDecisionDraftKey(scope)!==key)throw Error('The review context changed. Reopen this decision before asking.');
  if(pending||bridgeDecisionReviewSending.has(key))throw Error('A response is still pending. You can keep drafting.');
  if(!d.configured)throw Error('Connect a model in Settings.');
  const text=String(fd.get('question')||'');bridgeDecisionDraftWrite(scope,text,key);bridgeDecisionReviewSending.add(key);
  try{
   const result=await command('decision-integrity-send',{expected,thread:d.thread,question:text,request_id:crypto.randomUUID(),consent:true});
   // A next question typed while waiting belongs to the person, not this request.
   clearSentDecisionDraft(scope,text,key);
   return result;
  }catch(error){
   if(bridgeDecisionDraftKey(scope)===key){try{d.thread=(await command('decision-integrity-read',{expected})).thread;}catch{}}
   throw error;
  }finally{bridgeDecisionReviewSending.delete(key);}
 };
 modal('AI partner',`<p class="caption">${esc(d.title)} · Private to this reviewer</p><div class="decision-review-dialogue" aria-label="Private decision review" aria-live="polite">${turns||'<p>Test the recommendation, examine gaps, compare options or develop a decision rationale.</p>'}</div>${!d.messages.length?'<p class="caption">Try: “What evidence is missing?” or “What would make this recommendation unsafe?”</p>':''}<label class="form-field reviewer-composer" for="decision-review-question"><span>You</span><textarea id="decision-review-question" name="question" class="integrity-review-input" data-reviewer-draft="decision" data-reviewer-scope="${esc(scope)}" data-reviewer-draft-key="${esc(key)}" aria-label="Ask your AI partner" rows="4" maxlength="4000" required placeholder="Ask your AI partner">${esc(question)}</textarea></label><p class="caption">Uses this issue’s shared evidence, history and decision rights. Sending does not approve or change anything.</p>${pending?`<p class="caption">If an earlier request was interrupted, wait five minutes and <a class="item-title-link" href="#main" data-action="bridge-decision-recover" data-id="${esc(i.ref.id)}">recover this review</a>.</p>`:""}${!d.configured?'<p class="banner">Connect a model in Settings.</p>':''}`,'Ask',ask,{className:'decision-review-dialog',busyLabel:'Reviewing…'});
 const input=$('#decision-review-question');input?.addEventListener?.('input',()=>bridgeDecisionDraftWrite(scope,input.value,key));
 const submit=$('#modal-form button[type="submit"]');if(submit)submit.disabled=pending||!d.configured||bridgeDecisionReviewSending.has(key);
 $('#modal-title').classList.add('thought-partner-title');
 $('#modal-title').innerHTML='AI partner';
 const log=$('#modal .decision-review-dialogue'),latest=log?.querySelector?.('.personal-chat-message:last-child');
 if(latest)log.scrollTop+=latest.getBoundingClientRect().top-log.getBoundingClientRect().top-16;
}

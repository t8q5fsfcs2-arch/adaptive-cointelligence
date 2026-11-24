'use strict';
let state, view='projects', selected=null, busy=false, dirty=false, requirementsMode='scaffold';
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const rid=r=>r.ref.id, label=r=>`${r.id}:v${r.revision}`;
const records=kind=>state.records.filter(r=>r.kind===kind);
const get=id=>state.records.find(r=>rid(r)===id);
const findCase=id=>state.cases.find(r=>rid(r)===id);
const tag=(text,tone='')=>`<span class="tag ${tone}">${esc(text)}</span>`;
const ref=raw=>{const r=raw?.ref||raw;return `<span class="record-reference" data-record-id="${esc(r?.id||'')}" data-record-revision="${esc(r?.revision??'')}">${esc(referenceText(r))}</span>`;};
const para=t=>`<p class="pre">${esc(t)}</p>`;
const val=(title,text)=>`<div class="label-value"><label>${esc(title)}</label><div class="pre">${esc(text||'Not supplied')}</div></div>`;
const button=(text,action,id='',cls='')=>{
 const remove=/^Remove(?:\s|$)/.test(text);
 return `<button type="button" class="${cls}${remove?' remove-control':''}" data-action="${action}" data-id="${esc(id)}"${remove?` aria-label="${esc(text)}" title="${esc(text)}"`:''}>${remove?'<span aria-hidden="true">×</span>':esc(text)}</button>`;
};
const selectorChevron=()=>`<svg class="ui-selector-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>`;
const actionRow=(text,action,description,tone='',id='')=>`<div class="ui-action-row"><button type="button" class="${tone==='danger'?'danger':''}" data-action="${action}" data-id="${esc(id)}" aria-describedby="hint-${esc(action)}-${esc(id)}">${esc(text)}</button><p id="hint-${esc(action)}-${esc(id)}">${esc(description)}</p></div>`;
const field=(name,title,value='',help='',type='textarea')=>`<label class="form-field"><span>${esc(title)}</span>${type==='input'?`<input name="${name}" value="${esc(value)}" maxlength="20000" required>`:`<textarea name="${name}" maxlength="20000" ${['interpretation','recommendation'].includes(name)?'':'required'}>${esc(value)}</textarea>`}${help?`<small>${esc(help)}</small>`:''}</label>`;
const icon=n=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">${({intent:'<path d="M9 18h6M10 21h4M8 15c-5-5-1-12 4-12s9 7 4 12l-1 3H9Z"/>',packets:'<rect x="5" y="3" width="16" height="16" rx="2"/><path d="M3 7v14h14M9 8h8M9 12h8"/>',overview:'<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',requirements:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',preflight:'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="m8 12 3 3 5-6"/>',contributions:'<path d="M3 7h7l2 3h9v10H3Z"/><path d="M3 7V4h7l2 3h8v3"/>',review:'<rect x="3" y="4" width="7" height="16" rx="1"/><rect x="14" y="4" width="7" height="16" rx="1"/><path d="m9 12 6 0"/>',decisions:'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>'})[n]}</svg>`;
const impactBanner=id=>state.requirement_impacts[id]?.length?`<div class="banner signal-notice signal-advisory"><strong>A dependency has a newer version.</strong><p>The saved wording is preserved. Review whether the changed basis affects this requirement.</p>${state.requirement_impacts[id].map(x=>`<div>${ref(x.previous)} → ${ref(x.current)}</div>`).join('')}${sourceDetails(state.requirement_impacts[id].flatMap(x=>[x.previous,x.current]),'Changed source details')}<small>Based on recorded dependencies only.</small></div>`:'';
const statusTag=s=>tag(s.replaceAll('-',' '),typeof signalStatusTone==='function'?signalStatusTone(s):'');
const date=t=>t?new Date(t).toLocaleString():'';

function recordedDate(label,at){
 const parsed=typeof at==='string'&&at.trim()?new Date(at):null;
 if(!parsed||!Number.isFinite(parsed.getTime()))return `<span>${esc(label)} · Date not recorded</span>`;
 const short=parsed.toLocaleDateString(undefined,{year:'numeric',month:'short',day:'numeric'});
 const full=parsed.toLocaleString(undefined,{timeZoneName:'short'});
 return `<span>${esc(label)} <time datetime="${esc(at)}" title="${esc(full)}">${esc(short)}</time></span>`;
}

// Identity stays in label()/payloads. Normal reading uses permitted names/versions.
function referenceRecord(raw,provided){
 const target=raw?.ref||raw;if(!target?.id)return null;
 const matches=r=>r?.ref?.id===target.id&&r.ref.revision===target.revision;
 if(provided&&matches(provided))return provided;
 const current=typeof state==='undefined'?null:state;
 const rows=[...(current?.records||[]),...(current?.decisions||[]),...(current?.intake?.cases||[]),...(current?.cases||[])];
 if(current?.intake?.draft)rows.push({...current.intake.draft,kind:'intake-draft'});
 for(const c of current?.cases||[])rows.push(...(c.basis_records||[]),...(c.revisions||[]),...(c.target_record?[c.target_record]:[]));
 const exact=rows.find(matches);if(exact)return exact;
 const packet=(current?.packets||[]).find(p=>p.id===target.id&&p.revision===target.revision);
 if(packet)return {ref:{id:packet.id,revision:packet.revision},kind:'context-packet',body:{title:typeof packetTitle==='function'?packetTitle(packet):packet.purpose}};
 return null;
}
function referenceText(raw,provided){
 const target=raw?.ref||raw;if(!target?.id)return 'Reference not recorded';
 const record=referenceRecord(target,provided),b=record?.body||{};
 const names={requirement:'Requirement','requirement-drawer':'Requirement area',intent:'Business Intent','intake-draft':'Business Intent','intake-case':'Direction review','decision-case':'Requirement review',decision:'Decision','bridge-issue':'Issue','bridge-issue-decision':'Issue decision',contribution:'Outcomes report','contribution-draft':'Draft report',policy:'Policy',evidence:'Evidence',goal:'Goal','success-measure':'Success measure','context-packet':'Context packet','domain-brief':'Working brief','domain-request':'Work request','domain-deliverable':'Domain deliverable','project-request':'Work request','source':'Source'};
 const prefix=String(target.id).split('-')[0],fallback={REQ:'Requirement',DRW:'Requirement area',INT:'Business Intent',INTAKE:'Business Intent',CHG:'Requirement review',DEC:'Decision',ISSUE:'Issue',CON:'Outcomes report',PKT:'Context packet',POL:'Policy',EVD:'Evidence',CTX:'Context',G:'Goal',KPI:'Success measure',SRC:'Source'}[prefix]||'Record';
 const candidate=b.title||b.name||b.label||b.payload?.title||b.snapshot?.title||b.filename||record?.purpose;
 const title=typeof candidate==='string'&&candidate.trim()&&candidate!==target.id?candidate:(names[record?.kind]||fallback);
 return (record?.kind==='success-measure'&&typeof measureDisplayTitle==='function'?measureDisplayTitle(title):title)+(target.revision!=null?' · v'+target.revision:'');
}
function technicalRef(raw){
 const target=raw?.ref||raw;return `<span class="mono">${target?.id?esc(label(target)):'Reference not recorded'}</span>`;
}
function sourceDetails(raw,summary='Source details'){
 const refs=(Array.isArray(raw)?raw:[raw]).map(r=>r?.ref||r).filter(r=>r?.id),seen=new Set();
 const unique=refs.filter(r=>{const key=label(r);if(seen.has(key))return false;seen.add(key);return true;});
 return unique.length?`<details class="record-metadata"><summary>${esc(summary)}</summary><div class="metadata-content">${unique.map(r=>`<div>${technicalRef(r)}</div>`).join('')}</div></details>`:'';
}


async function load(projectId=currentProjectId,acceptGeneration=false){const r=await fetch('/api/state?project='+encodeURIComponent(projectId));const result=await r.json();if(!r.ok){if([401,403].includes(r.status)&&typeof checkAccountSession==='function')await checkAccountSession();throw Error(result.error||'Could not load workbench. Is the local server running?');}if(state?.auth?.account?.id&&result.auth?.account?.id!==state.auth.account.id){clearAccountViews();accountState=result.auth;state=result;restoreProjectView();render();throw Error('The signed-in account changed. Its workbench has been opened.');}if(!acceptGeneration&&state?.project?.id===result.project.id&&state.project.version!==result.project.version)throw Error('This project was reset or restored in another tab. Reload before saving; your unsaved text is still here.');state=result;}
async function command(action,data){const r=await fetch('/api/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf,'X-Workbench-Domain':state.domains?.active||'project','X-Workbench-Project':state.project.id,'X-Workbench-Version':String(state.project.version)},body:JSON.stringify(data)});const result=await r.json();if(!r.ok){if([401,403].includes(r.status)&&typeof checkAccountSession==='function')await checkAccountSession();throw Error(result.error||'Could not save');}return result;}
function toast(text){$('#notice').textContent=text;$('#notice').classList.add('visible');setTimeout(()=>$('#notice').classList.remove('visible'),5500);}
function projectTitle(){return state?.project?.title||records('project')[0]?.body.title||'Project';}
function selectWorkspaceView(next){
 if(next==='preflight'&&state.domains?.active){view='contributions';domainWorkMode='working';return;}
 if(typeof setupDraftPreviewProject!=='undefined')setupDraftPreviewProject=null;
 if(next==='planning'&&lockedRequirementsSetup())next='requirements';
 view=next;selected=null;
 if(next==='planning'||next==='requirements')requirementsMode='scaffold';
 if(view==='review')bridgeSection='overview';
 if(view==='intent'&&state.actor==='priya'){sponsorStage='framing';intakeStep='rationale';intakeCaseId=null;}
 else if(view==='intent'&&state.intake.published)intakeStep='review';
}
let navigationCollapsed=false;
function compactNavigation(){return window.matchMedia('(max-width: 1100px)').matches;}
function lockedRequirementsSetup(){return state.actor==='priya'&&Boolean(state.intake?.setup_governance?.enabled&&!state.intake.setup_governance.editable);}
function appHeader(actor,sponsorIdentity){
 return `<header class="ws-app-header"><div class="ws-brand-group"><button type="button" class="ws-home ws-home-wordmark" data-action="projects-home" aria-label="Adaptive Cointelligence · Home"><span class="ws-app-title"><strong class="ws-product-name">Adaptive Cointelligence</strong></span></button></div><div class="ws-app-user">${typeof acThemeToggleButton==='function'?acThemeToggleButton():''}${settingsNavigation()}${['testing','development'].includes(state.auth?.mode)?accountHeader():sponsorIdentity&&state.auth?.mode==='accounts'?homeIdentity(actor):`<span class="ws-user-name">${esc(actor.name)}${actor.name!==actor.role?' · '+esc(actor.role):''}</span><span class="ws-avatar" aria-hidden="true"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3Z"/></svg></span>`}</div><button type="button" id="app-menu-toggle" class="ws-menu-button" data-action="app-menu" aria-controls="site-navigation" aria-expanded="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg><span>Menu</span></button></header>`;
}
let businessDevelopmentOpen=false;
function businessDevelopmentNavigation(){
 const active=view==='planning'?'planning':view==='intent'?sponsorStage:null;
 return `<details class="business-development-nav ${active?'is-current':''}" ${businessDevelopmentOpen||active?'open':''}><summary class="business-development-title"><span class="app-navigation-label">Intent</span></summary><div class="business-development-children">${sponsorSteps.filter(([id])=>id!=='planning'||!lockedRequirementsSetup()).map(([id,title],i)=>`<button type="button" class="app-navigation-link sponsor-stage-link" data-action="sponsor-step" data-id="${id}" ${active===id?'aria-current="page"':''}><span class="sponsor-stage-number" aria-hidden="true">${i+1}</span><span>${esc(title)}</span></button>`).join('')}</div></details>`;
}
function projectPageIdentity(){
 const p=state.project||{},version=p.version_label||(p.version!=null?'v'+p.version:'');
 return `<header class="project-page-identity" aria-label="Project identity"><p class="project-page-title">${esc(p.title||'Untitled project')}</p>${p.reference||version?`<details class="record-metadata project-identity-details"><summary>Project details</summary><div class="metadata-content project-page-key">${p.reference?`<span class="project-page-id">${esc(p.reference)}</span>`:''}${p.reference&&version?'<span aria-hidden="true">·</span>':''}${version?`<span class="project-page-version">${esc(version)}</span>`:''}</div></details>`:''}</header>`;
}
function syncProjectPageIdentity(){
 const identity=$('.project-page-identity');if(!identity)return;
 const p=state.project||{},parts={'.project-page-title':p.title||'Untitled project','.project-page-id':p.reference||'','.project-page-version':p.version_label||(p.version!=null?'v'+p.version:'')};
 for(const [selector,text] of Object.entries(parts)){const node=identity.querySelector(selector);if(node&&node.textContent!==text)node.textContent=text;}
}
// Runtime test controls belong to developer support, not project status.
function projectStatusLine(){return '';}
function developerWorkspaceDetails(){
 const mode=state.auth?.mode;
 if(!mode||(mode==='accounts'&&state.actor!=='administrator'))return '';
 return `<details class="developer-workspace-details"><summary>Developer details</summary><div class="details-body">${state.workspace_notice?val('Evaluation controls',state.workspace_notice):''}<p>This is a working local decision system: your authored content, reviews, decisions, dependencies, and packet versions are stored in SQLite. NetworkX reconstructs the recorded relationships.</p><p>${state.auth?.mode==='accounts'?'Local accounts bind sign-in to an existing role and explicit project membership. Research and Design drafts, AI partner conversations and preflight remain within their domains. Enterprise SSO is not connected.':'This server explicitly enables test profiles. Switching roles here is not authenticated multi-user access.'}</p><p>The intake AI partner is a separate bounded agent with a replaceable model connection. It can prepare wording and questions; you choose what enters your private draft. Source text is extracted locally. Selected text and your draft are sent to the configured provider only when you ask your AI partner. Readiness and change signals remain deterministic checks.</p><p>Use Home to create or reopen projects, and the project selector for reset and recovery. Each project has its own SQLite database. Reset starts a blank intake and retains a restorable version of all prior work; it is not permanent deletion. Sponsor intake and direction publication are available. Launch authorization remains a separate workflow.</p>${val('Database',state.database)}</div></details>`;
}
function aboutContent(){
 return '<p>Adaptive Cointelligence connects project direction, evidence, professional work and decisions.</p><p>Working drafts stay private until you choose to share them. People publish selected work and authorize consequential changes.</p>'+developerWorkspaceDetails();
}
function mountProjectPageHeader(){
 if(['projects','thought-partner'].includes(view))return;
 const main=$('#main');if(!main||main.querySelector('.project-page-header'))return;
 const heading=main.querySelector([
  ':scope > .page-head',':scope > .chat-page-head',
  ':scope > .sponsor-surface > .page-head',':scope > .sponsor-surface > .sponsor-heading',
  ':scope > .workflow-page > .page-head'
 ].join(','));
 if(!heading)return;
 const identity=main.querySelector(':scope > .project-page-identity'),status=main.querySelector(':scope > .project-status-line'),sponsorActions=heading.querySelector('.sponsor-heading-actions'),requirementStatus=main.querySelector(':scope > .requirement-authority-summary');
 const intro=document.createElement('div'),titleArea=document.createElement('div'),statusArea=document.createElement('div');
 intro.className='project-page-header'+(status||sponsorActions||requirementStatus?' has-status':'');titleArea.className='project-title-area';statusArea.className='project-status-area';
 heading.before(intro);intro.append(titleArea,statusArea);
 if(identity)titleArea.append(identity);
 titleArea.append(heading);
 if(status)statusArea.append(status);
 if(sponsorActions)statusArea.append(sponsorActions);
 if(requirementStatus)statusArea.append(requirementStatus);
}
function navigationWayfindingIcon(kind){
 const paths={
  work:'<rect x="4" y="5" width="16" height="16" rx="2"/><path d="M9 5V3h6v2M8 10h8M8 14h8M8 18h5"/>',
  collaboration:'<circle cx="8" cy="7" r="3"/><path d="M2 21v-2a6 6 0 0 1 12 0v2m2-17a3 3 0 0 1 0 6m3 11v-2a6 6 0 0 0-3-5"/>',
  records:'<path d="M4 6h16v15H4ZM3 3h18v3H3ZM9 10h6m-6 4h6m-6 4h4"/>',
  home:'<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
  query:'<path d="M4 4h16v12H9l-5 4Z"/>',
  files:'<path d="M14 3H5v18h14V8Z"/><path d="M14 3v5h5M8 12h8M8 16h6"/>'
 };
 return `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${paths[kind]||paths.work}</svg>`;
}
function projectNavigationContent(){
 const names=workspaceNavigation(),global=['projects','thought-partner'].includes(view),info=typeof domainKnowledgeInfo==='function'?domainKnowledgeInfo():{domains:[],available:[],active:null};
 const active=state.domains?.active||null,current=id=>view===id?'aria-current="page"':'';
 const link=(label,attrs,meta='')=>`<button type="button" class="app-navigation-link" ${attrs}><span class="app-navigation-label">${esc(label)}</span>${meta?`<span class="app-navigation-meta">${esc(meta)}</span>`:''}</button>`;
 const intentRecord=typeof records==='function'?records('intent').find(r=>!r.scope||r.scope.startsWith('project:'))||records('intent')[0]:null,intentVersion=intentRecord?'v'+intentRecord.ref.revision:'';
 const intent=state.actor==='priya'&&!active?businessDevelopmentNavigation():active?link('Intent','data-action="nav-domain" data-id="project|intent"',intentVersion):names.intent?link('Intent',`data-nav="intent" ${current('intent')}`,intentVersion):'';
 const contextLink=global?'':state.actor==='priya'&&!active?'':active?link('Context','data-action="nav-domain" data-id="project|context"'):names.context?link('Context',`data-nav="context" ${current('context')}`):'';
 const domains=(info.domains||[]).filter(d=>(info.available||[]).includes(d.key)).map(d=>d.key===active?`${link(d.label,`data-nav="contributions" ${['contributions','preflight'].includes(view)?'aria-current="page"':''}`)}${typeof domainChatNavigation==='function'?domainChatNavigation():''}`:link(d.label,`data-action="nav-domain" data-id="${esc(d.key)}|contributions"`)).join('');
 const handoff=['priya','alex'].includes(state.actor)?names.delivery?link('Handoff',`data-nav="delivery" ${current('delivery')}`):link('Handoff','data-action="nav-domain" data-id="project|delivery"'):'';
 const project=global?'':`${intent}${contextLink}${domains}${names.requirements?link('Requirements',`data-nav="requirements" ${current('requirements')}`):''}${names.review?link('Decisions & Issues',`data-nav="review" ${current('review')}`):''}${handoff}`;
 const recordLinks=global?'':`<section class="app-navigation-group" data-navigation-group="records"><h3 class="app-navigation-heading">Records</h3>${names.decisions?link('Decision log',`data-nav="decisions" ${current('decisions')}`):''}${names.packets?link('Evidence trail',`data-nav="packets" ${current('packets')}`):''}${names.knowledge?link('Knowledge',`data-nav="knowledge" ${current('knowledge')}`):''}</section>`;
 const you=`<section class="app-navigation-group" data-navigation-group="you"><h3 class="app-navigation-heading">You</h3><div class="query-navigation-heading">${link('Ask',`data-action="thought-open" ${current('thought-partner')}`)}<button type="button" class="compact-text-action navigation-chat-add" data-action="thought-new" aria-label="New chat" title="New chat">＋</button></div>${typeof thoughtPartnerNavigation==='function'?thoughtPartnerNavigation():''}${link('Files (all projects)','data-action="files-open" aria-haspopup="dialog"')}</section>`;
 return `<nav class="app-navigation" aria-label="Project navigation"><div class="app-navigation-sections"><section class="app-navigation-group app-navigation-primary" data-navigation-group="work">${(global||!names.home?link('Home',`data-action="projects-home" ${current('projects')}`):link('Home',`data-nav="home" ${current('home')}`))}${project}${state.enterprise?.can_view?link('Enterprise context',`data-action="enterprise-open" ${current('enterprise')}`,state.enterprise.waiting_on_me?String(state.enterprise.waiting_on_me):''):''}</section>${recordLinks}${you}</div><div class="app-navigation-about">${button('About','about','','quiet')}</div></nav>`;
}
function refreshOpenProjectNavigation(){const nav=$('#modal.navigation-dialog[open] .app-navigation');if(nav)nav.outerHTML=projectNavigationContent();}
function persistentProjectNavigation(){return `<aside id="site-navigation" class="ws-site-navigation" aria-label="Site navigation">${projectNavigationContent()}</aside>`;}
function projectTaskNavigation(){
 if(!state.domains?.active)return '';
 const names=workspaceNavigation();
 return `<nav class="ws-task-navigation" aria-label="Domain workflow">${['contributions','review'].filter(id=>names[id]).map(id=>`<button type="button" data-nav="${id}" ${view===id?'aria-current="page"':''}>${esc(names[id])}</button>`).join('')}</nav>`;
}
function syncNavigationButton(){
 const toggle=$('#app-menu-toggle');if(!toggle)return;
 const compact=compactNavigation(),dialog=$('#modal');
 toggle.setAttribute('aria-controls',compact?'modal':'site-navigation');
 toggle.setAttribute('aria-expanded',String(compact?!!dialog?.open&&dialog.classList.contains('navigation-dialog'):!navigationCollapsed));
 if(compact)toggle.setAttribute('aria-haspopup','dialog');else toggle.removeAttribute('aria-haspopup');
}
function toggleProjectNavigation(){
 if(compactNavigation())modal('Menu',projectNavigationContent(),null,null,{className:'navigation-dialog',footer:false});
 else{navigationCollapsed=!navigationCollapsed;$('.ws-app-layout')?.classList.toggle('navigation-collapsed',navigationCollapsed);const nav=$('#site-navigation');if(!navigationCollapsed&&nav){nav.classList.remove('is-opening');void nav.offsetWidth;nav.classList.add('is-opening');}}
 syncNavigationButton();
}
async function navigateWorkspace(next){
 if(next==='overview'||next==='projects'){await openProjectsScreen();return;}
 await saveBeforeProjectChange();
 if(typeof caseOpenArea!=='undefined')caseOpenArea=null;
 if($('#modal')?.classList.contains('navigation-dialog'))closeModal();
 if(view==='projects'&&typeof setProjectsLocation==='function')setProjectsLocation(false);
 selectWorkspaceView(next);render();
 const heading=$('#main h1');if(heading){heading.tabIndex=-1;heading.focus();}
}
function render(){
 if(typeof enterpriseEnsure==='function')enterpriseEnsure();
 if(typeof reviewerDraftCapture==='function')reviewerDraftCapture();
 if(view==='planning'&&lockedRequirementsSetup()&&!(typeof setupDraftPreviewProject!=='undefined'&&setupDraftPreviewProject===`${state.actor}:${state.project.id}:${state.project.version}`)){view='requirements';selected=null;requirementsMode='scaffold';}
 if(view!=='planning'&&typeof setupDraftPreviewProject!=='undefined')setupDraftPreviewProject=null;
 if(view==='briefs'||view==='review'&&typeof bridgeSection!=='undefined'&&['assignments','developer-briefs'].includes(bridgeSection)){view=state.domains?.active?'contributions':'intent';selected=null;if(typeof bridgeSection!=='undefined')bridgeSection='overview';if(typeof publishedBriefNavigationOpen!=='undefined')publishedBriefNavigationOpen.set(publishedBriefNavigationKey(),true);}
 const planningRows=typeof capturePlanningRows==='function'?capturePlanningRows():null;
 const names=workspaceNavigation();
 if(view==='planning')requirementsMode='scaffold';
 if(!['projects','thought-partner','enterprise'].includes(view)&&!names[view]){view=state.domains?.active?'contributions':'intent';selected=null;}
 const actor=state.actors[state.actor], sponsorHomeActive=view==='projects', globalView=['projects','thought-partner','enterprise'].includes(view), sponsorIntakeActive=sponsorFlowActive(), sponsorIdentity=sponsorHomeActive||sponsorIntakeActive;
 $('#app').innerHTML=`<div class="workspace-app">${appHeader(actor,sponsorIdentity)}<div class="ws-app-layout ${navigationCollapsed?'navigation-collapsed':''}">${persistentProjectNavigation()}<div class="ws-content-column"><div class="ws-project-band ${sponsorHomeActive?'ws-home-band':''}"><div class="topbar">${globalView?'<span class="caption">'+(view==='projects'?'Home':view==='enterprise'?'Enterprise':'Query')+'</span>':projectControl()}${!sponsorHomeActive&&state.auth?.mode==='accounts'?accountHeader():''}</div></div><main id="main" class="main acx-page acx-view-${view} ${sponsorHomeActive?'sponsor-home-main':''}">${projectStatusLine(!globalView)}${view==='projects'?projectsScreen():({'thought-partner':thoughtPartnerScreen,intent:intakeScreen,planning:sponsorRequirements,delivery:deliveryScreen,requirements:requirements,contributions:domainScreen,preflight:preflightScreen,review:reviews,decisions:decisions,packets:packetsScreen,knowledge:typeof knowledgeScreen==='function'?knowledgeScreen:()=>'',context:typeof contextScreen==='function'?contextScreen:()=>'',enterprise:typeof enterpriseScreen==='function'?enterpriseScreen:()=>'',home:typeof projectHome==='function'?projectHome:()=>''}[view])()}</main></div></div></div>`;
 if(typeof mountAccountabilityHeader==='function')mountAccountabilityHeader();
 if(typeof mountProjectPageHeader==='function')mountProjectPageHeader();
 if(typeof mountThoughtPartner==='function')mountThoughtPartner();
 if(typeof lockSponsorSetupFields==='function')lockSponsorSetupFields();
 if(typeof mountFieldCoach==='function')mountFieldCoach();
 if(typeof mountRequirementTileLayout==='function')mountRequirementTileLayout();
 if(typeof mountDomainChat==='function')mountDomainChat();
 if(typeof mountReviewerUI==='function')mountReviewerUI();
 syncNavigationButton();
 if(typeof mountBridgeAgentActivity==='function')mountBridgeAgentActivity();
 const restored=planningRows&&restorePlanningRows(planningRows);
 if(!restored)window.scrollTo(0,0);
}
// Page intros stay short: one line inline, anything longer one click away.
function pageAbout(text){return `<details class="page-about"><summary>About this page</summary><p>${esc(text)}</p></details>`;}
function head(title,sub,actions=''){const long=sub&&String(sub).trim().split(/\s+/).length>14;return `<div class="page-head"><div><h1 tabindex="-1">${esc(title)}</h1>${sub?(long?pageAbout(sub):`<p>${esc(sub)}</p>`):''}</div><div class="actions">${actions}</div></div>`;}

function ratifiedRequirementRows(){return records('requirement').filter(r=>(!r.scope||r.scope.startsWith('project:'))&&r.body.status==='approved');}
function pendingRequirementRows(){return records('requirement').filter(r=>(!r.scope||r.scope.startsWith('project:'))&&r.body.status!=='approved');}
let requirementNavigationPending=false;
async function openRequirementSection(mode=requirementsMode,id=null){
 if(requirementNavigationPending)return;
 requirementNavigationPending=true;
 try{
  await saveBeforeProjectChange();
  requirementsMode=mode;selected=id;view='requirements';
  render();const heading=$('#main h1');if(heading){heading.tabIndex=-1;heading.focus();}
 }finally{requirementNavigationPending=false;}
}
function requirements(){
 const target=selected&&get(selected);
 if(target?.scope&&!target.scope.startsWith('project:'))return head('Requirements','Only published project requirements appear here.')+'<p class="requirements-baseline-empty">Not published to Requirements.</p>';
 if(selected&&get(selected)?.kind==='requirement')return requirementDetail(get(selected));
 if(selected&&get(selected)?.kind==='requirement-drawer')return drawerPage(selected);
 if(requirementsMode==='domains')return requirementsAcrossDomains();
 if(typeof requirementOrganizationRead==='function')return head('Requirements','Goals, requirements and the intent factors that guide development.')+requirementsToolbar()+requirementAuthoritySummary()+requirementOrganizationRead(sharedRequirementRows());
 if(typeof requirementAssessmentMapRead==='function')return head('Requirements','From Business Intent and published team findings. Inspect evidence, confidence and the next useful action.')+requirementsToolbar()+requirementAuthoritySummary()+requirementAssessmentMapRead(sharedRequirementRows())+`<details class="requirement-map-guidance"><summary>Goals, areas and review guidance</summary><div class="details-body">${requirementDrawers({sharedOnly:true})}</div></details>`;
 const drawers=sharedRequirementDrawerRows(),reqs=sharedRequirementRows().filter(r=>!drawers.some(d=>d.ref.id===r.body.drawer_id));
 return head('Requirements','Business Intent establishes requirement areas, known constraints and proposed behaviors. Domain findings add evidence; Decisions & Issues resolves gaps and consequential changes.')+requirementsToolbar()+requirementAuthoritySummary()+requirementDrawers({sharedOnly:true})+(reqs.length?`<section class="section"><h2>Requirement wording</h2><div class="grid two">${reqs.map(r=>`<article class="card" ${typeof ratifiedRequirementCategoryAttributes==='function'?ratifiedRequirementCategoryAttributes(r.body.drawer_id):''}><div class="card-head"><div><div class="eyebrow">${esc(r.body.drawer||'Project requirements')}</div><h3 class="acx-item-title"><a href="#main" class="item-title-link" data-action="requirement" data-id="${esc(rid(r))}">${esc(r.body.title||r.body.text)}</a></h3><details class="record-metadata"><summary>Source details</summary><div class="metadata-content">${technicalRef(r.ref)}</div></details></div>${tag(r.body.status==='approved'?'Ratified':'Proposed')}</div>${para(r.body.text)}${state.requirement_impacts[rid(r)]?tag('Basis changed · review needed','amber'):''}${typeof requirementAssessmentRead==='function'?requirementAssessmentRead(r,{compact:true}):`<div class="context-strip"><span>${requirementConfidenceLabel()}</span><span>Validation not recorded</span><span>Owner: ${esc(state.actors[r.body.owner]?.name||r.body.owner||'Not assigned')}</span></div>`}</article>`).join('')}</div></section>`:requirementScaffoldSource({sharedOnly:true}).categories.length?'':`<p class="requirements-baseline-empty">No published requirement areas.</p>`);
}
function requirementsToolbar(){
 const draft=state.actor==='priya'&&lockedRequirementsSetup()&&state.intake.draft?'<aside class="setup-draft-access" aria-label="Private setup draft"><span class="workbench-context-chip">Private</span><a href="#main" class="item-title-link" data-action="sponsor-setup-draft" title="Retained sponsor setup, separate from the published requirements">Saved setup draft</a></aside>':'';
 const populated=typeof sharedRequirementDrawerRows==='function'?sharedRequirementDrawerRows().length>0||records('requirement').length>0:true;
 return `<div class="requirements-toolbar${populated?'':' requirements-toolbar-empty'}">${populated?requirementsSwitch():''}<div class="requirement-view-controls">${typeof ratifiedRequirementCategoryControl==='function'?ratifiedRequirementCategoryControl():''}${populated&&typeof requirementLayoutControl==='function'&&(typeof requirementsMode==='undefined'||requirementsMode!=='domains')?requirementLayoutControl():''}</div>${draft}</div>`;
}
function requirementAuthoritySummary(){
 const reqs=[...ratifiedRequirementRows(),...pendingRequirementRows()],assessed=reqs.filter(r=>Object.values(state.requirement_assessments?.items?.[r.ref.id]?.uses||{}).some(use=>use.current)).length;
 return `<section class="requirement-authority-summary" aria-label="Requirement map status"><div class="requirement-status-chips"><div class="requirement-status-counts"><span class="workbench-context-chip">${reqs.length} requirement${reqs.length===1?'':'s'}</span>${assessed?`<span class="workbench-context-chip">${assessed} with recorded assessments</span>`:''}</div></div>${typeof requirementBusinessIntentConclusionRead==='function'?requirementBusinessIntentConclusionRead():''}</section>`;
}
function requirementDetail(r){
 const active=state.cases.find(c=>c.body.target.id===rid(r)&&!['approved','rejected'].includes(c.body.status));
 const related=state.cases.filter(c=>c.body.target.id===rid(r));
 return `<div class="breadcrumb">${button('← All requirements','back-requirements','','quiet')}</div>`+head(r.body.title||'Requirement dossier',r.body.drawer||'Project requirements',tag(r.body.status==='approved'?'Ratified':'Proposed'))+impactBanner(rid(r))+intentRefinementNotice(rid(r))+`<div class="grid requirement-dossier"><div class="card">${typeof requirementDeliveryStaging==='function'?requirementDeliveryStaging(r):''}${typeof needContextRequirementNotice==='function'?needContextRequirementNotice(r):''}${requirementContentRead(r)}${val('Rationale',r.body.rationale)}${val('Conditions and boundaries',r.body.conditions)}${linkedGoalsRead(r.body)}${typeof requirementEvidenceSection==='function'?requirementEvidenceSection(rid(r)):''}<div class="actions">${active?button('View proposed change in Decisions & Issues','case',rid(active),'quiet'):button(r.body.status==='approved'?'Discuss a change':'Discuss this proposal','requirement-discuss',rid(r),'quiet')}</div></div><details class="dossier-metadata"><summary>Source details & linked reviews</summary><div class="metadata-content">${technicalRef(r.ref)}</div><div class="grid two details-body"><div class="card"><h2>Decision boundaries</h2>${val('Decision status',r.body.status==='approved'?'Ratified':'Proposed')}${val('Evidence confidence','See the scoped assessment above; ratification does not establish a rating.')}${val('Evidence level','Calculated from shared work and open issues (D004); separate from the recorded rating and from ratification.')}${val('Validation','Not recorded as a shared requirement assessment')}${val('Fulfillment',r.body.fulfillment||'not-evaluated')}${val('Execution',r.body.execution||'not-authorized')}<small>Ratification adopts the wording. Evidence, fulfillment and execution remain separate.</small></div><div class="card"><h2>Linked reviews</h2>${related.length?related.map(c=>`<div class="rule">${statusTag(c.body.status)}<p>${esc(c.body.proposal.text)}</p>${button('Open review','case',rid(c),'small')}</div>`).join(''):'<p class="muted">No shared review yet.</p>'}</div></div></details></div>`+requirementResolution(r);
}
function contributionCard(r,draft=false){
 const b=r.body;return `<article class="card${typeof reportIsFocused==='function'&&reportIsFocused(r.ref.id)?' report-arrived':''}"><div class="card-head"><div><div class="eyebrow">${esc(b.domain)}</div><h3 class="acx-item-title"><a class="item-title-link${b.working_report?' workbench-document-link':''}" href="#main" data-action="read-contribution" data-id="${esc(rid(r))}">${esc(b.title||'Domain contribution')}</a></h3><p class="caption">Version ${esc(r.ref.revision)}</p></div>${tag(draft?'Within team':'Decisions & Issues',draft?'purple':'green')}</div>${para(b.working_report?.entries[0]?.text||b.observation||b.text)}${b.working_report?`<p class="caption">Findings · ${b.working_report.entries.length} sections</p>`:''}${tag(focusLabel(b),'blue')}${b.limitation?`<p class="caption">Limits: ${esc(b.limitation)}</p>`:''}<div class="actions workflow-card-actions">${!draft&&b.design_brief?`<a href="#main" class="workbench-document-link" data-action="pflow-shared-brief" data-id="${esc(b.design_brief.id+'|'+b.design_brief.revision)}">Working brief</a>`:''}${draft?'':packetContributionButton(r)}${!draft&&typeof reportBridgeEditButton==='function'?reportBridgeEditButton(r):''}${draft?button('Edit draft','edit-contribution',rid(r))+button('Preview publication','publish',rid(r),'primary'):''}</div>${draft?'':findingActions(r)}${sourceDetails(r.ref)}</article>`;
}
function contributions(){return head('Contributions','Work in your preferred tools. Bring the consequential finding, its source, and its limits here.',['sam','maya'].includes(state.actor)?button('New contribution','new-contribution','','primary'):'')+`<section><h2>Within your team ${tag('Drafts','purple')}</h2>${!['sam','maya'].includes(state.actor)?'<div class="empty">Switch to Research or Operations to author and publish a contribution.</div>':records('contribution-draft').length?`<div class="grid two">${records('contribution-draft').map(r=>contributionCard(r,true)).join('')}</div>`:'<div class="empty">No drafts in this profile. Start with an observation or an operational constraint.</div>'}</section><section class="section"><h2>Across teams ${tag('Published versions','green')}</h2><p class="muted">These versions can be selected for a shared requirement review. Publishing is not approval.</p>${records('contribution').length?`<div class="grid two">${records('contribution').map(r=>contributionCard(r)).join('')}</div>`:'<div class="empty">Published contributions will appear here.</div>'}</section>`;}
function reviews(){
 const content=selected&&findCase(selected)?reviewDetail(findCase(selected)):bridgeScreen();
 return `<div class="workflow-page bridge-page">${content}</div>`;
}
function basisCard(r){const b=r.body;return `<div class="card"><div class="card-head"><div><div class="eyebrow">${esc(b.domain||r.kind)}</div><h3>${esc(b.title||'Reviewed basis')}</h3><p class="caption">Version ${esc(r.ref.revision)}</p></div></div>${val('Observation / constraint',b.observation||b.text)}${b.interpretation?val('Interpretation',b.interpretation):''}${b.recommendation?val('Recommendation',b.recommendation):''}${b.limitation?val('Limits',b.limitation):''}<details class="record-metadata"><summary>Source details</summary><div class="metadata-content">${technicalRef(r.ref)}${b.source?`<p class="pre">${esc(b.source)}</p>`:''}</div></details></div>`;}
function reviewDetail(c){
 const b=c.body,closed=['approved','rejected'].includes(b.status),changed=!closed&&c.stale.length>0,decision=(state.decisions||[]).find(d=>d.ref.id===b.decision_ids?.at(-1));
 return `<div class="breadcrumb">${button('← All reviews','back-review','','quiet')}</div>`+head('Compare and decide',`${c.target_record.body.title||'Requirement'} · Review v${c.ref.revision}`,statusTag(b.status))+`<p class="caption">${recordedDate('Submitted',b.created_at)}${decision?' · '+recordedDate('Decision recorded',decision.body.at):''}</p>`+intentRefinementNotice(b.target.id)+`${changed?`<div class="banner signal-notice signal-advisory"><strong>The reviewed basis has changed.</strong><p>Earlier reviews and decisions remain recorded. Refresh the proposal before collecting new reviews.</p>${(typeof canPrepareRequirement==='function'?canPrepareRequirement():state.actor==='alex')?button('Review changed basis','revise',rid(c)):'The requirement owner can prepare the refreshed proposal.'}</div>`:''}${b.status==='deferred'?`<div class="banner blue"><strong>Waiting for ${esc(state.actors[b.next_owner]?.name||b.next_owner)}</strong>${para(b.next_question)}</div>`:''}<div class="grid cols"><div><div class="grid two comparison"><section class="card"><div class="eyebrow">${closed?'Previous basis':'Current requirement'}</div>${ref(c.target_record.ref)}${para(c.target_record.body.text)}${val('Acceptance criteria',c.target_record.body.acceptance_criteria)}${val('Conditions',c.target_record.body.conditions)}${statusTag(c.target_record.body.status)}</section><section class="card candidate"><div class="eyebrow">${b.status==='approved'?'Approved wording':'Proposed wording'}</div>${para(b.proposal.text)}${val('Acceptance criteria',b.proposal.acceptance_criteria)}${val('Conditions',b.proposal.conditions)}${b.proposal.rationale?val('Why this change',b.proposal.rationale):''}</section></div><section class="section"><div class="card-head"><div><h2>The two perspectives</h2><p class="caption">Exact versions selected for this review. Each team retains its own interpretation.</p></div>${!closed&&(typeof canPrepareRequirement==='function'?canPrepareRequirement():state.actor==='alex')?button('Revise proposal','revise',rid(c),'small'):''}</div><div class="grid two">${c.basis_records.filter(r=>r.kind==='contribution').map(basisCard).join('')}</div></section><section class="card section"><h2>Review history</h2><p class="caption">Earlier wording and assessments remain available after a proposal is revised.</p><details><summary>Inspect ${c.revisions.length} saved revisions</summary><div class="details-body">${c.revisions.map(v=>`<div class="packet-record">${ref(v.ref)} · ${statusTag(v.body.status)}${para(v.body.proposal.text)}${Object.entries(v.reviews).map(([a,r])=>`<p><strong>${esc(state.actors[a]?.name||a)}</strong> · ${esc(r.body.disposition.replaceAll('-',' '))}</p><p class="caption">${recordedDate('Submitted',r.body.at)}</p>${para(r.body.rationale)}`).join('')}</div>`).join('')}</div></details></section><section class="card section"><h2>Intent and constraints</h2>${c.basis_records.filter(r=>['intent','policy','evidence'].includes(r.kind)).map(r=>`<div class="rule">${ref(r.ref)}${para(r.body.text)}${r.body.limitation?`<small>${esc(r.body.limitation)}</small>`:''}${r.kind==='intent'&&r.body.intake?`<details><summary>Full Business Intent at this version</summary><div class="details-body">${Object.entries(r.body.intake).map(([k,v])=>val(intakeNames[k]||k,v)).join('')}</div></details>`:''}</div>`).join('')}<details><summary>All record references</summary><div class="details-body">${[c.ref,b.target,...b.basis].map(r=>`<div>${technicalRef(r)}</div>`).join('')}</div></details></section></div><aside class="card readiness"><h2>Review checks</h2>${typeof decisionRightsPanel==='function'?decisionRightsPanel(c,c.rights):''}<p class="caption">System checks · no AI interpretation</p>${Object.keys(b.required_reviews||{sam:'supported-with-limits',maya:'cleared-with-conditions'}).map(a=>{const review=c.reviews[a],r=review?.body;return `<div class="rule"><div class="rule-title"><span>${esc(state.actors[a]?.role||a)}</span>${tag(r?'Recorded':'Needed',r?'blue':'amber')}</div><p>${esc(r?r.disposition.replaceAll('-',' '):a==='sam'?'Does the evidence support the need within its limits?':'Does the proposal respect operational constraints?')}</p>${r?`<p class="caption">${recordedDate('Submitted',r.at)}</p><p class="pre">${esc(r.rationale)}</p>`:''}${!closed&&!changed&&state.actor===a?button(r?'Update my review':'Record my review','review-form',rid(c),'small'):''}</div>`;}).join('')}<div class="rule"><div class="rule-title">Requirement decision</div><p>${closed?'Decision recorded. Further changes require a new proposal.':c.ready?'Ready for the named decider’s decision.':changed?'Refresh the changed basis first.':'Approval needs the required reviews. Concerns must be resolved.'}</p>${!closed&&(c.rights?.can_decide??state.actor===b.decision_owner)?button('Record decision','decision-form',rid(c),'primary'):!closed?'<p>The named decider or active delegate records the decision.</p>':''}</div><div class="rule"><p>Requirement approval is separate from fulfillment and execution authorization.</p>${closed&&(typeof canPrepareRequirement==='function'?canPrepareRequirement():state.actor==='alex')?button('Propose another change','proposal',b.target.id):''}</div></aside></div>`;
}
function decisions(){return head('Decision log','See decisions, their evidence and what changed.')+intakeDecisionHistory()+bridgeDecisionHistory()+`<div class="grid cols"><div>${state.decisions.length?`<div class="history">${[...state.decisions].reverse().map(d=>`<article class="card"><div class="card-head"><div><div class="caption">${esc(projectHomeDate(d.body.at)||date(d.body.at))} · ${esc(d.body.actor.name)}</div><h3 class="acx-item-title"><a href="#main" class="item-title-link" data-action="case" data-id="${esc(d.body.case.id)}">${esc(d.body.proposal.text.slice(0,110))}${d.body.proposal.text.length>110?'…':''}</a></h3>${ref(d.ref)}</div>${statusTag(({approve:'approved',reject:'rejected',defer:'deferred'})[d.body.disposition])}</div>${val('Decision rationale',d.body.rationale)}<details><summary>Requirement wording & criteria</summary><div class="details-body">${para(d.body.proposal.text)}${val('Acceptance criteria',d.body.proposal.acceptance_criteria)}${val('Conditions',d.body.proposal.conditions)}</div></details>${d.body.next_question?val('Next question',d.body.next_question):''}${d.body.result_requirement?`<p>${ref(d.body.result_requirement)}</p>`:''}<details><summary>Reviewed basis and team responses</summary><div class="details-body">${[d.ref,...d.body.basis].map(r=>`<div>${technicalRef(r)}</div>`).join('')}${Object.entries(d.body.reviews).map(([a,r])=>`<p>${esc(state.actors[a]?.name||a)}: ${technicalRef(r)}</p>`).join('')}</div></details></article>`).join('')}</div>`:'<div class="empty"><h2>No requirement decisions yet</h2><p>Reviews inform a decision. Only an explicit decision saves one here.</p></div>'}</div><aside class="card"><details><summary>Evidence trail (${state.packets.length})</summary><p class="caption">Saved assemblies of exact record versions.</p>${state.packets.length?state.packets.map(p=>`<div class="rule"><a class="item-title-link" href="#main" data-action="packet" data-id="${esc(p.id+'|'+p.revision)}">${ref({id:p.id,revision:p.revision})}</a><p>${esc(p.purpose)}</p></div>`).join(''):'<p class="muted">Your first requirement will create a starting packet.</p>'}</details></aside></div>`;}

function modal(title,content,submitLabel,handler,options={}){
 if(typeof reviewerDraftCapture==='function')reviewerDraftCapture();
 const d=$('#modal');dirty=false;d.className=(options.className||'')+' acx-dialog';d.innerHTML=`<form id="modal-form"><header class="dialog-head"><div><h2 id="modal-title"${title.includes('AI partner')?' class="thought-partner-title"':''}>${esc(title)}</h2></div><button type="button" data-close class="quiet icon" aria-label="Close dialog">✕</button></header><div class="dialog-body"><div class="error" role="alert"></div>${content}</div>${options.footer===false?'':`<footer class="dialog-foot"><button type="button" data-close>${handler?'Cancel':'Close'}</button>${handler?`<button type="submit" class="primary ${options.submitTone==='danger'?'danger':''}">${esc(submitLabel)}</button>`:''}${options.footerActions||''}</footer>`}</form>`;
 if(typeof mountReviewerUI==='function')mountReviewerUI(d);
 $('#modal-form').addEventListener('input',event=>{if(!event.target.closest('.reviewer-width-control')&&!event.target.matches('[data-reviewer-draft]'))dirty=true;});
 $('#modal-form').addEventListener('submit',async e=>{e.preventDefault();if(!handler||busy)return;busy=true;const submit=e.submitter,priorLabel=submit.textContent;submit.disabled=true;if(options.busyLabel)submit.textContent=options.busyLabel;try{const result=await handler(new FormData(e.target));dirty=false;d.close();if(!result?.projectLoaded)await load();busy=false;render();toast(result?.message||'Saved');if(result?.decisionReviewIssue)await openDecisionReview(bridgeIssue(result.decisionReviewIssue));if(result?.modelConnectionProfile!==undefined)openModelConnections(result.modelConnectionProfile||null);if(result?.adminIntegrations)await openAdminIntegrations(result.adminIntegrations);if(result?.announcementsEditor)await openAnnouncementsSettings();if(result?.domainKnowledge){if(view==='knowledge'){knowledgeDomain=result.domainKnowledge;render();}else openDomainKnowledge(result.domainKnowledge);}if(result?.interpretationResult)openInterpretation(result.interpretationResult);if(result?.integrityReview)openIntegrityReview(result.integrityReview);if(result?.bridgeIssue){view='review';selected=result.bridgeIssue;render();}if(result?.demoDeliveryPreview)openDemoDeliveryPreview(result.demoDeliveryPreview);if(result?.demoDeliveryReceipt)openDemoDeliveryReceipt(result.demoDeliveryReceipt);if(result?.domainObjectives)projectObjectives(result.workRequest?projectTask(result.workRequest):null);if(result?.visualReport)openVisualReport(result.visualReport);if(result?.domainReport)openDomainReport(result.domainReport);if(result?.domainHandoff)domainHandoff(result.domainHandoff);if(result?.prototypePlan)openPrototype(prototypeRows().find(r=>r.ref.id===result.prototypePlan));if(result?.toolImportPreview)toolImportPreview(result.toolImportPreview);if(result?.goalsResult)openGoalsResult(result.goalsResult);if(result?.scaffoldResult)openScaffoldProposal(result.scaffoldResult);if(result?.requirementResult)openRequirementResult(result.requirementResult);if(result?.changeResult)openDocumentChange(result.changeResult);if(result?.sponsorAnalysis)openSponsorAnalysis(result.sponsorAnalysis);}catch(error){d.querySelector('.error').textContent=error.message;d.querySelector('.error').scrollIntoView({block:'nearest'});}finally{busy=false;submit.disabled=false;submit.textContent=priorLabel;if(options.refreshOnIdle)render();}});
 d.showModal();d.scrollTop=0;
}
function closeModal(){if(busy)return;if(typeof reviewerDraftCapture==='function')reviewerDraftCapture();if(dirty&&!confirm('Discard unsaved changes in this form?'))return;dirty=false;$('#modal').close();}
function requirementForm(drawer){const ds=records('requirement-drawer').filter(d=>d.body.status==='active');modal('Create a requirement',`<p class="muted">Capture a proposed requirement. The published intent, boundaries and selected drawer will be linked.</p>${field('title','Short title','','','input')}${ds.length?`<label class="form-field"><span>Requirement drawer</span><select name="drawer_id">${ds.map(d=>`<option value="${esc(d.ref.id)}" ${drawer?.ref.id===d.ref.id?'selected':''}>${esc((d.body.category_label?d.body.category_label+' / ':'')+d.body.label)}</option>`).join('')}</select></label>`:field('drawer','Requirement drawer','Customer experience','','input')}${field('text','What must be true?')}${field('rationale','Why does this matter?',drawer?.body.rationale||'')}<label class="form-field"><span>Acceptance criteria · optional while drafting</span><textarea name="acceptance_criteria" maxlength="20000"></textarea><small>Define or refine these through findings. Criteria are required before requirement approval.</small></label>${field('conditions','Conditions and exclusions',records('policy')[0]?.body.text||'')}`,'Save proposed requirement',async fd=>{const data=Object.fromEntries(fd);if(data.drawer_id)data.drawer=get(data.drawer_id).body.label;const r=await command('requirement',data);view='requirements';selected=r.id;return r;});}
function contributionForm(r){const b=r?.body||{};modal(`${r?'Edit':'New'} ${state.actor==='sam'?'Research':'Operations'} contribution`,`<p class="muted">Save in your team’s working space. You will preview and publish a version separately.</p>${field('title','Title',b.title||'','','input')}${validationFocusField(b)}${field('observation',state.actor==='sam'?'What did you observe?':'What is the operational position or constraint?',b.observation||'')}${field('source','Source reference and relevant excerpt',b.source||'','Record the report, section, date, or observation that supports this contribution. Links are stored as text; nothing is fetched.')}${field('interpretation','What do you think it means?',b.interpretation||'','Optional. Keep interpretation distinct from observation.')}${field('recommendation','What should be considered?',b.recommendation||'','Optional. This is a recommendation, not a decision.')}${field('limitation','Limits, uncertainty, or conditions',b.limitation||'')}${contributionRequirementFields(b)}`,'Save domain draft',async fd=>{const result=await command('contribution',{...Object.fromEntries(fd),requirement_refs:fd.getAll('requirement_ref').map(id=>get(id).ref),expected:r?.ref});view='contributions';selected=null;return result;});}
function publishForm(r){modal('Preview shared contribution',`<div class="banner blue">Everything below will be visible to the sponsor, Research, Operations, and the requirement owner in this project. Remove restricted material before publishing.</div>${val('Title',r.body.title)}${val('Investigation focus',focusLabel(r.body))}${val('Observation / constraint',r.body.observation)}${val('Source reference and excerpt',r.body.source)}${val('Interpretation',r.body.interpretation)}${val('Recommendation',r.body.recommendation)}${val('Limits',r.body.limitation)}${r.body.working_report?'</details>':''}${r.body.handoff?`<details open><summary>Handoff implications and questions</summary><div class="details-body">${val('Prepared for',r.body.recipient)}${Object.entries(r.body.handoff).map(([k,v])=>val(domainFieldLabels[k]||k,v||'Not specified')).join('')}</div></details>`:''}${contributionRequirementLinks(r.body)}<label class="checkbox"><input name="confirm" type="checkbox" required><span>I have reviewed this content and intend to share this version with the project.</span></label>`,'Publish to Decisions & Issues',()=>command('publish',{expected:r.ref,confirm:true}));}
function proposalForm(req,c,sourceId,bridgeIssueContext){
 if(state.intake.setup_governance?.enabled&&state.intake.setup_governance.baseline&&!bridgeIssueContext){navigateWorkspace('review').catch(e=>toast(e.message));toast('Open or raise a Decisions & Issues issue using the relevant published Outcomes reports.');return;}
 const p=c?.body.proposal||req.body, ids=new Set((c?.body.basis||[]).map(r=>r.id));
 if(sourceId)ids.add(sourceId);
 const cons=records('contribution').filter(r=>!bridgeIssueContext||bridgeIssueContext.body.basis.some(raw=>label(raw)===label(r.ref)));
 modal(c?'Revise the shared proposal':'Prepare a shared proposal',`<p class="muted">${c?'Saving creates a new proposal revision and requires fresh team reviews. Earlier responses remain in history.':'Choose the exact contributions that should inform this requirement. Both teams must review the resulting proposal.'}</p><div class="packet-record">${ref(req.ref)}${para(req.body.text)}</div>${field('text','Proposed requirement',p.text||'')}${field('rationale','Why this proposal?',p.rationale||'')}${field('acceptance_criteria','Acceptance criteria',p.acceptance_criteria||'','Describe the observable result, evaluation method and limits. A changed test needs review just as changed wording does.')}${field('conditions','Conditions and exclusions',p.conditions||'')}<h3>Choose the reviewed basis</h3><p class="caption">Select at least one contribution from each domain. Unselected prior contributions will not form part of the new active packet; earlier packets remain intact.</p>${cons.length?cons.map(r=>`<label class="checkbox selectable"><input type="checkbox" name="basis" value="${esc(rid(r))}" ${ids.has(rid(r))?'checked':''}><span><strong>${esc(r.body.domain)} · ${esc(r.body.title||r.body.text)}</strong><small>Version ${esc(r.ref.revision)}</small><span class="pre">${esc(r.body.observation||r.body.text)}</span>${r.body.limitation?`<small>Limits: ${esc(r.body.limitation)}</small>`:''}</span></label>`).join(''):'<div class="banner signal-notice signal-advisory">Publish the relevant Research and Design contributions first.</div>'}${sourceDetails([req.ref,...cons.map(r=>r.ref)])}<label class="checkbox"><input name="within_intent" type="checkbox" required><span>This proposal stays within the current Business Intent and boundaries. If it changes them, I will obtain a separate sponsor decision first.</span></label>`,c?'Save revised proposal':'Submit for team review',async fd=>{const result=await command(bridgeIssueContext?'bridge-propose':'proposal',{...Object.fromEntries(fd),target:req.ref,expected:c?.ref,...(bridgeIssueContext?{expected_issue:bridgeIssueContext.ref}:{}),selected:fd.getAll('basis').map(id=>cons.find(r=>rid(r)===id).ref),changes_intent:false});view='review';selected=result.id;return result;});
}
function reviewForm(c){const research=state.actor==='sam';modal(research?'Record Research’s assessment':state.actor==='lee'?'Record Design’s assessment':'Record Operations’ response',`<div class="packet-record"><div class="caption">Proposal under review · v${esc(c.ref.revision)}</div>${para(c.body.proposal.text)}${val('Conditions',c.body.proposal.conditions)}${sourceDetails([c.ref,c.body.target,...(c.body.basis||[])])}</div><label class="form-field"><span>${research?'What does the evidence support?':'Does the proposal respect the domain evidence and constraints?'}</span><select name="disposition"><option value="">Choose a response</option>${research?'<option value="supported-with-limits">Supported within its stated limits</option><option value="needs-more-evidence">More evidence is needed</option>':'<option value="cleared-with-conditions">Acceptable with the stated conditions</option><option value="not-cleared">Domain concerns remain unresolved</option>'}</select></label>${field('rationale','Explain your assessment','','Be specific about scope, uncertainty, or the concern that must be resolved.')}<p class="caption">This records a domain review. It does not approve the requirement.</p>`,'Save my review',fd=>command('review',{expected:c.ref,...Object.fromEntries(fd)}));}
function decisionForm(c){
 modal('Record the requirement decision',`<div class="packet-record">${ref(c.ref)}${para(c.body.proposal.text)}${val('Acceptance criteria',c.body.proposal.acceptance_criteria)}${val('Conditions',c.body.proposal.conditions)}${sourceDetails([c.ref,c.body.target,...(c.body.basis||[])])}</div>${!c.ready?'<div class="banner signal-notice signal-critical">Approval unavailable: approval requires supportive reviews, a current basis and no unresolved intent refinement affecting this requirement. You can still defer or reject.</div>':''}<label class="form-field"><span>Decision</span><select name="disposition" id="disposition"><option value="defer">Defer — request a next step</option><option value="approve" ${c.ready?'':'disabled'}>Approve this requirement</option><option value="reject">Reject this proposal</option></select></label>${field('rationale','Why this decision?')}<div id="defer-fields"><label class="form-field"><span>Who responds next?</span><select name="next_owner">${Object.entries(state.actors).filter(([id])=>id!=='administrator').map(([id,a])=>`<option value="${id}">${esc(a.name)} · ${esc(a.role)}</option>`).join('')}</select></label>${field('next_question','What question must they answer?')}</div><div id="approval-fields" hidden><label class="checkbox"><input name="confirm" type="checkbox"><span>I approve this exact wording, acceptance criteria, and conditions. This does not authorize execution or establish fulfillment.</span></label></div>`,'Save decision',fd=>command('decision',{...Object.fromEntries(fd),expected:c.ref,confirm:fd.get('confirm')==='on'}));
 const update=()=>{const d=$('#disposition').value;$('#defer-fields').hidden=d!=='defer';$('#defer-fields textarea').required=d==='defer';$('#approval-fields').hidden=d!=='approve';$('#approval-fields input').required=d==='approve';};$('#disposition').addEventListener('change',update);update();
}


document.addEventListener('click',async e=>{
 if(busy)return;
 const nav=e.target.closest('[data-nav]');if(nav){if(nav.tagName==='A')e.preventDefault();try{await navigateWorkspace(nav.dataset.nav);}catch(error){toast(error.message);}return;}
 if(e.target.closest('[data-close]')){closeModal();return;}
 const el=e.target.closest('[data-action]');if(!el)return;const {action,id}=el.dataset;
 if(el.tagName==='A')e.preventDefault();
 try{
  if(action==='app-menu'){toggleProjectNavigation();return;}
  if(typeof caseAction==='function'&&await caseAction(action,id))return;
  if(typeof cockpitAction==='function'&&await cockpitAction(action,id))return;
  if(typeof meaningAction==='function'&&await meaningAction(action,id))return;
  if(typeof enterpriseAction==='function'&&await enterpriseAction(action,id))return;
  if(typeof decisionRightsAction==='function'&&await decisionRightsAction(action,id))return;
  if(typeof myFilesAction==='function'&&await myFilesAction(action,id))return;
  if(action==='portfolio-access'){await portfolioAccessSettings();return;}
  if(typeof thoughtPartnerAction==='function'&&await thoughtPartnerAction(action,id))return;
  if(typeof projectLeaveObjectiveEdits==='function'&&!projectLeaveObjectiveEdits(action))return;
  if(typeof saveWorkingReportBeforeAction==='function')await saveWorkingReportBeforeAction(action);
  if(typeof integrityGapAction==='function'&&await integrityGapAction(action,id))return;
  if(typeof domainDevelopmentAction==='function'&&await domainDevelopmentAction(action,id))return;
  if(typeof workingReportAction==='function'&&await workingReportAction(action,id))return;
  if(typeof demoDeliveryAction==='function'&&await demoDeliveryAction(action,id))return;
  if(typeof projectFlowAction==='function'&&await projectFlowAction(action,id))return;
  if(typeof requirementAssessmentAction==='function'&&await requirementAssessmentAction(action,id))return;
  if(typeof domainKnowledgeAction==='function'&&await domainKnowledgeAction(action,id))return;
  if(typeof interpretationAction==='function'&&await interpretationAction(action,id))return;
  if(typeof domainChatAction==='function'&&await domainChatAction(action,id))return;
  if(await designVisualAction(action,id))return;
  if(await homeAction(action,id))return;
  if(await sponsorAction(action,id,el))return;
  if(await deliveryAction(action,id))return;
  if(await accountAction(action,id))return;
  if(await bridgeAction(action,id))return;
  if(await preflightAction(action,id))return;
  if(await domainAction(action,id))return;
  if(await documentChangeAction(action,id))return;
  if(await settingsAction(action,id))return;
  if(await scaffoldTailoringAction(action,id))return;
  if(typeof requirementEntryAction==='function'&&await requirementEntryAction(action,id))return;
  if(await goalsAction(action,id))return;
  if(await fieldCoachAction(action,id))return;
  if(await requirementAgentAction(action,id))return;
  if(await projectAction(action,id))return;
  if(await valueAction(action,id))return;
  if(await coachingAction(action,id))return;
  if(await refinementAction(action,id))return;
  if(await intakeAction(action,id))return;
  if(action==='refresh'){await load();render();toast('Current versions loaded');}
  else if(action==='requirement')await openRequirementSection(requirementsMode,id);
  else if(action==='requirement-discuss'){const question=$('#field-coach-question');if(question){question.focus();question.scrollIntoView({block:'nearest'});}}
  else if(action==='case'){view='review';selected=id;render();}
  else if(action==='back-requirements')await openRequirementSection();
  else if(action==='back-review'){view='review';selected=null;render();}
  else if(action==='requirements-mode')await openRequirementSection(id);
  else if(action==='new-requirement')requirementForm();
  else if(action==='new-contribution')contributionForm();
  else if(action==='edit-contribution')contributionForm(get(id));
  else if(action==='read-contribution'){const r=get(id);modal(r.body.title||'Domain contribution',`<p class="caption">Version ${esc(r.ref.revision)}</p>${sourceDetails(r.ref)}<div class="section">${typeof workingReportRead==='function'?workingReportRead(r.body):''}${r.body.working_report?'<details><summary>Supporting deliverable notes</summary>':''}${val('Observation / constraint',r.body.observation||r.body.text)}${val('Source reference and excerpt',r.body.source)}${val('Interpretation',r.body.interpretation)}${val('Recommendation',r.body.recommendation)}${val('Limits',r.body.limitation)}${r.body.working_report?'</details>':''}${r.body.handoff?`<details open><summary>Handoff implications and questions</summary><div class="details-body">${val('Prepared for',r.body.recipient)}${Object.entries(r.body.handoff).map(([k,v])=>val(domainFieldLabels[k]||k,v||'Not specified')).join('')}</div></details>`:''}${contributionRequirementLinks(r.body)}${findingActions(r)}</div>`);}
  else if(action==='publish')publishForm(get(id));
  else if(action==='proposal')proposalForm(get(id));
  else if(action==='revise'){const c=findCase(id);proposalForm(get(c.body.target.id),c);}
  else if(action==='review-form')reviewForm(findCase(id));
  else if(action==='decision-form')decisionForm(findCase(id));
  else if(action==='packet')inspectPacket(id);
  else if(action==='evidence-select'){evidenceSelected=id;render();if(typeof compact!=='undefined'&&compact)document.getElementById('evidence-detail-title')?.scrollIntoView({block:'start'});}
  else if(action==='evidence-team'){evidenceTeamFilter=id;render();}
  else if(action==='accountability-issue-filter'){accountabilityIssueFilter=id;render();}
  else if(action==='knowledge-tab'){knowledgeDomain=id;knowledgeEntry=null;render();}
  else if(action==='knowledge-type'){knowledgeType=id;knowledgeEntry=null;render();}
  else if(action==='knowledge-select'){knowledgeEntry=id;render();if(typeof compact!=='undefined'&&compact)document.getElementById('knowledge-detail-title')?.scrollIntoView({block:'start'});}
 else if(action==='need-context')inspectNeedContext(id);
  else if(action==='about')modal('About Adaptive Cointelligence',aboutContent());
 }catch(error){toast(error.message);}
});
document.addEventListener('change',async e=>{if(e.target.matches('[data-bridge-select]')){if(busy){e.target.value=bridgeBoard;return;}try{const action=e.target.dataset.bridgeSelect;if(action==='bridge-board')await bridgeAction(action,e.target.value);else if(action==='pflow-brief-board')await projectFlowAction(action,e.target.value);const selector=$('#bridge-board-filter');if(selector){selector.value=bridgeBoard;selector.focus();}}catch(error){toast(error.message);}return;}if(e.target.id==='workspace-view'){const prior=view;if(busy){e.target.value=prior;return;}try{await saveBeforeProjectChange();selectWorkspaceView(e.target.value);render();}catch(error){e.target.value=prior;toast(error.message);}return;}if(e.target.id==='profile')await switchPreviewUser(e.target.value,e.target);});
document.addEventListener('submit',async e=>{if(e.target.id==='setup-form'){e.preventDefault();const b=e.submitter;b.disabled=true;try{const r=await command('setup',Object.fromEntries(new FormData(e.target)));await load();render();toast(r.message);}catch(error){e.target.querySelector('.error').textContent=error.message;}finally{b.disabled=false;}}});
$('#modal').addEventListener('cancel',e=>{e.preventDefault();closeModal();});
window.addEventListener('beforeunload',e=>{if(dirty||pageDirty||typeof hasUnsavedDevelopmentEditors==='function'&&hasUnsavedDevelopmentEditors()||typeof hasUnsavedSubmission==='function'&&hasUnsavedSubmission()||typeof hasUnsavedWorkingReport==='function'&&hasUnsavedWorkingReport()){e.preventDefault();e.returnValue='';}else if(state?.project)rememberProjectView();});
startAccountApp().catch(error=>{$('#app').innerHTML=`<div class="welcome card section"><h1>Could not open the workbench</h1>${para(error.message)}<p>Start <code>workbench-web</code> in Terminal, then reload this page.</p></div>`;});

window.addEventListener('resize',()=>{syncNavigationButton();if(!compactNavigation()&&$('#modal')?.classList.contains('navigation-dialog')&&$('#modal').open)closeModal();});
document.addEventListener('close',syncNavigationButton,true);

document.addEventListener('toggle',e=>{if(e.target.matches('details.business-development-nav')&&e.target.isConnected)businessDevelopmentOpen=e.target.open;},true);

// Size adjacent reviewers against the actual work surface and visible viewport.
// This changes only layout: no saves, focus changes or replacement of editor DOM.
function reviewerPanelHeight(referenceBottom,panelTop,viewportHeight,headerBottom){
 const top=Math.max(panelTop,headerBottom+16);
 return Math.floor(Math.min(Math.max(referenceBottom-panelTop,400),viewportHeight-top-16));
}
(function observeReviewerLayout(){
 if(typeof MutationObserver==='undefined'||typeof ResizeObserver==='undefined')return;
 let scheduled=false;const watched=new Set();
 const schedule=()=>{if(!scheduled){scheduled=true;requestAnimationFrame(update);}};
 const observer=new ResizeObserver(schedule);
 function update(){
  scheduled=false;
  for(const el of watched)if(!el.isConnected){observer.unobserve(el);watched.delete(el);}
  const headerBottom=document.querySelector('.ws-app-header')?.getBoundingClientRect().bottom||0;
  document.querySelectorAll('.sponsor-coach,.domain-working-layout>.chat-console,.field-coach,.coach-panel,.personal-chat-console,[data-integrity-review-panel]').forEach(panel=>{
   const parent=panel.parentElement;
   const reference=panel.matches('.personal-chat-console')?null:panel.matches('.field-coach')?
    parent.querySelector(':scope > .field-coach-work,:scope > form'):panel.matches('.coach-panel')?
    parent.querySelector(':scope > form'):parent.querySelector('.sponsor-question-work,.sponsor-framing-editor,.domain-context-panel,.chat-findings,[data-review-work]');
   const a=panel.getBoundingClientRect(),b=reference?.getBoundingClientRect();
   if(reference&&!watched.has(reference)){watched.add(reference);observer.observe(reference);}
   const beside=b?(a.right<=b.left||a.left>=b.right):panel.matches('.personal-chat-console,[data-integrity-review-panel]')||parent.matches('.domain-working-layout');
   const height=beside?reviewerPanelHeight(b?.bottom??Infinity,a.top,window.innerHeight,headerBottom):0;
   if(height>=220){
    const value=height+'px';if(panel.style.getPropertyValue('--reviewer-panel-height')!==value)panel.style.setProperty('--reviewer-panel-height',value);
    panel.classList.add('reviewer-viewport-fit');
   }else{panel.style.removeProperty('--reviewer-panel-height');panel.classList.remove('reviewer-viewport-fit');}
  });
 }
 new MutationObserver(schedule).observe(document.querySelector('#app'),{childList:true,subtree:true});
 window.addEventListener('resize',schedule);window.addEventListener('scroll',schedule,{passive:true});
 window.visualViewport?.addEventListener('resize',schedule);schedule();
})();

// Personal layout controls. These never save project content or request a model.
(function reviewerWidthControls(){
 if(typeof MutationObserver==='undefined'||typeof ResizeObserver==='undefined'||!document.createElement)return;
 const entries=new Set();let queued=false,drag=null;
 const schedule=()=>{if(!queued){queued=true;requestAnimationFrame(update);}};
 const resize=new ResizeObserver(schedule);
 const clamp=(n,min,max)=>Math.round(Math.max(min,Math.min(max,n)));
 const kind=p=>p.matches('dialog')?'review-dialog':p.matches('.sponsor-framing-review')?'business-intent':p.matches('.sponsor-coach')?'project-framing':p.matches('.field-coach')?'field-guidance':p.matches('.coach-panel')?'intake':p.matches('.personal-chat-console')?'general':'domain';
 function key(p){return 'workbench-review-width:v1:'+encodeURIComponent(state.auth?.account?.id||state.actor||'local')+':'+encodeURIComponent(state.actor||'local')+':'+kind(p);}
 function bounds(e){
  const p=e.panel,parent=p.parentElement,box=parent.getBoundingClientRect();
  if(e.mode==='dialog')return{min:Math.min(360,window.innerWidth-32),max:window.innerWidth-32};
  if(e.mode==='domain'){
   const b=domainSplitBounds(e.domainHandle);return{min:Math.ceil(b.min*b.width/100),max:Math.floor(b.max*b.width/100)};
  }
  if(e.mode==='standalone')return{min:Math.min(340,box.width),max:box.width};
  const resources=parent.querySelector(':scope > .sponsor-resources'),resourceWidth=resources?(window.innerWidth<=1180?220:260):0;
  parent.style.setProperty('--reviewer-resource-width',resourceWidth+'px');
  const available=box.width-resourceWidth-(resources?32:16);
  return{min:Math.min(260,available/2),max:Math.max(available/2,available-300)};
 }
 function apply(e,value,save=false){
  const b=bounds(e),n=clamp(value,b.min,b.max),p=e.panel;
  if(e.mode==='domain'){
   const geometry=domainSplitBounds(e.domainHandle);domainSplitApply(e.domainHandle,n/geometry.width*100);if(save)domainSplitSave(Number(e.domainHandle.getAttribute('aria-valuenow')));
  }else if(e.mode==='column')p.parentElement.style.setProperty('--reviewer-width',n+'px');
  else if(e.mode==='dialog')p.style.setProperty('--reviewer-dialog-width',n+'px');
  else p.style.setProperty('--reviewer-standalone-width',n+'px');
  e.range.min=String(Math.ceil(b.min));e.range.max=String(Math.floor(b.max));e.range.value=String(n);
  if(e.output.textContent!==n+' px')e.output.textContent=n+' px';
  if(e.handle){e.handle.setAttribute('aria-valuemin',e.range.min);e.handle.setAttribute('aria-valuemax',e.range.max);e.handle.setAttribute('aria-valuenow',String(n));}
  if(save){e.requested=n;try{localStorage.setItem(e.key,String(n));}catch{}}
  return n;
 }
 function mount(panel){
  const previous=[...entries].find(e=>e.panel===panel);
  if(previous?.control.isConnected)return previous;
  if(previous){previous.handle?.remove();entries.delete(previous);}
  const parent=panel.parentElement,domainHandle=parent.querySelector(':scope > .domain-panel-resize');
  const mode=panel.matches('dialog')?'dialog':domainHandle?'domain':panel.matches('.personal-chat-console')||panel.matches('.chat-console')&&!parent.querySelector(':scope > .domain-context-panel,:scope > .chat-findings')?'standalone':'column';
  const control=document.createElement('details');control.className='reviewer-width-control';
  control.innerHTML='<summary title="Adjust AI partner width"><span aria-hidden="true">↔</span><span class="sr-only">Adjust AI partner width</span></summary><div class="reviewer-width-popover"><label>Review width <input type="range" min="260" max="800" step="1" aria-label="AI partner width"></label><div><output></output><button type="button">Reset</button></div></div>';
  let host=panel.querySelector('.sponsor-coach-title,.chat-console>header,.dialog-head');
  if(!host&&panel.matches('.personal-chat-console'))host=panel.closest('main')?.querySelector('.page-head');
  if(!host){const title=panel.querySelector('.thought-partner-title');host=document.createElement('div');host.className='reviewer-width-heading';if(title){title.before(host);host.append(title);}else panel.prepend(host);}
  host.classList.add('reviewer-width-host');
  if(host.matches('.dialog-head'))host.insertBefore(control,host.lastElementChild);else host.append(control);
  const e={panel,parent,mode,domainHandle,control,range:control.querySelector('input'),output:control.querySelector('output'),key:key(panel),defaultWidth:panel.getBoundingClientRect().width,requested:null};
  try{const value=localStorage.getItem(e.key);if(value!==null&&Number.isFinite(Number(value))&&Number(value)>0)e.requested=Number(value);}catch{}
  if(mode==='column'){
   const handle=document.createElement('div');handle.className='reviewer-column-resize';handle.tabIndex=0;handle.setAttribute('role','separator');handle.setAttribute('aria-label','Resize AI partner column');handle.setAttribute('aria-orientation','vertical');handle.title='Drag to resize · double-click to reset';handle.innerHTML='<span aria-hidden="true"></span>';parent.append(handle);e.handle=handle;
   handle.addEventListener('pointerdown',event=>{if(event.button!==0)return;event.preventDefault();handle.focus();drag={entry:e,start:event.clientX,width:Number(e.range.value),pointer:event.pointerId};handle.setPointerCapture?.(event.pointerId);document.body.classList.add('reviewer-column-resizing');});
   handle.addEventListener('keydown',event=>{const delta=event.shiftKey?32:8,b=bounds(e),old=Number(e.range.value),next=event.key==='ArrowLeft'?old+delta:event.key==='ArrowRight'?old-delta:event.key==='Home'?b.min:event.key==='End'?b.max:null;if(next!==null){event.preventDefault();apply(e,next,true);schedule();}});
   handle.addEventListener('dblclick',()=>reset(e));
  }
  if(mode==='standalone')panel.classList.add('reviewer-width-standalone');
  if(mode==='dialog')panel.classList.add('reviewer-width-dialog');
  e.range.addEventListener('input',()=>{e.requested=Number(e.range.value);apply(e,e.requested);schedule();});
  e.range.addEventListener('change',()=>apply(e,Number(e.range.value),true));
  control.querySelector('button').addEventListener('click',()=>reset(e));
  entries.add(e);resize.observe(parent);return e;
 }
 function reset(e){e.requested=null;try{localStorage.removeItem(e.key);}catch{}apply(e,e.defaultWidth);schedule();}
 function update(){
  queued=false;
  for(const e of entries)if(!e.panel.isConnected){e.handle?.remove();entries.delete(e);}
  document.querySelectorAll('.sponsor-coach,.domain-working-layout>.chat-console,.field-coach,.coach-panel,.personal-chat-console,dialog[open]:has(.dialog-head .thought-partner-title)').forEach(panel=>{
   const e=mount(panel),parent=panel.parentElement;
   if(e.mode==='column'){
    const work=parent.querySelector(':scope > .sponsor-question-work,:scope > .sponsor-framing-editor,:scope > form,:scope > .field-coach-work');
    const a=panel.getBoundingClientRect(),b=work?.getBoundingClientRect(),beside=b&&(a.left>=b.right||a.right<=b.left);
    e.control.hidden=!beside;e.handle.hidden=!beside;parent.classList.toggle('reviewer-width-layout',!!beside);
    if(!beside)return;
   }
   if(e.mode==='domain'){
    const b=e.domainHandle.getBoundingClientRect();e.control.hidden=b.width===0;if(e.control.hidden)return;
   }
   const width=e.mode==='domain'&&e.initialized?Number(e.domainHandle.getAttribute('aria-valuenow'))*domainSplitBounds(e.domainHandle).width/100:e.requested??e.defaultWidth;
   apply(e,width);e.initialized=true;
   if(e.handle){const a=panel.getBoundingClientRect(),b=parent.getBoundingClientRect();e.handle.style.left=(a.left-b.left-8)+'px';e.handle.style.top=Math.max(0,a.top-b.top)+'px';}
  });
 }
 function end(commit){if(!drag)return;const e=drag.entry;if(commit)apply(e,Number(e.range.value),true);else{e.requested=drag.width;apply(e,drag.width);}drag=null;document.body.classList.remove('reviewer-column-resizing');}
 document.addEventListener('pointermove',event=>{if(!drag||event.pointerId!==drag.pointer)return;event.preventDefault();drag.entry.requested=drag.width+drag.start-event.clientX;apply(drag.entry,drag.entry.requested);schedule();});
 document.addEventListener('pointerup',()=>end(true));document.addEventListener('pointercancel',()=>end(false));
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&drag){event.preventDefault();end(false);}});
 window.addEventListener('blur',()=>end(false));window.addEventListener('resize',schedule);
 const mutations=new MutationObserver(schedule);mutations.observe(document.querySelector('#app'),{childList:true,subtree:true});const dialog=document.querySelector('#modal');if(dialog)mutations.observe(dialog,{childList:true,subtree:true});schedule();
})();

// Project home: where the project stands across intent, investigation, alignment and delivery,
// what is waiting on this person, and what changed. Read-only; every number comes from loaded records.
function projectHomeLatest(kind){const m=new Map();for(const r of records(kind))if(!m.has(r.ref.id)||m.get(r.ref.id).ref.revision<r.ref.revision)m.set(r.ref.id,r);return [...m.values()];}
function projectHomeDate(at){const t=new Date(at);return isNaN(t)?'':t.toLocaleDateString(undefined,{day:'numeric',month:'short'});}
function projectHomeNav(target){const names=workspaceNavigation();if(target==='delivery'&&!['priya','alex'].includes(state.actor))target='requirements';if(target==='intent'&&state.domains?.active)return 'data-action="nav-domain" data-id="project|intent"';if(names[target])return `data-nav="${target}"`;if(['intent','delivery'].includes(target))return `data-action="nav-domain" data-id="project|${target}"`;return 'data-nav="review"';}
function projectHomeNeeds(){
 const me=state.actor,out=[];
 for(const i of state.bridge?.issues||[]){const b=i.body||{};if(['resolved','closed','withdrawn'].includes(b.status))continue;const reviews=b.required_reviews||{},mine=b.next_owner===me||(b.next_owner==null&&b.owner===me)||Object.entries(reviews).some(([who,done])=>who===me&&!done);if(mine)out.push({label:'Issue',title:b.title||i.ref.id,detail:b.next_question||'',attrs:`data-action="bridge-open" data-id="${esc(i.ref.id)}"`});}
 for(const c of state.intake?.cases||[]){const b=c.body||{};if(['published','withdrawn','closed'].includes(b.status))continue;const reviewers=b.reviewers||b.decision_rights?.reviewers||[];if(reviewers.includes(me)&&!(b.reviews||[]).some(r=>(r.actor?.id||r.actor||r.reviewer)===me))out.push({label:'Review',title:'Business Intent ready for your review',detail:'',attrs:projectHomeNav('intent')});else if(b.decision_owner===me&&b.status!=='draft')out.push({label:'Decide',title:'Business Intent decision',detail:'Reviews requested '+projectHomeDate(b.requested_at),attrs:projectHomeNav('intent')});}
 for(const c of state.cases||[]){const b=c.body||{};if(c.kind!=='decision-case'||['approved','rejected','withdrawn','closed'].includes(b.status))continue;const open=`data-action="case" data-id="${esc(c.ref.id)}"`,title=c.target_record?.body?.title||b.proposal?.title||'';if(b.decision_owner===me)out.push({label:'Decide',title:title||'Requirement decision',detail:'',attrs:open});else if(Object.keys(b.required_reviews||{}).includes(me)&&!(b.reviews||{})[me])out.push({label:'Review',title:title||'Requirement proposal',detail:'',attrs:open});}
 for(const p of state.enterprise?.proposals||[])if(p.mine?.length)out.push({label:'Decide',title:typeof enterpriseProposalTitle==='function'?enterpriseProposalTitle(p):'Wider reach',detail:p.reason||'',attrs:state.enterprise.can_view?'data-action="enterprise-open"':'data-nav="knowledge"'});
 for(const i of state.meaning?.items||[])if(i.mine?.length)out.push({label:'Decide',title:typeof meaningSentence==='function'?meaningSentence(i):'Meaning proposal',detail:i.reason||'',attrs:'data-nav="knowledge"'});
 return out;
}
function projectHome(){
 if(typeof caseOpenArea!=='undefined'&&caseOpenArea)return caseAreaScreen();
 const p=state.project||{},actors=state.actors||{},intents=records('intent'),intentRev=intents.length?Math.max(...intents.map(r=>r.ref.revision)):0,published=!!state.intake?.published;
 const refinement=projectHomeLatest('intent-refinement').sort((a,b)=>b.ref.revision-a.ref.revision)[0];
 const contributions=projectHomeLatest('contribution').filter(r=>r.body?.domain&&!String(r.ref.id).startsWith('CON-DEVBRIEF')),byTeam=new Map();for(const r of contributions){const d=r.body.domain;byTeam.set(d,(byTeam.get(d)||0)+r.ref.revision);}
 const issues=state.bridge?.issues||[],open=issues.filter(i=>!['resolved','closed','withdrawn'].includes(i.body?.status)),resolved=issues.length-open.length;
 const decided=(state.cases||[]).filter(c=>c.kind==='decision-case'&&c.body?.status==='approved'),req=decided[0]?.body?.result_requirement,delivery=state.demo_delivery||{},staged=(delivery.previews||[]).length;
 const sponsor=actors[(state.intake?.cases||[])[0]?.body?.requested_by||'priya']?.name;
 const stage=(n,title,status,tone,detail,attrs)=>`<a href="#main" class="home-stage-card" ${attrs}><span class="home-stage-step">${n} · ${esc(title)}</span><span class="home-stage-status tone-${tone}">${esc(status)}</span><span class="home-stage-detail">${detail}</span></a>`;
 const stages=[
  stage(1,'Intent',intentRev?(intentRev>1?`Revised · v${intentRev}`:`Published · v${intentRev}`):published?'Published':'Not published','',intentRev>1&&refinement?`Changed from a finding by ${esc(actors[refinement.body?.requested_by]?.name||'a domain team')}. Earlier versions are kept.`:intentRev?'The starting direction every team works from.':'The sponsor has not published Business Intent yet.',projectHomeNav('intent')),
  stage(2,'Investigate',byTeam.size?`${byTeam.size} team${byTeam.size===1?'':'s'} contributing`:'Not started',byTeam.size?'':'muted',byTeam.size?[...byTeam.entries()].map(([d,n])=>`${esc(d)}: ${n} version${n===1?'':'s'} shared`).join('<br>'):'Shared findings from Research and Design appear here.','data-nav="packets"'),
  stage(3,'Align',open.length?`${open.length} open issue${open.length===1?'':'s'}`:'No open issues',open.length?'warn':'ok',issues.length?`${resolved} resolved${open[0]?`<br>Open: ${esc(open[0].body?.title||'')}`:''}`:'Dependencies, contradictions and gaps between teams appear here.','data-nav="review"'),
  stage(4,'Deliver',decided.length?`${decided.length} requirement${decided.length===1?'':'s'} approved`:'Nothing approved yet',decided.length?'ok':'muted',decided.length?`${req?'Requirement v'+req.revision+' approved. ':''}${staged?`${staged} item${staged===1?'':'s'} staged for Jira and Azure DevOps.${delivery.mode==='simulated'?' Simulated; nothing sent.':''}`:''}`:'Approved requirements and handoff items appear here.',projectHomeNav('delivery'))
 ];
 const needs=projectHomeNeeds(),seen=new Set(),items=[...(state.bridge?.team_timeline?.items||[])].sort((a,b)=>String(b.end_at||b.start_at).localeCompare(String(a.end_at||a.start_at))).filter(i=>{const k=(i.title||'')+'|'+(i.owner||'');if(seen.has(k))return false;seen.add(k);return true;}).slice(0,6);
 const goals=projectHomeLatest('goal'),measures=projectHomeLatest('success-measure');
 const people=Object.entries(actors).filter(([k])=>!['administrator','maya'].includes(k));
 return `<div class="page-head project-home-head"><div><h1 tabindex="-1">${esc(p.title||'Untitled project')}</h1><p class="project-home-sub">${sponsor?`Sponsor ${esc(sponsor)}`:''}${/synthetic/i.test(p.title||'')?' · Synthetic demonstration project':''}</p></div></div>
 ${needs.length?`<section class="home-waiting" aria-labelledby="home-needs"><h2 id="home-needs">Waiting on you <span class="workbench-count is-accent">${needs.length}</span></h2><ul class="home-needs-list">${needs.map(n=>`<li><a href="#main" ${n.attrs}><span class="ac-state ${n.label==='Decide'?'ac-state-edited':'ac-state-suggested'}">${esc(n.label)}</span><span class="home-need-title">${esc(n.title)}</span>${n.detail?`<span class="home-need-detail">${esc(n.detail)}</span>`:''}</a></li>`).join('')}</ul></section>`:''}
 ${typeof caseBoard==='function'?caseBoard():''}
 <p class="case-section-title">07 · At the table</p>
 <div class="project-home-grid"><div class="project-home-main">
  <section class="card project-home-section" aria-labelledby="home-changes"><div class="project-home-section-head"><h2 id="home-changes">What changed</h2><a href="#main" data-nav="review">Full history</a></div>${items.length?`<ol class="home-changes">${items.map(i=>`<li><span class="home-change-date">${esc(projectHomeDate(i.end_at||i.start_at))}</span><span class="home-change-body"><button type="button" class="home-change-title" data-action="${esc(i.action||'')}" data-id="${esc(i.action_id||'')}">${esc(String(i.title||'').replace(/\s*\(synthetic\)$/i,''))}</button><span class="home-change-meta">${esc([i.owner_name,i.status].filter(Boolean).join(' · '))}</span></span></li>`).join('')}</ol>`:'<p class="caption">Shared work and decisions will appear here.</p>'}</section>
 </div><aside class="project-home-side">
  <section class="card project-home-section" aria-labelledby="home-people"><h2 id="home-people">People</h2><ul class="home-people">${people.map(([k,a])=>`<li><span class="home-avatar" aria-hidden="true">${esc((a.name||'?').split(' ').map(x=>x[0]).join('').slice(0,2))}</span><span><strong>${esc(a.name)}</strong><small>${esc(a.role)}</small></span></li>`).join('')}</ul></section>
 </aside></div>`;
}

// D003 shared suggestion states. Presentation only: the apply, dismiss and save actions stay with each feature.
function acSuggestionHead(origin,state='suggested'){const label={suggested:'Suggested',used:'Used in your draft · save to keep',validated:'Validated'}[state]||'Suggested';return `<div class="ac-suggestion-head"><span class="ac-state ac-state-${state==='used'?'edited':state}">${esc(label)}</span>${origin?`<span class="ac-origin">${esc(origin)}</span>`:''}</div>`;}

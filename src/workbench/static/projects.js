// Project identity and generation are explicit on every request. UI draft caches
// are keyed by both, so an old question or suggestion cannot leak into a reset.
let currentProjectId;
try{currentProjectId=sessionStorage.getItem('workbench-project')||'original';}catch{currentProjectId='original';}
const projectViews=new Map();
function projectControl(){return `<div class="ui-selector-field project-switcher"><label class="ui-control-label" for="project-picker">Project</label><div class="ui-selector-wrap"><button id="project-picker" type="button" class="ui-selector project-picker" data-action="projects" aria-haspopup="dialog" aria-controls="modal" aria-label="Change project: ${esc(state.project.title||'Project')}" title="${esc(state.project.title||'Project')}"><span class="project-picker-name">${esc(state.project.title)}</span></button>${selectorChevron()}</div></div>`;}
function projectCacheKey(){return `workbench-view:${state.auth?.account?.id||state.actor}:${state.project.id}:${state.project.version}`;}
function rememberProjectView(){
 if(['projects','thought-partner','overview'].includes(view))return; // Dashboard and retired overview cannot replace the last working location.
 const cache={view,selected,requirementsMode,intakeStep,intakeCaseId,valueReview,valueFocus,valueCoachMode,valueMessage,
  valueOpen:[...valueOpen],valueCandidateEdits:{...valueCandidateEdits},valueDismissed:[...valueDismissed],
  valueNavigationOpen,valueNavigationFocus,coachedField,chosenSources:[...chosenSources],sourcesOpen,coachingMessages:{...coachingMessages},...(typeof bridgeSection!=='undefined'?{bridge:{section:bridgeSection,board:typeof bridgeBoard!=='undefined'?bridgeBoard:null}}:{}),...(typeof domainWorkMode!=='undefined'?{domainWork:{mode:domainWorkMode,rail:typeof domainChatRail!=='undefined'?domainChatRail:'requirements'}}:{}),...(typeof sponsorStage!=='undefined'?{sponsor:{stage:sponsorStage,question:sponsorQuestion,fit:sponsorFit,resources:sponsorResources}}:{})};
 projectViews.set(projectCacheKey(),cache);
 try{sessionStorage.setItem(projectCacheKey(),JSON.stringify(cache));}catch{/* In-memory view remains available. */}
}
function resetProjectView(){
 if(typeof setupDraftPreviewProject!=='undefined')setupDraftPreviewProject=null;
 if(typeof sponsorStage!=='undefined'){sponsorStage='framing';sponsorQuestion='q2';sponsorFit=false;sponsorCoachResult=null;if(typeof sponsorResources!=='undefined')sponsorResources='questions';}
 if(typeof bridgeBoard!=='undefined'){bridgeBoard='research-design';bridgeSection='overview';}
 if(typeof domainWorkMode!=='undefined')domainWorkMode='conversation';
 if(typeof domainChatRail!=='undefined')domainChatRail='requirements';
 if(typeof domainChatPreview!=='undefined')domainChatPreview=null;
 if(typeof sharedReportFocus!=='undefined')sharedReportFocus=null;
 view=state?.domains?.active?'contributions':'intent';selected=null;requirementsMode='scaffold';dirty=false;pageDirty=false;
 intakeStep='rationale';intakeCaseId=null;valueReview=false;valueFocus='business_challenge';valueCoachMode='question';
 valueMessage='';valueWorking={};valueOpen=new Set(['reason']);valueCandidateEdits={};valueDismissed=new Set();
 valueNavigationOpen=true;valueNavigationFocus=null;coachedField='business_challenge';chosenSources=new Set();
 sourcesOpen=false;coachingMessages={};coachingWorking={};
}
function restoreProjectView(){
 if(typeof setupDraftPreviewProject!=='undefined')setupDraftPreviewProject=null;
 resetProjectView();
 let cache=projectViews.get(projectCacheKey());
 try{cache??=JSON.parse(sessionStorage.getItem(projectCacheKey())||'null');}catch{/* Use the initial question. */}
 if(!cache)return;
 ({view,selected,requirementsMode,intakeStep,intakeCaseId,valueReview,valueFocus,valueCoachMode,valueMessage,
  valueCandidateEdits,valueNavigationOpen,valueNavigationFocus,coachedField,sourcesOpen,coachingMessages}=cache);
 if(typeof sponsorStage!=='undefined'&&cache.sponsor){const s=cache.sponsor;sponsorStage=['framing','brief','planning','review'].includes(s.stage)?s.stage:'framing';sponsorQuestion=state.sponsor?.questions.some(q=>q.id===s.question)?s.question:'q2';sponsorFit=!!s.fit;if(typeof sponsorResources!=='undefined')sponsorResources=s.resources==='documents'?'documents':'questions';}
 if(view==='overview'||view==='projects'){view=state.domains?.active?'contributions':'intent';selected=null;}
 if(typeof bridgeSection!=='undefined'&&cache.bridge){
  bridgeSection=['overview','boards','assignments','work','reviews','timeline','activity'].includes(cache.bridge.section)?cache.bridge.section:'overview';
  if(typeof bridgeBoard!=='undefined'&&state.bridge?.boards?.[cache.bridge.board])bridgeBoard=cache.bridge.board;
 }
 if(typeof domainWorkMode!=='undefined'&&cache.domainWork)domainWorkMode=cache.domainWork.mode==='working'?'working':'conversation';
 if(typeof domainChatRail!=='undefined'&&cache.domainWork)domainChatRail=cache.domainWork.rail==='report'?'report':'requirements';
 valueOpen=new Set(cache.valueOpen);valueDismissed=new Set(cache.valueDismissed);chosenSources=new Set(cache.chosenSources);
}
function drawerValues(form){return Array.from(form.querySelectorAll('.drawer-edit')).map(el=>({key:el.dataset.key,included:el.querySelector('[name="included"]').checked,...Object.fromEntries(Array.from(el.querySelectorAll('input:not([type="checkbox"]),textarea,select')).map(input=>[input.name,input.value]))}));}
async function saveBeforeProjectChange(){if(typeof sponsorGoalsSaveIfDirty==='function')await sponsorGoalsSaveIfDirty();
 if(typeof saveWorkingReport==='function')await saveWorkingReport();
 if(!pageDirty)return;
 if($('#sponsor-editor')&&typeof saveSponsorDraft==='function'){await saveSponsorDraft();return;}
 if($('#value-proposition-form')||$('#coached-field-form'))await saveCoachedField();
 else {
  const form=$('#intake-drawers-form')||$('#intake-edit-form')||$('#intake-start-form');
  if(!form)throw Error('Save your current changes before opening another project.');
  const read=()=>form.id==='intake-drawers-form'?{drawers:scaffoldFormValues(form),...(typeof goalsFormPayload==='function'?goalsFormPayload(form):{goals_catalog:goalsFormValues(form)})}:Object.fromEntries(new FormData(form));
  const values=read(),snapshot=JSON.stringify(values);
  const action=form.id==='intake-drawers-form'?'intake-drawers':form.id==='intake-start-form'?'intake-start':'intake-save';
  await command(action,{...values,step:form.dataset.step,expected:state.intake.draft?.ref});
  await load();
  pageDirty=JSON.stringify(read())!==snapshot;
 }
 if(pageDirty)throw Error('New edits arrived while saving. Open Home again to save those too.');
}
async function activateProject(id){
 await load(id,true); // Failed loads retain the current state and form.
 currentProjectId=id;
 try{sessionStorage.setItem('workbench-project',id);}catch{}
 restoreProjectView();
 setProjectsLocation(false);
}
// This directory uses the existing catalog. It never combines project records.
function setProjectsLocation(home){
 history.replaceState(null,'',location.pathname+location.search+(home?'#projects':''));
}
function projectsLanding(){
 if(location.hash==='#projects')return true;
 try{return !sessionStorage.getItem(projectCacheKey());}catch{return true;}
}
function projectsScreen(){return sponsorHome();}
async function openProjectsScreen(){
 await saveBeforeProjectChange();
 rememberProjectView();
 await loadHome(); // On failure, retain the existing page and its authored content.
 $('#modal')?.close();dirty=false;
 view='projects';setProjectsLocation(true);render();
 $('#main h1')?.focus();
}
function projectDirectoryNavigation(){return `<div class="nav project-directory-nav"><button type="button" data-action="projects-home" ${view==='projects'?'class="active" aria-current="page"':''}>${icon('overview')}Home</button></div>`;}
function projectsDialog(){
 const own=state.actor==='priya',current=state.project;
 modal('Project options',`<section class="project-current"><div class="caption">CURRENT PROJECT</div><h3>${esc(current.title||'Project')}</h3><span class="project-saved">Saved</span></section><div class="ui-action-list">${actionRow('Continue this project','project-continue','Return to your workbench.')}${own?`${actionRow('Start a new project','project-new','Your current project stays saved. You can return to it anytime.')}${actionRow('Reset this project','project-reset','Start this project over. Its previous work remains recoverable.','danger')}`:''}</div><div class="section">${button('Home','projects-home')}</div>${own&&state.saved_versions.length?`<details class="project-saved-versions"><summary>Restore previous work</summary><div class="project-history">${state.saved_versions.map(v=>`<div class="project-row"><div><strong>${esc(v.reason)}</strong><small>${esc(new Date(v.saved_at).toLocaleString())}</small></div>${button('Restore','project-restore',v.id,'small')}</div>`).join('')}</div></details>`:''}${!own?'<p class="caption section">The business sponsor can create or reset projects.</p>':''}`,null,null,{footer:false,className:'project-dialog'});
 $('#modal [data-action="project-continue"]')?.focus();
}
function newProjectDialog({businessBrief=false}={}){
 modal(businessBrief?'Create Business Intent':'New project',`<p>Your current project stays saved.</p><label class="form-field"><span>Project name</span><input name="title" required maxlength="200" placeholder="A short name for the opportunity" autocomplete="off"></label>`,businessBrief?'Create Business Intent':'Create project',async fd=>{
  const result=await command('project-create',{title:fd.get('title')});
  await activateProject(result.project_id);
  return {...result,projectLoaded:true};
 });
}
function replaceProjectDialog(restoreId){
 const restore=!!restoreId,title=state.project.title;
 const saved=state.saved_versions.find(v=>v.id===restoreId);
 modal(restore?'Restore saved version':'Reset project',`<p><strong>${esc(title)}</strong></p><p>${restore?`Return to the version saved ${esc(new Date(saved.saved_at).toLocaleString())}. Your current work will also be kept in Saved versions.`:'This clears the active intake, generated drafts, AI partner conversations, source material, requirements and decisions for this project. A saved version keeps all of that work recoverable.'}</p><p class="caption">Other projects stay unchanged.</p><label class="form-field"><span>Type the project name to confirm</span><input name="confirm_title" required autocomplete="off"></label>`,restore?'Restore version':'Reset project',async fd=>{
  const result=await command(restore?'project-restore':'project-reset',{confirm_title:fd.get('confirm_title'),saved_version:restoreId});
  await activateProject(result.project_id);
  return {...result,projectLoaded:true};
 },{submitTone:restore?'normal':'danger'});
}
async function projectAction(action,id){
 if(action!=='projects'&&action!=='projects-home'&&!action.startsWith('project-'))return false;
 if(action==='project-continue'){closeModal();return true;}
 if(action==='project-new'){await saveBeforeProjectChange();rememberProjectView();newProjectDialog();return true;}
 if(action==='project-reset'||action==='project-restore'){replaceProjectDialog(action==='project-restore'?id:null);return true;}
 busy=true;
 try{
  if(action==='projects-home'){
   await openProjectsScreen();
  }else if(action==='projects'){
   await saveBeforeProjectChange();rememberProjectView();await load();projectsDialog();
  }else if(action==='project-open'){
   await saveBeforeProjectChange();rememberProjectView();
   await activateProject(id);$('#modal').close();
  }
 }finally{busy=false;}
 if(action==='project-open'){render();const heading=$('#main h1');if(heading){heading.tabIndex=-1;heading.focus();}toast('Opened '+(state.project.title||'Project'));}
 return true;
}

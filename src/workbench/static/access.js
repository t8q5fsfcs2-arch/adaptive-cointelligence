'use strict';
let accountState=null,enrollmentToken='';
function accountHeader(){
 if(['testing','development'].includes(state.auth?.mode))return `<div class="ui-selector-field role-switcher preview-role-switcher"><label class="ui-control-label" for="profile">Preview user</label><div class="ui-selector-wrap"><select id="profile" class="ui-selector" aria-label="Preview user">${Object.entries(state.actors).map(([id,a])=>`<option value="${id}" ${id===state.actor?'selected':''}>${esc(a.name)}${a.name!==a.role?' · '+esc(a.role):''}</option>`).join('')}</select>${selectorChevron()}</div></div>`;
 if(state.auth?.mode!=='accounts')return '';
 return `<div class="account-header"><div><strong>${esc(state.auth.account.username)}</strong><span class="caption">${esc(state.actors[state.actor].role)}</span></div>${button('Sign out','account-signout')}</div>`;
}
let previewRoleSwitching=false;
async function switchPreviewUser(next,control){
 const previous=state.actor;
 if(!['testing','development'].includes(state.auth?.mode)||!state.actors[next]||previewRoleSwitching||(typeof busy!=='undefined'&&busy)){control.value=previous;return;}
 if(next===previous)return;
 previewRoleSwitching=true;control.disabled=true;
 try{
  await saveBeforeProjectChange();
  await command('profile',{actor:next});
  if(typeof clearThoughtPartner==='function')clearThoughtPartner();
  if(typeof clearMyFiles==='function')clearMyFiles();
  await loadHome();resetProjectView();view='projects';setProjectsLocation(true);render();
  toast('Now working as '+state.actors[state.actor].name);
 }catch(error){control.value=state.actor||previous;toast(error.message);}
 finally{previewRoleSwitching=false;control.disabled=false;}
}
function workspaceNavigation(){
 return state.domains?.active?
  {contributions:'Workbench',preflight:'Preflight',review:'Decisions & Issues',intent:'Business Intent',requirements:'Requirements',decisions:'Decision log',packets:'Evidence trail',knowledge:'Knowledge',home:'Project home',briefs:'Business Intent',context:'Context'}:
  {intent:'Business Intent',...(state.actor==='priya'?{planning:'Requirements set up'}:{}),requirements:'Requirements',...(['priya','alex'].includes(state.actor)?{delivery:'Handoff'}:{}),review:'Decisions & Issues',decisions:'Decision log',packets:'Evidence trail',knowledge:'Knowledge',home:'Project home',briefs:'Business Intent',context:'Context'};
}
function clearAccountViews(){
 if(typeof clearReviewerDrafts==='function')clearReviewerDrafts();
 if(typeof clearKnowledgeCarry==='function')clearKnowledgeCarry();
 if(typeof clearThoughtPartner==='function')clearThoughtPartner();
 if(typeof clearHomeViews==='function')clearHomeViews();
 if(typeof clearMyFiles==='function')clearMyFiles();
 if(typeof knowledgeCardViews!=='undefined')knowledgeCardViews.clear();
 if(typeof knowledgeCardEdits!=='undefined')knowledgeCardEdits.clear();
 projectViews.clear();resetProjectView();state=null;currentProjectId='original';
 // Clear only this app's per-tab caches, including private candidate wording.
 try{for(let i=sessionStorage.length-1;i>=0;i--){const k=sessionStorage.key(i);if(k==='workbench-project'||k.startsWith('workbench-view:'))sessionStorage.removeItem(k);}}catch{}
 $('#modal')?.close();const notice=$('#notice');if(notice){notice.textContent='';notice.classList?.remove('visible');}dirty=false;pageDirty=false;
}
async function authRequest(action,data){
 const r=await fetch('/api/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':accountState.csrf},body:JSON.stringify(data)});
 const result=await r.json();if(!r.ok)throw Error(result.error||'Could not sign in.');return result;
}
function signInScreen(message=''){
 const enroll=!!enrollmentToken;
 $('#app').innerHTML=`<main id="main" class="welcome card account-entry"><div class="eyebrow">Intelligence Workbench</div><h1>${enroll?'Create your account':'Sign in'}</h1><p>${enroll?'Choose a username and password. This setup link determines your membership.':'Open the projects and domain workbench assigned to you.'}</p>${message?`<p class="error" role="alert">${esc(message)}</p>`:''}${accountState.setup_required&&!enroll?'<p class="banner">First-time setup: open the administrator setup link saved beside the local database.</p>':''}<form id="account-form"><div class="error" role="alert"></div><label class="form-field"><span>Username</span><input name="username" autocomplete="username" required minlength="3" maxlength="64" autocapitalize="none" spellcheck="false"></label><label class="form-field"><span>Password</span><input name="password" type="password" autocomplete="${enroll?'new-password':'current-password'}" required ${enroll?'minlength="15"':''} maxlength="128"></label>${enroll?'<p class="caption">Use a passphrase of at least 15 characters.</p>':''}<button class="primary" type="submit">${enroll?'Create account':'Sign in'}</button></form><p class="caption">Local accounts · Enterprise SSO is not connected.</p></main>`;
 $('#account-form').addEventListener('submit',async e=>{
  e.preventDefault();const form=e.target,b=e.submitter;b.disabled=true;
  try{
   const fd=new FormData(form);accountState=await authRequest(enroll?'auth-enroll':'auth-login',{username:fd.get('username'),password:fd.get('password'),...(enroll?{token:enrollmentToken}:{})});
   form.reset();enrollmentToken='';clearAccountViews();await openSignedInWorkspace();
  }catch(error){form.querySelector('.error').textContent=error.message;}finally{b.disabled=false;}
 });
}
async function openSignedInWorkspace(){
 if(accountState.account?.actor==='administrator'||accountState.administrator||location.hash==='#projects'||location.hash.startsWith('#thought-partner')||(accountState.mode==='accounts'&&!accountState.projects.length)){
  await loadHome();view=location.hash.startsWith('#thought-partner')?'thought-partner':'projects';render();return;
 }
 if(accountState.mode==='accounts'&&!accountState.projects.includes(currentProjectId))currentProjectId=accountState.projects[0];
 await load(currentProjectId,true);restoreProjectView();
 if(projectsLanding()){await loadHome();view='projects';}
 render();
}
async function startAccountApp(){
 const fragment=new URLSearchParams(location.hash.slice(1));enrollmentToken=fragment.get('enroll')||'';
 if(enrollmentToken)history.replaceState(null,'',location.pathname+location.search);
 const r=await fetch('/api/auth');accountState=await r.json();if(!r.ok)throw Error('Could not check your session.');
 if(enrollmentToken||!accountState.authenticated){signInScreen();return;}
 await openSignedInWorkspace();
}
async function accessSettings(){
 const result=await command('access-members',{});
 modal('Project members',`<p class="caption">${esc(state.project.display_title||state.project.title)} · Each account keeps its assigned role. Members can read project-shared work; private domain work stays in its domain.</p>${result.members.map(m=>`<div class="ui-action-row"><div><strong>${esc(m.username)}</strong><p class="caption">${esc(state.actors[m.actor].role)} · ${esc(state.actors[m.actor].name)}</p></div>${m.id===state.auth.account.id?tag('You'):button('Remove access','account-revoke',m.id,'danger')}</div>`).join('')}<details class="section"><summary>Add a member</summary><p class="caption">This local increment supports one account per existing role identity. An existing account gains project access immediately. A new member receives a setup link to choose their password.</p>${Object.entries(state.actors).filter(([a])=>a!=='administrator'&&!result.members.some(m=>m.actor===a)).map(([a,m])=>`<div class="ui-action-row"><div><strong>${esc(m.role)}</strong><p class="caption">${esc(m.name)}${result.invitations.some(i=>i.actor===a)?' · Setup pending':''}</p></div>${button('Add to project','account-invite',a)}</div>`).join('')}</details>`,null,null,{footer:false});
}
async function accountAction(action,id){
 if(!action.startsWith('account-'))return false;
 if(action==='account-signout'){
  await saveBeforeProjectChange();if(dirty)throw Error('Save or close your open draft before signing out.');
  accountState=await authRequest('auth-logout',{});clearAccountViews();signInScreen();
 }else if(action==='account-members')await accessSettings();
 else if(action==='account-invite'){
  const r=await command('access-invite',{actor:id});
  if(r.token){
   modal('Account setup link',`<p>${esc(state.actors[id].role)} · ${esc(state.project.display_title||state.project.title)}</p><p>This single-use link expires in 24 hours. It works on this Mac while the local server is running.</p><label class="form-field"><span>Setup link</span><input readonly value="${esc(location.origin+'/#enroll='+r.token)}"></label><p class="caption">The recipient chooses their own username and password. No message has been sent.</p>`);
  }else{await accessSettings();toast(r.message);}
 }else if(action==='account-revoke'){
  modal('Remove project access', '<p>This member will lose access to this project. Their saved work and other project memberships remain intact.</p>', 'Remove access',async()=>command('access-revoke',{account:id}),{submitTone:'danger'});
 }
 return true;
}

async function checkAccountSession(){
 if(accountState?.mode!=='accounts'||!accountState.authenticated)return;
 try{
  const response=await fetch('/api/auth'),next=await response.json();
  if(!response.ok)return;
  if(!next.authenticated||next.account?.id!==accountState.account?.id){
   clearAccountViews();accountState=next;
   if(next.authenticated)await openSignedInWorkspace();else signInScreen('Your session ended. Sign in again.');
  }else if(state?.project&&!next.projects.includes(state.project.id)){
   clearAccountViews();accountState=next;await openSignedInWorkspace();
  }else{accountState=next;if(state)state.csrf=next.csrf;}
 }catch{/* A temporary connection failure must not discard active work. */}
}
window.addEventListener('focus',checkAccountSession);
setInterval(checkAccountSession,60000);

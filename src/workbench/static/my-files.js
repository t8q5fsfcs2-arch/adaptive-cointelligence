'use strict';
let myFilesData=null,myFilesOwner=null,myFilesRequest=0,myFilesQuery='',myFilesLocation='all',myFilesIncludeArchived=false,myFileDetail=null,myFileEditing=false;
const myFilesIdentity=()=>state?.auth?.account?.id||'profile:'+state?.actor;
function clearMyFiles(){myFilesRequest++;if(typeof clearFileUpload==='function')clearFileUpload();myFilesData=null;myFilesOwner=null;myFilesQuery='';myFilesLocation='all';myFilesIncludeArchived=false;myFileDetail=null;myFileEditing=false;}
function myFilesDiscard(){return !dirty||confirm('Discard unsaved changes?');}
async function loadMyFiles(){
 const owner=myFilesIdentity(),request=++myFilesRequest,response=await fetch('/api/my-files'),data=await response.json();
 if(!response.ok)throw Error(data.error||'Could not open Files.');
 if(owner!==myFilesIdentity()||request!==myFilesRequest)return false;
 myFilesData=data;myFilesOwner=owner;return true;
}
async function openMyFiles(){
 await saveBeforeProjectChange();if(!myFilesDiscard())return;rememberProjectView();
 if(myFilesOwner!==myFilesIdentity())clearMyFiles();
 if(await loadMyFiles())showMyFiles();
}
function myFilesVisible(){
 const query=myFilesQuery.trim().toLocaleLowerCase();
 return (myFilesData?.files||[]).filter(f=>(myFilesIncludeArchived||!f.archived)&&
  (myFilesLocation==='all'||myFilesLocation.startsWith('project:')&&f.projects.includes(myFilesLocation.slice(8))||myFilesLocation.startsWith('thread:')&&f.locations.some(l=>l.id===myFilesLocation.slice(7)))&&
  (!query||[f.title,f.filename,f.project_title,f.project_reference,f.project_display_title,f.area,...f.locations.map(l=>l.title)].join(' ').toLocaleLowerCase().includes(query)));
}
function myFilesLocationLabel(file){
 if(file.kind==='conversation')return file.locations[0].title+' · AI partner';
 return (file.project_display_title||file.project_title)+' · '+file.area;
}
function myFilesCount(){const n=myFilesVisible().length;return n+' file'+(n===1?'':'s');}
function myFilesRows(){
 return myFilesVisible().map(f=>`<article class="my-file-row"><div><h3 class="acx-item-title"><a href="#main" class="item-title-link document-name-link" data-action="files-detail" data-id="${esc(f.id)}">${esc(f.title)}</a></h3><p class="caption">${esc(myFilesLocationLabel(f))}</p><p class="caption">${f.saved_version?'Saved project version · ':''}${f.source?'Source v'+f.source.revision+' · ':''}${f.original_available?'Original retained':'Extracted text only'}${f.archived?' · Archived in Files':''}${f.source_archived?' · Removed from conversation':''}</p></div><time datetime="${esc(f.at||'')}">${esc(f.at?date(f.at):'Date not recorded')}</time></article>`).join('')||'<p class="empty">No matching files. Upload a file to a project or conversation.</p>';
}
function showMyFiles(){
 if(typeof clearFileUpload==='function')clearFileUpload();
 myFileDetail=null;myFileEditing=false;
 const threads=new Map();for(const f of myFilesData.files)for(const l of f.locations)threads.set(l.id,l.title);
 const projects=myFilesData.projects;
 $('#modal')?.close();modal('Files',`<p class="caption">Your uploads across projects and conversations.</p>${myFilesData.unavailable_locations?'<p class="banner signal-notice signal-critical" role="alert">Some project files are unavailable. Refresh to retry.</p>':''}<div class="my-files-toolbar"><label class="form-field"><span>Search files</span><input type="search" id="my-files-search" value="${esc(myFilesQuery)}" placeholder="Name, project or conversation"></label><label class="form-field"><span>Location</span><select id="my-files-location"><option value="all">All locations</option>${projects.length?`<optgroup label="Projects">${projects.map(p=>`<option value="project:${esc(p.id)}" ${myFilesLocation==='project:'+p.id?'selected':''}>${esc(p.display_title||p.title)}</option>`).join('')}</optgroup>`:''}${threads.size?`<optgroup label="Conversations">${[...threads].map(([id,title])=>`<option value="thread:${esc(id)}" ${myFilesLocation==='thread:'+id?'selected':''}>${esc(title)}</option>`).join('')}</optgroup>`:''}</select></label></div><div class="my-files-list-tools"><p id="my-files-count" role="status">${myFilesCount()}</p><label class="checkbox"><input type="checkbox" id="my-files-archived" ${myFilesIncludeArchived?'checked':''}><span>Include archived</span></label><div class="my-files-library-actions">${button('Upload file','files-upload')}${button('Refresh','files-refresh','','compact-text-action')}</div></div><div id="my-files-results">${myFilesRows()}</div>`,null,null,{footer:false,className:'my-files-dialog'});
 dirty=false;
}
function updateMyFilesList(){const results=$('#my-files-results');if(results)results.innerHTML=myFilesRows();const count=$('#my-files-count');if(count)count.textContent=myFilesCount();dirty=false;}
async function openMyFile(id){
 const owner=myFilesIdentity(),request=++myFilesRequest,response=await fetch('/api/my-file?'+new URLSearchParams({id})),data=await response.json();
 if(!response.ok)throw Error(data.error||'This file is unavailable.');
 if(owner!==myFilesIdentity()||request!==myFilesRequest)return;
 myFileDetail=data;myFileEditing=false;showMyFile();
}
function showMyFile(){
 const f=myFileDetail;if(!f)return;const query=new URLSearchParams({id:f.id});
 $('#modal')?.close();modal(f.title,`<div class="my-file-breadcrumb">${button('← Files','files-back','','compact-text-action')}</div><p>${esc(myFilesLocationLabel(f))}</p>${f.saved_version?'<p class="caption">This file belongs to a saved project version. Opening the project shows its current work.</p>':''}<div class="my-file-metadata"><span>${esc(f.filename)}</span><span>${esc(f.at?date(f.at):'Date not recorded')}</span><span>${f.characters.toLocaleString()} text characters</span></div><div class="my-file-actions">${f.original_available?`<a class="item-title-link" href="/api/my-file-download?${esc(query)}&amp;format=original" download="${esc(f.filename)}">Download original</a>`:''}<a class="item-title-link" href="/api/my-file-download?${esc(query)}&amp;format=text" download>Download extracted text</a>${button('Rename','files-rename','','compact-text-action')}${button(f.archived?'Restore to Files':'Archive from Files',f.archived?'files-restore':'files-archive','','compact-text-action')}</div>${myFileEditing?`<div class="my-file-name-editor"><label class="form-field"><span>Display name in Files</span><input id="my-file-name" maxlength="200" value="${esc(f.title)}" required></label>${button('Save name','files-save-name','','small')}</div>`:''}<p class="caption">Display names and archiving affect only this library. Files remain attached to their projects or conversations; evidence and earlier citations stay intact.</p>${f.source_archived?'<p class="caption">This document was removed from future retrieval in its conversation. Open that conversation to restore its use there.</p>':''}${f.kind==='conversation'&&f.projects.length?'<p class="caption">Project links are conversation context, not an assignment of this private upload to a project.</p>':''}<section class="my-file-locations"><h3>Open location</h3>${f.project?button(f.saved_version?'Open current project':'Open '+f.area,'files-location','project','compact-text-action'):''}${!f.saved_version?f.locations.map((l,i)=>button(l.title,'files-location',String(i),'compact-text-action')).join(''):''}</section><details class="my-file-text"><summary>Read extracted text</summary><div class="pre">${esc(f.text||'No extracted text.')}</div></details>`,null,null,{footer:false,className:'my-files-dialog'});
 dirty=false;
}
async function updateMyFile(action,title){
 const f=myFileDetail,owner=myFilesIdentity();if(!f)return;
 const result=await command('my-file-update',{id:f.id,expected_revision:f.revision,action,...(title!==undefined?{title}:{})});
 if(owner!==myFilesIdentity())return;dirty=false;
 if(await loadMyFiles()){if(action==='rename')await openMyFile(f.id);else showMyFiles();}
 toast(result.message);
}
async function openFileLocation(index){
 if(!myFilesDiscard())return;const f=myFileDetail,location=index==='project'?null:f.locations[Number(index)];
 await saveBeforeProjectChange();rememberProjectView();dirty=false;$('#modal')?.close();
 if(location?.kind==='conversation'){
  personalChatSelected=location.id;if(personalChatData)personalChatData.thread=null;
  try{sessionStorage.setItem('workbench-chat-last:'+thoughtOwner(),location.id);}catch{}
  await openThoughtPartner();await loadThoughtPartner();return;
 }
 await activateProject(f.project);
 if(!f.saved_version&&f.domain&&f.domain!=='business'&&state.domains?.active!==f.domain){await command('domain-select',{domain:f.domain});await load();}
 if(!f.saved_version&&f.domain&&f.domain!=='business'){view='contributions';selected=location?.draft||null;domainWorkMode='conversation';}
 else if(state.actor==='priya'){view='intent';sponsorStage='brief';sponsorResources='documents';sourcesOpen=true;}
 render();$('#main h1')?.focus();
}
async function myFilesAction(action,id){
 if(!action.startsWith('files-'))return false;
 if(typeof fileUploadAction==='function'&&await fileUploadAction(action))return true;
 if(action==='files-open')await openMyFiles();
 else if(action==='files-detail'){if(myFilesDiscard())await openMyFile(id);}
 else if(action==='files-back'){if(myFilesDiscard())showMyFiles();}
 else if(action==='files-refresh'){if(myFilesDiscard()&&await loadMyFiles())showMyFiles();}
 else if(action==='files-rename'){myFileEditing=true;showMyFile();$('#my-file-name')?.focus();}
 else if(action==='files-save-name')await updateMyFile('rename',$('#my-file-name').value);
 else if(action==='files-archive'||action==='files-restore'){if(myFilesDiscard())await updateMyFile(action==='files-archive'?'archive':'restore');}
 else if(action==='files-location')await openFileLocation(id);
 return true;
}
document.addEventListener('input',e=>{if(e.target.id==='my-files-search'){myFilesQuery=e.target.value;updateMyFilesList();}});
document.addEventListener('change',e=>{if(e.target.id==='my-files-location'){myFilesLocation=e.target.value;updateMyFilesList();}if(e.target.id==='my-files-archived'){myFilesIncludeArchived=e.target.checked;updateMyFilesList();}});

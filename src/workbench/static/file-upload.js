'use strict';
let myFileUpload=null,myFileUploading=false;
function clearFileUpload(){myFileUpload=null;}
async function openFileUpload(){
 if(!myFilesDiscard())return;
 const owner=myFilesIdentity(),response=await fetch('/api/my-file-destinations'),targets=await response.json();
 if(!response.ok)throw Error(targets.error||'Could not load upload locations.');
 if(owner!==myFilesIdentity())return;
 let kind='',choice='';
 if(myFilesLocation.startsWith('project:')){
  const index=targets.projects.findIndex(p=>p.destination.project===myFilesLocation.slice(8));
  if(index>=0){kind='project';choice=String(index);}
 }else if(myFilesLocation.startsWith('thread:')){
  const id=myFilesLocation.slice(7),index=targets.conversations.findIndex(p=>(p.destination.thread||p.destination.conversation?.id)===id);
  if(index>=0){kind='conversation';choice=String(index);}
 }
 myFileUpload={owner,targets,kind,choice,file:null,content:null,request:crypto.randomUUID(),saved:null};
 showFileUpload();
}
function selectedFileDestination(){
 const u=myFileUpload;if(!u)return null;
 if(u.kind==='project')return u.targets.projects[Number(u.choice)]?.destination||null;
 if(u.kind==='conversation')return u.choice==='new'?{kind:'new-conversation'}:u.targets.conversations[Number(u.choice)]?.destination||null;
 return null;
}
function fileUploadReady(){
 const u=myFileUpload;return !!(u?.file&&u.kind&&u.choice!==''&&selectedFileDestination());
}
function fileUploadTarget(){
 const u=myFileUpload;if(!u)return;
 const target=$('#my-file-upload-target');if(!target)return;
 if(!u.kind){target.innerHTML='';return;}
 const project=u.kind==='project',options=project?u.targets.projects:u.targets.conversations;
 target.innerHTML=`<label class="form-field"><span>${project?'Project location':'Conversation'}</span><select id="my-file-upload-location">${project?'<option value="">Choose private location</option>':'<option value="new">New conversation · named after this file</option>'}${options.map((option,i)=>`<option value="${i}" ${u.choice===String(i)?'selected':''} ${option.disabled?'disabled':''}>${esc(option.label)}${option.disabled?' · Response in progress':''}</option>`).join('')}</select></label><p class="caption">${project?'Private Business Intent or domain files.':'Private source for this conversation.'}</p>`;
 const select=$('#my-file-upload-location');if(select)select.value=u.choice;
 const save=$('#my-file-upload-save');if(save)save.disabled=!fileUploadReady();
}
function showFileUpload(){
 const u=myFileUpload;if(!u)return;$('#modal')?.close();
 modal('Upload file',`<div class="my-file-breadcrumb">${button('← My files','files-upload-back','','compact-text-action')}</div><div id="my-file-upload-error" class="error" role="alert"></div><div class="my-files-upload-fields"><div class="my-files-choose-row"><button type="button" data-action="files-upload-choose">Choose file</button><span id="my-file-upload-name">No file selected</span><input type="file" id="my-file-upload-file" accept=".pdf,.docx,.pptx,.txt,.md,.csv,.json" hidden></div><p class="caption">PDF, Word, PowerPoint, TXT, Markdown, CSV or JSON · up to 5 MB</p><fieldset class="my-files-save-to"><legend>Save to</legend><label><input type="radio" name="my-file-kind" value="project" ${u.kind==='project'?'checked':''} ${!u.targets.projects.length?'disabled':''}>Project</label><label><input type="radio" name="my-file-kind" value="conversation" ${u.kind==='conversation'?'checked':''}>Conversation</label></fieldset>${!u.targets.projects.length?'<p class="caption">No private project upload locations assigned.</p>':''}${u.targets.unavailable_locations?'<p class="caption">Some project locations are unavailable. Reopen Upload to refresh.</p>':''}<div id="my-file-upload-target"></div><div class="my-files-upload-footer"><span id="my-file-upload-status" class="caption" role="status"></span><button type="button" data-action="files-upload-save" id="my-file-upload-save" disabled>Save file</button></div></div>`,null,null,{footer:false,className:'my-files-dialog'});
 fileUploadTarget();dirty=false;
}
function setFileUploadBusy(value){
 myFileUploading=value;busy=value;
 for(const control of document.querySelectorAll('#modal .my-files-upload-fields input,#modal .my-files-upload-fields select,#modal button'))control.disabled=value;
 if(!value){
  const project=document.querySelector('input[name="my-file-kind"][value="project"]');if(project)project.disabled=!myFileUpload?.targets.projects.length;
  const save=$('#my-file-upload-save');if(save)save.disabled=!(myFileUpload?.saved||fileUploadReady());
 }
}
async function saveFileUpload(){
 const u=myFileUpload;if(!u||myFileUploading||(!u.saved&&!fileUploadReady()))return;
 const owner=u.owner,error=$('#my-file-upload-error'),status=$('#my-file-upload-status');if(error)error.textContent='';
 setFileUploadBusy(true);
 try{
  if(!u.saved){
   if(!u.file.size||u.file.size>5*1024*1024)throw Error('Choose a supported file under 5 MB.');
   status.textContent='Reading file…';
   if(!u.content)u.content=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Could not read this file.'));reader.readAsDataURL(u.file);});
   if(owner!==myFilesIdentity())return;
   status.textContent='Saving privately…';
   u.saved=await command('my-file-upload',{filename:u.file.name,content:u.content,destination:selectedFileDestination(),request_id:u.request,expected_owner:u.targets.owner});
  }
  if(owner!==myFilesIdentity())return;dirty=false;status.textContent='File saved.';
  if(await loadMyFiles()){const result=u.saved;clearFileUpload();await openMyFile(result.id);toast(result.message);}
 }catch(problem){
  if(owner===myFilesIdentity()){
   if(error)error.textContent=u.saved?'File saved. Choose View file to reload details.':problem.message||'Could not confirm this upload. Retry Save file to check the same attempt.';
   if(status)status.textContent='';
   if(u.saved){const save=$('#my-file-upload-save');if(save)save.textContent='View file';}
  }
 }finally{setFileUploadBusy(false);}
}
async function fileUploadAction(action){
 if(action==='files-upload'){await openFileUpload();return true;}
 if(action==='files-upload-choose'){$('#my-file-upload-file')?.click();return true;}
 if(action==='files-upload-back'){if(myFilesDiscard()){clearFileUpload();showMyFiles();}return true;}
 if(action==='files-upload-save'){await saveFileUpload();return true;}
 return false;
}
document.addEventListener('change',e=>{
 const u=myFileUpload;if(!u||u.owner!==myFilesIdentity()||myFileUploading)return;
 if(e.target.id==='my-file-upload-file'){
  u.file=e.target.files[0]||null;u.content=null;u.request=crypto.randomUUID();u.saved=null;
  const name=$('#my-file-upload-name');if(name)name.textContent=u.file?.name||'No file selected';
 }else if(e.target.name==='my-file-kind'){
  u.kind=e.target.value;u.choice=u.kind==='conversation'?'new':u.targets.projects.length===1?'0':'';u.request=crypto.randomUUID();u.saved=null;fileUploadTarget();
 }else if(e.target.id==='my-file-upload-location'){u.choice=e.target.value;u.request=crypto.randomUUID();u.saved=null;}
 // Choosing a location without a file is navigation, not authored work to discard.
 dirty=!!u.file&&!u.saved;
 const save=$('#my-file-upload-save');if(save)save.disabled=!fileUploadReady();
});
document.addEventListener('cancel',e=>{if(myFileUploading&&e.target.id==='modal')e.preventDefault();},true);

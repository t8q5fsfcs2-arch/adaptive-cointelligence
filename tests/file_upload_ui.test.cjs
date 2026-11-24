const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function harness(){
 const elements=new Map(),handlers={},dialogs=[],commands=[],opened=[],controls=[{disabled:false}];
 for(const id of ['#my-file-upload-target','#my-file-upload-location','#my-file-upload-save','#my-file-upload-error','#my-file-upload-status','#my-file-upload-name'])elements.set(id,{innerHTML:'',textContent:'',disabled:false,value:''});
 const projectRadio={disabled:false};let sequence=0;
 const ctx={state:{actor:'priya'},dirty:false,busy:false,myFilesLocation:'all',myFilesDiscard:()=>true,myFilesIdentity:()=> 'profile:'+ctx.state.actor,
  $:s=>elements.get(s)||null,modal:(...args)=>dialogs.push(args),esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
  button:(text,action)=>`<button data-action="${action}">${text}</button>`,crypto:{randomUUID:()=> 'upload-request-'+ ++sequence},
  document:{addEventListener:(name,handler)=>handlers[name]=handler,querySelectorAll:()=>controls,querySelector:()=>projectRadio},
  command:async(action,data)=>{commands.push({action,data});return {id:'F',message:'Saved privately'};},
  loadMyFiles:async()=>true,openMyFile:async id=>opened.push(id),toast(){},showMyFiles(){},FileReader:class {
   readAsDataURL(file){this.result='data:text/plain;base64,SGVsbG8=';this.onload();}
  }};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/file-upload.js'),'utf8'),ctx);
 const targets={owner:'profile:priya',projects:[{label:'Clinic · Business Intent',destination:{kind:'project',project:'P',generation:3,domain:'business'}}],conversations:[{label:'Existing thread',destination:{kind:'conversation',thread:'CHAT'}}]};
 ctx.targets=targets;ctx.file={name:'notes.txt',size:5};ctx.fetch=async()=>({ok:true,json:async()=>targets});
 return {ctx,elements,handlers,dialogs,commands,opened,projectRadio,run:s=>vm.runInContext(s,ctx)};
}
function ready(h,kind='project',choice='0'){h.ctx.kind=kind;h.ctx.choice=choice;h.run("myFileUpload={owner:'profile:priya',targets,kind,choice,file,content:null,request:'stable-attempt-0001',saved:null}");}
test('upload discloses permitted locations after the user chooses a destination type',async()=>{
 const h=harness();await h.run('openFileUpload()');const html=h.dialogs[0][1];
 assert.match(html,/Save to|Choose file/);assert.match(html,/name="my-file-kind" value="project"/);assert.match(html,/name="my-file-kind" value="conversation"/);assert.doesNotMatch(html,/configured model|OpenAI/);
 h.ctx.dirty=true;h.handlers.change({target:{name:'my-file-kind',value:'project'}});assert.equal(h.run('selectedFileDestination().project'),'P');assert.equal(h.elements.get('#my-file-upload-save').disabled,true);assert.equal(h.ctx.dirty,false);
 h.handlers.change({target:{id:'my-file-upload-file',files:[h.ctx.file]}});assert.equal(h.elements.get('#my-file-upload-save').disabled,false);assert.equal(h.ctx.dirty,true);
});
test('saving sends the explicit location, source file and current owner with no coaching action',async()=>{
 const h=harness();ready(h);await h.run('saveFileUpload()');
 assert.equal(h.commands.length,1);const call=h.commands[0];assert.equal(call.action,'my-file-upload');assert.equal(call.data.expected_owner,'profile:priya');assert.equal(call.data.destination.project,'P');assert.equal(call.data.destination.generation,3);assert.equal(call.data.content,'SGVsbG8=');assert.deepEqual(h.opened,['F']);
});
test('a retry after a lost response preserves the original attempt identifier',async()=>{
 const h=harness();ready(h,'conversation','new');let attempts=0;
 h.ctx.command=async(action,data)=>{h.commands.push({action,data});if(!attempts++)throw Error('Connection lost');return {id:'F',message:'Saved'};};
 await h.run('saveFileUpload()');await h.run('saveFileUpload()');assert.equal(h.commands.length,2);assert.equal(h.commands[0].data.request_id,h.commands[1].data.request_id);assert.equal(h.commands[0].data.destination.kind,'new-conversation');assert.deepEqual(h.opened,['F']);
});
test('a saved upload whose detail refresh failed is reopened without uploading again',async()=>{
 const h=harness();ready(h);let reads=0;h.ctx.loadMyFiles=async()=>{if(!reads++)throw Error('Read failed');return true;};
 await h.run('saveFileUpload()');assert.equal(h.elements.get('#my-file-upload-save').textContent,'View file');await h.run('saveFileUpload()');assert.equal(h.commands.length,1);assert.deepEqual(h.opened,['F']);
});
test('changing persona while the local file is being read prevents its transmission',async()=>{
 const h=harness();ready(h);let reader;
 h.ctx.FileReader=class{readAsDataURL(){reader=this;this.result='data:text/plain;base64,SGVsbG8=';}};
 const pending=h.run('saveFileUpload()');h.ctx.state.actor='lee';reader.onload();await pending;assert.equal(h.commands.length,0);assert.equal(h.opened.length,0);
});
test('conversation-only users keep the project choice disabled after an error',()=>{
 const h=harness();h.ctx.targets.projects=[];ready(h,'conversation','new');h.run('setFileUploadBusy(false)');assert.equal(h.projectRadio.disabled,true);
});

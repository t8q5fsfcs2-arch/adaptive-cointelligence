const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function harness(){
 const dialogs=[],elements=new Map(),ctx={state:{actor:'priya',auth:{mode:'development'},project:{id:'P'}},dirty:false,view:'intent',
  esc:v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),date:s=>s,
  button:(title,action,id='')=>`<button data-action="${action}" data-id="${id}">${title}</button>`,
  $:s=>elements.get(s)||null,modal:(...args)=>dialogs.push(args),confirm:()=>true,toast(){},document:{addEventListener(){}},
  saveBeforeProjectChange:async()=>{},rememberProjectView(){},Map,URLSearchParams};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/my-files.js'),'utf8'),ctx);
 return {ctx,dialogs,elements,run:s=>vm.runInContext(s,ctx)};
}
const projectFile={id:'F',kind:'project',title:'Notes',filename:'notes.txt',at:'2026-11-11',characters:20,project:'P',project_title:'Clinic',projects:['P'],origin:'',area:'Research',domain:'research',locations:[{kind:'domain',id:'T',title:'Research review',draft:'D',domain:'research'}],source:{id:'SRC',revision:1},saved_version:null,original_available:true,revision:0,archived:false,text:'Private extracted text'};
const chatFile={...projectFile,id:'C',kind:'conversation',title:'<script> filename',project:null,project_title:'',projects:[],area:'AI partner',locations:[{kind:'conversation',id:'CHAT',title:'Planning conversation'}],source:null,original_available:false};
function seed(h){h.ctx.initial={files:[projectFile,chatFile],projects:[{id:'P',title:'Clinic',origin:''}]};h.run("myFilesData=initial;myFilesOwner='profile:priya'");}
test('one library filters by project or conversation and escapes file names without listing source text',()=>{
 const h=harness();seed(h);h.run('showMyFiles()');const html=h.dialogs[0][1];assert.match(html,/Projects|Conversations/);assert.match(html,/&lt;script> filename/);assert.doesNotMatch(html,/<script>|Private extracted text/);
 h.run("myFilesLocation='project:P'");assert.equal(h.run('myFilesVisible().length'),1);
 h.run("myFilesLocation='thread:CHAT'");assert.equal(h.run('myFilesVisible()[0].id'),'C');
 h.run("myFilesLocation='all';myFilesQuery='Clinic'");assert.equal(h.run('myFilesVisible().length'),1);
 h.run("myFilesQuery='';myFilesData.files=[{...initial.files[0],archived:true}]");assert.equal(h.run('myFilesVisible().length'),0);
 h.run('myFilesIncludeArchived=true');assert.equal(h.run('myFilesVisible().length'),1);
});
test('older text-only files never offer an original download, and management explains its personal scope',()=>{
 const h=harness();h.ctx.file=chatFile;h.run('myFileDetail=file;showMyFile()');const html=h.dialogs[0][1];
 assert.match(html,/Download extracted text|Display names and archiving affect only this library/);assert.doesNotMatch(html,/Download original|Delete/);
 assert.match(html,/Read extracted text/);assert.match(html,/Private extracted text/);assert.match(html,/Archive from Files/);
});
test('opening files saves current work first and save failures retain the existing form',async()=>{
 const h=harness(),order=[];h.ctx.saveBeforeProjectChange=async()=>order.push('save');h.ctx.fetch=async()=>{order.push('fetch');return {ok:true,json:async()=>({files:[],projects:[]})};};
 await h.run('openMyFiles()');assert.deepEqual(order,['save','fetch']);assert.equal(h.dialogs[0][0],'Files');
 h.ctx.saveBeforeProjectChange=async()=>{throw Error('Preserve draft');};await assert.rejects(h.run('openMyFiles()'),/Preserve draft/);assert.equal(h.dialogs.length,1);
});
test('a late inventory or document response cannot populate a different persona',async()=>{
 const h=harness();let release;h.ctx.fetch=()=>new Promise(r=>{release=r;});const pending=h.run('loadMyFiles()');h.ctx.state.actor='lee';h.run('clearMyFiles()');release({ok:true,json:async()=>({files:[projectFile],projects:[]})});assert.equal(await pending,false);assert.equal(h.run('myFilesData'),null);
 const detail=h.run("openMyFile('F')");h.ctx.state.actor='sam';h.run('clearMyFiles()');release({ok:true,json:async()=>projectFile});await detail;assert.equal(h.run('myFileDetail'),null);assert.equal(h.dialogs.length,0);
});
test('archive uses the displayed file revision and returns to the library without project or chat writes',async()=>{
 const h=harness(),commands=[];seed(h);h.ctx.file=projectFile;h.run('myFileDetail=file');
 h.ctx.command=async(action,data)=>{commands.push({action,data});return {message:'Saved'};};
 h.ctx.fetch=async()=>({ok:true,json:async()=>({files:[{...projectFile,archived:true,revision:1}],projects:[]})});
 await h.run("updateMyFile('archive')");assert.equal(commands.length,1);assert.equal(commands[0].action,'my-file-update');assert.equal(commands[0].data.expected_revision,0);assert.equal(commands[0].data.id,'F');assert.equal(h.dialogs.at(-1)[0],'Files');assert.equal(h.ctx.state.project.id,'P');
});
test('opening a saved conversation resumes its thread and keeps unsent drafts',async()=>{
 const h=harness(),drafts=new Map([['existing','Unsent work']]);h.ctx.file=chatFile;h.run('myFileDetail=file');h.ctx.personalChatSelected=null;h.ctx.personalChatData={thread:{id:'OLD'}};h.ctx.personalChatDrafts=drafts;h.ctx.thoughtOwner=()=> 'profile:priya';h.ctx.sessionStorage={setItem(){}};
 const calls=[];h.ctx.openThoughtPartner=async()=>calls.push('open');h.ctx.loadThoughtPartner=async()=>calls.push('load');
 await h.run("openFileLocation('0')");assert.equal(h.ctx.personalChatSelected,'CHAT');assert.deepEqual(calls,['open','load']);assert.equal(drafts.get('existing'),'Unsent work');
});

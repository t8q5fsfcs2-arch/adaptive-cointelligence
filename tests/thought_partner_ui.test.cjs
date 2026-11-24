const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function harness(){
 const listeners={},calls=[],storage=new Map(),input={value:'My synthetic question',focus(){}},ctx={Map,Set,URLSearchParams,crypto:require('node:crypto').webcrypto,setTimeout:()=>1,clearTimeout(){},state:{actor:'priya',csrf:'test'},view:'thought-partner',sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},document:{addEventListener:(type,fn)=>listeners[type]=fn},history:{replaceState(){}},location:{pathname:'/',search:''},render:()=>calls.push('render'),esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),head:(t,s)=>`<h1>${t}</h1><p>${s}</p>`,button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,$:s=>s==='#personal-chat-message'?input:null,saveBeforeProjectChange:async()=>calls.push('save'),rememberProjectView:()=>calls.push('remember')};
 ctx.para=s=>'<p>'+ctx.esc(s)+'</p>';vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/thought-partner.js'),'utf8'),ctx);
 const run=s=>vm.runInContext(s,ctx);run("personalChatOwner=thoughtOwner();personalChatData={threads:[],thread:null,projects:[{id:'A',version:1,title:'Synthetic project'}],model:{configured:true}};");return {ctx,calls,listeners,input,storage,run};
}
test('general chat is the default; project context and source receipts disclose in place',()=>{
 const h=harness(),html=h.run('thoughtPartnerScreen()');assert.match(html,/Project context · General chat/);assert.match(html,/<details class="personal-chat-context"[^>]*>/);assert.match(html,/private drafts and documents/);assert.match(html,/textarea[^>]+maxlength="4000"/);assert.doesNotMatch(html,/OpenAI|configured model|data-nav=/);
 h.run(`personalChatSelected='thread';personalChatData.thread={id:'thread',projects:['A'],messages:[],count:0};`);assert.match(h.run('thoughtPartnerScreen()'),/Project context · Synthetic project/);
});
test('untrusted responses are escaped, provider errors stay distinct and simulated output is labeled',()=>{
 const h=harness();h.ctx.message={id:'m',role:'assistant',mode:'simulated',status:'complete',text:'<script>not executable</script>',citations:['P1:S1'],context:{sources:[{id:'P1:S1',project:'<Synthetic>',record_id:'REQ',revision:2}]}};
 const html=h.run('personalMessage(message)');assert.match(html,/&lt;script>/);assert.match(html,/Simulated/);assert.match(html,/Source references/);assert.doesNotMatch(html,/<script>|Edit and retry/);
 h.ctx.message.status='failed';const error=h.run('personalMessage(message)');assert.match(error,/chat-error/);assert.match(error,/Edit and retry/);assert.doesNotMatch(error,/Source references/);
});
test('global chat saves project drafts first and a failed save preserves the project surface',async()=>{
 const h=harness();h.ctx.view='planning';await h.run('openThoughtPartner()');assert.deepEqual(h.calls,['save','remember','render']);assert.equal(h.ctx.view,'thought-partner');
 h.ctx.view='planning';h.ctx.saveBeforeProjectChange=async()=>{throw Error('Draft not saved');};await assert.rejects(h.run('openThoughtPartner()'),/Draft not saved/);assert.equal(h.ctx.view,'planning');
});
test('Send retains the message until saved and retries an uncertain response with the same request ID',async()=>{
 const h=harness(),requests=[];h.ctx.command=async(action,data)=>{requests.push({action,data});if(action==='thought-chat-create')return {id:'thread'};throw Error('Connection interrupted');};
 const submit=()=>h.listeners.submit({target:{id:'personal-chat-form'},preventDefault(){}});await submit();assert.equal(h.run('personalDraft().text'),'My synthetic question');assert.match(h.run('personalChatNotice'),/Connection interrupted/);assert.equal(requests.length,2);
 const request=requests[1].data.request_id;await submit();assert.equal(requests.length,3);assert.equal(requests[2].data.request_id,request);assert.equal(requests[2].data.expected_count,0);
 h.ctx.command=async()=>({saved:true});h.ctx.fetch=async()=>({ok:true,json:async()=>({threads:[],thread:{id:'thread',projects:[],messages:[],count:2},projects:[],model:{configured:true}})});await submit();assert.equal(h.run('personalDraft().text'),'');
});
test('out-of-order fetches cannot reveal a previously selected conversation',async()=>{
 const h=harness(),pending=[];h.ctx.fetch=()=>new Promise(resolve=>pending.push(resolve));h.run("personalChatSelected='A'");const first=h.run('loadThoughtPartner()');h.run("personalChatSelected='B'");const second=h.run('loadThoughtPartner()');
 pending[1]({ok:true,json:async()=>({thread:{id:'B'}})});await second;pending[0]({ok:true,json:async()=>({thread:{id:'A'}})});await first;assert.equal(h.run('personalChatData.thread.id'),'B');
});
test('switching identity clears cached transcripts and reload errors do not start a retry loop',async()=>{
 const h=harness();h.ctx.fetch=async()=>{throw Error('Unavailable');};await h.run('loadThoughtPartner()');assert.equal(h.run('personalChatLoadFailed'),true);h.run('personalChatData=null');let calls=0;h.ctx.fetch=async()=>{calls++;};h.run('mountThoughtPartner()');assert.equal(calls,0);
 h.ctx.state.actor='sam';h.run('thoughtPartnerScreen()');assert.equal(h.run('personalChatData'),null);assert.equal(h.run('personalChatSelected'),null);assert.equal(h.run('personalDraft().text'),'');
});

test('project context stays expanded while selecting more than one project',()=>{
 const h=harness();h.listeners.toggle({target:{id:'personal-chat-context',open:true}});h.listeners.change({target:{dataset:{personalProject:'A'},checked:true}});assert.match(h.run('thoughtPartnerScreen()'),/<details class="personal-chat-context"[^>]* open>/);
});
test('documents have a discoverable upload control, thread manager and private extracted-text access',()=>{
 const h=harness();h.run(`personalChatSelected='t';personalChatData.thread={id:'t',projects:[],messages:[],count:0,documents:[{id:'d',title:'<Study>.docx',characters:400,at:'2026-11-11',revision:1,archived:false}]};`);
 const html=h.run('thoughtPartnerScreen()');assert.match(html,/aria-label="Add document"/);assert.match(html,/Documents \(1\)/);assert.match(html,/data-action="thought-document"/);assert.match(html,/&lt;Study>/);assert.doesNotMatch(html,/<Study>/);
 let manager='';h.ctx.date=s=>s;h.ctx.modal=(title,body)=>manager=body;h.run('personalDocumentsDialog()');for(const action of ['thought-document-rename','thought-document-archive'])assert.match(manager,new RegExp(action));assert.match(manager,/restore/i);
});


test('general threads live in navigation outside projects without a second history pane',()=>{
 const h=harness();h.run("personalChatData.threads=[{id:'g',title:'Independent <question>'}]");const nav=h.run('thoughtPartnerNavigation()'),main=h.run('thoughtPartnerScreen()');assert.match(nav,/aria-label="Recent chats"/);assert.doesNotMatch(nav,/General chats|See more/);assert.doesNotMatch(nav,/data-nav=|project-chat-navigation/);assert.match(nav,/Independent &lt;question>/);assert.doesNotMatch(main,/personal-chat-history|Saved conversations/);
 h.ctx.state.auth={account:{id:'different-user'}};assert.doesNotMatch(h.run('thoughtPartnerNavigation()'),/Independent/);
});
test('a general thread selected from a project opens Chats after saving and does not create or move a project record',async()=>{
 const h=harness(),writes=[];h.ctx.view='contributions';h.ctx.command=async(a,d)=>writes.push([a,d]);h.ctx.fetch=async()=>({ok:true,json:async()=>({threads:[{id:'g',title:'General question'}],thread:{id:'g',projects:[],messages:[],count:0},projects:[],model:{configured:true}})});
 await h.run("thoughtPartnerAction('thought-thread','g')");assert.equal(h.ctx.view,'thought-partner');assert.equal(h.run('personalChatSelected'),'g');assert.deepEqual(h.calls.slice(0,2),['save','remember']);assert.deepEqual(writes,[]);
});
test('general chat loading remains owner scoped when requested from a project menu',async()=>{
 const h=harness();h.ctx.view='contributions';h.run('personalChatNavOpen=true');let release;h.ctx.fetch=()=>new Promise(resolve=>release=resolve);const loading=h.run('loadThoughtPartner()');h.ctx.state.actor='sam';release({ok:true,json:async()=>({threads:[{id:'private',title:'Prior owner chat'}]})});await loading;assert.doesNotMatch(h.run('thoughtPartnerNavigation()'),/Prior owner chat/);
});


test('loading general thread names from a project updates only navigation and leaves the active editor untouched',async()=>{
 const h=harness();h.ctx.view='planning';h.run('personalChatNavOpen=true');let refreshed=0;h.ctx.refreshGeneralChatNavigation=()=>refreshed++;h.ctx.fetch=async()=>({ok:true,json:async()=>({threads:[{id:'g',title:'Independent chat'}],thread:null,projects:[],model:{configured:true}})});
 await h.run('loadThoughtPartner()');assert.equal(refreshed,1);assert.deepEqual(h.calls,[]);assert.equal(h.ctx.view,'planning');assert.match(h.run('thoughtPartnerNavigation()'),/Independent chat/);
});


test('loading the global menu first still restores the current owners last general chat',()=>{
 const h=harness();h.storage.set('workbench-chat-last:profile:sam','saved-sam-thread');h.ctx.state.actor='sam';h.run('thoughtPartnerNavigation()');assert.equal(h.run('personalChatSelected'),'saved-sam-thread');assert.equal(h.run('personalChatOwner'),'profile:sam');assert.equal(h.run('personalChatData'),null);
});


test('the latest three threads are direct links and older threads unfold behind See more',()=>{
 const h=harness();h.run("personalChatData.threads=Array.from({length:8},(_,i)=>({id:'t'+i,title:'Query '+i}))");let html=h.run('thoughtPartnerNavigation()'),recent=html.match(/<nav aria-label="Recent chats">([\s\S]*?)<\/nav>/)[1];
 assert.equal((recent.match(/data-action="thought-thread"/g)||[]).length,3);assert.match(recent,/Query 0/);assert.match(recent,/Query 2/);assert.doesNotMatch(recent,/Query 3/);assert.match(html,/<summary>See more<\/summary>/);assert.match(html,/Query 7/);assert.doesNotMatch(html,/data-general-chat-navigation open/);
 h.run('personalChatNavOpen=true');html=h.run('thoughtPartnerNavigation()');assert.match(html,/data-general-chat-navigation open/);assert.match(html,/Search chats/);assert.doesNotMatch(html,/General chats/);
});
test('expanded query search stays available when a search has only one result',()=>{
 const h=harness();h.run("personalChatNavOpen=true;personalChatQuery='specific';personalChatData.threads=[{id:'t',title:'A specific query'}]");const html=h.run('thoughtPartnerNavigation()');assert.match(html,/data-general-chat-navigation open/);assert.match(html,/data-personal-chat-search/);assert.match(html,/A specific query/);
});
test('entering a project loads its owners recent queries without sending a message or replacing the project editor',()=>{
 const h=harness();h.ctx.view='contributions';h.run('personalChatData=null');let reads=0;h.ctx.loadThoughtPartner=()=>reads++;h.run('mountThoughtPartner()');assert.equal(reads,1);assert.deepEqual(h.calls,[]);assert.equal(h.ctx.view,'contributions');
});


test('the general reviewer composer stays editable while pending but access loss still blocks it',()=>{
 const h=harness();h.run("personalChatSelected='thread';personalChatData.thread={id:'thread',projects:[],messages:[{role:'assistant',status:'pending',text:'',citations:[],context:{sources:[]}}],count:1};personalDraft().text='Next private question'");let html=h.run('thoughtPartnerScreen()');assert.match(html,/<label class="reviewer-composer-label"[^>]*>You<\/label>/);assert.match(html,/<textarea[^>]*rows="4"/);assert.doesNotMatch(html,/<textarea[^>]*disabled/);assert.match(html,/<button type="submit" disabled>Ask/);assert.match(html,/Next private question/);
 h.run('personalChatData.thread.blocked=true');assert.match(h.run('thoughtPartnerScreen()'),/<textarea[^>]*disabled/);
});

test('a newly typed general question survives the earlier response and keeps the original project snapshot',async()=>{
 const h=harness(),calls=[];let release,started;const ready=new Promise(resolve=>started=resolve);h.run("personalChatSelected='thread';personalChatData.thread={id:'thread',projects:['A'],messages:[],count:0};personalDraft().projects=['A'];personalDraft().initialized=true");h.ctx.command=async(action,data)=>{calls.push({action,data});started();return new Promise(resolve=>release=resolve);};h.ctx.fetch=async()=>({ok:true,json:async()=>({threads:[],thread:{id:'thread',projects:['A'],messages:[],count:2},projects:[{id:'A',version:2,title:'Synthetic project'}],model:{configured:true}})});
 const pending=h.listeners.submit({target:{id:'personal-chat-form'},preventDefault(){}});await ready;h.input.value='Next private question';h.listeners.input({target:{id:'personal-chat-message',value:h.input.value}});release({saved:true});await pending;assert.equal(calls.length,1);assert.equal(calls[0].data.message,'My synthetic question');assert.equal(calls[0].data.projects[0].version,1);assert.equal(h.run('personalDraft().text'),'Next private question');
});

test('new general-thread creation moves the live draft without erasing text typed during creation',async()=>{
 const h=harness();let release,started;const ready=new Promise(resolve=>started=resolve),calls=[];h.ctx.command=async(action,data)=>{calls.push({action,data});if(action==='thought-chat-create'){started();return new Promise(resolve=>release=resolve);}return {saved:true};};h.ctx.fetch=async()=>({ok:true,json:async()=>({threads:[],thread:{id:'created',projects:[],messages:[],count:2},projects:[],model:{configured:true}})});
 const pending=h.listeners.submit({target:{id:'personal-chat-form'},preventDefault(){}});await ready;h.input.value='Next question during creation';h.listeners.input({target:{id:'personal-chat-message',value:h.input.value}});release({id:'created'});await pending;assert.equal(h.run('personalChatSelected'),'created');assert.equal(h.run('personalDraft().text'),'Next question during creation');assert.equal(calls[1].data.message,'My synthetic question');
});

test('an old same-owner response cannot clear a newer send after the chat cache was reset',async()=>{
 const h=harness(),pending=[];h.run("personalChatSelected='first';personalChatData.thread={id:'first',projects:[],messages:[],count:0}");h.ctx.command=async(action,data)=>new Promise(resolve=>pending.push({action,data,resolve}));h.ctx.fetch=async()=>({ok:true,json:async()=>({threads:[],thread:{id:'second',projects:[],messages:[],count:2},projects:[],model:{configured:true}})});
 const first=h.listeners.submit({target:{id:'personal-chat-form'},preventDefault(){}});await Promise.resolve();h.run("clearThoughtPartner();personalChatOwner=thoughtOwner();personalChatSelected='second';personalChatData={threads:[],thread:{id:'second',projects:[],messages:[],count:0},projects:[],model:{configured:true}}");h.input.value='Second operation';const second=h.listeners.submit({target:{id:'personal-chat-form'},preventDefault(){}});await Promise.resolve();assert.equal(pending.length,2);pending[0].resolve({saved:true});await first;assert.equal(h.run('personalChatSending.thread'),'second');assert.equal(h.run('personalDraft().text'),'Second operation');pending[1].resolve({saved:true});await second;assert.equal(h.run('personalChatSending'),null);
});

test('general response polling restores the active composer caret without moving it to another thread',()=>{
 const h=harness(),events=[];let current={selectionStart:4,selectionEnd:9};h.ctx.document.activeElement=current;h.ctx.$=selector=>selector==='#personal-chat-message'?current:null;h.ctx.render=()=>{current={focus:options=>events.push(options),setSelectionRange:(a,b)=>events.push([a,b])};};h.run('renderThoughtPartner()');assert.equal(events[0].preventScroll,true);assert.deepEqual(events[1],[4,9]);
 events.length=0;h.ctx.document.activeElement=current;current.selectionStart=1;current.selectionEnd=1;h.ctx.render=()=>{h.run("personalChatSelected='different'");current={focus:()=>events.push('wrong thread focus')};};h.run('renderThoughtPartner()');assert.deepEqual(events,[]);
});

test('an earlier same-owner failure cannot replace the current conversation notice',async()=>{
 const h=harness(),pending=[];h.run("personalChatSelected='first';personalChatData.thread={id:'first',projects:[],messages:[],count:0}");h.ctx.command=async()=>new Promise((resolve,reject)=>pending.push({resolve,reject}));h.ctx.fetch=async()=>({ok:true,json:async()=>({threads:[],thread:{id:'second',projects:[],messages:[],count:2},projects:[],model:{configured:true}})});
 const first=h.listeners.submit({target:{id:'personal-chat-form'},preventDefault(){}});await Promise.resolve();h.run("clearThoughtPartner();personalChatOwner=thoughtOwner();personalChatSelected='second';personalChatData={threads:[],thread:{id:'second',projects:[],messages:[],count:0},projects:[],model:{configured:true}}");h.input.value='Second operation';const second=h.listeners.submit({target:{id:'personal-chat-form'},preventDefault(){}});await Promise.resolve();h.run("personalChatNotice='Current context notice'");pending[0].reject(Error('Earlier private error'));await first;assert.equal(h.run('personalChatNotice'),'Current context notice');assert.equal(h.run('personalChatSending.thread'),'second');pending[1].resolve({saved:true});await second;
});

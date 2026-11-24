const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(){
 const store=new Map();
 const ctx={state:{actor:'sam',actors:{sam:{name:'Sam',role:'Research evidence reviewer'},lee:{name:'Lee',role:'Design reviewer'}},auth:{mode:'accounts',account:{id:'research-id',username:'sam',admin:false}},domains:{active:'research',profiles:[{key:'research',config:{label:'Research',descriptor:'Research expertise'}}],handoffs:[]}},
 esc:v=>String(v??'').replaceAll('<','&lt;').replaceAll('"','&quot;'),button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,selectorChevron:()=>'',
 window:{addEventListener(){}},setInterval(){},URLSearchParams,
 projectViews:new Map(),resetProjectView(){},currentProjectId:'A',dirty:true,pageDirty:true,
 sessionStorage:{get length(){return store.size},key:i=>[...store.keys()][i],removeItem:k=>store.delete(k)},
 $:()=>({close(){}}),fetch:async()=>({ok:true,json:async()=>({mode:'accounts',authenticated:false,csrf:'fresh'})}),
 recordList:[],records:kind=>ctx.recordList.filter(r=>r.kind===kind),head:(t,s)=>t+s,para:s=>s,tag:t=>t,label:r=>r.id+':v'+r.revision,
 contributionCard:r=>'SHARED:'+r.body.title,selected:null
 };vm.createContext(ctx);require('./ui_reference_helpers.cjs')(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/packets.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/access.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domains.js'),'utf8'),ctx);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/preflight.js'),'utf8'),ctx);
 ctx.val=(t,s)=>t+':'+s;
 return {ctx,store,run:s=>vm.runInContext(s,ctx)};
}
test('signed-in identity replaces arbitrary role selector; testing remains explicitly labelled',()=>{
 const h=harness(),html=h.run('accountHeader()');assert.match(html,/sam/);assert.match(html,/Research evidence reviewer/);assert.match(html,/Sign out/);assert.doesNotMatch(html,/<select|Local role/);
 h.ctx.state.auth.mode='testing';assert.match(h.run('accountHeader()'),/Preview user/);
 h.ctx.state.auth.mode='development';const preview=h.run('accountHeader()');assert.match(preview,/Preview user/);assert.doesNotMatch(preview,/Sign out/);assert.equal((preview.match(/id="profile"/g)||[]).length,1);assert.match(preview,/>Sam · Research evidence reviewer/);
 h.ctx.state.auth.mode='unknown';assert.equal(h.run('accountHeader()'),'');h.ctx.state.auth=null;assert.equal(h.run('accountHeader()'),'');
});
test('preview user switch saves first, preserves the selected target and clears private view caches',async()=>{
 const h=harness(),calls=[];h.ctx.state.auth.mode='testing';h.ctx.view='contributions';h.ctx.control={value:'lee',disabled:false};
 let release;h.ctx.saveBeforeProjectChange=()=>{calls.push('save');return new Promise(r=>release=r);};
 h.ctx.command=async(a,d)=>calls.push([a,d.actor]);h.ctx.clearThoughtPartner=()=>calls.push('clear-chat');h.ctx.clearMyFiles=()=>calls.push('clear-files');h.ctx.loadHome=async()=>{calls.push('load');h.ctx.state.actor='lee';};h.ctx.resetProjectView=()=>calls.push('reset');h.ctx.setProjectsLocation=()=>{};h.ctx.render=()=>calls.push('render');h.ctx.toast=t=>calls.push(t);
 const first=h.run("switchPreviewUser('lee',control)");assert.equal(h.ctx.control.disabled,true);h.ctx.control.value='sam';await h.run("switchPreviewUser('sam',control)");release();await first;
 assert.deepEqual(calls.slice(0,6),['save',['profile','lee'],'clear-chat','clear-files','load','reset']);assert.equal(h.ctx.state.actor,'lee');assert.equal(h.ctx.control.disabled,false);assert.ok(calls.includes('render'));
});
test('failed draft save and account-bound sessions cannot change preview users',async()=>{
 const h=harness(),messages=[];h.ctx.state.auth.mode='development';h.ctx.control={value:'lee',disabled:false};h.ctx.saveBeforeProjectChange=async()=>{throw Error('Draft save failed');};h.ctx.command=()=>assert.fail('Must not switch');h.ctx.toast=t=>messages.push(t);
 const before=JSON.stringify(h.ctx.state);await h.run("switchPreviewUser('lee',control)");assert.equal(h.ctx.control.value,'sam');assert.equal(h.ctx.control.disabled,false);assert.equal(JSON.stringify(h.ctx.state),before);assert.deepEqual(messages,['Draft save failed']);
 for(const mode of ['accounts','unknown',undefined]){h.ctx.state.auth={mode};h.ctx.control.value='lee';h.ctx.saveBeforeProjectChange=()=>assert.fail('No account impersonation');await h.run("switchPreviewUser('lee',control)");assert.equal(h.ctx.control.value,'sam');}
});
test('domain navigation leads with personal workspace, preflight and Decisions & Issues',()=>{
 const h=harness(),n=h.run('workspaceNavigation()');assert.deepEqual(Object.keys(n).slice(0,3),['contributions','preflight','review']);assert.equal(n.preflight,'Preflight');assert.equal(n.review,'Decisions & Issues');assert.ok(n.intent);assert.ok(n.requirements);assert.equal(n.overview,undefined);
 h.ctx.state.domains.active=null;assert.equal(h.run('workspaceNavigation()').overview,undefined);assert.ok(h.run('workspaceNavigation()').intent);assert.equal(h.run('workspaceNavigation()').preflight,undefined);
});
test('sign-out clears only workbench caches including unapplied private edits',()=>{
 const h=harness();h.store.set('workbench-view:research-id:A:1','private');h.store.set('workbench-project','A');h.store.set('unrelated','keep');h.ctx.projectViews.set('A',{private:'text'});
 h.run('clearAccountViews()');assert.equal(h.ctx.state,null);assert.equal(h.ctx.projectViews.size,0);assert.equal(h.store.size,1);assert.equal(h.store.get('unrelated'),'keep');assert.equal(h.ctx.dirty,false);
});
test('private workspace excludes the shared work feed',()=>{
 const h=harness();h.ctx.state.domains.can_configure=[];h.ctx.state.domains.reports=[];h.ctx.state.domains.sources=[];
 h.ctx.recordList=[{kind:'contribution',ref:{id:'C',revision:1},body:{title:'Released Design'}}];
 const privateHtml=h.run('domainScreen()');assert.match(privateHtml,/Research workbench/);assert.doesNotMatch(privateHtml,/Released Design|Published contributions/);
 const shared=h.run('sharedDomainReleases()');assert.match(shared,/Released Design/);assert.doesNotMatch(shared,/New deliverable/);
});
test('legacy preflight opens sharing in the same AI partner surface',()=>{
 const h=harness();h.ctx.domainPanels=new Map();h.ctx.chatKey=()=>"current-work";h.ctx.domainChatScreen=()=>'<main>AI partner · Prepare to share</main>';
 const html=h.run('domainPreflightScreen()');assert.match(html,/AI partner/);assert.equal(h.ctx.domainPanels.get('current-work'),'sharing');assert.doesNotMatch(html,/Prepared packages|Review & send/);
});

test('sponsor replaces preflight with planning while domain preflight remains separate',()=>{
 const h=harness();h.ctx.state.domains.active=null;h.ctx.state.actor='priya';assert.equal(h.run('workspaceNavigation()').preflight,undefined);assert.equal(h.run('workspaceNavigation()').planning,'Requirements set up');assert.equal(h.run('workspaceNavigation()').delivery,'Handoff');
 h.ctx.state.actor='alex';assert.equal(h.run('workspaceNavigation()').preflight,undefined);
});

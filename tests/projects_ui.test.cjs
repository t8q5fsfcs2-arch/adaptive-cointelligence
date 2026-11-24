const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function harness(){
 const storage=new Map(),ctx={console,Map,Set,Date,sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
 state:{actor:'priya',project:{id:'A',version:1,title:'Alpha'},projects:[],saved_versions:[]},
 location:{pathname:'/',search:'',hash:''},history:{replaceState(){}},
 document:{addEventListener(){}},$:()=>null,esc:s=>String(s??'').replaceAll('<','&lt;').replaceAll('"','&quot;'),button:(s,a,id)=>`<button data-action="${a}" data-id="${id}">${s}</button>`,tag:s=>s,
 view:'intent',selected:null,requirementsMode:'scaffold',intakeStep:'value',intakeCaseId:null,
 valueReview:false,valueFocus:'measures',valueCoachMode:'question',valueMessage:'Unsent question',valueWorking:{},valueOpen:new Set(['reason']),
 valueCandidateEdits:{candidate:'Edited suggestion'},valueDismissed:new Set(['old']),valueNavigationOpen:true,valueNavigationFocus:null,
 coachedField:'measures',chosenSources:new Set(['SOURCE-A']),sourcesOpen:true,coachingMessages:{measures:'Private message'},coachingWorking:{},pageDirty:false,dirty:false,busy:false,
 head:(t,s,a='')=>`<h1>${t}</h1><p>${s}</p>${a}`,render:()=>{},toast:()=>{},modal:()=>{},
 FormData:class{constructor(form){return Object.entries(form.fields)[Symbol.iterator]();}}
 };vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8').split('\n').find(l=>l.startsWith('const actionRow=')),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/home.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/projects.js'),'utf8'),ctx);
 ctx.loadHome=async()=>{};return {ctx,storage,run:s=>vm.runInContext(s,ctx)};
}
test('switch clears project-specific caches and returning restores position and unapplied edits',async()=>{
 const h=harness();h.ctx.load=async id=>{h.ctx.state.project={id,version:1,title:id};};
 h.run('rememberProjectView()');await h.run("activateProject('B')");
 assert.equal(h.ctx.valueFocus,'business_challenge');assert.equal(h.ctx.chosenSources.size,0);
 assert.equal(Object.keys(h.ctx.valueCandidateEdits).length,0);assert.equal(Object.keys(h.ctx.coachingMessages).length,0);
 await h.run("activateProject('A')");assert.equal(h.ctx.valueFocus,'measures');assert.equal(h.ctx.valueCandidateEdits.candidate,'Edited suggestion');
 assert.equal(h.ctx.chosenSources.has('SOURCE-A'),true);assert.equal(h.storage.get('workbench-project'),'A');
});
test('reset generation never reuses old project caches',async()=>{
 const h=harness();h.run('rememberProjectView()');h.ctx.load=async()=>{h.ctx.state.project.version=2;};
 await h.run("activateProject('A')");assert.equal(h.ctx.valueFocus,'business_challenge');assert.equal(h.ctx.valueMessage,'');
 assert.equal(h.ctx.chosenSources.size,0);assert.equal(Object.keys(h.ctx.valueCandidateEdits).length,0);
});
test('opening project picker saves active answer first and preserves failure edits',async()=>{
 const h=harness(),calls=[];h.ctx.pageDirty=true;h.ctx.$=s=>s==='#value-proposition-form'?{}:null;
 h.ctx.saveCoachedField=async()=>{calls.push('save');h.ctx.pageDirty=false;};h.ctx.load=async()=>calls.push('load');h.ctx.modal=()=>calls.push('picker');
 await h.run("projectAction('projects')");assert.deepEqual(calls,['save','load','picker']);assert.equal(h.ctx.busy,false);
 h.ctx.pageDirty=true;h.ctx.saveCoachedField=async()=>{throw Error('Save failed');};calls.length=0;
 await assert.rejects(h.run("projectAction('projects')"),/Save failed/);assert.equal(h.ctx.pageDirty,true);assert.equal(h.ctx.busy,false);assert.equal(calls.length,0);
});
test('typing during save prevents switching and keeps newer text',async()=>{
 const h=harness();h.ctx.pageDirty=true;h.ctx.$=s=>s==='#value-proposition-form'?{}:null;
 h.ctx.saveCoachedField=async()=>{h.ctx.valueWorking.measures='New typing';};h.ctx.load=async()=>assert.fail('Must not change projects');
 await assert.rejects(h.run("projectAction('projects')"),/New edits arrived/);
 assert.equal(h.ctx.valueWorking.measures,'New typing');assert.equal(h.ctx.busy,false);
});
test('failed target load retains current project and caches',async()=>{
 const h=harness();h.ctx.load=async()=>{throw Error('Unavailable');};
 await assert.rejects(h.run("activateProject('B')"),/Unavailable/);assert.equal(h.ctx.state.project.id,'A');assert.equal(h.ctx.valueFocus,'measures');
 assert.equal(h.ctx.valueCandidateEdits.candidate,'Edited suggestion');
});
test('project choices are explicit and names are escaped',()=>{
 const h=harness();h.ctx.state.project.title='<script>';h.ctx.state.projects=[h.ctx.state.project];let markup='';h.ctx.modal=(title,body)=>markup=body;
 h.run('projectsDialog()');assert.doesNotMatch(markup,/<script>/);assert.match(markup,/&lt;script>/);assert.doesNotMatch(markup,/Current project options|Pick up where you left off/);
 assert.match(markup,/Continue this project/);assert.match(markup,/Start a new project/);assert.match(markup,/Reset this project/);assert.match(markup,/current project stays saved/);
});
test('background reload cannot silently adopt a reset while an old form is open',async()=>{
 const h=harness();h.ctx.currentProjectId='A';h.ctx.state.csrf='token';
 h.ctx.fetch=async()=>({ok:true,json:async()=>({project:{id:'A',version:2,title:'Alpha'}})});
 const source=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8').split('\n').find(l=>l.startsWith('async function load('));
 vm.runInContext(source,h.ctx);
 await assert.rejects(h.run('load()'),/reset or restored/);assert.equal(h.ctx.state.project.version,1);
 await h.run("load('A',true)");assert.equal(h.ctx.state.project.version,2);
});
test('commands send the explicit project and generation with the request',async()=>{
 const h=harness();h.ctx.state.csrf='token';let request;
 h.ctx.fetch=async(url,options)=>{request={url,options};return {ok:true,json:async()=>({message:'saved'})};};
 const source=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8').split('\n').find(l=>l.startsWith('async function command('));
 vm.runInContext(source,h.ctx);await h.run("command('intake-save',{value:'Preserved'})");
 assert.equal(request.options.headers['X-Workbench-Project'],'A');assert.equal(request.options.headers['X-Workbench-Version'],'1');
 assert.equal(JSON.parse(request.options.body).value,'Preserved');
});

test('directory shows all saved projects with one opening action each and no destructive controls',()=>{
 const h=harness();h.ctx.head=(title,desc,actions)=>title+desc+actions;
 h.ctx.state.projects=[{id:'A',title:'Alpha'},{id:'B',title:'<Private name>'}];
 const markup=h.run('projectsScreen()');
 assert.match(markup,/Alpha/);assert.match(markup,/&lt;Private name>/);assert.doesNotMatch(markup,/<Private name>/);
 assert.equal((markup.match(/data-action="project-open"/g)||[]).length,2);
 assert.match(markup,/Create Business Intent/);assert.doesNotMatch(markup,/project-reset|project-restore/);
 h.ctx.state.actor='sam';assert.doesNotMatch(h.run('projectsScreen()'),/New project/);
});
test('directory retains the project position across repeated visits and opening another project',async()=>{
 const h=harness();h.ctx.$=s=>s==='#modal'?{close(){}}:null;
 h.ctx.load=async(id='A')=>{h.ctx.state.project={id,version:1,title:id};};
 await h.run("projectAction('projects-home')");assert.equal(h.ctx.view,'projects');
 h.run('rememberProjectView()'); // Reload/unload of the directory must not clobber intake position.
 await h.run("projectAction('project-open','B')");assert.equal(h.ctx.view,'intent');
 await h.run("projectAction('projects-home')");await h.run("projectAction('project-open','A')");
 assert.equal(h.ctx.view,'intent');assert.equal(h.ctx.valueFocus,'measures');
 assert.equal(h.ctx.valueCandidateEdits.candidate,'Edited suggestion');assert.equal(h.ctx.busy,false);
});
test('directory save failure preserves authored work and does not navigate',async()=>{
 const h=harness();h.ctx.pageDirty=true;h.ctx.$=s=>s==='#coached-field-form'?{}:null;
 h.ctx.saveCoachedField=async()=>{throw Error('Offline');};h.ctx.load=async()=>assert.fail('Must not navigate');
 await assert.rejects(h.run("projectAction('projects-home')"),/Offline/);
 assert.equal(h.ctx.view,'intent');assert.equal(h.ctx.pageDirty,true);assert.equal(h.ctx.busy,false);
});
test('opening directory saves scaffold areas together with goal and metric edits',async()=>{
 const h=harness(),form={id:'intake-drawers-form',dataset:{step:'drawers'}},calls=[];
 h.ctx.state.intake={draft:{ref:{id:'INTAKE-001',revision:2}}};h.ctx.pageDirty=true;
 h.ctx.$=s=>s==='#intake-drawers-form'?form:null;
 h.ctx.scaffoldFormValues=()=>[{key:'accessibility',included:true}];
 h.ctx.goalsFormValues=()=>({goals:[{title:'Complete the task'}],measures:[{title:'Completion rate'}]});
 h.ctx.command=async(action,data)=>calls.push({action,data});h.ctx.load=async()=>{};
 await h.run("projectAction('projects-home')");
 assert.equal(calls[0].action,'intake-drawers');assert.equal(calls[0].data.goals_catalog.measures[0].title,'Completion rate');
 assert.equal(calls[0].data.drawers[0].key,'accessibility');assert.equal(h.ctx.pageDirty,false);assert.equal(h.ctx.view,'projects');
});
test('first visit opens directory but a saved project position remains available',()=>{
 const h=harness();assert.equal(h.run('projectsLanding()'),true);
 h.run('rememberProjectView()');assert.equal(h.run('projectsLanding()'),false);
 h.ctx.location.hash='#projects';assert.equal(h.run('projectsLanding()'),true);
});


test('Home keeps project status with project rows and leaves issues in Accountability',()=>{
 const h=harness();h.ctx.state.projects=[{id:'A',title:'Clinic Feedback',summary:{stage:'Project dashboard',needs:['1 open issue']}}];
 h.ctx.state.bridge={issues:[{ref:{id:'ISSUE-1'},body:{title:'Photo timing conflict'}}]};const before=JSON.stringify(h.ctx.state),html=h.run('projectsScreen()');
 assert.match(html,/Clinic Feedback/);assert.match(html,/1 open issue/);assert.match(html,/Business Intent published/);assert.doesNotMatch(html,/Photo timing conflict|ISSUE-1|Project dashboard/);assert.equal(JSON.stringify(h.ctx.state),before);
});

test('sponsor homepage keeps the Figma structure and renders only saved project rows',()=>{
 const h=harness();h.ctx.state.projects=[{id:'A',title:'Draft initiative',created_at:'2026-11-01',summary:{stage:'Business Intent',brief_status:'draft',needs:['Continue your brief']}},{id:'B',title:'Published initiative',summary:{stage:'Project dashboard',brief_status:'published',brief_revision:2,published_at:'2026-11-02',needs:[],last_activity:'2026-11-03'}}];
 const before=JSON.stringify(h.ctx.state);const html=h.run('sponsorHome()');
 for(const text of ['Move projects forward','without losing context','How it works','Why use this','Browse published Business Intent','Projects','Needs you','Last activity'])assert.match(html,new RegExp(text));
 assert.doesNotMatch(html,/hours to minutes|About 20 minutes|Word, PDF|Steven Boliek/);
 assert.equal((html.match(/data-action="project-open"/g)||[]).length,2);assert.equal(JSON.stringify(h.ctx.state),before);
 h.run("homeProjectQuery='published';homePublishedOnly=true");const rows=h.run('homeProjectRows()');assert.match(rows,/Published initiative/);assert.doesNotMatch(rows,/Draft initiative/);assert.match(rows,/v2/);
 h.run("homeProjectQuery='<script>';homePublishedOnly=false");assert.doesNotMatch(h.run('homeProjectRows()'),/<script>/);assert.doesNotMatch(h.run('sponsorHome()'),/<script>/);
 const result={textContent:''},body={innerHTML:''},clear={hidden:true};h.ctx.$=s=>s==='#home-results'?result:s==='#home-project-rows'?body:s==='[data-action="home-clear"]'?clear:null;h.run('updateHomeProjects()');assert.match(result.textContent,/<script>/);assert.equal(result.innerHTML,undefined);
});
test('new-brief entry saves work before opening the real project creation flow',async()=>{
 const h=harness(),calls=[];h.ctx.saveBeforeProjectChange=async()=>calls.push('save');h.ctx.rememberProjectView=()=>calls.push('remember');h.ctx.newProjectDialog=o=>calls.push(o.businessBrief?'create-brief':'wrong');
 await h.run("homeAction('home-create')");assert.deepEqual(calls,['save','remember','create-brief']);
 h.ctx.saveBeforeProjectChange=async()=>{throw Error('Save failed');};calls.length=0;await assert.rejects(h.run("homeAction('home-create')"),/Save failed/);assert.deepEqual(calls,[]);
});
test('Home keeps filter announcements while showing the total only once at rest',()=>{
 const h=harness();h.ctx.state.projects=[{id:'A',title:'Alpha',summary:{brief_status:'draft'}}];
 assert.match(h.run('sponsorHome()'),/id="home-results" class="sr-only" role="status" aria-live="polite">1 project/);
 const results={textContent:'',className:'sr-only'},rows={innerHTML:''},clear={hidden:true};
 h.ctx.$=s=>s==='#home-results'?results:s==='#home-project-rows'?rows:s==='[data-action="home-clear"]'?clear:null;
 h.run("homeProjectQuery='missing';updateHomeProjects()");
 assert.equal(results.className,'');assert.equal(results.textContent,'0 projects matching “missing”');assert.equal(clear.hidden,false);assert.match(rows.innerHTML,/No projects match/);
 h.run("homeProjectQuery='';updateHomeProjects()");
 assert.equal(results.className,'sr-only');assert.equal(results.textContent,'1 project');assert.equal(clear.hidden,true);assert.match(rows.innerHTML,/Alpha/);
});

test('sponsor stage and question restore by project while private coach results clear',async()=>{
 const h=harness();Object.assign(h.ctx,{sponsorStage:'brief',sponsorQuestion:'q17',sponsorFit:false,sponsorCoachResult:{id:'private'},sponsorResources:'documents'});h.ctx.state.sponsor={questions:[{id:'q17'}]};h.run('rememberProjectView()');h.ctx.load=async id=>{h.ctx.state.project={id,version:1,title:id};};await h.run("activateProject('B')");assert.equal(h.ctx.sponsorStage,'framing');assert.equal(h.ctx.sponsorCoachResult,null);await h.run("activateProject('A')");assert.equal(h.ctx.sponsorStage,'brief');assert.equal(h.ctx.sponsorQuestion,'q17');assert.equal(h.ctx.sponsorResources,'documents');assert.equal(h.ctx.sponsorCoachResult,null);
});

test('Home restores the universal marquee above projects and keeps detailed orientation available',()=>{
 const h=harness();h.ctx.state.projects=[{id:'A',title:'Alpha',version:1}];const before=JSON.stringify(h.ctx.state),html=h.run('sponsorHome()');
 assert.ok(html.indexOf('id="home-title"')<html.indexOf('id="home-projects"'));assert.match(html,/<h1 id="home-title"[^>]*>Move projects forward/);assert.doesNotMatch(html,/<h1[^>]*>Home<|<h2[^>]*>Home</);
 assert.match(html,/<details class="home-help" id="home-how">/);assert.match(html,/How the workbench supports your project/);
 assert.match(html,/<a[^>]+data-action="project-open"[^>]+data-id="A"/);assert.equal(JSON.stringify(h.ctx.state),before);
});

test('Home provides one creation action beside projects and discloses orientation in place',()=>{
 const h=harness(),html=h.run('sponsorHome()');assert.equal((html.match(/data-action="home-create"/g)||[]).length,1);assert.match(html,/<details class="home-help" id="home-how">/);assert.doesNotMatch(html,/href="#home-how"/);
});

test('Home restores exact bridge subsection and domain working report across browser reload',async()=>{
 const h=harness();Object.assign(h.ctx,{view:'review',bridgeSection:'timeline',bridgeBoard:'business-research',domainWorkMode:'working',domainChatRail:'report'});h.ctx.state.bridge={boards:{'business-research':'Business · Research'}};h.run('rememberProjectView()');
 h.run('projectViews.clear();resetProjectView();restoreProjectView()');assert.equal(h.ctx.view,'review');assert.equal(h.ctx.bridgeSection,'timeline');assert.equal(h.ctx.bridgeBoard,'business-research');assert.equal(h.ctx.domainWorkMode,'working');assert.equal(h.ctx.domainChatRail,'report');
 h.ctx.view='thought-partner';h.run('rememberProjectView();resetProjectView();restoreProjectView()');assert.equal(h.ctx.view,'review');assert.equal(h.ctx.bridgeSection,'timeline');
});
test('retired overview locations fall back to work without hiding valid sponsor question caches',()=>{
 const h=harness();h.run('rememberProjectView()');const cache=JSON.parse(h.storage.get('workbench-view:priya:A:1'));cache.view='overview';h.storage.set('workbench-view:priya:A:1',JSON.stringify(cache));h.run('projectViews.clear();restoreProjectView()');assert.equal(h.ctx.view,'intent');assert.equal(h.ctx.valueFocus,'measures');
});

test('opening a project renders interactive work only after the busy guard is cleared',async()=>{
 const h=harness(),states=[];h.ctx.load=async id=>{h.ctx.state.project={id,version:1,title:id};};h.ctx.$=selector=>selector==='#modal'?{close(){}}:null;h.ctx.render=()=>states.push(h.ctx.busy);await h.run("projectAction('project-open','B')");assert.deepEqual(states,[false]);assert.equal(h.ctx.busy,false);
});


test('project controls and reset context use the name while identity and confirmation stay unchanged',()=>{
 const h=harness(),dialogs=[];h.ctx.selectorChevron=()=>'<svg></svg>';h.ctx.state.project.display_title='WB-007 · v2 — Alpha';h.ctx.modal=(...args)=>dialogs.push(args);
 const picker=h.run('projectControl()');assert.match(picker,/Change project: Alpha/);assert.doesNotMatch(picker,/WB-007/);
 h.run('replaceProjectDialog()');assert.match(dialogs[0][1],/Alpha/);assert.doesNotMatch(dialogs[0][1],/WB-007/);assert.match(dialogs[0][1],/Type the project name to confirm/);assert.equal(h.ctx.state.project.display_title,'WB-007 · v2 — Alpha');
});
test('Home searches readable project references and does not show environment version names',()=>{
 const h=harness();h.ctx.state.actors={priya:{role:'Business sponsor'}};h.ctx.state.projects=[{id:'A',title:'Alpha',reference:'WB-007',display_title:'WB-007 · v2 — Alpha',origin:'Version A',summary:{stage:'Business Intent',brief_status:'draft',needs:[]}}];
 h.run("homeProjectQuery='wb-007'");const html=h.run('homeProjectRows()');assert.match(html,/>Alpha<\/a>/);assert.match(html,/aria-label="Open project: Alpha"/);assert.doesNotMatch(html,/WB-007|Version A|Version B/);assert.equal(h.ctx.state.projects[0].reference,'WB-007');
 h.ctx.row={...h.ctx.state.projects[0],sponsor:'Priya',teams:[],attention:[],assignments:[]};h.run('homePortfolioData={projects:[row]}');
 const portfolio=h.run('homePortfolioRows()');assert.match(portfolio,/>Alpha<\/a>/);assert.doesNotMatch(portfolio,/WB-007|Version A|Version B/);
});

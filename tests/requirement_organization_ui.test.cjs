const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(){
 const row=(id,kind,body,revision=1,scope='project:demo')=>({ref:{id,revision},kind,scope,body});
 const experience=row('DRW-EX','requirement-drawer',{label:'Experience and usability',status:'active'}),operations=row('DRW-OPS','requirement-drawer',{label:'Operations',status:'active'}),child=row('DRW-EX-RESUME','requirement-drawer',{label:'Continuity',parent_id:'DRW-EX',status:'active'}),empty=row('DRW-OPS-SUPPORT','requirement-drawer',{label:'Support and recovery',parent_id:'DRW-OPS',status:'active'});
 const req=row('REQ-RESUME','requirement',{title:'Keep draft progress',text:'Retain entered values after interruption.',acceptance_criteria:'Resuming shows the saved values.',drawer_id:child.ref.id,status:'proposed'}),other=row('REQ-OWNER','requirement',{title:'Name the next owner',text:'Show accepted responsibility.',acceptance_criteria:'An accepted handoff identifies its next owner.',drawer_id:operations.ref.id,status:'approved'});
 const goal=row('GOAL-ONE','goal',{title:'Less repeated entry',outcome:'Resume without repeated work',measure_refs:[{id:'MEASURE-ONE',revision:1}]}),measure=row('MEASURE-ONE','success-measure',{name:'Repeated entry time',goal_ids:[goal.ref.id],definition:'Observed repeated entry after interruption',baseline:'Not measured'});
 const intent=row('INT-ONE','intent',{intake:{in_scope:'Nonurgent draft continuity.',out_scope:'Production execution.',constraints:'Existing access boundaries apply.',dependencies:'A trustworthy saved-state event.',assumptions:'People may otherwise repeat entry.',project_risks:'An unreliable status could mislead the user.',open_questions:'Which event demonstrates accepted responsibility?'}},2),policy=row('POL-ONE','policy',{text:'Existing access boundaries apply.\nOutside scope: Production execution.',status:'user-declared-boundary'},2);
 const c={state:{actor:'sam',actors:{sam:{name:'Sam',role:'Research'}},project:{id:'P',version:1},records:[experience,operations,child,empty,req,other,goal,measure,intent,policy],cases:[],packets:[{id:'PKT-INTENT',revision:2,records:[intent,policy]}],requirement_impacts:{},requirement_assessments:{items:{},standards:[],can_record:false},intake:{cases:[],source_questions:[],setup_governance:{},draft:{ref:{id:'PRIVATE-DRAFT',revision:99},body:{values:{constraints:'PRIVATE NEW CONSTRAINT'},goal_snapshot:{goals:[{body:{title:'PRIVATE GOAL'}}]}}}},domains:{active:'research'}},document:{addEventListener(){},querySelector(){return null;},querySelectorAll(){return[];}},selected:null,requirementsMode:'scaffold',calls:[],command(){c.calls.push('command');},fetch(){c.calls.push('fetch');},head:(title,copy)=>`<h1>${title}</h1><p>${copy}</p>`,button:(title,action,id)=>`<button data-action="${action}" data-id="${id}">${title}</button>`,selectorChevron:()=>'',workspaceNavigation:()=>({review:'Decisions & Issues'}),requirementsSwitch:()=>'<nav>Team input & reviews</nav>',lockedRequirementsSetup:()=>false};
 c.records=kind=>c.state.records.filter(r=>r.kind===kind);c.get=id=>c.state.records.find(r=>r.ref.id===id);
 vm.createContext(c);const app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');
 for(const prefix of ['const esc=','const rid=','const val=','const para='])vm.runInContext(app.split('\n').find(line=>line.startsWith(prefix)),c);
 require('./ui_reference_helpers.cjs')(c);
 for(const name of ['signals.js','goals.js','scaffold.js','requirement-assessments.js','requirement-organization.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/'+name),'utf8'),c);
 return {c,row,req,other,goal,measure,intent,policy,experience,operations,run:code=>vm.runInContext(code,c)};
}
function primary(html){return html.replace(/<details class="record-metadata">[\s\S]*?<\/details>/g,'').replace(/<[^>]*>/g,'');}
test('shared map has three distinct groups and canonical requirement categories with visible closed trackers',()=>{
 const h=harness(),before=JSON.stringify(h.c.state),html=h.run('requirementOrganizationRead(sharedRequirementRows())');
 for(const title of ['Goals and measures','Requirements','Intent factors'])assert.equal((html.match(new RegExp('>'+title+'<','g'))||[]).length,1,title);
 assert.ok(html.indexOf('>Goals and measures<')<html.indexOf('>Requirements<'));assert.ok(html.indexOf('>Requirements<')<html.indexOf('>Intent factors<'));
 assert.match(html,/requirement-organization-category-heading[\s\S]*>Experience and usability</);assert.match(html,/>Operations</);
 const summaries=[...html.matchAll(/<details class="workbench-drawer requirement-record"[^>]*><summary>([\s\S]*?)<\/summary>/g)];
 assert.equal(summaries.length,2);assert.ok(summaries.every(m=>m[1].includes('requirement-drawer-indicator')));assert.doesNotMatch(html,/<details class="workbench-drawer requirement-record"[^>]* open/);
 assert.equal((html.match(/data-action="requirement" data-id="REQ-RESUME"/g)||[]).length,1);assert.match(html,/data-id="DRW-OPS-SUPPORT"/);
 assert.equal(JSON.stringify(h.c.state),before);assert.equal(h.c.calls.length,0);
});
test('goals and measures remain actual published indicator objects and never become requirement rows',()=>{
 const h=harness(),html=h.run('requirementOrganizationRead(sharedRequirementRows())');
 assert.match(html,/Less repeated entry/);assert.match(html,/Repeated entry time/);assert.match(html,/Observed repeated entry/);
 assert.equal((html.match(/<details class="goal-read"/g)||[]).length,1);assert.equal((html.match(/<details class="goal-measure-read"/g)||[]).length,1);
 assert.doesNotMatch(html,/data-requirement="GOAL-ONE"|data-requirement="MEASURE-ONE"|PRIVATE GOAL|PRIVATE NEW CONSTRAINT/);
});
test('intent factors use exact published values and pinned policy metadata with no inferred completeness or duplicate policy body',()=>{
 const h=harness(),html=h.run('requirementOrganizationIntentFactorsRead()');
 for(const text of ['Scope','Constraints','Dependencies','Assumptions','Risks &amp; open decisions','Nonurgent draft continuity.','A trustworthy saved-state event.','Which event demonstrates accepted responsibility?'])assert.ok(html.includes(text),text);
 assert.match(html,/From published Business Intent · v2/);assert.match(html,/INT-ONE:v2/);assert.match(html,/POL-ONE:v2/);
 const bodies=[...html.matchAll(/<details class="requirement-intent-factor">[\s\S]*?<div class="details-body">([\s\S]*?)<\/div><\/details>/g)].map(m=>m[1]).join('');assert.equal((bodies.match(/Existing access boundaries apply\./g)||[]).length,1);assert.doesNotMatch(html,/Current project policy|Complete|Approved|Validated|PRIVATE/);
 assert.doesNotMatch(html,/<details class="requirement-intent-factor"[^>]* open/);assert.doesNotMatch(primary(html),/INT-ONE|POL-ONE/);
});
test('an independently recorded current policy is named separately when no exact intent packet links it',()=>{
 const h=harness();h.c.state.packets=[];h.policy.body.text='A separately recorded public policy boundary.';
 const html=h.run('requirementOrganizationIntentFactorsRead()');assert.match(html,/Current project policy &amp; limits/);assert.match(html,/User-declared boundary/);assert.match(html,/POL-ONE:v2/);assert.match(html,/A separately recorded public policy boundary/);
});
test('category filtering retains native routing and unassigned records are preserved without invented classification',()=>{
 const h=harness();h.c.state.records.push(h.row('UNLINKED','requirement',{title:'An unassigned published condition',text:'A retained independent condition.',acceptance_criteria:'Observe the independent condition.',status:'proposed'}));
 h.run('syncRatifiedRequirementCategory();ratifiedRequirementCategory="DRW-OPS"');const html=h.run('requirementOrganizationRead(sharedRequirementRows())');
 assert.match(html,/data-ratified-category="DRW-EX" hidden/);assert.match(html,/data-ratified-category="DRW-OPS"/);assert.match(html,/data-id="UNLINKED"/);assert.match(html,/An unassigned published condition/);assert.doesNotMatch(html,/>Other requirements<|>Uncategorized</);
});
test('private records, newer private intake and earlier intent versions never replace current shared factors',()=>{
 const h=harness();h.c.state.records.push(h.row('PRIVATE-REQ','requirement',{title:'PRIVATE REQUIREMENT',status:'proposed'},1,'intake:sponsor'),h.row('PRIVATE-GOAL','goal',{title:'PRIVATE GOAL',outcome:'Private outcome'},1,'intake:sponsor'),h.row('INT-ONE','intent',{intake:{constraints:'EARLIER PUBLISHED CONSTRAINT'}},1));
 const html=h.run('requirementOrganizationRead(state.records.filter(r=>r.kind==="requirement"))');assert.doesNotMatch(html,/PRIVATE|EARLIER PUBLISHED CONSTRAINT/);assert.match(html,/Existing access boundaries apply/);
 h.req.body.title='<script>unsafe</script>';const escaped=h.run('requirementOrganizationRead(sharedRequirementRows())');assert.doesNotMatch(escaped,/<script>unsafe/);assert.match(escaped,/&lt;script&gt;/);
});
test('the native requirements entry point keeps team and exact-record routing ahead of the organized map',()=>{
 const h=harness(),app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');
 vm.runInContext(app.slice(app.indexOf('function requirements(){'),app.indexOf('function requirementsToolbar(')),h.c);
 h.c.requirementsToolbar=()=>'<nav>Native category filter and private setup link</nav>';h.c.requirementAuthoritySummary=()=>'<aside>Recorded authority boundary</aside>';h.c.requirementsAcrossDomains=()=>'<section>Native team input</section>';h.c.requirementDetail=r=>'<article>Exact dossier '+r.ref.id+'</article>';
 assert.match(h.run('requirements()'),/requirement-organization/);h.c.requirementsMode='domains';assert.equal(h.run('requirements()'),'<section>Native team input</section>');h.c.selected=h.req.ref.id;assert.equal(h.run('requirements()'),'<article>Exact dossier REQ-RESUME</article>');
});

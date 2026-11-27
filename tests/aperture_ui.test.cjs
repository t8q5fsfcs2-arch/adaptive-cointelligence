const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const src=f=>fs.readFileSync(path.join(__dirname,'../src/workbench/static/'+f),'utf8');
const NAV_PROJECT={intent:'Business Intent',requirements:'Requirements',delivery:'Handoff',review:'Decisions & Issues',home:'Project home'};
const NAV_DOMAIN={contributions:'Workbench',review:'Decisions & Issues',intent:'Business Intent',requirements:'Requirements',home:'Project home'};
const goal=(title='Use clinician time',extra={})=>({kind:'goal',ref:{id:'G-1',revision:1},body:{title,outcome:'Fewer unused appointments',active:true,...extra}});
const measure=name=>({kind:'success-measure',ref:{id:'M-'+name,revision:1},body:{name,active:true}});
const intent=revision=>({kind:'intent',ref:{id:'INT-001',revision},body:{}});
function ctx(o={}){
 const actor=o.actor||'priya',domain=o.domain??(actor==='sam'?'research':actor==='lee'?'design':null);
 const recs=o.records||[];
 const c={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
  view:o.view||'home',selected:o.selected||null,bridgeSection:'overview',caseOpenArea:null,
  state:{actor,actors:{priya:{name:'Dana Okafor'},sam:{name:'Jordan Reyes'},lee:{name:'Mei Chen'},alex:{name:'Sofia Alvarez'},maya:{name:'Tom Becker'}},domains:{active:domain},
   intake:{published:o.published??false,refinements:o.refinements||[],cases:o.intakeCases||[]},bridge:{issues:o.issues||[]},cases:o.cases||[]},
  records:kind=>recs.filter(r=>r.kind===kind),
  projectHomeLatest:kind=>recs.filter(r=>r.kind===kind),
  projectHomeNeeds:()=>o.needs||[],
  workspaceNavigation:()=>domain?NAV_DOMAIN:NAV_PROJECT,
  cockpitAreas:()=>o.areas||[],cockpitQuest:()=>o.quest||'',cockpitChanged:()=>!!o.changed,
  workingDomainPlanStatus:()=>o.plan||'Ready to guide work',chatWork:()=>o.work===false?null:({}),chatTaskGuidance:()=>({next:o.guide||null}),
  caseAreas:()=>o.allAreas||[]};
 vm.createContext(c);vm.runInContext(src('aperture.js'),c);return c;}
const band=c=>vm.runInContext('apertureBand()',c);
const published=(rev=1,more=[])=>[goal(),measure('Missed-appointment rate'),intent(rev),...more];

test('a draft intent puts the sponsor at the Intent stage with one move: publish',()=>{
 let html=band(ctx({view:'home',records:[goal()]}));
 assert.match(html,/data-stage="intent"/);assert.match(html,/data-intent="draft"/);
 assert.match(html,/Business Intent not published/);assert.match(html,/Your draft is private/);
 assert.match(html,/Nobody can work from your intent until you publish it/);
 assert.match(html,/<button type="button" class="aperture-next-button" data-nav="intent">Finish and publish Business Intent<\/button>/);
 assert.match(html,/<li class="is-current" aria-current="step">Intent<\/li>/);
 // Already on Business Intent: the move is stated, not a button that goes nowhere.
 html=band(ctx({view:'intent',records:[goal()]}));
 assert.match(html,/<p class="aperture-next-title">Finish and publish Business Intent<\/p>/);assert.doesNotMatch(html,/aperture-next-button/);
});

test('teams see that nothing can be shared until the intent is published',()=>{
 const html=band(ctx({actor:'sam',view:'home'}));
 assert.match(html,/No goal published yet/);assert.match(html,/Teams start once the sponsor publishes it/);
 assert.match(html,/Business Intent is not published yet/);assert.match(html,/data-nav="contributions">Open your workbench/);
 assert.match(html,/Prepare your plan while the intent is drafted/);
});

test('a draft with reviewers reads as in review',()=>{
 const html=band(ctx({intakeCases:[{kind:'intake-case',ref:{id:'C1',revision:1},body:{status:'in-review'}}]}));
 assert.match(html,/data-intent="in-review"/);assert.match(html,/Business Intent in review/);assert.match(html,/Your draft is with reviewers/);
});

test('a published intent with no team work is the Investigate stage',()=>{
 const html=band(ctx({view:'intent',published:true,records:published(1)}));
 assert.match(html,/data-stage="investigate"/);assert.match(html,/Intent v1 · published/);
 assert.match(html,/Use clinician time/);assert.match(html,/Fewer unused appointments/);assert.match(html,/Measured by Missed-appointment rate/);
 assert.match(html,/No team has shared work against Intent v1 yet/);assert.match(html,/<li class="is-done">Intent<\/li><li class="is-current" aria-current="step">Investigate/);
 assert.match(html,/data-nav="home">See what teams shared/);
 // On Project home itself there is nothing further to open.
 assert.match(band(ctx({view:'home',published:true,records:published(1)})),/You are up to date/);
});

test('an open change request moves everyone to Align and changes each person\'s focus',()=>{
 const refinements=[{ref:{id:'ICR-1',revision:1},body:{status:'open',requested_by:'sam'}}];
 let html=band(ctx({published:true,records:published(1),refinements}));
 assert.match(html,/data-stage="align"/);assert.match(html,/data-intent="change-requested"/);assert.match(html,/Intent v1 · change requested/);
 assert.match(html,/Jordan Reyes asked to change it, citing a published finding/);
 assert.match(html,/data-action="intent-learning">Review the change request/);
 html=band(ctx({actor:'alex',published:true,records:published(1),refinements}));
 assert.match(html,/Requirement approval waits while the intent change request is open/);
});

test('a revised intent names whose finding changed it and keeps the earlier version',()=>{
 const html=band(ctx({actor:'lee',published:true,records:published(2),refinements:[{ref:{id:'ICR-1',revision:3},body:{status:'incorporated',requested_by:'sam'}}]}));
 assert.match(html,/Intent v2 · revised/);assert.match(html,/Changed from Jordan Reyes’s finding\. Earlier versions are kept/);
});

test('open issues put the project in Align and point every role to them',()=>{
 const issues=[{ref:{id:'I1',revision:1},body:{status:'open',title:'Visit types'}}];
 for(const actor of ['priya','sam','alex']){
  const html=band(ctx({actor,published:true,records:published(1),issues}));
  assert.match(html,/data-stage="align"/,actor);assert.match(html,/<a href="#main" data-nav="review">1 open issue between teams\.<\/a>/,actor);
 }
});

test('approved requirements put the project in Deliver; the owner sees ratification and the weakest area',()=>{
 const reqs=[{kind:'requirement',ref:{id:'R1',revision:2},scope:'project:demo',body:{status:'approved'}},{kind:'requirement',ref:{id:'R2',revision:1},scope:'project:demo',body:{status:'proposed'}}];
 const html=band(ctx({actor:'alex',view:'intent',published:true,records:published(1,reqs),allAreas:[{label:'Customer needs',level:'empty',next:'3 parts need evidence'}]}));
 assert.match(html,/data-stage="deliver"/);assert.match(html,/1 of 2 requirements ratified/);
 assert.match(html,/Weakest area: Customer needs · 3 parts need evidence/);assert.match(html,/data-nav="requirements">Review proposed requirements/);
});

test('anything waiting on the person is always the next move',()=>{
 const html=band(ctx({actor:'alex',published:true,records:published(1),needs:[{label:'Decide',title:'Requirement v2',detail:'Reviews are in',attrs:'data-action="case" data-id="CHG-1"'}]}));
 assert.match(html,/data-action="case" data-id="CHG-1">Decide: Requirement v2<\/button>/);assert.match(html,/Reviews are in/);
});

test('on the workbench the band carries the next step, changed inputs, the weakest area and the question',()=>{
 const html=band(ctx({actor:'sam',view:'contributions',published:true,records:published(2),changed:true,plan:'Set up the plan',quest:'Why do patients <miss>?',
  areas:[{id:'DRW-needs',label:'Customer needs',level:'empty',next:'3 parts need evidence'}],guide:{action:'dchat-guidance-context',title:'Review changed inputs',why:'Keep saved work.'}}));
 assert.match(html,/data-action="dchat-guidance-context">Your inputs changed since you started/);
 assert.match(html,/data-action="cockpit-area" data-id="DRW-needs">Customer needs: no shared evidence yet · 3 parts need evidence/);
 assert.match(html,/data-action="dchat-guidance-context" data-id="">Review changed inputs<\/button>/);
 // At most three lines: the question and the plan line give way to what changed and the weakest area.
 assert.equal((html.match(/<li class=/g)||[]).length,3+4);
});

test('on the workbench with no conversation yet, setting up the plan is the next move',()=>{
 const html=band(ctx({actor:'sam',view:'contributions',work:false,plan:'Set up the plan'}));
 assert.match(html,/data-action="pflow-brief">Set up your working plan<\/button>/);assert.match(html,/Working plan: Set up the plan/);
});

test('the band stays off detail pages, record pages and people without a project role',()=>{
 assert.equal(band(ctx({selected:'R1',published:true,records:published(1)})),'');
 assert.equal(band(ctx({view:'decisions',published:true,records:published(1)})),'');
 assert.equal(band(ctx({actor:'maya',published:true,records:published(1)})),'');
});

test('text from records is escaped',()=>{
 const html=band(ctx({published:true,records:[goal('<img src=x>'),intent(1)]}));
 assert.match(html,/&lt;img src=x>/);assert.doesNotMatch(html,/<img/);
});

test('the band is mounted on project screens and replaces the workbench heads-up strip',()=>{
 assert.match(src('app.js'),/\$\{!globalView&&typeof apertureBand==='function'\?apertureBand\(\):''\}\$\{projectStatusLine/);
 assert.match(src('domain-chat.js'),/\$\{typeof apertureBand==='function'\?'':cockpitHud\(\)\}/);
 assert.match(src('index.html'),/<script src="\/aperture\.js" defer><\/script>/);assert.match(src('index.html'),/<link rel="stylesheet" href="\/aperture\.css">/);
});

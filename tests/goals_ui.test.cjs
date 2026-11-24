const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function harness(){const ctx={state:{goals:{goals:[],measures:[],runs:[]},intake:{draft:{body:{values:{value:'Less effort',measures:'Completion rate'}}}},records:[],packets:[],cases:[]},esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,val:(t,v)=>`<label>${t}</label>${String(v).replaceAll('<','&lt;')}`,document:{addEventListener:()=>{}}};ctx.get=id=>ctx.state.records.find(x=>x.ref.id===id);ctx.records=k=>ctx.state.records.filter(x=>x.kind===k);vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8').match(/^const rid=.*$/m)[0],ctx);require('./ui_reference_helpers.cjs')(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/goals.js'),'utf8'),ctx);return {ctx,run:s=>vm.runInContext(s,ctx)};}
test('goals use progressive disclosure with editable fields and no invented targets',()=>{const h=harness();h.ctx.state.goals.goals=[{id:'G-one',body:{title:'Less effort',outcome:'Resume without repeating work',active:true,basis_fields:['value']}}];h.ctx.state.goals.measures=[{id:'M-one',body:{name:'Completion rate',active:true,baseline:'',target:'',goal_ids:['G-one'],basis_fields:['measures']}}];const html=h.run('goalsEditor()');assert.match(html,/Goals & success measures/);assert.match(html,/Calculation or observation/);assert.match(html,/Measurement plan/);assert.match(html,/Goals measured/);assert.doesNotMatch(html,/<details[^>]* open/);assert.doesNotMatch(html,/98%|target reached|Next question/);assert.match(html,/<textarea[^>]*data-goal-field="target"[^>]*><\/textarea>/);});
test('source changes expose an explicit acknowledgement and escape user content',()=>{const h=harness();const html=h.run("goalDraftRow({id:'G-one',body:{title:'<script>bad</script>',outcome:'Improve',basis_fields:['value']},changed_fields:['value']},'goals')");assert.match(html,/Source changed/);assert.match(html,/data-review-basis/);assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);});
test('requirement goal view reads the pinned version, not the latest wording',()=>{const h=harness();h.ctx.state.records=[{ref:{id:'G-one',revision:2},kind:'goal',body:{title:'New title',outcome:'New outcome'}}];h.ctx.state.packets=[{records:[{ref:{id:'G-one',revision:1},kind:'goal',body:{title:'Earlier goal',outcome:'Earlier outcome',measure_refs:[{id:'M-one',revision:1}]}},{ref:{id:'M-one',revision:1},kind:'success-measure',body:{name:'Original measure',baseline:'',target:'',goal_ids:['G-one']}}]}];const html=h.run("linkedGoalsRead({goal_refs:[{id:'G-one',revision:1}]})");assert.match(html,/Earlier outcome/);assert.match(html,/Original measure/);assert.match(html,/Newer version needs review/);assert.doesNotMatch(html,/New outcome|New title/);assert.match(html,/Not yet specified/);assert.match(html,/Outcome not yet evaluated/);});
test('a missing pinned version is explicit and never substituted with latest',()=>{const h=harness();h.ctx.state.records=[{ref:{id:'G-one',revision:2},kind:'goal',body:{title:'New title',outcome:'New outcome'}}];const html=h.run("linkedGoalsRead({goal_refs:[{id:'G-one',revision:1}]})");assert.match(html,/Exact goal version unavailable/);assert.doesNotMatch(html,/New outcome/);});
test('direction snapshots expose goals with related measures and independent constraints remain allowed',()=>{const h=harness();const html=h.run("goalsRead({goals:[{id:'G-one',body:{title:'Improve',outcome:'An outcome'}}],measures:[{body:{name:'Rate',goal_ids:['G-one']}}]})");assert.match(html,/Improve/);assert.match(html,/Rate/);assert.match(html,/Not yet specified/);assert.match(h.run('goalLinkEditor({goal_ids:[]})'),/Policy and constraint requirements can stand independently/);});

test('a KPI with an unavailable linked goal is still visible with its saved measurement fields',()=>{
 const h=harness(),catalog={goals:[],measures:[{ref:{id:'M-retained',revision:5},body:{name:'Retained rate',goal_ids:['G-missing'],baseline:'Fictional 60%',target:'Fictional 85%',definition:'Completed / started'}}]};
 const before=JSON.stringify(catalog),html=h.run('goalsRead('+JSON.stringify(catalog)+')');
 for(const t of ['Retained rate','Fictional 60%','Fictional 85%','Completed / started','Version 5','M-retained:v5'])assert.ok(html.includes(t),t);
 assert.equal(JSON.stringify(catalog),before);
});
test('older title-based measures have a readable name without rewriting saved data',()=>{
 const h=harness(),item={ref:{id:'M-older',revision:1},body:{title:'Evidence-complete closures',definition:'Completed with evidence or an exception',status:'candidate'}},before=JSON.stringify(item);
 const html=h.run('measureRead('+JSON.stringify(item)+')');assert.match(html,/Evidence-complete closures/);assert.match(html,/Completed with evidence or an exception/);assert.equal(JSON.stringify(item),before);
});


test('goals and measures use the same module shell while preserving linked and unlinked measure drawers',()=>{
 const h=harness(),catalog={goals:[{ref:{id:'G',revision:1},body:{title:'Clear handoffs',outcome:'Know the next action'}}],measures:[{ref:{id:'M',revision:2},body:{name:'Waiting time',goal_ids:['G'],baseline:'Unknown'}},{ref:{id:'M-other',revision:1},body:{name:'Separate measure',goal_ids:[]}}]};
 const before=JSON.stringify(catalog),html=h.run('goalsRead('+JSON.stringify(catalog)+')');
 assert.match(html,/class="card section workbench-record-module"/);assert.match(html,/class="workbench-module-header"/);assert.match(html,/class="workbench-module-drawers"/);
 for(const text of ['Clear handoffs','Know the next action','Waiting time','Separate measure','Unknown','Version 2','M:v2'])assert.ok(html.includes(text),text);
 assert.doesNotMatch(html,/<details[^>]* open/);assert.equal(JSON.stringify(catalog),before);
});


test('shared goals identify Business development as their source and expose setup editing only to the sponsor',()=>{
 const h=harness();h.ctx.state.actor='priya';h.ctx.state.records=[{kind:'goal',ref:{id:'G-shared',revision:2},body:{title:'Published outcome',outcome:'Shared definition',measure_refs:[]}}];
 h.ctx.state.goals.goals=[{id:'G-shared',body:{title:'PRIVATE NEW DRAFT'}}];
 let html=h.run('publicGoalsRead()');assert.match(html,/These indicators are developed from answers to the Business development intake questions and published through Requirements set up/);assert.match(html,/Edit in Business development/);assert.match(html,/Published outcome/);assert.doesNotMatch(html,/PRIVATE NEW DRAFT/);
 h.ctx.state.actor='sam';html=h.run('publicGoalsRead()');assert.match(html,/read only/);assert.doesNotMatch(html,/Edit in Business development/);
});

test('indicator sources link exact saved versions and name configured intake questions',()=>{
 const h=harness();h.ctx.state.intake.source_questions=[{id:'q17',title:'Measuring success',field:'measures'}];
 const item={ref:{id:'M-original',revision:2},body:{name:'Rate',basis_fields:['measures'],basis_values:{measures:'Original planned measure'}}};
 h.ctx.state.records=[item];let captured;h.ctx.modal=(title,content)=>{captured={title,content};};
 const html=h.run('indicatorSourceLinks('+JSON.stringify(item)+')');assert.match(html,/Q17 · Measuring success/);assert.match(html,/data-action="goals-source"/);
 const token=encodeURIComponent(JSON.stringify({ref:item.ref,key:'measures',draft:false}));
 h.ctx.state.intake.draft.body.values.measures='NEW PRIVATE ANSWER';h.ctx.state.actor='sam';
 h.run('openIndicatorSource('+JSON.stringify(token)+')');
 assert.match(captured.content,/Original planned measure/);assert.doesNotMatch(captured.content,/NEW PRIVATE ANSWER|Open current/);
 h.ctx.state.records=[{...item,ref:{id:'M-original',revision:3}}];assert.throws(()=>h.run('openIndicatorSource('+JSON.stringify(token)+')'),/unavailable/);
});
test('legacy field links require matching historical question evidence and never guess missing links',()=>{
 const h=harness();h.ctx.state.intake.source_questions=[{id:'q6',title:'Pain points',field:'pain_points',legacy_field:'bottlenecks'}];
 const item={ref:{id:'G',revision:1},body:{basis_fields:['bottlenecks'],basis_values:{bottlenecks:'Saved pain'},source_case:{id:'CASE',revision:3}}};
 assert.equal(h.run('indicatorSourceQuestion('+JSON.stringify(item)+',"bottlenecks")'),null);
 h.ctx.state.intake.cases=[{ref:{id:'CASE',revision:4},body:{snapshot:{values:{bottlenecks:'Saved pain'},sponsor_brief:{answers:{q6:{items:['Saved pain'],roles:[]}}}}}}];
 assert.equal(h.run('indicatorSourceQuestion('+JSON.stringify(item)+',"bottlenecks").id'),'q6');
 h.ctx.state.intake.cases[0].body.snapshot.sponsor_brief.answers.q6.items=['Different answer'];
 assert.equal(h.run('indicatorSourceQuestion('+JSON.stringify(item)+',"bottlenecks")'),null);
 assert.match(h.run('indicatorSourceLinks({body:{basis_fields:[]}})'),/have not been linked/);
});
test('draft and shared goal and measure drawers expose source links without the prepare header action',()=>{
 const h=harness(),item={id:'G-one',ref:{id:'DRAFT-G-one',revision:2},body:{title:'Goal',outcome:'Improve',basis_fields:['value'],basis_values:{value:'Less effort'}}};
 h.ctx.state.goals.goals=[item];
 let html=h.run('goalsEditor({planning:true})');assert.match(html,/Source intake questions/);assert.doesNotMatch(html,/Prepare from intake/);
 html=h.run('goalsEditor()');assert.doesNotMatch(html,/Prepare from intake/);
 const shared={...item,id:undefined,ref:{id:'G-one',revision:1}};
 html=h.run('goalsRead({goals:['+JSON.stringify(shared)+'],measures:[]})');assert.match(html,/Source intake questions/);
 html=h.run('measureRead('+JSON.stringify({...shared,body:{...shared.body,name:'Rate'}})+')');assert.match(html,/Source intake questions/);
});
test('sponsor source titles go straight to their question while saved answers and role boundaries remain separate',async()=>{
 const h=harness(),item={ref:{id:'M',revision:1},body:{name:'Rate',basis_fields:['measures'],basis_values:{measures:'Original answer'}}};
 h.ctx.state.records=[item];h.ctx.state.intake.source_questions=[{id:'q17',title:'Success metrics',field:'measures'}];h.ctx.state.actor='priya';h.ctx.state.sponsor={};
 let html=h.run('indicatorSourceLinks('+JSON.stringify(item)+')');
 assert.match(html,/data-action="goals-source-current"[^>]*>Q17 · Success metrics/);assert.match(html,/Saved answer for Q17 · Success metrics/);
 let route,focused=false,scrolled=false,opened=false;
 h.ctx.sponsorAction=async(action,id)=>{route={action,id};};h.ctx.modal=()=>{opened=true;};
 h.ctx.document.querySelector=selector=>selector==='#modal'?{open:false}:selector==='#sponsor-editor h2'?{focus:()=>{focused=true;},scrollIntoView:()=>{scrolled=true;}}:null;
 const token=encodeURIComponent(JSON.stringify({ref:item.ref,key:'measures',draft:false}));
 await h.run('goalsAction("goals-source-current",'+JSON.stringify(token)+')');
 assert.deepEqual(route,{action:'sponsor-question',id:'q17'});assert.ok(focused&&scrolled);assert.equal(opened,false);
 h.ctx.state.actor='sam';h.ctx.state.sponsor=null;html=h.run('indicatorSourceLinks('+JSON.stringify(item)+')');assert.doesNotMatch(html,/goals-source-current/);assert.match(html,/data-action="goals-source"/);
});

test('closed Goal and Success measure headings identify their role and name explicitly linked goals',()=>{
 const h=harness(),goals=[{id:'G-a',body:{title:'Recover work'}},{id:'G-b',body:{title:'Reduce repeated entry'}}],measure={id:'M-one',body:{name:'Completion rate',goal_ids:['G-a','G-b'],basis_fields:[]}},before=JSON.stringify({goals,measure});h.ctx.state.goals.goals=goals;
 const goal=h.run('goalDraftRow('+JSON.stringify(goals[0])+',"goals",{planning:true})'),draft=h.run('goalDraftRow('+JSON.stringify(measure)+',"measures",{planning:true})');
 assert.match(goal,/<span class="workbench-object-type">Goal<\/span>/);assert.match(draft,/<span class="workbench-object-type">Success measure<\/span>/);assert.match(draft,/Supports goals: Recover work · Reduce repeated entry/);assert.doesNotMatch(draft,/KPI: Completion rate/);assert.equal(JSON.stringify({goals,measure}),before);
});
test('shared measure goal names use the supplied public catalog and never private draft names',()=>{
 const h=harness(),catalog={goals:[{kind:'goal',scope:'project:demo',ref:{id:'G-a',revision:1},body:{title:'Public outcome',outcome:'Published meaning'}},{kind:'goal',scope:'intake:private',ref:{id:'G-private',revision:1},body:{title:'PRIVATE CATALOG GOAL'}}],measures:[{kind:'success-measure',scope:'project:demo',ref:{id:'M',revision:1},body:{name:'Rate',goal_ids:['G-a','G-private']}},{kind:'success-measure',scope:'project:demo',ref:{id:'M-unlinked',revision:1},body:{name:'Separate rate',goal_ids:[]}}]};
 h.ctx.state.goals.goals=[{id:'G-a',body:{title:'PRIVATE DRAFT NAME'}}];h.ctx.catalog=catalog;const before=JSON.stringify(h.ctx.state),source=JSON.stringify(catalog),html=h.run('goalsRead(catalog,"Goals",2,true,{tileCovers:true})');
 assert.match(html,/Supports goals: Public outcome · Linked goal unavailable/);assert.match(html,/>No goal linked</);assert.doesNotMatch(html,/PRIVATE CATALOG GOAL|PRIVATE DRAFT NAME/);assert.match(html,/<span class="workbench-object-type">Success measure<\/span>/);assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(JSON.stringify(catalog),source);
});
test('historical measure support names stay pinned instead of borrowing current or private goal wording',()=>{
 const h=harness(),oldGoal={kind:'goal',scope:'project:demo',ref:{id:'G-a',revision:1},body:{title:'Earlier outcome',outcome:'Earlier intent',measure_refs:[{id:'M',revision:1}]}},oldMeasure={kind:'success-measure',scope:'project:demo',ref:{id:'M',revision:1},body:{name:'Earlier rate',goal_ids:['G-a','G-b']}};
 h.ctx.state.records=[{...oldGoal,ref:{id:'G-a',revision:2},body:{title:'CURRENT NAME',outcome:'Current intent'}},{kind:'goal',scope:'project:demo',ref:{id:'G-b',revision:9},body:{title:'UNPINNED CURRENT GOAL'}}];h.ctx.state.goals.goals=[{id:'G-b',body:{title:'PRIVATE GOAL'}}];h.ctx.state.packets=[{records:[oldGoal,oldMeasure]}];
 const before=JSON.stringify(h.ctx.state),html=h.run('linkedGoalsRead({goal_refs:[{id:"G-a",revision:1}]})');assert.match(html,/Supports goals: Earlier outcome · Linked goal unavailable/);assert.match(html,/Newer version needs review/);assert.doesNotMatch(html,/CURRENT NAME|UNPINNED CURRENT GOAL|PRIVATE GOAL/);assert.match(html,/<span class="workbench-object-type">Goal<\/span>/);assert.match(html,/<span class="workbench-object-type">Success measure<\/span>/);assert.equal(JSON.stringify(h.ctx.state),before);
});
test('standalone measures and map callbacks keep missing relationships honest without showing identifiers',()=>{
 const h=harness(),items=[{body:{name:'Unlinked rate',goal_ids:[]}},{body:{name:'Linked rate',goal_ids:['SECRET-GOAL-ID']}}];h.ctx.items=items;h.ctx.state.goals.goals=[{id:'SECRET-GOAL-ID',body:{title:'PRIVATE UNSUPPLIED NAME'}}];const html=h.run('items.map(measureRead).join("")');assert.match(html,/>No goal linked</);assert.match(html,/>Linked goal unavailable</);assert.doesNotMatch(html,/SECRET-GOAL-ID|PRIVATE UNSUPPLIED NAME/);assert.equal((html.match(/workbench-object-type">Success measure/g)||[]).length,2);
 const goal={kind:'goal',ref:{id:'G',revision:1},body:{title:'Exact linked outcome',measure_refs:[{id:'M',revision:2}]}},measure={kind:'success-measure',ref:{id:'M',revision:2},body:{name:'Pinned rate',goal_ids:[]}};h.ctx.goal=goal;h.ctx.measure=measure;
 assert.match(h.run('measureRead(measure,{goals:[goal],shared:true})'),/Supports goal: Exact linked outcome/);measure.ref.revision=3;assert.match(h.run('measureRead(measure,{goals:[goal],shared:true})'),/>No goal linked</);
});

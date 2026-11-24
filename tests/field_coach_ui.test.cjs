const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../src/workbench/static/field-coach.js'),'utf8');
function harness(){
 const library=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/workbench/config/field_guidance.json')));
 const fields=[{dataset:{goalField:'name'},value:'Completion'},{dataset:{goalField:'definition'},value:'Original response',isConnected:true,dispatchEvent(){}}];
 const row={querySelectorAll:s=>s==='[data-goal-field]'?fields:[]};
 const c={state:{intake:{draft:{ref:{id:'INTAKE-001',revision:1}}},field_guidance:library},document:{addEventListener(){},querySelector:()=>null},command:async()=>({output:{assessment:'Advice',why_it_matters:'Reason',next_question:'',suggested_wording:'Suggested response'},mode:'simulated'}),pageDirty:false,toast(){},selectorChevron:()=>'<svg class="ui-selector-chevron" aria-hidden="true"></svg>',Event:class{},row,fields};vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8').match(/^const rid=.*$/m)[0],c);require('./ui_reference_helpers.cjs')(c);vm.runInContext(code,c);vm.runInContext("fieldCoachSelection={mode:'draft',kind:'measure',id:'M-one',field:'definition',el:fields[1],row}",c);return {c,run:s=>vm.runInContext(s,c)};
}
test('uses working field content, without saving first or altering other fields',async()=>{const h=harness();let sent;h.c.command=async(a,d)=>{sent={a,d};return {output:{assessment:'Fine',suggested_wording:'Better'},mode:'simulated'};};await h.run("fieldCoachAction('field-coach-review')");assert.equal(sent.d.working.definition,'Original response');assert.equal(sent.a,'field-coach');assert.equal(h.c.pageDirty,false);assert.equal(h.c.fields[1].value,'Original response');});
test('an edit while review is pending makes its suggested wording inapplicable',async()=>{const h=harness();let finish;h.c.command=()=>new Promise(r=>finish=r);const p=h.run("fieldCoachAction('field-coach-review')");h.c.fields[1].value='New human wording';finish({output:{suggested_wording:'Old suggestion'}});await p;assert.equal(h.run('coachAdviceCurrent()'),false);await assert.rejects(h.run("fieldCoachAction('field-coach-use')"),/response changed/);assert.equal(h.c.fields[1].value,'New human wording');});
test('switching context during a request does not deliver old advice to the new field',async()=>{const h=harness();let finish;h.c.command=()=>new Promise(r=>finish=r);const p=h.run("fieldCoachAction('field-coach-review')");h.run("fieldCoachEpoch++;fieldCoachSelection={...fieldCoachSelection,field:'target'}");finish({output:{suggested_wording:'Stale'}});await p;assert.equal(h.run('fieldCoachAdvice'),null);});
test('applying explicit advice changes only the chosen field and remains an editable unsaved draft',async()=>{const h=harness();await h.run("fieldCoachAction('field-coach-review')");await h.run("fieldCoachAction('field-coach-use')");assert.equal(h.c.fields[0].value,'Completion');assert.equal(h.c.fields[1].value,'Suggested response');assert.equal(h.c.pageDirty,true);assert.equal(h.run('coachAdviceCurrent()'),false);});
test('model failure is visible and leaves the response intact',async()=>{const h=harness();h.c.command=async()=>{throw Error('Provider unavailable');};await h.run("fieldCoachAction('field-coach-review')");assert.equal(h.run('fieldCoachAdvice.error'),'Provider unavailable');assert.equal(h.c.fields[1].value,'Original response');assert.equal(h.run('fieldCoachPending'),false);});
test('record requests use exact refs and never send a client override',()=>{const h=harness();h.run("fieldCoachSelection={mode:'record',kind:'requirement',id:'REQ-one',field:'text',record:{ref:{id:'REQ-one',revision:3}}}");assert.equal(h.run('coachPayload().expected.revision'),3);assert.equal(h.run('coachPayload().working'),undefined);});

function connectionHarness(){
 const h=harness(),c=h.c;
 c.state.intake.draft.body={values:{value:'Less effort',need:'Lost progress',jobs:'Resume work'}};
 c.links=[{dataset:{basisField:'value'},checked:true},{dataset:{basisField:'need'},checked:false},{dataset:{basisField:'jobs'},checked:false}];
 c.row.isConnected=true;c.row.querySelectorAll=s=>s==='[data-goal-field]'?c.fields:s==='[data-basis-field]:checked'?c.links.filter(x=>x.checked):s==='[data-basis-field]'?c.links:[];
 c.status={textContent:''};c.row.querySelector=()=>c.status;c.refreshBasisSummary=()=>{};
 c.document.querySelectorAll=()=>[{dataset:{basisSuggestion:'need'}}];
 c.command=async action=>action==='field-coach-check'?{current:true}:{ref:{id:'ADVICE-one',revision:1},mode:'simulated',output:{assessment:'A useful connection',why_it_matters:'Explains the goal',next_question:'',suggested_wording:'',basis_suggestions:[{field:'need',reason:'Explains the effort',source_answer:'Lost progress'}]}};
 h.run("fieldCoachSelection.field='basis_fields'");return h;
}
test('recommended connections stay proposals until explicitly used, preserving existing links',async()=>{
 const h=connectionHarness();await h.run("fieldCoachAction('field-coach-review')");assert.equal(h.c.links[1].checked,false);assert.equal(h.c.pageDirty,false);
 await h.run("fieldCoachAction('field-coach-use-links')");assert.equal(h.c.links[0].checked,true);assert.equal(h.c.links[1].checked,true);assert.equal(h.c.links[2].checked,false);
 assert.equal(h.c.fields[1].value,'Original response');assert.equal(h.c.pageDirty,true);assert.match(h.c.status.textContent,/save draft/);
});
test('an answer or selected-link change invalidates intake connection suggestions',async()=>{
 for(const edit of ['answer','link']){
  const h=connectionHarness();await h.run("fieldCoachAction('field-coach-review')");
  if(edit==='answer')h.c.state.intake.draft.body.values.need='Different need';else h.c.links[0].checked=false;
  await assert.rejects(h.run("fieldCoachAction('field-coach-use-links')"),/response changed/);assert.equal(h.c.links[1].checked,false);
 }
});
test('server-side stale advice and concurrent typing never apply old intake connections',async()=>{
 const h=connectionHarness();await h.run("fieldCoachAction('field-coach-review')");h.c.command=async()=>{throw Error('Intake changed');};
 await assert.rejects(h.run("fieldCoachAction('field-coach-use-links')"),/Intake changed/);assert.equal(h.c.links[1].checked,false);
 let finish;h.c.command=()=>new Promise(r=>finish=r);const pending=h.run("fieldCoachAction('field-coach-use-links')");h.c.fields[1].value='New outcome';finish({current:true});
 await assert.rejects(pending,/response changed/);assert.equal(h.c.links[1].checked,false);
});
test('connection suggestions escape source content and reasons',()=>{
 const h=connectionHarness();h.c.esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');h.c.intakeAnswerLabel=k=>k;
 const html=h.run(`coachBasisSuggestions(fieldCoachSelection,{basis_suggestions:[{field:'need',reason:'<script>bad</script>',source_answer:'<img src=x onerror=bad>'}]},false)`);
 assert.doesNotMatch(html,/<script>|<img/);assert.match(html,/Read saved answer/);assert.match(html,/Use selected connections/);
});

test('connection feedback leads with actionable reasons instead of a generic technical assessment',()=>{
 const h=connectionHarness();h.c.esc=s=>String(s??'');h.c.intakeAnswerLabel=k=>k;
 const html=h.run(`coachAdviceBody(fieldCoachSelection,{assessment:'A long basis_fields assessment',why_it_matters:'Repeated explanation',next_question:'Which field?',basis_suggestions:[{field:'need',reason:'Explains reporting effort',source_answer:'Lost progress'}]},false)`);
 assert.match(html,/Suggested connections/);assert.match(html,/Explains reporting effort/);assert.match(html,/Read saved answer/);
 assert.doesNotMatch(html,/basis_fields|Repeated explanation|Which field/);
 const wording=h.run(`coachAdviceBody({...fieldCoachSelection,field:'outcome'},{assessment:'Clarify the outcome',why_it_matters:'Make the goal observable',next_question:'Who benefits?'},false)`);
 assert.match(wording,/Clarify the outcome/);assert.match(wording,/Who benefits/);
});


test('AI partner identity stays visible while selected field guidance remains specific',()=>{
 const h=harness(),panel={innerHTML:'',querySelector:()=>null};
 h.c.document.querySelector=selector=>selector==='#field-coach'?panel:null;
 h.c.view='planning';h.c.esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 h.run('fieldCoachSelection=null;paintFieldCoach()');
 assert.match(panel.innerHTML,/<h2 id="field-coach-title" class="thought-partner-title">AI partner<\/h2>/);assert.doesNotMatch(panel.innerHTML,/ws-ai-mark/);
 assert.doesNotMatch(panel.innerHTML,/A little guidance/);
 h.run("fieldCoachSelection={mode:'draft',kind:'measure',id:'M-one',field:'definition',el:fields[1],row};paintFieldCoach()");
 assert.match(panel.innerHTML,/AI partner/);assert.match(panel.innerHTML,/<h3 class="coach-field-title">/);
 const fieldTitle=h.c.state.field_guidance.groups.measure.definition.title;assert.ok(panel.innerHTML.includes(fieldTitle));
 assert.match(panel.innerHTML,/Completion/);assert.match(panel.innerHTML,/class="reviewer-speaker">You/);
 assert.equal(h.c.fields[1].value,'Original response');assert.equal(h.c.pageDirty,false);
});

test('all roles browse only the same published items on Requirements',()=>{
 const h=harness();h.c.view='requirements';h.c.state.records=[{kind:'requirement',scope:'project:demo',ref:{id:'REQ',revision:3},body:{title:'Published wording',status:'approved'}},{kind:'requirement',scope:'project:demo',ref:{id:'PROPOSED',revision:2},body:{title:'Candidate wording',status:'proposed'}},{kind:'goal',scope:'project:demo',ref:{id:'G',revision:2},body:{title:'Published goal'}},{kind:'success-measure',scope:'project:demo',ref:{id:'M',revision:1},body:{name:'Published measure'}},...['requirement','goal','success-measure'].map((kind,i)=>({kind,scope:'domain:research',ref:{id:'PRIVATE-'+i,revision:1},body:{title:'PRIVATE RECORD'}})),{kind:'requirement',ref:{id:'UNSCOPED',revision:1},body:{title:'Unscoped record',status:'proposed'}}];
 h.c.state.goals={goals:[{id:'PRIVATE',body:{title:'PRIVATE DRAFT'}}],measures:[]};
 const before=JSON.stringify(h.c.state);let baseline;
 for(const actor of ['priya','sam','lee','alex','maya']){
  h.c.state.actor=actor;const items=JSON.stringify(h.run('coachBrowseItems()'));if(!baseline)baseline=items;assert.equal(items,baseline);assert.doesNotMatch(items,/PRIVATE|UNSCOPED/);assert.match(items,/Candidate wording/);assert.equal(h.run('coachBrowseItems().length'),4);
 }
 delete h.c.state.actor;assert.equal(JSON.stringify(h.c.state),before);
 h.c.state.actor='priya';h.c.view='planning';assert.match(JSON.stringify(h.run('coachBrowseItems()')),/PRIVATE/);
});
test('published reviewer selects proposed exact wording without enabling edits or changing saved work',async()=>{
 const h=harness(),panel={innerHTML:'',querySelector:()=>null};h.c.view='requirements';h.c.state.actor='priya';h.c.state.records=[{kind:'requirement',scope:'project:demo',ref:{id:'APPROVED',revision:2},body:{title:'Ratified wording',text:'Keep the accepted wording',status:'approved'}},{kind:'requirement',scope:'project:demo',ref:{id:'PENDING',revision:4},body:{title:'Pending wording',text:'A hypothesis to review',status:'proposed'}},{kind:'requirement',scope:'intake:priya',ref:{id:'PRIVATE',revision:1},body:{title:'Private wording',status:'proposed'}}];
 h.c.esc=v=>String(v??'');h.c.document.querySelector=s=>s==='#field-coach'?panel:null;
 const calls=[];h.c.command=async(...args)=>{calls.push(args);throw Error('Unexpected call');};
 const before=JSON.stringify(h.c.state);assert.match(JSON.stringify(h.run('coachRecordOptions()')),/Ratified wording/);assert.match(JSON.stringify(h.run('coachRecordOptions()')),/Pending wording/);assert.doesNotMatch(JSON.stringify(h.run('coachRecordOptions()')),/Private wording/);
 h.run("fieldCoachSelection=null;selectCoachRecord('PENDING')");assert.equal(h.run('fieldCoachSelection.mode'),'record');assert.equal(h.run('coachPayload().expected.revision'),4);assert.equal(h.run('coachPayload().working'),undefined);
 assert.match(panel.innerHTML,/<p class="caption coach-item-name">Pending wording<\/p>/);assert.match(panel.innerHTML,/Carry concern to Decisions & Issues/);assert.match(panel.innerHTML,/does not edit or approve/);assert.doesNotMatch(panel.innerHTML,/Use this wording|data-action="approve"|data-action="decide"/);
 await assert.rejects(h.run("fieldCoachAction('field-coach-use')"),/response changed/);assert.equal(calls.length,0);assert.equal(h.c.pageDirty,false);assert.equal(JSON.stringify(h.c.state),before);
 h.run("selectCoachRecord('PRIVATE')");assert.equal(h.run('fieldCoachSelection'),null);
 h.run("selectCoachRecord('APPROVED')");assert.doesNotMatch(panel.innerHTML,/<p class="caption coach-item-name">Proposed/);assert.equal(JSON.stringify(h.c.state),before);
});
test('published reviewer mounts for proposed requirements or public outcomes and stays absent for private-only options',()=>{
 for(const kind of ['requirement','goal','success-measure','private-only']){
  const h=harness();h.c.view='requirements';h.c.selected=null;h.c.get=()=>null;h.c.ratifiedRequirementRows=()=>[];
  h.c.state.records=[{kind:kind==='private-only'?'requirement':kind,scope:kind==='private-only'?'domain:research':'project:demo',ref:{id:'ITEM',revision:1},body:{title:'Saved item',status:'proposed'}}];
  h.c.state.goals={goals:[{id:'PRIVATE',body:{title:'Private sponsor draft'}}],measures:[]};const before=JSON.stringify(h.c.state),mounted=[];
  const main={children:[],append(){}};h.c.document.querySelector=s=>s==='#main'?main:null;h.c.document.createElement=()=>({append(){},insertAdjacentHTML(position,html){mounted.push(html);}});
  h.run('mountFieldCoach()');assert.equal(mounted.length,kind==='private-only'?0:1,kind);if(mounted.length)assert.match(mounted[0],/id="field-coach"/);assert.equal(JSON.stringify(h.c.state),before);
 }
});
test('published review explains its read-only role and offers Decisions & Issues without changing a record',()=>{
 const h=harness(),panel={innerHTML:'',querySelector:()=>null};h.c.view='requirements';h.c.state.actor='sam';h.c.state.records=[];h.c.esc=v=>String(v??'');h.c.document.querySelector=selector=>selector==='#field-coach'?panel:null;
 h.run('fieldCoachSelection=null;paintFieldCoach()');assert.match(panel.innerHTML,/Discuss an item/);assert.match(panel.innerHTML,/<option value="">Select an item<\/option>/);assert.match(panel.innerHTML,/does not edit or approve/);assert.match(panel.innerHTML,/data-nav="review"/);assert.doesNotMatch(panel.innerHTML,/what to include and why it matters|Choose a published requirement, goal or measure|Review explains or questions the published item/);
 const item={kind:'requirement',scope:'project:demo',ref:{id:'REQ',revision:2},body:{text:'Published requirement',status:'approved'}};h.c.state.records=[item];const before=JSON.stringify(item);
 h.run("fieldCoachSelection={mode:'record',kind:'requirement',id:'REQ',field:'text',record:state.records[0]};paintFieldCoach()");
 assert.match(panel.innerHTML,/>Ask<\/button>/);assert.match(panel.innerHTML,/data-reviewer-draft="field-coach"/);assert.doesNotMatch(panel.innerHTML,/Coach this response|Use this wording/);assert.equal(JSON.stringify(item),before);
});

test('carry concern prepares exact proposed requirement context without a model call or automatic issue publication',async()=>{
 const h=harness(),req={kind:'requirement',scope:'project:demo',ref:{id:'REQ',revision:3},body:{text:'A published requirement',status:'proposed'}},sent=[];h.c.view='requirements';h.c.state.records=[req];h.c.document.querySelector=selector=>selector==='#field-coach-question'?{value:'Who confirms ownership?'}:null;
 h.run("fieldCoachSelection={mode:'record',kind:'requirement',id:'REQ',field:'text',record:state.records[0]};fieldCoachAdvice={ref:{id:'ADVICE',revision:1},stamp:coachStamp()};");
 const prepared={ref:{id:'HANDOFF',revision:1},title:'Concern',question:'Who confirms ownership?',consequence:'Ownership could be unclear'};h.c.command=async(a,d)=>{sent.push({a,d});return prepared;};let preview;h.c.bridgeRaiseForm=d=>{preview=d;};
 await h.run("fieldCoachAction('field-coach-handoff')");assert.equal(sent.length,1);assert.equal(sent[0].a,'field-coach-concern-prepare');assert.equal(sent[0].d.requirement.revision,3);assert.equal(sent[0].d.advice.id,'ADVICE');assert.equal(preview.handoff,prepared);assert.equal(preview.question,'Who confirms ownership?');assert.equal(h.c.pageDirty,false);assert.equal(req.body.text,'A published requirement');
});

test('a concern on a new target never carries retained AI advice from an earlier field or requirement',async()=>{
 const h=harness(),sent=[];h.c.view='requirements';h.c.state.records=[{kind:'requirement',scope:'project:demo',ref:{id:'B',revision:2},body:{text:'Second requirement'}}];h.c.document.querySelector=s=>s==='#field-coach-question'?{value:'Human concern about B'}:null;
 h.run("fieldCoachSelection={mode:'record',kind:'requirement',id:'B',field:'text',record:state.records[0]};fieldCoachAdvice={ref:{id:'ADVICE-A',revision:1},stamp:'Earlier target'}");h.c.command=async(a,d)=>{sent.push(d);return {title:'Concern',question:d.question};};h.c.bridgeRaiseForm=()=>{};
 await h.run("fieldCoachAction('field-coach-handoff')");assert.equal(sent[0].requirement.id,'B');assert.equal(sent[0].question,'Human concern about B');assert.equal(sent[0].advice,undefined);
});

test('page questions freeze only exact public context without requiring an item or changing records',async()=>{
 const h=harness(),question={value:'What remains uncertain on this page?'};h.c.view='requirements';h.c.state.actor='sam';h.c.state.records=[
  {kind:'requirement',scope:'project:demo',ref:{id:'R',revision:2},body:{title:'Public'}},
  {kind:'intent',scope:'project:demo',ref:{id:'I',revision:3},body:{text:'Public intent'}},
  {kind:'requirement',scope:'domain:research',ref:{id:'PRIVATE',revision:1},body:{title:'Private'}}];
 h.c.document.querySelector=s=>s==='#field-coach-question'?question:null;h.run('fieldCoachSelection=null');
 const before=JSON.stringify(h.c.state);let sent;h.c.command=async(a,d)=>{sent={a,d};return {output:{assessment:'Advice'},ref:{id:'A',revision:1}};};
 await h.run("fieldCoachAction('field-coach-review')");assert.equal(sent.d.mode,'project');assert.equal(sent.d.question,question.value);assert.deepEqual(JSON.parse(JSON.stringify(sent.d.basis)),[{id:'I',revision:3},{id:'R',revision:2}]);assert.equal(JSON.stringify(h.c.state),before);assert.equal(h.c.pageDirty,false);
});

test('pending page questions stay editable, serialize sending and preserve the next question across local selection',async()=>{
 const h=harness(),question={value:'First question'};h.c.view='requirements';h.c.state.records=[];h.c.document.querySelector=s=>s==='#field-coach-question'?question:null;h.run('fieldCoachSelection=null');
 let finish,calls=0;h.c.command=()=>{calls++;return new Promise(r=>finish=r);};const first=h.run("fieldCoachAction('field-coach-review')");
 question.value='Next question';await h.run("fieldCoachAction('field-coach-review')");assert.equal(calls,1);h.run("selectFieldCoach({mode:'record',kind:'requirement',id:'NEXT',field:'text',record:{ref:{id:'NEXT',revision:1},body:{text:'Other'}}})");
 assert.equal(question.value,'Next question');finish({output:{assessment:'Earlier response'}});await first;assert.equal(question.value,'Next question');assert.equal(h.run('fieldCoachAdvice'),null);assert.equal(h.run('fieldCoachPending'),false);
});

test('draft-page context stays bound to the saved sponsor version and blank generic questions never send',async()=>{
 const h=harness();h.c.view='planning';h.c.state.actor='priya';h.run('fieldCoachSelection=null');assert.equal(h.run('coachPayload().mode'),'draft-page');assert.equal(h.run('coachPayload().expected.id'),'INTAKE-001');
 h.c.state.actor='sam';assert.equal(h.run('coachPayload().mode'),'project');let calls=0;h.c.command=async()=>{calls++;};await assert.rejects(h.run("fieldCoachAction('field-coach-review')"),/Enter a question/);assert.equal(calls,0);
});

const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(actor='priya'){
 const draft={ref:{id:'INTAKE-001',revision:3},body:{title:'Test intake',values:{value:'A bounded value hypothesis',research_question:'What do users need?'},scaffold:[{included:true}],goal_snapshot:{goals:[],measures:[]}}};
 const ctx={state:{actor,actors:{},intake:{draft,cases:[],preflight:{blockers:[],packages:[]}},domains:{active:actor==='sam'?'research':'design',profiles:[],handoffs:[]}},selected:null,view:'preflight',intakeStep:'value',valueReview:false,valueCoachMode:'question',
 ref:r=>r.id+':v'+r.revision,esc:v=>String(v??'').replaceAll('<','&lt;'),label:r=>r.id+':v'+r.revision,head:(t,s,a='')=>`<h1>${t}</h1>${s}${a}`,tag:(s,t)=>`<span class="${t}">${s}</span>`,button:(t,a,id='')=>`<button data-action="${a}" data-id="${id}">${t}</button>`,para:s=>`<p>${s}</p>`,val:(t,s)=>`<label>${t}</label>${s}`,date:s=>s||'',intakeSnapshot:b=>'EXACT SNAPSHOT:'+b.title,
 domainFieldLabels:{},recordList:[],records:k=>ctx.recordList.filter(r=>r.kind===k),domainInfo:()=>ctx.state.domains,domainProfile:()=>ctx.state.domains.profiles[0],
 domainPreflightScreen:()=>ctx.domainPreflightArea(),abandonIntakeEdits:()=>true,render(){},domainText:(n,t,v)=>`<label>${t}</label><textarea name="${n}">${v}</textarea>`,modal:(t,b,submit,callback)=>ctx.dialog={t,b,submit,callback},command:async(a,data)=>{ctx.calls.push({a,data});return {id:'SAVED',message:'Saved'};},calls:[]
 };ctx.state.domains.profiles=[{key:ctx.state.domains.active,config:{label:actor==='sam'?'Research':'Design',criteria:['Bound claims'],downstream_questions:'What must the recipient know?'}}];
 vm.createContext(ctx);require('./ui_reference_helpers.cjs')(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/packets.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/preflight.js'),'utf8'),ctx);
 return {ctx,run:s=>vm.runInContext(s,ctx),draft};
}
function packageFor(h,current=true){const p={ref:{id:'PREF',revision:1},current,body:{snapshot:h.draft.body,draft:h.draft.ref,handoff:{research_focus:'Research priority',design_focus:'Design priority',open_questions:'Limits open'},at:'Today'}};h.ctx.state.intake.preflight.packages=[p];return p;}
test('sponsor area communicates private preparation and separate shared decisions',()=>{
 const h=harness(),html=h.run('preflightScreen()');assert.match(html,/Business sponsor preflight/);assert.match(html,/Prepare sponsor package/);assert.match(html,/Private previews/);assert.match(html,/Uploaded documents and private AI partner conversations stay private/);assert.doesNotMatch(html,/Publish contribution/);
 h.ctx.state.intake.preflight.blockers=['Review the value proposition'];assert.match(h.run('preflightScreen()'),/Review the value proposition/);assert.doesNotMatch(h.run('preflightScreen()'),/>Prepare sponsor package</);assert.match(h.run('preflightScreen()'),/data-action="preflight-value-review"/);
});
test('prepared snapshot has explicit sharing action; stale and shared packages cannot share again',()=>{
 const h=harness(),p=packageFor(h);h.ctx.selected='PREF';let html=h.run('preflightScreen()');assert.match(html,/EXACT SNAPSHOT:Test intake/);assert.match(html,/Share for direction review/);assert.match(html,/Research priority/);assert.match(html,/Design priority/);
 p.current=false;html=h.run('preflightScreen()');assert.match(html,/Needs refresh/);assert.doesNotMatch(html,/Share for direction review/);
 h.ctx.state.intake.cases=[{ref:{id:'CASE',revision:1},body:{preflight:p.ref}}];assert.match(h.run('preflightScreen()'),/Open direction review/);assert.doesNotMatch(h.run('preflightScreen()'),/Share for direction review/);
});
test('sponsor preparation and release use exact references and explicit confirmation',async()=>{
 const h=harness();await h.run("preflightAction('preflight-sponsor-prepare','')");assert.match(h.ctx.dialog.b,/What should Research investigate/);assert.match(h.ctx.dialog.b,/What should Design explore/);assert.equal(h.ctx.calls.length,0);
 await h.ctx.dialog.callback(new Map([['research_focus','Question'],['design_focus','Flow'],['open_questions','Unknown']]));assert.equal(h.ctx.calls[0].a,'intake-preflight');assert.equal(h.ctx.calls[0].data.expected.revision,3);assert.equal(h.ctx.selected,'SAVED');
 packageFor(h);await h.run("preflightAction('preflight-sponsor-share','PREF')");assert.match(h.ctx.dialog.b,/type="checkbox" required/);await h.ctx.dialog.callback(new Map([['confirm','on']]));assert.equal(h.ctx.calls[1].a,'intake-request');assert.equal(h.ctx.calls[1].data.preflight.id,'PREF');assert.equal(h.ctx.calls[1].data.confirm,true);
});
test('Research and Design have distinct handoff guidance and empty states',()=>{
 const r=harness('sam'),d=harness('lee');assert.match(r.run('preflightScreen()'),/Research preflight/);assert.match(r.run('preflightScreen()'),/What Design needs/);assert.match(d.run('preflightScreen()'),/Design preflight/);assert.match(d.run('preflightScreen()'),/Research into design/);assert.match(d.run('preflightScreen()'),/accessibility gaps/);assert.match(d.run('preflightScreen()'),/Open my workbench/);assert.doesNotMatch(d.run('preflightScreen()'),/Every saved deliverable has/);
});
test('domain area separates unprepared work, current packages, stale history and shared releases',()=>{
 const h=harness('sam');h.ctx.recordList=['D1','D2'].map(id=>({kind:'contribution-draft',ref:{id,revision:2},body:{title:id,chassis:1,deliverable_type:'Finding',observation:'Observed task interruption'}}));
 h.ctx.state.domains.handoffs=[{ref:{id:'H1'},current:true,body:{draft:{id:'D1',revision:2},recipient:'design',handoff:{downstream_needs:'Test resumption'}}},{ref:{id:'H0'},current:false,body:{draft:{id:'D2',revision:1},recipient:'design',handoff:{}}}];
 let html=h.run('preflightScreen()');assert.match(html,/Prepared packages/);assert.match(html,/Prepare handoff/);assert.match(html,/Needs refresh/);assert.match(html,/Test resumption/);assert.match(html,/Package history/);
 h.ctx.recordList.push({kind:'contribution',ref:{id:'C1'},body:{preflight:{ref:{id:'H1'}}}});html=h.run('preflightScreen()');assert.match(html,/Open Decisions & Issues/);assert.doesNotMatch(html,/Review sharing preview/);
});

test('blocked sponsor action opens the value proposition review in Business Intent',async()=>{
 const h=harness();await h.run("preflightAction('preflight-value-review','')");assert.equal(h.ctx.view,'intent');assert.equal(h.ctx.intakeStep,'value');assert.equal(h.ctx.valueReview,true);assert.equal(h.ctx.valueCoachMode,'whole');
});

test('sponsor and domain preflight expose the actual private packet inspector before release',()=>{
 const h=harness(),p=packageFor(h);p.body.packet={id:'PKT-PREP-PREF',revision:1};h.ctx.state.packets=[{...p.body.packet,purpose:'Prepared sponsor direction',audience_scopes:['intake:sponsor','project:demo'],refs:[p.ref],records:[{ref:p.ref,kind:'sponsor-preflight',body:{title:'Sponsor snapshot'}}],changed_refs:[]}];
 h.ctx.selected='PREF';const html=h.run('preflightScreen()');assert.match(html,/Inspect context packet/);assert.match(html,/PKT-PREP-PREF:v1/);assert.match(html,/Business sponsor only/);assert.match(html,/Inspect packet contents/);assert.match(html,/Saved manifest/);assert.match(html,/Share for direction review/);
 const d=harness('sam');d.ctx.state.domains.handoffs=[{ref:{id:'H',revision:1},current:true,body:{packet:{id:'PKT-PREP-H',revision:1},draft:{id:'D',revision:1},recipient:'design',handoff:{}}}];assert.match(d.run('preflightScreen()'),/data-action="packet" data-id="PKT-PREP-H\|1"/);
});


test('an owned prepared report can be edited or reviewed for sending without publishing on render',()=>{
 const h=harness('sam');h.ctx.recordList=[{kind:'contribution-draft',ref:{id:'D',revision:4},body:{owner:'sam',title:'Authored report',chassis:1,observation:'Earlier notes',working_report:{entries:[{heading:'Finding',text:'Author conclusion'}]}}}];h.ctx.state.domains.handoffs=[{ref:{id:'H',revision:1},current:true,body:{draft:{id:'D',revision:4},recipient:'bridge',handoff:{}}}];const html=h.run('preflightScreen()');assert.match(html,/Review & send/);assert.match(html,/data-action="wreport-edit" data-id="D"/);assert.equal(h.ctx.calls.length,0);
});

test('preflight leads with saved intake names and versions while exact identity stays in closed metadata',()=>{
 const h=harness(),before=JSON.stringify(h.ctx.state),html=h.run('preflightScreen()'),caption=html.match(/<p class="caption">Saved intake[^<]*<\/p>/)[0];
 assert.match(html,/Test intake/);assert.match(caption,/Version 3/);assert.doesNotMatch(caption,/INTAKE-001/);assert.match(html,/<details class="record-metadata"><summary>Source details<\/summary>[\s\S]*INTAKE-001:v3/);assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(h.ctx.calls.length,0);
});

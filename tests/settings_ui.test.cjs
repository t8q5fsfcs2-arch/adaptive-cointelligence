const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
function harness(){
 const calls=[],dialogs=[];
 const profile={short_label:'Priority now',expert_role:'Prioritization coach',answer_goal:'Explain priority.',hint:'Why now?',quality_checks:['Assess consequences.'],answer_shape:['Reason'],starter:'Because...',connections:['value']};
 const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/workbench/config/agent_personas.json'),'utf8'));
 for(const p of catalog.profiles)p.implementation={status:p.id==='P02'?'partial':'specified',label:p.id==='P02'?'Partly implemented':'Specified · not connected',runtime_id:p.id==='P02'?'business-intent-coach':null,summary:'Coverage is explicit.'};
 catalog.history=[];catalog.ref=null;
 const settings={agent_registry:catalog,ref:null,config:{questions:{why_now:profile,value:{...profile,short_label:'Value proposition'}},persona:{name:'Coach',remit:'Help',style:'Concise'},skills:{'coach-field':'Evaluate the response.'}},skills:{'coach-field':{label:'Coach a response',trigger:'Coach this response'}},guardrails:'People decide.',integrations:{ref:null,items:[]}};
 const ctx={URLSearchParams,state:{actor:'priya',actors:{priya:{role:'Business sponsor'},sam:{role:'Research'},lee:{role:'Design'}},intake:{draft:{}},coaching:{settings}},pageDirty:false,busy:false,dirty:false,intakeStep:'value',valueFocus:'why_now',coachedField:'why_now',valueGroups:[['Business reason',['why_now','value']]],contextGroups:[],
  coachInfo:()=>({model:{configured:false}}),tag:(s)=>`<span>${s}</span>`,
  esc:s=>String(s??'').replaceAll('<','&lt;').replaceAll('"','&quot;'),projectTitle:()=> 'Synthetic project',selectorChevron:()=>'<svg></svg>',shortQuestion:k=>settings.config.questions[k]?.short_label||k,
  button:(text,action,id)=>`<button data-action="${action}" data-id="${id}">${text}</button>`,
  document:{querySelector:()=>null,addEventListener:()=>{}},$:()=>null,confirm:()=>true,
  modal:(...args)=>dialogs.push(args),command:async(action,data)=>{calls.push({action,data});return {message:'Saved'};},
  abandonIntakeEdits:()=>true,saveCoachedField:async()=>{},intakeProfileForm:()=>dialogs.push(['Intake settings']),
 };
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/settings.js'),'utf8'),ctx);
 return {ctx,calls,dialogs,run:s=>vm.runInContext(s,ctx)};
}
test('settings has one visible entry and the root respects each role’s rights',()=>{
 const h=harness(),trigger=h.run('settingsNavigation()');assert.match(trigger,/data-action="settings-home"/);assert.match(trigger,/>Settings</);assert.doesNotMatch(trigger,/<details/);
 h.run('openSettingsHome()');let html=h.dialogs[0][1];for(const t of ['Intake settings','Agents & expertise','Integrations'])assert.ok(html.includes(t),t);
 h.ctx.state.actor='sam';h.run('openSettingsHome()');html=h.dialogs[1][1];assert.doesNotMatch(html,/Agents & expertise|data-action="settings-intake"/);assert.match(html,/Integrations/);assert.doesNotMatch(html,/data-action="pflow-tools"/);
});

test('editing question expertise sends complete criteria and selected connections with its version',async()=>{
 const h=harness();h.run("openAgentSettings('question','why_now')");
 const handler=h.dialogs[0][3],fd=new Map([['expert_role','Portfolio specialist'],['answer_goal','Explain priority.'],['quality_checks',' Check opportunity cost.\n\nKeep uncertainty. '],['hint','Why now?'],['answer_shape','Reason\nConsequence'],['starter','Because...'],['reason','Refine priority advice.']]);fd.getAll=()=>['value'];
 await handler(fd);const {action,data}=h.calls[0];assert.equal(action,'coach-settings-save');assert.equal(data.expected,null);assert.equal(data.key,'why_now');
 assert.deepEqual(Array.from(data.config.quality_checks),['Check opportunity cost.','Keep uncertainty.']);assert.deepEqual(data.config.connections,['value']);assert.equal(data.reason,'Refine priority advice.');
});
test('opening settings saves active answers and refuses to lose new typing during save',async()=>{
 const h=harness();h.ctx.document.querySelector=()=>({});h.ctx.saveCoachedField=async()=>{h.calls.push('save');};
 await h.run("settingsAction('settings-agents','')");assert.equal(h.calls[0],'save');assert.equal(h.dialogs.length,1);assert.equal(h.ctx.busy,false);
 h.ctx.saveCoachedField=async()=>{h.ctx.pageDirty=true;};
 await assert.rejects(h.run("settingsAction('settings-agents','')"),/New edits arrived/);
 assert.equal(h.dialogs.length,1);assert.equal(h.ctx.pageDirty,true);assert.equal(h.ctx.busy,false);
});
test('canceling tab navigation keeps unsaved configuration in place',async()=>{
 const h=harness();h.ctx.dirty=true;h.ctx.confirm=()=>false;
 await h.run("settingsAction('settings-agent-tab','persona')");assert.equal(h.dialogs.length,0);assert.equal(h.ctx.dirty,true);
});
test('question fields render configurable copy safely and keep secondary guidance collapsed',()=>{
 const h=harness();h.ctx.state.coaching.settings.config.questions.why_now.expert_role='<script>bad</script>';
 h.run("openAgentSettings('question','why_now')");const html=h.dialogs[0][1];assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);assert.match(html,/<details class="settings-detail"><summary>Question guidance/);assert.match(html,/View saved instructions/);
});

test('profile inspector offers all source IDs and saving a descriptor never edits coaching instructions',async()=>{
 const h=harness();h.run("openAgentRegistry('P04')");const [title,html,label,handler]=h.dialogs[0];
 assert.match(html,/P14 · Ratification coordinator/);assert.match(html,/Specified · not connected/);
 assert.match(html,/<details class="settings-detail"><summary>Responsibilities & attributes/);
 assert.doesNotMatch(html,/Configure intake AI partner/);
 await handler(new Map([['descriptor','Quality partner'],['reason','Clarify purpose']]));
 assert.equal(h.calls[0].action,'agent-descriptor-save');assert.equal(h.calls[0].data.persona_id,'P04');
 assert.equal(h.calls[0].data.descriptor,'Quality partner');assert.equal(h.calls[0].data.expected,null);
});
test('intake profile points to its existing configuration and escapes descriptor text',()=>{
 const h=harness();h.ctx.state.coaching.settings.agent_registry.profiles[1].descriptor='<script>bad</script>';
 h.run('openAgentRegistry()');const html=h.dialogs[0][1];
 assert.match(html,/Partly implemented/);assert.match(html,/Configure intake AI partner/);assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);
 h.run("openAgentSettings('question','why_now')");assert.equal(h.dialogs[1][0],'Intake AI partner · P02');assert.match(h.dialogs[1][1],/P02 uses the expertise/);
});
test('returning to inventory protects unsaved instruction edits',async()=>{
 const h=harness();h.ctx.dirty=true;h.ctx.confirm=()=>false;
 await h.run("settingsAction('settings-agent-registry','')");assert.equal(h.dialogs.length,0);
});

test('configuration editor separates testing from activation',()=>{
 const h=harness();h.run("openAgentSettings('question','why_now')");const [title,html,submit]=h.dialogs[0];
 assert.equal(submit,'Use in intake');assert.match(html,/Test changes/);assert.match(html,/Compare responses/);
 assert.match(html,/Sends two requests/);assert.match(html,/Editing this example does not change the saved intake/);
 assert.match(html,/Earlier AI partner conversations are excluded/);assert.equal(h.calls.length,0);
});
test('comparison renders the actual output safely and preserves partial failures',()=>{
 const h=harness();h.ctx.result={status:'completed',output:{reply:'<script>unsafe</script>',suggestions:[{text:'A proposed answer',rationale:'A reason'}],questions:[{question:'Which alternative?'}]}};
 const html=h.run("settingsTestOutput(result,'Your changes')");assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);assert.match(html,/A proposed answer/);assert.match(html,/Which alternative/);
 h.ctx.result={status:'failed',error:'Model unavailable'};assert.match(h.run("settingsTestOutput(result,'Current settings')"),/Model unavailable/);
});
test('only an unchanged reviewed configuration carries its comparison reference into activation',async()=>{
 const h=harness();h.run("openAgentSettings('persona')");const fd=new Map([['name','Updated coach'],['remit','Clarify value'],['style','Concise']]);
 h.ctx.config={name:'Updated coach',remit:'Clarify value',style:'Concise'};
 h.run("activeSettingsTest={signature:JSON.stringify(config),comparison:{id:'COACH-TEST-1',revision:4}}");
 await h.dialogs[0][3](fd);assert.equal(h.calls[0].data.comparison.id,'COACH-TEST-1');
 fd.set('style','Different');await h.dialogs[0][3](fd);assert.equal(h.calls[1].data.comparison,null);
});

test('agent monitoring separates live workflow from configuration tests and does not invent quality or cost',()=>{
 const h=harness();h.ctx.state.agent_monitoring={summaries:[{persona_id:'P02',mode:'live',purpose:'workflow',total:3,completed:2,failed:1,stale:0,running:0,unknown:0,applied:1,median_ms:1250,tokens:90,usage_coverage:2},{persona_id:'P02',mode:'simulated',purpose:'configuration-test',total:7,completed:7,failed:0,stale:0,running:0,unknown:0,applied:0,median_ms:2,tokens:null,usage_coverage:0}],runs:[],legacy_count:4};
 const html=h.run("agentPerformance('P02')");assert.match(html,/2 \/ 3/);assert.match(html,/1.3 s/);assert.match(html,/simulated/);assert.match(html,/Configuration tests/);assert.match(html,/Cost: not available/);assert.match(html,/Answer quality is tracked separately in Methods & quality/);assert.match(html,/4 earlier AI partner result/);assert.doesNotMatch(html,/100%|\$0/);
});
test('agent labels reflect runtime modes and descriptors cannot set execution mode',async()=>{
 const h=harness(),registry=h.ctx.state.coaching.settings.agent_registry;
 registry.profiles[1].implementation={label:'Live',mode:'live',runtime_id:'business-intent-coach',version:'11',summary:'Working intake coach.'};
 registry.profiles[3].implementation={label:'Not connected',mode:'not-connected',runtime_id:'requirement-assistant',version:'1',summary:'Configured role awaits a connection.'};
 h.run("openAgentRegistry('P04')");const html=h.dialogs[0][1];assert.match(html,/Configure Requirement Assistant/);assert.match(html,/Not connected/);assert.match(html,/No simulation is selectable/);assert.doesNotMatch(html,/name="mode"/);
});
test('requirement controls expose draft and advisory review without applying automatically',()=>{
 const h=harness();vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/requirement-agent.js'),'utf8'),h.ctx);
 h.ctx.drawer={key:'needs',label:'Needs',included:true,requirement:'Existing wording'};
 const html=h.run('requirementAgentControls(drawer)');assert.match(html,/Suggest a revision/);assert.match(html,/Ask your AI partner about this requirement/);assert.match(html,/Uses saved intake/);assert.equal(h.calls.length,0);
});
test('requirement requests protect unsaved drawer edits',async()=>{
 const h=harness();vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/requirement-agent.js'),'utf8'),h.ctx);
 h.ctx.pageDirty=true;await assert.rejects(h.run("requirementAgentAction('req-agent-draft','needs')"),/Save the scaffold/);assert.equal(h.calls.length,0);
});
test('Integrations consolidates Figma files, MCP setup and other connections without making external requests',()=>{
 const h=harness();h.ctx.projectToolsSummary=()=>'<section>Figma & FigJam saved files</section>';h.ctx.projectMcpSetup=()=>'<details>Figma MCP setup</details>';
 h.ctx.state.coaching.settings.integrations.items=[{id:'saved',kind:'mcp',name:'Saved source',endpoint:'https://example.test/mcp',purpose:'Read permitted context'}];
 h.run('openIntegrationSettings()');const [title,html]=h.dialogs[0];assert.equal(title,'Integrations');for(const t of ['Figma & FigJam saved files','Figma MCP setup','Other MCPs & APIs','Setup saved · not active','Saved source'])assert.ok(html.includes(t),t);assert.equal(h.calls.length,0);
 h.run('openSettingsHome()');const root=h.dialogs[1][1];assert.equal((root.match(/data-action="settings-integrations"/g)||[]).length,1);assert.doesNotMatch(root,/pflow-tools/);
});
test('domain users can open their unified work-tool settings without sponsor-only connection definitions',()=>{
 const h=harness();h.ctx.state.actor='sam';h.ctx.state.coaching={};h.ctx.projectToolsSummary=()=>'<section>Research file links</section>';h.ctx.projectMcpSetup=()=>'<details>Figma MCP setup</details>';
 h.run('openIntegrationSettings()');const html=h.dialogs[0][1];assert.match(html,/Research file links/);assert.match(html,/Figma MCP setup/);assert.doesNotMatch(html,/Other MCPs & APIs|Coaching model|settings-connection/);
});
test('integration settings remain reachable before intake and cannot save extra definitions without a draft',()=>{
 const h=harness();h.ctx.state.intake.draft=null;const items=h.run('settingsDestinations()');assert.equal(items.find(x=>x.action==='settings-integrations').enabled,true);
 h.run('openIntegrationSettings()');assert.match(h.dialogs[0][1],/Create a Business Intent draft/);assert.doesNotMatch(h.dialogs[0][1],/data-action="settings-connection"/);
});
test('opening integrations saves framing edits and stays on the draft if saving fails',async()=>{
 const h=harness();let saved=false;h.ctx.saveBeforeProjectChange=async()=>{saved=true;};await h.run("settingsAction('settings-integrations','')");assert.equal(saved,true);assert.equal(h.dialogs[0][0],'Integrations');assert.equal(h.ctx.busy,false);
 h.ctx.saveBeforeProjectChange=async()=>{throw Error('Unsaved newer text');};await assert.rejects(h.run("settingsAction('settings-integrations','')"),/Unsaved newer text/);assert.equal(h.dialogs.length,1);assert.equal(h.ctx.busy,false);
});
test('opening the Settings destination preserves the page draft and exposes only permitted sections',async()=>{
 const h=harness(),calls=[];h.ctx.saveBeforeProjectChange=async()=>calls.push('save');await h.run("settingsAction('settings-home','')");assert.deepEqual(calls,['save']);assert.equal(h.dialogs[0][0],'Settings');assert.match(h.dialogs[0][1],/Settings sections|Integrations/);assert.equal(h.ctx.busy,false);
 h.ctx.saveBeforeProjectChange=async()=>{throw Error('Save blocked');};await assert.rejects(h.run("settingsAction('settings-home','')"),/Save blocked/);assert.equal(h.dialogs.length,1);
});

test('settings purpose groups do not expose restricted sponsor configuration to domain users',()=>{
 const h=harness();h.run('openSettingsHome()');const sponsor=h.dialogs.at(-1)[1];
 assert.match(sponsor,/Business Intent & assistance/);assert.match(sponsor,/Connections & access/);
 h.ctx.state.actor='sam';h.run('openSettingsHome()');const research=h.dialogs.at(-1)[1];assert.doesNotMatch(research,/Business Intent & assistance|Agents & expertise/);assert.match(research,/Connections & access/);assert.equal(h.calls.length,0);
});


test('model setup is sitewide for Admin and assigned details are read only for other roles',()=>{
 const h=harness();h.ctx.state.global_context=true;
 h.ctx.state.model_connection={available:true,can_manage:true,revision:2,profiles:[{id:'M1',name:'Pilot',model:'model-one',provider:'openai',revision:1}],projects:[{id:'__general__',title:'General AI partner'},{id:'original',title:'Clinic'}],assignments:{original:'M1'}};
 h.run('openSettingsHome()');assert.match(h.dialogs[0][1],/Model connections/);assert.match(h.dialogs[0][1],/assign them to projects/);
 h.run('openModelConnections()');assert.match(h.dialogs[1][1],/Pilot/);assert.match(h.dialogs[1][1],/Add connection/);
 h.ctx.state.model_connection.can_manage=false;h.ctx.state.model_connection.profile={name:'Pilot',model:'model-one'};
 h.run('openModelConnections()');const html=h.dialogs[2][1];assert.match(html,/Administrator manages/);assert.doesNotMatch(html,/api_key|Add connection|Assign to projects/);
});
test('model form never preloads saved keys and saves configuration without testing or assigning',async()=>{
 const h=harness();h.ctx.state.model_connection={available:true,can_manage:true,revision:3,profiles:[{id:'M1',name:'Pilot',provider:'openai',model:'model-one',revision:1,test:{status:'passed'}}],projects:[{id:'original',title:'Clinic'}],assignments:{original:'M1'}};
 h.run("openModelConnection('M1')");const [,html,,save]=h.dialogs[0];assert.match(html,/type="password" name="api_key" value=""/);assert.match(html,/New|new requests/);assert.match(html,/Clinic/);assert.match(html,/Saving sends no model request/);
 await save(new Map([['name','Pilot'],['provider','openai'],['model','new-model'],['api_key','']]));
 assert.equal(h.calls.length,1);assert.equal(h.calls[0].action,'model-connection-save');assert.equal(h.calls[0].data.expected,3);assert.equal(h.calls[0].data.api_key,'');
});
test('model assignments preserve explicit choices and disclose replacement and unassignment',async()=>{
 const h=harness();h.ctx.state.model_connection={available:true,can_manage:true,revision:4,profiles:[{id:'M1',name:'Pilot',model:'model-one'},{id:'M2',name:'Other'}],projects:[{id:'__general__',title:'General AI partner'},{id:'a',title:'Project A'},{id:'b',title:'Project B'}],assignments:{a:'M1',b:'M2'}};
 h.run("openModelAssignments('M1')");const [,html,,save]=h.dialogs[0];assert.match(html,/General AI partner/);assert.match(html,/Current: Other/);assert.match(html,/Unchecking removes/);
 const fd=new Map();fd.getAll=()=>['a','b'];await save(fd);assert.equal(h.calls[0].action,'model-connection-assign');assert.deepEqual(h.calls[0].data.projects,['a','b']);
});
test('navigation to assignment setup protects unsaved model connection edits',async()=>{
 const h=harness();h.ctx.dirty=true;h.ctx.confirm=()=>false;await h.run("settingsAction('settings-model-assign','M1')");assert.equal(h.dialogs.length,0);
});

test('enabled Settings destinations use blue link semantics while helper copy stays separate',()=>{
 const h=harness();h.run('openSettingsHome()');const html=h.dialogs[0][1];
 assert.match(html,/<a href="#main" class="settings-destination-link item-title-link" data-action="settings-decision-rights">/);
 assert.match(html,/<small>Name deciders/);assert.doesNotMatch(html,/<button[^>]*data-action="settings-decision-rights"/);
 const css=fs.readFileSync(path.join(__dirname,'../src/workbench/static/workspace.css'),'utf8');assert.match(css,/settings-destination-link>small\{[^}]*color:var\(--ws-color-text-body-helper\)/);
});

test('Admin Home settings stay available without opening a project or creating intake',()=>{
 const h=harness();h.ctx.state.global_context=true;h.ctx.state.actor='administrator';h.ctx.state.auth={administrator:true};h.ctx.state.intake={};
 h.ctx.state.model_connection={available:true,can_manage:true,profiles:[],assignments:{},projects:[],revision:0};
 h.run('openSettingsHome()');const html=h.dialogs[0][1];for(const action of ['settings-models','settings-decision-rights','portfolio-access'])assert.ok(html.includes('data-action="'+action+'"'));
 assert.doesNotMatch(html,/disabled|Create a Business Intent draft|after you open a project/);assert.match(html,/Sitewide settings/);
});

test('Admin Integrations is a blue destination on Home and within project Settings',()=>{
 const h=harness();h.ctx.state.actor='administrator';h.ctx.state.auth={administrator:true};h.ctx.state.actors.administrator={role:'Administrator'};
 h.ctx.state.model_connection={available:true,can_manage:true};h.ctx.state.global_context=true;
 h.run('openSettingsHome()');let html=h.dialogs.at(-1)[1];assert.match(html,/<a[^>]+class="settings-destination-link item-title-link"[^>]+data-action="settings-integrations"/);assert.match(html,/MCPs, APIs and tool links/);
 h.ctx.state.model_connection=null;h.run('openSettingsHome()');assert.match(h.dialogs.at(-1)[1],/data-action="settings-integrations"/);
 h.ctx.state.global_context=false;h.run('openSettingsHome()');html=h.dialogs.at(-1)[1];assert.match(html,/data-action="settings-integrations"/);
});
test('Admin integration project selection reads only configuration and keeps authorization separate',async()=>{
 const h=harness();h.ctx.state.actor='administrator';h.ctx.state.auth={administrator:true};h.ctx.state.global_context=true;
 const projects=[{id:'p1',title:'Fictional Clinic'}],requested=[];
 h.ctx.fetch=async url=>{requested.push(url);return {ok:true,json:async()=>url.includes('?')?{projects,project:{...projects[0],version:3},tools:{ref:null,links:{},mcp:{endpoint:'https://mcp.figma.com/mcp'}},connections:{ref:null,items:[{id:'c1',name:'Read-only context',kind:'api',endpoint:'https://example.test/context',purpose:'Read context.'}]}}:{projects}};};
 await h.run("settingsAction('settings-integrations','')");let html=h.dialogs.at(-1)[1];assert.match(html,/Choose a project/);assert.equal(requested[0],'/api/admin-integrations');assert.equal(h.ctx.state.global_context,true);
 await h.run("openAdminIntegrations('p1')");html=h.dialogs.at(-1)[1];for(const text of ['Figma & FigJam file links','Read-only context','Setup saved, not active','FigJam, Figma & Lucid imports'])assert.ok(html.includes(text),text);
 assert.equal(h.calls.length,0);assert.match(html,/credentials and private work remain separate/);
 h.run("openAdminIntegrationConnection('c1')");const save=h.dialogs.at(-1)[3];
 h.ctx.fetch=async(url,options)=>{requested.push({url,options});return {ok:true,json:async()=>({message:'Saved'})};};
 await save(new Map([['name','Refined source'],['kind','api'],['endpoint','https://example.test/context'],['purpose','Approved context'],['credential_ref','WB_CONTEXT_TOKEN']]));
 const call=requested.at(-1);assert.equal(call.url,'/api/admin-integration-save');assert.equal(call.options.headers['X-Workbench-Project'],'p1');assert.equal(call.options.headers['X-Workbench-Version'],'3');assert.equal(JSON.parse(call.options.body).expected,null);
});


test('every development persona receives the same enabled project Settings destinations',()=>{
 const h=harness();h.ctx.state.auth={mode:'development',settings_access:true};h.ctx.state.global_context=false;
 const lists=[];
 for(const actor of ['priya','sam','lee','maya','alex','administrator']){
  h.ctx.state.actor=actor;h.ctx.state.actors[actor]||={role:actor};
  const entries=h.run('settingsDestinations()');lists.push(entries.map(x=>x.action));
  for(const entry of entries)assert.equal(entry.enabled,true,actor+': '+entry.action);
  h.run('openSettingsHome()');const html=h.dialogs.at(-1)[1];
  for(const name of ['Announcements','Intake settings','Agents & expertise','Domain knowledge','Domain workbenches','Add domain','Decision rights','Integrations'])assert.ok(html.includes(name),actor+': '+name);
  assert.doesNotMatch(html,/available to your role|disabled/);
 }
 for(const list of lists)assert.deepEqual(Array.from(list),Array.from(lists[0]));
});
test('Home settings exposes announcements and integration configuration to a regular development persona',()=>{
 const h=harness();h.ctx.state.actor='sam';h.ctx.state.auth={mode:'development',settings_access:true};h.ctx.state.global_context=true;h.ctx.state.model_connection={available:true,can_manage:true};
 h.run('openSettingsHome()');const html=h.dialogs.at(-1)[1];
 for(const action of ['settings-announcements','settings-models','settings-integrations','settings-decision-rights','portfolio-access'])assert.match(html,new RegExp('data-action="'+action+'"'));
 assert.doesNotMatch(html,/Administrator ·|administrator manages/i);
});

// Configuration changes are explicit; only the separate test action calls a model.
function settingsDestinations(){
 const sponsor=state.actor==='priya',draft=sponsor&&!!state.intake?.draft,categoryAccess=!!state.intake?.profile?.body.drawers.some(d=>d.owner===state.actor),knowledge=state.domain_knowledge,canAdd=!!knowledge?.can_add,domainKnowledge=!!knowledge?.domains.length,configureDomains=!!state.domains?.can_configure.length;
 return [
  {label:'Announcements',action:'settings-announcements',description:'Edit and publish updates for everyone on Home.',visible:settingsAdmin(),enabled:true},
  {label:'Model connections',action:'settings-models',description:'Sitewide models and project assignments.',visible:!!state.model_connection?.available,enabled:true},
  {label:'Decision rights',action:'settings-decision-rights',description:'Name deciders, required reviewers, delegates and escalation contacts.',visible:true,enabled:true},
  {label:'Domain workbenches',action:'settings-domains',description:'Configure professional methods, vocabulary and AI partner standards.',visible:sponsor||!!state.domains?.active||canAdd,enabled:draft||configureDomains||canAdd},
  {label:'Domain knowledge',action:'settings-domain-knowledge',description:'Maintain the team’s vocabulary, standards and best practices.',visible:sponsor||domainKnowledge,enabled:draft||domainKnowledge},
  {label:'Add domain',action:'settings-domain-add',description:'Set up another team and assign its members.',visible:canAdd,enabled:canAdd},
  {label:'Intake settings',action:'settings-intake',description:'Configure requirement categories and question guidance.',visible:sponsor||categoryAccess,enabled:draft||categoryAccess},
  {label:'Agents & expertise',action:'settings-agents',description:'Inspect and refine agent instructions, skills and performance.',visible:sponsor,enabled:draft},
  {label:'Integrations',action:'settings-integrations',description:'Manage MCPs, APIs and Figma/FigJam file links.',visible:['priya','sam','lee'].includes(state.actor)||settingsAdmin(),enabled:true},
  {label:'Project visibility',action:'portfolio-access',description:'Assign shared project summary visibility independently of project membership.',visible:!!state.auth?.account?.admin||!!state.auth?.administrator,enabled:true},
  {label:'Project members',action:'account-members',description:'Manage account membership for this project.',visible:!!state.auth?.account?.admin&&!state.global_context&&state.auth?.mode==='accounts',enabled:true}
 ].map(item=>state.auth?.settings_access&&item.action!=='account-members'?{...item,visible:true,enabled:true}:item).filter(item=>item.visible);
}
function settingsNavigation(){return `<button type="button" class="ws-settings-button" data-action="settings-home" aria-haspopup="dialog" aria-controls="modal"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m9 3-1 3-3 1-2 5 2 5 3 1 1 3h6l1-3 3-1 2-5-2-5-3-1-1-3Z"/><circle cx="12" cy="12" r="3"/></svg><span>Settings</span></button>`;}
function settingsAdmin(){return !!(state.auth?.settings_access||state.auth?.account?.admin||state.auth?.administrator);}
function openSettingsHome(){
 const items=settingsDestinations();
 if(state.global_context){
  const admin=settingsAdmin();
  modal('Settings',`${admin?'<p class="caption settings-scope">Sitewide settings</p>':''}<nav class="settings-destinations" aria-label="Settings sections">${state.model_connection?.available||admin?`<section class="acx-settings-group"><h3 class="acx-subsection-title">Connections</h3>${state.model_connection?.available?`<a href="#main" class="settings-destination-link item-title-link" data-action="settings-models"><span>Model connections</span><small>${state.model_connection.can_manage?'Manage connections and assign them to projects.':'See the assigned connection. The Administrator manages setup.'}</small></a>`:''}${admin?'<a href="#main" class="settings-destination-link item-title-link" data-action="settings-integrations"><span>Integrations</span><small>MCPs, APIs and tool links. Choose a project to manage its setup.</small></a>':''}</section>`:''}${admin?`<section class="acx-settings-group"><h3 class="acx-subsection-title">Home page</h3><a href="#main" class="settings-destination-link item-title-link" data-action="settings-announcements"><span>Announcements</span><small>Edit and publish updates for everyone on Home.</small></a></section>`:''}${admin?`<section class="acx-settings-group"><h3 class="acx-subsection-title">Project settings</h3><a href="#main" class="settings-destination-link item-title-link" data-action="settings-decision-rights"><span>Decision rights</span><small>Name deciders, required reviewers, delegates and escalation contacts.</small></a><a href="#main" class="settings-destination-link item-title-link" data-action="portfolio-access"><span>Project visibility</span><small>Assign access to shared project summaries.</small></a></section>`:''}</nav><p class="caption">${admin?'Manage connections and access here. Project-specific configurations remain with their projects.':'Project settings are available after you open a project.'}</p>`,null,null,{className:'settings-dialog'});return;
 }
 modal('Settings',`<p class="caption settings-scope">${esc(projectTitle())} · ${esc(state.actors[state.actor].role)}</p><p>Configure this project and its capabilities.</p><nav class="settings-destinations" aria-label="Settings sections">${[[state.model_connection?.can_manage?'Sitewide settings':'Model connection',['settings-models','portfolio-access']],['Home page',['settings-announcements']],['Project settings',['settings-decision-rights']],['Teams & domain knowledge',['settings-domains','settings-domain-knowledge','settings-domain-add']],['Business Intent & assistance',['settings-intake','settings-agents']],['Connections & access',['settings-integrations','account-members']]].map(([title,actions])=>{const group=items.filter(item=>actions.includes(item.action));return group.length?`<section class="acx-settings-group"><h3 class="acx-subsection-title">${esc(title)}</h3>${group.map(item=>item.enabled?`<a href="#main" class="settings-destination-link item-title-link" data-action="${item.action}"><span>${esc(item.label)}</span><small>${esc(item.description)}</small></a>`:`<button type="button" disabled><span>${esc(item.label)}</span><small>${esc(item.description)}${state.actor==='priya'?' Create a Business Intent draft to enable this setting.':' Your domain leader or administrator manages this setting.'}</small></button>`).join('')}</section>`:'';}).join('')||'<p class="caption">There are no configuration options for this role in this project.</p>'}</nav>`,null,null,{className:'settings-dialog'});
}
function projectCoachSettings(){return state.coaching.settings;}
function settingField(name,title,value,help='',rows=3,limit=4000){return `<label class="form-field"><span>${esc(title)}</span><textarea name="${name}" rows="${rows}" maxlength="${limit}" required>${esc(value)}</textarea>${help?`<small>${esc(help)}</small>`:''}</label>`;}
function settingInput(name,title,value,help='',required=true){return `<label class="form-field"><span>${esc(title)}</span><input name="${name}" value="${esc(value)}" maxlength="200" ${required?'required':''}>${help?`<small>${esc(help)}</small>`:''}</label>`;}
function settingSelector(id,title,options,name=''){return `<div class="ui-selector-field settings-selector"><label class="ui-control-label" for="${id}">${title}</label><div class="ui-selector-wrap"><select id="${id}" class="ui-selector" ${name?`name="${name}"`:""}>${options}</select>${selectorChevron()}</div></div>`;}
function settingsScope(){const c=projectCoachSettings();return `<p class="caption settings-scope">${esc(projectTitle())} · ${c.ref?`Saved version ${c.ref.revision}`:'Default configuration'}</p>`;}
function settingsTabs(area){return `<nav class="settings-tabs" aria-label="AI partner settings">${[['question','Question expertise'],['persona','AI partner persona'],['skill','Skills']].map(([key,title])=>`<button type="button" data-action="settings-agent-tab" data-id="${key}" class="${area===key?'selected':''}" ${area===key?'aria-current="page"':''}>${title}</button>`).join('')}</nav>`;}
function questionOptions(key){return [['Value proposition',valueGroups.flatMap(g=>g[1]).concat('assumption_owner')],['Context',contextGroups.flatMap(g=>g[1])]].map(([label,keys])=>`<optgroup label="${label}">${keys.filter(k=>projectCoachSettings().config.questions[k]).map(k=>`<option value="${k}" ${k===key?'selected':''}>${esc(shortQuestion(k))}</option>`).join('')}</optgroup>`).join('');}
function expertSettingsFields(key,p){return `<div class="settings-expert-summary">${settingInput('expert_role','Expert role',p.expert_role)}${settingField('answer_goal','What a good answer should do',p.answer_goal)}</div>${settingField('quality_checks','What the AI partner checks',p.quality_checks.join('\n'),'One criterion per line.',5)}${typeof questionMethods==='function'?questionMethods(key):''}<details class="settings-detail"><summary>Question guidance & related answers</summary><div class="details-body">${settingField('hint','Guidance shown with the question',p.hint)}${settingField('answer_shape','Suggested answer structure',p.answer_shape.join('\n'),'One element per line.')}${settingField('starter','Help getting started',p.starter)}<fieldset class="settings-connections"><legend>Related answers to emphasize</legend><p class="caption">The AI partner receives the intake and gives these answers particular attention.</p><div>${Object.entries(projectCoachSettings().config.questions).filter(([k])=>k!==key).map(([k,v])=>`<label><input type="checkbox" name="connections" value="${k}" ${p.connections.includes(k)?'checked':''}>${esc(v.short_label)}</label>`).join('')}</div></fieldset></div></details>`;}
function savedInstructionDetails(skill,key){return `<details class="settings-detail" data-saved-instructions data-skill="${skill}" data-field="${key}"><summary>View saved instructions</summary><p class="caption">Saved instructions for ${esc(projectCoachSettings().skills[skill].label)}${skill==='coach-field'?' · '+esc(shortQuestion(key)):''}. Unsaved edits are not included. Answers and selected source material are added when you ask your AI partner.</p><pre class="settings-instructions">Open to load saved instructions.</pre></details>`;}
function settingsTime(value){const d=new Date(value);return Number.isNaN(d.getTime())?esc(value):esc(d.toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'}));}
function openAgentRegistry(key='P02'){
 const registry=projectCoachSettings().agent_registry;
 const profile=registry.profiles.find(p=>p.id===key)||registry.profiles[0];key=profile.id;
 const runtime=profile.implementation,model=coachInfo().model;
 const history=registry.history.filter(h=>h.persona_id===key);
 const attributes=[['Role & journey',profile.role],['Persona & purpose',profile.purpose],['Trigger',profile.trigger],['Inputs',profile.inputs],['Skills',profile.skills],['Output / on screen',profile.output],['Boundaries',profile.boundaries],['Prior work',profile.prior_work]];
 const details=`<details class="settings-detail"><summary>Responsibilities & attributes</summary><dl class="agent-attributes">${attributes.map(([label,value])=>`<div><dt>${label}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl></details>`;
 const counts=registry.profiles.reduce((out,p)=>{const k=p.implementation.label;out[k]=(out[k]||0)+1;return out;},{Live:0,Simulated:0});
 const countText=Object.entries(counts).map(([label,n])=>`${n} ${label.toLowerCase()}`).join(' · ');
 const tracking=`<details class="settings-detail"><summary>Runtime & tracking</summary>${runtime.runtime_id?`<dl class="agent-attributes"><div><dt>Runtime</dt><dd>${esc(runtime.runtime_id)} · version ${esc(runtime.version)}</dd></div><div><dt>Model connection</dt><dd>${model.configured?'Configured model':'Not configured'}</dd></div><div><dt>Tools & authority</dt><dd>Bounded model reasoning over permitted saved context. No external write tools; people apply proposals and approve decisions.</dd></div><div><dt>Quality validation</dt><dd>Expert quality has not been established across representative cases. Completion measures execution, not correctness.</dd></div></dl>`:'<p class="caption">No executable reasoning role is bound to this profile.</p>'}${runtime.supporting_service?'<p class="caption">Rule-based supporting services exist. They are ordinary application code, not simulated agents.</p>':''}<h4>Descriptor history</h4>${history.length?history.map(h=>`<p><strong>Version ${esc(h.revision)}</strong> · ${settingsTime(h.at)}<br>${esc(h.descriptor)}</p>`).join(''):'<p class="caption">Using the original descriptor.</p>'}</details>`;
 modal('Agents & expertise',`<p class="caption settings-scope">${esc(projectTitle())} · ${esc(countText)}</p>${settingSelector('settings-agent-profile','Agent profile',registry.profiles.map(p=>`<option value="${p.id}" ${p.id===key?'selected':''}>${esc(p.id+' · '+p.name+' — '+p.implementation.label)}</option>`).join(''))}<div class="agent-status">${tag(runtime.label)}${runtime.runtime_id?'<span class="caption">Implemented capabilities are listed below.</span>':''}</div><section class="agent-implementation"><h3>Available now</h3><p>${esc(runtime.summary)}</p>${key==='P02'&&runtime.runtime_id?button('Configure intake AI partner','settings-agent-configure','','secondary small'):key==='P04'&&runtime.runtime_id?button('Configure Requirement Assistant','settings-requirement-configure','','secondary small'):key==='P06'?button('Configure Research workbench','domain-configure','research','small'):key==='P12'?button('Configure Design workbench','domain-configure','design','small'):''}</section>${typeof expertiseSummary==='function'?expertiseSummary(key):''}${agentPerformance(key)}<details class="settings-detail"><summary>Descriptor</summary>${settingField('descriptor','Your descriptor',profile.descriptor,'Labels this role; it does not change its execution status.',2,600)}</details>${details}${tracking}<details class="settings-detail"><summary>Status definitions & source</summary><dl class="agent-attributes"><div><dt>Live</dt><dd>An executable role is wired to a real model adapter. Its run history shows what has actually executed.</dd></div><div><dt>Simulated</dt><dd>An explicit test adapter supplies responses. Simulations are excluded from live metrics. No simulation is selectable in this application.</dd></div><div><dt>Not connected</dt><dd>The role is implemented, but no model connection is configured.</dd></div><div><dt>Not implemented</dt><dd>A role specification exists; no executable agent is connected.</dd></div></dl><p><a href="${esc(registry.source.url)}" target="_blank" rel="noopener noreferrer">${esc(registry.source.title)}</a> · ${esc(key)}</p>${settingInput('reason','Why this descriptor change? (optional)','','',false)}</details>`,'Save descriptor',fd=>command('agent-descriptor-save',{expected:registry.ref,persona_id:key,descriptor:fd.get('descriptor'),reason:fd.get('reason')}),{className:'settings-dialog agent-registry-dialog'});
 const select=$('#settings-agent-profile');
 if(select){select.addEventListener('input',e=>e.stopPropagation());select.addEventListener('change',()=>{if(dirty&&!confirm('Discard unsaved descriptor changes?')){select.value=key;return;}openAgentRegistry(select.value);});}
}
function coachSettingsPatch(area,fd){
 const data=Object.fromEntries(fd);
 return area==='skill'?{instructions:data.instructions}:area==='persona'?{name:data.name,remit:data.remit,style:data.style}:{expert_role:data.expert_role,answer_goal:data.answer_goal,hint:data.hint,starter:data.starter,quality_checks:data.quality_checks.split('\n').map(s=>s.trim()).filter(Boolean),answer_shape:data.answer_shape.split('\n').map(s=>s.trim()).filter(Boolean),connections:fd.getAll('connections')};
}
function settingsTestPanel(area,key){
 const isField=area!=='skill'||key==='coach-field',focus=area==='question'?key:(valueFocus||'business_challenge');
 const model=coachInfo().model;
 if(!state.intake.draft&&!projectCoachSettings().intake_ref)return '<p class="caption">Save a Business Intent before testing these instructions against project context.</p>';
 return `<details class="settings-detail" id="coach-test-options"><summary>Test changes</summary><div class="settings-test-inputs">${isField&&area!=='question'?settingSelector('settings-test-question','Question to test',questionOptions(focus)):''}${isField?`<label class="form-field"><span>Response to test</span><textarea id="settings-test-answer" rows="3" maxlength="20000">${esc(state.intake.draft?.body?.values?.[focus]||'')}</textarea><small>Editing this example does not change the saved intake.</small></label>`:'<p class="caption">Tests this skill against the saved intake and selected source material.</p>'}<p class="caption">Compare two fresh responses using the same intake context and selected material. Sends two requests to the configured model. Earlier AI partner conversations are excluded.</p><button type="button" data-action="settings-test" ${model.configured?'':'disabled'}>Compare responses</button>${model.configured?'':'<p class="caption">Connect a model to test behavior.</p>'}<div id="settings-test-results" role="status" aria-live="polite"></div></div></details>`;
}
function settingsTestOutput(result,title){
 if(result.status!=='completed')return `<section class="settings-test-result"><h3>${esc(title)}</h3><p class="error">${esc(result.error||'No response was completed.')}</p></section>`;
 const o=result.output;
 return `<section class="settings-test-result"><h3>${esc(title)}</h3><p class="pre">${esc(o.reply)}</p>${o.suggestions.map(s=>`<details><summary>Suggested answer</summary><p class="pre">${esc(s.text)}</p><p class="caption">${esc(s.rationale)}</p></details>`).join('')}${o.questions.map(q=>`<p class="caption"><strong>Follow-up:</strong> ${esc(q.question)}</p>`).join('')}</section>`;
}
let activeSettingsTest=null;
function attachSettingsTest(area,key,configRef){
 const form=$('#modal-form');if(!form)return;
 activeSettingsTest={area,key,configRef,comparison:null,signature:null};
 const answer=$('#settings-test-answer'),select=$('#settings-test-question');
 for(const el of [answer,select])if(el)el.addEventListener('input',e=>e.stopPropagation());
 if(select)select.addEventListener('change',()=>{answer.value=state.intake.draft?.body?.values?.[select.value]||'';invalidate();});
 function invalidate(){const box=$('#settings-test-results');if(activeSettingsTest?.comparison&&box){activeSettingsTest.comparison=null;box.innerHTML='<p class="caption">The settings or test response changed. Compare again to review their effect.</p>';}}
 form.addEventListener('input',invalidate);
 if(answer)answer.addEventListener('input',invalidate);
}
async function compareSettings(){
 const form=$('#modal-form'),editor=activeSettingsTest,box=$('#settings-test-results');
 if(!editor||!form||!form.reportValidity())return;
 editor.comparison=null;editor.signature=null;
 const fd=new FormData(form),config=coachSettingsPatch(editor.area,fd);
 const field=editor.area==='question'?editor.key:($('#settings-test-question')?.value||valueFocus||'business_challenge');
 const payload={expected:editor.configRef,area:editor.area,key:editor.key,config,draft_expected:state.intake.draft?.ref||projectCoachSettings().intake_ref,field,
  sources:selectedSourceRefs(),consent:true};
 if($('#settings-test-answer'))payload.test_answer=$('#settings-test-answer').value;
 const controls=[...form.querySelectorAll('button,input,textarea,select')].map(el=>[el,el.disabled]);
 busy=true;controls.forEach(([el])=>el.disabled=true);box.innerHTML='<p class="caption">Comparing current settings with your changes…</p>';
 try{
  const result=await command('coach-settings-test',payload);
  if(result.status==='completed'&&result.current){editor.comparison=result.ref;editor.signature=JSON.stringify(config);}
  box.innerHTML=`<div class="settings-test-comparison">${settingsTestOutput(result.results.current,'Current settings')}${settingsTestOutput(result.results.proposed,'Your changes')}</div><p class="caption">${result.current?'Both used the same answer and context. Model responses can vary; one comparison does not establish quality.':'The saved intake or configuration changed during the test. Reopen settings and compare again.'} ${result.status==='completed'?'Choose “Use in intake” to activate your configuration.':'The test is incomplete. Any completed response is retained; compare again before relying on it.'}</p>`;
  box.scrollIntoView({block:'nearest'});
 }catch(error){box.innerHTML=`<p class="error">${esc(error.message)}</p>`;}
 finally{controls.forEach(([el,disabled])=>el.disabled=disabled);busy=false;}
}
function openAgentSettings(area='question',key='',override=null){
 const c=projectCoachSettings();
 key=area==='question'?(c.config.questions[key]?key:(intakeStep==='context'?coachedField:valueFocus)||'business_challenge'):area==='skill'?(c.skills[key]?key:'coach-field'):'';
 if(area==='question'&&!c.config.questions[key])key='business_challenge';
 const value=override||(area==='persona'?c.config.persona:area==='skill'?c.config.skills[key]:c.config.questions[key]);
 let body='';
 if(area==='question')body='<p class="caption settings-intro">P02 uses the expertise below for the selected question.</p>'+settingSelector('settings-question','Question',questionOptions(key))+''+expertSettingsFields(key,value);
 if(area==='persona')body=`<p class="settings-intro">One intake AI partner uses these shared instructions and the expertise for each question.</p>${settingInput('name','AI partner name',value.name)}${settingField('remit','Role and purpose',value.remit)}${settingField('style','Communication style',value.style)}`;
 if(area==='skill')body=settingSelector('settings-skill','Skill',Object.entries(c.skills).map(([k,v])=>`<option value="${k}" ${k===key?'selected':''}>${esc(v.label)}</option>`).join(''))+`<p class="caption settings-intro">Used when you choose “${esc(c.skills[key].trigger)}”.</p>`+settingField('instructions','How the AI partner should perform this task',value,'This refines the existing skill; its output format and human decision rights stay enforced.',6);
 const skill=area==='skill'?key:'coach-field',previewKey=area==='question'?key:'business_challenge';
 modal('Intake AI partner · P02',`<div class="agent-config-navigation">${button('Agent profiles','settings-agent-registry','','secondary small')}</div>${settingsScope()}${settingsTabs(area)}<div data-agent-editor data-area="${area}" data-key="${key}">${body}</div><p class="caption settings-boundary">${esc(c.guardrails)}</p><details class="settings-detail"><summary>Change note & defaults</summary><div class="details-body">${settingInput('reason','Why this change? (optional)','','Helps explain this configuration version.',false)}${button('Use default settings','settings-agent-default',area+'|'+key,'small')}</div></details>${savedInstructionDetails(skill,previewKey)}${settingsTestPanel(area,key)}`, 'Use in intake',fd=>{
  const config=coachSettingsPatch(area,fd),test=activeSettingsTest;
  const comparison=test?.signature===JSON.stringify(config)?test.comparison:null;
  return command('coach-settings-save',{expected:c.ref,area,key,config,reason:fd.get('reason'),comparison});
 },{className:'settings-dialog'});
 if(override)dirty=true;
 for(const [id,nextArea] of [['settings-question','question'],['settings-skill','skill']]){
  const select=$('#'+id);if(!select)continue;
  // Changing the selector is navigation, not an edit to the expertise itself.
  select.addEventListener('input',e=>e.stopPropagation());
  select.addEventListener('change',()=>{if(dirty&&!confirm('Discard unsaved settings changes?')){select.value=key;return;}openAgentSettings(nextArea,select.value);});
 }
 attachInstructionPreview();
 attachSettingsTest(area,key,c.ref);
}
function attachInstructionPreview(){
 const disclosure=$('[data-saved-instructions]');if(!disclosure)return;
 disclosure.addEventListener('toggle',async()=>{if(!disclosure.open||disclosure.dataset.loaded)return;disclosure.dataset.loaded='loading';const pre=disclosure.querySelector('pre');pre.textContent='Loading…';try{const result=await command('coach-settings-preview',{skill:disclosure.dataset.skill,field:disclosure.dataset.field});pre.textContent=result.instructions;disclosure.dataset.loaded='true';}catch(error){pre.textContent=error.message;delete disclosure.dataset.loaded;}});
}
function openIntegrationSettings(){
 const sponsor=state.actor==='priya',c=sponsor?projectCoachSettings():null,model=coachInfo().model||{},items=c?.integrations?.items||[],canDefine=sponsor&&!!state.intake?.draft;
 const definitions=sponsor?`<section class="section"><div class="card-head"><h3>Other MCPs & APIs</h3>${canDefine?button('Add connection','settings-connection','','small'):''}</div><p class="caption">These additional connection definitions are saved for the project. Selected-content imports use the separate user connections above. Other operations are not active.</p>${items.length?items.map(item=>`<article class="settings-connection"><div class="card-head"><h4>${esc(item.name)}</h4>${tag('Setup saved · not active')}</div><p class="caption">${item.kind==='mcp'?'MCP server':'API'} · ${esc(item.endpoint)}</p><p>${esc(item.purpose)}</p>${canDefine?button('Edit details','settings-connection',item.id,'small'):''}</article>`).join(''):'<p class="caption">No additional MCP or API connections configured.</p>'}${!canDefine?'<p class="caption">Create a Business Intent draft to save additional MCP or API connection definitions.</p>':''}</section>`:'';
 const provider=sponsor?`<details class="settings-detail"><summary>AI partner model</summary>${tag(model.configured?'Configured':'Not configured')}<p>${model.configured?'The AI partner uses the configured model connection.':'No model connection configured.'}</p><p class="caption">Provider credentials are managed on the local server. Your AI partner runs only when asked.</p></details>`:'';
 modal('Integrations',`<p class="caption settings-scope">${esc(projectTitle())} · MCPs, APIs & work tools</p>${typeof projectToolsSummary==='function'?projectToolsSummary():''}${typeof projectMcpSetup==='function'?projectMcpSetup():''}${typeof toolImportSettings==='function'?toolImportSettings():''}${definitions}${provider}`,null,null,{className:'settings-dialog'});
}
function openConnectionForm(id){
 const c=projectCoachSettings().integrations,item=c.items.find(x=>x.id===id)||{name:'',kind:'mcp',endpoint:'',purpose:'',credential_ref:''};
 modal(id?'Edit connection details':'Add connection',`<p class="caption settings-scope">${esc(projectTitle())}</p><p class="muted">This saves setup details only. No connection or external request is made.</p>${settingInput('name','Name',item.name)}${settingSelector('connection-kind','Type',[['mcp','MCP server'],['api','API']].map(([key,title])=>`<option value="${key}" ${item.kind===key?'selected':''}>${title}</option>`).join(''),'kind')}<label class="form-field"><span>Endpoint</span><input name="endpoint" type="url" value="${esc(item.endpoint)}" placeholder="https://service.example/mcp" maxlength="2000" required><small>Base URL only. Do not include credentials or query parameters.</small></label>${settingField('purpose','What this connection is for',item.purpose,'For example, retrieve approved requirements or prepare Jira story updates.')}<details class="settings-detail"><summary>Credential reference (optional)</summary><div class="details-body">${settingInput('credential_ref','Environment variable name',item.credential_ref,'Enter a name such as JIRA_API_TOKEN, never a token or password.',false)}</div></details>`,'Save connection details',fd=>command('integration-settings-save',{...Object.fromEntries(fd),id:id||null,expected:c.ref}),{className:'settings-dialog'});
}
let adminIntegrationData=null,adminIntegrationOwner=null;
function integrationIdentity(){return state.auth?.account?.id||state.actor;}
function integrationProjectSelector(data){return settingSelector('settings-integration-project','Project','<option value="">Choose a project</option>'+data.projects.map(p=>`<option value="${esc(p.id)}" ${data.project?.id===p.id?'selected':''}>${esc(p.display_title||p.title)}</option>`).join(''));}
async function openAdminIntegrations(project){
 if(!settingsAdmin())throw Error('Only the Administrator can manage project integration settings here.');
 const owner=integrationIdentity(),selected=project||(!state.global_context&&state.project?.id),response=await fetch('/api/admin-integrations'+(selected?'?'+new URLSearchParams({project:selected}):'')),data=await response.json();
 if(!response.ok)throw Error(data.error||'Integration settings are unavailable.');if(owner!==integrationIdentity())return;
 adminIntegrationData=data;adminIntegrationOwner=owner;
 const tools=data.tools,connections=data.connections,linkLabels={research_figjam:'Research · FigJam board',design_figma:'Design · Figma file',design_figjam:'Design · FigJam board'};
 const configured=tools?Object.entries(linkLabels).filter(([key])=>tools.links[key]):[];
 modal('Integrations',`<p class="caption settings-scope">Administrator · Project setup</p>${integrationProjectSelector(data)}${data.project?`
 <section class="acx-settings-group"><div class="card-head"><h3 class="acx-subsection-title">Figma & FigJam file links</h3><a href="#main" class="item-title-link" data-action="settings-integration-files">${configured.length?'Edit file links':'Add file links'}</a></div>${configured.map(([key,title])=>`<p>${projectToolLink(tools.links[key],title)}</p>`).join('')||'<p class="caption">No file links saved.</p>'}<p class="caption">Shortcuts open the project’s files. They do not authorize MCP access.</p></section>
 <section class="acx-settings-group"><div class="card-head"><h3 class="acx-subsection-title">MCPs & APIs</h3><a href="#main" class="item-title-link" data-action="settings-integration-edit">Add connection</a></div>${connections.items.map(item=>`<article class="rule"><h4 class="acx-item-title"><a href="#main" class="item-title-link" data-action="settings-integration-edit" data-id="${esc(item.id)}">${esc(item.name)}</a></h4><p class="caption">${item.kind==='mcp'?'MCP':'API'} · Setup saved, not active</p><p class="caption">${esc(item.endpoint)}</p><p>${esc(item.purpose)}</p></article>`).join('')||'<p class="caption">No additional connections saved.</p>'}<p class="caption">These are project setup definitions. Saving does not authorize a tool or send a request.</p></section>
 <details class="settings-detail"><summary>FigJam, Figma & Lucid imports</summary><p>Research and Design users manage their own authorized imports in Settings → Integrations within the project.</p><p class="caption">Their credentials and private work remain separate. A saved endpoint or file link does not establish an active connection.</p><p>Figma MCP server: <code>${esc(tools.mcp.endpoint)}</code></p></details>`:'<p>Choose a project to see its MCP, API and tool settings. Model connections are managed separately in Settings.</p>'}`,null,null,{className:'settings-dialog'});
 const selector=$('#settings-integration-project');if(selector){selector.addEventListener('input',e=>e.stopPropagation());selector.addEventListener('change',()=>{openAdminIntegrations(selector.value||null).catch(error=>toast(error.message));});}
}
function checkedAdminIntegration(){if(!settingsAdmin()||adminIntegrationOwner!==integrationIdentity()||!adminIntegrationData?.project)throw Error('Choose a project again before editing its integrations.');return adminIntegrationData;}
async function saveAdminIntegration(action,data,selected){
 checkedAdminIntegration();const response=await fetch('/api/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf,'X-Workbench-Project':selected.project.id,'X-Workbench-Version':String(selected.project.version)},body:JSON.stringify(data)}),result=await response.json();
 if(!response.ok)throw Error(result.error||'Integration settings could not be saved.');
 if(!state.global_context&&state.project?.id===selected.project.id)await load();
 return {...result,projectLoaded:true,adminIntegrations:selected.project.id};
}
function openAdminIntegrationFiles(){
 const data=checkedAdminIntegration(),labels={research_figjam:'Research · FigJam board',design_figma:'Design · Figma file',design_figjam:'Design · FigJam board'};
 modal('Figma & FigJam file links',`<p class="caption settings-scope">${esc(data.project.display_title||data.project.title)} · Settings</p>${Object.entries(labels).map(([key,title])=>`<label class="form-field"><span>${title}</span><input name="${key}" type="url" maxlength="2000" value="${esc(data.tools.links[key]||'')}" placeholder="https://www.figma.com/${key.includes('figjam')?'board':'design'}/…"><small>Opens the selected file. Leave blank to remove this shortcut.</small></label>`).join('')}<p class="caption">Only this project’s file links change. MCP authorization remains separate.</p>`,'Save file links',fd=>saveAdminIntegration('admin-work-tools-save',{expected:data.tools.ref,links:Object.fromEntries(Object.keys(labels).map(k=>[k,fd.get(k)]))},data),{className:'settings-dialog'});
}
function openAdminIntegrationConnection(id){
 const data=checkedAdminIntegration(),item=data.connections.items.find(row=>row.id===id)||{name:'',kind:'mcp',endpoint:'',purpose:'',credential_ref:''};if(id&&!item.id)throw Error('Reopen Integrations to refresh this connection.');
 modal(id?'Edit connection details':'Add connection',`<p class="caption settings-scope">${esc(data.project.display_title||data.project.title)} · Settings</p><p class="caption">Saves setup details for this project. No connection or external request is made.</p>${settingInput('name','Name',item.name)}${settingSelector('admin-connection-kind','Type',[['mcp','MCP server'],['api','API']].map(([key,title])=>`<option value="${key}" ${item.kind===key?'selected':''}>${title}</option>`).join(''),'kind')}<label class="form-field"><span>Endpoint</span><input name="endpoint" type="url" value="${esc(item.endpoint)}" maxlength="2000" required><small>Base URL only. No credentials or query parameters.</small></label>${settingField('purpose','What this connection is for',item.purpose)}<details class="settings-detail"><summary>Credential reference (optional)</summary>${settingInput('credential_ref','Environment variable name',item.credential_ref,'A variable name only. Never enter a token or password.',false)}</details>`,'Save connection details',fd=>saveAdminIntegration('admin-integration-save',{...Object.fromEntries(fd),id:id||null,expected:data.connections.ref},data),{className:'settings-dialog'});
}
async function settingsAction(action,id){
 if(!action.startsWith('settings-'))return false;
 if(typeof expertiseAction==='function'&&await expertiseAction(action,id))return true;
 if(['settings-home','settings-integrations'].includes(action)&&typeof saveBeforeProjectChange==='function'){
  if(busy)return true;busy=true;
  try{await saveBeforeProjectChange();}finally{busy=false;}
 }else if(['settings-intake','settings-agents','settings-integrations'].includes(action)){
  if(document.querySelector('#coached-field-form,#value-proposition-form')){
   busy=true;try{await saveCoachedField();if(pageDirty)throw Error('New edits arrived while saving. Open Settings again to include them.');}finally{busy=false;}
  }else if(!abandonIntakeEdits())return true;
 }
 if(['settings-model-edit','settings-model-assign'].includes(action)&&dirty&&!confirm('Discard unsaved connection edits?'))return true;
 if(action==='settings-announcements'){if(typeof saveBeforeProjectChange==='function')await saveBeforeProjectChange();await openAnnouncementsSettings();}
 else if(action.startsWith('settings-announcement-'))await announcementSettingsAction(action,id);
 else if(action==='settings-home')openSettingsHome();
 else if(action==='settings-agent-monitor-refresh'){if(dirty&&!confirm('Discard unsaved descriptor changes?'))return true;await load();openAgentRegistry(id);}
 else if(action==='settings-agent-run-detail'){if(dirty&&!confirm('Discard unsaved descriptor changes?'))return true;openAgentRun(id);}
 else if(action==='settings-requirement-configure'){if(dirty&&!confirm('Discard unsaved descriptor changes?'))return true;openRequirementAgentSettings();}
 else if(action==='settings-models')openModelConnections();
 else if(action==='settings-model-edit')openModelConnection(id);
 else if(action==='settings-model-assign')openModelAssignments(id);
 else if(action==='settings-model-test'||action==='settings-model-remove'){
  if(busy)return true;
  if(dirty&&!confirm('Discard unsaved connection edits?'))return true;
  if(action==='settings-model-remove'&&!confirm('Remove this connection and its saved API key? Assigned projects will disconnect. Existing work stays saved.'))return true;
  busy=true;
  try{
   const result=await command(action==='settings-model-test'?'model-connection-test':'model-connection-remove',{expected:state.model_connection.revision,id,confirm_remove:true});
   await load();render();openModelConnections(result.modelConnectionProfile||null);toast(result.message);
  }finally{busy=false;}
 }
 else if(action==='settings-test')await compareSettings();
 else if(action==='settings-intake')intakeProfileForm();
 else if(action==='settings-agents')openAgentRegistry();
 else if(action==='settings-agent-registry'||action==='settings-agent-configure'){if(dirty&&!confirm('Discard unsaved settings changes?'))return true;if(action==='settings-agent-registry')openAgentRegistry(id||'P02');else openAgentSettings();}
 else if(action==='settings-integrations'){if(settingsAdmin())await openAdminIntegrations();else openIntegrationSettings();}
 else if(action==='settings-integration-files')openAdminIntegrationFiles();
 else if(action==='settings-integration-edit')openAdminIntegrationConnection(id);
 else if(action==='settings-integration-back'){if(dirty&&!confirm('Discard unsaved integration changes?'))return true;await openAdminIntegrations(adminIntegrationData?.project?.id);}
 else if(action==='settings-agent-tab'){if(dirty&&!confirm('Discard unsaved settings changes?'))return true;openAgentSettings(id);}
 else if(action==='settings-agent-default'){
  if(dirty&&!confirm('Replace unsaved edits with the default settings?'))return true;
  const [area,key]=id.split('|'),d=projectCoachSettings().defaults;
  openAgentSettings(area,key,area==='question'?d.questions[key]:area==='skill'?d.skills[key]:d.persona);
 }
 else if(action==='settings-connection')openConnectionForm(id);
 return true;
}

function agentDuration(ms){return ms===null||ms===undefined?'Not recorded':(ms/1000).toFixed(1)+' s';}
function agentMetricCards(s){
 if(!s)return '<p class="caption">No recorded runs in this group yet.</p>';
 return `<div class="agent-metrics">${[['Requests',s.total],['Completed',`${s.completed} / ${s.total}`],['Median duration',agentDuration(s.median_ms)],['Reported tokens',s.tokens===null?'Not reported':s.tokens.toLocaleString()]].map(([name,value])=>`<div><span>${esc(name)}</span><strong>${esc(value)}</strong></div>`).join('')}</div><p class="caption">${s.failed} failed · ${s.stale} stale · ${s.running} running · ${s.unknown} outcome unknown · ${s.applied} results used. Token usage reported for ${s.usage_coverage} of ${s.total} requests.</p>`;
}
function agentPerformance(key){
 const m=state.agent_monitoring||{summaries:[],runs:[],legacy_count:0};
 const summaries=m.summaries.filter(s=>s.persona_id===key),runs=m.runs.filter(r=>r.persona_id===key).slice(0,8);
 const workflow=summaries.find(s=>s.mode==='live'&&s.purpose==='workflow');
 const other=summaries.filter(s=>s!==workflow);
 return `<section class="agent-performance"><div class="card-head"><h3>Performance <span class="caption">Last 30 days</span></h3>${button('Refresh','settings-agent-monitor-refresh',key,'small')}</div><p class="caption">Live workflow runs</p>${agentMetricCards(workflow)}<p class="caption">Cost: not available. Answer quality is tracked separately in Methods & quality. Using a result does not establish its accuracy.</p>${other.length?`<details class="settings-detail"><summary>Configuration tests & other execution modes</summary>${other.map(s=>`<h4>${esc(s.mode)} · ${s.purpose==='configuration-test'?'Configuration tests':s.purpose==='evaluation'?'Evaluation responses':s.purpose==='evaluation-assessment'?'Automated assessments':'Workflow'}</h4>${agentMetricCards(s)}`).join('')}</details>`:''}${key==='P02'&&m.legacy_count?`<p class="caption">${m.legacy_count} earlier AI partner result(s) predate execution monitoring and are excluded from these metrics.</p>`:''}<details class="settings-detail"><summary>Recent runs${runs.length?' · '+runs.length:''}</summary>${runs.length?`<ul class="agent-run-list">${runs.map(r=>`<li><div><strong>${esc(r.skill)}</strong> ${tag(r.status,r.status==='failed'?'red':r.status==='succeeded'?'green':'amber')}<p class="caption">${settingsTime(r.started_at)} · ${esc(r.mode)} · ${r.purpose==='configuration-test'?'Configuration test':r.purpose==='evaluation'?'Evaluation response':r.purpose==='evaluation-assessment'?'Automated assessment':'Workflow'} · ${agentDuration(r.duration_ms)}</p></div>${button('Inspect','settings-agent-run-detail',r.ref.id,'small')}</li>`).join('')}</ul>`:'<p class="caption">No execution receipts for this role.</p>'}</details></section>`;
}
function openAgentRun(id){
 const r=state.agent_monitoring?.runs.find(r=>r.ref.id===id),full=state.records.find(r=>r.kind==='agent-execution'&&r.ref.id===id);
 if(!r)throw Error('This run is unavailable in the current project. Refresh the monitoring view.');
 if(!full){modal('Domain execution receipt',`${val('Role',r.persona_id)}${val('Status',r.status)}${val('Mode',r.mode)}${val('Duration',agentDuration(r.duration_ms))}${val('Model connection',r.model?'Recorded with this run':'Not recorded')}${val('Reported tokens',r.usage?.total_tokens??'Not reported')}${r.error?val('Issue',r.error):''}<p class="caption">Source text and AI partner output remain in the author’s domain. This receipt reports execution only.</p>`);return;}
 const b=full.body;
 modal('Agent run',`${button('Back to agent','settings-agent-registry',r.persona_id,'small')}<div class="context-strip">${tag(r.mode)}${tag(r.status)}<span>${esc(r.agent)} · v${esc(r.agent_version)}</span></div><dl class="agent-attributes"><div><dt>Task</dt><dd>${esc(r.skill)} · ${esc(r.purpose)}</dd></div><div><dt>Model</dt><dd>${r.provider?'Recorded with this run':'Not configured'}</dd></div><div><dt>Started / duration</dt><dd>${settingsTime(r.started_at)} · ${agentDuration(r.duration_ms)}</dd></div><div><dt>Configuration</dt><dd>${r.configuration?esc(label(r.configuration)):r.purpose==='configuration-test'?'Default or proposed configuration':'Default configuration'}<br><code>${esc(r.configuration_fingerprint||'Not recorded')}</code></dd></div><div><dt>Input version</dt><dd>${esc(label(r.basis))}</dd></div><div><dt>Cost / quality</dt><dd>Cost unavailable. See Methods & quality for case assessments.</dd></div></dl>${r.error?`<p class="banner signal-notice signal-critical">${esc(r.error)}</p>`:''}<details class="settings-detail"><summary>Token usage</summary><pre class="settings-instructions">${esc(JSON.stringify(r.usage,null,2)||'Not reported')}</pre></details><details class="settings-detail"><summary>Exact instructions & inputs</summary><pre class="settings-instructions">${esc(b.instructions||'Not recorded')}</pre><pre class="settings-instructions">${esc(JSON.stringify(b.context,null,2))}</pre></details><details class="settings-detail"><summary>Output</summary><pre class="settings-instructions">${esc(b.output?JSON.stringify(b.output,null,2):'No completed output was retained.')}</pre></details>`,null,null,{className:'settings-dialog'});
}


function modelConnectionStatus(profile){return profile.test?.status==='passed'?'Test passed':profile.test?.status==='failed'?'Test failed':'Not tested';}
function openModelConnections(id=null){
 const c=state.model_connection;if(!c?.available)throw Error('Model settings are not available here.');
 if(!c.can_manage){modal('Model connections',`${c.profile?`<p><strong>${esc(c.profile.name)}</strong></p><p>${esc(c.profile.model)} · ${esc(modelConnectionStatus(c.profile))}</p>`:'<p>No model connection is assigned here.</p>'}<p class="caption">The Administrator manages connections and project assignments. Documents and conversations remain saved.</p>`);return;}
 if(id){openModelConnection(id);return;}
 modal('Model connections',`<div class="card-head"><p class="caption">Sitewide setup · Administrator</p>${button('Add connection','settings-model-edit','','compact-text-action')}</div><p>Save a connection, test it, then choose which projects use it.</p>${(c.profiles||[]).map(profile=>`<article class="rule"><h3 class="acx-item-title"><a href="#main" class="item-title-link" data-action="settings-model-edit" data-id="${esc(profile.id)}">${esc(profile.name)}</a></h3><p class="caption">${esc(profile.model)} · ${esc(modelConnectionStatus(profile))} · ${Object.values(c.assignments).filter(id=>id===profile.id).length} assignment(s)</p></article>`).join('')||'<p class="caption">No connections yet.</p>'}`,null,null,{className:'settings-dialog'});
}
function openModelConnection(id=''){
 const c=state.model_connection;if(!c?.can_manage)throw Error('Only the Administrator can manage model connections.');
 const p=c.profiles.find(row=>row.id===id);if(id&&!p)throw Error('Reopen model settings to refresh this connection.');
 const assigned=c.projects.filter(project=>c.assignments[project.id]===id);
 const body=`<p class="caption">Sitewide connection · credentials stay on this computer, outside project records and Git.</p>
 ${p?`<section aria-label="Connection status"><p><strong>${esc(modelConnectionStatus(p))}</strong>${p.test?.at?' · '+settingsTime(p.test.at):''}</p>${p.test?.status==='failed'?`<p class="error" role="alert">${esc(p.test.error)}</p>`:''}<div class="actions">${button('Test connection','settings-model-test',id,'compact-text-action')}${button('Assign to projects','settings-model-assign',id,'compact-text-action')}${button('Remove connection','settings-model-remove',id,'compact-text-action')}</div></section>`:''}
 ${settingInput('name','Connection name',p?.name||'','A recognizable name, such as Research pilot.')}
 ${settingSelector('model-connection-provider','Provider',[['openai','OpenAI'],['anthropic','Anthropic']].map(([key,title])=>`<option value="${key}" ${p?.provider===key?'selected':''}>${title}</option>`).join(''),'provider')}
 <label class="form-field"><span>Model ID</span><input name="model" value="${esc(p?.model||'')}" maxlength="160" required autocomplete="off"><small>Use a model available to your API account that supports structured responses.</small></label>
 <label class="form-field"><span>API key</span><input type="password" name="api_key" value="" maxlength="4096" autocomplete="off" spellcheck="false" ${p?'':'required'}><small>${p?'Key saved. Leave blank to keep it for the same provider.':'Your provider’s API usage is billed to this key.'}</small></label>
 ${assigned.length?`<p>Changes will apply to new requests in: ${assigned.map(project=>esc(project.display_title||project.title)).join(', ')}.</p>`:'<p class="caption">No project uses this connection until you assign it.</p>'}
 <p class="caption">Saving sends no model request. Test connection sends a small test, without project data. The AI partner sends permitted context and selected document excerpts when a user asks.</p>`;
 modal(p?'Edit model connection':'Add model connection',body,'Save connection',async fd=>{
  const payload={expected:c.revision,id:p?.id||null,name:fd.get('name'),provider:fd.get('provider'),model:fd.get('model'),api_key:fd.get('api_key')};
  const key=document.querySelector('#modal-form input[name="api_key"]');if(key)key.value='';
  return command('model-connection-save',payload);
 },{className:'settings-dialog',busyLabel:'Saving…'});
}
function openModelAssignments(id){
 const c=state.model_connection,p=c?.profiles.find(row=>row.id===id);if(!c?.can_manage||!p)throw Error('Choose a saved model connection.');
 modal('Assign model connection',`<p><strong>${esc(p.name)}</strong> · ${esc(p.model)}</p><p>Choose where this connection will be used. Each project uses one connection; new projects stay unassigned.</p><fieldset class="model-assignment-list"><legend>Destinations</legend>${c.projects.map((project,i)=>{const current=c.profiles.find(row=>row.id===c.assignments[project.id]);return `<label class="checkbox"><input type="checkbox" name="projects" aria-label="${esc(project.display_title||project.title)}" aria-describedby="model-assignment-status-${i}" value="${esc(project.id)}" ${current?.id===id?'checked':''}><span>${esc(project.display_title||project.title)} <small id="model-assignment-status-${i}">${current?'Current: '+esc(current.name):'Not assigned'}</small></span></label>`;}).join('')}</fieldset><p class="caption">Checking replaces the current connection for that destination. Unchecking removes this connection there. Changes affect new requests; existing records and conversations remain.</p>`,'Save assignments',fd=>command('model-connection-assign',{expected:c.revision,id,projects:fd.getAll('projects')}),{className:'settings-dialog'});
}

let announcementsEditor=null;
function announcementOwner(){return state.auth?.account?.id||state.actor;}
function checkedAnnouncementsEditor(){
 if(!settingsAdmin()||!announcementsEditor||announcementsEditor.owner!==announcementOwner())throw Error('Reopen Announcements in Settings.');
 return announcementsEditor;
}
async function openAnnouncementsSettings(){
 if(!settingsAdmin())throw Error('Only the Administrator can manage Home announcements.');
 if(dirty&&!confirm('Discard unsaved settings changes?'))return;
 const owner=announcementOwner(),response=await fetch('/api/admin-announcements'),data=await response.json();
 if(!response.ok)throw Error(data.error||'Announcements are unavailable.');if(owner!==announcementOwner())return;
 announcementsEditor={owner,data,items:data.items.map(item=>({...item})),unsaved:false};showAnnouncementsEditor();
}
function captureAnnouncementsForm(){
 const editor=checkedAnnouncementsEditor(),form=$('#modal-form');
 editor.items=[...form.querySelectorAll('[data-announcement-entry]')].map(el=>({title:el.querySelector('[name="announcement-title"]').value,body:el.querySelector('[name="announcement-body"]').value}));
 editor.unsaved=JSON.stringify(editor.items)!==JSON.stringify(editor.data.items);return editor;
}
async function saveAnnouncementsChange(action,data,editor){
 checkedAnnouncementsEditor();
 const fields=[...($('#modal-form')?.querySelectorAll('input,textarea')||[])].map(el=>[el,el.disabled]);fields.forEach(([el])=>el.disabled=true);
 try{
  const result=await command(action,{expected:editor.data.revision,...data});
  if(state.global_context||view==='projects')await loadHome();
  return {...result,projectLoaded:true,announcementsEditor:true};
 }finally{fields.forEach(([el,disabled])=>el.disabled=disabled);}
}
function showAnnouncementsEditor(){
 const editor=checkedAnnouncementsEditor(),data=editor.data,published=data.published;
 const status=editor.unsaved?'Unsaved draft changes':data.pending?'Draft changes · not published':published?'Published on Home':'Sample updates are showing';
 modal('Announcements',`<p class="caption settings-scope">Sitewide · Home page</p><p><strong id="announcement-edit-status">${status}</strong></p>${published?`<p class="caption">Published ${settingsTime(published.at)} · ${esc(published.author.name)}</p>`:''}<p class="caption">Up to three short updates. Publish makes them visible to everyone on Home.</p>
 <div class="announcements-editor">${editor.items.map((item,i)=>`<section data-announcement-entry="${i}"><div class="card-head"><h3>Announcement ${i+1}</h3><button type="button" class="compact-text-action remove-control" data-action="settings-announcement-remove" data-id="${i}" aria-label="Remove announcement ${i+1}" title="Remove announcement ${i+1}"><span aria-hidden="true">×</span></button></div><label class="form-field"><span>Title</span><input name="announcement-title" aria-label="Announcement ${i+1} title" value="${esc(item.title)}" maxlength="100" required></label><label class="form-field"><span>Message</span><textarea name="announcement-body" aria-label="Announcement ${i+1} message" rows="3" maxlength="500" required>${esc(item.body)}</textarea></label></section>`).join('')||'<p class="caption">No updates in this draft. Publishing it will clear the announcement area; earlier publications remain in history.</p>'}</div>
 <div class="actions">${editor.items.length<3?button('Add announcement','settings-announcement-add','','compact-text-action'):''}</div>
 ${data.history.length?`<details class="settings-detail"><summary>Publication history (${data.history.length})</summary>${data.history.map(p=>`<article class="rule"><p class="caption">Published ${settingsTime(p.at)} · ${esc(p.author.name)}</p>${homeAnnouncementList(p.items)}</article>`).join('')}</details>`:''}`,'Save draft',async()=>{const current=captureAnnouncementsForm();return saveAnnouncementsChange('announcements-save',{items:current.items},current);},{className:'settings-dialog announcements-settings-dialog',footerActions:button('Preview & publish','settings-announcement-preview','','compact-text-action')});
 $('#modal-form')?.addEventListener?.('input',()=>{editor.unsaved=true;const status=$('#announcement-edit-status');if(status)status.textContent='Unsaved draft changes';});
 dirty=editor.unsaved;
}
function previewAnnouncements(){
 const form=$('#modal-form');if(!form.reportValidity())return;
 const editor=captureAnnouncementsForm(),canPublish=!editor.unsaved&&editor.data.pending;
 modal('Preview announcements',`<p>This is how the updates will appear on Home for everyone.</p><div class="sponsor-home announcements-preview"><aside class="home-announcements"><h2>Announcements</h2>${homeAnnouncementList(editor.items)}</aside></div>${!canPublish?`<p class="caption">${editor.unsaved||!editor.data.published?'Save this draft before publishing.':'This version is already published.'}</p>`:''}<div class="actions">${button('Back to editing','settings-announcement-back','','compact-text-action')}</div>`,canPublish?'Publish to Home':null,canPublish?()=>saveAnnouncementsChange('announcements-publish',{confirm:true},editor):null,{className:'settings-dialog'});
 dirty=editor.unsaved;
}
async function announcementSettingsAction(action,id){
 const editor=checkedAnnouncementsEditor();
 if(action==='settings-announcement-preview'){previewAnnouncements();return;}
 if(action==='settings-announcement-back'){showAnnouncementsEditor();return;}
 captureAnnouncementsForm();
 if(action==='settings-announcement-add'&&editor.items.length<3)editor.items.push({title:'',body:''});
 else if(action==='settings-announcement-remove'&&/^\d+$/.test(id)&&Number(id)<editor.items.length)editor.items.splice(Number(id),1);
 else return;
 editor.unsaved=JSON.stringify(editor.items)!==JSON.stringify(editor.data.items);showAnnouncementsEditor();
}

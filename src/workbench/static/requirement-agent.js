// P04 operates on saved, accepted intake; proposals enter drawers only by human choice.
function requirementAgentControls(drawer){
 const runtime=state.coaching?.settings?.agent_registry?.profiles.find(p=>p.id==='P04')?.implementation;
 if(!runtime||!drawer.included)return '';
 const latest=state.requirement_agent?.runs?.find(r=>r.body.drawer===drawer.key&&(!drawer.requirement_id||(r.body.requirement_id||'REQ-INTAKE-'+r.body.drawer)===drawer.requirement_id));
 const target=drawer.requirement_id?JSON.stringify({drawer:drawer.key,requirement_id:drawer.requirement_id}):drawer.key;
 return `<section class="requirement-agent-controls"><div class="card-head"><strong>Drafting tools</strong>${tag(runtime.label,runtime.mode==='live'?'green':'amber')}</div><div class="actions">${button(drawer.requirement?'Suggest a revision':'Draft requirement','req-agent-draft',target,'small')}${drawer.requirement?button('Ask your AI partner about this requirement','field-coach-area',target,'small'):''}${latest?button('View latest advice','req-agent-result',latest.ref.id,'small'):''}</div><p class="caption">Uses saved intake. You review and choose what enters this drawer.</p></section>`;
}
function openRequirementAgentSettings(){
 const c=state.requirement_agent.settings;
 modal('Requirement Assistant · P04',`<p class="caption">${esc(projectTitle())} · ${c.ref?'Configuration v'+c.ref.revision:'Default configuration'}</p>${settingField('tailor','Scaffold tailoring guidance',c.config.tailor,'Connects the configured areas to this project’s Business Intent and requirements.',5)}${settingField('draft','Drafting guidance',c.config.draft,'Used when drafting a requirement for a selected drawer.',5)}${settingField('review','Review guidance',c.config.review,'Used for requirement review and the goal, measure and requirement field AI partner.',5)}<details class="settings-detail"><summary>Fixed task boundaries</summary><pre class="settings-instructions">${esc(c.guardrails)}</pre></details><p class="caption">These settings apply to the next request. Run the assistant in a drawer and inspect its result and performance here.</p>`,'Save configuration',fd=>command('requirement-agent-settings',{expected:c.ref,draft:fd.get('draft'),review:fd.get('review'),tailor:fd.get('tailor')}),{className:'settings-dialog'});
}
function requirementResultContent(r){
 const b=r.body,o=b.output;
 return `<p class="caption">${esc(b.drawer_label)} · ${b.skill==='draft'?'Drafting':'Advisory review'} · ${settingsTime(b.at)}</p>${para(o.summary)}${o.findings.length?`<section><h3>Review findings</h3>${o.findings.map(f=>`<div class="rule"><strong>${esc(f.issue)}</strong>${para(f.recommendation)}</div>`).join('')}</section>`:''}${o.open_questions.length?`<section><h3>Still to resolve</h3><ul>${o.open_questions.map(q=>`<li>${esc(q)}</li>`).join('')}</ul></section>`:''}<details class="settings-detail"><summary>Basis & rationale</summary>${para(o.rationale)}<ul>${o.basis_fields.map(k=>`<li><strong>${esc(intakeNames[k]||k)}</strong>${para(b.context.values[k])}</li>`).join('')}</ul><p class="caption">Saved intake ${esc(label(b.basis))} · Configuration ${b.configuration?'v'+b.configuration.revision:'defaults'} · ${esc(b.agent)} v${esc(b.agent_version)}</p></details>`;
}
function openRequirementResult(id){
 const r=state.requirement_agent?.runs.find(r=>r.ref.id===id);if(!r)throw Error('This result is unavailable. Refresh the workbench.');
 const b=r.body,canApply=b.skill==='draft'&&b.output.requirement&&!b.applied;
 const fresh=JSON.stringify(b.basis)===JSON.stringify(state.intake.draft.ref)&&b.configuration_fingerprint===state.requirement_agent.settings.fingerprint;
 const controls=canApply&&fresh?`<div class="ac-suggestion">${typeof acSuggestionHead==='function'?acSuggestionHead('From your AI partner · edit it here; it becomes a draft in the drawer only when you use it'):''}${field('requirement','Proposed requirement',b.output.requirement)}${field('acceptance_criteria','Acceptance criteria',b.output.acceptance_criteria.join('\n'))}<label class="checkbox"><input type="checkbox" required><span>I reviewed this wording and want to use it as a draft in the selected drawer.</span></label></div>`:canApply?'<p class="banner signal-notice signal-advisory">The intake or configuration has changed. Generate a new draft before applying it.</p>':b.applied?'<p class="caption">This draft was used. Its history is retained.</p>':'';
 modal('Requirement Assistant result',requirementResultContent(r)+controls,canApply&&fresh?'Use in drawer':null,canApply&&fresh?fd=>command('requirement-agent-apply',{result:r.ref,expected:state.intake.draft.ref,requirement:fd.get('requirement'),acceptance_criteria:fd.get('acceptance_criteria'),confirm:true}):null,{className:'settings-dialog'});
}
async function requirementAgentAction(action,id){
 if(!action.startsWith('req-agent-'))return false;
 if(action==='req-agent-result'){openRequirementResult(id);return true;}
 if(pageDirty)throw Error('Save the scaffold before requesting assistance so the agent receives your current wording.');
 const skill=action==='req-agent-draft'?'draft':action==='req-agent-review'?'review':null;
 if(!skill)return false;
 const target=id?.startsWith('{')?JSON.parse(id):{drawer:id};
 const area=scaffoldLeaves().find(d=>d.key===target.drawer&&d.included);
 const entry=target.requirement_id&&area?requirementDrafts(area,target.drawer).find(x=>x.id===target.requirement_id):null;
 const drawer=entry?{...area,...entry,label:entry.title||area.label}:area;if(!drawer)throw Error('Choose an included drawer.');
 const model=coachInfo().model;
 modal(skill==='draft'?'Draft a requirement':'Review this requirement',`${val('Drawer',(drawer.category?drawer.category+' / ':'')+drawer.label)}${areaCriteria(drawer)}<p>${skill==='draft'?'Prepare a candidate requirement and acceptance criteria from the saved intake.':'Check the saved requirement for clarity, gaps, and consistency with the intake.'}</p><p class="caption">Sends the saved intake and this drawer to the configured model. Your wording remains unchanged until you choose to use a proposal.</p>`,skill==='draft'?'Draft requirement':'Review requirement',async()=>{const result=await command('requirement-agent-run',{skill,drawer:target.drawer,...(target.requirement_id?{requirement_id:target.requirement_id}:{}),expected:state.intake.draft.ref,consent:true});return {...result,requirementResult:result.ref.id};});
 return true;
}

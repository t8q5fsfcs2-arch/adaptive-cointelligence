// Methods affect live instructions. Evaluations use fictional cases and never fill intake fields.
function qualityCases(persona){return (state.agent_quality?.cases||[]).filter(c=>c.persona_id===persona);}
function qualityResults(id){return (state.agent_quality?.results||[]).filter(r=>r.case.id===id);}
function qualityVerdict(r){
 if(!r)return 'Not tested';
 if(r.status!=='assessed')return r.status.replaceAll('-',' ');
 const ratings=Object.values(r.assessment||{}).map(v=>v.rating);
 return ratings.includes('needs-work')?'Automated: needs work':ratings.includes('uncertain')?'Automated: uncertain':'Automated: criteria met';
}
function expertiseSummary(persona){
 if(!state.agent_methods?.[persona])return '';
 const cases=qualityCases(persona),latest=cases.map(c=>qualityResults(c.id).find(r=>r.current&&r.signature.mode==='live'));
 const tested=latest.filter(r=>r?.status==='assessed').length,reviewed=latest.filter(r=>r?.human_review).length;
 return `<section class="agent-expertise-summary"><h3>Methods & quality</h3><p class="caption">${Object.keys(state.agent_methods[persona].methods).length} methods · ${tested} / ${cases.length} cases assessed with current settings · ${reviewed} human-reviewed</p>${button('View methods & evaluation','settings-expertise',persona,'compact-text-action')}<p class="caption">Case results are evidence to inspect, not expert certification.</p></section>`;
}
function expertiseTabs(persona,tab){return `<nav class="settings-tabs" aria-label="Methods and quality">${[['methods','Methods'],['quality','Evaluation']].map(([id,title])=>`<button type="button" data-action="settings-expertise-tab" data-id="${persona}|${id}" ${id===tab?'aria-current="page" class="selected"':''}>${title}</button>`).join('')}</nav>`;}
function methodCard(m,persona){
 return `<details class="settings-detail method-card"><summary>${esc(m.name)}</summary><div class="details-body"><p class="caption">${m.source.url?`<a href="${esc(m.source.url)}" target="_blank" rel="noopener noreferrer">${esc(m.source.title)}</a>`:esc(m.source.title)}</p><p>${esc(m.guidance)}</p><dl class="agent-attributes"><div><dt>Starting answer</dt><dd>${esc(m.example.before)}</dd></div><div><dt>Stronger response</dt><dd>${esc(m.example.after)}</dd></div><div><dt>Why this helps</dt><dd>${esc(m.example.lesson)}</dd></div></dl><p class="caption">${esc(m.limits)}</p>${m.project_guidance?`<h4>Your project refinement</h4><p class="pre">${esc(m.project_guidance)}</p><p class="caption pre">${esc(m.project_example)}</p>`:''}${button('Refine this method','settings-method-edit',persona+'|'+m.id,'secondary small')}</div></details>`;
}
function openExpertise(persona='P02',tab='methods',caseId=''){
 const methods=state.agent_methods?.[persona];if(!methods)throw Error('Methods are available for the two implemented agents.');
 const cases=qualityCases(persona),chosen=cases.find(c=>c.id===caseId)||cases[0];
 let body=tab==='methods'?`<p>These methods guide the agent’s responses. Refine their application for this project.</p><p class="caption">Library v${esc(methods.library_version)} · ${methods.ref?'Project refinement v'+methods.ref.revision:'Default guidance'} · Examples are fictional.</p>${Object.values(methods.methods).map(m=>methodCard(m,persona)).join('')}`:qualityPanel(persona,chosen);
 modal(`${persona} · Methods & quality`,`${button('Back to agent','settings-agent-registry',persona,'secondary small')}${expertiseTabs(persona,tab)}${body}`,null,null,{className:'settings-dialog expertise-dialog'});
 const select=$('#quality-case');if(select){select.addEventListener('input',e=>e.stopPropagation());select.addEventListener('change',()=>openExpertise(persona,'quality',select.value));}
}
function qualityPanel(persona,c){
 const latest=qualityResults(c.id)[0],previous=qualityResults(c.id).slice(1).find(r=>comparable(latest,r));
 return `<p>Test the saved configuration on a fictional case. Compare the response with the criteria before relying on it.</p>${settingSelector('quality-case','Case',qualityCases(persona).map(x=>`<option value="${x.id}" ${x.id===c.id?'selected':''}>${esc(x.title)}</option>`).join(''))}<details class="settings-detail"><summary>Test input & criteria</summary><dl class="agent-attributes">${Object.entries(c.values).map(([k,v])=>`<div><dt>${esc(shortQuestion(k))}</dt><dd>${esc(v)}</dd></div>`).join('')}${c.drawer?`<div><dt>Requirement</dt><dd>${esc(c.drawer.requirement)}</dd></div>`:''}</dl><h4>Assessment criteria</h4><ol>${c.criteria.map(x=>`<li>${esc(x.text)}</li>`).join('')}</ol></details><div class="quality-actions">${button('Run test','settings-quality-run',c.id,'primary')}${latest?button('Inspect result','settings-quality-detail',latest.ref.id,'secondary'):''}${previous?button('Compare versions','settings-quality-compare',latest.ref.id+'|'+previous.ref.id,'secondary'):''}</div><p class="caption">Two model requests: agent response, then automated assessment. Uses the fictional input above and this project’s agent settings; excludes project answers and documents.</p><div id="quality-progress" role="status" aria-live="polite"></div>${latest?`<section class="quality-latest"><h3>Latest result</h3><p>${esc(qualityVerdict(latest))} · ${latest.current?'Current settings':'Earlier settings'} · ${esc(latest.signature.mode)}</p><p class="caption">${settingsTime(latest.at)} · ${latest.human_review?'Human review recorded':'Human review pending'}</p>${latest.error?`<p class="error">${esc(latest.error)}</p>`:''}</section>`:''}<p class="caption">${esc(state.agent_quality.assessment_limit)}</p><details class="settings-detail"><summary>All cases & recent results</summary><ul class="agent-run-list">${qualityCases(persona).map(x=>{const r=qualityResults(x.id)[0];return `<li><div><strong>${esc(x.title)}</strong><p class="caption">${esc(qualityVerdict(r))}${r&&!r.current?' · Earlier settings':''}</p></div>${button(r?'Inspect':'Open','settings-quality-case',persona+'|'+x.id,'secondary small')}</li>`;}).join('')}</ul>${qualityResults(c.id).length>1?`<h4>This case’s history</h4><ul class="agent-run-list">${qualityResults(c.id).slice(0,12).map(r=>`<li><span>${settingsTime(r.at)} · ${esc(qualityVerdict(r))} · ${r.current?'current':'earlier'}</span>${button('Inspect','settings-quality-detail',r.ref.id,'secondary small')}</li>`).join('')}</ul>`:''}</details>`;
}
function openMethodEditor(persona,id){
 const cfg=state.agent_methods[persona],m=cfg.methods[id];
 modal(`${m.name} · project refinement`,`${button('Back to methods','settings-expertise',persona,'secondary small')}<p class="caption">Adds project guidance to the method. Its source, base guidance and evidence rules stay visible.</p><details class="settings-detail"><summary>Base guidance</summary><p>${esc(m.guidance)}</p><p class="caption">${esc(m.limits)}</p></details>${settingField('guidance','How to apply this method here',m.project_guidance||'','Describe the emphasis or constraints the agent should use.',5,3000)}${settingField('example','Example of the behavior you want',m.project_example||'','Use fictional information if you plan to run evaluation cases.',5,2000)}`,'Save refinement',fd=>command('agent-method-save',{persona_id:persona,method_id:id,expected:cfg.ref,guidance:fd.get('guidance'),example:fd.get('example')}),{className:'settings-dialog'});
}
async function runQualityCase(id){
 const c=state.agent_quality.cases.find(c=>c.id===id),box=$('#quality-progress'),form=$('#modal-form');
 const controls=[...form.querySelectorAll('button,input,textarea,select')].map(el=>[el,el.disabled]);
 busy=true;controls.forEach(([el])=>el.disabled=true);box.textContent='Running the agent and assessing its response…';
 try{const result=await command('agent-quality-run',{case_id:id,expected:state.agent_quality.signatures[id],consent:true});await load();openQualityDetail(result.ref.id);}
 catch(error){box.textContent=error.message;}
 finally{controls.forEach(([el,disabled])=>el.disabled=disabled);busy=false;}
}
function qualityResult(id){const r=state.agent_quality.results.find(r=>r.ref.id===id);if(!r)throw Error('Evaluation unavailable. Refresh the project.');return r;}
function qualityResponse(r){
 const o=r.output;if(!o)return `<p class="caption">${esc(r.error||'No completed response.')}</p>`;
 if(r.case.persona_id==='P02')return `<p class="pre">${esc(o.reply)}</p>${o.suggestions.map(s=>`<blockquote><p class="pre">${esc(s.text)}</p><p class="caption">${esc(s.rationale)}</p></blockquote>`).join('')}${o.questions.map(q=>`<p><strong>Follow-up:</strong> ${esc(q.question)}</p>`).join('')}`;
 return `<p class="pre">${esc(o.summary)}</p>${o.requirement?`<blockquote>${esc(o.requirement)}</blockquote>`:''}${o.acceptance_criteria.length?`<ul>${o.acceptance_criteria.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}${o.findings.map(f=>`<p><strong>${esc(f.issue)}</strong><br>${esc(f.recommendation)}</p>`).join('')}${o.open_questions.map(q=>`<p>${esc(q)}</p>`).join('')}`;
}
function qualityCriteria(r){return `<div class="quality-criteria">${r.case.criteria.map(c=>{const a=r.assessment?.[c.id],h=r.human_review?.ratings?.[c.id];return `<article><h4>${esc(c.text)}</h4><p><strong>Automated: ${esc(a?.rating||'Not assessed')}</strong><br>${esc(a?.note||'')}</p><p class="caption"><strong>Human: ${esc(h?.rating||'Pending')}</strong>${h?'<br>'+esc(h.note):''}</p></article>`;}).join('')}</div>`;}
function openQualityDetail(id){
 const r=qualityResult(id);
 modal(r.case.title,`${button('Back to evaluation','settings-quality-case',r.case.persona_id+'|'+r.case.id,'secondary small')}<p class="caption">${settingsTime(r.at)} · ${esc(r.signature.mode)} · ${r.current?'Current settings':'Earlier settings'}</p><h3>Agent response</h3>${qualityResponse(r)}<h3>Assessment</h3>${qualityCriteria(r)}<p class="caption">${esc(state.agent_quality.assessment_limit)}</p>${r.output?button(r.human_review?'Revise human review':'Record human review','settings-quality-review',id,'secondary'):''}${r.human_review?`<p class="caption">Recorded by ${esc(r.human_review.reviewer)} · ${settingsTime(r.human_review.at)}<br>Reviewer’s stated experience: ${esc(r.human_review.reviewer_context)}<br>${esc(r.human_review.note)}</p>`:''}<details class="settings-detail"><summary>Exact version & test input</summary><pre class="settings-instructions">${esc(JSON.stringify({signature:r.signature,case:r.case},null,2))}</pre></details>`,null,null,{className:'settings-dialog'});
}
function openQualityReview(id){
 const r=qualityResult(id),h=r.human_review;
 modal('Human assessment',`<p>${esc(r.case.title)}</p><details class="settings-detail" open><summary>Agent response</summary>${qualityResponse(r)}</details>${r.case.criteria.map(c=>`${settingSelector('rating-'+c.id,c.text,[['','Choose a rating'],['pass','Meets criterion'],['needs-work','Needs work'],['uncertain','Uncertain']].map(([k,v])=>`<option value="${k}" ${h?.ratings[c.id].rating===k?'selected':''}>${v}</option>`).join(''),'rating-'+c.id)}${settingField('note-'+c.id,'Reason',h?.ratings[c.id].note||'','Point to what the response did or missed.',2,700)}`).join('')}${settingInput('reviewer_context','Your relevant experience',h?.reviewer_context||'','Recorded as self-reported experience, not verified credentials.')}${settingField('note','Overall assessment & next improvement',h?.note||'','This assesses the saved response; it does not approve project work.',3,1500)}`,'Save human assessment',fd=>command('agent-quality-review',{expected:r.ref,ratings:Object.fromEntries(r.case.criteria.map(c=>[c.id,{rating:fd.get('rating-'+c.id),note:fd.get('note-'+c.id)}])),reviewer_context:fd.get('reviewer_context'),note:fd.get('note')}),{className:'settings-dialog'});
}
function comparable(a,b){return a&&b&&a.output&&b.output&&a.signature.configuration_fingerprint!==b.signature.configuration_fingerprint&&['agent_version','case_fingerprint','case_version','model','provider','mode','assessor_version'].every(k=>a.signature[k]===b.signature[k]);}
function openQualityComparison(aid,bid){
 const a=qualityResult(aid),b=qualityResult(bid);if(!comparable(a,b))throw Error('Choose the same case, model and agent version with different configurations.');
 modal('Compare configuration versions',`${button('Back to evaluation','settings-quality-case',a.case.persona_id+'|'+a.case.id,'secondary small')}<p>${esc(a.case.title)}</p><p class="caption">Same fictional input, rubric, agent version and model. Each response is a single sample; model variation may also explain differences.</p><div class="settings-test-comparison">${[[b,'Earlier configuration'],[a,'Later configuration']].map(([r,title])=>`<section><h3>${title}</h3><p class="caption">${settingsTime(r.at)} · ${esc(qualityVerdict(r))}</p>${qualityResponse(r)}${qualityCriteria(r)}</section>`).join('')}</div>`,null,null,{className:'settings-dialog'});
}
async function expertiseAction(action,id){
 if(!['settings-expertise','settings-expertise-tab','settings-method-edit','settings-quality-run','settings-quality-case','settings-quality-detail','settings-quality-review','settings-quality-compare'].includes(action))return false;
 if(dirty&&!confirm('Discard unsaved settings changes?'))return true;
 const [a,b]=id.split('|');
 if(action==='settings-expertise')openExpertise(a);
 if(action==='settings-expertise-tab')openExpertise(a,b);
 if(action==='settings-method-edit')openMethodEditor(a,b);
 if(action==='settings-quality-case')openExpertise(a,'quality',b);
 if(action==='settings-quality-run')await runQualityCase(id);
 if(action==='settings-quality-detail')openQualityDetail(id);
 if(action==='settings-quality-review')openQualityReview(id);
 if(action==='settings-quality-compare')openQualityComparison(a,b);
 return true;
}

function questionMethods(key){
 const cfg=state.agent_methods?.P02;if(!cfg)return '';
 const methods=Object.values(cfg.methods).filter(m=>m.fields.includes(key));
 return `<details class="settings-detail"><summary>Methods behind this question</summary>${methods.map(m=>`<p><strong>${esc(m.name)}</strong><br><span class="caption">${esc(m.source.title)}</span></p>`).join('')}${button('Inspect or refine methods','settings-expertise','P02','secondary small')}</details>`;
}

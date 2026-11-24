'use strict';
// Saved model judgments are read only. Opening this view never requests a model.
const businessAssessmentDimensions={'logical-rigor':'Reasoning','material-coverage':'Material coverage','evidence-quality':'Evidence quality',applicability:'Applicability','independent-patterns':'Independent patterns',counterevidence:'Counterevidence'};
const businessAssessmentConclusions={investigate:'Investigate within limits',refine:'Refine the business argument',reconsider:'Reconsider the starting proposition'};
function businessAssessmentInfo(){return state.coaching?.business_assessments||null;}
function businessAssessmentCurrent(){return businessAssessmentInfo()?.current||null;}
function businessAssessmentLevel(value){return typeof confidenceLabel==='function'?confidenceLabel(value):({'not-rated':'Not rated',low:'Low',moderate:'Moderate',high:'High'})[value]||'Not rated';}
function businessAssessmentDateRead(at){return typeof recordedDate==='function'?recordedDate('Assessed',at):esc(at||'Date not recorded');}
function businessAssessmentText(value){return typeof value==='string'?value.replaceAll('-',' '):'';}
function businessAssessmentCitations(value){
 const rows=[],seen=new Set();
 const collect=node=>{if(Array.isArray(node)){node.forEach(collect);return;}if(!node||typeof node!=='object')return;if(node.quote&&(node.source_ref||node.source)){const key=JSON.stringify([node.source_ref||node.source,node.quote]);if(!seen.has(key)){seen.add(key);rows.push(node);}return;}Object.values(node).forEach(collect);};
 collect(value);return rows;
}
function businessAssessmentCitationRead(c){
 const raw=c.source_ref||(typeof c.source==='object'?c.source:null),name=c.source_title||(raw&&typeof referenceText==='function'?referenceText(raw):'Selected evidence excerpt');
 return `<figure class="business-assessment-citation"><blockquote>${esc(c.quote||'')}</blockquote><figcaption>${esc(name)}${c.page?' · p. '+esc(c.page):''}</figcaption>${raw?sourceDetails(raw):''}</figure>`;
}
function businessAssessmentConfidenceRead(confidence){
 if(!confidence)return '';
 const dimensions=confidence.dimensions||{},patterns=confidence.patterns;
 return `${val('Claim',confidence.claim)}${val('Scope',confidence.scope)}${val('Reason for confidence',confidence.rationale)}${val('Limits',confidence.limits)}<details><summary>Reasoning & evidence</summary><div class="details-body business-assessment-reasons">${Object.entries(businessAssessmentDimensions).map(([key,title])=>{const d=dimensions[key];return d?`<section><h4>${title} · ${esc(businessAssessmentText(d.judgment))}</h4>${para(d.rationale)}${d.limits?val('Limits',d.limits):''}${(d.citations||[]).map(businessAssessmentCitationRead).join('')}</section>`:'';}).join('')}${patterns?`<section><h4>Pattern basis · ${esc(businessAssessmentText(patterns.status))}</h4>${val('Recurrence',patterns.recurrence)}${val('Exceptions',patterns.exceptions)}${val('Population limits',patterns.population_limits)}${(patterns.families||[]).map((family,i)=>`<details><summary>Evidence family ${i+1} · ${esc(businessAssessmentText(family.relationship))}</summary><div class="details-body">${para(family.rationale)}${(family.citations||[]).map(businessAssessmentCitationRead).join('')}</div></details>`).join('')}</section>`:''}</div></details>`;
}
function businessAssessmentOutputRead(output,{standard,at,actor,mode,basis,shared=false,historical=false}={}){
 if(!output?.confidence)return '';
 return `<div class="business-assessment-output"><p class="business-assessment-result">${esc(businessAssessmentConclusions[output.conclusion]||'Recorded conclusion')}</p><p class="business-assessment-signals">${historical?'Historical confidence':'Confidence'}: ${esc(businessAssessmentLevel(output.confidence.level))} <span aria-hidden="true">·</span> Argument completeness: ${esc(businessAssessmentText(output.completeness?.status)||'Not recorded')}</p><p>${esc(output.summary||'')}</p>${output.next_action?val('Next useful action',output.next_action):''}<details><summary>Assessment reasoning & limits</summary><div class="details-body">${businessAssessmentConfidenceRead(output.confidence)}${output.completeness?`${val('Completeness reasoning',output.completeness.rationale)}${output.completeness.missing_parts?.length?`<ul>${output.completeness.missing_parts.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}`:''}${output.claim_assessments?.length?`<details><summary>Material claims (${output.claim_assessments.length})</summary><div class="details-body">${output.claim_assessments.map((claim,i)=>`<details><summary>Claim ${i+1} · ${esc(businessAssessmentText(claim.judgment))} · Confidence: ${esc(businessAssessmentLevel(claim.confidence?.level))}</summary><div class="details-body">${para(claim.rationale)}${businessAssessmentConfidenceRead(claim.confidence)}${(claim.evidence||[]).map(businessAssessmentCitationRead).join('')}</div></details>`).join('')}</div></details>`:''}${output.limits?val('Assessment limits',output.limits):''}<p class="caption">${mode==='simulated'?'Scripted example':'Model judgment'}${actor?' · Requested by '+esc(state.actors?.[actor]?.name||'Recorded project member'):''}${at?' · '+businessAssessmentDateRead(at):''}${basis?' · Business Intent v'+esc(basis.revision):''}</p><p class="caption">${shared?'Explicitly released assessment':'Private assessment'}. Confidence concerns the recorded claim and evidence; it does not approve requirements, authorize delivery or establish benefit.</p>${sourceDetails([standard?.ref||standard,basis].filter(Boolean))}</div></details></div>`;
}
function businessAssessmentPublishedBasis(basis=null){
 const rows=(state.records||[]).filter(x=>!x.scope||String(x.scope).startsWith('project:'));
 const intent=basis?.published_intent_ref?rows.find(x=>x.kind==='intent'&&x.ref.id===basis.published_intent_ref.id&&x.ref.revision===basis.published_intent_ref.revision):rows.filter(x=>x.kind==='intent').sort((a,b)=>b.ref.revision-a.ref.revision)[0];
 const anchor=intent?.body?.business_assessment?.ref;if(!anchor)return null;
 const record=rows.find(x=>x.kind==='business-assessment-release'&&x.ref.id===anchor.id&&x.ref.revision===anchor.revision);if(!record?.body?.assessment)return null;
 const stale=[],standard=record.body.standard;if(!standard?.ref||!standard.body)stale.push('The exact assessment standard is unavailable in this view.');
 for(const raw of [...(record.body.sources||[]),...(standard?.ref?[standard.ref]:[])]){const source=rows.find(x=>x.ref.id===raw.id);if(!source)stale.push('An exact released evidence source or standard is unavailable in this view.');else if(source.ref.revision!==raw.revision)stale.push('Released evidence or the assessment standard has a newer version.');else if(standard?.ref?.id===raw.id&&JSON.stringify(source.body)!==JSON.stringify(standard.body))stale.push('The saved assessment standard cannot be verified.');}
 return {intent,record,stale:[...new Set(stale)]};
}
function businessAssessmentPublishedPanel(published=businessAssessmentPublishedBasis()){
 if(!published)return '';
 const {record,intent,stale}=published,body=record.body,output=body.assessment;
 return `<section class="business-assessment-panel business-assessment-published" aria-label="Published business assessment"><h3>Published business assessment · v${esc(intent.ref.revision)}</h3><p class="business-assessment-signals">${stale.length?'Review needed':`Confidence: ${esc(businessAssessmentLevel(output.confidence?.level))} · Argument: ${esc(businessAssessmentText(output.completeness?.status))}`}</p><details><summary>Published conclusion & limits</summary><div class="details-body">${stale.length?`<p class="business-assessment-caution">${stale.map(esc).join(' ')}</p>`:''}${businessAssessmentOutputRead(output,{standard:body.standard,at:body.assessed_at,mode:body.assessor?.mode,basis:body.basis,shared:true,historical:!!stale.length})}${sourceDetails([intent.ref,record.ref])}</div></details></section>`;
}
function businessAssessmentPanel(){
 const info=businessAssessmentInfo(),current=info?.current;if(!current)return businessAssessmentPublishedPanel();
 const b=current.body,stale=current.stale?.length,published=stale?businessAssessmentPublishedPanel():'';
 const panel=`<section class="business-assessment-panel" aria-label="Business assessment"><h3>${stale?'Earlier business assessment':'Business assessment'}</h3>${stale?'<p class="business-assessment-caution">Saved inputs or the assessment standard changed. This earlier judgment has not been applied to the current draft.</p>':''}${businessAssessmentOutputRead(b.output,{standard:b.standard,at:b.at,actor:b.actor,mode:b.mode,basis:b.basis,historical:!!stale})}${info.history?.length>1?`<details><summary>Earlier assessments (${info.history.length-1})</summary><div class="details-body">${info.history.slice(1).map(h=>`<p class="caption">Business Intent v${esc(h.basis?.revision)} · Historical confidence: ${esc(businessAssessmentLevel(h.confidence_level))}${h.at?' · '+businessAssessmentDateRead(h.at):''}</p>${sourceDetails(h.ref)}`).join('')}</div></details>`:''}</section>`;
 return published?published+`<details><summary>Private draft assessment · review needed</summary><div class="details-body">${panel}</div></details>`:panel;
}
function businessAssessmentReleasePreview(preview){
 if(!preview)return '';
 const output=preview.assessment||preview.output,manifest=preview.source_excerpt_manifest||[],citations=manifest.length?manifest.flatMap(source=>(source.passages||[]).map(p=>({...p,source_title:source.source_title}))):businessAssessmentCitations(output);
 return `<details class="business-assessment-release-preview"><summary>Assessment & selected excerpts to share</summary><div class="details-body">${businessAssessmentOutputRead(output,{standard:preview.standard,at:preview.assessed_at||preview.at,mode:preview.assessor?.mode||preview.mode,basis:preview.basis})}<section><h4>Selected evidence excerpts</h4>${citations.length?citations.map(businessAssessmentCitationRead).join(''):'<p>No document excerpts are included in this assessment.</p>'}</section><p class="caption">Only this assessment and the displayed excerpts are released. Full uploaded files and other private AI partner conversations remain private.</p></div></details>`;
}
function businessAssessmentReleaseChoice({preparing=false}={}){
 const info=businessAssessmentInfo(),current=info?.current;if(!current)return '';
 if(!info.current_is_fresh||current.stale?.length)return '<p class="caption">The earlier business assessment is excluded because its basis changed.</p>';
 return `<section class="business-assessment-release-choice"><label class="checkbox"><input type="checkbox" name="release_business_assessment"><span>${preparing?'Include this business assessment in the private preview. Sharing will require a separate confirmation.':'Include this business assessment and authorize sharing its selected evidence excerpts with project participants.'}</span></label>${businessAssessmentReleasePreview(current.body)}</section>`;
}
function businessAssessmentSelectedRelease(fd){
 const info=businessAssessmentInfo(),current=info?.current;
 if(fd.get('release_business_assessment')!=='on')return null;
 if(!current||!info.current_is_fresh||current.stale?.length)throw Error('The business assessment changed. Reopen the current assessment before sharing.');
 return current.ref;
}
function businessAssessmentSharedRead(anchor){
 if(!anchor?.ref)return '';
 const released=anchor.snapshot||(state.records||[]).find(x=>x.kind==='business-assessment-release'&&(!x.scope||String(x.scope).startsWith('project:'))&&x.ref.id===anchor.ref.id&&x.ref.revision===anchor.ref.revision)?.body;
 if(!released?.assessment)return '';
 return `<section class="card section business-assessment-shared" aria-label="Released Business assessment"><h2>Business assessment</h2>${businessAssessmentOutputRead(released.assessment,{standard:released.standard,at:released.assessed_at,mode:released.assessor?.mode,basis:released.basis,shared:true})}${sourceDetails(anchor.ref)}</section>`;
}
function businessRequirementBasis(r){
 const anchor=r.body?.business_assessment;if(!anchor?.ref)return null;
 const record=(state.records||[]).find(x=>x.kind==='business-assessment-release'&&(!x.scope||String(x.scope).startsWith('project:'))&&x.ref.id===anchor.ref.id&&x.ref.revision===anchor.ref.revision);
 if(!record)return null;
 const target=(record.body.requirement_targets||[]).find(x=>x.id===r.ref.id);
 if(!target)return null;
 const link=(record.body.assessment?.requirement_links||[]).find(x=>x.target===r.ref.id&&x.assessment_scope==='business-intake-basis');
 if(!link?.business_basis_confidence)return null;
 const stale=[];
 if(target.text!==r.body.text||target.acceptance_criteria!==r.body.acceptance_criteria)stale.push('Requirement wording or acceptance criteria changed after this business assessment.');
 const publicRows=(state.records||[]).filter(x=>!x.scope||String(x.scope).startsWith('project:'));
 for(const raw of record.body.sources||[]){const source=publicRows.find(x=>x.ref.id===raw.id);if(!source)stale.push('An exact released evidence source is unavailable in this view.');else if(source.ref.revision!==raw.revision)stale.push('Released evidence has a newer version; the earlier basis needs review.');}
 return {record,link,stale:[...new Set(stale)]};
}
function businessRequirementBasisSummary(r){
 const basis=businessRequirementBasis(r);if(!basis)return '';
 return basis.stale.length?'Earlier business basis · Review needed':`Initial business basis: ${businessAssessmentLevel(basis.link.business_basis_confidence.level)} · Definition: ${businessAssessmentText(basis.link.completeness?.status)||'Not recorded'}`;
}
function businessRequirementBasisRead(r){
 const basis=businessRequirementBasis(r);if(!basis)return '';
 const {record,link,stale}=basis,c=link.business_basis_confidence;
 return `<section class="business-requirement-basis"><h4>Initial business basis</h4><p>${esc(businessRequirementBasisSummary(r))}</p>${stale.length?`<p class="business-assessment-caution">${stale.map(esc).join(' ')}</p>`:''}<p class="caption">${stale.length?'Earlier business need and starting definition':'Business need and starting definition for this exact wording'}. Full requirement evidence and suitability for a use remain separate.</p><details><summary>Business basis reasoning & limits</summary><div class="details-body">${val('Connection to Business Intent',link.rationale)}${val('Definition reasoning',link.completeness?.rationale)}${link.completeness?.gaps?.length?`<ul>${link.completeness.gaps.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}${businessAssessmentConfidenceRead(c)}${val('Business basis limits',link.limits)}<p class="caption">${record.body.assessor?.mode==='simulated'?'Explicitly released scripted example':'Explicitly released model judgment'}${stale.length?' · Historical confidence: '+esc(businessAssessmentLevel(c.level)):''}${record.body.assessed_at?' · '+businessAssessmentDateRead(record.body.assessed_at):''}; not full requirement verification or fulfillment.</p>${sourceDetails([record.ref,record.body.standard?.ref].filter(Boolean))}</div></details></section>`;
}

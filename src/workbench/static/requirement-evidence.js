// Requirement evidence level (D004): a read-only tank over shared records. Never edits, approves or rates.
const requirementEvidenceLabels={empty:'Empty',low:'Low',moderate:'Moderate',high:'High'};
function requirementEvidence(id){return state.requirement_evidence?.[id]||null;}
function requirementEvidenceTank(level){const fill={empty:0,low:1,moderate:2,high:3}[level]??0;return `<span class="ac-tank ac-tank-${esc(level)}" aria-hidden="true">${[1,2,3].map(n=>`<span class="${n<=fill?'is-filled':''}"></span>`).join('')}</span>`;}
function requirementEvidenceChip(id){
 const e=requirementEvidence(id),level=e?.level||'empty';
 return `<span class="ac-evidence-chip" data-requirement-evidence="${esc(id)}">${requirementEvidenceTank(level)}<span>Coverage: ${esc(requirementEvidenceLabels[level])}</span></span>`;
}
function requirementEvidenceAge(days){if(days==null)return 'No dated evidence';if(days===0)return 'Today';if(days===1)return '1 day ago';return days+' days ago';}
// D012: three signals shown together and never merged: the recorded confidence rating, the computed
// evidence coverage, and which teams have contributions on the current version (D014 rev 2 names).
// Low confidence alone blocks nothing.
function requirementValidatedBy(id){
 const e=requirementEvidence(id),names=e?.current_teams||[],on=new Set(names.map(t=>String(t).toLowerCase()));
 const known=(state.domains?.profiles||state.domains?.domains||[]).map(d=>({key:String(d.key||'').toLowerCase(),label:d.config?.label||d.label||d.key})).filter(d=>d.label);
 const teams=known.map(d=>({label:d.label,done:on.has(d.key)||on.has(String(d.label).toLowerCase())}));
 for(const n of names)if(!teams.some(t=>String(t.label).toLowerCase()===String(n).toLowerCase()||t.done&&known.find(k=>k.label===t.label)?.key===String(n).toLowerCase()))teams.push({label:n,done:true});
 return teams;
}
function requirementSignals(id){
 const e=requirementEvidence(id),level=e?.level||'empty',r=typeof get==='function'?get(id):null;
 const a=r&&typeof requirementAssessmentCurrent==='function'?requirementAssessmentCurrent(r):null;
 const rated=a?.current?(a.confidence?.level||'not-rated'):'not-rated',stale=a?.status==='needs-reassessment',fresh=(a?.reassess||[]).length>0;
 const label=typeof confidenceLabel==='function'?confidenceLabel(rated):({'not-rated':'Not rated',low:'Low',moderate:'Moderate',high:'High'})[rated];
 const flag=stale?'Needs reassessment: its basis changed':fresh?'Needs reassessment: new shared evidence since this rating':'';
 const teams=requirementValidatedBy(id),raise=e?.raise_to;
 return `<div class="requirement-signals" data-requirement-signals="${esc(id)}"><h4>How sure are we</h4><dl>
 <div class="requirement-signal"><dt>Confidence rating</dt><dd><span class="signal-value lv-${esc(rated)}">${esc(label)}</span>${flag?`<span class="signal-flag">${esc(flag)}</span>`:''}</dd><p class="caption">A judgment by the requirement owner, for a named use.</p></div>
 <div class="requirement-signal"><dt>Evidence coverage</dt><dd>${requirementEvidenceChip(id)}</dd><p class="caption">Counted from shared work. Coverage, not quality.</p></div>
 <div class="requirement-signal"><dt>Contributions from</dt><dd>${teams.length?teams.map(t=>`<span class="signal-team ${t.done?'is-done':''}"><span aria-hidden="true">${t.done?'✓':'○'}</span> ${esc(t.label)}<span class="sr-only">${t.done?' has':' has not'} published work on the current version</span></span>`).join(''):'<span class="caption">No teams yet</span>'}</dd><p class="caption">Teams with published work on the current version. Publication is not validation.</p></div>
 </dl>${raise?.needs?.length?`<p class="requirement-raise"><strong>To raise coverage to ${esc(requirementEvidenceLabels[raise.to]||raise.to)}:</strong> ${esc(raise.needs.join('; '))}.</p>`:''}<p class="caption">These three are separate. None of them approves or blocks anything.</p></div>`;
}
function requirementEvidenceSection(id){
 const e=requirementEvidence(id),level=e?.level||'empty',n=(x,one,many)=>`${x} ${x===1?one:many}`;
 const facts=e?[
  ['Shared work referencing it',n(e.contributions,'contribution','contributions')+(e.teams.length?' · '+e.teams.join(', '):'')],
  ['On the current version',n(e.on_current,'contribution','contributions')+(e.current_teams.length?' · '+e.current_teams.join(', '):'')],
  ['Independent sources cited',String(e.independent_origins??0)],
  ['Newest evidence',requirementEvidenceAge(e.age_days)],
  ['Open contradictions',String(e.open_contradictions)],
  ['Open gaps',String(e.open_gaps)],
  ['Open dependencies',String(e.open_dependencies)],
  ['Issues worked through',String(e.resolved_issues)]
 ]:[];
 const reasons=e?.reasons?.length?e.reasons:['No shared work references this requirement yet.'];
 return `<section class="requirement-evidence" aria-label="How sure are we">${requirementSignals(id)}<header><h4>Evidence coverage</h4>${requirementEvidenceChip(id)}</header>
 <p class="caption">${reasons.map(esc).join(' ')}</p>
 ${facts.length?`<dl class="requirement-evidence-facts">${facts.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>`:''}
 <p class="caption requirement-evidence-how">Fill it by sharing work that references this requirement; challenge it in <a href="#main" class="item-title-link" data-nav="review">Decisions &amp; Issues</a>.</p><details class="page-about"><summary>How this is calculated</summary><p>From shared records only: references, teams, version, recency and open issues. It is not the recorded confidence and approves nothing.</p></details></section>`;
}

// D007: the case board, the opened area and the readiness view.
// Presentation only. Everything is calculated from existing records: requirement drawers,
// D004 evidence levels, goals, measures, issues, contributions and intent versions.
let caseOpenArea=null;
const CASE_LEVELS=['empty','low','moderate','high'];
const CASE_LEVEL_WORD={empty:'Empty',low:'Low',moderate:'Moderate',high:'High'};
// Display mapping agreed on the design canvas: which side's work mainly fills each area.
const CASE_SIDES={needs:'problem',measurement:'problem',experience:'solution',operations:'solution',technology:'solution',governance:'solution'};
const CASE_ORDER=['needs','measurement','experience','operations','technology','governance'];
const CASE_SHORT={needs:'Needs',measurement:'Outcomes',experience:'Experience',operations:'Operations',technology:'Technology',governance:'Policy'};
const CASE_ICONS={
 lock:'<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
 warn:'<path d="M12 3 2 21h20L12 3z"/><path d="M12 10v5M12 18v.5"/>',
 wait:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
 arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',back:'<path d="M19 12H5M11 6l-6 6 6 6"/>',
 check:'<path d="M5 12l5 5 9-10"/>',flag:'<path d="M5 21V4h11l-2 4 2 4H5"/>',
 bench:'<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
 table:'<circle cx="12" cy="12" r="8"/><path d="M12 4v16M4 12h16"/>'
};
function caseIcon(name,size=14,sw=2){return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${CASE_ICONS[name]}</svg>`;}
function caseGlyph(level){
 const fill={empty:'',low:'<path d="M8 8V1.5A6.5 6.5 0 0 1 14.5 8Z" fill="var(--lv)"/>',moderate:'<path d="M8 1.5A6.5 6.5 0 0 1 8 14.5Z" fill="var(--lv)"/>',high:'<circle cx="8" cy="8" r="6.5" fill="var(--lv)"/>'}[level]||'';
 return `<svg class="case-glyph lv-${level}" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><circle cx="8" cy="8" r="6.5" fill="none" stroke="var(--lv)" stroke-width="1.6"/>${fill}</svg>`;
}
function caseBar(level){const k=CASE_LEVELS.indexOf(level);return `<span class="case-bar lv-${level}" aria-hidden="true">${[0,1,2].map(i=>`<span class="${i<k?'on':''}"></span>`).join('')}</span>`;}
function caseLatest(kind){return typeof projectHomeLatest==='function'?projectHomeLatest(kind):[];}
function casePartLevel(e){return e?.level||'empty';}
// Next step for one part, taken from the D004 rules.
function casePartNext(e){
 if(!e||e.level==='empty')return 'Needs evidence';
 if(e.level==='low')return e.open_contradictions||e.open_gaps?'Resolve at the table':!e.on_current?'Needs work on this version':'Needs fresh evidence';
 if(e.level==='moderate')return (e.current_teams||[]).length<2?'2nd team → High':'More work on this version → High';
 return 'Holding';
}
// Areas are the published requirement drawers; parts are their included children.
function caseAreas(){
 const drawers=caseLatest('requirement-drawer').filter(r=>r.body?.status!=='withdrawn'),ev=state.requirement_evidence||{};
 return drawers.filter(r=>!String(r.ref.id).slice(4).includes('/')).map(r=>{
  const key=String(r.ref.id).slice(4);
  let parts=drawers.filter(c=>String(c.ref.id).startsWith(r.ref.id+'/')&&c.body?.included!==false).map(c=>{const path=String(c.ref.id).slice(4),e=ev['REQ-INTAKE-'+path]||null;return {id:c.ref.id,label:c.body.label||path,level:casePartLevel(e),evidence:e,requirement:'REQ-INTAKE-'+path};});
  if(!parts.length){const e=ev['REQ-INTAKE-'+key]||null;parts=[{id:r.ref.id,label:r.body.label||key,level:casePartLevel(e),evidence:e,requirement:'REQ-INTAKE-'+key}];}
  const levels=parts.map(p=>p.level),fed=levels.filter(l=>l!=='empty').length;
  // Area rule (D007): empty until any part has evidence; low if any part is low; high only when every part is high.
  const level=!fed?'empty':levels.includes('low')?'low':levels.every(l=>l==='high')?'high':'moderate';
  const lowPart=parts.find(p=>p.level==='low'),emptyN=parts.length-fed;
  const next=level==='high'?'Holding':lowPart?casePartNext(lowPart.evidence):emptyN?`${emptyN} part${emptyN===1?'':'s'} need${emptyN===1?'s':''} evidence`:casePartNext(parts.find(p=>p.level==='moderate')?.evidence);
  return {id:r.ref.id,key,label:r.body.label||key,short:CASE_SHORT[key]||r.body.label||key,side:CASE_SIDES[key]||'solution',parts,level,fed,next};
 }).sort((a,b)=>(CASE_ORDER.indexOf(a.key)+1||99)-(CASE_ORDER.indexOf(b.key)+1||99));
}
function casePublishedValues(){const c=(state.intake?.cases||[]).find(c=>c.body?.status==='published'&&c.body.snapshot);return c?.body.snapshot.values||{};}
function caseIssues(){const all=state.bridge?.issues||[],open=all.filter(i=>!['resolved','closed','withdrawn'].includes(i.body?.status));return {all,open};}
function caseOpenType(open,re){return open.filter(i=>re.test(String(i.body?.type||i.body?.kind||''))).length;}
function caseMilestones(areas){
 const contributions=caseLatest('contribution').filter(r=>r.body?.domain&&!String(r.ref.id).startsWith('CON-DEVBRIEF')&&!/draft|withdrawn/.test(String(r.body.status||'')));
 const research=contributions.find(r=>/research/i.test(r.body.domain)),intents=records('intent'),rev=intents.length?Math.max(...intents.map(r=>r.ref.revision)):0,refined=caseLatest('intent-refinement').length;
 const {all}=caseIssues(),settled=all.find(i=>/depend/i.test(String(i.body?.type||i.body?.kind||''))&&['resolved','closed'].includes(i.body?.status));
 const ev=Object.values(state.requirement_evidence||{}),shared=ev.find(e=>(e.teams||[]).length>=2);
 const measures=caseLatest('success-measure'),targets=measures.filter(m=>String(m.body?.target||'').trim()).length,fed=areas.filter(a=>a.level!=='empty').length;
 const who=id=>state.actors?.[id]?.name||id||'';
 return [
  {title:'First evidence',by:research?research.body.domain:'Problem side',earned:!!research},
  {title:'Intent revised',by:rev>1?'v'+rev:'From evidence',earned:rev>1&&refined>0},
  {title:'Dependency settled',by:settled?(who(settled.body?.owner)||'At the table'):'At the table',earned:!!settled},
  {title:'Two teams, one need',by:shared?(caseAreas().find(a=>a.parts.some(p=>p.requirement===shared.requirement?.id))?.short||'Shared'):'Any requirement',earned:!!shared},
  {title:'All areas fed',by:`${fed}/${areas.length}`,earned:areas.length>0&&fed===areas.length},
  {title:'All targets set',by:`${targets}/${measures.length}`,earned:measures.length>0&&targets===measures.length}
 ];
}
function caseKey(){
 return `<p class="case-key"><span class="case-label">Key</span>${CASE_LEVELS.map(l=>`<span>${caseGlyph(l)}${CASE_LEVEL_WORD[l]}</span>`).join('')}<span>${caseIcon('lock',13)}Needs a target</span><span>${caseIcon('warn',13)}Open conflict</span><span>${caseIcon('arrow',13)}Opens detail</span></p>`;
}
function caseRow(a,cls='case-row',action='case-area'){
 return `<li><button type="button" class="${cls} lv-${a.level}" data-action="${action}" data-id="${esc(a.id)}" aria-label="${esc(a.label)}: ${CASE_LEVEL_WORD[a.level]}. ${esc(a.next)}">${caseGlyph(a.level)}<span class="case-row-text"><span class="case-row-name">${esc(a.label)}</span><span class="case-row-next">${esc(a.next)}</span></span>${caseBar(a.level)}<span class="case-row-level">${CASE_LEVEL_WORD[a.level]}</span><span class="case-row-go">${caseIcon('arrow',14)}</span></button></li>`;
}
function caseSide(side,areas,values){
 const mine=areas.filter(a=>a.side===side),filled=mine.filter(a=>a.level!=='empty').length;
 const conf=side==='problem'?{n:'04',title:'The problem',team:'Research',q:values.research_question}:{n:'05',title:'The solution',team:'Design',q:values.operations_question};
 const domain=(typeof domainKnowledgeInfo==='function'?domainKnowledgeInfo().domains||[]:[]).find(d=>new RegExp(conf.team,'i').test(d.label||d.key));
 const open=domain?`<a href="#main" data-action="nav-domain" data-id="${esc(domain.key)}|contributions">${caseIcon('bench',13)}Open workbench</a>`:'';
 return `<section class="case-panel" id="case-${side}" aria-labelledby="case-${side}-title"><div class="case-side-head"><span class="case-num">${conf.n}</span><h2 id="case-${side}-title">${conf.title}</h2><span class="case-team case-team-${conf.team.toLowerCase()}">${conf.team}</span><span class="case-filled">${filled}/${mine.length} filled</span></div>
 ${String(conf.q||'').trim()?`<div class="case-quest">${caseIcon('flag',14)}<p>${esc(String(conf.q).trim())}</p>${open}</div>`:open?`<div class="case-quest">${caseIcon('flag',14)}<p class="caption">No validation question set yet.</p>${open}</div>`:''}
 <ul class="case-rows">${mine.map(a=>caseRow(a)).join('')}</ul></section>`;
}
function caseRail(areas,ms,measures,targets){
 const side=s=>{const m=areas.filter(a=>a.side===s);return `${m.filter(a=>a.level!=='empty').length}/${m.length}`;};
 const earned=ms.filter(m=>m.earned).length,fed=areas.filter(a=>a.level!=='empty').length;
 const items=[['01','Mission','case-mission',caseIcon('check',12,2.6),'is-done'],['02','Proof','case-proof',(targets<measures?caseIcon('lock',12):'')+`${targets}/${measures}`,targets<measures?'is-gold':'is-done'],['03','Strength','case-strength',`${fed}/${areas.length}`,''],['04','Problem','case-problem',side('problem'),''],['05','Solution','case-solution',side('solution'),''],['06','Milestones','case-milestones',`${earned}/${ms.length}`,'is-gold']];
 return `<nav class="case-rail" aria-label="On this page">${items.map(([n,l,h,c,cls])=>`<a href="#${h}" data-case-jump="${h}"><span class="case-num">${n}</span><span class="case-rail-label">${l}</span><span class="case-rail-count ${cls}">${c}</span></a>`).join('')}</nav>`;
}
// Who the latest intent revision came from: the source work's owner, else who requested the change.
function caseIntentCredit(rev){
 if(rev<2)return '';const ref=caseLatest('intent-refinement').sort((a,b)=>b.ref.revision-a.ref.revision)[0];if(!ref)return '';
 const src=ref.body?.source?.id&&typeof get==='function'?get(ref.body.source.id):null,id=src?.body?.owner||ref.body?.requested_by;
 const n=state.actors?.[id]?.name;return n?`from ${n.split(' ')[0]}’s finding`:'';
}
function caseHandoff(){
 const approved=(state.cases||[]).filter(c=>c.kind==='decision-case'&&c.body?.status==='approved').length,d=state.demo_delivery||{},staged=(d.previews||[]).length;
 return `<p class="case-handoff"><span class="case-label">Handoff</span><span><b>${approved}</b> requirement${approved===1?'':'s'} approved</span><span><b>${staged}</b> item${staged===1?'':'s'} staged for Jira and Azure DevOps${staged&&d.mode==='simulated'?' · simulated, nothing sent':''}</span><a href="#main" ${projectHomeNav('delivery')}>Open handoff ${caseIcon('arrow',12)}</a></p>`;
}
function caseBoard(){
 const areas=caseAreas(),values=casePublishedValues(),goal=caseLatest('goal')[0],measures=caseLatest('success-measure');
 const mission=String(values.value||goal?.body?.basis_values?.value||'').trim();
 const intents=records('intent'),rev=intents.length?Math.max(...intents.map(r=>r.ref.revision)):0;
 const sponsor=state.actors?.[(state.intake?.cases||[])[0]?.body?.requested_by||'priya']?.name||'';
 const targets=measures.filter(m=>String(m.body?.target||'').trim()).length,ms=caseMilestones(areas),earned=ms.filter(m=>m.earned).length;
 const {open}=caseIssues(),conflicts=caseOpenType(open,/contradict|conflict|challenge/i),waiting=(state.cases||[]).filter(c=>c.kind==='decision-case'&&!['approved','rejected','withdrawn','closed'].includes(c.body?.status)).length+open.length;
 const fed=areas.filter(a=>a.level!=='empty').length;
 return `${caseRail(areas,ms,measures.length,targets)}<div class="case-grid">
 <div class="case-top">
  <section class="case-panel" id="case-mission" aria-labelledby="case-mission-label"><p class="case-label is-accent" id="case-mission-label"><span>01 · Mission</span></p>${mission?`<p class="case-mission">${esc(mission)}</p>`:'<p class="caption">The sponsor has not published the promise yet.</p>'}<p class="case-meta">${esc(sponsor)}${rev?` · Intent v${rev}`:''}${caseIntentCredit(rev)?' '+esc(caseIntentCredit(rev)):''} · <a href="#main" ${projectHomeNav('intent')}>Brief</a> · <a href="#main" ${projectHomeNav('context')}>Context</a></p></section>
  <section class="case-panel" id="case-proof" aria-labelledby="case-proof-label"><p class="case-label is-gold" id="case-proof-label"><span>02 · Win conditions</span><span class="case-label-meta">${targets<measures.length?caseIcon('lock',12):caseIcon('check',12,2.6)}${targets}/${measures.length} set</span></p>
   ${goal?`<p class="case-meta"><strong>${esc(goal.body.title||'')}</strong></p>`:''}
   ${measures.length?measures.map(m=>{const t=String(m.body?.target||'').trim();return `<div class="case-measure"><span>${esc(m.body?.name||m.body?.text||m.ref.id)}</span><span class="case-measure-target ${t?'is-set':''}">${t?caseIcon('check',12,2.6)+esc((m.body.baseline?m.body.baseline+' → ':'')+t):caseIcon('lock',12)+'Target'}</span></div>`;}).join(''):'<p class="caption">No measures published yet.</p>'}</section>
 </div>
 <section class="case-panel case-strength" id="case-strength" aria-labelledby="case-strength-label">
  <div class="case-strength-head"><span class="case-label" id="case-strength-label">03 · Case strength</span><span class="case-score">${fed}<small>/${areas.length}</small></span></div>
  <div class="case-cta-wrap"><button type="button" class="case-cta" data-action="case-ready">${caseReadinessInfo().can_decide?'Ready to build?':'See readiness'} ${caseIcon('arrow',14)}</button>${caseCallLine(caseReadinessInfo())}</div>
  <div class="case-strip">${areas.map(a=>`<button type="button" class="case-strip-cell lv-${a.level}" data-action="case-area" data-id="${esc(a.id)}" aria-label="${esc(a.label)}: ${CASE_LEVEL_WORD[a.level]}"><span class="case-strip-bar ${a.level!=='empty'?'on':''}"></span><span class="case-strip-name">${caseGlyph(a.level)}${esc(a.short)}</span></button>`).join('')}</div>
  <p class="case-counters"><span class="${conflicts?'is-low':''}">${caseIcon('warn',13)}<b>${conflicts}</b> conflict${conflicts===1?'':'s'}</span><span class="${targets<measures.length?'is-gold':''}">${caseIcon('lock',13)}<b>${measures.length-targets}</b> target${measures.length-targets===1?'':'s'} to set</span><span>${caseIcon('wait',13)}<b>${waiting}</b> at the table</span></p>
  ${caseHandoff()}
 </section>
 <div class="case-sides">${caseSide('problem',areas,values)}${caseSide('solution',areas,values)}</div>
 <section class="case-panel" id="case-milestones" aria-labelledby="case-ms-label"><p class="case-label is-gold" id="case-ms-label"><span>06 · Milestones · ${earned}/${ms.length}</span><span class="case-label-meta">Disproving counts too</span></p>
  <div class="case-milestones done-${Math.max(0,ms.filter((m,i)=>m.earned&&ms.slice(0,i).every(x=>x.earned)).length-1)}"><ol>${ms.map(m=>`<li><span class="case-ms-dot ${m.earned?'is-earned':''}">${caseIcon(m.earned?'check':'lock',m.earned?14:12,m.earned?2.6:2)}</span><span class="case-ms-title ${m.earned?'':'is-locked'}">${esc(m.title)}<span class="sr-only">${m.earned?' · earned':' · not yet'}</span></span><span class="case-ms-by">${esc(m.by)}</span></li>`).join('')}</ol></div></section>
 ${caseKey()}</div>`;
}
function caseAreaScreen(){
 const a=caseAreas().find(x=>x.id===caseOpenArea);if(!a){caseOpenArea=null;return projectHome();}
 const ev=a.parts.map(p=>p.evidence).filter(Boolean),teams=[...new Set(ev.flatMap(e=>e.current_teams||e.teams||[]))],contribs=ev.reduce((n,e)=>n+(e.contributions||0),0),open=ev.reduce((n,e)=>n+(e.open_contradictions||0)+(e.open_gaps||0),0);
 const parts=a.parts.map(p=>({...p,next:casePartNext(p.evidence)+(p.evidence?.contributions?` · ${p.evidence.contributions} shared`:'')}));
 return `<p><button type="button" class="case-back" data-action="case-back">${caseIcon('back',14)}The case</button></p>
 <div class="case-grid"><section class="case-panel lv-${a.level}"><p class="case-label"><span>${a.side==='problem'?'04 · The problem':'05 · The solution'}</span></p>
  <div class="case-area-head">${caseGlyph(a.level)}<h1 tabindex="-1">${esc(a.label)}</h1><span class="case-area-level">${caseBar(a.level)}<span class="case-row-level case-level-word">${CASE_LEVEL_WORD[a.level]}</span></span></div>
  <dl class="case-facts"><div><dt>Parts fed</dt><dd>${a.fed}/${a.parts.length}</dd></div><div><dt>Shared work</dt><dd>${contribs}</dd></div><div><dt>Teams now</dt><dd>${teams.length?esc(teams.join(', ')):'0'}</dd></div><div><dt>Open conflicts</dt><dd>${open}</dd></div></dl>
  <p class="case-meta">Next: ${esc(a.next)}</p></section>
 <section class="case-panel" aria-labelledby="case-parts-title"><p class="case-label" id="case-parts-title"><span>Parts</span><span class="case-label-meta">Open a part for its evidence, versions and decisions</span></p>
  <ul class="case-rows">${parts.map(p=>caseRow(p,'case-row case-part','open-drawer')).join('')}</ul></section>
 <p class="case-meta"><a href="#main" data-nav="review">${caseIcon('table',13)} Raise something at the table</a></p>
 ${caseKey()}</div>`;
}
function caseReadinessInfo(){return state.readiness||{history:[],outcomes:{},can_decide:false};}
function caseCallLine(r){const c=r.current;if(!c)return '';const who=state.actors?.[c.actor]?.name||c.actor;const lv=c.outcome==='ready'?'high':c.outcome==='not-yet'?'low':'moderate';
 return `<span class="case-call lv-${lv}">${caseGlyph(lv)}<b>${esc(c.label)}</b><span>${esc(who)} · ${esc(typeof projectHomeDate==='function'?projectHomeDate(c.at):'')}</span>${r.basis_changed?`<span class="case-call-changed">${caseIcon('warn',12)}Basis changed since</span>`:''}</span>`;}
function caseReadiness(){
 const areas=caseAreas(),measures=caseLatest('success-measure'),targets=measures.filter(m=>String(m.body?.target||'').trim()).length,{open}=caseIssues();
 const conflicts=caseOpenType(open,/contradict|conflict|challenge/i),values=casePublishedValues(),r=caseReadinessInfo();
 const checks=[
  ['Every area has evidence',areas.filter(a=>a.level!=='empty').length,areas.length],
  ['No area is low',areas.filter(a=>a.level!=='low').length,areas.length],
  ['Every measure has a target',targets,measures.length],
  ['No open conflicts',conflicts?0:1,1],
  ['Nothing waiting at the table',open.length?0:1,1],
  ['Both validation questions set',[values.research_question,values.operations_question].filter(v=>String(v||'').trim()).length,2]
 ];
 const met=checks.filter(c=>c[1]>=c[2]).length,who=id=>state.actors?.[id]?.name||id;
 const list=`<ul class="case-checks">${checks.map(([t,n,d])=>{const ok=n>=d;return `<li class="case-check ${ok?'is-met lv-high':'is-open lv-low'}">${caseGlyph(ok?'high':'empty')}<span>${esc(t)}</span><b>${d>1?`${n}/${d}`:ok?'Met':'Open'}</b></li>`;}).join('')}</ul>`;
 const current=r.current?`<section class="case-call-panel"><p class="case-label"><span>Current call</span>${r.history.length>1?`<span class="case-label-meta">${r.history.length} calls kept</span>`:''}</p>${caseCallLine(r)}<p class="case-call-reason">${esc(r.current.reason)}</p>${r.current.conditions?`<p class="case-call-reason"><strong>Conditions:</strong> ${esc(r.current.conditions)}</p>`:''}${r.basis_changed?'<p class="case-meta">The board has changed since this call. It stands until it is reconsidered.</p>':''}${r.history.length>1?`<details class="case-call-history"><summary>Earlier calls</summary><ol>${r.history.slice(1).map(h=>`<li><b>${esc(h.label)}</b> · ${esc(who(h.actor))} · ${esc(projectHomeDate(h.at))}<br><span>${esc(h.reason)}</span></li>`).join('')}</ol></details>`:''}</section>`:'';
 const deciders=(r.deciders||[]).map(who).join(' or ');
 const form=r.can_decide?`<fieldset class="case-outcomes"><legend>${r.current?'Record a new call':'Your call'}</legend>${Object.entries(r.outcomes).map(([k,l],i)=>`<label><input type="radio" name="outcome" value="${esc(k)}" ${i===2&&!r.current||r.current?.outcome===k?'checked':''} required><span>${esc(l)}</span></label>`).join('')}</fieldset>
 <label class="form-field"><span>Why</span><textarea name="reason" maxlength="2000" required rows="3"></textarea></label>
 <label class="form-field case-conditions"><span>Conditions (for Ready with conditions)</span><textarea name="conditions" maxlength="2000" rows="2"></textarea></label>
 <label class="checkbox"><input type="checkbox" name="confirm" required>I am making this call. The board's current state is kept with it.</label>`:`<p class="case-meta">${esc(deciders||'The Business direction decider')} makes this call. ${r.current?'':'No call recorded yet.'} <a href="#main" data-action="case-table">Raise it at the table</a></p>`;
 const body=`<p class="case-meta">${met} of ${checks.length} checks met. The board informs the call; people make it.</p>${list}${current}${form}`;
 modal('Ready to build?',body,r.can_decide?'Record the call':null,r.can_decide?async fd=>command('readiness-decide',{outcome:fd.get('outcome'),reason:fd.get('reason')||'',conditions:fd.get('conditions')||'',confirm:fd.get('confirm')==='on',expected:r.ref||null}):null,r.can_decide?{}:{footer:false});
}
async function caseAction(action,id){
 if(action==='theme-toggle'){acToggleTheme();return true;}
 if(action==='case-area'){caseOpenArea=id;render();window.scrollTo(0,0);$('#main h1')?.focus();return true;}
 if(action==='case-back'){caseOpenArea=null;render();return true;}
 if(action==='case-ready'){caseReadiness();return true;}
 if(action==='case-table'){closeModal();await navigateWorkspace('review');return true;}
 return false;
}
document.addEventListener('click',e=>{const a=e.target.closest('[data-case-jump]');if(!a)return;e.preventDefault();const t=document.getElementById(a.dataset.caseJump);if(t){t.scrollIntoView({behavior:'smooth',block:'start'});t.setAttribute('tabindex','-1');t.focus({preventScroll:true});}});

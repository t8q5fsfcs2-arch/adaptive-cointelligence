// Project focus band: the goal, what matters now and one next move, on each person's main screens.
// Presentation only. Every line is read from state the product already keeps; nothing here
// saves, approves, publishes or calls a model. It changes with Business Intent status and the
// project's plan stage (Intent, Investigate, Align, Deliver).
const APERTURE_VIEWS=['home','intent','contributions','requirements','review','delivery'];
const APERTURE_STAGES=[['intent','Intent'],['investigate','Investigate'],['align','Align'],['deliver','Deliver']];
const APERTURE_CLOSED=['resolved','closed','withdrawn','approved','rejected','published','incorporated','cancelled'];

function apertureLatest(kind){return typeof projectHomeLatest==='function'?projectHomeLatest(kind):[];}
function apertureName(actor){return state.actors?.[actor]?.name||'a team';}
function apertureRole(){const a=state.actor;return a==='priya'?'sponsor':a==='alex'?'owner':state.domains?.active?'domain':null;}
function apertureOpen(rows){return (rows||[]).filter(r=>!APERTURE_CLOSED.includes(r.body?.status));}

// Business Intent status: draft, in review, change requested, published or revised.
function apertureIntent(){
 const intents=apertureLatest('intent'),revision=intents.length?Math.max(...intents.map(r=>r.ref.revision)):0;
 const refinements=state.intake?.refinements||[],requested=refinements.filter(r=>['open','drafted','deferred'].includes(r.body?.status));
 const reviewing=apertureOpen(state.intake?.cases).filter(c=>c.kind!=='intent-refinement');
 const published=Boolean(revision||state.intake?.published);
 const incorporated=refinements.filter(r=>r.body?.status==='incorporated').sort((a,b)=>b.ref.revision-a.ref.revision)[0];
 let status=!published?(reviewing.length?'in-review':'draft'):requested.length?'change-requested':revision>1?'revised':'published';
 const label={draft:'Business Intent not published',['in-review']:'Business Intent in review',['change-requested']:`Intent v${revision} · change requested`,revised:`Intent v${revision} · revised`,published:`Intent v${revision} · published`}[status];
 const detail=status==='change-requested'?`${apertureName(requested[0].body.requested_by)} asked to change it, citing a published finding.`:status==='revised'&&incorporated?`Changed from ${apertureName(incorporated.body.requested_by)}’s finding. Earlier versions are kept.`:status==='in-review'?'Reviewers are checking the draft before it is published.':status==='draft'?(state.actor==='priya'?'Your draft is private. Teams cannot work from it yet.':'Teams start once the sponsor publishes it.'):'';
 return {status,revision,label,detail,requested,reviewing};
}

// Plan stage: where the project's work stands across all teams.
function apertureStage(intent=apertureIntent()){
 if(!intent.revision&&!state.intake?.published)return 'intent';
 const issues=apertureOpen(state.bridge?.issues),cases=apertureOpen((state.cases||[]).filter(c=>c.kind==='decision-case'));
 if(issues.length||cases.length||intent.requested.length)return 'align';
 const approved=(state.cases||[]).some(c=>c.kind==='decision-case'&&c.body?.status==='approved')||records('requirement').some(r=>r.body?.status==='approved');
 return approved?'deliver':'investigate';
}

function apertureGoal(){
 const goals=apertureLatest('goal').filter(g=>g.body?.active!==false&&g.body?.status!=='withdrawn');
 const measures=apertureLatest('success-measure').filter(m=>m.body?.active!==false).map(m=>m.body.name||m.body.text).filter(Boolean);
 const g=goals[0]?.body;
 return {title:g?.title||g?.text||'',outcome:g&&g.outcome&&g.outcome!==g.title?g.outcome:'',more:Math.max(0,goals.length-1),measures};
}

function apertureLevel(level){return {empty:'no shared evidence yet',low:'low evidence',moderate:'moderate evidence',high:'high evidence'}[level]||level;}
function apertureCanNav(target){return typeof workspaceNavigation==='function'&&Boolean(workspaceNavigation()[target]);}

// What matters now: at most three lines, for this person, at this stage.
function apertureMatters(role,stage,intent){
 const out=[],add=(text,tone='',attrs='')=>{if(text&&out.length<3)out.push({text,tone,attrs});};
 const issues=apertureOpen(state.bridge?.issues),contributions=apertureLatest('contribution').filter(r=>r.body?.domain&&!String(r.ref.id).startsWith('CON-DEVBRIEF'));
 const teams=new Set(contributions.map(r=>r.body.domain));
 if(role==='sponsor'){
  if(stage==='intent')add(intent.status==='in-review'?'Your draft is with reviewers. Publish once they respond.':'Nobody can work from your intent until you publish it.','warn');
  if(intent.requested.length)add(`${intent.requested.length} change request${intent.requested.length===1?'':'s'} to your intent, each backed by a published finding.`,'warn','data-action="intent-learning"');
  if(stage!=='intent')add(teams.size?`${teams.size} team${teams.size===1?'':'s'} shared ${contributions.length} piece${contributions.length===1?'':'s'} of work against Intent v${intent.revision}.`:`No team has shared work against Intent v${intent.revision} yet.`);
  if(issues.length)add(`${issues.length} open issue${issues.length===1?'':'s'} between teams.`,'warn','data-nav="review"');
 }
 if(role==='domain'){
  if(stage==='intent')add('Business Intent is not published yet. You can prepare, but nothing can be shared against it.','warn');
  if(view==='contributions'&&typeof cockpitChanged==='function'&&cockpitChanged())add('Your inputs changed since you started. Check this work still fits the current intent.','warn','data-action="dchat-guidance-context"');
  const area=typeof cockpitAreas==='function'?cockpitAreas()[0]:null;
  if(area)add(`${area.label}: ${apertureLevel(area.level)} · ${area.next}`,area.level==='empty'||area.level==='low'?'warn':'',view==='contributions'?`data-action="cockpit-area" data-id="${esc(area.id)}"`:'');
  const quest=typeof cockpitQuest==='function'?cockpitQuest():'';
  if(quest)add(`Your team is validating: ${quest}`);
  const plan=view==='contributions'&&typeof workingDomainPlanStatus==='function'?workingDomainPlanStatus():'';
  if(plan&&plan!=='Ready to guide work')add(`Working plan: ${plan}`);
 }
 if(role==='owner'){
  const mine=apertureOpen((state.cases||[]).filter(c=>c.kind==='decision-case')).filter(c=>c.body?.decision_owner===state.actor);
  if(mine.length)add(`${mine.length} requirement decision${mine.length===1?'':'s'} waiting for you.`,'warn');
  const reqs=records('requirement').filter(r=>!r.scope||r.scope.startsWith('project:')),ratified=reqs.filter(r=>r.body?.status==='approved').length;
  if(stage!=='intent')add(reqs.length?`${ratified} of ${reqs.length} requirement${reqs.length===1?'':'s'} ratified.`:'No requirements proposed yet.');
  if(intent.requested.length)add('Requirement approval waits while the intent change request is open.','warn');
  const weak=typeof caseAreas==='function'?caseAreas().filter(a=>a.level==='empty'||a.level==='low')[0]:null;
  if(weak)add(`Weakest area: ${weak.label} · ${weak.next}`);
  if(stage==='intent')add('Requirements start from the published Business Intent.');
 }
 if(stage!=='intent'&&issues.length&&role!=='sponsor')add(`${issues.length} open issue${issues.length===1?'':'s'} between teams.`,'warn','data-nav="review"');
 return out;
}

// One next move. Waiting items come first; otherwise the step that fits this role and stage.
function apertureNext(role,stage,intent){
 const needs=typeof projectHomeNeeds==='function'?projectHomeNeeds():[];
 if(needs.length)return {title:`${needs[0].label}: ${needs[0].title}`,why:needs[0].detail||'Waiting on you.',attrs:needs[0].attrs};
 const nav=(target,title,why)=>apertureCanNav(target)&&view!==target?{title,why,attrs:`data-nav="${target}"`}:null;
 if(role==='sponsor'){
  if(stage==='intent')return view==='intent'?{title:'Finish and publish Business Intent',why:'Teams start from the published version.',attrs:''}:nav('intent','Finish and publish Business Intent','Teams start from the published version.');
  if(intent.requested.length)return {title:'Review the change request',why:'A published finding challenges the current intent.',attrs:'data-action="intent-learning"'};
  if(stage==='align')return nav('review','Open Decisions & Issues','Teams need a decision before work continues.');
  if(stage==='deliver')return nav('delivery','Review the handoff','Approved requirements are ready to hand over.')||nav('home','See what changed','Follow the latest shared work.');
  return nav('home','See what teams shared','Follow findings against the current intent.');
 }
 if(role==='domain'){
  if(view==='contributions'){
   const guide=typeof chatTaskGuidance==='function'&&typeof chatWork==='function'&&chatWork()?chatTaskGuidance().next:null;
   if(guide)return {title:guide.title,why:guide.why||'',attrs:`data-action="${esc(guide.action)}" data-id="${esc(guide.id||'')}"`};
   if(typeof workingDomainPlanStatus==='function'&&workingDomainPlanStatus()==='Set up the plan')return {title:'Set up your working plan',why:'Decide what your team will investigate first.',attrs:'data-action="pflow-brief"'};
   return null;
  }
  return nav('contributions','Open your workbench',stage==='intent'?'Prepare your plan while the intent is drafted.':'Continue your work against the current intent.');
 }
 if(role==='owner'){
  if(stage==='intent')return null;
  if(records('requirement').some(r=>r.body?.status!=='approved'))return nav('requirements','Review proposed requirements','Ratify what the evidence supports.');
  if(stage==='align')return nav('review','Open Decisions & Issues','Open items may affect requirements.');
  return nav('requirements','Check requirement coverage','Find where evidence is still thin.');
 }
 return null;
}

function apertureStepper(stage){
 const at=APERTURE_STAGES.findIndex(([k])=>k===stage);
 return `<ol class="aperture-stages" aria-label="Plan stage">${APERTURE_STAGES.map(([k,label],i)=>`<li class="${i<at?'is-done':i===at?'is-current':''}"${i===at?' aria-current="step"':''}>${esc(label)}</li>`).join('')}</ol>`;
}

function apertureBand(){
 if(!state||!APERTURE_VIEWS.includes(view)||selected||(typeof caseOpenArea!=='undefined'&&caseOpenArea))return '';
 if(view==='review'&&typeof bridgeSection!=='undefined'&&bridgeSection!=='overview')return '';
 const role=apertureRole();if(!role)return '';
 const intent=apertureIntent(),stage=apertureStage(intent),goal=apertureGoal(),matters=apertureMatters(role,stage,intent),next=apertureNext(role,stage,intent);
 const stageWord=APERTURE_STAGES.find(([k])=>k===stage)[1];
 const goalText=goal.title?`<p class="aperture-goal">${esc(goal.title)}</p>${goal.outcome?`<p class="aperture-outcome">${esc(goal.outcome)}</p>`:''}${goal.measures.length?`<p class="aperture-measures">Measured by ${esc(goal.measures.join(' · '))}</p>`:''}${goal.more?`<p class="aperture-measures">+${goal.more} more goal${goal.more===1?'':'s'}</p>`:''}`:`<p class="aperture-goal is-missing">${role==='sponsor'?'Set the goal in Business Intent':'No goal published yet'}</p>`;
 const mattersList=matters.length?`<ul class="aperture-matters">${matters.map(m=>`<li class="${m.tone?'is-'+m.tone:''}">${m.attrs?`<a href="#main" ${m.attrs}>${esc(m.text)}</a>`:esc(m.text)}</li>`).join('')}</ul>`:'<p class="aperture-calm">Nothing needs your attention at this stage.</p>';
 const nextBlock=next?`${next.attrs?`<button type="button" class="aperture-next-button" ${next.attrs}>${esc(next.title)}</button>`:`<p class="aperture-next-title">${esc(next.title)}</p>`}${next.why?`<p class="aperture-why">${esc(next.why)}</p>`:''}`:'<p class="aperture-next-title">You are up to date</p><p class="aperture-why">Nothing is waiting on you.</p>';
 return `<section class="aperture" aria-label="Project focus" data-stage="${stage}" data-intent="${intent.status}">
 <div class="aperture-cell aperture-goal-cell"><h2 class="aperture-label">Our goal</h2>${goalText}<p class="aperture-status"><span class="aperture-intent is-${intent.status}">${esc(intent.label)}</span>${intent.detail?` <span class="aperture-intent-detail">${esc(intent.detail)}</span>`:''}</p>${apertureStepper(stage)}</div>
 <div class="aperture-cell aperture-matters-cell"><h2 class="aperture-label">What matters now <span class="aperture-stage-word">· ${esc(stageWord)}</span></h2>${mattersList}</div>
 <div class="aperture-cell aperture-next-cell"><h2 class="aperture-label">Your next move</h2>${nextBlock}</div>
</section>`;
}

const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
test('meaning disposition shows the material alternative and clarification without inventing a human answer',()=>{
 const h=harness();h.ctx.part={interpretation:{state:'conditional',reading:'Active state',basis:'Two readings remain.',alternatives:[{reading:'History only',consequence:'Does not prove active state.'}],clarification:{question:'Which <scope>?',owner_role:'Requirement owner',dependent_action:'Accept behavior',release_condition:'Record scope and reassess evidence.'}}};
 const html=h.run('bridgeIntegrityMeaning(part)');
 for(const text of ['conditional','History only','Does not prove active state','Requirement owner','Accept behavior','Record scope','No human answer'])assert.ok(html.includes(text));
 assert.ok(html.includes('&lt;scope>'));assert.ok(!html.includes('<scope>'));
 assert.match(h.run('bridgeIntegrityMeaning({})'),/earlier review did not record/);
});
test('current review UI stops superseded selection before proposal or assessment',async()=>{
 const h=harness(),i=issue(h),calls=[];
 h.ctx.command=async(a,data)=>{calls.push({a,data});return {purpose:'current',boundary:'Bounded current review.',current_use_eligible:false,superseded:[{selected:{id:'POL',revision:1},current:{id:'POL',revision:2}}]};};
 await h.ctx.bridgeIntegrityAction('bridge-integrity-assess',i);
 const dialog=h.dialogs.at(-1);assert.match(dialog[1],/Historical comparison/);assert.match(dialog[1],/POL:v1/);
 const fd=new Map([['review_purpose','current'],['semantic','on']]);
 await assert.rejects(dialog[3](fd),/not current/);
 assert.deepEqual(calls.map(c=>c.a),['integrity-preflight','integrity-preflight']);
});
test('historical UI records exact purpose and opens the saved review without attaching it',async()=>{
 const h=harness(),i=issue(h),calls=[];
 h.ctx.command=async(a,data)=>{calls.push({a,data});if(a==='integrity-preflight')return {purpose:'current',boundary:'Selected evidence.',superseded:[]};if(a==='integrity-assess')return {ref:{id:'HISTORY',revision:1}};return {ref:{id:'HISTORY',revision:1},context:{},summary:'Historical review'};};
 await h.ctx.bridgeIntegrityAction('bridge-integrity-assess',i);
 const result=await h.dialogs.at(-1)[3](new Map([['review_purpose','historical'],['historical_reason','Retain the original comparison basis.'],['semantic','on']]));
 const request=calls.find(c=>c.a==='integrity-assess').data;
 assert.equal(request.review_purpose,'historical');assert.equal(request.mode,'advisory');assert.equal(request.confirm,false);
 assert.equal(request.historical_reason,'Retain the original comparison basis.');assert.equal(request.packets,i.body.packet_refs);
 assert.ok(result.integrityReview);assert.ok(!calls.some(c=>['integrity-proposal','integrity-attach'].includes(c.a)));
});
function harness(){
 const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),nodes=new Map(),calls=[],dialogs=[];
 const ctx={state:{actor:'alex',actors:{priya:{name:'Priya',role:'Business sponsor'},sam:{name:'Sam',role:'Research'},lee:{name:'Lee',role:'Design'},alex:{name:'Alex',role:'Requirement owner'}},bridge:{boards:{'business-research':'Sponsor · Research','business-design':'Sponsor · Design','research-design':'Research · Design'},kinds:{conflict:'Conflict',question:'Information need'},actors:['alex','lee','priya','sam'],issues:[],outcomes:[]},packets:[],cases:[],intake:{refinements:[],baseline_values:{value:'Current value'},draft:{ref:{id:'INTAKE',revision:1}}},records:[]},
 selected:null,view:'review',intakeStep:'rationale',intakeCaseId:null,esc,label:r=>r.id+':v'+r.revision,packetKey:p=>p.id+'|'+p.revision,packetTitle:p=>p.purpose,
 ref:r=>esc(r.id+':v'+r.revision),head:(t,s,a='')=>`<h1>${esc(t)}</h1>${esc(s)}${a}`,tag:(t)=>esc(t),statusTag:s=>esc(s),para:s=>`<p>${esc(s)}</p>`,val:(t,s)=>`<label>${esc(t)}</label>${esc(s)}`,date:s=>s||'',button:(t,a,id='',cls='')=>`<button class="${cls}" data-action="${a}" data-id="${esc(id)}">${esc(t)}</button>`,intakeReviewNotice:()=>'',sharedDomainReleases:()=>'Published work feed',intakeNames:{value:'Value proposition',in_scope:'Scope'},
 records:k=>ctx.state.records.filter(r=>r.kind===k),get:id=>ctx.state.records.find(r=>r.ref.id===id),findCase:id=>ctx.state.cases.find(c=>c.ref.id===id),
 field:(n,t,v,h,type)=>`<label>${esc(t)}<input name="${n}"></label>`,domainText:(n,t,v,r)=>`<label>${esc(t)}<textarea name="${n}" ${r?'required':''}>${esc(v)}</textarea></label>`,settingSelector:(id,t,opts,name)=>`<label>${t}<select id="${id}" name="${name}">${opts}</select></label>`,
 $:s=>{if(!nodes.has(s))nodes.set(s,{value:s==='#bridge-route'?'requirement':'comment',addEventListener(){},hidden:false,required:false});return nodes.get(s);},modal:(...args)=>dialogs.push(args),command:async(a,data)=>{calls.push({a,data});return {id:'ISSUE-SAVED',message:'Saved'};},render(){},abandonIntakeEdits:()=>true,
 proposalForm:(...args)=>ctx.proposal=args,decisionForm:c=>ctx.decision=c
 };vm.createContext(ctx);const app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');vm.runInContext(app.slice(app.indexOf('function recordedDate('),app.indexOf('\nasync function load(')),ctx);vm.runInContext(app.match(/^const ref=.*$/m)[0].replace('const ref=','ref='),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/signals.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/bridge.js'),'utf8'),ctx);return {ctx,calls,dialogs,nodes,run:s=>vm.runInContext(s,ctx)};
}
function issue(h,status='open',route='requirement'){
 const i={ref:{id:'ISSUE-1',revision:1},body:{title:'Which cue?',question:'A <script>question</script>',consequence:'Avoid repeated effort',boards:['research-design'],kind:'conflict',owner:'sam',decision_owner:route==='intent'?'priya':route==='coordination'?'sam':'alex',status,route,target:route==='requirement'?{id:'REQ',revision:1}:{id:'INT-001',revision:1},packet_refs:[{id:'PKT',revision:1}],basis:[{id:'CON',revision:1}],requirement_refs:[{id:'REQ',revision:1}],next_owner:'sam',next_question:'Clarify the cue',linked:null,resolution:null},events:[],changed:[],basis_records:[]};
 h.ctx.state.bridge.issues.push(i);h.ctx.state.records.push({ref:{id:'REQ',revision:1},kind:'requirement',body:{title:'Resume work',text:'Resume safely'}});return i;
}
function caseFor(h,i){const c={ref:{id:'CASE',revision:3},body:{target:{id:'REQ',revision:1},status:'pending-review',proposal:{text:'Show a cue',acceptance_criteria:'Observe resumption',conditions:'Bounded'},required_reviews:{sam:'supported-with-limits',lee:'cleared-with-conditions'},basis:[]},target_record:h.ctx.state.records[0],reviews:{},ready:true,stale:[]};h.ctx.state.cases=[c];i.body.linked={kind:'requirement',ref:c.ref};return c;}
test('three configured bridge boards organize issues by status and preserve existing work/review views',()=>{
 const h=harness();issue(h);issue(h,'awaiting-decision');const done=issue(h,'resolved');done.body.resolution={actor:'alex'};
 h.run("bridgeSection='boards'");
 const html=h.run('bridgeScreen()');for(const s of ['Decisions & Issues','Sponsor · Research','Sponsor · Design','Research · Design','To investigate','Waiting or decision','Resolved','Raise an issue'])assert.match(html,new RegExp(s));
 assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);
 h.run("bridgeSection='work'");assert.match(h.run('bridgeScreen()'),/Published work feed/);h.run("bridgeSection='reviews'");assert.match(h.run('bridgeScreen()'),/Requirements in development/);
});
test('issue detail connects source inspection, next owner, response history and governing decision',()=>{
 const h=harness(),i=issue(h);h.ctx.selected=i.ref.id;caseFor(h,i);const html=h.run('bridgeScreen()');for(const s of ['Question to resolve','Why this matters','Next response','Linked requirement review','Record requirement decision','Responses and history'])assert.match(html,new RegExp(s));assert.match(html,/<a[^>]+data-action="packet" data-id="PKT\|1"/);assert.doesNotMatch(html,/<script>/);
});
test('decision modal readiness includes issue freshness and open information requests',async()=>{
 const h=harness(),i=issue(h);caseFor(h,i);i.changed=[{previous:{id:'R',revision:1}}];await h.run("bridgeAction('bridge-decide','ISSUE-1')");assert.equal(h.ctx.decision.ready,false);i.changed=[];i.body.information_request={status:'open',owner:'lee'};await h.run("bridgeAction('bridge-decide','ISSUE-1')");assert.equal(h.ctx.decision.ready,false);
 i.body.information_request.status='answered';await h.run("bridgeAction('bridge-decide','ISSUE-1')");assert.equal(h.ctx.decision.ready,true);
});
test('new issue form exposes only shared packets and includes exact target versions once',async()=>{
 const h=harness();issue(h);h.ctx.state.packets=[{id:'PKT',revision:1,purpose:'Shared finding',audience_scopes:['project:demo'],records:[]},{id:'PRIVATE',revision:1,purpose:'Secret',audience_scopes:['domain:research','project:demo'],records:[]}];await h.run("bridgeAction('bridge-new','')");const html=h.dialogs[0][1];assert.match(html,/Shared finding/);assert.doesNotMatch(html,/Secret|PRIVATE/);
 const fd=new Map([['title','Cue question'],['kind','conflict'],['question','Which cue?'],['consequence','Repeated work'],['owner','sam'],['route','requirement'],['target','REQ']]);fd.getAll=k=>({board:['business-design'],packet:['PKT|1'],affected:[]}[k]||[]);await h.dialogs[0][3](fd);
 assert.equal(h.calls[0].a,'bridge-raise');assert.equal(h.calls[0].data.packet_refs[0].revision,1);assert.equal(h.calls[0].data.requirement_refs.length,1);assert.equal(h.calls[0].data.target.revision,1);assert.equal(h.ctx.selected,'ISSUE-SAVED');assert.equal(h.run('bridgeBoard'),'business-design');
});
test('requirement proposal keeps the issue context and review linkage',async()=>{
 const h=harness(),i=issue(h),c=caseFor(h,i);await h.run("bridgeAction('bridge-propose','ISSUE-1')");assert.equal(h.ctx.proposal[0].ref.id,'REQ');assert.equal(h.ctx.proposal[1].ref.id,c.ref.id);assert.equal(h.ctx.proposal[3].ref.id,i.ref.id);
});
test('sponsor adoption is not shown as resolution and final outcomes remain linked',()=>{
 const h=harness(),i=issue(h,'investigating','intent');h.ctx.state.actor='priya';i.body.linked={kind:'intent',ref:{id:'ICR',revision:2}};h.ctx.state.intake.refinements=[{ref:i.body.linked.ref,body:{status:'drafted',proposed_value:'A revised scope'}}];h.ctx.selected=i.ref.id;
 const html=h.run('bridgeScreen()');assert.match(html,/Prepare sponsor response/);assert.match(html,/Continue intake and preflight/);assert.match(html,/leaves this issue open/);assert.doesNotMatch(html,/Record requirement decision/);
});
test('no-change closure is explicit and the main history retains past outcomes after reopening',async()=>{
 const h=harness(),i=issue(h,'open','coordination');h.ctx.state.actor='sam';await h.run("bridgeAction('bridge-close','ISSUE-1')");assert.match(h.dialogs[0][1],/Existing requirements and Business Intent remain unchanged/);
 await h.dialogs[0][3](new Map([['rationale','No change needed'],['confirm','on']]));assert.equal(h.calls[0].a,'bridge-close');assert.equal(h.calls[0].data.confirm,true);
 h.ctx.state.bridge.outcomes=[{issue:i.ref,title:'Which cue?',disposition:'no-governing-change',rationale:'Retain scope',actor:'sam',decision:{id:'D',revision:1},at:'Now'}];assert.match(h.run('bridgeDecisionHistory()'),/Retain scope/);assert.match(h.run('bridgeDecisionHistory()'),/data-action="bridge-open"[^>]+data-id="ISSUE-1"/);
});
test('information requests expose the assigned response and authority-specific withdrawal',()=>{
 const h=harness(),i=issue(h);caseFor(h,i);i.body.information_request={status:'open',owner:'lee',question:'Which cue was tested?'};h.ctx.selected=i.ref.id;
 assert.match(h.run('bridgeScreen()'),/Withdraw information request/);h.ctx.state.actor='lee';let html=h.run('bridgeScreen()');assert.match(html,/Answer this request/);assert.doesNotMatch(html,/Withdraw information request|Record requirement decision/);
});

test('overview puts my next actions first and shows exact context in a collapsed row',async()=>{
 const h=harness(),i=issue(h,'awaiting-decision'),c=caseFor(h,i);
 i.body.next_owner='alex';
 const other=issue(h,'open','coordination');
 other.ref.id='ISSUE-2';
 other.body.title='Another team is investigating';
 h.ctx.state.bridge.timeline={entries:[{at:'2026-11-10T17:00:00Z',ref:{id:'EV',revision:2},category:'Issue recorded',subject:'Earlier handoff'}]};
 const html=h.run('bridgeScreen()');
 assert.match(html,/Open issues[\s\S]+Needs your attention[\s\S]+Which cue\?[\s\S]+Commitments and requests[\s\S]+Another team is investigating[\s\S]+<table class="accountability-table">/);h.run("bridgeSection='timeline'");assert.match(h.run('bridgeScreen()'),/Earlier handoff/);h.run("bridgeSection='overview'");
 const attention=html.slice(html.indexOf('id="accountability-attention-title"'),html.indexOf('id="accountability-commitments-title"'));assert.doesNotMatch(attention,/For you|Another team is investigating|Other open work|condition-chip-reference">Open</);
 h.run("bridgeSection='boards'");assert.match(h.run('bridgeScreen()'),/Another team is investigating/);h.run("bridgeSection='overview'");
 assert.match(html,/<details class="accountability-item[^\"]*" name="accountability-work"[^>]*>/);
 assert.match(html,/Requirement at review[\s\S]+Resume safely[\s\S]+Resume work · v1[\s\S]+Proposed wording[\s\S]+Show a cue[\s\S]+Review v3/);assert.match(html,/<details class="record-metadata"><summary>Source details<\/summary>[\s\S]+CASE:v3[\s\S]+REQ:v1/);
 assert.match(html,/data-action="packet" data-id="PKT\|1"/);
 assert.match(html,/data-action="bridge-decide" data-id="ISSUE-1"/);
 assert.doesNotMatch(html,/aria-label="Project work and reviews"/);h.run("bridgeSection='boards'");assert.match(h.run('bridgeScreen()'),/<aside[^>]+aria-label="Project work and reviews"[\s\S]+Published work[\s\S]+Teams &amp; Agents[\s\S]+Requirement reviews/);h.run("bridgeSection='overview'");assert.doesNotMatch(html,/data-action="bridge-section" data-id="assignments"/);
 i.changed=[{previous:{id:'REQ',revision:1}}];
 assert.doesNotMatch(h.run('bridgeScreen()'),/data-action="bridge-decide"/);
 i.changed=[];
 i.body.information_request={status:'open',owner:'lee',question:'Which work should proceed?'};
 assert.doesNotMatch(h.run('bridgeScreen()'),/data-action="bridge-decide"/);
 h.ctx.state.actor='lee';
 assert.match(h.run('bridgeScreen()'),/data-action="bridge-answer"/);
 assert.doesNotMatch(h.run('bridgeScreen()'),/data-action="bridge-decide"/);
 await h.run("bridgeAction('bridge-answer','ISSUE-1')");
 assert.match(h.dialogs[0][1],/Which work should proceed\?/);
 assert.equal(c.ready,true);
 assert.equal(h.calls.length,0);
});

test('overview includes sponsor decisions and keeps overflow in the same list',()=>{
 const h=harness();
 h.ctx.state.actor='priya';
 h.ctx.state.intake.cases=[{ref:{id:'INT-REVIEW',revision:1},body:{status:'pending-review',decision_owner:'priya',snapshot:{title:'Publish the next direction'}},ready:true}];
 for(let n=1;n<=4;n++){
  const i=issue(h);
  i.ref.id='ISSUE-'+n;
  i.body.next_owner='priya';
 }
 let html=h.run('bridgeScreen()');
 assert.match(html,/Needs your attention[\s\S]+Publish the next direction[\s\S]+Awaiting direction decision/);
 assert.match(html,/id="accountability-extra-mine" hidden/);
 assert.match(html,/data-action="bridge-overview-more" data-id="mine"/);
 h.ctx.state.actor='lee';
 html=h.run('bridgeScreen()');
 assert.doesNotMatch(html,/id="accountability-attention-title"/);assert.match(html,/Commitments and requests[\s\S]+Publish the next direction/);assert.doesNotMatch(html,/Other open work/);
});


test('issue submission and resolution retain separate event dates, including in collapsed overview rows',()=>{
 const h=harness(),i=issue(h);
 h.ctx.state.actor='sam';
 i.body.created_at='2026-11-01T15:00:00Z';i.body.updated_at='2026-11-07T15:00:00Z';i.waiting_since=i.body.updated_at;
 let html=h.run('bridgeScreen()');assert.match(html,/<summary>[\s\S]*Submitted <time datetime="2026-11-01T15:00:00Z"/);
 assert.match(h.run('bridgeCard(state.bridge.issues[0])'),/Submitted <time datetime="2026-11-01T15:00:00Z"/);
 i.body.status='resolved';i.body.resolution={actor:'alex',disposition:'approve',at:'2026-11-09T15:00:00Z',rationale:'Reviewed exact versions'};
 html=h.run('bridgeCard(state.bridge.issues[0])');assert.match(html,/Submitted <time datetime="2026-11-01T15:00:00Z"/);assert.match(html,/Resolved <time datetime="2026-11-09T15:00:00Z"/);
 i.decision_receipt={available:true,decision:{id:'DEC',revision:1},outcome:'approve',decider:{id:'alex',name:'Alex'},at:'2026-11-09T15:00:00Z',rationale:'Reviewed exact versions',approved:{ref:{id:'REQ',revision:2},kind:'requirement',text:'Approved cue'},evidence:[],reviews:[]};h.ctx.selected=i.ref.id;assert.match(h.run('bridgeScreen()'),/Decision receipt[\s\S]+Recorded <time datetime="2026-11-09T15:00:00Z"/);
 i.body.status='open';i.body.resolution=null;assert.doesNotMatch(h.run('bridgeCard(state.bridge.issues[0])'),/Resolved <time/);
});

test('reviews show proposal submission, individual assessments and the recorded decision date',()=>{
 const h=harness(),i=issue(h),c=caseFor(h,i);c.body.created_at='2026-11-02T15:00:00Z';c.body.decision_ids=['DEC-1'];c.body.status='approved';c.basis_records=[];c.revisions=[];
 c.reviews.sam={body:{at:'2026-11-03T15:00:00Z',disposition:'supported-with-limits',rationale:'Bounded evidence'}};
 h.ctx.state.decisions=[{ref:{id:'DEC-1',revision:1},body:{at:'2026-11-04T15:00:00Z'}}];
 h.run("bridgeRequirementBucket='reviews'");assert.match(h.run('bridgeReviewQueue()'),/Submitted <time datetime="2026-11-02T15:00:00Z"/);
 h.ctx.c=c;h.ctx.rid=r=>r.ref.id;h.ctx.intentRefinementNotice=()=>'';h.ctx.basisCard=()=>'';
 const app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');h.run(app.slice(app.indexOf('function reviewDetail('),app.indexOf('function decisions(')));
 const html=h.run('reviewDetail(c)');assert.match(html,/Submitted <time datetime="2026-11-02T15:00:00Z"/);assert.match(html,/Submitted <time datetime="2026-11-03T15:00:00Z"/);assert.match(html,/Decision recorded <time datetime="2026-11-04T15:00:00Z"/);
 assert.doesNotMatch(html,/Design[\s\S]*Submitted <time datetime="undefined"/);
});

test('missing and invalid dates never invent a submission time or render unsafe markup',()=>{
 const h=harness();
 for(const value of [undefined,null,'','not a date','<script>alert(1)</script>']){h.ctx.testAt=value;const html=h.run("recordedDate('Submitted',testAt)");assert.match(html,/Date not recorded/);assert.doesNotMatch(html,/<time|Invalid Date|<script>/);}
 const i=issue(h);i.body.created_at=null;i.body.updated_at='2026-11-09T15:00:00Z';const html=h.run('bridgeCard(state.bridge.issues[0])');assert.match(html,/Submitted · Date not recorded/);assert.doesNotMatch(html,/datetime="2026-11-09/);
 h.ctx.event={at:'2026-11-03T15:00:00Z',ref:{id:'REVIEW',revision:1},category:'Business direction review submitted',intake_case:{id:'CASE',revision:2}};
 assert.match(h.run('bridgeTimelineEntry(event)'),/data-action="intake-case" data-id="CASE"/);
});


test('resolved receipt leads with the actual transaction and discloses evidence and historical authority',()=>{
 const h=harness(),i=issue(h,'resolved'),c=caseFor(h,i);i.body.resolution={packet:{id:'RESULT',revision:2}};
 i.decision_receipt={available:true,decision:{id:'DEC-EXACT',revision:1},outcome:'approve',decider:{id:'priya',name:'Recorded delegate'},at:'2026-11-09T15:00:00Z',rationale:'Approve with bounded evidence <script>',approved:{ref:{id:'REQ',revision:2},kind:'requirement',text:'The exact approved wording',acceptance_criteria:'Observe successful use',conditions:'Within the stated limits'},evidence:[{ref:{id:'FINDING',revision:3},kind:'contribution',fields:{title:'Observed in the study',observation:'A source-grounded finding',limitation:'Small sample'}}],reviews:[{ref:{id:'ASSESS',revision:1},kind:'domain-review',reviewer:{id:'sam',name:'Recorded reviewer'},fields:{rationale:'Supported within limits'}}],authority:{authorized_as:'delegate',principal:'bound-account',policy:{policy:{id:'POLICY',revision:2},decider:'alex',reviewers:['sam'],people:{alex:{name:'Recorded primary'}}},delegation:{by:'alex',at:'2026-11-08T15:00:00Z',reason:'Named coverage'}},boundary:'Requirement approval only'};
 h.ctx.selected=i.ref.id;h.ctx.state.actors.alex.name='A different current member';const html=h.run('bridgeScreen()');
 for(const s of ['Decision receipt','Recorded delegate','Approve with bounded evidence &lt;script>','Approved wording','The exact approved wording','Observe successful use','Evidence and reviews (2)','Authority at the time of decision','Recorded primary','Named coverage','RESULT|2'])assert.ok(html.includes(s),s);
 assert.match(html,/<details class="receipt-evidence"><summary>/);assert.match(html,/<details class="receipt-authority"><summary>/);assert.doesNotMatch(html,/A different current member|Linked requirement review|<script>|data-action="decision-form"/);
 assert.match(html,/data-action="case" data-id="CASE"/);assert.equal(h.calls.length,0);
});

test('a resolved no-change or rejection receipt never presents proposed text as approved',()=>{
 const h=harness(),i=issue(h,'resolved');i.body.resolution={};caseFor(h,i);i.decision_receipt={available:true,decision:{id:'DEC',revision:1},outcome:'reject',decider:{id:'alex',name:'Alex'},rationale:'The evidence does not support the change',approved:null,wording_message:'The proposal was rejected. No new requirement wording was approved.',evidence:[],reviews:[],authority:null};h.ctx.selected=i.ref.id;
 const html=h.run('bridgeScreen()');assert.match(html,/Proposal rejected/);assert.doesNotMatch(html,/<h3>Approved wording|Show a cue/);assert.match(html,/No decision-authority snapshot was recorded/);assert.match(html,/Recorded · Date not recorded/);
});

test('missing exact records show an honest receipt gap without fabricated approval details',()=>{
 const h=harness(),i=issue(h,'resolved');i.body.resolution={rationale:'Should not be promoted to a receipt'};i.decision_receipt={available:false,decision:{id:'MISSING',revision:2},message:'The saved decision record is unavailable.'};h.ctx.selected=i.ref.id;const html=h.run('bridgeScreen()');assert.match(html,/role="status">The saved decision record is unavailable/);assert.doesNotMatch(html,/Approved wording|Should not be promoted to a receipt/);
});

test('receipt distinguishes stage and simulation from an unconfirmed external send and links only local results',()=>{
 const h=harness(),i=issue(h,'resolved');i.body.resolution={};i.decision_receipt={available:true,decision:{id:'DEC',revision:1},outcome:'approve',decider:{name:'Alex'},rationale:'Approve bounded wording',approved:{kind:'requirement',ref:{id:'REQ',revision:2},text:'Approved'},evidence:[],reviews:[],delivery:{applicable:true,message:'No confirmed external update is recorded. A live Jira/ADO connector is not connected.',targets:[{target:'jira',status:'simulated',stories:[{receipt:{id:'DEMO-RECEIPT',revision:1},key:'DEMO-CLINIC-1'}],transactions:[{ref:{id:'PREVIEW',revision:1},kind:'demo-delivery-preview',mode:'demo',status:'simulated',destination:'DEMO'}]},{target:'ado',status:'staged',stories:[],transactions:[{ref:{id:'DRAFT',revision:1},kind:'delivery-draft',mode:'preview',status:'staged',destination:'SYNTHETIC'}]}]}};h.ctx.selected=i.ref.id;
 const html=h.run('bridgeScreen()');for(const s of ['Jira / Azure DevOps','Simulated · no external update','Staged · not sent','Actually sent','Not confirmed','local simulated story'])assert.ok(html.includes(s),s);
 assert.match(html,/<a[^>]+data-action="demo-delivery-item"[^>]+data-id="DEMO-RECEIPT"/);assert.match(html,/<a[^>]+data-action="bridge-receipt-stage"[^>]+data-id="DRAFT"/);assert.doesNotMatch(html,/href="https:|Actually sent[^<]*confirmed successfully/);assert.match(html,/<details><summary>Saved transactions/);
});

test('a saved payload preview opens read-only from the receipt without a send or staging action',async()=>{
 const h=harness(),i=issue(h,'resolved');h.ctx.selected=i.ref.id;i.decision_receipt={delivery:{targets:[{target:'jira',transactions:[{ref:{id:'DRAFT',revision:2},kind:'delivery-draft',target:'jira',source:{id:'REQ',revision:2},destination:'SYNTHETIC',items:[{title:'Exact story draft',requirement:'The approved condition',acceptance_criteria:'Observe completion',payload:{title:'<script>'},method:'POST',endpoint:'/issue'}]}]}]}};
 await h.run("bridgeAction('bridge-receipt-stage','DRAFT')");const d=h.dialogs[0];assert.match(d[1],/Staged · not sent/);assert.match(d[1],/The approved condition/);assert.doesNotMatch(d[1],/<script>/);assert.equal(d[2],null);assert.equal(d[3],null);assert.equal(h.calls.length,0);
});

test('legacy brief content remains readable without a duplicate primary bridge tab',()=>{
 const h=harness();h.ctx.projectFlow=()=>({can_request:true});h.ctx.domainBriefDirectory=()=>'<section>ALL ACCESSIBLE BRIEFS</section>';h.run("bridgeSection='assignments'");
 const html=h.run('bridgeScreen()');assert.match(html,/ALL ACCESSIBLE BRIEFS/);assert.doesNotMatch(html,/Send domain brief|pflow-request-new/);assert.equal((html.match(/data-action="bridge-section" data-id="assignments"/g)||[]).length,0);assert.doesNotMatch(html,/data-id="developer-briefs"|Brief board|Raise an issue/);
 h.run("bridgeSection='developer-briefs'");assert.match(h.run('bridgeScreen()'),/ALL ACCESSIBLE BRIEFS/);assert.equal(h.run('bridgeSection'),'assignments');
});

function integrityFixture(h,i){
 const v={assessment:{id:'IR-REVIEW',revision:1},summary:'Execution-time qualification is not established.',mode:'formal',scope:'cross-domain',semantic_evaluated:true,model:{model:'test'},
 proposal:{ref:{id:'PROPOSAL',revision:1},body:{text:'Retain assignment checks and add execution enforcement.',rationale:'Qualification may expire after assignment.'}},stale:[],
 findings:[{key:'timing',title:'Timing gap',classifications:['weakening'],effect:'Assignment differs from execution.',citations:[{id:'REQ',revision:1,field:'text',quote:'valid at execution <script>'}],origin:'deterministic',support:'supported',action:'Establish enforcement',material:true}],
 domain_approval:'recorded',reconciliation:'unresolved',ratification:null,can_reconcile:true,local_approvals:[{packet:{id:'P1',revision:1},can_approve:false,disposition:'approved-with-limits'},{packet:{id:'P2',revision:1},can_approve:false,disposition:'approved'}],history_records:[],
 trace:{packets:[{id:'P1',revision:1},{id:'P2',revision:1}],requirements:[{id:'REQ',revision:1}],records:[{ref:{id:'REQ',revision:1},kind:'requirement',body:{title:'Qualified work',text:'Only valid personnel work.'}}],predecessors:[],manifest:{boundary:'One dependency hop',omitted:[],unavailable:[]}}};
 i.integrity=v;i.rights={can_decide:true};return v;
}
test('AI partner leads with the exact recommendation and material difference, with trace in place',()=>{
 const h=harness(),i=issue(h),v=integrityFixture(h,i),html=h.ctx.bridgeDetail(i);
 assert.ok(html.indexOf('Recommendation under review')<html.indexOf('Trace the recommendation'));
 assert.match(html,/Timing gap/);assert.match(html,/Record disposition/);assert.match(html,/Governing requirements/);
 assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);
 assert.match(html,/Local domain approval/);assert.match(html,/Cross-domain reconciliation/);assert.match(html,/Shared-use ratification/);
 assert.doesNotMatch(h.ctx.bridgeIntegrityActions(i),/data-action="bridge-propose"/);
});
test('a human challenge and deferral submit exact review context and a rationale',async()=>{
 const h=harness(),i=issue(h);integrityFixture(h,i);
 await h.run("bridgeAction('bridge-integrity-dispose','ISSUE-1')");
 assert.match(h.dialogs[0][1],/Challenge the finding with rationale/);assert.match(h.dialogs[0][1],/Investigate and defer/);
 await h.dialogs[0][3](new Map([['finding','timing'],['disposition','reject-with-rationale'],['rationale','Cited evidence does not support this interpretation.']]));
 assert.equal(h.calls[0].a,'integrity-dispose');assert.equal(h.calls[0].data.expected.revision,1);
 assert.equal(h.calls[0].data.rationale,'Cited evidence does not support this interpretation.');
});
test('ratification opens with the AI partner and requires explicit confirmation',async()=>{
 const h=harness(),i=issue(h);integrityFixture(h,i);
 await h.run("bridgeAction('bridge-integrity-ratify','ISSUE-1')");
 assert.match(h.dialogs[0][1],/Decision basis/);assert.match(h.dialogs[0][1],/Recommendation under review/);
 assert.match(h.dialogs[0][1],/type="checkbox" name="confirm" required/);
 assert.match(h.dialogs[0][1],/Governing requirements remain unchanged/);
});
test('changed review inputs remain visible and earlier dispositions expand without a second destination',()=>{
 const h=harness(),i=issue(h),v=integrityFixture(h,i);v.stale=[{previous:{id:'REQ',revision:1}}];v.history_records=[{assessment:{id:'OLD',revision:1},summary:'Earlier gap',dispositions:{timing:{disposition:'investigate-and-defer'}}}];
 const html=h.ctx.bridgeIntegrityPanel(i);assert.match(html,/Inputs changed/);assert.match(html,/Earlier gap/);assert.match(html,/investigate and defer/);
 assert.doesNotMatch(html,/data-action=".*navigate/);
});

test('live recommendation and execution proof are distinct from the human proposal',()=>{
 const h=harness(),i=issue(h),v=integrityFixture(h,i);v.execution_receipt={ref:{id:'RUN',revision:2},mode:'live',status:'succeeded',model:'returned-model',finished_at:'2026-11-14T20:00:00Z'};v.model={model:'configured-model',resolved_model:'returned-model',response_id:'resp-real',settings:{reasoning_effort:'low'}};
 const html=h.ctx.bridgeIntegrityPanel(i);assert.match(html,/Model recommendation/);assert.match(html,/Recommendation under review/);assert.match(html,/Live model response/);assert.match(html,/Model execution receipt/);assert.match(html,/returned-model/);assert.match(html,/resp-real/);
});

test('model citation tokens open exact source passages without a write',async()=>{
 const h=harness(),i=issue(h),v=integrityFixture(h,i);const key='C-0123456789abcdef';
 v.trace.citation_catalog={[key]:{id:'REQ',revision:1,field:'text',quote:'Only valid personnel work. <script>'}};v.summary='Enforce the current condition ('+key+').';
 const html=h.ctx.bridgeIntegrityPanel(i);assert.match(html,/Requirement v1<\/a>/);assert.match(html,/bridge-integrity-evidence-C-0123456789abcdef/);
 await h.run("bridgeAction('bridge-integrity-evidence-C-0123456789abcdef','ISSUE-1')");assert.match(h.dialogs[0][1],/Exact assessed version/);assert.match(h.dialogs[0][1],/&lt;script>/);assert.equal(h.dialogs[0][3],undefined);assert.equal(h.calls.length,0);
});


test('decision support is a private issue-local entry for named deciders and reviewers',()=>{
 const h=harness(),i=issue(h);i.rights={can_decide:true};
 let html=h.run('bridgeDetail(bridgeIssue("ISSUE-1"))');
 assert.match(html,/AI partner[\s\S]+Private support for this decision/);assert.match(html,/data-action="bridge-decision-review"/);
 i.rights={can_decide:false,can_review:false};assert.doesNotMatch(h.run('bridgeDetail(bridgeIssue("ISSUE-1"))'),/data-action="bridge-decision-review"/);
 i.rights.can_review=true;assert.match(h.run('bridgeDetail(bridgeIssue("ISSUE-1"))'),/data-action="bridge-decision-review"/);
});
test('opening private review reads saved context but sends only on explicit question submission',async()=>{
 const h=harness(),i=issue(h);i.rights={can_decide:true};
 h.ctx.command=async(a,data)=>{h.calls.push({a,data});return {title:'Which cue?',private:true,configured:true,thread:null,messages:[]};};
 h.ctx.crypto={randomUUID:()=> 'request-synthetic'};
 h.nodes.set('#modal-title',{classList:{add(){}},innerHTML:''});
 await h.run("bridgeAction('bridge-decision-review','ISSUE-1')");assert.equal(h.calls.length,1);assert.equal(h.calls[0].a,'decision-integrity-read');
 assert.match(h.dialogs[0][1],/Private to this reviewer/);assert.match(h.dialogs[0][1],/Sending does not approve or change anything/);
 assert.doesNotMatch(h.dialogs[0][1],/approve this requirement/i);
 await h.dialogs[0][3](new Map([['question','What evidence is missing?']]));assert.equal(h.calls[1].a,'decision-integrity-send');assert.equal(h.calls[1].data.expected.id,'ISSUE-1');assert.equal(h.calls[1].data.consent,true);
});

test('private review source links expand exact saved passages in place without model calls',async()=>{
 const h=harness();let opens=0,focuses=0;
 const group={open:false},entry={open:false,closest:()=>({}),parentElement:{closest:()=>group},scrollIntoView(){opens++;},querySelector:()=>({focus(){focuses++;}})};
 h.ctx.document={getElementById:id=>id==='decision-evidence-0-C-1234567890abcdef'?entry:null};
 await h.run("bridgeAction('bridge-decision-source','decision-evidence-0-C-1234567890abcdef')");
 assert.equal(entry.open,true);assert.equal(group.open,true);assert.equal(opens,1);assert.equal(focuses,1);assert.equal(h.calls.length,0);
});

function optionsFixture(h,i){
 const v=integrityFixture(h,i),key='C-0123456789abcdef';v.trace.citation_catalog={[key]:{id:'REQ',revision:1,field:'text',quote:'Valid at execution.'}};
 const option=(id,gate)=>({id,kind:id==='C'?'investigate':'retain',action:id==='C'?'Inspect the existing control <script>':'Rely on assignment only',owner:'alex',hard_gate:gate,gate_reasons:gate==='blocked'?['Execution timing is not covered.']:[],declared_condition_results:[],comparison:{fidelity:'Current execution condition',evidence:'Unverified control records',workability:'Owner inspection required',risk_and_change:'Reversible investigation',effort_and_cost:'Unknown'},dependencies:[],uncertainties:['Enforcement remains unverified.'],evidence_refs:[key]});
 v.decision_trace={recommendation:{preferred_option:'C',requested_decision:'Authorize evidence inspection.',why:'An existing control may resolve the gap.',authority:{decider:'alex'},conditions:['Execution coverage is unproven.'],would_change_if:['Actual control records contradict coverage.']},options:[option('B','blocked'),option('C','passes')],obligations:[{source:v.trace.citation_catalog[key],elements:{timing:{status:'specified',quote:'at execution',interpretation:'At execution'},threshold:{status:'unspecified',quote:'',interpretation:''}}}],packet_findings:[{packet_ref:'P1:v1',obligation_ref:key,status:'uncertain',reasoning:'A packet is not enforcement evidence.',evidence_refs:[key]}],differences:[{classification:'complementary',obligation_ref:key,consequence:'Qualification might expire after assignment.',would_disprove:'Actual start-control records.',evidence_refs:[key]}],intended_use:'Support the named human decision.',support_boundary:'Semantic support awaits human review.'};
 return v;
}
test('decision trace leads with the requested decision and limits; options and source details unfold',()=>{
 const h=harness(),i=issue(h);optionsFixture(h,i);const html=h.ctx.bridgeIntegrityPanel(i);
 assert.ok(html.indexOf('Requested decision')<html.indexOf('Trace the recommendation'));
 for(const text of ['What remains unproven','Compare options','Blocked under the current basis','Admissible next action','Source obligations and interpretations','Unspecified in this clause','Semantic support awaits human review'])assert.ok(html.includes(text));
 assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);
 assert.doesNotMatch(html,/<details[^>]*open/);assert.equal(h.calls.length,0);
});
test('blocked options cannot be accepted in the dialog and modifications retain exact context',async()=>{
 const h=harness(),i=issue(h);optionsFixture(h,i);
 await h.run("bridgeAction('bridge-integrity-option-0','ISSUE-1')");assert.doesNotMatch(h.dialogs[0][1],/value="accept-next-step"/);
 await h.dialogs[0][3](new Map([['disposition','modify'],['rationale','Need execution coverage'],['proposed_correction','Retain the assignment check and inspect the start control.']]));
 assert.equal(h.calls[0].a,'integrity-option-response');assert.equal(h.calls[0].data.option,'B');assert.equal(h.calls[0].data.expected.revision,1);assert.match(h.calls[0].data.proposed_correction,/start control/);
 await h.run("bridgeAction('bridge-integrity-option-1','ISSUE-1')");assert.match(h.dialogs[1][1],/value="accept-next-step"/);
});
test('option response controls respect authority freshness and closed state',()=>{
 const h=harness(),i=issue(h),v=optionsFixture(h,i);
 assert.match(h.ctx.bridgeIntegrityDecision(i),/Record response to this option/);
 i.rights.can_decide=false;assert.doesNotMatch(h.ctx.bridgeIntegrityDecision(i),/Record response to this option/);
 i.rights.can_decide=true;v.stale=[{}];assert.doesNotMatch(h.ctx.bridgeIntegrityDecision(i),/Record response to this option/);
 v.stale=[];i.body.status='resolved';assert.doesNotMatch(h.ctx.bridgeIntegrityDecision(i),/Record response to this option/);
});
test('human corrections and prior option responses remain inspectable after reassessment',()=>{
 const h=harness(),i=issue(h),v=optionsFixture(h,i);
 v.findings[0].disposition={body:{disposition:'modify-with-rationale',rationale:'Keep the limited scenario',proposed_correction:'Check the start condition',actor:'alex',at:'2026-11-15T01:00:00Z'}};
 v.history_records=[{assessment:{id:'OLD',revision:1},summary:'Investigate the candidate.',decision_trace:v.decision_trace,option_responses:{C:{disposition:'accept-next-step',rationale:'Inspect before changing',actor:'alex',at:'2026-11-15T01:00:00Z'}},inputs:[]}];
 const html=h.ctx.bridgeIntegrityPanel(i);assert.match(html,/Earlier options and recommendation/);assert.match(html,/Inspect before changing/);assert.match(html,/Check the start condition/);assert.match(html,/Recorded by/);
 v.findings=[];v.reconciliation='recorded';v.option_responses={C:{disposition:'defer'}};
 assert.doesNotMatch(h.ctx.bridgeIntegrityActions(i),/Review ratification/);
});

test('review handoff previews the requirement and excerpt and requires confirmation through the native issue form',async()=>{
 const h=harness(),req={kind:'requirement',ref:{id:'REQ',revision:4},body:{title:'Owner <check>',text:'Saved published wording',acceptance_criteria:'Observed acceptance'}},handoff={ref:{id:'HANDOFF',revision:1},requirement_record:req,context:[req],historical_context:true,review_excerpt:{assessment:'<script>Concern</script>',why_it_matters:'Do not infer acceptance'},user_question:'Who accepts?'};
 h.ctx.state.records=[req];h.ctx.handoff=handoff;h.run("bridgeRaiseForm({handoff,title:'Clarify owner',question:'Who accepts?',consequence:'Work may be missed',route:'requirement',owner:'alex',kind:'question'})");
 const dialog=h.dialogs.at(-1);assert.equal(dialog[0],'Carry concern to Decisions & Issues');for(const t of ['Saved published wording','Observed acceptance','Who accepts?','confirm_handoff','earlier context','&lt;script>'])assert.ok(dialog[1].includes(t),t);assert.doesNotMatch(dialog[1],/<script>/);assert.equal(h.calls.length,0);
 const values={title:'Clarify owner',question:'Who accepts?',consequence:'Work may be missed',route:'requirement',kind:'question',owner:'alex',target:'REQ',confirm_handoff:'on'},fd={get:k=>values[k],getAll:k=>k==='board'?['research-design']:k==='affected'?['REQ']:[],*[Symbol.iterator](){yield* Object.entries(values);}};
 await dialog[3](fd);assert.equal(h.calls[0].a,'field-coach-concern-publish');assert.equal(h.calls[0].data.expected.id,'HANDOFF');assert.equal(h.calls[0].data.confirm,true);assert.equal(h.ctx.view,'review');assert.equal(h.ctx.selected,'ISSUE-SAVED');
});
test('review concern context distinguishes published candidates from approved requirements without changing either',()=>{
 const h=harness();
 for(const status of ['proposed','approved']){
  const r={kind:'requirement',scope:'project:demo',ref:{id:'REQ',revision:4},body:{title:'Shared wording',text:'Exact saved text',status}},handoff={requirement_record:r,context:[r]},before=JSON.stringify(handoff);h.ctx.handoff=handoff;
  const html=h.run('bridgeReviewConcernContext(handoff)');assert.match(html,status==='approved'?/Published requirement/:/Published candidate/);assert.match(html,/Exact saved text/);assert.match(html,/REQ:v4/);assert.match(html,/confirm_handoff/);assert.equal(JSON.stringify(handoff),before);assert.equal(h.calls.length,0);
 }
});

test('project rail counts only published work and opens exact report and review records without writes',()=>{
 const h=harness(),i=issue(h),c=caseFor(h,i);
 h.ctx.state.records.push(
  {kind:'contribution-draft',ref:{id:'PRIVATE',revision:1},body:{title:'Private draft must stay private',domain:'Research'}},
  {kind:'contribution',ref:{id:'REPORT-1',revision:2},body:{title:'Earlier published report',domain:'Research',published_at:'2026-11-14T12:00:00Z'}},
  {kind:'contribution',ref:{id:'REPORT-2',revision:4},body:{title:'Latest <report>',domain:'Design',owner:'lee',published_at:'2026-11-16T12:00:00Z',working_report:{entries:[]}}}
 );
 const before=JSON.stringify(h.ctx.state),html=h.run('bridgeProjectRail()');
 assert.match(html,/2 published items/);assert.match(html,/data-action="read-contribution" data-id="REPORT-2"/);
 assert.match(html,/Latest &lt;report>/);assert.match(html,/Lee · v4/);
 assert.doesNotMatch(html,/Private draft must stay private|data-id="PRIVATE"|<report>|Created in Workbench|Published domain work<\/span>/);
 assert.match(html,/1 open review/);assert.match(html,/<section class="requirement-rail-group requirement-rail-current"><h3>Current review<\/h3><div class="requirement-rail-review-item"><a[^>]*data-action="case" data-id="CASE">Resume work<\/a><span class="condition-chip condition-chip-reference">Pending review<\/span><\/div>/);assert.match(html,/<h3>Browse requirements<\/h3>[\s\S]*data-id="candidates">Requirements in development<\/a><span>1<\/span>/);assert.doesNotMatch(html,/1 total|1 candidate/);
 assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(h.calls.length,0);
 c.stale=[{previous:{id:'CON',revision:1},current:{id:'CON',revision:2}}];const staleBefore=JSON.stringify(h.ctx.state),stale=h.run('bridgeProjectRail()');assert.match(stale,/<div class="requirement-rail-review-item"><a[^>]*data-id="CASE">Resume work<\/a><span class="condition-chip condition-chip-advisory">[\s\S]*?Review needs refresh<\/span><\/div>/);assert.equal(JSON.stringify(h.ctx.state),staleBefore);assert.equal(h.calls.length,0);
});

test('project rail preserves the three destinations, exposes unassigned work and distinguishes closed reviews',async()=>{
 const h=harness(),i=issue(h);i.body.next_owner=null;const c=caseFor(h,i);c.body.status='approved';
 h.run("bridgeSection='reviews'");const html=h.run('bridgeScreen()');
 assert.match(html,/Next responder unassigned/);assert.match(html,/0 open reviews/);assert.match(html,/<h3>Latest review<\/h3><div class="requirement-rail-review-item"><a[^>]*data-id="CASE">Resume work<\/a><span class="condition-chip condition-chip-reference">Approved<\/span><\/div>/);assert.doesNotMatch(html,/0 open · 1 total/);
 assert.match(html,/data-id="reviews" aria-current="page"/);
 const tabs=h.run('bridgeTabs()');assert.doesNotMatch(tabs,/Published work|Requirement reviews|Teams &amp; Agents/);
 for(const key of ['work','activity','reviews']){await h.ctx.bridgeAction('bridge-section',key);assert.equal(h.run('bridgeSection'),key);assert.equal(h.ctx.selected,null);}
 assert.match(html,/<footer class="accountability-rail-action"><button type="button" class="accountability-rail-workspace-action" data-action="bridge-requirement-view" data-id="reviews" aria-current="page">View all reviews/);
 h.run("bridgeRequirementBucket='candidates';bridgeRequirementCategory='OLD';selected='CASE'");const beforeNavigation=JSON.stringify(h.ctx.state);await h.ctx.bridgeAction('bridge-requirement-view','reviews');assert.equal(h.run('bridgeRequirementBucket'),'reviews');assert.equal(h.run('bridgeRequirementCategory'),'');assert.equal(h.run('bridgeSection'),'reviews');assert.equal(h.ctx.view,'review');assert.equal(h.ctx.selected,null);assert.equal(JSON.stringify(h.ctx.state),beforeNavigation);
 assert.equal(h.calls.length,0);
 const empty=harness().run('bridgeProjectRail()');assert.match(empty,/No recorded reviews\./);assert.match(empty,/No open assignments or requests\./);
});

test('quiet project update summary retains the last two publications and response priority without inventing deadlines',()=>{
 const h=harness();
 h.ctx.published=[1,2,3].map(n=>({ref:{id:'REPORT-'+n,revision:1},body:{title:'Publication '+n,domain:'Research',published_at:'2026-11-16T12:00:00Z'}}));
 h.ctx.items=[
  {kind:'issue',id:'NEWER',title:'Later request',owner:'alex',attention:true,gate:true,since:'2026-11-16T12:00:00Z',status:'Open'},
  {kind:'brief',id:'ASSIGNMENT',title:'Other accepted work',owner:'alex',attention:false,gate:false},
  {kind:'issue',id:'OLDER',title:'Earlier request',owner:'alex',attention:true,gate:true,since:'2026-11-14T12:00:00Z',status:'Information requested'}
 ];
 const before=JSON.stringify(h.ctx.items),html=h.run('bridgeProjectUpdate(published,items)');
 for(const text of ['Project update summary','Last 2 published','2 awaiting you','Due date not set.'])assert.ok(html.includes(text));
 assert.match(html,/Latest: Publication 1[\s\S]+Previous: Publication 2/);assert.doesNotMatch(html,/Publication 3|Later request|Other accepted work/);
 assert.match(html,/Next response: Earlier request/);assert.match(html,/data-action="bridge-section" data-id="work"/);assert.match(html,/data-action="bridge-section" data-id="activity"/);
 assert.equal(JSON.stringify(h.ctx.items),before);assert.equal(h.calls.length,0);
 assert.match(h.run('bridgeProjectUpdate([],[])'),/Nothing published[\s\S]+No responses pending/);
});

test('accountability header relocates the existing identity and status once without rebuilding them',()=>{
 const h=harness(),identity={kind:'identity'},status={kind:'status'},moved=[];
 const direct=new Map([[':scope > .project-page-identity',identity],[':scope > .project-status-line',status]]);
 const slot=kind=>({append(node){moved.push({kind,node});for(const [key,value] of direct)if(value===node)direct.delete(key);}});
 const identitySlot=slot('identity'),statusSlot=slot('status');
 const intro={querySelector:selector=>selector==='[data-accountability-identity]'?identitySlot:statusSlot},main={querySelector:selector=>direct.get(selector)};
 h.ctx.$=selector=>selector==='.accountability-page-intro'?intro:selector==='#main'?main:null;
 h.ctx.projectPageIdentity=h.ctx.projectStatusLine=()=>{throw Error('Must reuse the rendered node');};
 h.run('mountAccountabilityHeader()');h.run('mountAccountabilityHeader()');
 assert.equal(moved.length,2);assert.equal(moved[0].node,identity);assert.equal(moved[1].node,status);
 h.ctx.$=()=>null;assert.doesNotThrow(()=>h.run('mountAccountabilityHeader()'));assert.equal(h.calls.length,0);
});

test('pending requirement candidates retain their exact fields without entering the ratified baseline',()=>{
 const h=harness();h.ctx.state.records=[
  {ref:{id:'REQ-INTAKE/needs',revision:3},kind:'requirement',body:{status:'proposed',title:'Candidate <name>',text:'First condition\nSecond condition <script>',acceptance_criteria:'Observe the exact response',rationale:'Keep this saved rationale',conditions:'Only within the declared scope'}},
  {ref:{id:'REQ-approved',revision:2},kind:'requirement',body:{status:'approved',title:'Ratified baseline only',text:'Approved wording'}}
 ];
 const before=JSON.stringify(h.ctx.state),html=h.run('bridgeReviewQueue()');
 assert.match(html,/<h2>Requirements in development<\/h2>/);assert.match(html,/Decision reviews \(0\)/);assert.doesNotMatch(html,/<h2>Requirement reviews<\/h2>/);
 assert.match(html,/class="pending-requirement" id="candidate-REQ-INTAKE\/needs"/);
 const summary=html.match(/<details class="pending-requirement"[^>]*><summary>([\s\S]*?)<\/summary>/)[1];
 assert.match(summary,/<span class="workbench-object-heading"><span class="workbench-object-type">Requirement<\/span><span>Candidate &lt;name><\/span><\/span>/);
 assert.equal((summary.match(/workbench-object-type/g)||[]).length,1);assert.doesNotMatch(summary,/>Goal<|>Success measure</);
 for(const value of ['Candidate &lt;name>','First condition\nSecond condition &lt;script>','Observe the exact response','Keep this saved rationale','Only within the declared scope','REQ-INTAKE/needs:v3'])assert.ok(html.includes(value),value);
 assert.doesNotMatch(html,/Ratified baseline only|Approved wording|<script>/);
 assert.match(html,/data-action="proposal" data-id="REQ-INTAKE\/needs"/);assert.equal(h.calls.length,0);assert.equal(JSON.stringify(h.ctx.state),before);
});
test('candidate actions reuse an active review and honor current proposal capability',()=>{
 const h=harness(),i=issue(h),c=caseFor(h,i);h.ctx.state.records[0].body.status='proposed';h.ctx.state.actor='sam';
 let html=h.run('bridgeReviewQueue()');assert.match(html,/data-action="case" data-id="CASE"/);assert.doesNotMatch(html,/data-action="proposal"/);
 h.ctx.state.cases=[];html=h.run('bridgeReviewQueue()');assert.doesNotMatch(html,/data-action="proposal"/);
 h.ctx.canPrepareRequirement=()=>true;assert.match(h.run('bridgeReviewQueue()'),/data-action="proposal" data-id="REQ"/);
 h.ctx.state.actor='alex';h.ctx.canPrepareRequirement=()=>false;assert.doesNotMatch(h.run('bridgeReviewQueue()'),/data-action="proposal"/);
 assert.equal(h.calls.length,0);
});
test('requirement review rail makes candidates discoverable even before a decision case exists',()=>{
 const h=harness();h.ctx.state.records=[{kind:'requirement',ref:{id:'REQ',revision:1},body:{status:'proposed',title:'Awaiting first review',text:'Saved candidate'}}];
 const before=JSON.stringify(h.ctx.state),html=h.run('bridgeProjectRail()');
 assert.match(html,/0 open reviews/);assert.match(html,/<section class="requirement-rail-group requirement-rail-browse"><h3>Browse requirements<\/h3>[\s\S]*data-action="bridge-requirement-view" data-id="candidates">Requirements in development<\/a><span>1<\/span>/);assert.doesNotMatch(html,/No recorded reviews\.|Current review|Latest review|0 total/);assert.equal(JSON.stringify(h.ctx.state),before);
 h.ctx.state.records.push({kind:'requirement-drawer',ref:{id:'DRW-test',revision:1},body:{label:'Published shell'}});const shellBefore=JSON.stringify(h.ctx.state),withShell=h.run('bridgeProjectRail()');assert.match(withShell,/data-id="shells">Requirement areas<\/a><span>1<\/span>/);assert.match(withShell,/data-id="candidates">Requirements in development<\/a><span>1<\/span>/);assert.equal(JSON.stringify(h.ctx.state),shellBefore);assert.equal(h.calls.length,0);
});
test('candidate queue uses the shared pending projection with a safe standalone fallback',()=>{
 const h=harness();h.ctx.state.records=[{kind:'requirement',ref:{id:'REQ-all',revision:1},body:{status:'proposed',title:'Fallback candidate'}}];
 h.ctx.pendingRequirementRows=()=>[{kind:'requirement',ref:{id:'REQ-selected',revision:2},body:{status:'proposed',title:'Canonical candidate',text:'Selected pending projection'}}];
 const projected=h.run('bridgeReviewQueue()');assert.match(projected,/Canonical candidate/);assert.doesNotMatch(projected,/Fallback candidate/);
 delete h.ctx.pendingRequirementRows;delete h.ctx.records;
 assert.match(h.run('bridgeReviewQueue()'),/No requirements in development\./);
});

test('published requirement shells remain scoped areas with exact criteria rather than validation claims',()=>{
 const h=harness();h.ctx.state.records=[
  {kind:'requirement-drawer',ref:{id:'DRW-a',revision:2},body:{label:'Published <area>',question:'Investigate the saved scope\nKeep this boundary',criteria:'Exact reviewer criterion',evidence:'Evidence still to collect',status:'active'}},
  {kind:'requirement-drawer',ref:{id:'DRW-a/child',revision:1},body:{label:'A nested area',parent_id:'DRW-a',question:'Question for the child',criteria:'Child criterion',status:'active'}},
  {kind:'requirement',ref:{id:'REQ',revision:1},body:{status:'proposed',drawer_id:'DRW-a/child',title:'Candidate within child',text:'Saved proposed wording'}},
  {kind:'requirement-drawer-draft',ref:{id:'PRIVATE',revision:1},body:{label:'Private area must not appear'}}
 ];
 h.run("bridgeRequirementBucket='shells'");const before=JSON.stringify(h.ctx.state),html=h.run('bridgeReviewQueue()');
 for(const text of ['Published &lt;area>','Investigate the saved scope\nKeep this boundary','Exact reviewer criterion','Evidence still to collect','A nested area','Child criterion','DRW-a:v2','DRW-a/child:v1','1 requirement'])assert.ok(html.includes(text),text);
 assert.match(html,/data-action="requirement" data-id="REQ"/);assert.doesNotMatch(html,/Private area must not appear|data-action="decision|Validated|Substantiated/);assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(h.calls.length,0);
 const rail=h.run('bridgeProjectRail()');assert.match(rail,/data-action="bridge-requirement-view" data-id="shells">Requirement areas/);
});
test('requirement filters show one bucket and preserve category scope across candidates shells and reviews',async()=>{
 const h=harness();h.ctx.state.records=[
  {kind:'requirement-drawer',ref:{id:'DRW-a',revision:1},body:{label:'Area A'}},{kind:'requirement-drawer',ref:{id:'DRW-a/child',revision:1},body:{label:'Child A',parent_id:'DRW-a'}},
  {kind:'requirement-drawer',ref:{id:'DRW-b',revision:1},body:{label:'Area B'}},
  {kind:'requirement',ref:{id:'REQ-a',revision:1},body:{status:'proposed',title:'Candidate A',text:'Wording A',drawer_id:'DRW-a/child'}},
  {kind:'requirement',ref:{id:'REQ-b',revision:1},body:{status:'proposed',title:'Candidate B',text:'Wording B',drawer_id:'DRW-b'}}
 ];
 h.ctx.state.cases=[{ref:{id:'CASE-a',revision:1},body:{status:'pending-review',target:{id:'REQ-a',revision:1},proposal:{text:'Review wording A'}}},{ref:{id:'CASE-b',revision:1},body:{status:'pending-review',target:{id:'REQ-b',revision:1},proposal:{text:'Review wording B'}}}];
 const before=JSON.stringify(h.ctx.state);h.ctx.render=()=>{};
 let html=h.run('bridgeReviewQueue()');assert.match(html,/Requirements in development \(2\)/);assert.match(html,/Requirement areas \(3\)/);assert.match(html,/Decision reviews \(2\)/);assert.doesNotMatch(html,/<h2>Requirement areas<\/h2>|<h2>Requirement reviews<\/h2>/);
 h.run("bridgeRequirementFilter('category','DRW-a')");html=h.run('bridgeReviewQueue()');assert.match(html,/Candidate A/);assert.doesNotMatch(html,/Candidate B/);assert.match(html,/Requirements in development \(1\)/);
 h.run("bridgeRequirementFilter('bucket','shells')");html=h.run('bridgeReviewQueue()');assert.match(html,/id="shell-DRW-a\/child"/);assert.doesNotMatch(html,/id="shell-DRW-b"|<h2>Requirements in development<\/h2>/);
 h.run("bridgeRequirementFilter('bucket','reviews')");html=h.run('bridgeReviewQueue()');assert.match(html,/Review wording A/);assert.doesNotMatch(html,/Review wording B|class="pending-requirement"/);
 await h.run("bridgeAction('bridge-requirement-view','candidates')");assert.equal(h.run('bridgeRequirementBucket'),'candidates');assert.equal(h.run('bridgeRequirementCategory'),'');assert.equal(h.run('bridgeSection'),'reviews');assert.equal(h.ctx.selected,null);
 h.run("bridgeRequirementFilter('category','UNKNOWN')");assert.equal(h.run('bridgeRequirementCategory'),'');assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(h.calls.length,0);
});

test('candidate evidence cue counts only public reports linked to its exact version',()=>{
 const h=harness(),candidate={kind:'requirement',ref:{id:'REQ',revision:3},body:{status:'proposed',title:'An exact candidate',text:'Saved wording'}};
 h.ctx.state.records=[candidate,
  {kind:'contribution',scope:'project:demo',ref:{id:'REPORT-current',revision:4},body:{title:'Exact <shared> report',requirement_refs:[{id:'REQ',revision:3},{id:'REQ',revision:3}],published_at:'2026-11-20'}},
  {kind:'contribution',scope:'project:demo',ref:{id:'REPORT-old-target',revision:1},body:{title:'Report linked to previous candidate',requirement_refs:[{id:'REQ',revision:2}]}},
  {kind:'contribution',scope:'project:demo',ref:{id:'REPORT-unversioned',revision:1},body:{title:'Unversioned link cannot qualify',requirement_refs:[{id:'REQ'}]}},
  {kind:'contribution-draft',scope:'domain:research',ref:{id:'PRIVATE-draft',revision:1},body:{title:'Private draft must not leak',requirement_refs:[{id:'REQ',revision:3}]}},
  {kind:'contribution',scope:'domain:research',ref:{id:'PRIVATE-scope',revision:1},body:{title:'Private scope must not leak',requirement_refs:[{id:'REQ',revision:3}]}}
 ];
 h.ctx.candidate=candidate;const before=JSON.stringify(h.ctx.state),html=h.run('bridgeRequirementCandidate(candidate)');
 assert.match(html,/Evidence: 1 linked report/);assert.match(html,/data-action="read-contribution" data-id="REPORT-current"/);assert.match(html,/Exact &lt;shared> report/);assert.match(html,/REPORT-current:v4/);
 assert.doesNotMatch(html,/previous candidate|Unversioned link|Private draft|Private scope|Validated|Substantiated/);assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(h.calls.length,0);
 candidate.ref.revision=4;const later=h.run('bridgeRequirementCandidate(candidate)');assert.match(later,/Evidence: Not linked here/);assert.match(later,/No published report is linked to this exact version here/);assert.doesNotMatch(later,/data-action="read-contribution"/);
});

test('candidate and shell trace references stay available within optional source details',()=>{
 const h=harness();h.ctx.state.records=[
  {kind:'requirement-drawer',ref:{id:'DRW-metadata',revision:2},body:{label:'Readable area title',question:'A saved question',criteria:'Saved criteria'}},
  {kind:'requirement',ref:{id:'REQ-metadata',revision:3},body:{status:'proposed',title:'Readable candidate title',text:'Saved wording',drawer_id:'DRW-metadata'}},
  {kind:'contribution',scope:'project:demo',ref:{id:'REPORT-metadata',revision:4},body:{title:'Readable report title',requirement_refs:[{id:'REQ-metadata',revision:3}]}}
 ];
 const before=JSON.stringify(h.ctx.state),candidate=h.run('bridgeReviewQueue()'),primary=candidate.slice(0,candidate.indexOf('<details class="requirement-source-details">'));
 assert.match(primary,/Readable candidate title/);assert.match(primary,/Readable report title/);assert.match(primary,/data-action="read-contribution" data-id="REPORT-metadata"/);
 assert.doesNotMatch(primary,/REQ-metadata:v3|REPORT-metadata:v4/);assert.match(candidate,/<details class="requirement-source-details"><summary>Source details<\/summary>[\s\S]+REQ-metadata:v3[\s\S]+REPORT-metadata:v4/);
 h.run("bridgeRequirementBucket='shells'");const shells=h.run('bridgeReviewQueue()'),shellPrimary=shells.slice(0,shells.indexOf('<details class="requirement-source-details">'));
 assert.match(shellPrimary,/Readable area title/);assert.doesNotMatch(shellPrimary,/DRW-metadata:v2/);assert.match(shells,/<details class="requirement-source-details"><summary>Source details<\/summary>[\s\S]+DRW-metadata:v2/);assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(h.calls.length,0);
});

test('board cards use the same authoritative request owner and simulation indication as overview',()=>{
 const h=harness(),i=issue(h,'awaiting-decision');i.body.title='SIMULATION — Decide the scope';i.body.information_request={status:'open',owner:'lee',question:'Which scope did participants test?'};h.ctx.state.actor='lee';
 const before=JSON.stringify(h.ctx.state),html=h.run('bridgeCard(state.bridge.issues[0])');
 assert.match(html,/condition-chip-attention accountability-for-you">For you/);assert.match(html,/Information requested/);assert.match(html,/Requested information/);assert.match(html,/Which scope did participants test/);assert.match(html,/Next response · Lee/);assert.doesNotMatch(html,/Next response · Sam|SIMULATION —|condition-chip-success/);assert.match(html,/condition-chip-reference">Simulation/);
 i.body.status='resolved';i.body.resolution={actor:'alex',at:'2026-11-20T17:00:00Z'};const closed=h.run('bridgeCard(state.bridge.issues[0])');assert.match(closed,/condition-chip-reference">Resolved/);assert.doesNotMatch(closed,/For you|condition-chip-success|Information requested/);assert.match(closed,/Decided by Alex/);assert.match(closed,/data-action="bridge-open" data-id="ISSUE-1"/);
 i.body.status='awaiting-decision';i.body.resolution=null;assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(h.calls.length,0);
});

function primaryRecordText(html){return html.replace(/<details class="record-metadata">[\s\S]*?<\/details>/g,'').replace(/<[^>]*>/g,'');}
test('review cards and packet selectors use readable names while exact IDs remain in source metadata and control values',()=>{
 const h=harness(),i=issue(h),c=caseFor(h,i);h.ctx.rows=[c];
 const before=JSON.stringify(h.ctx.state),html=h.run('bridgeRequirementReviewCases(rows)'),primary=primaryRecordText(html);
 assert.match(primary,/Show a cue/);assert.match(primary,/Resume work · v1/);assert.doesNotMatch(primary,/CASE:v3|REQ:v1/);assert.match(html,/data-action="case" data-id="CASE"/);assert.match(html,/CASE:v3/);assert.match(html,/REQ:v1/);
 h.ctx.state.packets=[{id:'PKT-INTERNAL',revision:4,purpose:'Published study',audience_scopes:['project:demo'],records:[]}];h.ctx.issue=i;
 const fields=h.run('bridgeSelectionFields(issue)');assert.match(fields,/value="PKT-INTERNAL\|4"/);assert.match(primaryRecordText(fields),/Published study[\s\S]*Version 4/);assert.doesNotMatch(primaryRecordText(fields),/PKT-INTERNAL/);
 h.ctx.state.packets=[];assert.equal(JSON.stringify(h.ctx.state),before);
});
test('business intent source labels keep readable title and version but submit the unchanged exact source reference',async()=>{
 const h=harness(),i=issue(h,'open','intent');h.ctx.state.records.push({kind:'contribution',ref:{id:'CON-INTERNAL',revision:3},body:{title:'Observed handoff',domain:'Research',text:'Bounded finding'}});i.body.basis=[{id:'CON-INTERNAL',revision:3}];i.basis_records=[h.ctx.state.records.at(-1)];h.ctx.state.records.push({kind:'intent',ref:{id:'INT-BASE',revision:1},body:{text:'Published business direction'}});h.ctx.issue=i;
 h.run('bridgeIntentForm(issue)');const dialog=h.dialogs.at(-1),html=dialog[1];assert.match(html,/value="CON-INTERNAL:v3"/);assert.match(primaryRecordText(html),/Research · Observed handoff · v3/);assert.doesNotMatch(primaryRecordText(html),/CON-INTERNAL/);
 await dialog[3](new Map([['source','CON-INTERNAL:v3'],['field','value'],['proposed_value','Refine the thesis'],['rationale','New bounded evidence']]));
 assert.equal(h.calls[0].a,'bridge-intent-propose');assert.equal(h.calls[0].data.source.id,'CON-INTERNAL');assert.equal(h.calls[0].data.source.revision,3);
});
test('superseded review inputs show versions without escaped reference markup or IDs in primary copy',()=>{
 const h=harness();h.ctx.basis={purpose:'historical',superseded:[{selected:{id:'POL-INTERNAL',revision:1},current:{id:'POL-INTERNAL',revision:2}}]};
 const html=h.run('bridgeIntegrityBasis(basis)'),primary=primaryRecordText(html);assert.match(primary,/Policy · v1 → Policy · v2/);assert.doesNotMatch(primary,/POL-INTERNAL|&lt;span|data-record-id/);assert.match(html,/POL-INTERNAL:v1/);assert.match(html,/POL-INTERNAL:v2/);
});

function decisionComposerHarness({configured=true,messages=[]}={}){
 const h=harness(),drafts=new Map();h.ctx.state.project={id:'PROJECT-A',version:1};
 h.nodes.set('#modal-title',{classList:{add(){}},innerHTML:''});
 const key=(surface,scope='')=>[h.ctx.state.project.id,h.ctx.state.actor,surface,scope].join('|');
 h.ctx.reviewerDraftKey=key;h.ctx.reviewerDraftRead=(surface,scope)=>drafts.get(key(surface,scope))||'';
 h.ctx.reviewerDraftWrite=(surface,text,scope)=>drafts.set(key(surface,scope),text);
 h.ctx.reviewerDraftWriteKey=(bound,text)=>drafts.set(bound,text);
 h.ctx.reviewerDraftCapture=()=>{const input=h.nodes.get('#decision-review-question');if(input?.boundKey)drafts.set(input.boundKey,input.value);};
 const originalModal=h.ctx.modal;
 h.ctx.modal=(...args)=>{
  originalModal(...args);const html=args[1],listeners=new Map();
  const input={boundKey:html.match(/data-reviewer-draft-key="([^"]+)"/)?.[1],value:html.match(/<textarea[^>]*id="decision-review-question"[^>]*>([\s\S]*?)<\/textarea>/)?.[1]||'',addEventListener:(name,fn)=>listeners.set(name,fn),listeners};
  input.getAttribute=name=>name==='data-reviewer-draft-key'?input.boundKey:null;
  h.nodes.set('#decision-review-question',input);
 };
 h.ctx.crypto={randomUUID:()=> 'request-synthetic'};
 h.ctx.command=async(a,data)=>{h.calls.push({a,data});return a==='decision-integrity-read'?{title:'Which cue?',private:true,configured,thread:{id:'THREAD',revision:1},messages}:{message:'Response saved',decisionReviewIssue:data.expected.id};};
 h.type=text=>{const input=h.nodes.get('#decision-review-question');input.value=text;input.listeners.get('input')?.();};
 h.drafts=drafts;return h;
}
test('private decision composer stays visible and editable while a response is pending',async()=>{
 const h=decisionComposerHarness({messages:[{question:'Earlier question',status:'pending',citations:[],catalog:{},mode:'live'}]}),i=issue(h);
 await h.ctx.openDecisionReview(i);const dialog=h.dialogs.at(-1),textarea=dialog[1].match(/<textarea[^>]*id="decision-review-question"[^>]*>/)[0];
 assert.match(dialog[1],/<span>You<\/span><textarea[^>]*rows="4"/);assert.match(dialog[1],/class="integrity-review-name">AI partner/);
 assert.doesNotMatch(textarea,/disabled|readonly/);assert.equal(dialog[2],'Ask');assert.equal(h.nodes.get('#modal-form button[type="submit"]').disabled,true);
 h.type('My next question');await assert.rejects(dialog[3](new Map([['question','My next question']])),/still pending/);
 assert.equal(h.ctx.reviewerDraftRead('decision',i.ref.id),'My next question');assert.deepEqual(h.calls.map(c=>c.a),['decision-integrity-read']);
});
test('unconfigured private review preserves its four-row question area without enabling paid submission',async()=>{
 const h=decisionComposerHarness({configured:false}),i=issue(h);await h.ctx.openDecisionReview(i);
 const dialog=h.dialogs.at(-1);assert.match(dialog[1],/rows="4"/);assert.equal(dialog[2],'Ask');assert.equal(h.nodes.get('#modal-form button[type="submit"]').disabled,true);
 h.type('Save this question for later');await h.ctx.openDecisionReview(i);
 assert.match(h.dialogs.at(-1)[1],/>Save this question for later<\/textarea>/);
 assert.equal(h.calls.filter(c=>c.a==='decision-integrity-send').length,0);
});
test('decision drafts survive close and reopen while remaining isolated by issue, actor and project',async()=>{
 const h=decisionComposerHarness(),i=issue(h);await h.ctx.openDecisionReview(i);h.type('Keep this private question');
 h.nodes.delete('#decision-review-question');await h.ctx.openDecisionReview(i);assert.match(h.dialogs.at(-1)[1],/>Keep this private question<\/textarea>/);
 const other={...i,ref:{id:'ISSUE-2',revision:1}};await h.ctx.openDecisionReview(other);assert.doesNotMatch(h.dialogs.at(-1)[1],/>Keep this private question<\/textarea>/);
 h.ctx.state.actor='lee';await h.ctx.openDecisionReview(i);assert.doesNotMatch(h.dialogs.at(-1)[1],/>Keep this private question<\/textarea>/);
 h.ctx.state.actor='alex';h.ctx.state.project.id='PROJECT-B';await h.ctx.openDecisionReview(i);assert.doesNotMatch(h.dialogs.at(-1)[1],/>Keep this private question<\/textarea>/);
 h.ctx.state.project.id='PROJECT-A';await h.ctx.openDecisionReview(i);assert.match(h.dialogs.at(-1)[1],/>Keep this private question<\/textarea>/);
 assert.equal(h.calls.filter(c=>c.a!=='decision-integrity-read').length,0);
});
test('successful decision send preserves a next question typed in flight and serializes duplicate sends',async()=>{
 const h=decisionComposerHarness(),i=issue(h);await h.ctx.openDecisionReview(i);h.type('First question');
 const dialog=h.dialogs.at(-1);let finish;
 h.ctx.command=(a,data)=>{h.calls.push({a,data});return a==='decision-integrity-send'?new Promise(resolve=>{finish=resolve;}):Promise.resolve({title:'Which cue?',configured:true,thread:{id:'THREAD',revision:2},messages:[]});};
 const sent=dialog[3](new Map([['question','First question']]));h.type('Follow-up question');
 await assert.rejects(dialog[3](new Map([['question','Follow-up question']])),/still pending/);
 finish({message:'Response saved'});await sent;assert.equal(h.ctx.reviewerDraftRead('decision',i.ref.id),'Follow-up question');
 const send=h.calls.find(c=>c.a==='decision-integrity-send');assert.equal(send.data.question,'First question');assert.equal(send.data.expected.id,i.ref.id);assert.equal(send.data.expected.revision,1);assert.equal(send.data.consent,true);
 assert.equal(h.calls.filter(c=>c.a==='decision-integrity-send').length,1);
 await h.ctx.openDecisionReview(i);assert.match(h.dialogs.at(-1)[1],/>Follow-up question<\/textarea>/);
});
test('failed decision send retains the question and exact issue basis for retry',async()=>{
 const h=decisionComposerHarness(),i=issue(h);await h.ctx.openDecisionReview(i);h.type('Question that must survive');
 h.ctx.command=async(a,data)=>{h.calls.push({a,data});if(a==='decision-integrity-send')throw Error('Connection interrupted');return {title:'Which cue?',configured:true,thread:{id:'THREAD',revision:2},messages:[]};};
 await assert.rejects(h.dialogs.at(-1)[3](new Map([['question','Question that must survive']])),/Connection interrupted/);
 assert.equal(h.ctx.reviewerDraftRead('decision',i.ref.id),'Question that must survive');await h.ctx.openDecisionReview(i);
 assert.match(h.dialogs.at(-1)[1],/>Question that must survive<\/textarea>/);assert.ok(h.calls.every(c=>c.data.expected.id===i.ref.id&&c.data.expected.revision===1));
 assert.equal(h.calls.filter(c=>c.a==='decision-integrity-send').length,1);
});
test('a switched actor cannot submit or receive the earlier actor private review dialog',async()=>{
 const h=decisionComposerHarness(),i=issue(h);await h.ctx.openDecisionReview(i);const oldDialog=h.dialogs.at(-1);h.type('Alex private draft');
 h.ctx.state.actor='lee';await assert.rejects(oldDialog[3](new Map([['question','Alex private draft']])),/context changed/);assert.equal(h.calls.filter(c=>c.a==='decision-integrity-send').length,0);
 let finish;h.ctx.command=()=>new Promise(resolve=>{finish=resolve;});const loading=h.ctx.openDecisionReview(i),count=h.dialogs.length;
 h.ctx.state.actor='sam';finish({title:'Lee private response',configured:true,thread:null,messages:[]});await loading;
 assert.equal(h.dialogs.length,count);
});

test('successful unchanged question clears once and cannot be recaptured when the dialog reopens',async()=>{
 const h=decisionComposerHarness(),i=issue(h);await h.ctx.openDecisionReview(i);h.type('Question to send');
 await h.dialogs.at(-1)[3](new Map([['question','Question to send']]));
 assert.equal(h.ctx.reviewerDraftRead('decision',i.ref.id),'');assert.equal(h.nodes.get('#decision-review-question').value,'');
 await h.ctx.openDecisionReview(i);assert.match(h.dialogs.at(-1)[1],/placeholder="Ask your AI partner"><\/textarea>/);
 assert.equal(h.calls.filter(c=>c.a==='decision-integrity-send').length,1);
});

function inlineDecisionFixture(options={}){
 const h=decisionComposerHarness(options),i=issue(h);i.rights={can_decide:true};h.ctx.selected=i.ref.id;
 const bound=h.ctx.reviewerDraftKey('decision',i.ref.id),input={value:'',getAttribute:name=>name==='data-reviewer-draft-key'?bound:null,focus(){}};
 h.nodes.set('#decision-inline-question',input);
 h.typeInline=text=>{input.value=text;h.ctx.reviewerDraftWrite('decision',text,i.ref.id);};
 return {...h,i,input};
}
test('decision rail has an always-visible four-row composer while the full dialogue is optional',()=>{
 const h=inlineDecisionFixture();h.ctx.state.coaching={model:{configured:false}};
 const html=h.ctx.bridgeDecisionReviewEntry(h.i);assert.match(html,/<span>You<\/span><textarea[^>]*id="decision-inline-question"[^>]*rows="4"/);
 assert.match(html,/data-action="bridge-decision-inline-ask"[^>]*disabled>Ask/);assert.match(html,/data-action="bridge-decision-review"[^>]*>Conversation &amp; evidence/);
 const textarea=html.match(/<textarea[^>]*id="decision-inline-question"[^>]*>/)[0];assert.doesNotMatch(textarea,/disabled|readonly/);
 assert.match(html,/Asking does not approve or change anything/);assert.equal(h.calls.length,0);
});
test('ordinary decision Ask uses exact read-send-read boundaries and returns the latest response inline',async()=>{
 const h=inlineDecisionFixture();h.typeInline('What evidence is missing?');let reads=0,renders=0;
 h.ctx.render=()=>{renders++;};h.ctx.command=async(a,data)=>{h.calls.push({a,data});if(a==='decision-integrity-send')return {saved:true,decisionReviewIssue:h.i.ref.id};return {configured:true,thread:{id:'THREAD',revision:++reads},messages:reads===1?[]:[{question:'What evidence is missing?',reply:'Verify <ownership>.',status:'complete',citations:[],catalog:{},mode:'live'}]};};
 await h.ctx.askDecisionInline(h.i);const html=h.ctx.bridgeDecisionReviewEntry(h.i);
 assert.deepEqual(h.calls.map(c=>c.a),['decision-integrity-read','decision-integrity-send','decision-integrity-read']);
 assert.ok(h.calls.every(c=>c.data.expected.id===h.i.ref.id&&c.data.expected.revision===1));assert.equal(h.calls[1].data.consent,true);assert.equal(h.calls[1].data.question,'What evidence is missing?');assert.equal(h.calls[1].data.thread.revision,1);
 assert.match(html,/class="integrity-review-name">AI partner/);assert.match(html,/Verify &lt;ownership>/);assert.doesNotMatch(html,/<ownership>/);
 assert.equal(h.ctx.reviewerDraftRead('decision',h.i.ref.id),'');assert.equal(h.input.value,'');assert.equal(h.dialogs.length,0);assert.equal(renders,0);
});
test('inline decision send serializes requests and keeps a next question typed while waiting',async()=>{
 const h=inlineDecisionFixture();h.typeInline('First question');let finish,reads=0;
 h.ctx.command=(a,data)=>{h.calls.push({a,data});if(a==='decision-integrity-send')return new Promise(resolve=>{finish=resolve;});return Promise.resolve({configured:true,thread:{id:'THREAD',revision:++reads},messages:reads===1?[]:[{question:'First question',reply:'Inspect the recorded source.',status:'complete',citations:[],catalog:{}}]});};
 const request=h.ctx.askDecisionInline(h.i);await new Promise(setImmediate);h.typeInline('Next question');await h.ctx.askDecisionInline(h.i);
 assert.equal(h.calls.filter(c=>c.a==='decision-integrity-send').length,1);finish({saved:true});await request;
 assert.equal(h.ctx.reviewerDraftRead('decision',h.i.ref.id),'Next question');assert.equal(h.input.value,'Next question');assert.equal(h.dialogs.length,0);
 assert.match(h.ctx.bridgeDecisionReviewEntry(h.i),/Inspect the recorded source/);
});
test('inline pending or unavailable reviews retain the question and never send another model request',async()=>{
 for(const configured of [true,false]){
  const h=inlineDecisionFixture();h.typeInline('Keep this question');h.ctx.command=async(a,data)=>{h.calls.push({a,data});return {configured,thread:{id:'THREAD',revision:1},messages:configured?[{question:'Earlier question',reply:'',status:'pending',citations:[],catalog:{}}]:[]};};
  await h.ctx.askDecisionInline(h.i);const html=h.ctx.bridgeDecisionReviewEntry(h.i);
  assert.deepEqual(h.calls.map(c=>c.a),['decision-integrity-read']);assert.equal(h.ctx.reviewerDraftRead('decision',h.i.ref.id),'Keep this question');
  assert.match(html,/data-action="bridge-decision-inline-ask"[^>]*disabled>Ask/);assert.equal(h.dialogs.length,0);
 }
});
test('inline decision errors remain inline and retain the exact question and issue version',async()=>{
 const h=inlineDecisionFixture();h.typeInline('Question to retry');h.ctx.command=async(a,data)=>{h.calls.push({a,data});if(a==='decision-integrity-send')throw Error('Connection interrupted');return {configured:true,thread:{id:'THREAD',revision:3},messages:[]};};
 await h.ctx.askDecisionInline(h.i);assert.match(h.ctx.bridgeDecisionReviewEntry(h.i),/Connection interrupted/);
 assert.equal(h.ctx.reviewerDraftRead('decision',h.i.ref.id),'Question to retry');assert.equal(h.input.value,'Question to retry');assert.equal(h.dialogs.length,0);
 assert.ok(h.calls.every(c=>c.data.expected.id===h.i.ref.id&&c.data.expected.revision===1));assert.deepEqual(h.calls.map(c=>c.a),['decision-integrity-read','decision-integrity-send']);
});
test('inline review stops before sending when the actor or exact target changes during context preparation',async()=>{
 for(const change of ['actor','target','selection']){
  const h=inlineDecisionFixture();h.typeInline('Keep the original question');let finish;
  h.ctx.command=(a,data)=>{h.calls.push({a,data});return new Promise(resolve=>{finish=resolve;});};
  const request=h.ctx.askDecisionInline(h.i);
  if(change==='actor')h.ctx.state.actor='lee';else if(change==='target')h.i.ref={id:h.i.ref.id,revision:2};else h.ctx.selected='OTHER-ISSUE';
  finish({configured:true,thread:{id:'THREAD',revision:1},messages:[]});await request;
  assert.deepEqual(h.calls.map(c=>c.a),['decision-integrity-read']);assert.equal(h.calls[0].data.expected.revision,1);assert.equal(h.dialogs.length,0);
 }
});

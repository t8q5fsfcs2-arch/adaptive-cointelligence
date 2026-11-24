const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');

function harness(){
 const esc=value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const ctx={
  state:{actor:'lee',actors:{lee:{name:'Lee'},sam:{name:'Sam'},alex:{name:'Alex'},priya:{name:'Priya'}},bridge:{boards:{'research-design':'Research · Design'},issues:[],timeline:{entries:[]}},cases:[],packets:[],records:[],intake:{cases:[]},project_flow:{requests:[]}},
  selected:null,earlierTimeline:null,esc,
  packetKey:r=>r.id+'|'+r.revision,label:r=>r.id+':v'+r.revision,packetTitle:r=>r.purpose,
  ref:r=>esc(r.id+':v'+r.revision),date:value=>value,
  para:value=>`<p>${esc(value)}</p>`,val:(title,value)=>`<p>${esc(title)}: ${esc(value)}</p>`,
  button:(title,action,id='',cls='')=>`<button class="${cls}" data-action="${action}" data-id="${esc(id)}">${esc(title)}</button>`,
  findCase:id=>ctx.state.cases.find(r=>r.ref.id===id),get:id=>ctx.state.records.find(r=>r.ref.id===id),records:kind=>ctx.state.records.filter(r=>r.kind===kind),
  recordedDate:(title,at)=>`${title} · ${esc(at||'Date not recorded')}`,
 };
 vm.createContext(ctx);
 const app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');vm.runInContext(app.slice(app.indexOf('function recordedDate('),app.indexOf('\nasync function load(')),ctx);vm.runInContext(app.match(/^const ref=.*$/m)[0].replace('const ref=','ref='),ctx);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/signals.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/bridge.js'),'utf8'),ctx);
 return {ctx,run:source=>vm.runInContext(source,ctx)};
}

function issue(h,status='open'){
 const r={ref:{id:'ISSUE',revision:3},body:{title:'Confirm the evidence cue',question:'Which cue should be used?',next_question:'The earlier broad question',next_owner:'sam',owner:'sam',decision_owner:'alex',status,route:'requirement',boards:['research-design'],packet_refs:[{id:'SHARED',revision:2}],requirement_refs:[{id:'REQ',revision:1}],consequence:'Avoid repeating work'},changed:[]};
 h.ctx.state.bridge.issues.push(r);
 h.ctx.state.records.push({ref:{id:'REQ',revision:1},kind:'requirement',body:{title:'Resume safely',text:'Show the saved cue'}});
 return r;
}

function review(h,i){
 const r={ref:{id:'CASE',revision:4},body:{status:'pending-review',target:{id:'REQ',revision:1},decision_owner:'alex',required_reviews:{sam:'supported-with-limits',lee:'cleared-with-conditions'},proposal:{text:'Make the cue visible'}},target_record:h.ctx.state.records[0],stale:[],reviews:{},ready:true};
 h.ctx.state.cases.push(r);
 if(i)i.body.linked={kind:'requirement',ref:r.ref};
 return r;
}

test('an open information request routes its exact question and responder instead of the previous assignment',()=>{
 const h=harness(),i=issue(h,'awaiting-decision');review(h,i);
 i.body.information_request={status:'open',owner:'lee',question:'Which cue did participants actually test?'};
 const before=JSON.stringify(h.ctx.state);
 const item=h.run('bridgeTimelineStatus()[0]');
 assert.equal(item.owner,'lee');assert.equal(item.next,i.body.information_request.question);
 h.ctx.item=item;
 const html=h.run('accountabilityRow(item)');
 assert.match(html,/<dt>Next response<\/dt><dd>Lee<\/dd>/);
 assert.doesNotMatch(html.slice(0,html.indexOf('</summary>')),/Next response · Lee/);
 assert.match(html,/Requested information[\s\S]+Which cue did participants actually test/);
 assert.match(html,/Why this is waiting[\s\S]+answer or explicit withdrawal/);
 assert.match(html,/data-action="bridge-answer" data-id="ISSUE"/);
 assert.doesNotMatch(html,/earlier broad question|data-action="bridge-decide"/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});

test('missing responder stays unassigned instead of borrowing the issue owner',()=>{
 const h=harness(),i=issue(h);
 i.body.information_request={status:'open',question:'Who can supply this source?'};
 h.ctx.item=h.run('bridgeTimelineStatus()[0]');
 assert.equal(h.ctx.item.owner,undefined);
 assert.match(h.run('accountabilityRow(item)'),/Owner unassigned/);
 assert.doesNotMatch(h.run('accountabilityRow(item)'),/Next response · Sam/);
});

test('active delegation controls the next decision and existing action without promoting the original decider',()=>{
 const h=harness(),i=issue(h,'awaiting-decision'),c=review(h,i);
 i.rights={active_decider:'lee',can_decide:true};c.rights={active_decider:'lee',can_decide:true};
 h.ctx.item=h.run('bridgeTimelineStatus()[0]');
 assert.equal(h.ctx.item.owner,'lee');
 assert.match(h.run('accountabilityContext(item)'),/data-action="bridge-decide"/);
 i.rights.can_decide=false;c.rights.can_decide=false;h.ctx.state.actor='alex';
 assert.doesNotMatch(h.run('accountabilityContext(item)'),/data-action="bridge-decide"/);
});

test('changed policy takes precedence over an old request and suppresses decision shortcuts',()=>{
 const h=harness(),i=issue(h,'awaiting-decision'),c=review(h,i);
 i.body.information_request={status:'open',owner:'sam',question:'An older request'};
 i.rights={changed:true,current_decider:'lee',active_decider:'alex',can_decide:false};
 c.rights={changed:true,can_decide:false};
 h.ctx.item=h.run('bridgeTimelineStatus()[0]');
 assert.equal(h.ctx.item.owner,'lee');
 assert.equal(h.ctx.item.requestLabel,'Requested response');
 assert.match(h.run('accountabilityRow(item)'),/recorded decision policy changed/);
 assert.doesNotMatch(h.run('accountabilityContext(item)'),/data-action="bridge-decide"/);
});

test('an explicit escalation shows the recorded responder and reason without a deadline',()=>{
 const h=harness(),i=issue(h,'awaiting-decision');
 i.rights={escalation:{status:'open',owner:'lee',reason:'Confirm coverage while the owner is unavailable.'}};
 h.ctx.item=h.run('bridgeTimelineStatus()[0]');
 assert.equal(h.ctx.item.owner,'lee');
 const html=h.run('accountabilityRow(item)');
 assert.match(html,/Confirm coverage while the owner is unavailable/);
 assert.match(html,/An escalation response is still needed/);
 assert.doesNotMatch(html,/overdue|due by|tomorrow/i);
});

test('brief request and acceptance preserve separate assignment and publication meanings',()=>{
 const h=harness();
 h.ctx.state.project_flow.requests=[{ref:{id:'WORK',revision:1},body:{title:'Investigate the cue',status:'requested',requested_by:'sam',recipient:'lee',expected_output:'Evidence from the selected task'},changed:[],published_outputs:[]}];
 const before=JSON.stringify(h.ctx.state);
 let item=h.run('bridgeTimelineStatus({includeAccepted:true})[0]');h.ctx.item=item;
 assert.equal(item.owner,'lee');assert.equal(item.attention,true);
 assert.match(h.run('accountabilityRow(item)'),/has not accepted this assignment/);
 assert.match(h.run('accountabilityRow(item)'),/does not publish work or approve requirements/);
 assert.equal(JSON.stringify(h.ctx.state),before);
 h.ctx.state.project_flow.requests[0].body.status='accepted';
 item=h.run('bridgeTimelineStatus({includeAccepted:true})[0]');h.ctx.item=item;
 assert.equal(item.attention,false);assert.equal(item.waitingReason,'');
 assert.match(h.run('accountabilityRow(item)'),/Expected output[\s\S]+Evidence from the selected task/);
 assert.match(h.run('accountabilityRow(item)'),/Assignment accepted; no published output is linked yet/);
 h.ctx.state.project_flow.requests[0].published_outputs=[{ref:{id:'RELEASE',revision:1}}];
 assert.equal(h.run('bridgeTimelineStatus({includeAccepted:true}).length'),0);
});

test('required responses use actual recorded reviewers and preserve non-clearing review status',()=>{
 const h=harness();issue(h,'resolved');const c=review(h);c.ready=false;
 c.reviews.sam={body:{disposition:'supported-with-limits'}};
 c.reviews.lee={body:{disposition:'concerns-remain'}};
 h.ctx.item=h.run('bridgeTimelineStatus()[0]');
 assert.deepEqual(Array.from(h.ctx.item.owner),['lee']);
 assert.match(h.run('accountabilityRow(item)'),/Required responses from Lee have not yet cleared this review/);
 assert.doesNotMatch(h.run('accountabilityRow(item)'),/required domain responses are recorded|Requested decision/);
 c.stale=[{id:'SOURCE',revision:2}];
 h.ctx.item=h.run('bridgeTimelineStatus()[0]');
 assert.match(h.run('accountabilityRow(item)'),/refers to changed source versions/);
 assert.doesNotMatch(h.run('accountabilityContext(item)'),/data-action="decision-form"/);
});

test('direction review never invents a sponsor and distinguishes publication from build authorization',()=>{
 const h=harness();
 h.ctx.state.intake.cases=[{ref:{id:'DIRECTION',revision:1},body:{status:'pending-review',snapshot:{title:'Investigate the cue'},reviewers:[]},ready:true}];
 h.ctx.item=h.run('bridgeSponsorGates()[0]');
 assert.equal(h.ctx.item.owner,undefined);
 const html=h.run('accountabilityRow(item)');
 assert.match(html,/Owner unassigned/);
 assert.match(html,/Requested decision[\s\S]+publish the reviewed direction/);
 assert.match(html,/does not approve requirements or authorize development/);
 assert.doesNotMatch(html,/Next response · Priya/);
 h.ctx.state.intake.cases[0].rights={active_decider:'lee'};
 assert.equal(h.run('bridgeSponsorGates()[0].owner'),'lee');
});

test('related requirements unfold as named links while response and exact packet actions stay visible',()=>{
 const h=harness(),i=issue(h,'awaiting-decision');review(h,i);
 i.body.information_request={status:'open',owner:'lee',question:'Confirm the selected evidence.'};
 i.body.requirement_refs.push({id:'REQ',revision:1});
 for(let n=2;n<=10;n++){
  i.body.requirement_refs.push({id:'REQ-'+n,revision:1});
  h.ctx.state.records.push({ref:{id:'REQ-'+n,revision:1},body:{title:'Related requirement '+n}});
 }
 h.ctx.state.packets=[{id:'SHARED',revision:1,purpose:'Earlier evidence'},{id:'SHARED',revision:2,purpose:'Released findings <script>'},{id:'PRIVATE',revision:1,purpose:'Private draft'}];
 h.ctx.item=h.run('bridgeTimelineStatus()[0]');
 const html=h.run('accountabilityContext(item)');
 const primary=html.match(/<div class="workflow-card-actions">([\s\S]*?)<\/div>/)[1];
 for(const action of ['bridge-answer','bridge-open','packet'])assert.match(primary,new RegExp('data-action="'+action+'"'));
 assert.match(primary,/data-action="packet" data-id="SHARED\|2"/);
 assert.match(primary,/Inspect Released findings &lt;script>/);
 assert.doesNotMatch(primary,/data-action="requirement"/);
 assert.match(html,/<\/div><details><summary>Related requirements \(10\)<\/summary>/);
 assert.doesNotMatch(html,/<details[^>]*\bopen\b/);
 assert.match(html,/<a href="#main" class="item-title-link" data-action="requirement" data-id="REQ">Resume safely<\/a>/);
 assert.match(html,/data-id="REQ-10">Related requirement 10<\/a>/);
 assert.equal((html.match(/data-action="requirement"/g)||[]).length,10);
 assert.doesNotMatch(html,/<button[^>]+data-action="requirement"/);
 assert.doesNotMatch(html,/SHARED\|1|PRIVATE|Private draft|<script>/);
 i.body.requirement_refs=[];
 assert.doesNotMatch(h.run('accountabilityContext(item)'),/Related requirements/);
});

test('project timeline stays first with its existing compact team links and recorded history',()=>{
 const h=harness();
 h.ctx.projectTeamTimeline=()=>'<div class="team-timeline"><a data-team-timeline-key="research">Research</a><a data-team-timeline-key="design">Design</a></div>';
 const before=JSON.stringify(h.ctx.state),html=h.run('bridgeTimelineScreen()');
 assert.ok(html.indexOf('id="project-timeline-title"')<html.indexOf('Status now'));
 assert.ok(html.indexOf('Status now')<html.indexOf('Recorded event history'));
 assert.match(html,/class="team-timeline"[\s\S]+data-team-timeline-key="research"[\s\S]+data-team-timeline-key="design"/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});

test('the attention preview keeps the requested response and expands the waiting reason without making uncertainty a blocker',()=>{
 const h=harness(),i=issue(h);
 i.body.information_request={status:'open',owner:'lee',question:'Which participant observation supports the routing rule?'};
 h.ctx.item=h.run('bridgeTimelineStatus()[0]');
 const html=h.run('accountabilityRow(item)'),summary=html.match(/<summary>([\s\S]*?)<\/summary>/)[1];
 assert.match(summary,/Requested information[\s\S]*Which participant observation supports the routing rule/);
 assert.doesNotMatch(summary,/Why waiting/);
 assert.match(html,/Why this is waiting[\s\S]*answer or explicit withdrawal/);
 assert.match(html,/data-signal="attention"/);
 assert.doesNotMatch(html,/data-signal="critical"|accountability-item-alert/);
 i.changed=[{id:'SOURCE',revision:2}];
 h.ctx.item=h.run('bridgeTimelineStatus()[0]');
 const changed=h.run('accountabilityRow(item)');
 assert.match(changed,/data-signal="advisory"/);
 assert.match(changed,/accountability-item-alert[\s\S]*aria-hidden="true">⚠/);
 assert.doesNotMatch(changed,/data-signal="critical"/);
});

test('one Updates disclosure preserves both the project snapshot and native exact update actions',()=>{
 const h=harness();
 h.ctx.projectUpdateFeed=()=>'<details class="project-update-feed"><summary>Updates · 2 new</summary><div class="project-update-items"><button data-action="pflow-update" data-id="EVENT-2">Exact changed requirement</button><details><summary>Earlier updates</summary><button data-action="pflow-update" data-id="EVENT-1">Earlier event</button></details></div></details>';
 const before=JSON.stringify(h.ctx.state),html=h.run('bridgeUpdatesControl()');
 assert.equal((html.match(/class="project-update-feed"/g)||[]).length,1);
 assert.match(html,/Project update summary[\s\S]*data-id="work"[\s\S]*data-id="activity"/);
 assert.match(html,/data-action="pflow-update" data-id="EVENT-2"/);
 assert.match(html,/Earlier updates[\s\S]*data-id="EVENT-1"/);
 assert.doesNotMatch(html,/project-update-alert|role="alert"/);
 assert.equal(JSON.stringify(h.ctx.state),before);
});

test('overview timeline and activity share explicit chips while retaining named responders and exact tasks',()=>{
 const h=harness();h.ctx.item={kind:'direction-review',id:'DISPLAY',title:'SIMULATION — Clarify the boundary',status:'Decision rights changed',owner:['lee','sam'],attention:true,next:'Which exact boundary applies?',requestLabel:'Requested response',waitingReason:'The recorded policy changed.',where:'Business Intent',submitted_at:'2026-11-20T17:00:00Z',since:'2026-11-20T18:00:00Z',action:'<button>Open review</button>'};
 const before=JSON.stringify(h.ctx.state),indication=h.run('bridgeItemIndication(item)'),overview=h.run('accountabilityRow(item)'),now=h.run('bridgeStatusNowRow(item)'),activity=h.run('bridgeStatusRow(item,true)');
 for(const html of [overview,now,activity]){assert.match(html,/condition-chip-advisory/);assert.match(html,/Clarify the boundary/);assert.doesNotMatch(html,/SIMULATION —/);assert.match(html,/Which exact boundary applies/);assert.match(html,/Open review/);assert.match(html,/2026-11-20/);}
 assert.ok(now.includes(indication.chips));assert.ok(activity.includes(indication.chips));
 const summary=overview.slice(0,overview.indexOf('</summary>'));assert.doesNotMatch(summary,/For you|Next response · Lee|Lee, Sam/);
 assert.match(overview,/<dt>Next response<\/dt><dd>Lee, Sam<\/dd>/);assert.match(now,/<dt>Next response<\/dt><dd>Lee, Sam<\/dd>/);assert.match(activity,/Business Intent/);assert.match(activity,/Waiting since/);
 assert.match(indication.chips,/condition-chip-advisory/);assert.match(indication.chips,/condition-chip-reference">Simulation/);assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(h.ctx.item.title,'SIMULATION — Clarify the boundary');
 h.ctx.item.status='Urgent-sounding unfamiliar wording';h.ctx.item.owner=[];
 const unknown=h.run('bridgeItemIndication(item).chips');assert.doesNotMatch(unknown,/condition-chip-advisory|condition-chip-critical/);assert.match(unknown,/condition-chip-reference/);
});

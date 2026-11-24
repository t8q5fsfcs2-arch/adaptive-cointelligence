const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function harness(){
 const dialogs=[],esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),label=r=>r.id+':v'+r.revision;
 const ctx={state:{packets:[],edges:[],records:[]},esc,label,ref:r=>esc(label(r)),tag:t=>esc(t),para:s=>`<p>${esc(s)}</p>`,val:(t,v)=>`<label>${esc(t)}</label><p>${esc(v)}</p>`,button:(t,a,id)=>`<button data-action="${esc(a)}" data-id="${esc(id)}">${esc(t)}</button>`,head:(t,s,a='')=>`<h1>${esc(t)}</h1><p>${esc(s)}</p>${a}`,modal:(...args)=>dialogs.push(args)};
 vm.createContext(ctx);require('./ui_reference_helpers.cjs')(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/packets.js'),'utf8'),ctx);
 return {ctx,dialogs,run:s=>vm.runInContext(s,ctx)};
}
function packet(){return {id:'PKT-CON-1',revision:1,purpose:'Design handoff',audience_scopes:['project:demo'],refs:[{id:'CON-1',revision:1},{id:'REQ-1',revision:1}],records:[{ref:{id:'CON-1',revision:1},kind:'contribution',body:{title:'Research finding',text:'Original observation',interpretation:'Tentative interpretation',limitation:'Small sample',status:'published-for-review',recipient:'design',handoff:{intent_implications:'Consider resumption',downstream_needs:'Test cues',open_questions:'Which cue?'},requirement_refs:[{id:'REQ-1',revision:1}]}},{ref:{id:'REQ-1',revision:1},kind:'requirement',body:{title:'Original requirement',goal_refs:[{id:'GOAL-1',revision:1}]}}],changed_refs:[{previous:{id:'REQ-1',revision:1},current:{id:'REQ-1',revision:2}}]};}
test('inspection preserves historical content and exposes version changes without substituting latest',()=>{
 const h=harness();h.ctx.state.packets=[packet()];h.ctx.state.records=[{ref:{id:'REQ-1',revision:2},body:{title:'New wording must not replace original'}}];h.run("inspectPacket('PKT-CON-1|1')");const html=h.dialogs[0][1];assert.match(html,/Original requirement/);assert.match(html,/REQ-1:v2/);assert.match(html,/Included records have changed/);assert.doesNotMatch(html,/New wording must not replace original/);
});
test('handoff meaning, open questions, audience and limits are visible in inspectable records',()=>{
 const h=harness();h.ctx.state.packets=[packet()];h.run("inspectPacket('PKT-CON-1|1')");const html=h.dialogs[0][1];for(const text of ['Project participants','Tentative interpretation','Small sample','Consider resumption','Test cues','Which cue?','published-for-review','Full saved record and lineage'])assert.ok(html.includes(text));assert.doesNotMatch(html,/<textarea|type="submit"/);
});
test('coverage makes missing goals and measures explicit without implicitly retrieving them',()=>{
 const h=harness();h.ctx.state.packets=[packet()];h.ctx.state.records=[{ref:{id:'GOAL-1',revision:1},body:{title:'Outside goal content'}}];h.run("inspectPacket('PKT-CON-1|1')");const html=h.dialogs[0][1];assert.match(html,/Goals<\/span><span class="caption">Not included/);assert.match(html,/Success measures<\/span><span class="caption">Not included/);assert.match(html,/GOAL-1:v1/);assert.match(html,/Outside this packet/);assert.doesNotMatch(html,/Outside goal content/);
});
test('relationships exclude unrelated records and retain exact source versions',()=>{
 const h=harness();h.ctx.p=packet();h.ctx.state.edges=[{from:{id:'OTHER',revision:1},to:{id:'SECRET',revision:1}},{from:{id:'CON-1',revision:2},to:{id:'NEW',revision:1}},{from:{id:'CON-1',revision:1},to:{id:'SOURCE',revision:1}}];const links=h.run('packetRelationships(p)');assert.ok(links.some(l=>l.to.id==='SOURCE'));assert.ok(!links.some(l=>['SECRET','NEW'].includes(l.to.id)));
});
test('hostile record and manifest text is escaped at every disclosure level',()=>{
 const h=harness(),p=packet();p.purpose='<img src=x onerror=evil>';p.records[0].body.handoff.open_questions='<script>evil</script>';h.ctx.state.packets=[p];h.run("inspectPacket('PKT-CON-1|1')");const html=h.dialogs[0][1];assert.match(html,/&lt;img/);assert.match(html,/&lt;script/);assert.doesNotMatch(html,/<script>|<img src/);
});
test('list groups versions without hiding older packets or choosing the wrong contribution version',()=>{
 const h=harness(),old=packet(),newer=structuredClone(old);newer.revision=2;newer.records[0].ref.revision=2;h.ctx.state.packets=[old,newer];h.ctx.record={ref:{id:'CON-1',revision:1}};assert.equal(h.run('packetGroups()[0][0].revision'),2);const html=h.run('packetsScreen()');assert.match(html,/Earlier packets \(1\)/);assert.match(html,/Inspect version 1/);assert.equal(h.run('packetLinkFor(record).revision'),1);
});
test('missing and empty packets have honest read-only states',()=>{
 const h=harness();assert.match(h.run('packetsScreen()'),/No evidence trail yet/);h.run("inspectPacket('MISSING|1')");assert.match(h.dialogs[0][1],/not available in the current project and role/);
});

test('prepared packets show a private audience and exact draft contents without implying release',()=>{
 const h=harness(),p=packet();p.id='PKT-PREP-H';p.audience_scopes=['domain:research','project:demo'];p.records[0].kind='contribution-draft';h.ctx.state.packets=[p];h.run("inspectPacket('PKT-PREP-H|1')");const html=h.dialogs[0][1];assert.match(html,/Research only/);assert.match(html,/Prepared and private/);assert.match(html,/Intended release: project participants/);assert.match(html,/Deliverable draft/);assert.doesNotMatch(html,/Research only, Project participants/);assert.match(h.run('packetsScreen()'),/Prepared · private/);
});
test('release receipts expose the prepared and released manifests and exact identity mapping',()=>{
 const h=harness(),p=packet();p.records.push({ref:{id:'RECEIPT',revision:1},kind:'packet-release',body:{status:'released-not-approved',prepared_packet:{id:'PKT-PREP-H',revision:1},published_packet:{id:p.id,revision:1},released_by:'sam',at:'synthetic time',reference_map:[{prepared:{id:'DRAFT',revision:2},released:{id:'CON-1',revision:1}}]}});p.refs.push({id:'RECEIPT',revision:1});h.ctx.state.packets=[p];h.run("inspectPacket('PKT-CON-1|1')");const html=h.dialogs[0][1];assert.match(html,/Packet release receipt/);assert.match(html,/Prepared → released reference mapping/);assert.match(html,/DRAFT:v2/);assert.match(html,/PKT-PREP-H:v1/);assert.match(html,/released-not-approved/);
});
test('sponsor draft records open the exact intake snapshot and distinguish proposed goals',()=>{
 const h=harness(),p=packet();p.records=[{ref:{id:'SPREF',revision:1},kind:'sponsor-preflight',body:{snapshot:{title:'Frozen intake'}}},{ref:{id:'G',revision:1},kind:'goal-draft',body:{title:'Goal',outcome:'Resume work'}}];p.refs=p.records.map(r=>r.ref);h.ctx.intakeSnapshot=b=>'SAVED SNAPSHOT '+b.title;h.ctx.state.packets=[p];h.run("inspectPacket('PKT-CON-1|1')");const html=h.dialogs[0][1];assert.match(html,/SAVED SNAPSHOT Frozen intake/);assert.match(html,/Goal draft/);assert.match(html,/Goals<\/span><span class="caption">Included/);
});

test('Design packet title identifies its own deliverable instead of an upstream Research input',()=>{
 const h=harness(),p=packet();p.id='PKT-PREP-H';p.records.push({ref:{id:'DESIGN-DRAFT',revision:1},kind:'contribution-draft',body:{title:'Design prototype'}});h.ctx.p=p;assert.equal(h.run('packetTitle(p)'),'Design prototype');
 p.records.push({ref:{id:'DESIGN',revision:1},kind:'contribution',body:{title:'Published Design'}});p.id='PKT-DESIGN';assert.equal(h.run('packetTitle(p)'),'Published Design');
});

test('packet list names open exact historical packet revisions and preserve changed-version warnings',()=>{
 const h=harness();h.ctx.state.packets=[packet(),{...packet(),revision:2,purpose:'Later packet'}];const before=JSON.stringify(h.ctx.state),html=h.run('packetsScreen()');
 assert.match(html,/data-action="packet"[^>]+data-id="PKT-CON-1\|1"/);assert.match(html,/data-id="PKT-CON-1\|2"/);
 assert.doesNotMatch(html,/>Inspect packet</);assert.equal(JSON.stringify(h.ctx.state),before);
});

test('situated claim discloses coherent meaning, conditional relations and exact evidence without implying approval',()=>{
 const h=harness(),raw={id:'NEED-1',revision:1},r={ref:raw,kind:'need-context',body:{title:'Ownership after handoff',claim:'Routing is not accepted ownership.',domain:'research',limitation:'Selected interviews only.',dimensions:Object.fromEntries(['people','job','situation','triggers','pains','gains','boundaries','dependencies'].map(k=>[k,{text:k==='people'?'A receptionist <script>':k,state:'interpretation',evidence_ids:['E1']} ])),evidence:[{id:'E1',ref:{id:'SRC',revision:1},quote:'Source <quote>',rationale:'One interview.',use:'active'}],links:[{ref:{id:'REQ',revision:2},relation:'depends-on',rationale:'Ownership needs an acceptance event.',conditions:'Nonurgent concern only.',use:'active'}]}};
 h.ctx.state.records=[r];h.run("inspectNeedContext('NEED-1|1')");const html=h.dialogs[0][1];
 for(const text of ['Routing is not accepted ownership.','Job to be done','Triggers','Pains and obstacles','Gains sought','Boundaries','Dependencies','Selected interviews only.','Source &lt;quote>','depends on','Nonurgent concern only.','REQ:v2','Sharing does not approve'])assert.ok(html.includes(text),text);
 assert.doesNotMatch(html,/<script>|<textarea|type="submit"/);
 h.ctx.p={...packet(),id:'PKT-NEED-1',records:[r],refs:[raw]};assert.equal(h.run('packetTitle(p)'),'Ownership after handoff');
 h.ctx.plan={situated_context:{included:[],to_review:[raw]}};const links=h.run('needContextPlanLinks(plan)');assert.match(links,/Additional research context to review/);assert.match(links,/has not been incorporated/);assert.match(links,/data-id="NEED-1\|1"/);
});

test('situated relationships name the exact requirement version inside the packet and flag changed active basis',()=>{
 const h=harness(),r={ref:{id:'NEED',revision:1},kind:'need-context',body:{title:'Context',claim:'A bounded claim.',domain:'research',limitation:'Limited.',dimensions:Object.fromEntries(['people','job','situation','triggers','pains','gains','boundaries','dependencies'].map(k=>[k,{text:k,state:'unknown',evidence_ids:[]} ])),evidence:[],links:[{ref:{id:'REQ',revision:1},relation:'refines',rationale:'Ground the requirement.',conditions:'This task only.',use:'active'}]}};
 h.ctx.r=r;h.ctx.p={records:[r,{ref:{id:'REQ',revision:1},kind:'requirement',body:{title:'Show evidence and limits of returned status'}}]};h.ctx.state.records=[{ref:{id:'REQ',revision:2},kind:'requirement',body:{title:'Changed title must not replace the saved requirement'}}];
 const html=h.run('needContextContent(r,p)');assert.match(html,/Show evidence and limits of returned status/);assert.doesNotMatch(html,/Changed title must not replace/);assert.match(html,/Active context has changed/);assert.match(html,/REQ:v1/);
});

test('intentional historical context is distinguished from a changed active basis',()=>{
 const h=harness();h.ctx.p={id:'PKT-NEED-x',records:[{kind:'need-context',body:{evidence:[],links:[{ref:{id:'INT',revision:1},use:'historical'},{ref:{id:'INT',revision:2},use:'active'}]}}],changed_refs:[{previous:{id:'INT',revision:1},current:{id:'INT',revision:2}}]};
 assert.equal(h.run('packetChanges(p).active.length'),0);assert.equal(h.run('packetChanges(p).historical.length'),1);assert.match(h.run('packetStatus(p)'),/Active basis unchanged/);
 h.ctx.p.changed_refs.push({previous:{id:'INT',revision:2},current:{id:'INT',revision:3}});assert.equal(h.run('packetChanges(p).active.length'),1);assert.match(h.run('packetStatus(p)'),/1 active references changed/);
});

test('research revision leads with proposed requirements criteria and brief changes while keeping earlier content exact',()=>{
 const h=harness(),base={title:'Ownership after handoff',claim:'An acceptance event establishes initial ownership.',domain:'research',limitation:'One fictional scenario.',dimensions:Object.fromEntries(['people','job','situation','triggers','pains','gains','boundaries','dependencies'].map(k=>[k,{text:k,state:'unknown',evidence_ids:[]} ])),evidence:[],links:[]},old={ref:{id:'NEED',revision:1},kind:'need-context',body:base},updated={ref:{id:'NEED',revision:2},kind:'need-context',body:{...base,claim:'Continuing responsibility needs current shift context.',previous:old.ref,change_summary:'A fictional shift handoff qualifies initial acceptance.',changed_fields:['claim'],example:'fictional-follow-up',review_items:['text','acceptance_criteria','objectives'].map(field=>({target:{id:field==='objectives'?'BRIEF':'REQ',revision:1},field,title:'Ownership',current_text:'Earlier '+field,proposed_text:'Proposed '+field+' <script>',rationale:'Why '+field,evidence_ids:['E1'],status:'reconsideration-needed'}))}},p={id:'PKT-NEED-x',revision:2,purpose:'Updated review',audience_scopes:['project:demo'],refs:[old.ref,updated.ref],records:[old,updated],changed_refs:[{previous:old.ref,current:updated.ref}]};
 h.ctx.state.records=[updated];h.ctx.state.packets=[{...p,revision:1,refs:[old.ref],records:[old]},p];h.run("inspectPacket('PKT-NEED-x|2')");const html=h.dialogs[0][1];
 for(const text of ['Research changes to consider','Fictional follow-up demonstration','Requirement wording','Acceptance criteria','Working brief','Earlier wording and why','An acceptance event establishes initial ownership.','Continuing responsibility needs current shift context.','existing requirements and the saved brief remain unchanged'])assert.ok(html.includes(text),text);
 assert.doesNotMatch(html,/<script>|<textarea|type="submit"/);assert.match(html,/&lt;script>/);assert.equal(h.run('packetChanges(state.packets[1]).active.length'),0);
 const list=h.run('packetsScreen()');assert.match(list,/Earlier packets \(1\)/);assert.match(list,/Review research changes/);
 h.ctx.requirement={ref:{id:'REQ',revision:1}};const notice=h.run('needContextRequirementNotice(requirement)');assert.match(notice,/Fictional follow-up/);assert.match(notice,/Existing wording is unchanged/);
});

test('packet names remain primary while exact inspection keys and manifest identities remain available',()=>{
 const h=harness(),p=packet();h.ctx.state.packets=[p];h.ctx.sample=p;const before=JSON.stringify(p),html=h.run('packetCard(sample)');
 assert.match(html,/data-action="packet" data-id="PKT-CON-1\|1">Research finding<\/a>/);assert.match(html,/<details class="record-metadata"><summary>Source details<\/summary>[\s\S]*PKT-CON-1:v1/);const primary=html.slice(0,html.indexOf('<details class="record-metadata">')).replace(/<[^>]+>/g,'');assert.doesNotMatch(primary,/PKT-CON-1/);assert.equal(JSON.stringify(p),before);assert.equal(h.dialogs.length,0);
});
test('evidence trail lists every package version with its team, author, purpose, audience and exact versions',()=>{
 const h=harness(),v1=packet(),v2=structuredClone(v1);v1.records[0].body.domain='Design';v1.records[0].body.domain_key='design';v1.records[0].body.owner='lee';v2.revision=2;v2.records[0]=structuredClone(v1.records[0]);v2.records[0].ref.revision=2;v2.records.push({ref:{id:'SRC-1',revision:1},kind:'source',body:{title:'Prototype notes'}});
 h.ctx.state.actors={lee:{name:'Mei Chen'}};h.ctx.state.packets=[v2,v1];const html=h.run('packetsScreen()');
 assert.equal((html.match(/class="evidence-row[ "]/g)||[]).length,2);assert.match(html,/Package v2 of 2/);assert.match(html,/Package v1 of 2/);assert.match(html,/ac-team-design/);assert.match(html,/Mei Chen/);assert.match(html,/Project participants/);
 assert.match(html,/Updated<\/span><span>Finding · Research finding <span class="evidence-version">v1 → v2/);assert.match(html,/Added<\/span><span>Source · Prototype notes/);assert.match(html,/data-action="packet" data-id="PKT-CON-1\|2"/);
});
test('evidence trail filters by team and search without changing packets',()=>{
 const h=harness(),a=packet(),b=packet();b.id='PKT-INTENT';b.purpose='Published starting direction';b.records=[{ref:{id:'INT-001',revision:2},kind:'intent',body:{}}];h.ctx.state.packets=[a,b];const before=JSON.stringify(h.ctx.state);
 h.run("evidenceTeamFilter='sponsor'");let html=h.run('packetsScreen()');assert.match(html,/Business intent published/);assert.doesNotMatch(html,/evidence-row-title">Research finding/);
 h.run("evidenceTeamFilter='all';evidenceQuery='zzz'");html=h.run('packetsScreen()');assert.match(html,/No packages match/);assert.equal(JSON.stringify(h.ctx.state),before);
});
test('evidence trail shows what references a package and that newer versions exist',()=>{
 const h=harness(),p=packet();h.ctx.state.packets=[p];h.ctx.state.records=[{ref:{id:'ISSUE-1',revision:3},kind:'bridge-issue',body:{title:'Which visits?',packet_refs:[{id:'PKT-CON-1',revision:1}]}}];const html=h.run('packetsScreen()');assert.match(html,/Issue: Which visits\? · v3/);assert.match(html,/included item has a newer version|included items have a newer version/);
});

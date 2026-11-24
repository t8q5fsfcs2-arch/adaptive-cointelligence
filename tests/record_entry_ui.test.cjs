const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function harness(){
 const req={ref:{id:'REQ-1',revision:2},body:{title:'Preserve an interrupted report',text:'Retain entered content when upload fails.',acceptance_criteria:'Retry without re-entry.',status:'approved'}},con={ref:{id:'CON-1',revision:3},body:{title:'Observed interruption',text:'A bounded finding.',limitation:'Small sample.'}};
 const progress={domains:[{domain:'Research',status:'Review recorded',contributions:[con.ref],reviewed_versions:[{id:'CON-1',revision:2}]}],case:{id:'CHG-1'},case_status:'approved',brief_considerations:[],next_question:'Who owns follow-up?',next_owner:'priya'};
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const c={state:{actors:{priya:{name:'Sponsor'}},requirement_resolution:{'REQ-1':progress}},requirementsMode:'domains',esc,records:k=>k==='requirement'?[req]:[],get:id=>id==='CON-1'?con:null,head:(t,s)=>`<h1>${t}</h1><p>${s}</p>`,para:v=>`<p>${esc(v)}</p>`,val:(t,v)=>`<strong>${esc(t)}</strong><p>${esc(v)}</p>`,label:r=>r.id+':v'+r.revision,ref:r=>esc(r.id+':v'+r.revision),statusTag:esc,impactBanner:()=>'',button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`};
 vm.createContext(c);const app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');vm.runInContext(app.slice(app.indexOf('function recordedDate('),app.indexOf('\nasync function load(')),c);vm.runInContext(app.match(/^const ref=.*$/m)[0].replace('const ref=','ref='),c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/signals.js'),'utf8'),c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/resolution.js'),'utf8'),c);return {c,req,con,progress,run:s=>vm.runInContext(s,c)};
}
test('cross-domain entries retain separate requirement, contribution and review destinations',()=>{
 const h=harness(),before=JSON.stringify([h.req,h.con,h.progress]);let summaries=0;h.c.requirementAuthoritySummary=()=>{summaries++;return '<section class="requirement-authority-summary">1 approved</section>';};const html=h.run('requirementsAcrossDomains()');
 assert.equal(summaries,1);assert.match(html,/requirement-authority-summary/);assert.match(html,/1 approved/);
 assert.match(html,/data-action="requirement" data-id="REQ-1"/);assert.match(html,/data-action="read-contribution" data-id="CON-1"/);assert.match(html,/data-action="case" data-id="CHG-1"/);
 assert.doesNotMatch(html,/>Open dossier<|>Read contribution</);assert.equal(JSON.stringify([h.req,h.con,h.progress]),before);
});
test('disclosing full wording preserves criteria, historical review basis and the pending next owner',()=>{
 const h=harness(),html=h.run('requirementsAcrossDomains()');
 for(const text of ['Requirement & criteria','Retain entered content when upload fails.','Retry without re-entry.','CON-1:v3','CON-1:v2','Selected in prior review','Who owns follow-up?','Next: Sponsor','Preparation checks only.'])assert.ok(html.includes(text),text);
});
test('shared team input includes published proposals and ratification separately but excludes private records',()=>{
 const h=harness(),pending={scope:'project:demo',ref:{id:'PENDING',revision:1},body:{title:'Pending candidate',text:'Investigate this proposed wording.',status:'proposed'}},privateRow={scope:'actor:priya',ref:{id:'PRIVATE',revision:1},body:{title:'PRIVATE DRAFT',status:'proposed'}};
 const rows=[h.req,pending,privateRow];h.c.records=k=>k==='requirement'?rows:[];const before=JSON.stringify(rows),html=h.run('requirementsAcrossDomains()');
 assert.match(html,/Preserve an interrupted report/);assert.match(html,/Pending candidate/);assert.match(html,/REQ-1:v2<\/span> · Ratified/);assert.match(html,/PENDING:v1<\/span> · Proposed/);const primary=html.replace(/<details class="record-metadata">[\s\S]*?<\/details>/g,'');assert.doesNotMatch(primary,/>Proposed<|>Ratified</);assert.match(html,/Confidence: Not rated/);assert.match(html,/Validation not recorded/);assert.doesNotMatch(html,/PRIVATE DRAFT|>Validated</);assert.equal(JSON.stringify(rows),before);
 h.req.body.status='proposed';assert.match(h.run('requirementsAcrossDomains()'),/Preserve an interrupted report/);
 h.c.records=()=>[];const empty=h.run('requirementsAcrossDomains()');assert.match(empty,/No published requirement map yet/);assert.doesNotMatch(empty,/data-action="requirement"/);
});
test('team input leads with report titles and keeps exact historical source versions on demand',()=>{
 const h=harness();h.progress.domains[0].status='Contribution shared';h.progress.domains[0].response={body:{rationale:'Useful within the stated sample.'}};h.progress.domains.push({domain:'Design',status:'No contribution shared',contributions:[],reviewed_versions:[]});
 const before=JSON.stringify([h.con,h.progress]),html=h.run('domainResolutionCards('+JSON.stringify(h.progress)+',true)');
 assert.match(html,/<h3>Research<\/h3>/);assert.match(html,/data-action="read-contribution" data-id="CON-1">Observed interruption<\/a>/);
 assert.match(html,/class="record-metadata domain-resolution-source"><summary>Source<\/summary>/);assert.match(html,/CON-1:v3/);assert.match(html,/CON-1:v2/);assert.match(html,/Selected in prior review/);assert.match(html,/Useful within the stated sample/);assert.match(html,/Earlier review basis/);
 const primary=html.replace(/<details class="record-metadata domain-resolution-source">[\s\S]*?<\/details>/g,'');
 assert.doesNotMatch(primary,/CON-1:v3|CON-1:v2|<h3>Contribution shared/);assert.match(primary,/<strong>Design<\/strong> — Nothing linked yet/);assert.doesNotMatch(primary,/article class="card"|does not imply the domain has done no work/);assert.equal(JSON.stringify([h.con,h.progress]),before);
 h.progress.case_status='pending-review';h.progress.domains[0].status='Concern needs resolution';const open=h.run('domainResolutionCards('+JSON.stringify(h.progress)+')').replace(/<details class="record-metadata domain-resolution-source">[\s\S]*?<\/details>/g,'');assert.match(open,/Change review: Concern needs resolution/);assert.doesNotMatch(open,/condition-chip-advisory/);
 h.progress.domains[0].status='Basis changed — review again';assert.match(h.run('domainResolutionCards('+JSON.stringify(h.progress)+')'),/condition-chip-advisory/);
 h.progress.domains[0].status='Awaiting domain review';assert.doesNotMatch(h.run('domainResolutionCards('+JSON.stringify(h.progress)+')'),/condition-chip-advisory/);
});

test('contribution requirement links keep human titles and exact selected versions without visible internal IDs',()=>{
 const h=harness();h.c.state.records=[{kind:'requirement',ref:h.req.ref,body:h.req.body}];h.c.links={requirement_refs:[h.req.ref]};
 const html=h.run('contributionRequirementLinks(links)'),primary=html.replace(/<details class="record-metadata">[\s\S]*?<\/details>/g,'').replace(/<[^>]*>/g,'');
 assert.match(primary,/Preserve an interrupted report · v2/);assert.doesNotMatch(primary,/REQ-1/);assert.match(html,/REQ-1:v2/);
 const fields=h.run('contributionRequirementFields(links)');assert.match(fields,/name="requirement_ref" value="REQ-1" checked/);assert.doesNotMatch(fields.replace(/<[^>]*>/g,''),/REQ-1/);
});

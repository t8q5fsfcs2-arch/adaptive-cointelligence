const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(domain='design'){
 const work={ref:{id:'D',revision:3},body:{title:'Fictional Design',owner:'lee',chassis:1,source_refs:[],requirement_refs:[],input_refs:[]}},thread={ref:{id:'CHAT',revision:1},body:{draft_id:'D'},plan:[]},row={ref:{id:'DEVBRIEF',revision:1},body:{title:'Developer brief',text:'A private candidate brief.',owner:'lee',conversation:'CHAT',draft_id:'D',requirement_refs:[],input_refs:[],source_refs:[],prototype:null},changed:[],source_options:[],prototype_options:[],history:[]},calls=[],dialogs=[],listeners={};
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const c={state:{actor:'lee',project:{id:'P',version:1},domains:{active:domain,profiles:[{key:'design',config:{label:'Design',deliverable_types:['Prototype design brief','Evidence-backed developer brief']}},{key:'research',config:{label:'Research',deliverable_types:['Research finding','Study synthesis']}}]},developer_briefs:{can_author:domain==='design',private:domain==='design'?[row]:[],shared:[]},domain_chat:{threads:[thread],turns:[],reports:[],submissions:[],objectives:[],implications:[]},bridge:{issues:[]},delivery:{drafts:[]}},selected:'D',busy:false,Map,Date,structuredClone,document:{addEventListener:(n,f)=>(listeners[n]??=[]).push(f),getElementById:()=>null,querySelector:()=>null,querySelectorAll:()=>[]},domainInfo:()=>({sources:[],deliverables:{}}),domainProfile:()=>({key:domain,config:{label:domain,descriptor:'Domain expertise'}}),records:k=>k==='contribution-draft'?[work]:[],get:()=>null,domainInputOptions:()=>[],domainFieldLabels:{},label:r=>r?.id+':v'+r?.revision,date:v=>v||'',packetKey:p=>p.id+'|'+p.revision,esc,para:v=>`<p>${esc(v)}</p>`,button:(t,a)=>`<button data-action="${a}">${t}</button>`,render:()=>{},toast:()=>{},load:async()=>{},command:async(a,d)=>{calls.push({a,d});return {ref:{id:'DEVBRIEF',revision:2}};},modal:(...a)=>dialogs.push(a),setTimeout:()=>1,clearTimeout:()=>{},closeModal:()=>{},domainHandoff:()=>{}};
 vm.createContext(c);require('./ui_reference_helpers.cjs')(c);for(const name of ['project-flow.js','domain-chat.js','working-report.js','domain-development.js','domain-prototypes.js','developer-brief.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static',name),'utf8'),c);return {c,row,thread,calls,dialogs,listeners,run:s=>vm.runInContext(s,c)};
}
test('the Design artifact has one editor beside the existing AI partner and shares the same text resizability rules',()=>{
 const h=harness();h.run("domainPanels.set(chatKey(),'developer-brief')");const html=h.run('domainChatScreen()');assert.match(html,/Developer brief/);assert.match(html,/id="developer-brief-document" maxlength="40000"/);assert.equal((html.match(/id="domain-chat-composer"/g)||[]).length,1);assert.doesNotMatch(html,/id="submission-document"/);assert.match(html,/Review sharing preview/);assert.match(html,/<details><summary>Prototype, evidence &amp; requirements|<details><summary>Prototype, evidence & requirements/);
 const research=harness('research');assert.doesNotMatch(research.run('chatWorkspaceActions()'),/Developer brief/);
 const css=fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-chat.css'),'utf8');assert.match(css,/#developer-brief-document\{[^}]*resize:vertical/);
});
test('unsaved brief edits are isolated and flushed through the existing navigation save path',async()=>{
 const h=harness();h.run("developerBriefDraft().text='An edited private draft';developerBriefDraft().dirty=true");assert.equal(h.run('hasUnsavedDevelopmentEditors()'),true);await h.run('saveDevelopmentEditors()');assert.equal(h.calls[0].a,'developer-brief-save');assert.equal(h.calls[0].d.expected.revision,1);assert.equal(h.calls[0].d.text,'An edited private draft');assert.equal(h.run('hasUnsavedDeveloperBrief()'),false);
 h.c.state.project.id='OTHER';assert.equal(h.run('hasUnsavedDeveloperBrief()'),false);
});
test('published Domain briefs excludes private drafts while working editors retain them',()=>{
 const h=harness();h.row.body.text='SECRET PRIVATE WORDING';h.row.last_shared={id:'PUBLISHED-DEVBRIEF',revision:2};h.c.state.developer_briefs.shared=[{kind:'project-developer-brief',ref:{id:'PUBLISHED-DEVBRIEF',revision:2},body:{title:'Earlier shared title',source_version:h.row.ref,published_at:'today'},changed:[]}];
 const before=JSON.stringify(h.c.state),rows=h.run('domainBriefItems()'),html=h.run('domainBriefDirectory()');
 assert.equal(rows.filter(r=>r.type==='Developer brief').length,1);assert.doesNotMatch(html,/Draft changes|pflow-developer-draft|Start a brief/);assert.doesNotMatch(h.run('workingDomainBriefs()'),/pflow-developer-draft/);assert.match(h.run('downstreamDomainBriefs()'),/pflow-developer-draft/);assert.match(html,/data-action="devbrief-shared" data-id="PUBLISHED-DEVBRIEF:v2"/);assert.doesNotMatch(html,/SECRET PRIVATE WORDING/);assert.equal(JSON.stringify(h.c.state),before);
 h.c.state.actor='sam';h.c.state.developer_briefs.can_author=false;
 const reader=h.run('domainBriefDirectory()');assert.match(reader,/Earlier shared title/);assert.doesNotMatch(reader,/pflow-developer-draft|Draft changes|devbrief-open/);
});
test('collection title and navigation are shared across domains and escape stored text',()=>{
 const h=harness('research');h.c.state.developer_briefs.shared=[{ref:{id:'PUBLISHED-DEVBRIEF',revision:1},body:{title:'<script>Shared</script>',owner:'lee'},changed:[]}];
 const html=h.run('domainBriefDirectory()');assert.match(html,/<h2>Working briefs<\/h2>/);assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>|devbrief-open/);assert.doesNotMatch(h.run('chatWorkspaceActions()'),/pflow-briefs/);assert.match(h.run('workingDomainBriefs()'),/Edit plan/);
});
test('selecting a developer brief opens its own work item and saves previous edits first',async()=>{
 const h=harness(),events=[];h.c.view='contributions';h.c.bridgeSection='overview';h.c.closeModal=()=>{};h.c.saveWorkingReport=async()=>events.push('save:'+h.c.selected);h.c.openDeveloperBrief=async()=>events.push('open:'+h.c.selected);
 await h.run('openDomainDeveloperBrief("DEVBRIEF")');assert.deepEqual(events,['save:D','open:D']);assert.equal(h.c.view,'contributions');
 h.c.selected='OTHER';await h.run('openDomainBriefDirectory()');assert.equal(h.c.view,'contributions');assert.equal(h.c.selected,'OTHER');assert.equal(h.c.bridgeSection,'overview');assert.equal(h.calls.length,0);
 h.c.state.actor='sam';await assert.rejects(h.run('openDomainDeveloperBrief("DEVBRIEF")'),/unavailable/);
});
test('applying a saved coach response previews the replacement and retains exact provenance without another model call',async()=>{
 const h=harness();h.c.state.domain_chat.turns=[{ref:{id:'TURN',revision:4},body:{conversation:'CHAT',role:'assistant',message:'A proposed brief, not approved.'}}];await h.run("developerBriefAction('devbrief-response','')");assert.equal(h.calls.length,0);assert.match(h.dialogs[0][1],/version history/);await h.dialogs[0][3]();assert.equal(h.calls[0].a,'developer-brief-save');assert.equal(h.calls[0].d.discussion.id,'TURN');assert.equal(h.calls[0].d.text,'A proposed brief, not approved.');
});
test('linked delivery states remain explicit and never claim the whole brief is approved',()=>{
 const h=harness();h.c.body={requirement_refs:[{id:'REQ',revision:2}]};h.c.state.bridge.issues=[{ref:{id:'ISSUE',revision:3},body:{title:'Resolve retry behavior'},decision_receipt:{approved:{ref:{id:'REQ',revision:2}},delivery:{targets:[{target:'jira',status:'simulated'},{target:'ado',status:'staged'}]}}}];const html=h.run('developerBriefDecisionLinks(body)');assert.match(html,/Decision receipt/);assert.match(html,/Simulated · not sent/);assert.match(html,/Staged · not sent/);assert.match(html,/No development approval is recorded for this brief/);
});

test('retired output types and unconfigured domains cannot populate the active brief collection',()=>{
 const h=harness();assert.match(h.run('downstreamDomainBriefs()'),/Developer brief/);assert.doesNotMatch(h.run('domainBriefDirectory()'),/pflow-developer-draft/);
 h.c.state.domains.profiles[0].config.deliverable_types=['Prototype test plan'];assert.doesNotMatch(h.run('domainBriefDirectory()'),/devbrief-open|pflow-developer-draft|devbrief-shared/);
 h.c.state.domains.profiles=[];assert.equal(h.run('domainBriefItems().length'),0);assert.doesNotMatch(h.run('domainBriefDirectory()'),/Start a brief/);
});


test('all project roles see the same released versions while private changes stay in working context',()=>{
 const h=harness();h.row.body.text='PRIVATE CANDIDATE';h.c.state.intake={published:{ref:{id:'BUSINESS',revision:3},body:{status:'published'}}};const design={kind:'project-design-brief',ref:{id:'DESIGN-RELEASE',revision:2},body:{domain:'Design',owner:'lee'}},originalRecords=h.c.records;h.c.records=k=>k==='project-design-brief'?[design]:originalRecords(k);h.c.state.developer_briefs.shared=[{ref:{id:'PUBLISHED-DEV',revision:4},body:{title:'Released implementation brief',owner:'lee'},changed:[]}];
 const before=JSON.stringify(h.c.state);for(const actor of ['priya','sam','lee','alex']){h.c.state.actor=actor;const html=h.run('domainBriefDirectory()');for(const id of ['BUSINESS|3','DESIGN-RELEASE|2','PUBLISHED-DEV:v4'])assert.ok(html.includes(id));assert.doesNotMatch(html,/PRIVATE CANDIDATE|pflow-developer-draft|pflow-objectives-edit|devbrief-open/);}h.c.state.actor='lee';assert.equal(JSON.stringify(h.c.state),before);
});
test('legacy brief navigation opens Business Intent without replacing unsaved work',async()=>{
 const h=harness();h.c.view='contributions';h.c.selected='D';h.c.saveBeforeProjectChange=async()=>{throw Error('Must not replace the editor');};await h.run('openDomainBriefDirectory()');assert.equal(h.c.view,'contributions');assert.equal(h.c.selected,'D');assert.equal(h.calls.length,0);assert.equal(h.dialogs[0][0],'Business Intent');assert.equal(h.dialogs[0][2],null);
});
test('the menu exposes only Business Intent while published and private domain records stay retained',()=>{
 const h=harness();h.c.state.intake={published:{ref:{id:'BUS',revision:2},body:{status:'published'}}};h.c.state.developer_briefs.shared=[{ref:{id:'PUBLISHED-DEV',revision:3},body:{title:'Released development brief',owner:'lee'},changed:[]}];const before=JSON.stringify(h.c.state),menu=h.run('domainBriefNavigation()');assert.match(menu,/Business Intent/);assert.match(menu,/pflow-business-intent/);assert.doesNotMatch(menu,/Domain briefs|PUBLISHED-DEV|devbrief-shared|pflow-developer-draft|pflow-objectives-edit|<details/);assert.equal(JSON.stringify(h.c.state),before);
});


test('menu brief rows omit author names while the published reader retains attribution',()=>{
 const h=harness();h.c.state.actors={priya:{name:'Sponsor Person'},lee:{name:'Design Person'}};h.c.state.intake={published:{ref:{id:'BUS',revision:2},body:{status:'published',source_draft:{id:'DRAFT',revision:1},snapshot:{title:'Released baseline'}}},cases:[]};h.c.intakeSnapshot=()=>'<p>Released baseline</p>';
 const menu=h.run('domainBriefNavigation()');assert.match(menu,/Business Intent/);assert.doesNotMatch(menu,/Published v2/);assert.doesNotMatch(menu,/Sponsor Person|Design Person/);h.run('openBusinessDomainBrief("BUS|2")');assert.match(h.dialogs[0][1],/Sponsor Person/);
});


test('private downstream briefs live with sharing output rather than the domain planning brief',()=>{
 const h=harness(),before=JSON.stringify(h.c.state),plan=h.run('workingDomainBriefs()'),output=h.run('submissionEditor()');assert.doesNotMatch(plan,/Developer brief|devbrief-open|pflow-developer-draft/);assert.match(output,/Downstream handoff/);assert.match(output,/data-action="pflow-developer-draft"/);assert.doesNotMatch(h.run('domainBriefNavigation()'),/pflow-developer-draft/);assert.equal(JSON.stringify(h.c.state),before);
 const research=harness('research');assert.equal(research.run('downstreamDomainBriefs()'),'');
});

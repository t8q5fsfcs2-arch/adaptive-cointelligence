const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
function harness(){
 const calls=[],dialogs=[],listeners={};
 const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const config={label:'Research',authors:['sam'],descriptor:'Research coach',criteria:['Locate the observation'],deliverable_types:['Finding'],expertise:'Evidence',evidence_standard:'Source',coach_guidance:'Focus',vocabulary:'Terms',downstream_questions:'Unknowns',examples:'Example'};
 const report={ref:{id:'R',revision:2},current:true,body:{draft:{id:'D',revision:1},mode:'simulated',reviewed:false,dispositions:{},output:{summary:'<script>unsafe</script>',strengths:[],suggestions:[{issue:'Missing context',direction:'intent',edit:{field:'interpretation',text:'A qualified interpretation'},kind:'evidence',question:'Which task?',basis:'observation',quote:'A finding'}]}}};
 const ctx={state:{actor:'sam',actors:{sam:{name:'Sam'}},domains:{active:'research',profiles:[{key:'research',config,ref:{id:'CONFIG',revision:2}}],can_configure:['research'],reports:[report],guardrails:'Preserve authority'}},dirty:false,pageDirty:false,busy:false,
 get:id=>({ref:{id,revision:1},body:{title:'Draft',interpretation:'Original'}}),label:r=>r.id+':v'+r.revision,button:(title,action,id)=>`<button data-action="${action}" data-id="${id}">${title}</button>`,val:(title,text)=>`<p>${esc(title)}: ${esc(text)}</p>`,esc,para:s=>`<p>${esc(s)}</p>`,settingSelector:()=>'',settingInput:()=>'',settingField:()=>'',
 $:()=>({addEventListener:(name,fn)=>listeners[name]=fn,querySelectorAll:()=>[]}),
 document:{querySelector:()=>null},confirm:()=>true,abandonIntakeEdits:()=>true,
 modal:(...args)=>dialogs.push(args),command:async(action,data)=>{calls.push({action,data});return {message:'Review saved',domainReport:'R'};},saveCoachedField:async()=>{},
 };
 vm.createContext(ctx);require('./ui_reference_helpers.cjs')(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/packets.js'),'utf8'),ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domains.js'),'utf8'),ctx);
 return {ctx,calls,dialogs,listeners,run:s=>vm.runInContext(s,ctx)};
}
test('advisory feedback escapes model text and saves decisions without reopening the report',async()=>{
 const h=harness();h.run("openDomainReport('R')");const html=h.dialogs[0][1];assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);assert.match(html,/<details class="rule" open><summary>Missing context/);assert.match(html,/<summary>Evidence and linked requirements/);assert.match(html,/Looking back/);assert.match(html,/Review suggested wording/);
 const result=await h.dialogs[0][3](new Map([['confirm','on'],['action-0','deferred'],['rationale-0','Follow up with the researcher']]));
 assert.equal(h.calls[0].action,'domain-disposition');assert.equal(h.calls[0].data.expected.revision,2);assert.equal(h.calls[0].data.dispositions[0].action,'deferred');assert.equal(result.domainReport,undefined);
});
test('stale feedback retains notes but cannot apply old suggestions',()=>{
 const h=harness();h.ctx.state.domains.reports[0].current=false;h.run("openDomainReport('R')");assert.equal(typeof h.dialogs[0][3],'function');assert.match(h.dialogs[0][1],/Earlier draft or context/);assert.doesNotMatch(h.dialogs[0][1],/Review suggested wording/);
});
test('domain settings preserve unsaved intake and cancelled form edits',async()=>{
 const h=harness();h.ctx.dirty=true;h.ctx.confirm=()=>false;await h.run("domainAction('settings-domains','research')");assert.equal(h.dialogs.length,0);
 h.ctx.dirty=false;h.ctx.document.querySelector=()=>({});h.ctx.saveCoachedField=async()=>{h.ctx.pageDirty=true;};
 await assert.rejects(h.run("domainAction('settings-domains','research')"),/New edits arrived/);assert.equal(h.dialogs.length,0);assert.equal(h.ctx.busy,false);
});

test('suggested wording is previewed and author edits travel with exact versions',async()=>{
 const h=harness();h.run("domainEditPreview('R',0)");assert.match(h.dialogs[0][1],/Original/);assert.match(h.dialogs[0][1],/A qualified interpretation/);
 await h.dialogs[0][3](new Map([['text','Author-refined wording'],['confirm','on']]));const c=h.calls[0];assert.equal(c.action,'domain-apply-advice');assert.equal(c.data.text,'Author-refined wording');assert.equal(c.data.report.revision,2);assert.equal(c.data.expected.revision,1);
});
test('continuing a conversation carries only the selected earlier exchange',async()=>{
 const h=harness();h.ctx.state.domains.model={provider:'TEST DOUBLE',configured:true};h.run("domainCoach(get('D'),state.domains.reports[0])");
 assert.match(h.dialogs[0][1],/previous exchange/);await h.dialogs[0][3](new Map([['question','What does this change?']]));assert.equal(h.calls[0].action,'domain-coach');assert.equal(h.calls[0].data.previous.id,'R');assert.equal(h.calls[0].data.question,'What does this change?');
});
test('prepare to share packages open questions without asking the model',async()=>{
 const h=harness();h.ctx.state.domains.handoffs=[];h.run("domainPrepare(get('D'))");assert.match(h.dialogs[0][1],/Which task/);assert.match(h.dialogs[0][1],/does not make a model request/);
 await h.dialogs[0][3](new Map([['recipient','design'],['intent_implications','Reconsider the assumption'],['downstream_needs','Clarify resumption'],['open_questions','What information is needed?']]));assert.equal(h.calls[0].action,'domain-prepare');assert.equal(h.calls[0].data.expected.id,'D');assert.equal(h.calls[0].data.open_questions,'What information is needed?');
});
test('preflight retains questions from the previous draft for author review and excludes rejected advice',()=>{
 const h=harness(),r=h.ctx.state.domains.reports[0];r.current=false;r.body.dispositions={'0':{action:'accepted'}};
 h.run("domainPrepare(get('D'))");assert.match(h.dialogs[0][1],/Which task/);assert.match(h.dialogs[0][1],/earlier drafts/);
 r.body.dispositions['0'].action='rejected';h.run("domainPrepare(get('D'))");assert.doesNotMatch(h.dialogs[1][1],/Which task/);
});


test('published input selection pins historical versions until the author changes them',()=>{
 const h=harness();
 const old={ref:{id:'PUB',revision:1},body:{title:'<script>old</script>',domain:'Research',observation:'Earlier finding',limitation:'Small sample'}};
 const current={ref:{id:'PUB',revision:2},body:{title:'Current finding',domain:'Research',observation:'Revised finding'}};
 h.ctx.state.domains.input_versions=[old];
 h.ctx.records=kind=>kind==='contribution'?[current]:[];
 h.ctx.get=id=>id==='PUB'?current:null;
 h.ctx.body={input_refs:[old.ref]};
 const html=h.run('domainInputChoices(body)');
 assert.match(html,/&lt;script>/);
 assert.doesNotMatch(html,/<script>/);
 assert.match(html,/value="PUB:v1" checked/);
 assert.match(html,/value="PUB:v2" >/);
 assert.match(html,/Earlier version/);
 h.ctx.ref=r=>r.id+':v'+r.revision;
 const selected=h.run('domainSelectedInputs(body)');
 assert.match(selected,/Earlier finding/);
 assert.doesNotMatch(selected,/Revised finding/);
});

test('deliverable form submits the selected published version and describes model context',async()=>{
 const h=harness();
 const published={ref:{id:'PUB',revision:3},body:{title:'Research finding',domain:'Research',observation:'Observed interruption'}};
 h.ctx.records=kind=>kind==='contribution'?[published]:[];
 h.ctx.state.domains.sources=[];h.ctx.state.domains.relations=[];
 h.ctx.state.domains.model={configured:true,provider:'TEST DOUBLE'};
 h.ctx.view='contributions';h.ctx.selected=null;
 h.run('domainEdit()');
 assert.match(h.dialogs[0][1],/Published work to build on/);
 assert.match(h.dialogs[0][1],/name="input_ref" value="PUB:v3"/);
 const values=new Map([['title','Design proposal'],['deliverable_type','Finding']]);
 values.getAll=key=>key==='input_ref'?['PUB:v3']:[];
 await h.dialogs[0][3](values);
 assert.equal(h.calls[0].action,'domain-save');
 assert.equal(h.calls[0].data.input_refs[0].id,'PUB');
 assert.equal(h.calls[0].data.input_refs[0].revision,3);
 h.run("domainCoach(get('D'))");
 assert.match(h.dialogs[1][1],/selected published work/);
});

test('published input choices keep exact values while names lead and source IDs unfold outside the label',()=>{
 const h=harness(),record={kind:'contribution',ref:{id:'CON-PRIVATE-IDENTIFIER',revision:7},body:{title:'Observed handoff delay',domain:'Research',observation:'A receiving worker waited.',limitation:'One observed task.'}};h.ctx.state.records=[record];h.ctx.records=kind=>h.ctx.state.records.filter(r=>r.kind===kind);h.ctx.state.domains.input_versions=[];h.ctx.sample={input_refs:[record.ref]};const before=JSON.stringify(h.ctx.state),html=h.run('domainInputChoices(sample)');
 assert.match(html,/value="CON-PRIVATE-IDENTIFIER:v7" checked/);assert.match(html,/Observed handoff delay/);assert.match(html,/Version 7/);const choice=html.match(/<label class="checkbox selectable">([\s\S]*?)<\/label>/)[1];assert.doesNotMatch(choice.replace(/<[^>]+>/g,''),/CON-PRIVATE-IDENTIFIER/);assert.doesNotMatch(choice,/<details/);assert.match(html,/<\/label><details class="record-metadata"><summary>Source details<\/summary>[\s\S]*CON-PRIVATE-IDENTIFIER:v7/);assert.equal(JSON.stringify(h.ctx.state),before);assert.equal(h.calls.length,0);
});

test('legacy AI partner keeps an open scoped question draft and preserves the exact advisory request',async()=>{
 const h=harness();h.ctx.state.project={id:'project-one'};h.ctx.state.auth={account:{id:'account-one'}};h.ctx.state.domains.model={configured:true};
 h.run("legacyDomainReviewerWrite('D','Keep my question <private>.')");h.run("domainCoach(get('D'),state.domains.reports[0])");
 const [title,html,submit,handler]=h.dialogs[0];assert.equal(title,'AI partner');assert.equal(submit,'Ask');assert.match(html,/rows="5"/);assert.match(html,/data-reviewer-draft="legacy-domain-coach"/);assert.match(html,/data-reviewer-scope="D"/);assert.match(html,/class="reviewer-speaker">You/);assert.match(html,/class="reviewer-speaker">AI partner/);assert.match(html,/Keep my question &lt;private>\./);assert.match(html,/Private sources require explicit release/);assert.equal(h.calls.length,0);
 await handler(new Map([['question','Which evidence matters?']]));assert.equal(h.calls[0].action,'domain-coach');assert.equal(h.calls[0].data.expected.id,'D');assert.equal(h.calls[0].data.previous.id,'R');assert.equal(h.calls[0].data.consent,true);
 h.run("domainCoach(get('D'))");assert.match(h.dialogs[1][1],/Which evidence matters\?/);assert.equal(h.run("legacyDomainReviewerRead('OTHER')"),'');
 h.ctx.state.actor='lee';assert.equal(h.run("legacyDomainReviewerRead('D')"),'');h.ctx.state.actor='sam';h.ctx.state.project.id='project-two';assert.equal(h.run("legacyDomainReviewerRead('D')"),'');h.ctx.state.project.id='project-one';h.ctx.state.auth.account.id='account-two';assert.equal(h.run("legacyDomainReviewerRead('D')"),'');
 h.ctx.state.auth.account.id='account-one';assert.equal(h.run("legacyDomainReviewerRead('D')"),'Which evidence matters?');
});
test('legacy reviewer blocks an outdated role/project binding and empty or disconnected requests before model commands',async()=>{
 const h=harness();h.ctx.state.project={id:'project-one'};h.ctx.state.domains.model={configured:true};h.run("domainCoach(get('D'))");const handler=h.dialogs[0][3];
 h.ctx.state.project.id='project-two';await assert.rejects(handler(new Map([['question','Old project context']])),/project or role changed/);assert.equal(h.calls.length,0);assert.equal(h.run("legacyDomainReviewerRead('D')"),'');
 h.ctx.state.project.id='project-one';await assert.rejects(handler(new Map([['question','   ']])),/Enter a question/);assert.equal(h.calls.length,0);
 h.ctx.state.domains.model.configured=false;await assert.rejects(handler(new Map([['question','Keep this draft while disconnected']])),/Connect a model/);assert.equal(h.calls.length,0);assert.equal(h.run("legacyDomainReviewerRead('D')"),'Keep this draft while disconnected');
});
test('saved advisory reviews retain their separate notes action and identify AI output',()=>{
 const h=harness();h.ctx.state.domains.reports[0].body.question='A saved human question';h.run("openDomainReport('R')");assert.equal(h.dialogs[0][0],'Saved review');assert.equal(h.dialogs[0][2],'Save notes');assert.match(h.dialogs[0][1],/You: A saved human question/);assert.match(h.dialogs[0][1],/class="reviewer-speaker">AI partner/);assert.match(h.dialogs[0][1],/&lt;script>unsafe/);assert.equal(h.calls.length,0);
});

test('legacy detail reviewer exposes an inline question and sends it through consent without a second question-entry step',async()=>{
 const h=harness(),draft={ref:{id:'D',revision:1},body:{title:'Saved finding',domain_key:'research',deliverable_type:'Finding',observation:'Observed context loss',interpretation:'A bounded interpretation',recommendation:'Investigate',limitation:'One task',source:'Local observation',links:[],source_refs:[]}};
 h.ctx.state.project={id:'project-one'};Object.assign(h.ctx.state.domains,{model:{configured:true},runs:[],sources:[],handoffs:[],input_versions:[]});h.ctx.records=()=>[];h.ctx.head=(title,copy)=>`<h1>${title}</h1><p>${copy}</p>`;h.ctx.date=v=>v;h.ctx.get=id=>id==='D'?draft:null;h.ctx.draft=draft;
 h.run("legacyDomainReviewerWrite('D','Keep this question.')");const before=JSON.stringify(h.ctx.state),html=h.run('domainDetail(draft)');
 assert.match(html,/data-integrity-review-panel/);assert.match(html,/class="reviewer-scroll"/);assert.match(html,/id="legacy-domain-detail-question"[^>]*rows="5"/);assert.match(html,/Keep this question\./);assert.match(html,/data-action="domain-coach" data-id="D"[^>]*>Ask<\/button>/);assert.match(html,/data-reviewer-scope="D"/);assert.equal(JSON.stringify(h.ctx.state),before);
 const composer={value:'Which evidence do I need?',dataset:{reviewerScope:'D',reviewerDraftKey:h.run("legacyDomainReviewerKey('D')")}};h.ctx.document.querySelector=selector=>selector==='#legacy-domain-detail-question'?composer:null;
 await h.run("domainAction('domain-coach','D')");assert.equal(h.calls.length,0);assert.equal(h.dialogs[0][0],'Ask your AI partner');assert.match(h.dialogs[0][1],/You: Which evidence do I need\?/);assert.match(h.dialogs[0][1],/will be sent to the configured model/);assert.doesNotMatch(h.dialogs[0][1],/<textarea/);
 await h.dialogs[0][3](new Map());assert.equal(h.calls[0].action,'domain-coach');assert.equal(h.calls[0].data.question,composer.value);assert.equal(h.calls[0].data.expected.id,'D');assert.equal(h.calls[0].data.previous.id,'R');assert.equal(h.calls[0].data.consent,true);assert.equal(h.run("legacyDomainReviewerRead('D')"),composer.value);
 composer.dataset.reviewerDraftKey='earlier-role';await assert.rejects(h.run("domainAction('domain-coach','D')"),/project or role changed/);assert.equal(h.calls.length,1);
});

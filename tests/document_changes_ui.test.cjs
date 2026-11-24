const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(){
 const item={effect:'challenges',reason:'A reported gap',evidence_kind:'reported-finding',limitation:'Small sample',proposed_text:'<script>proposed</script>',citations:[]};
 const review={ref:{id:'C1',revision:1},stale:[],body:{trigger_title:'New findings',trigger_source:{id:'NEW',revision:1},basis:{id:'D',revision:2},sources:[{id:'OLD',revision:1},{id:'NEW',revision:1}],mode:'live',values:{value:'Old words'},status:'open',decisions:[],downstream:[],already_changed_fields:[],at:'today',agent_version:'17',review_version:'1',output:{summary:'A source challenges this claim.',recommendation:'revise',assessments:{value:item},impacts:[],requirements:[],questions:['What is still unknown?']}}};
 const dialogs=[],calls=[],esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const ctx={state:{actor:'priya',actors:{},intake:{draft:{ref:{id:'D',revision:2},body:{values:{value:'Old words'}}}},document_changes:{reviews:[review],pending_sources:[{id:'NEW',revision:1}]}},pageDirty:false,esc,shortQuestion:s=>s,label:r=>r.id+':v'+r.revision,date:s=>s,para:s=>'<p>'+esc(s)+'</p>',val:(t,s)=>'<label>'+esc(t)+'</label><p>'+esc(s)+'</p>',tag:esc,button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,citationsHtml:()=>'',field:(n,t)=>`<label>${t}<textarea name="${n}"></textarea></label>`,coachInfo:()=>({sources:[{ref:{id:'OLD',revision:1},body:{title:'Prior source'}},{ref:{id:'NEW',revision:1},body:{title:'New findings'}}]}),modal:(...args)=>dialogs.push(args),command:async(a,d)=>{calls.push({a,d});return{};}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/document-changes.js'),'utf8'),ctx);
 return {ctx,review,calls,dialogs,run:s=>vm.runInContext(s,ctx)};
}
test('review shows a bounded comparison with source details collapsed and escapes generated wording',()=>{
 const h=harness();h.run("openDocumentChange('C1')");const html=h.dialogs[0][1];
 assert.match(html,/Current proposition at assessment/);assert.match(html,/Proposed revision/);assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);
 assert.match(html,/No requirement drawers or requirements exist/);assert.match(html,/Jira remain unchanged/);assert.match(html,/<details class="section"><summary>What holds/);
});
test('stale assessments retain results but replace adoption with reassessment',()=>{
 const h=harness();h.review.stale=['The saved intake changed.'];h.run("openDocumentChange('C1')");const html=h.dialogs[0][1];
 assert.match(html,/Assess again/);assert.doesNotMatch(html,/data-action="document-change-edit"|data-action="document-change-keep"/);
});
test('quality flags stay visible on the report and the editable affected proposal',()=>{
 const h=harness();h.review.quality_flags=[{field:'measures',message:'Average and median do not match.',blocks_application:true}];
 h.review.body.output.impacts=[{...h.review.body.output.assessments.value,field:'measures'}];
 h.run("openDocumentChange('C1')");assert.match(h.dialogs[0][1],/Check before applying/);
 h.ctx.r=h.review;h.run('documentChangeEdit(r)');assert.match(h.dialogs[1][1],/measures · Needs correction/);
 assert.match(h.dialogs[1][1],/Average and median do not match/);
});
test('an additional unassessed source opens its own review instead of the older decision',()=>{
 const h=harness();h.ctx.state.document_changes.pending_sources.push({id:'NEWER',revision:1});const html=h.run('documentChangeNotice()');
 assert.match(html,/data-action="document-change-start" data-id="NEWER"/);
});
test('edit form requires explicit selection and records reason with edited text',async()=>{
 const h=harness();h.ctx.r=h.review;h.run('documentChangeEdit(r)');const html=h.dialogs[0][1];
 assert.doesNotMatch(html,/<input[^>]*checked/);assert.match(html,/recorded as not adopted/);
 const fd={getAll:()=>[],get:()=>''};await assert.rejects(h.dialogs[0][3](fd),/Choose at least one/);
 fd.getAll=()=>['value'];fd.get=k=>k==='reason'?'A bounded change':'Edited proposal';await h.dialogs[0][3](fd);
 assert.equal(h.calls[0].a,'intake-change-resolve');assert.equal(h.calls[0].d.reason,'A bounded change');assert.equal(h.calls[0].d.changes.value,'Edited proposal');
});

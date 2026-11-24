const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
function harness(){
 const calls=[],dialogs=[],esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const source={ref:{id:'PDF',revision:2},body:{title:'Synthetic.pdf',visual_pdf:{page_count:3}}};
 const draft={ref:{id:'D',revision:4},body:{source_refs:[source.ref],requirement_refs:[{id:'REQ',revision:3}],input_refs:[{id:'FIND',revision:2}]}};
 const report={ref:{id:'VIS',revision:1},current:false,basis_records:[{ref:{id:'REQ',revision:3},kind:'requirement',body:{title:'Report first'}}],body:{draft:draft.ref,source:source.ref,pages:[{page:2}],mode:'live',output:{summary:'<script>unsafe</script>',limitations:'Static only',findings:[{page:2,area:'Photo gate',assessment:'tension',observation:'Photo required',rationale:'Blocks reporting',recommendation:'Allow evidence later',uncertainty:'Test interaction',context_links:[{ref:{id:'REQ',revision:3},quote:'Submit without a photo'}]}]}}};
 const ctx={state:{actor:'lee',project:{id:'project & x',version:7},design_visual:{available:true,reports:[report]}},URLSearchParams,document:{addEventListener:()=>{},querySelector:()=>null},domainInfo:()=>({sources:[source],model:{provider:'OpenAI'}}),label:r=>r.id+':v'+r.revision,domainInputOptions:()=>[{ref:{id:'FIND',revision:2},body:{domain_key:'research'}}],records:()=>[{kind:'intent'}],get:()=>draft,esc,button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,val:(t,v)=>`<strong>${t}</strong><p>${esc(v)}</p>`,para:s=>`<p>${esc(s)}</p>`,domainText:()=>'<textarea name="question"></textarea>',date:s=>s,modal:(...args)=>dialogs.push(args),command:async(action,data)=>{calls.push({action,data});return {};}};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/design-visual.js'),'utf8'),ctx);
 return {ctx,draft,source,report,calls,dialogs,run:s=>vm.runInContext(s,ctx)};
}
test('preview URLs pin project generation source revision and page without binary data',()=>{
 const h=harness(),url=h.run("visualPageUrl({id:'PDF',revision:2},3)"),query=new URL(url,'http://localhost').searchParams;
 assert.equal(query.get('project'),'project & x');assert.equal(query.get('generation'),'7');assert.equal(query.get('revision'),'2');assert.equal(query.get('page'),'3');assert.equal(query.get('source'),'PDF');
});
test('only exact selected visual source versions appear on the Design deliverable',()=>{
 const h=harness();assert.equal(h.run('visualSources(get()).length'),1);h.draft.body.source_refs[0]={id:'PDF',revision:1};assert.equal(h.run('visualSources(get()).length'),0);
 h.ctx.state.actor='sam';assert.equal(h.run('visualEntry(get())'),'');
});
test('review submits explicit page choice with saved draft and source versions',async()=>{
 const h=harness();h.run('openVisualReview(get())');const dialog=h.dialogs[0];assert.match(dialog[1],/Only those page images are sent/);assert.match(dialog[1],/1 selected published Research/);
 await dialog[3]({getAll:()=>['2','3'],get:()=> 'Check reporting'});const {action,data}=h.calls[0];assert.equal(action,'design-visual-review');assert.equal(data.expected.revision,4);assert.equal(data.source.revision,2);assert.deepEqual(Array.from(data.pages),[2,3]);assert.equal(data.consent,true);
 await assert.rejects(async()=>dialog[3]({getAll:()=>[],get:()=>''}),/Select one to six/);
});
test('feedback escapes model content keeps page links citations and warns on changed basis',()=>{
 const h=harness();h.run("openVisualReport('VIS')");const html=h.dialogs[0][1];assert.match(html,/&lt;script>/);assert.doesNotMatch(html,/<script>/);assert.match(html,/Earlier review/);assert.match(html,/Live AI review/);assert.match(html,/View page 2/);assert.match(html,/Report first/);assert.match(html,/Submit without a photo/);assert.match(html,/Edit Design deliverable/);
});

test('unrelated navigation is not intercepted by the visual action handler',async()=>{
 const h=harness();for(const value of ['undefined','null',"'projects'","'domain-open'"])assert.equal(await h.run('designVisualAction('+value+')'),false);
});

test('PDF attachment uses one atomic command with the exact draft version',async()=>{
 const h=harness();h.run("visualFileContent=async()=> 'synthetic-pdf-base64'; uploadVisual(get())");
 await h.dialogs[0][3]({get:()=>({name:'synthetic.pdf'})});
 assert.equal(h.calls.length,1);assert.equal(h.calls[0].action,'design-pdf-attach');assert.equal(h.calls[0].data.expected.revision,4);assert.equal(h.calls[0].data.content,'synthetic-pdf-base64');
});

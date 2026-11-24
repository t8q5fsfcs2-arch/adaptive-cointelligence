const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');
function harness(){
 const row={kind:'requirement',ref:{id:'REQ-INTERNAL-01',revision:2},body:{title:'Keep <draft> & context',text:'Saved wording'}};
 const c={state:{records:[row],cases:[],packets:[]}};vm.createContext(c);
 vm.runInContext(app.match(/^const esc=.*$/m)[0]+'\n'+app.match(/^const rid=.*$/m)[0],c);
 require('./ui_reference_helpers.cjs')(c);return {c,row,run:s=>vm.runInContext(s,c)};
}
test('readable reference text keeps canonical identity in metadata without interactive nesting',()=>{
 const h=harness(),before=JSON.stringify(h.c.state);h.c.raw=h.row.ref;
 const html=h.run('ref(raw)'),visible=html.replace(/<[^>]*>/g,'');
 assert.match(visible,/Keep &lt;draft&gt; &amp; context · v2/);assert.doesNotMatch(visible,/REQ-INTERNAL-01/);
 assert.match(html,/data-record-id="REQ-INTERNAL-01" data-record-revision="2"/);assert.doesNotMatch(html,/<details|<button|<a /);
 assert.equal(h.run('label(raw)'),'REQ-INTERNAL-01:v2');assert.equal(JSON.stringify(h.c.state),before);
});
test('historical references never substitute a newer title for an unloaded saved version',()=>{
 const h=harness();h.c.old={id:h.row.ref.id,revision:1};
 assert.equal(h.run('referenceText(old)'),'Requirement · v1');
 h.c.pinned={kind:'requirement',ref:h.c.old,body:{title:'Earlier saved title'}};
 assert.equal(h.run('referenceText(old,pinned)'),'Earlier saved title · v1');
 assert.equal(h.row.body.title,'Keep <draft> & context');
});
test('source details retain distinct exact versions while deduplicating identical references',()=>{
 const h=harness();h.c.refs=[h.row.ref,{...h.row.ref},{id:h.row.ref.id,revision:1}];const before=JSON.stringify(h.c.refs);
 const html=h.run('sourceDetails(refs)');
 assert.match(html,/<details class="record-metadata"><summary>Source details<\/summary>/);assert.doesNotMatch(html,/<details[^>]* open/);
 assert.equal((html.match(/REQ-INTERNAL-01:v2/g)||[]).length,1);assert.equal((html.match(/REQ-INTERNAL-01:v1/g)||[]).length,1);
 assert.equal(JSON.stringify(h.c.refs),before);
});

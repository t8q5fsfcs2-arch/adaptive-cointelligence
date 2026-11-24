const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(){
 const handlers={},renders=[],submit={textContent:'Share',disabled:false},error={textContent:'',scrollIntoView(){}},dialog={open:false,showModal(){this.open=true},close(){this.open=false},querySelector:()=>error};
 const c={busy:false,dirty:false,$:s=>s==='#modal'?dialog:{addEventListener:(event,fn)=>handlers[event]=fn},esc:v=>String(v),FormData:class{},load:async()=>{},render:()=>renders.push({busy:c.busy,open:dialog.open}),toast:()=>{}};vm.createContext(c);let source=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');source=source.slice(source.indexOf('function modal('),source.indexOf('function closeModal'));vm.runInContext(source,c);
 return {c,dialog,submit,error,renders,run:s=>vm.runInContext(s,c),submitForm:()=>handlers.submit({preventDefault(){},target:{},submitter:submit})};
}
test('a completed Share renders the workbench enabled and releases the submit guard',async()=>{
 const h=harness();h.c.handler=async()=>({message:'Shared'});h.run("modal('Share findings','Findings preview','Share',handler)");await h.submitForm();assert.deepEqual(h.renders,[{busy:false,open:false}]);assert.equal(h.c.busy,false);assert.equal(h.submit.disabled,false);
});
test('a failed transaction retains the dialog and permits retry without rendering success',async()=>{
 const h=harness();h.c.handler=async()=>{throw Error('Source changed. Review again.')};h.run("modal('Share findings','Preview','Share',handler)");await h.submitForm();assert.equal(h.dialog.open,true);assert.equal(h.error.textContent,'Source changed. Review again.');assert.equal(h.renders.length,0);assert.equal(h.c.busy,false);assert.equal(h.submit.disabled,false);
});

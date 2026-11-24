const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(actor='sam'){
 const listeners={},stored=new Map(),style={},attrs={'aria-valuenow':'65'},classes=new Set();let renders=0;
 const parent={style:{setProperty:(k,v)=>style[k]=v},getBoundingClientRect:()=>({width:1024,left:20})};
 const handle={parentElement:parent,dataset:{defaultSplit:'65'},isConnected:true,setAttribute:(k,v)=>attrs[k]=v,getAttribute:k=>attrs[k],closest:s=>s==='.domain-panel-resize'?handle:null,focus(){},setPointerCapture(){},releasePointerCapture(){}};
 const ctx={state:{actor,domains:{active:actor==='sam'?'research':'design'},auth:{account:{id:'person'}},project:{id:'one',version:1}},document:{addEventListener:(n,fn)=>(listeners[n]??=[]).push(fn),querySelector:()=>handle,body:{classList:{add:n=>classes.add(n),remove:n=>classes.delete(n)}}},localStorage:{getItem:k=>stored.get(k)??null,setItem:(k,v)=>stored.set(k,v),removeItem:k=>stored.delete(k)},render:()=>renders++};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-chat.js'),'utf8'),ctx);
 const event=(kind,patch={})=>{let prevented=false;for(const fn of listeners[kind]||[])fn({target:handle,button:0,pointerId:1,preventDefault(){prevented=true;},...patch});return prevented;};
 return {ctx,stored,style,attrs,classes,parent,handle,event,run:s=>vm.runInContext(s,ctx),renders:()=>renders};
}
test('one divider component supports Research and Design with keyboard resizing and personal persistence',()=>{
 for(const actor of ['sam','lee']){const h=harness(actor);assert.match(h.run("domainSplitHandle('implications')"),/role="separator".*tabindex="0"/);assert.equal(h.event('keydown',{key:'ArrowRight'}),true);assert.equal(h.attrs['aria-valuenow'],'67');assert.equal(h.run("domainSplitValue('sharing')"),67);assert.equal(h.renders(),0);h.ctx.state.domains.active='other-configured-domain';assert.equal(h.run("domainSplitValue('implications')"),67);h.ctx.state.project.id='two';assert.equal(h.run("domainSplitValue('implications')"),67);h.ctx.state.actor='someone-else';assert.equal(h.run("domainSplitValue('implications')"),65);h.ctx.state.actor=actor;h.ctx.state.auth.account.id='another-account';assert.equal(h.run("domainSplitValue('implications')"),65);}
});
test('pointer resizing preserves mounted draft content and commits only on release',()=>{
 const h=harness();h.event('pointerdown');h.event('pointermove',{clientX:532});assert.equal(h.attrs['aria-valuenow'],'50');assert.equal(h.stored.size,0);assert.equal(h.classes.has('domain-panel-resizing'),true);h.event('pointerup');assert.equal([...h.stored.values()][0],'50');assert.equal(h.classes.size,0);assert.equal(h.renders(),0);
});
test('escape and pointer cancellation restore the starting width without persisting',()=>{
 for(const cancel of ['Escape','pointercancel']){const h=harness();h.event('pointerdown');h.event('pointermove',{clientX:532});if(cancel==='Escape')h.event('keydown',{key:'Escape'});else h.event('pointercancel');assert.equal(h.attrs['aria-valuenow'],'65');assert.equal(h.stored.size,0);assert.equal(h.classes.size,0);}
});
test('minimum widths, reset and storage failures have safe fallbacks',()=>{
 const h=harness();h.event('keydown',{key:'Home'});assert.equal(h.attrs['aria-valuenow'],'32');h.event('keydown',{key:'End'});assert.equal(h.attrs['aria-valuenow'],'70');h.event('dblclick');assert.equal(h.attrs['aria-valuenow'],'65');assert.equal(h.stored.size,0);h.ctx.localStorage.getItem=()=>{throw Error('blocked');};h.ctx.localStorage.setItem=()=>{throw Error('blocked');};h.event('keydown',{key:'ArrowLeft'});assert.equal(h.attrs['aria-valuenow'],'63');
});
test('resizing has no card, model, publication or project-data operation',()=>{
 const h=harness();h.ctx.command=()=>{throw Error('No backend write belongs in layout adjustment');};h.ctx.state.privateDraft='unchanged';h.event('pointerdown');h.event('pointermove',{clientX:532});h.event('pointerup');assert.equal(h.ctx.state.privateDraft,'unchanged');assert.equal(h.renders(),0);
});

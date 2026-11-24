const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../src/workbench/static/app.js'),'utf8').split('function reviewerPanelHeight')[1];
function layout(kind,{bottom=1800,top=160,viewport=720,stacked=false}={}){
 const attrs=new Map(),classes=new Set(),events={},queue=[],input={value:'Unsent question',selectionStart:4};
 const reference={isConnected:true,getBoundingClientRect:()=>({left:stacked?700:100,right:stacked?1000:650,bottom})};
 const parent={querySelector:()=>reference,matches:s=>s==='.domain-working-layout'&&kind==='chat-console'};
 const panel={parentElement:parent,input,matches:s=>s.split(',').some(x=>x.trim()==='.'+kind),getBoundingClientRect:()=>({left:700,right:1000,top}),style:{getPropertyValue:k=>attrs.get(k)||'',setProperty:(k,v)=>attrs.set(k,v),removeProperty:k=>attrs.delete(k)},classList:{add:k=>classes.add(k),remove:k=>classes.delete(k)}};
 const c={document:{querySelector:()=>({getBoundingClientRect:()=>({bottom:80})}),querySelectorAll:s=>s.includes('.'+kind)?[panel]:[]},window:{innerHeight:viewport,addEventListener:(k,f)=>events[k]=f},requestAnimationFrame:f=>queue.push(f),MutationObserver:class{observe(){}},ResizeObserver:class{observe(){}unobserve(){}}};
 vm.createContext(c);vm.runInContext('function reviewerPanelHeight'+source,c);const flush=()=>{while(queue.length)queue.shift()();};flush();
 return{attrs,classes,input,resize:height=>{c.window.innerHeight=height;events.resize();flush();}};
}
for(const kind of ['sponsor-coach','chat-console','field-coach','coach-panel','personal-chat-console'])test(kind+' keeps the composer within the viewport and retains its draft on resizing',()=>{
 const h=layout(kind);assert.equal(h.attrs.get('--reviewer-panel-height'),'544px');assert.ok(h.classes.has('reviewer-viewport-fit'));
 h.resize(640);assert.equal(h.attrs.get('--reviewer-panel-height'),'464px');assert.equal(h.input.value,'Unsent question');assert.equal(h.input.selectionStart,4);
});
test('a shorter adjacent module determines the common baseline',()=>{assert.equal(layout('sponsor-coach',{bottom:620}).attrs.get('--reviewer-panel-height'),'460px');});
test('stacked field guidance flows normally instead of inheriting a sidebar height',()=>{const h=layout('field-coach',{stacked:true});assert.equal(h.classes.has('reviewer-viewport-fit'),false);assert.equal(h.attrs.size,0);});

const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
function harness(info){
 const calls=[],dialogs=[],imports=[],esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const ctx={chatInfo:()=>info,esc,label:r=>r.id+':v'+r.revision,date:s=>String(s||''),
  domainText:(name,title,value)=>`<label>${esc(title)}<textarea name="${name}">${esc(value)}</textarea></label>`,
  projectFlow:()=>({tools:{links:{research_figjam:'https://www.figma.com/board/Proj1/Team'}}}),
  modal:(title,body,submit,handler,options)=>dialogs.push({title,body,submit,handler,options}),
  command:(action,data)=>{calls.push({action,data});return {};},
  openToolImport:async prefill=>imports.push(prefill)};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,'..','src','workbench','static','domain-flows.js'),'utf8'),ctx);
 return {ctx,calls,dialogs,imports};
}
const flow={ref:{id:'FLOW-1',revision:2},body:{title:'Journey <b>',diagram:'flowchart LR\n A --> B',at:'2026-11-21'},exports:[
 {ref:{id:'FX-2',revision:1},body:{flow:{id:'FLOW-1',revision:2},title:'Journey <b>',diagram:'flowchart LR\n A --> B',status:'staged',url:'',at:'x'}},
 {ref:{id:'FX-1',revision:3},body:{flow:{id:'FLOW-1',revision:1},status:'sent',board_url:'https://www.figma.com/board/Abc/Flow',at:'y'}}]};

test('the action appears only where user-flow export is configured',()=>{
 assert.equal(harness({user_flows:{enabled:false,flows:[]}}).ctx.domainFlowActions(),'');
 assert.match(harness({user_flows:{enabled:true,flows:[]}}).ctx.domainFlowActions(),/data-action="flow-open">User flows</);
});

test('flows are listed escaped and editing saves a new version of the same flow',async()=>{
 const h=harness({user_flows:{enabled:true,flows:[flow]}});
 await h.ctx.domainFlowAction('flow-open');assert.doesNotMatch(h.dialogs[0].body,/<b>/);assert.match(h.dialogs[0].body,/Staged · nothing sent/);
 await h.ctx.domainFlowAction('flow-edit','FLOW-1');const d=h.dialogs[1];
 assert.match(d.body,/Review & create in FigJam/);assert.match(d.body,/Earlier flow version/);
 d.handler(new Map([['title','Journey'],['diagram','flowchart LR\n A --> C']]));
 assert.deepEqual(JSON.parse(JSON.stringify(h.calls[0])),{action:'domain-flow-save',data:{flow:{id:'FLOW-1',revision:2},title:'Journey',diagram:'flowchart LR\n A --> C'}});
});

test('staging offers the project FigJam board and sending requires an explicit confirmed command',async()=>{
 const h=harness({user_flows:{enabled:true,flows:[flow]}});
 await h.ctx.domainFlowAction('flow-stage','FLOW-1');assert.match(h.dialogs[0].body,/Proj1\/Team/);
 h.dialogs[0].handler(new Map([['url','']]));
 assert.deepEqual(JSON.parse(JSON.stringify(h.calls[0])),{action:'domain-flow-stage',data:{flow:{id:'FLOW-1',revision:2},url:''}});
 await h.ctx.domainFlowAction('flow-send','FX-2');assert.match(h.dialogs[1].body,/new board in your FigJam drafts/);assert.match(h.dialogs[1].body,/never retried automatically/);
 h.dialogs[1].handler();assert.deepEqual(JSON.parse(JSON.stringify(h.calls[1])),{action:'domain-flow-send',data:{export:{id:'FX-2',revision:1},confirm:true}});
});

test('a confirmed board is pulled back through the existing FigJam import',async()=>{
 const h=harness({user_flows:{enabled:true,flows:[flow]}});
 await h.ctx.domainFlowAction('flow-pull','FX-1');
 assert.deepEqual(JSON.parse(JSON.stringify(h.imports)),[{provider:'figjam',url:'https://www.figma.com/board/Abc/Flow'}]);
 assert.equal(await h.ctx.domainFlowAction('proto-open'),false);
});

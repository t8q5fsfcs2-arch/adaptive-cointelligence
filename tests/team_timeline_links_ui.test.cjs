const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(){
 const handlers={},frames=[],events=[],nodes=new Map();
 const document={addEventListener:(name,fn)=>(handlers[name]??=[]).push(fn),getElementById:()=>null,querySelector:selector=>nodes.get(selector)||null,querySelectorAll:()=>[]};
 const a={key:'A',ref:{id:'REQ',revision:1},title:'Decision',owner_name:'Alex',status:'Waiting',category:'Required review'},b={key:'B',ref:{id:'ISSUE',revision:2},title:'Assessment',owner_name:'Lee',status:'Pending',category:'Required review'},c={key:'C',ref:{id:'REPORT',revision:1},title:'Other work',owner_name:'Sam'};
 const links=[{from_key:'A',to_key:'B',kind:'waiting',label:'Alex is awaiting Lee’s required review',evidence_refs:[a.ref,b.ref]}];
 const context={state:{bridge:{team_timeline:{items:[a,b,c],connections:links}}},document,window:{addEventListener(){}},Date,Intl,Map,Set,Number,Math,setTimeout,clearTimeout,requestAnimationFrame:fn=>frames.push(fn),esc:v=>String(v??''),button:()=>'',modal:()=>{},closeModal:()=>events.push('closeModal')};
 vm.createContext(context);
 for(const file of ['team-timeline.js','team-timeline-links.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static',file),'utf8'),context);
 return {context,handlers,frames,events,nodes,run:code=>vm.runInContext(code,context)};
}
test('only direct recorded relations are selected; unrelated bars remain unconnected',()=>{
 const h=harness();assert.equal(h.run('teamTimelineRelations(state.bridge.team_timeline.items[0]).length'),1);
 assert.equal(h.run('teamTimelineRelations(state.bridge.team_timeline.items[1]).length'),1);
 assert.equal(h.run('teamTimelineRelations(state.bridge.team_timeline.items[2]).length'),0);
 assert.equal(h.run('teamTimelinePinnedKey'),null);
});
test('grouped publication markers retain member connections without inventing links',()=>{
 const h=harness();h.run("teamTimelineDisplayItems.set('GROUP',{key:'GROUP',members:[state.bridge.team_timeline.items[1],state.bridge.team_timeline.items[2]]})");
 assert.equal(h.run("teamTimelineRelations(teamTimelineResolveKey('GROUP')).length"),1);
});
test('pinned traces allow related hover detail and suppress unrelated cards',()=>{
 const h=harness();h.run("teamTimelinePinnedKey='A'");
 assert.equal(h.run('teamTimelineTraceAllows(state.bridge.team_timeline.items[1])'),true);
 assert.equal(h.run('teamTimelineTraceAllows(state.bridge.team_timeline.items[2])'),false);
 h.context.unrelated={dataset:{teamTimelineKey:'C'}};
 h.run('teamTimelineShow(unrelated)');assert.equal(h.run('teamTimelineAnchor'),null);
});
test('waiting arrows point from the waiting owner to the responder around bar ends',()=>{
 const h=harness();h.context.a={right:200,top:300,height:30};h.context.b={left:50,right:200,top:100,height:30};h.context.bounds={left:0,top:0};
 assert.equal(h.run("teamTimelineConnectorPath(a,b,bounds,'waiting',0,400)"),'M200 315H212V115H200');
 assert.equal(h.run("teamTimelineConnectorPath(a,b,bounds,'waiting',1,400)"),'M200 315H217V115H200');
});
test('connection explanations stay with the selected item in accessible text',()=>{
 const h=harness();const html=h.run('teamTimelineDetail(state.bridge.team_timeline.items[0])');
 assert.match(html,/Connections/);assert.match(html,/Alex is awaiting Lee’s required review/);
 const unrelated=h.run('teamTimelineDetail(state.bridge.team_timeline.items[2])');assert.doesNotMatch(unrelated,/Connections/);
});
test('routes clear bar text and stay anchored when horizontal scrolling shifts the content',()=>{
 const h=harness();h.context.a={right:200,top:300,height:30};h.context.b={left:50,right:200,top:100,height:30};h.context.bounds={left:0,top:0,protectedRight:250};
 const original=h.run("teamTimelineConnectorPath(a,b,bounds,'shared-input',0,400)");assert.match(original,/H262/);
 h.context.a.right-=80;h.context.b.left-=80;h.context.b.right-=80;h.context.bounds.left-=80;
 assert.equal(h.run("teamTimelineConnectorPath(a,b,bounds,'shared-input',0,400)"),original);
 const handoff=h.run("teamTimelineConnectorPath(a,b,bounds,'handoff',0,400)");
 assert.match(handoff,/V332H262V132/);
});
test('pinning closes only the read-only detail and schedules local drawing, without a command',()=>{
 const h=harness();const pin={dataset:{teamTimelinePin:'A'}};
 const event={target:{closest:selector=>selector==='[data-team-timeline-pin]'?pin:null}};
 for(const handler of h.handlers.click)handler(event);
 assert.deepEqual(h.events,['closeModal']);assert.equal(h.run('teamTimelinePinnedKey'),'A');assert.equal(h.frames.length,1);
});
test('escape clears a pinned trace and preserves the normal modal escape path',()=>{
 const h=harness();let stopped=false;h.run("teamTimelinePinnedKey='A'");
 for(const handler of h.handlers.keydown)handler({key:'Escape',stopPropagation:()=>stopped=true});
 assert.equal(h.run('teamTimelinePinnedKey'),null);assert.equal(stopped,true);
 h.run("teamTimelinePinnedKey='A'");h.nodes.set('#modal[open]',{});
 for(const handler of h.handlers.keydown)handler({key:'Escape',stopPropagation(){}});
 assert.equal(h.run('teamTimelinePinnedKey'),'A');
});

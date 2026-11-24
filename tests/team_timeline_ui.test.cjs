const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(items=[]){
 const listeners={},windowListeners={},dialogs=[];
 const esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
 const context={state:{bridge:{team_timeline:{items}}},Date,Intl,Map,Number,Math,setTimeout,clearTimeout,esc,
  document:{addEventListener:(name,callback)=>listeners[name]=callback,getElementById:()=>null},
  window:{addEventListener:(name,callback)=>windowListeners[name]=callback},
  modal:(...args)=>dialogs.push(args),button:(text,action,id)=>`<button data-action="${action}" data-id="${esc(id)}">${esc(text)}</button>`};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/team-timeline.js'),'utf8'),context);
 return {context,listeners,dialogs,run:code=>vm.runInContext(code,context)};
}
const sample=(key='ONE',changes={})=>({key,ref:{id:key,revision:3},title:'Clarify <unknown> route',category:'Decisions & Issues',status:'Investigating',team:'design',team_label:'Design',owner:'lee',owner_name:'Lee',start_at:'2026-11-14T12:00:00Z',elapsed_since:'2026-11-14T12:00:00Z',elapsed_label:'Pending',action:'bridge-open',action_id:key,...changes});
const now=Date.parse('2026-11-17T12:00:00Z');
test('timeline renders real owners, elapsed labels, keyboard scroll region and escaped titles',()=>{
 const h=harness([sample()]);h.context.now=now;
 const html=h.run('projectTeamTimeline(now)');
 assert.match(html,/Horizontal team project timeline" tabindex="0"/);
 assert.match(html,/Clarify &lt;unknown>/);assert.match(html,/Lee · Investigating/);assert.match(html,/Pending 3d/);
 assert.match(html,/Bars span recorded elapsed time/);assert.doesNotMatch(html,/overdue|accepted|<unknown>/i);
});
test('unknown times have a separate date bucket and never become today or overdue',()=>{
 const h=harness([sample('UNDATED',{start_at:null,elapsed_since:null,milestone:true})]);h.context.now=now;
 const html=h.run('projectTeamTimeline(now)');
 assert.match(html,/Date not recorded/);assert.match(html,/Publication date not recorded/);
 assert.doesNotMatch(html,/Pending 3d|overdue/i);
 assert.match(h.run('teamTimelineDetail(state.bridge.team_timeline.items[0],now)'),/Date not set/);
});
test('recorded holds and simultaneous work remain visible without drawers',()=>{
 const items=[sample('A',{delay:'Waiting for information',delay_since:'2026-11-16T12:00:00Z'}),sample('B'),sample('C')];
 const h=harness(items);h.context.now=now;const html=h.run('projectTeamTimeline(now)');
 assert.match(html,/team-timeline-waiting/);assert.match(html,/Waiting for information/);assert.doesNotMatch(html,/<details|<summary|data-team-timeline-expand/);
 for(const item of items)assert.match(html,new RegExp('data-team-timeline-key="'+item.key+'"'));
});
test('closed elapsed time stops at its recorded end and invalid date order is explicit',()=>{
 const h=harness();h.context.now=now;
 assert.equal(h.run("teamTimelineElapsed('2026-11-14T12:00:00Z','2026-11-15T12:00:00Z',now)"),'1d');
 assert.equal(h.run("teamTimelineElapsed('2026-11-18T12:00:00Z',null,now)"),'Check recorded dates');
 assert.equal(h.run("teamTimelineElapsed(null,null,now)"),'Time not recorded');
});
test('long histories and far future or undated records stay bounded and accessible',()=>{
 const h=harness([sample('OLD',{start_at:'2000-01-01T12:00:00Z',elapsed_since:'2000-01-01T12:00:00Z',closed:true,end_at:'2000-01-02T12:00:00Z'}),sample('FUTURE',{start_at:'2050-01-01T12:00:00Z',elapsed_since:'2050-01-01T12:00:00Z'}),sample('MISSING',{start_at:null,elapsed_since:null})]);h.context.now=now;
 const html=h.run('projectTeamTimeline(now)');assert.match(html,/Earlier work/);assert.match(html,/Later records/);assert.match(html,/Date not recorded/);
 const columns=Number(html.match(/data-team-timeline-columns="(\d+)"/)[1]);assert(columns<=41);
});
test('selecting a box opens a read-only detail with the native source action and no command',()=>{
 const h=harness([sample()]);const attrs={};
 const anchor={dataset:{teamTimelineKey:'ONE'},removeAttribute:key=>delete attrs[key]};
 h.listeners.click({target:{closest:()=>anchor}});
 assert.equal(h.dialogs.length,1);assert.match(h.dialogs[0][1],/data-action="bridge-open" data-id="ONE"/);
 assert.match(h.dialogs[0][1],/does not change ownership, requirements or approvals/);
});
test('hover and keyboard focus expose the same contextual detail, escape dismisses it',()=>{
 const h=harness([sample()]);let current=null;
 h.context.window.innerWidth=900;h.context.window.innerHeight=800;
 h.context.document.createElement=()=>({style:{},setAttribute(){},getBoundingClientRect:()=>({width:350,height:300}),addEventListener(){},remove(){current=null}});
 h.context.document.body={append:node=>current=node};h.context.document.getElementById=()=>current;
 const attrs={},anchor={dataset:{teamTimelineKey:'ONE'},setAttribute:(k,v)=>attrs[k]=v,removeAttribute:k=>delete attrs[k],getBoundingClientRect:()=>({left:790,top:400,bottom:464})};
 h.listeners.focusin({target:{closest:()=>anchor}});
 assert.match(current.innerHTML,/Owner \/ next responder/);assert.equal(attrs['aria-describedby'],'team-timeline-tooltip');
 assert(Number.parseFloat(current.style.left)<=542);
 let stopped=false;h.listeners.keydown({key:'Escape',stopPropagation:()=>stopped=true});
 assert.equal(current,null);assert.equal(stopped,true);assert.equal(attrs['aria-describedby'],undefined);
});
test('empty projection uses a truthful empty state',()=>{
 assert.match(harness().run('projectTeamTimeline()'),/will appear here when recorded/);
});
test('numbered project days retain a stable origin while actual dates stay in contextual detail',()=>{
 const h=harness([sample()]);h.context.now=now;
 h.context.state.bridge.team_timeline.origin_at='2026-11-13T12:00:00Z';
 const html=h.run('projectTeamTimeline(now)');
 assert.match(html,/>Day 2<\/span>/);assert.match(html,/>Day 5 · Now<\/span>/);assert.doesNotMatch(html,/Scroll horizontally|Shared work by team/);
 const detail=h.run('teamTimelineDetail(state.bridge.team_timeline.items[0],now)');
 assert.match(detail,/Nov/);
 assert.equal(h.run("teamTimelineDayNumber(Date.parse('2026-11-03T12:00:00Z'),Date.parse('2026-10-31T12:00:00Z'))"),4);
});

test('work spans exact multi-day intervals and parallel tasks use independent rows',()=>{
 const h=harness([sample('A'),sample('B',{elapsed_since:'2026-11-15T12:00:00Z',start_at:'2026-11-15T12:00:00Z'})]);h.context.now=now;
 const model=h.run('teamTimelineModel(state.bridge.team_timeline.items,"2026-11-13T12:00:00Z",now)');
 assert.equal(model.lanes[0].bars[0].x,1);assert.equal(model.lanes[0].bars[0].width,3);
 assert.equal(model.lanes[0].bars[1].x,2);assert.equal(model.lanes[0].bars[1].width,2);
 assert.equal(model.lanes[0].rows,2);
 const html=h.run('projectTeamTimeline(now)');assert.match(html,/data-team-span="3"/);assert.doesNotMatch(html,/style=/);
});

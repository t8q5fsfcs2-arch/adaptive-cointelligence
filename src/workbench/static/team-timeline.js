'use strict';

// A dated view of shared actions, not an estimate of effort or an inferred plan.
function teamTimelineTime(value){
 if(!value)return null;
 const at=Date.parse(value);return Number.isFinite(at)?at:null;
}
function teamTimelineElapsed(since,end,now=Date.now()){
 const start=teamTimelineTime(since),finish=end?teamTimelineTime(end):now;
 if(start===null||finish===null)return 'Time not recorded';
 if(start>finish)return 'Check recorded dates';
 const minutes=Math.floor((finish-start)/60000);
 if(minutes<1)return 'under 1 min';
 if(minutes<60)return `${minutes} min`;
 const hours=Math.floor(minutes/60);
 if(hours<24)return `${hours}h${minutes%60?' '+minutes%60+'m':''}`;
 const days=Math.floor(hours/24);return `${days}d${hours%24?' '+hours%24+'h':''}`;
}
function teamTimelineDay(at){
 const date=new Date(at);return new Date(date.getFullYear(),date.getMonth(),date.getDate()).getTime();
}
function teamTimelineDayNumber(day,origin){
 const ordinal=at=>{const date=new Date(at);return Date.UTC(date.getFullYear(),date.getMonth(),date.getDate());};
 return Math.round((ordinal(day)-ordinal(origin))/86400000)+1;
}
function teamTimelineDate(value){
 const at=teamTimelineTime(value);return at===null?'Not recorded':new Date(at).toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});
}
function teamTimelineTiming(item,now){
 if(item.milestone)return item.start_at?'Published '+new Date(item.start_at).toLocaleDateString(undefined,{month:'short',day:'numeric'}):'Publication date not recorded';
 if(item.closed&&!item.end_at)return 'End time not recorded';
 return item.elapsed_since?`${item.elapsed_label} ${teamTimelineElapsed(item.elapsed_since,item.end_at,now)}`:'Responder timing not recorded';
}
function teamTimelineDetail(item,now=Date.now(),compact=false){
 if(item.members&&compact)return item.members.slice(0,3).map(member=>{
  const links=typeof teamTimelineRelations==='function'?teamTimelineRelations(member):[];
  return `<div class="team-timeline-group-item"><h3>${esc(member.title)}</h3><p>${esc(member.owner_name+' · '+teamTimelineTiming(member,now))}</p>${links.length?`<p>${esc(links[0].label)}</p>`:''}</div>`;
 }).join('')+(item.members.length>3?`<p>${item.members.length-3} additional records · select for full details</p>`:'');
 if(item.members)return item.members.slice(0,compact?3:item.members.length).map(member=>`<div class="team-timeline-group-item"><h3>${esc(member.title)}</h3><dl>${teamTimelineDetail(member,now,compact)}</dl></div>`).join('')+(compact&&item.members.length>3?`<p>${item.members.length-3} additional records · select for full details</p>`:'');
 const next=item.next_action||'',question=compact&&next.length>160?next.slice(0,157)+'…':next;
 const fields=[['Owner / next responder',item.owner_name],['Status',item.status],
  ['Recorded action',teamTimelineDate(item.start_at)],['Elapsed',teamTimelineTiming(item,now)],
  ...(item.delay?[['Waiting / hold',item.delay+(item.delay_since?' · '+teamTimelineElapsed(item.delay_since,null,now):' · start not recorded')]]:[]),
  ['Due date','Date not set'],...(question?[['Next action',question]]:[]),
  ...(!compact&&item.detail?[['Context',item.detail]]:[]),...(!compact?[['Source',`${item.category} · ${item.ref.id} · v${item.ref.revision}`]]:[])];
 const links=typeof teamTimelineRelations==='function'?teamTimelineRelations(item):[];
 if(links.length)fields.push(['Connections',links.slice(0,compact?2:links.length).map(link=>link.label).join('\n')]);
 return fields.map(([name,value])=>`<div class="team-timeline-detail-row"><dt>${esc(name)}</dt><dd>${esc(value||'Not recorded')}</dd></div>`).join('');
}
const teamTimelineDisplayItems=new Map();
function teamTimelineGroup(key,title,members){
 const group={...members[0],key,title,members,owner_name:[...new Set(members.map(item=>item.owner_name))].join(', '),status:members.length+' shared records',action:null};
 teamTimelineDisplayItems.set(key,group);return group;
}
function teamTimelineModel(items,originAt,now){
 const day=86400000,dated=items.map(item=>teamTimelineTime(item.elapsed_since||item.start_at)).filter(at=>at!==null);
 const recordedOrigin=teamTimelineTime(originAt),origin=recordedOrigin??(dated.length?Math.min(...dated):now);
 const current=Math.max(0,(now-origin)/day),first=Math.max(0,Math.floor(current)-30),count=Math.min(31,Math.max(1,Math.floor(current)-first+1));
 const lanes=new Map(),outside=new Set();
 for(const item of items){if(!lanes.has(item.team))lanes.set(item.team,{key:item.team,label:item.team_label,items:[],bars:[],milestones:new Map(),outside:{},rows:0});lanes.get(item.team).items.push(item);}
 for(const lane of lanes.values()){
  const work=[];
  for(const item of lane.items){
   const stamp=teamTimelineTime(item.elapsed_since||item.start_at),finish=item.closed?teamTimelineTime(item.end_at):now;
   let bucket=stamp===null||(!item.milestone&&!item.elapsed_since)?'undated':stamp>origin+(first+count)*day?'later':(item.milestone?stamp:finish)!==null&&(item.milestone?stamp:finish)<origin+first*day?'earlier':null;
   if(item.closed&&(finish===null||stamp!==null&&finish<stamp))bucket='undated';
   if(bucket){outside.add(bucket);(lane.outside[bucket]??=[]).push(item);continue;}
   const x=Math.max(0,(stamp-origin)/day-first),end=Math.min(count,(finish-origin)/day-first);
   if(item.milestone){const key=Math.floor(x);if(!lane.milestones.has(key))lane.milestones.set(key,[]);lane.milestones.get(key).push(item);continue;}
   work.push({item,x,end:Math.max(x,end),width:Math.max(0,end-x)});
  }
  const ends=[];
  work.sort((a,b)=>Number(a.item.closed)-Number(b.item.closed)||a.x-b.x||a.item.title.localeCompare(b.item.title));
  for(const node of work){let row=ends.findIndex(end=>end<=node.x);if(row<0)row=ends.length;ends[row]=node.end+0.06;node.row=row;lane.bars.push(node);}
  lane.rows=ends.length;
 }
 const order=label=>/sponsor/i.test(label)?0:/research/i.test(label)?1:/design/i.test(label)?2:/requirement owner/i.test(label)?3:4;
 return {origin,recordedOrigin,current,first,count,outside:['earlier','later','undated'].filter(key=>outside.has(key)),lanes:[...lanes.values()].sort((a,b)=>order(a.label)-order(b.label)||a.label.localeCompare(b.label))};
}
function projectTeamTimeline(now=Date.now()){
 const items=state.bridge?.team_timeline?.items||[];
 if(!items.length)return '<p class="caption">Shared assignments, published work and accountability actions will appear here when recorded.</p>';
 if(typeof teamTimelineResetTrace==='function')teamTimelineResetTrace();
 teamTimelineDisplayItems.clear();
 const model=teamTimelineModel(items,state.bridge?.team_timeline?.origin_at,now),width=model.count+model.outside.length;
 const attrs=item=>`data-team-timeline-key="${esc(item.key)}" aria-label="${esc(item.title+' · '+item.owner_name+' · '+item.status+' · '+teamTimelineTiming(item,now)+(item.delay?' · '+item.delay:''))}" aria-haspopup="dialog"`;
 const title=item=>item.title.replace(/^SIMULATION\s*[—–-]\s*/i,'').replace(/^(Research|Design)\s*[—–-]\s*/i,'');
 const bar=node=>{
  const item=node.item,small=node.width<0.15,elapsed=teamTimelineElapsed(item.elapsed_since,item.end_at,now);
  return `<button type="button" class="team-timeline-item team-timeline-bar ${item.delay?'team-timeline-waiting':''} ${item.closed?'team-timeline-closed':''} ${small?'team-timeline-short':node.width<1.3?'team-timeline-narrow':''}" ${attrs(item)} data-team-x="${node.x}" data-team-span="${node.width}" data-team-row="${node.row}"><span class="team-timeline-item-title">${esc(title(item))}</span><span class="team-timeline-item-owner">${esc(item.owner_name+' · '+elapsed)}</span></button>`;
 };
 const labels={earlier:'Earlier work',later:'Later records',undated:'Date not recorded'};
 const nowLine=`<span class="team-timeline-now" data-team-x="${model.current-model.first}" aria-hidden="true"></span>`;
 if(typeof requestAnimationFrame==='function')requestAnimationFrame(teamTimelineArrange);
 return `<div class="team-timeline-scroll" role="region" aria-label="Horizontal team project timeline" tabindex="0"><div class="team-timeline-grid" data-team-timeline-columns="${width}">
 <div class="team-timeline-grid-row team-timeline-axis"><div class="team-timeline-label">Team</div><div class="team-timeline-track team-timeline-axis-track" data-team-width="${width}">${Array.from({length:model.count},(_,index)=>`<span class="team-timeline-date" title="${esc(teamTimelineDate(new Date(model.origin+(model.first+index)*86400000).toISOString()))}">Day ${model.first+index+1}${Math.floor(model.current)===model.first+index?' · Now':''}</span>`).join('')}${model.outside.map(key=>`<span class="team-timeline-date team-timeline-outside-date">${labels[key]}</span>`).join('')}${nowLine}</div></div>
 ${model.lanes.map(lane=>{
  const pending=lane.items.filter(item=>!item.closed&&!item.milestone).length;
  const markers=[...lane.milestones.values()].map(members=>{
   const item=members.length===1?members[0]:teamTimelineGroup('publications:'+lane.key+':'+members[0].start_at,members.length+' shared publications',members);
   const stamp=teamTimelineTime(members[0].start_at),x=(stamp-model.origin)/86400000-model.first;
   return `<button type="button" class="team-timeline-publication" ${attrs(item)} data-team-x="${x}"><span aria-hidden="true"></span></button>`;
  }).join('');
  const undated=model.outside.map((bucket,index)=>{
   const members=lane.outside[bucket]||[];if(!members.length)return '';
   const item=members.length===1?members[0]:teamTimelineGroup(bucket+':'+lane.key,members.length+' '+labels[bucket].toLowerCase(),members);
   return `<button type="button" class="team-timeline-outside-item" ${attrs(item)} data-team-x="${model.count+index}">${members.length===1?esc(title(item)):members.length+' records'}</button>`;
  }).join('');
  return `<div class="team-timeline-grid-row team-timeline-lane"><div class="team-timeline-label"><strong>${esc(lane.label)}</strong><span>${pending} next ${pending===1?'action':'actions'}</span></div><div class="team-timeline-track" data-team-width="${width}" data-team-rows="${lane.rows}" data-team-markers="${lane.milestones.size?1:0}">${lane.bars.map(bar).join('')}${markers}${undated}${nowLine}</div></div>`;
 }).join('')}
 </div></div><div class="team-timeline-legend"><span><i class="team-timeline-key-dot"></i>Pending / working</span><span><i class="team-timeline-key-dot waiting"></i>Recorded wait / hold</span><span><i class="team-timeline-key-dot published"></i>Shared publication</span><span>Bars span recorded elapsed time. Exact dates and context in details.</span><span class="team-timeline-trace-status" aria-live="polite"></span><button type="button" class="team-timeline-clear" data-team-timeline-clear hidden>Clear trace</button></div>`;
}
function teamTimelineArrange(){
 const chart=document.querySelector('.team-timeline-grid');if(!chart)return;
 const dayWidth=parseFloat(getComputedStyle(chart).getPropertyValue('--team-timeline-day-width'))||144;
 const coarse=window.matchMedia?.('(pointer: coarse)').matches,step=coarse?48:34;
 for(const track of chart.querySelectorAll('.team-timeline-track')){
  const rows=Number(track.dataset.teamRows)||0,shown=rows,markers=Number(track.dataset.teamMarkers)||0;
  track.style.width=Number(track.dataset.teamWidth)*dayWidth+'px';
  if(!track.classList.contains('team-timeline-axis-track'))track.style.height=Math.max(44,shown*step+markers*24+8)+'px';
  for(const node of track.querySelectorAll('[data-team-x]')){
   node.style.left=Number(node.dataset.teamX)*dayWidth+'px';
   if(node.classList.contains('team-timeline-bar')){
    node.hidden=Number(node.dataset.teamRow)>=shown;
    node.style.top=4+Number(node.dataset.teamRow)*step+'px';
    node.style.width=Math.max(8,Number(node.dataset.teamSpan)*dayWidth)+'px';
   }else if(node.classList.contains('team-timeline-publication'))node.style.top=4+shown*step+'px';
  }
 }
 if(typeof teamTimelineRefreshTrace==='function')teamTimelineRefreshTrace();
}

let teamTimelineAnchor=null,teamTimelineHideTimer=null,teamTimelineDismissed=null;
function teamTimelineHide(){
 clearTimeout(teamTimelineHideTimer);
 if(typeof teamTimelineClearTrace==='function')teamTimelineClearTrace();
 document.getElementById('team-timeline-tooltip')?.remove();
 teamTimelineAnchor?.removeAttribute('aria-describedby');teamTimelineAnchor=null;
}
function teamTimelineItem(node){return teamTimelineDisplayItems.get(node?.dataset.teamTimelineKey)||state.bridge?.team_timeline?.items?.find(item=>item.key===node?.dataset.teamTimelineKey);}
function teamTimelineShow(anchor){
 if(anchor===teamTimelineDismissed)return;
 const item=teamTimelineItem(anchor);if(!item)return;
 if(typeof teamTimelineTraceAllows==='function'&&!teamTimelineTraceAllows(item))return;
 teamTimelineHide();teamTimelineAnchor=anchor;
 if(typeof teamTimelineTrace==='function')teamTimelineTrace(item);
 const tooltip=document.createElement('div');tooltip.id='team-timeline-tooltip';tooltip.className='team-timeline-tooltip';tooltip.setAttribute('role','tooltip');
 tooltip.innerHTML=`<strong>${esc(item.title)}</strong><dl>${teamTimelineDetail(item,Date.now(),true)}</dl>`;
 document.body.append(tooltip);anchor.setAttribute('aria-describedby',tooltip.id);
 const box=anchor.getBoundingClientRect(),width=tooltip.getBoundingClientRect().width;
 tooltip.style.left=Math.max(8,Math.min(box.left,window.innerWidth-width-8))+'px';
 const height=tooltip.getBoundingClientRect().height;
 tooltip.style.top=Math.max(8,box.bottom+8+height<=window.innerHeight?box.bottom+8:Math.min(box.top-height-8,window.innerHeight-height-8))+'px';
 tooltip.addEventListener('pointerenter',()=>clearTimeout(teamTimelineHideTimer));
 tooltip.addEventListener('pointerleave',()=>{teamTimelineHideTimer=setTimeout(teamTimelineHide,150);});
}
document.addEventListener('pointerover',event=>{
 const anchor=event.target.closest?.('[data-team-timeline-key]');if(anchor&&anchor!==teamTimelineAnchor)teamTimelineShow(anchor);
});
document.addEventListener('pointerout',event=>{
 const anchor=event.target.closest?.('[data-team-timeline-key]');
 if(anchor&&!anchor.contains(event.relatedTarget)){teamTimelineDismissed=null;teamTimelineHideTimer=setTimeout(teamTimelineHide,150);}
});
document.addEventListener('focusin',event=>{const anchor=event.target.closest?.('[data-team-timeline-key]');if(anchor)teamTimelineShow(anchor);});
document.addEventListener('focusout',event=>{if(event.target.closest?.('[data-team-timeline-key]')){teamTimelineDismissed=null;teamTimelineHideTimer=setTimeout(teamTimelineHide,150);}});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&teamTimelineAnchor){teamTimelineDismissed=teamTimelineAnchor;teamTimelineHide();event.stopPropagation();}},true);
document.addEventListener('scroll',event=>{if(!event.target.closest?.('#team-timeline-tooltip'))teamTimelineHide();},true);
window.addEventListener('resize',()=>{teamTimelineHide();teamTimelineArrange();});
document.addEventListener('click',event=>{
 const anchor=event.target.closest?.('[data-team-timeline-key]');if(!anchor)return;
 const item=teamTimelineItem(anchor);if(!item)return;
 teamTimelineHide();
 const names={'bridge-open':'Open issue','pflow-request':'Open Working brief','packet':'Inspect published packet','pflow-shared-brief':'Read shared Working brief','intake-case':'Open Business Intent review',case:'Open requirement review'};
 const links=typeof teamTimelineRelations==='function'?teamTimelineRelations(item):[];
 modal(item.title,`${links.length?`<button type="button" data-team-timeline-pin="${esc(item.key)}">Trace connections</button>`:''}<dl class="team-timeline-record-detail">${teamTimelineDetail(item)}</dl>${(item.members||[item]).filter(member=>member.action).map(member=>`<div class="actions">${button((names[member.action]||'Open shared record')+(item.members?' · '+member.title:''),member.action,member.action_id)}</div>`).join('')}<p class="caption">Shared records only. This view does not change ownership, requirements or approvals.</p>`,null,null);
});

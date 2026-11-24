'use strict';

let teamTimelinePinnedKey=null;
function teamTimelineRelations(item){
 const keys=new Set((item.members||[item]).map(member=>member.key));
 return (state.bridge?.team_timeline?.connections||[]).filter(link=>keys.has(link.from_key)||keys.has(link.to_key));
}
function teamTimelineResolveKey(key){return teamTimelineDisplayItems.get(key)||state.bridge?.team_timeline?.items?.find(item=>item.key===key);}
function teamTimelineTraceAllows(item){
 if(!teamTimelinePinnedKey)return true;
 const pinned=teamTimelineResolveKey(teamTimelinePinnedKey);if(!pinned)return true;
 const allowed=new Set([teamTimelinePinnedKey,...teamTimelineRelations(pinned).flatMap(link=>[link.from_key,link.to_key])]);
 return (item.members||[item]).some(member=>allowed.has(member.key));
}
function teamTimelineClearTrace(force=false){
 if(teamTimelinePinnedKey&&!force)return;
 document.querySelector('.team-timeline-connections')?.remove();
 document.querySelectorAll('.team-timeline-connected').forEach(node=>node.classList.remove('team-timeline-connected'));
 const status=document.querySelector('.team-timeline-trace-status');if(status)status.textContent='';
 const clear=document.querySelector('[data-team-timeline-clear]');if(clear)clear.hidden=true;
}
function teamTimelineResetTrace(){teamTimelinePinnedKey=null;teamTimelineClearTrace(true);}
function teamTimelineConnectorPath(a,b,bounds,kind,index,width){
 const waiting=kind==='waiting',x1=a.right-bounds.left,y1=a.top+a.height/2-bounds.top;
 const x2=(waiting?b.right:b.left)-bounds.left,y2=b.top+b.height/2-bounds.top;
 const elbow=Math.min(width-6,Math.max(x1,x2,bounds.protectedRight||0)+12+index*5);
 if(kind==='handoff')return `M${x1} ${y1}V${a.top+a.height-bounds.top+2}H${elbow}V${b.top+b.height-bounds.top+2}H${x2-6}V${y2}H${x2}`;
 return `M${x1} ${y1}H${elbow}V${y2}H${x2}`;
}
function teamTimelineTrace(item,pin=false){
 if(!item)return;
 if(pin)teamTimelinePinnedKey=item.key;
 else if(teamTimelinePinnedKey&&teamTimelinePinnedKey!==item.key)return;
 teamTimelineClearTrace(true);
 const chart=document.querySelector('.team-timeline-grid');if(!chart)return;
 const links=teamTimelineRelations(item),nodes=new Map();
 for(const node of chart.querySelectorAll('[data-team-timeline-key]')){
  const value=teamTimelineItem(node);if(value)for(const member of value.members||[value])nodes.set(member.key,node);
 }
 const pairs=[],seen=new Set();
 for(const link of links){
  const from=nodes.get(link.from_key),to=nodes.get(link.to_key);
  if(!from||!to||from===to)continue;
  const key=[from.dataset.teamTimelineKey,to.dataset.teamTimelineKey,link.kind].join('|');
  if(seen.has(key))continue;seen.add(key);pairs.push({link,from,to});
 }
 if(!pairs.length)return;
 const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');
 svg.classList.add('team-timeline-connections');svg.setAttribute('aria-hidden','true');
 const bounds=chart.getBoundingClientRect();
 bounds.protectedRight=Math.max(0,...Array.from(chart.querySelectorAll('.team-timeline-bar')).map(node=>node.getBoundingClientRect().right-bounds.left));
 svg.setAttribute('width',String(chart.scrollWidth));svg.setAttribute('height',String(chart.offsetHeight));
 svg.setAttribute('viewBox',`0 0 ${chart.scrollWidth} ${chart.offsetHeight}`);
 const defs=document.createElementNS(ns,'defs');
 for(const kind of ['handoff','waiting','shared-input']){
  const marker=document.createElementNS(ns,'marker');marker.id='timeline-arrow-'+kind;
  for(const [name,value] of Object.entries({viewBox:'0 0 6 6',refX:'5',refY:'3',markerWidth:'5',markerHeight:'5',orient:'auto'}))marker.setAttribute(name,value);
  const arrow=document.createElementNS(ns,'path');arrow.setAttribute('d','M0 0L6 3L0 6Z');arrow.setAttribute('class','team-timeline-arrow '+kind);marker.append(arrow);defs.append(marker);
 }
 svg.append(defs);
 pairs.forEach(({link,from,to},index)=>{
  from.classList.add('team-timeline-connected');to.classList.add('team-timeline-connected');
  const a=from.getBoundingClientRect(),b=to.getBoundingClientRect();
  const path=document.createElementNS(ns,'path');path.setAttribute('d',teamTimelineConnectorPath(a,b,bounds,link.kind,index,chart.scrollWidth));
  path.setAttribute('class','team-timeline-connection '+link.kind);path.setAttribute('marker-end','url(#timeline-arrow-'+link.kind+')');
  const title=document.createElementNS(ns,'title');title.textContent=link.label;path.append(title);svg.append(path);
 });
 chart.append(svg);
 const status=document.querySelector('.team-timeline-trace-status');
 if(status)status.textContent=links[0].label+(links.length>1?' · '+(links.length-1)+' other connection'+(links.length>2?'s':''):'');
 const clear=document.querySelector('[data-team-timeline-clear]');if(clear)clear.hidden=!teamTimelinePinnedKey;
}
function teamTimelineRefreshTrace(){
 const item=teamTimelinePinnedKey?teamTimelineResolveKey(teamTimelinePinnedKey):teamTimelineAnchor?teamTimelineItem(teamTimelineAnchor):null;
 if(item)teamTimelineTrace(item,!!teamTimelinePinnedKey);
}
document.addEventListener('click',event=>{
 const clear=event.target.closest?.('[data-team-timeline-clear]');
 if(clear){teamTimelineResetTrace();teamTimelineHide();return;}
 const pin=event.target.closest?.('[data-team-timeline-pin]');if(!pin)return;
 const item=teamTimelineResolveKey(pin.dataset.teamTimelinePin);if(!item)return;
 teamTimelinePinnedKey=item.key;closeModal();teamTimelineHide();
 requestAnimationFrame(()=>teamTimelineTrace(item,true));
});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'&&teamTimelinePinnedKey&&!document.querySelector('#modal[open]')){teamTimelineResetTrace();event.stopPropagation();}
},true);
document.addEventListener('scroll',()=>{if(teamTimelinePinnedKey)teamTimelineRefreshTrace();},true);

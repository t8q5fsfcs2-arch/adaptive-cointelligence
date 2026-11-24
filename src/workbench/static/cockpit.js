// Workbench as a cockpit (D010). Presentation only: the conversation stays dominant; a heads-up strip
// and an instrument rail put next moves and the existing workbench tools one click away. Every item is
// read from existing state. No AI output is generated or implied here.
const COCKPIT_ICONS={
 next:'<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5 13.5 13.5 8.5 15.5 10.5 10.5z"/>',
 suggest:'<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
 review:'<path d="M9 11l3 3 8-8"/><path d="M20 12v7H4V5h10"/>',
 brief:'<path d="M6 3h9l4 4v14H6z"/><path d="M9 12h7M9 16h5"/>',
 blocks:'<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
 flows:'<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.5 6H14a3 3 0 0 1 3 3v6.5"/>',
 proto:'<rect x="3" y="5" width="18" height="12" rx="2"/><path d="M8 21h8M12 17v4"/>',
 report:'<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
 updates:'<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
 changed:'<path d="M20 11a8 8 0 0 0-15-3M4 4v4h4M4 13a8 8 0 0 0 15 3M20 20v-4h-4"/>',
 quest:'<path d="M5 21V4h11l-2 4 2 4H5"/>',close:'<path d="M6 6l12 12M18 6 6 18"/>',asked:'<path d="M3 13h5l2 3h4l2-3h5"/><path d="M5 5h14l2 8v6H3v-6z"/>'
};
function cockpitIcon(name,size=18){return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${COCKPIT_ICONS[name]||''}</svg>`;}
function cockpitSide(){const k=state.domains?.active;return k==='research'?'problem':k==='design'?'solution':null;}
// The areas on this team's side where shared work would count most: lowest level first.
function cockpitAreas(){
 if(typeof caseAreas!=='function')return [];const side=cockpitSide(),order=['empty','low','moderate','high'];
 return caseAreas().filter(a=>(!side||a.side===side)&&a.level!=='high').sort((a,b)=>order.indexOf(a.level)-order.indexOf(b.level)).slice(0,2);
}
function cockpitQuest(){if(typeof casePublishedValues!=='function')return '';const v=casePublishedValues(),k=state.domains?.active;return String(k==='research'?v.research_question||'':k==='design'?v.operations_question||'':'').trim();}
function cockpitNeeds(){return typeof projectHomeNeeds==='function'?projectHomeNeeds(state.actor):[];}
function cockpitChanged(){return typeof chatContextChanged==='function'&&chatWork()?chatContextChanged():false;}
function cockpitNextCount(){return cockpitNeeds().length+(cockpitChanged()?1:0);}
function cockpitHud(){
 const changed=cockpitChanged(),area=cockpitAreas()[0],quest=cockpitQuest(),guide=typeof chatTaskGuidance==='function'?chatTaskGuidance().next:null;
 const cell=(icon,cls,title,sub,attrs)=>`<button type="button" class="cockpit-hud-cell ${cls}" ${attrs}><span class="cockpit-hud-title">${icon}<span>${esc(title)}</span></span><span class="cockpit-hud-sub">${esc(sub)}</span></button>`;
 return `<section class="cockpit-hud" aria-label="Where you stand">
 ${guide?cell(cockpitIcon('next',14),'is-next','Next: '+guide.title,guide.why||'',`data-action="${guide.action}" data-id="${esc(guide.id||'')}"`):''}
 ${changed?cell(cockpitIcon('changed',14),'is-changed','Inputs changed since you started','Review what moved before reusing this work','data-action="dchat-guidance-context"'):''}
 ${area?cell(typeof caseGlyph==='function'?caseGlyph(area.level):'','lv-'+area.level,area.label,`${CASE_LEVEL_WORD[area.level]} · ${area.next}`,`data-action="cockpit-area" data-id="${esc(area.id)}"`):''}
 ${quest?`<div class="cockpit-hud-cell is-quest" title="${esc(quest)}"><span class="cockpit-hud-title">${cockpitIcon('quest',14)}<span>${esc(quest)}</span></span><span class="cockpit-hud-sub">What your team is validating</span></div>`:''}
 </section>`;
}
// The instrument rail: the workbench's existing tools, plus Next moves, Reviews and Updates.
function cockpitRail(){
 const panel=domainPanel(),n=cockpitNextCount(),reviews=typeof chatReports==='function'?chatReports().length:0,updates=(state.domain_updates||[]).filter(u=>u.new).length;
 const item=(icon,label,action,o={})=>`<button type="button" class="workbench-section cockpit-instrument${o.on?' is-on':''}" data-action="${action}" ${o.panel?`aria-pressed="${!!o.on}" aria-expanded="${!!o.on}"`:'aria-haspopup="dialog"'}${o.controls?` aria-controls="${o.controls}"`:''}>${cockpitIcon(icon)}<span class="cockpit-instrument-label">${esc(label)}</span>${o.count?`<span class="workbench-count${o.tone?' is-'+o.tone:''}">${o.count}</span>`:''}</button>`;
 const blocks=typeof projectImplicationsPanel==='function',align=!blocks&&chatAlignmentRows().length;
 return `<nav class="chat-workspace-actions domain-working-actions cockpit-rail" aria-label="Workbench instruments">
 ${item('next','Next moves','cockpit-next',{panel:1,on:panel==='next',count:n,tone:'gold',controls:'cockpit-panel'})}
 ${item('suggest','Suggest','cockpit-suggest',{panel:1,on:panel==='suggest',count:cockpitSuggestions().length,tone:'accent',controls:'cockpit-panel'})}
 ${item('review','Reviews','cockpit-reviews',{panel:1,on:panel==='reviews',count:reviews,controls:'cockpit-panel'})}
 <span class="cockpit-rail-rule" aria-hidden="true"></span>
 ${item('brief','Brief','dchat-guidance-context')}
 ${blocks?item('blocks','Building blocks','dev-implications',{panel:1,on:panel==='implications',count:typeof knowledgeCards==='function'?knowledgeCards().length:0,controls:'project-implications-panel'}):align?item('blocks','Alignment','dchat-alignment-panel',{panel:1,on:panel==='alignment',count:chatAlignmentGroups().length,controls:'domain-alignment-panel'}):''}
 ${typeof domainFlowActions==='function'&&typeof flowInfo==='function'&&flowInfo().enabled?item('flows','User flows','flow-open',{count:(flowInfo().flows||[]).length}):''}
 ${typeof domainPrototypeActions==='function'&&state.domains?.active==='design'?item('proto','Prototype alternatives','proto-open'):''}
 ${item('report','Outcomes report','dchat-sharing-panel',{panel:1,on:panel==='sharing',controls:'domain-sharing-panel'})}
 ${item('updates','Updates','cockpit-updates',{panel:1,on:panel==='updates',count:updates,controls:'cockpit-panel'})}
 </nav>`;
}
function cockpitPanelHead(icon,title,note){return `<header class="cockpit-panel-head"><h2>${cockpitIcon(icon,16)}${esc(title)}</h2><button type="button" class="quiet small" data-action="dchat-panel-none" aria-label="Close ${esc(title)}">${cockpitIcon('close',13)}</button></header>${note?`<p class="caption">${esc(note)}</p>`:''}`;}
function cockpitRow(icon,cls,label,title,detail,control){return `<li class="cockpit-move ${cls}"><span class="cockpit-move-icon">${icon}</span><span class="cockpit-move-text"><span class="cockpit-move-label">${esc(label)}</span><span class="cockpit-move-title">${esc(title)}</span>${detail?`<span class="cockpit-move-detail">${esc(detail)}</span>`:''}</span>${control}</li>`;}
function cockpitNextPanel(){
 const guide=typeof chatTaskGuidance==='function'?chatTaskGuidance().next:null,needs=cockpitNeeds().slice(0,5),more=cockpitNeeds().length-needs.length,areas=cockpitAreas(),changed=cockpitChanged(),reviews=typeof chatReports==='function'?chatReports().length:0;
 const act=(text,attrs,primary)=>`<button type="button" class="${primary?'primary':'quiet'} small" ${attrs}>${esc(text)}</button>`;
 const rows=[
  ...(changed?[cockpitRow(cockpitIcon('changed',15),'is-changed','Changed','Inputs changed since you started','Your saved work is kept.',act('See change','data-action="dchat-guidance-context"'))]:[]),
  ...needs.map(n=>cockpitRow(cockpitIcon('asked',15),'is-asked',n.label,n.title,n.detail,act('Open',n.attrs,true))),
  ...(guide?[cockpitRow(cockpitIcon('next',15),'','In your work',guide.title,guide.why,act('Go',`data-action="${guide.action}" data-id="${esc(guide.id||'')}"`))]:[]),
  ...areas.map(a=>cockpitRow(typeof caseGlyph==='function'?`<span class="lv-${a.level}">${caseGlyph(a.level)}</span>`:'','','Your work counts here',`${a.label} · ${CASE_LEVEL_WORD[a.level]}`,a.next,act('Open area',`data-action="cockpit-area" data-id="${esc(a.id)}"`)))
 ];
 return `<aside id="cockpit-panel" class="domain-context-panel cockpit-panel" aria-label="Next moves">${cockpitPanelHead('next','Next moves','From the project and your own work. Your conversation stays open.')}
 ${rows.length?`<ul class="cockpit-moves">${rows.join('')}</ul>`:'<p class="caption">Nothing is waiting on you.</p>'}${more>0?`<p class="caption">${more} more on <a href="#main" data-nav="home">Project home</a>.</p>`:''}
 <p class="cockpit-panel-foot">${cockpitIcon('review',14)}<span>${reviews?`<strong>${reviews} saved review${reviews===1?'':'s'}</strong> of this work`:'No saved review of this work yet'}</span><button type="button" class="quiet small" data-action="cockpit-reviews">Reviews</button></p></aside>`;
}
// Saved reviews are the AI partner's recorded assessments of this work. Nothing is generated here.
function cockpitReviewsPanel(){
 const reports=typeof chatReports==='function'?chatReports():[];
 return `<aside id="cockpit-panel" class="domain-context-panel cockpit-panel" aria-label="Reviews">${cockpitPanelHead('review','Reviews','Saved AI partner reviews of this work. A review runs only when you ask for one.')}
 ${reports.length?`<ul class="cockpit-moves">${reports.map(r=>cockpitRow(cockpitIcon('review',15),'',(r.selection_current??r.current)?'Current':'Inputs changed since',typeof chatBatchName==='function'?chatBatchName(r.body.batch):'Review',typeof projectHomeDate==='function'?projectHomeDate(r.body.at||r.body.created_at||''):'',`<button type="button" class="quiet small" data-action="dchat-report" data-id="${esc(r.ref.id)}">Inspect</button>`)).join('')}</ul>`:'<p class="caption">No reviews saved yet.</p>'}
 <div class="evidence-actions"><button type="button" class="primary small" data-action="dchat-review-work">Ask for a review</button></div></aside>`;
}
function cockpitUpdatesPanel(){
 return `<aside id="cockpit-panel" class="domain-context-panel cockpit-panel" aria-label="Updates">${cockpitPanelHead('updates','Updates','Recorded decisions and published findings.')}${typeof projectUpdateFeed==='function'?projectUpdateFeed().replace('<details class="project-update-feed">','<details class="project-update-feed" open>'):''}</aside>`;
}
// Quiet suggestions (D011): the suggestions the AI partner already returned with its replies to this
// work, surfaced at the edge. A count on the rail is the only signal; nothing is inserted or generated here.
function cockpitSuggestInfo(){return state.quiet_suggestions||{enabled:true,dismissed:[],ref:null};}
function cockpitSuggestions(){
 const info=cockpitSuggestInfo();if(!info.enabled||typeof chatReports!=='function')return [];
 const gone=new Set(info.dismissed.map(d=>d.report+'|'+d.index)),out=[];
 for(const r of chatReports()){
  if(!(r.selection_current??r.current))continue;
  (r.body.output?.findings||r.body.output?.suggestions||[]).forEach((f,i)=>{if(!gone.has(r.ref.id+'|'+i))out.push({report:r.ref.id,index:i,title:f.issue||f.recommendation||f.observation||'Suggestion',detail:f.question||f.uncertainty||'',where:f.page?`Page ${f.page}${f.area?' · '+f.area:''}`:''});});
 }
 return out.slice(0,3);
}
function cockpitSuggestPanel(){
 const info=cockpitSuggestInfo(),items=cockpitSuggestions(),off=!info.enabled,down=typeof chatModelUnavailable==='function'&&chatModelUnavailable();
 const card=s=>`<li class="cockpit-suggestion"><span class="ac-state ac-state-suggested">Suggested · AI partner</span><span class="cockpit-move-title">${esc(s.title)}</span>${s.detail?`<span class="cockpit-move-detail">${esc(s.detail)}</span>`:''}${s.where?`<span class="cockpit-move-detail">${esc(s.where)}</span>`:''}<span class="cockpit-suggestion-actions"><button type="button" class="quiet small" data-action="dchat-report" data-id="${esc(s.report)}">Show me</button>${s.detail?`<button type="button" class="quiet small" data-action="cockpit-suggest-ask" data-id="${esc(s.report+'|'+s.index)}">Ask about it</button>`:''}<button type="button" class="quiet small" data-action="cockpit-suggest-dismiss" data-id="${esc(s.report+'|'+s.index)}">Dismiss</button></span></li>`;
 return `<aside id="cockpit-panel" class="domain-context-panel cockpit-panel" aria-label="Suggestions">${cockpitPanelHead('suggest','Suggestions','From your AI partner’s replies on this work. Private to you. They never block sharing.')}
 ${off?'<p class="caption">Quiet suggestions are off. Your AI partner still answers when you ask.</p>':items.length?`<ul class="cockpit-suggestions">${items.map(card).join('')}</ul>`:`<p class="caption">${down?'AI partner unavailable. Suggestions arrive with its replies once a model is connected.':'No open suggestions. They arrive with your AI partner’s replies.'}</p>`}
 <div class="evidence-actions">${!off&&items.length>1?'<button type="button" class="quiet small" data-action="cockpit-suggest-dismiss" data-id="all">Dismiss all</button>':''}<button type="button" class="quiet small" data-action="cockpit-suggest-toggle" aria-pressed="${!off}">${off?'Turn on':'Turn off'}</button></div></aside>`;
}
async function cockpitSuggestAction(action,id){
 const info=cockpitSuggestInfo();
 if(action==='cockpit-suggest-toggle'){try{const r=await command('suggestions-toggle',{expected:info.ref,enabled:!info.enabled});await load();renderDomainChat();toast(r.message);}catch(error){toast(error.message);}return true;}
 if(action==='cockpit-suggest-dismiss'){const items=id==='all'?cockpitSuggestions().map(s=>({report:s.report,index:s.index})):[{report:id.split('|')[0],index:Number(id.split('|')[1])}];if(!items.length)return true;
  try{const r=await command('suggestions-dismiss',{expected:info.ref,items});await load();renderDomainChat();toast(r.message);}catch(error){toast(error.message);}return true;}
 if(action==='cockpit-suggest-ask'){const s=cockpitSuggestions().find(x=>x.report+'|'+x.index===id);if(!s)return true;const d=chatDraft();d.text=s.detail;d.revision=(d.revision||0)+1;renderDomainChat();const box=document.getElementById('domain-chat-message');if(box){box.value=s.detail;box.focus();}return true;}
 return false;
}
function cockpitPanel(panel){if(panel==='suggest')return cockpitSuggestPanel();return panel==='next'?cockpitNextPanel():panel==='reviews'?cockpitReviewsPanel():panel==='updates'?cockpitUpdatesPanel():'';}
async function cockpitAction(action,id){
 if(action.startsWith('cockpit-suggest-'))return cockpitSuggestAction(action,id);
 const toggle={'cockpit-next':'next','cockpit-suggest':'suggest','cockpit-reviews':'reviews','cockpit-updates':'updates'}[action];
 if(toggle){if(typeof saveWorkingReport==='function')await saveWorkingReport();domainPanels.set(chatKey(),domainPanel()===toggle?null:toggle);renderDomainChat();return true;}
 if(action==='cockpit-area'){await navigateWorkspace('home');caseOpenArea=id;render();window.scrollTo(0,0);$('#main h1')?.focus();return true;}
 return false;
}

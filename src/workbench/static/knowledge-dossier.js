// Building block cards and dossier. Presentation over existing block data and actions only:
// every stat is read from the saved block, nothing is scored by a model, and editing stays one click away (D003).
const kcFamilies={finding:'evidence','user-situation':'evidence','user-flow':'flow','user-story':'flow',artifact:'artifact',hypothesis:'open',question:'open',challenge:'risk',dependency:'risk',implication:'risk','performance-goal':'goal',note:'note'};
function kcFamily(type){return kcFamilies[type]||'note';}
function kcIcon(type,size=18){return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${(typeof knowledgeCardIconPaths!=='undefined'&&knowledgeCardIconPaths[type])||(typeof knowledgeCardIconPaths!=='undefined'?knowledgeCardIconPaths.note:'')}"/></svg>`;}
function kcTypeLabel(type){return knowledgeCardInfo().types[type]?.label||type;}
function kcFields(row){return Object.entries(row.body.card?.fields||{}).filter(([,v])=>String(v||'').trim());}
function kcInReport(row){const sel=typeof submissionDraft==='function'?(submissionDraft()?.implication_refs||[]):[];return sel.find(v=>v.id===row.ref.id)||null;}
function kcSharedState(row,m){if(!m.shared)return null;return m.shared_source&&label(m.shared_source)===label(row.ref)?'current':'behind';}
function kcConnections(m){return (m.relations?.length||0)+(m.backlinks?.length||0);}
function kcLevel(row,m){
 const p=row.body.payload,steps=[
  ['statement','Captured what it says',!!p.statement?.trim(),null],
  ['rationale','Why it matters and its limits',!!p.rationale?.trim(),null],
  ['context',typeof knowledgeCardDetailsTitle==='function'?knowledgeCardDetailsTitle(kcMetaType(row,m)):'Details',kcFields(row).length>0,'context'],
  ['evidence','At least one source passage',(p.evidence||[]).length>0,'evidence'],
  ['links','Connected to another block or project item',kcConnections(m)>0,'links']];
 return {level:steps.filter(s=>s[2]).length,steps,next:steps.find(s=>!s[2])||null};
}
function kcMetaType(row,m){return (m||knowledgeCardMeta(row)).type;}
function kcCare(row,m){
 const tasks=[],type=kcMetaType(row,m),support=typeof implicationSupport==='function'?implicationSupport(row):{status:''};
 if(row.body.status==='dismissed')tasks.push({text:'Archived. Restore it to use it again.',action:'kc-archive',id:row.ref.id,label:'Restore'});
 if(type==='note')tasks.push({text:'Still a working note. Choose a more specific type.',action:'kc-edit-section',id:row.ref.id+'|type',label:'Choose type'});
 if((m.relations||[]).some(l=>l.changed))tasks.push({text:'A linked item has a newer version.',action:'kc-edit-section',id:row.ref.id+'|links',label:'Review links'});
 if(support.status==='earlier-basis')tasks.push({text:'Supporting inputs changed since you saved this.',action:'kc-edit-section',id:row.ref.id+'|evidence',label:'Review sources'});
 if(kcSharedState(row,m)==='behind')tasks.push({text:'You changed it privately after sharing. The shared copy keeps the earlier version.',action:'kc-shared',id:label(m.shared),label:'View shared copy'});
 return tasks;
}
function kcPips(level){return `<span class="kc-pips" aria-hidden="true">${[1,2,3,4,5].map(n=>`<span class="${n<=level?'is-on':''}"></span>`).join('')}</span>`;}
function kcAge(at){if(!at)return '';const d=Math.max(0,Math.floor((Date.now()-new Date(at).getTime())/86400000));return d===0?'today':d===1?'1 day ago':d+' days ago';}
function kcWhen(at){return at?(typeof date==='function'?date(at):at):'Not recorded';}
function kcOrigin(row){const b=row.body;if(b.origin_selection)return b.origin_selection.role==='user'?'Saved from your chat message':'Saved from an AI partner reply';const c=(b.captures||[])[0]?.origin;if(c)return c.review?'Captured from a review':'Captured from chat';return 'Added by hand';}

// Collection card (trading-card front).
function kcCard(row){
 const p=row.body.payload,m=knowledgeCardMeta(row),type=m.type,lv=kcLevel(row,m),care=kcCare(row,m),report=kcInReport(row),shared=kcSharedState(row,m);
 const badges=[report?'<span class="kc-badge kc-badge-report">In report</span>':'',shared?`<span class="kc-badge">${shared==='current'?'Shared':'Shared · changed'}</span>`:'',row.body.status==='suggested'?'<span class="kc-badge kc-badge-suggested">Suggested</span>':'',row.body.status==='dismissed'?'<span class="kc-badge">Archived</span>':''].join('');
 return `<article class="knowledge-card-row kc-card kc-fam-${kcFamily(type)}${care.length?' needs-care':''}">
 <div class="kc-card-band">${kcIcon(type,16)}<span>${esc(kKnowledgeTile(type))}</span><span class="kc-card-ver">v${row.ref.revision}</span></div>
 <h3><a href="#main" class="item-title-link kc-card-link" data-action="kc-open" data-id="${esc(row.ref.id)}">${esc(p.title)}</a></h3>
 <p class="knowledge-card-excerpt">${esc(p.statement.slice(0,120))}${p.statement.length>120?'…':''}</p>
 ${badges?`<div class="kc-badges">${badges}</div>`:''}
 <div class="kc-card-foot"><span class="kc-level" title="Completeness ${lv.level} of 5">${kcPips(lv.level)}<span class="sr-only">Completeness ${lv.level} of 5</span></span><span class="kc-mini-stats"><span title="Source passages">${(p.evidence||[]).length} src</span><span title="Connections">${kcConnections(m)} ${kcConnections(m)===1?'link':'links'}</span></span>${care.length?`<span class="kc-care-dot" title="${esc(care.length+' to look after')}">${care.length}<span class="sr-only"> to look after</span></span>`:''}</div>
</article>`;
}
function kKnowledgeTile(type){return (typeof knowledgeTileLabels!=='undefined'&&knowledgeTileLabels[type])||kcTypeLabel(type);}
function kcCollectionSummary(){const all=knowledgeCards().filter(r=>r.body.status!=='dismissed'),care=all.filter(r=>kcCare(r,knowledgeCardMeta(r)).length).length,report=all.filter(kcInReport).length;return `<div class="kc-collection-summary" role="status"><span><strong>${all.length}</strong> ${all.length===1?'block':'blocks'}</span><span><strong>${report}</strong> in report</span>${care?`<span class="kc-care-text"><strong>${care}</strong> to look after</span>`:'<span>All in good shape</span>'}</div>`;}

// Dossier (card back).
function kcDossierTab(){const v=knowledgeCardView();return v.dossierTab||'profile';}
function kcDossier(row){
 const p=row.body.payload,m=knowledgeCardMeta(row),type=m.type,lv=kcLevel(row,m),care=kcCare(row,m),report=kcInReport(row),tab=kcDossierTab();
 const tabs=[['profile','Profile'],['sources','Sources',(p.evidence||[]).length],['connections','Links',kcConnections(m)],['history','History'],['care','Care',care.length]];
 const stat=(k,v,sub='')=>`<div><dt>${esc(k)}</dt><dd>${v}${sub?`<span class="caption">${esc(sub)}</span>`:''}</dd></div>`;
 return `<div class="knowledge-card-detail kc-dossier kc-fam-${kcFamily(type)}">
 <div class="kc-dossier-nav"><a href="#main" class="item-title-link" data-action="kc-back">← Collection</a><button type="button" class="small" data-action="kc-edit" data-id="${esc(row.ref.id)}">Edit block</button></div>
 <article class="kc-hero">
  <header class="kc-band">${kcIcon(type,20)}<span>${esc(kcTypeLabel(type))}</span><span class="kc-hero-ver">v${row.ref.revision}</span></header>
  <div class="kc-hero-body"><h3>${esc(p.title)}</h3><p class="kc-hero-statement">${esc(p.statement)}</p></div>
  <footer class="kc-hero-foot"><span class="kc-level">${kcPips(lv.level)}<span>Completeness ${lv.level}/5</span></span><span class="kc-condition ${care.length?'is-care':'is-good'}">${care.length?care.length+' to look after':'In good shape'}</span></footer>
 </article>
 <dl class="kc-stats">${stat('Sources',`${(p.evidence||[]).length}<small>/4</small>`)}${stat('Links',String(kcConnections(m)))}${stat('Versions',String(row.ref.revision))}${stat('Report',report?'Used':'No')}</dl>
 <div class="kc-tabs" role="tablist" aria-label="Block dossier">${tabs.map(([k,t,n])=>`<button type="button" role="tab" aria-selected="${tab===k}" data-action="kc-dossier-tab" data-id="${k}">${t}${n?` <span class="kc-tab-count">${n}</span>`:''}</button>`).join('')}</div>
 <section class="kc-tab-panel" role="tabpanel">${({profile:kcProfile,sources:kcSources,connections:kcLinks,history:kcHistory,care:kcCarePanel})[tab](row,m,lv,care)}</section>
 <div class="kc-dossier-actions"><button type="button" class="compact-text-action" data-action="kc-select" data-id="${esc(row.ref.id)}">${report?label(report)===label(row.ref)?'Remove from Outcomes report':'Use latest version in report':'Use in Outcomes report'}</button><button type="button" class="compact-text-action" data-action="kc-assess" data-id="${esc(row.ref.id)}">Assess with AI partner</button><button type="button" class="compact-text-action" data-action="kc-archive" data-id="${esc(row.ref.id)}">${row.body.status==='dismissed'?'Restore block':'Archive block'}</button></div>
 
</div>`;
}
function kcProfile(row){const p=row.body.payload,type=kcMetaType(row),labels=knowledgeCardInfo().types[type]?.fields||{},fields=kcFields(row);
 return `${p.rationale?.trim()?`<h4>Why it matters and what remains uncertain</h4><p class="pre">${esc(p.rationale)}</p>`:''}${fields.length?`<dl class="kc-fields">${fields.map(([k,v])=>`<div><dt>${esc(labels[k]||k)}</dt><dd class="pre">${esc(v)}</dd></div>`).join('')}</dl>`:''}${!p.rationale?.trim()&&!fields.length?`<p class="caption">Only the main statement is filled in. ${kcFix(row,'context','Add details')}</p>`:''}`;}
function kcSourceTitle(raw){const ref=typeof knowledgeParseRef==='function'?knowledgeParseRef(raw):null,t=ref?(knowledgeCardInfo().targets||[]).find(x=>x.ref.id===ref.id):null;return t?.title||raw;}
function kcSources(row){const ev=row.body.payload.evidence||[];return ev.length?`<ul class="kc-source-list">${ev.map(e=>`<li><strong>${esc(kcSourceTitle(e.source))}</strong>${e.page?`<span class="caption">Page ${esc(e.page)}</span>`:''}${e.quote?`<blockquote>${esc(e.quote)}</blockquote>`:''}</li>`).join('')}</ul>${ev.length<4?`<p class="caption">${kcFix(row,'evidence','Add another passage')}</p>`:''}`:`<p class="caption">No source passages yet. Saved wording is not evidence until it points to an exact source. ${kcFix(row,'evidence','Add a source passage')}</p>`;}
function kcLinks(row,m){const rel=knowledgeCardInfo().relations||{};return `${m.relations.length?`<ul class="kc-link-list">${m.relations.map(l=>`<li><span class="kc-rel">${esc(rel[l.relation]||l.relation)}</span><a href="#main" class="item-title-link" data-action="kc-related" data-id="${esc(label(l.ref))}">${esc(l.title)}</a>${l.changed?'<span class="kc-badge kc-badge-changed">Newer version</span>':''}${l.rationale?`<span class="caption">${esc(l.rationale)}</span>`:''}</li>`).join('')}</ul>`:''}${m.backlinks.length?`<h4>Linked from</h4><ul class="kc-link-list">${m.backlinks.map(l=>`<li><span class="kc-rel">${esc(rel[l.relation]||l.relation)}</span><a href="#main" class="item-title-link" data-action="kc-open" data-id="${esc(l.ref.id)}">${esc(l.title)}</a></li>`).join('')}</ul>`:''}${kcConnections(m)?'':`<p class="caption">Not connected yet. Link what this supports, depends on or changes. ${kcFix(row,'links','Add a connection')}</p>`}`;}
function kcHistory(row,m){const b=row.body;return `<dl class="kc-fields"><div><dt>Origin</dt><dd>${esc(kcOrigin(row))}</dd></div><div><dt>Created</dt><dd>${esc(kcWhen(b.created_at))}</dd></div><div><dt>Last saved</dt><dd>${esc(kcWhen(b.at))} · version ${row.ref.revision}</dd></div>${(b.captures||[]).length?`<div><dt>Passages added</dt><dd>${b.captures.length}</dd></div>`:''}</dl>${b.origin_selection?`<blockquote>${esc(b.origin_selection.text)}</blockquote>`:''}<p><button type="button" class="compact-text-action" data-action="kc-history" data-id="${esc(row.ref.id)}">View saved versions</button>${m.shared?`<button type="button" class="compact-text-action" data-action="kc-shared" data-id="${esc(label(m.shared))}">View shared copy · v${m.shared.revision}</button>`:''}</p>`;}
function kcCarePanel(row,m,lv,care){return `${care.length?`<ul class="kc-care-list">${care.map(t=>`<li><span>${esc(t.text)}</span><button type="button" class="compact-text-action" data-action="${esc(t.action)}" data-id="${esc(t.id)}">${esc(t.label)}</button></li>`).join('')}</ul>`:'<p class="caption">Nothing needs attention.</p>'}<h4>Completeness</h4><ol class="kc-steps">${lv.steps.map(([k,t,done,section])=>`<li class="${done?'is-done':''}"><span>${esc(t)}</span>${!done&&section?kcFix(row,section,'Add'):''}</li>`).join('')}</ol><p class="caption">Counts what is filled in, not whether it is right.</p>`;}
function kcFix(row,section,text){return `<button type="button" class="compact-text-action" data-action="kc-edit-section" data-id="${esc(row.ref.id+'|'+section)}">${esc(text)}</button>`;}
function kcDossierActive(row){const v=knowledgeCardView();if(!row||row.ref.id==='NEW-CARD'||v.dossier!==row.ref.id)return false;if(typeof knowledgeCarryState==='function'&&knowledgeCarryState())return false;const d=typeof knowledgeCardEdits!=='undefined'?knowledgeCardEdits.get(knowledgeCardEditKey(row.ref.id)):null;return !d?.dirty;}

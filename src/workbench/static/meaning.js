// D009 step 2: meaning proposals between teams. Mappings and shares are proposed here and decided
// explicitly by each team lead they touch. Presentation and commands only; rules live in meaning.py.
function meaningInfo(){return state.meaning||{items:[],relations:{},types:{},can_propose:false,waiting_on_me:0};}
function meaningTeam(key){return (domainKnowledgeInfo().domains||[]).find(d=>d.key===key)?.label||key;}
function meaningPerson(id){return state.actors?.[id]?.name||id;}
function meaningStatusChip(i){const s={proposed:['ac-state-suggested',i.waiting?.length?'Proposed · waiting on '+i.waiting.map(meaningTeam).join(', '):'Proposed'],approved:['ac-state-validated','Approved'],declined:['ac-state-edited','Declined'],withdrawn:['','Withdrawn'],retired:['','Retired']}[i.status]||['',i.status];return `<span class="ac-state ${s[0]}">${esc(s[1])}</span>`;}
function meaningSentence(i){const a=i.concepts[0],b=i.concepts[1];return i.type==='mapping'?`${a.concept.title} (${meaningTeam(a.domain)}) ${meaningInfo().relations[i.relation]||i.relation} ${b.concept.title} (${meaningTeam(b.domain)})`:`Share ${a.concept.title} (${meaningTeam(a.domain)}) with ${meaningTeam(i.grantee)}`;}
function meaningActions(i){const id=esc(i.ref.id);return `${i.mine?.length?`<button type="button" class="primary small" data-action="meaning-decide" data-id="${id}">Decide</button>`:''}${i.can_withdraw?`<button type="button" class="quiet small" data-action="meaning-close" data-id="${id}">Withdraw</button>`:''}${i.can_retire?`<button type="button" class="quiet small" data-action="meaning-close" data-id="${id}">Retire</button>`:''}`;}
function meaningRow(i){return `<li class="meaning-row${i.mine?.length?' is-mine':''}"><span class="meaning-row-text"><span class="meaning-row-title">${esc(meaningSentence(i))}</span><span class="meaning-row-meta">${esc(meaningPerson(i.proposed_by))} · ${esc(typeof projectHomeDate==='function'?projectHomeDate(i.at):'')} · ${esc(i.reason)}${i.changed?.length?` · <strong>Changed since: ${esc(i.changed.join(', '))}</strong>`:''}</span></span>${meaningStatusChip(i)}<span class="meaning-row-actions">${meaningActions(i)}</span></li>`;}
// Panel above a team's knowledge: open proposals, and concepts other teams share with this team.
function meaningPanel(d){
 const info=meaningInfo(),open=info.items.filter(i=>i.status==='proposed'),shared=info.items.filter(i=>i.type==='share'&&i.status==='approved'&&i.grantee===d.key);
 if(!open.length&&!shared.length)return '';
 return `<section class="card meaning-panel" aria-labelledby="meaning-panel-title"><p class="case-label" id="meaning-panel-title"><span>Across teams${open.length?` · ${open.length} proposed`:''}</span>${info.waiting_on_me?`<span class="case-label-meta meaning-waiting">${info.waiting_on_me} waiting on you</span>`:''}</p>
 ${open.length?`<ul class="meaning-rows">${open.map(meaningRow).join('')}</ul>`:''}
 ${shared.length?`<p class="meaning-shared"><strong>Shared with ${esc(d.label)}:</strong> ${shared.map(i=>`${esc(i.concepts[0].concept.title)} <span class="caption">from ${esc(meaningTeam(i.concepts[0].domain))}</span>`).join(' · ')}</p>`:''}</section>`;
}
// In a concept's detail: its approved and proposed mappings and shares, and the ways to propose one.
function knowledgeAcrossTeams(d,e){
 if(!['term','category'].includes(e.kind)||e.status==='archived')return '';
 const info=meaningInfo(),mine=info.items.filter(i=>['proposed','approved'].includes(i.status)&&i.concepts.some(c=>c.domain===d.key&&c.concept.id===e.id));
 const others=(domainKnowledgeInfo().domains||[]).filter(x=>x.key!==d.key);
 const line=i=>{if(i.type==='share')return `<li><span class="meaning-rel">shared with</span><span class="meaning-other">${esc(meaningTeam(i.grantee))}</span>${meaningStatusChip(i)}<span class="meaning-row-actions">${meaningActions(i)}</span></li>`;
  const self=i.concepts.findIndex(c=>c.domain===d.key&&c.concept.id===e.id),other=i.concepts[1-self],rel=self===0?i.relation:({broader:'narrower',narrower:'broader'}[i.relation]||i.relation);
  return `<li><span class="meaning-rel">${esc(rel)}</span><span class="meaning-other">${esc(other.concept.title)} <span class="caption">${esc(meaningTeam(other.domain))}</span></span>${meaningStatusChip(i)}<span class="meaning-row-actions">${meaningActions(i)}</span></li>`;};
 return `<h3>Across teams</h3>${mine.length?`<ul class="meaning-links">${mine.map(line).join('')}</ul>`:'<p class="caption">No mappings or shares yet.</p>'}
 ${info.can_propose&&others.length?`<div class="evidence-actions">${button('Propose a mapping','meaning-map',d.key+'|'+e.id,'quiet')}${button('Propose sharing','meaning-share',d.key+'|'+e.id,'quiet')}</div><p class="caption">Each team lead it touches decides. Nothing is inferred.</p>`:''}`;
}
function meaningConceptRead(side){const c=side.concept,row=(t,v)=>String(v||'').trim()?`<p class="meaning-bound"><strong>${t}</strong> ${esc(v)}</p>`:'';return `<div class="meaning-side"><p class="case-label"><span>${esc(meaningTeam(side.domain))}</span></p><h3>${esc(c.title)}</h3><p>${esc(c.definition)}</p>${row('Includes',c.includes)}${row('Excludes',c.excludes)}${row('Not to be confused with',c.not_confused_with)}</div>`;}
function meaningProposeMapping(key,id){
 const d=domainKnowledgeProfile(key),e=d.entries.find(x=>x.id===id),info=meaningInfo();
 const options=(domainKnowledgeInfo().domains||[]).filter(x=>x.key!==key).map(x=>{const cs=x.entries.filter(c=>['term','category'].includes(c.kind)&&c.status!=='archived');return cs.length?`<optgroup label="${esc(x.label)}">${cs.map(c=>`<option value="${esc(x.key+'|'+c.id)}">${esc(c.title)}</option>`).join('')}</optgroup>`:'';}).join('');
 if(!options){toast('No other team has a term or category to map to yet.');return;}
 modal('Propose a mapping',`<p class="caption">${esc(e.title)} · ${esc(d.label)}</p>${settingSelector('meaning-relation',esc(e.title)+'…',Object.entries(info.relations).map(([k,t])=>`<option value="${k}" ${k==='distinct-from'?'selected':''}>${esc(t)}</option>`).join(''),'relation')}${settingSelector('meaning-target','Concept in another team',options,'target')}${domainText('reason','Why',"",true,'What the two teams need to agree, and what goes wrong without it.')}<p class="caption">Both team leads decide. Nothing changes until both approve.</p>`,'Propose',async fd=>{const [td,ti]=String(fd.get('target')).split('|');return command('meaning-propose',{type:'mapping',relation:fd.get('relation'),reason:fd.get('reason'),from:{domain:key,id},to:{domain:td,id:ti}});},{className:'settings-dialog'});
}
function meaningProposeShare(key,id){
 const d=domainKnowledgeProfile(key),e=d.entries.find(x=>x.id===id),others=(domainKnowledgeInfo().domains||[]).filter(x=>x.key!==key);
 modal('Propose sharing',`<p class="caption">${esc(e.title)} · ${esc(d.label)}</p>${settingSelector('meaning-grantee','Share with',others.map(x=>`<option value="${esc(x.key)}">${esc(x.label)}</option>`).join(''),'grantee')}${domainText('reason','Why',"",true,'How the other team will use this concept.')}<p class="caption">${esc(d.label)}'s lead decides. The other team may then use the concept as ${esc(d.label)} defines it.</p>`,'Propose',async fd=>command('meaning-propose',{type:'share',grantee:fd.get('grantee'),reason:fd.get('reason'),from:{domain:key,id}}),{className:'settings-dialog'});
}
function meaningDecide(id){
 const i=meaningInfo().items.find(x=>x.ref.id===id);if(!i)return;const stale=i.changed?.length;
 modal('Decide this proposal',`<p class="meaning-decide-title">${esc(meaningSentence(i))}</p><p class="caption">Proposed by ${esc(meaningPerson(i.proposed_by))}: ${esc(i.reason)}</p><div class="meaning-sides">${i.concepts.map(meaningConceptRead).join('')}</div>
 ${stale?`<p class="meaning-stale"><strong>${esc(i.changed.join(', '))} changed since this was proposed.</strong> It can be declined, then proposed again on the current wording.</p>`:''}
 <fieldset class="case-outcomes"><legend>Your decision for ${esc(i.mine.map(meaningTeam).join(', '))}</legend>${stale?'':'<label><input type="radio" name="outcome" value="approve" required><span>Approve</span></label>'}<label><input type="radio" name="outcome" value="decline" required ${stale?'checked':''}><span>Decline</span></label></fieldset>
 ${domainText('reason','Why',"",true,'Kept with the decision.')}<label class="checkbox"><input type="checkbox" name="confirm" required>I am deciding this as team lead.</label>`,'Record decision',async fd=>command('meaning-decide',{proposal:i.ref,outcome:fd.get('outcome'),reason:fd.get('reason'),confirm:fd.get('confirm')==='on'}),{className:'settings-dialog'});
}
function meaningClose(id){
 const i=meaningInfo().items.find(x=>x.ref.id===id);if(!i)return;const retire=i.status==='approved';
 modal(retire?'Retire this':'Withdraw this proposal',`<p class="meaning-decide-title">${esc(meaningSentence(i))}</p>${domainText('reason','Why',"",true,retire?'It stops being in effect. The record is kept.':'The record is kept.')}`,retire?'Retire':'Withdraw',async fd=>command('meaning-close',{proposal:i.ref,reason:fd.get('reason')}),{className:'settings-dialog'});
}
async function meaningAction(action,id){
 if(action==='meaning-map'){const [k,e]=id.split('|');meaningProposeMapping(k,e);return true;}
 if(action==='meaning-share'){const [k,e]=id.split('|');meaningProposeShare(k,e);return true;}
 if(action==='meaning-decide'){meaningDecide(id);return true;}
 if(action==='meaning-close'){meaningClose(id);return true;}
 return false;
}

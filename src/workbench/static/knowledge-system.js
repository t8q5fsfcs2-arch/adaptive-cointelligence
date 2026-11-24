// D014 revision 2: how a block counts, and what the system checks. Read-only views over
// server projections. Services detect; reviewers judge; decision owners settle consequences.
function knowledgeSystemConfig(){return state.knowledge_system?.config||(typeof knowledgeCardInfo==='function'?knowledgeCardInfo().system:null)||{components:{},categories:{}};}
function knowledgeComponentNames(keys){const c=knowledgeSystemConfig().components||{};return (keys||[]).map(k=>c[k]?.label||k).join(', ');}
function knowledgeComponentHolds(keys){const c=knowledgeSystemConfig().components||{};return (keys||[]).map(k=>(c[k]?.holds||k).toLowerCase()).join(', ');}
function knowledgeBlockSystem(row,m){
 const s=m?.system;if(!s||row.ref.id==='NEW-CARD')return '';
 const type=(typeof knowledgeCardInfo==='function'?knowledgeCardInfo().types[s.type]?.label:'')||'block';
 const links=(s.links||[]).filter(l=>l.eligibility);
 return `<details class="knowledge-card-section knowledge-block-system" data-knowledge-disclosure="system" ${typeof knowledgeCardDisclosure==='function'?knowledgeCardDisclosure('system'):''}><summary>How this block counts</summary>
 <p class="caption">Carries: ${esc(knowledgeComponentNames(s.components))||'nothing yet'}.</p>
 ${s.missing?.length?`<p class="caption">A complete ${esc(type.toLowerCase())} also needs ${esc(knowledgeComponentHolds(s.missing))}.</p>`:`<p class="caption">Complete for a ${esc(type.toLowerCase())}.</p>`}
 ${links.length?`<ul class="knowledge-block-eligibility">${links.map(l=>`<li><span class="ac-state ${l.eligibility.eligible?'ac-state-validated':'ac-state-suggested'}">${l.eligibility.eligible?(l.eligibility.counts?'Counts':'Eligible'):'Not yet'}</span> ${esc(l.eligibility.coaching)}</li>`).join('')}</ul>`:'<p class="caption">Link this block to a requirement to see whether it can count toward it.</p>'}
 <p class="caption">Eligible is not counted: a block counts once you save or share it.</p></details>`;
}
function knowledgeSystemChecks(){
 const s=state.knowledge_system?.structure;if(!s)return '';
 const diffs=s.differences||[],reach=s.challenge_reach||[],stale=s.stale_pins||[],gaps=s.category_gaps||[];
 const total=diffs.length+reach.length+gaps.length; // older pins are expected history, kept folded
 // A private block and its shared copy carry the same title: name each piece of work once.
 const names=list=>[...new Set(list.map(d=>d.title))];
 const relation=r=>String(r||'').replaceAll('-',' ');
 const groupLine=g=>`${esc(g.group)}: ${g.links.map(l=>`${esc(relation(l.relation))}${l.conditions?' · '+esc(l.conditions):' · no scope stated'} · v${esc(l.revision??'?')}`).join('; ')}`;
 // Lead with what matters most: scope, then versions. Relation and use differences are usually expected.
 const lead=['scope-differs','scope-stated-by-one-group','revision-skew'];
 const split=d=>{const pairs=d.kinds.map((k,i)=>[k,d.messages[i]]),first=pairs.filter(([k])=>lead.includes(k)),main=first.length?first:pairs.slice(0,1);return {main:main.map(([,m])=>m),rest:pairs.filter(x=>!main.includes(x)).map(([,m])=>m)};};
 return `<section class="section card knowledge-system-checks" aria-labelledby="knowledge-system-checks-title"><h2 id="knowledge-system-checks-title">System checks <span class="caption">${total}</span></h2>
 <p class="caption">Computed from recorded links and versions. These report what to look at; a reviewer judges meaning and the decision owner settles consequences.</p>
 ${total?'':'<p class="caption">Nothing needs a look right now.</p>'}
 ${diffs.length?`<h3>Differences between groups</h3><ul class="list">${diffs.map(d=>`<li class="rule"><strong>${esc(d.title)}</strong><p>${split(d).main.map(esc).join(' ')}</p><p class="caption">${d.groups.map(groupLine).join('<br>')}</p>${split(d).rest.length?`<details class="page-about"><summary>Also differs</summary><p class="caption">${split(d).rest.map(esc).join(' ')}</p></details>`:''}<p class="caption">${esc(d.next)}</p></li>`).join('')}</ul>`:''}
 ${reach.length?`<h3>What open challenges reach</h3><ul class="list">${reach.map(r=>`<li class="rule"><strong>${esc(r.title||r.issue.id)}</strong><p class="caption">${names(r.dependents).length?'Depends on it: '+names(r.dependents).slice(0,5).map(esc).join(', ')+(names(r.dependents).length>5?` and ${names(r.dependents).length-5} more`:''):''}${r.packets.length?(r.dependents.length?'<br>':'')+`Held in ${r.packets.length} packet${r.packets.length===1?'':'s'}`:''}</p></li>`).join('')}</ul>`:''}
 ${stale.length?`<details class="page-about"><summary>Packets pinned to older versions (${stale.length})</summary><p class="caption">Expected as work moves on. Worth a look only for a packet someone is still working from.</p><ul class="list">${stale.map(p=>`<li class="rule"><strong>${esc(p.purpose)}</strong><p class="caption">${p.changed.length} item${p.changed.length===1?' has':'s have'} a newer version. The packet keeps what was issued.</p></li>`).join('')}</ul></details>`:''}
 ${gaps.length?`<h3>Requirements whose linked blocks cannot count yet</h3><ul class="list">${gaps.map(g=>`<li class="rule"><strong>${esc(g.title)}</strong><p class="caption">${esc(g.note)}</p></li>`).join('')}</ul>`:''}
 </section>`;
}

'use strict';
// Ephemeral question drafts, isolated by account, role, project and surface.
// Draft persistence never publishes project content or requests a model.
const reviewerDrafts=new Map();
function reviewerDraftKey(surface,scope=''){
 return JSON.stringify(['reviewer-question-v1',state?.auth?.account?.id||'local',state?.actor||'local',state?.project?.id||'general',surface,scope]);
}
function clearReviewerDrafts(){
 reviewerDrafts.clear();
 try{for(let i=sessionStorage.length-1;i>=0;i--){const key=sessionStorage.key(i);if(key?.startsWith('["reviewer-question-v1",'))sessionStorage.removeItem(key);}}catch{}
 for(const el of document.querySelectorAll?.('[data-reviewer-draft]')||[]){el.value='';el.dataset.reviewerLastValue='';}
 if(typeof fieldCoachSessions!=='undefined')fieldCoachSessions.clear();
 if(typeof fieldCoachAdvice!=='undefined')fieldCoachAdvice=null;
}
function reviewerDraftRead(surface,scope=''){
 const key=reviewerDraftKey(surface,scope);if(reviewerDrafts.has(key))return reviewerDrafts.get(key);
 try{const value=sessionStorage.getItem(key);if(value!==null){reviewerDrafts.set(key,value);return value;}}catch{}
 return '';
}
function reviewerDraftWriteKey(key,text){
 const value=String(text??'');reviewerDrafts.set(key,value);try{sessionStorage.setItem(key,value);}catch{}
 for(const el of document.querySelectorAll?.('[data-reviewer-draft]')||[])if(el.dataset.reviewerDraftKey===key){el.value=value;el.dataset.reviewerLastValue=value;}
}
function reviewerDraftWrite(surface,text,scope=''){reviewerDraftWriteKey(reviewerDraftKey(surface,scope),text);}
function reviewerDraftCapture(root=document){
 for(const el of root.querySelectorAll?.('[data-reviewer-draft]')||[]){
  // A previously mounted key remains bound to its original account/project.
  const key=el.dataset.reviewerDraftKey||reviewerDraftKey(el.dataset.reviewerDraft,el.dataset.reviewerScope||'');
  el.dataset.reviewerDraftKey=key;
  if(el.dataset.reviewerLastValue===undefined||el.value!==el.dataset.reviewerLastValue)reviewerDraftWriteKey(key,el.value);
  el.dataset.reviewerLastValue=el.value;
 }
}
function mountReviewerUI(root=document){
 for(const el of root.querySelectorAll?.('[data-reviewer-draft]')||[]){
  const current=reviewerDraftKey(el.dataset.reviewerDraft,el.dataset.reviewerScope||''),bound=el.dataset.reviewerDraftKey;
  if(bound&&bound!==current)continue;
  const key=bound||current;el.dataset.reviewerDraftKey=key;
  const saved=reviewerDraftRead(el.dataset.reviewerDraft,el.dataset.reviewerScope||'');
  if(el.dataset.reviewerLastValue!==undefined&&el.value===el.dataset.reviewerLastValue){el.value=saved;}
  else if(saved&&!el.value)el.value=saved;
  else if(el.value)reviewerDraftWriteKey(key,el.value);
  el.dataset.reviewerLastValue=el.value;
 }
}
document.addEventListener('input',event=>{
 const el=event.target;if(!el.matches?.('[data-reviewer-draft]'))return;
 const key=el.dataset.reviewerDraftKey||reviewerDraftKey(el.dataset.reviewerDraft,el.dataset.reviewerScope||'');
 el.dataset.reviewerDraftKey=key;reviewerDraftWriteKey(key,el.value);
});
window.addEventListener('pagehide',()=>reviewerDraftCapture());

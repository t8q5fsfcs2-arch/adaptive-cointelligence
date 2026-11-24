'use strict';

// These are presentation meanings, not workflow permissions or evidence grades.
// An unfamiliar status stays quiet until its meaning has been explicitly mapped.
function signalStatusKind(status,{recordedAction=false}={}){
 const advisory=new Set(['basis-changed','source-changed','context-changed','stale','review-needed','policy-changed','decision-rights-changed']);
 const critical=new Set(['error','failed','save-failed','request-failed','permission-denied','action-blocked']);
 const completedAction=new Set(['approved','saved','succeeded','sent','published']);
 if(critical.has(status))return 'critical';
 if(advisory.has(status))return 'advisory';
 if(recordedAction&&completedAction.has(status))return 'success';
 return 'reference';
}

// Compatibility with the established tag palette. The visible status wording
// remains the source of meaning; a colored tag must never stand in for it.
function signalStatusTone(status,options){
 return {reference:'',advisory:'amber',critical:'red',success:'green'}[signalStatusKind(status,options)];
}

function signalNoticeClass(kind='reference'){
 const allowed=new Set(['reference','advisory','critical','success']);
 return 'signal-notice signal-'+(allowed.has(kind)?kind:'reference');
}

// Chips describe changing conditions. Titles and source identity remain separate.
function signalConditionChip(text,kind='reference',extraClass=''){
 const tone=['reference','attention','advisory','critical','success'].includes(kind)?kind:'reference';
 return `<span class="condition-chip condition-chip-${tone}${extraClass?' '+esc(extraClass):''}">${tone==='advisory'||tone==='critical'?'<span aria-hidden="true">⚠</span> ':''}${esc(text)}</span>`;
}
function signalItemTitle(text){return String(text||'').replace(/^SIMULATION\s*[—–:-]\s*/i,'');}

// Shared vocabulary; evidence thresholds are fixed in requirement_evidence.py.
// These levels are never calculated from filled fields, report counts or approval.
const confidenceLevels=Object.freeze({
 'not-rated':Object.freeze({label:'Not rated',meaning:'No shared evidence assessment is recorded.'}),
 low:Object.freeze({label:'Low',meaning:'Limited support or material gaps remain.'}),
 moderate:Object.freeze({label:'Moderate',meaning:'Relevant evidence supports the key claims within stated limits.'}),
 high:Object.freeze({label:'High',meaning:'Material claims have strong, applicable evidence and no unresolved material contradiction.'})
});
function confidenceLabel(level='not-rated'){return confidenceLevels[level]?.label||confidenceLevels['not-rated'].label;}
// Requirement-level shared confidence has no native assessment transition yet.
function requirementConfidenceLabel(){return 'Confidence: '+confidenceLabel('not-rated');}

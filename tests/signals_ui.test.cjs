const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const context={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;')};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/signals.js'),'utf8'),context);
const kind=(status,options)=>context.signalStatusKind(status,options);

test('ordinary work, proposals and uncertainty do not manufacture warnings or authority',()=>{
 for(const status of ['proposed','pending-review','working','draft','published','deferred','rejected','uncertain','absent','low-confidence','not-assessed','not-authorized','configured']){
  assert.equal(kind(status),'reference',status);
  assert.equal(context.signalStatusTone(status),'',status);
 }
});

test('unfamiliar or caution-like wording stays neutral instead of being classified by its text',()=>{
 for(const status of ['new-status','urgent review warning','looks-approved','blocked','validated','high-confidence',null,undefined,'']){
  assert.equal(kind(status),'reference');
 }
});

test('recorded changes ask for attention without implying a hard stop',()=>{
 for(const status of ['basis-changed','source-changed','context-changed','stale','review-needed','policy-changed','decision-rights-changed']){
  assert.equal(kind(status),'advisory');
  assert.equal(context.signalStatusTone(status),'amber');
 }
});

test('explicit failed actions and authorization failures retain the critical signal',()=>{
 for(const status of ['error','failed','save-failed','request-failed','permission-denied','action-blocked']){
  assert.equal(kind(status),'critical');
  assert.equal(context.signalStatusTone(status),'red');
 }
});

test('green needs an explicit saved action context and never validates an evidence grade',()=>{
 for(const status of ['approved','saved','succeeded','sent','published']){
  assert.equal(kind(status),'reference');
  assert.equal(kind(status,{recordedAction:true}),'success');
  assert.equal(context.signalStatusTone(status,{recordedAction:true}),'green');
 }
 for(const status of ['supported','validated','high-confidence','uncertain','fulfilled']){
  assert.equal(kind(status,{recordedAction:true}),'reference');
 }
});

test('notice classes accept only explicit meanings and introduce no live announcement or content',()=>{
 assert.equal(context.signalNoticeClass('advisory'),'signal-notice signal-advisory');
 assert.equal(context.signalNoticeClass('critical'),'signal-notice signal-critical');
 assert.equal(context.signalNoticeClass('warning'),'signal-notice signal-reference');
 assert.equal(context.signalNoticeClass('critical" role="alert'),'signal-notice signal-reference');
 assert.doesNotMatch(context.signalNoticeClass('success'),/role|aria|alert/);
});

test('condition chips share explicit meanings without grading content or rewriting the source title',()=>{
 const source='SIMULATION — Check the <scope>';
 assert.equal(context.signalItemTitle(source),'Check the <scope>');assert.equal(source,'SIMULATION — Check the <scope>');
 assert.match(context.signalConditionChip('Open'),/condition-chip-reference/);
 assert.match(context.signalConditionChip('For you','attention'),/condition-chip-attention/);
 assert.match(context.signalConditionChip('<Changed>','advisory'),/aria-hidden="true">⚠[\s\S]+&lt;Changed>/);
 assert.match(context.signalConditionChip('Urgent wording','invented'),/condition-chip-reference/);
 assert.doesNotMatch(context.signalConditionChip('High confidence'),/advisory|critical|success/);
 for(const [level,label] of [['not-rated','Not rated'],['low','Low'],['moderate','Moderate'],['high','High']])assert.equal(context.confidenceLabel(level),label);
 for(const value of [undefined,'approved','validated',95,'unknown'])assert.equal(context.confidenceLabel(value),'Not rated');
 assert.equal(context.requirementConfidenceLabel(),'Confidence: Not rated');
});

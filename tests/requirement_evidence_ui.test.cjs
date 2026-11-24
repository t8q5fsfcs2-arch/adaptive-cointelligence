const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
function ctx(evidence){const c={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),state:{requirement_evidence:evidence}};vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/requirement-evidence.js'),'utf8'),c);return c;}
const high={level:'high',reasons:['High: 2 contributions from 2 teams on the current version.'],contributions:4,on_current:2,teams:['Design','Research'],current_teams:['Design','Research'],age_days:0,open_contradictions:0,open_gaps:0,open_dependencies:0,resolved_issues:1};
test('evidence chip shows a filled tank and its level',()=>{
 const c=ctx({'REQ-1':high});const html=vm.runInContext("requirementEvidenceChip('REQ-1')",c);
 assert.match(html,/ac-tank ac-tank-high/);assert.equal((html.match(/is-filled/g)||[]).length,3);assert.match(html,/Evidence: High/);
});
test('evidence section explains its factors, invites teams and stays read-only',()=>{
 const c=ctx({'REQ-1':high});const html=vm.runInContext("requirementEvidenceSection('REQ-1')",c);
 assert.match(html,/4 contributions · Design, Research/);assert.match(html,/Open contradictions<\/dt><dd>0/);assert.match(html,/Issues worked through<\/dt><dd>1/);
 assert.match(html,/data-nav="review">Decisions &amp; Issues/);assert.match(html,/not the recorded confidence and approves nothing/);
 assert.doesNotMatch(html,/<textarea|<input|<select|data-action=/);
});
test('a requirement nobody has referenced shows an empty tank',()=>{
 const c=ctx({});const html=vm.runInContext("requirementEvidenceSection('REQ-2')",c);
 assert.match(html,/Evidence: Empty/);assert.equal((html.match(/is-filled/g)||[]).length,0);assert.match(html,/No shared work references this requirement yet/);
});
test('D012: confidence rating, evidence level and validated-by appear together and stay separate',()=>{
 const c=ctx({'REQ-1':{...high,level:'moderate',current_teams:['Research'],raise_to:{to:'high',needs:['work from 2 teams on the current version']}}});
 c.state.domains={profiles:[{key:'research',config:{label:'Research'}},{key:'design',config:{label:'Design'}}]};c.get=id=>({ref:{id,revision:2},body:{}});
 c.requirementAssessmentCurrent=()=>({status:'suitable',current:{body:{}},confidence:{level:'moderate'},reassess:[{reason:'New shared evidence since this rating'}]});
 const html=vm.runInContext("requirementEvidenceSection('REQ-1')",c);
 assert.match(html,/How sure are we/);assert.match(html,/Confidence rating<\/dt><dd><span class="signal-value lv-moderate">Moderate/);assert.match(html,/Needs reassessment: new shared evidence since this rating/);
 assert.match(html,/Evidence level<\/dt><dd><span class="ac-evidence-chip"/);
 assert.match(html,/signal-team is-done"><span aria-hidden="true">✓<\/span> Research/);assert.match(html,/signal-team "><span aria-hidden="true">○<\/span> Design/);
 assert.match(html,/To raise evidence to High:<\/strong> work from 2 teams on the current version\./);assert.match(html,/None of them approves or blocks anything/);
 assert.doesNotMatch(html,/<textarea|<input|<select|data-action=|\d+%/);
});
test('D012: an unrated requirement says Not rated, never Low, and a changed basis asks for reassessment',()=>{
 const c=ctx({});c.get=id=>({ref:{id,revision:1},body:{}});c.requirementAssessmentCurrent=()=>({status:'not-assessed',current:null,confidence:{level:'not-rated'}});
 let html=vm.runInContext("requirementSignals('REQ-9')",c);assert.match(html,/lv-not-rated">Not rated/);assert.doesNotMatch(html,/Needs reassessment|To raise/);assert.match(html,/No teams yet/);
 c.requirementAssessmentCurrent=()=>({status:'needs-reassessment',current:{body:{}},confidence:{level:'not-rated'}});
 assert.match(vm.runInContext("requirementSignals('REQ-9')",c),/Needs reassessment: its basis changed/);
});

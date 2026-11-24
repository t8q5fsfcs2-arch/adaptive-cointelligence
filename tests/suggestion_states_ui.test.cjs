const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const read=f=>fs.readFileSync(path.join(__dirname,'../src/workbench/static',f),'utf8');
function ctx(){const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');const c={esc,para:s=>`<p>${esc(s)}</p>`,tag:t=>`<span class="tag">${esc(t)}</span>`,button:(t,a,id)=>`<button data-action="${esc(a)}" data-id="${esc(id)}">${esc(t)}</button>`,citationsHtml:()=>'' ,intakeNames:{why_now:'What makes this a priority now?'}};vm.createContext(c);const app=read('app.js');vm.runInContext(app.slice(app.indexOf('// D003 shared suggestion states')),c);return c;}
test('one helper names the Suggested, Used and Validated states with their origin, escaped',()=>{
 const c=ctx();
 assert.match(vm.runInContext("acSuggestionHead('From <your> AI partner')",c),/<span class="ac-state ac-state-suggested">Suggested<\/span><span class="ac-origin">From &lt;your> AI partner<\/span>/);
 assert.match(vm.runInContext("acSuggestionHead('',  'used')",c),/ac-state-edited">Used in your draft · save to keep</);
 assert.match(vm.runInContext("acSuggestionHead('x','validated')",c),/ac-state-validated">Validated</);
});
test('AI-filled intake answers arrive as suggestions with their basis, and show when used but not yet saved',()=>{
 const c=ctx();const src=read('coaching.js');vm.runInContext(src.slice(src.indexOf('function coachSuggestion('),src.indexOf('\n',src.indexOf('function coachSuggestion('))),c);c.validRun=()=>true;
 const fresh=vm.runInContext("coachSuggestion({ref:{id:'R',revision:1},body:{applied:{}}},{field:'why_now',basis:'hypothesis',text:'End of life',rationale:'Memo',citations:[]})",c);
 assert.match(fresh,/class="coach-suggestion ac-suggestion"/);assert.match(fresh,/Suggested<\/span><span class="ac-origin">From your AI partner · a hypothesis to test/);assert.match(fresh,/data-action="coach-apply" data-id="R\|why_now">Use this wording/);
 const used=vm.runInContext("coachSuggestion({ref:{id:'R',revision:1},body:{applied:{why_now:'x'}}},{field:'why_now',basis:'source-supported',text:'End of life',rationale:'Memo',citations:[]})",c);
 assert.match(used,/ac-suggestion is-edited/);assert.match(used,/Used in your draft · save to keep/);assert.match(used,/informed by your sources/);assert.doesNotMatch(used,/coach-apply/);
});
test('a sponsor answer filled for the person is marked Suggested with its origin until they edit or save it',()=>{
 const c=ctx();const src=read('sponsor.js');for(const n of ['function sponsorAnswerHas','function sponsorAnswerState','function sponsorAnswerStatus']){const i=src.indexOf(n);vm.runInContext(src.slice(i,src.indexOf('\nfunction',i+5)),c);}
 assert.match(vm.runInContext("sponsorAnswerStatus({items:['Text'],roles:[],ai:true,origin:'Reviewed source suggestion'})",c),/Suggested · Reviewed source suggestion/);
 assert.doesNotMatch(vm.runInContext("sponsorAnswerStatus({items:['Text'],roles:[],ai:false,edited:true})",c),/Suggested/);
 assert.doesNotMatch(vm.runInContext("sponsorAnswerStatus({items:[],roles:[],ai:true})",c),/Suggested/);
});
test('AI-proposed plan sections are marked Suggested until the author decides; author sections are not',()=>{
 const c=ctx();const src=read('project-flow.js');const i=src.indexOf('function projectDesignSection(');vm.runInContext(src.slice(i,src.indexOf('\nfunction',i+5)),c);
 Object.assign(c,{designBriefKinds:{'design-consideration':'Consideration'},projectSectionField:()=>'',field:()=>'',settingSelector:()=>'',domainText:()=>'',crypto:{randomUUID:()=>'x'}});
 let ai='',author='';try{ai=vm.runInContext("projectDesignSection({kind:'design-consideration',title:'Test the visit-type check',origin:'model',disposition:'proposed'},'0',false,{})",c);author=vm.runInContext("projectDesignSection({kind:'design-consideration',title:'Mine',origin:'author',disposition:'use'},'1',false,{})",c);}catch(e){}
 if(ai){assert.match(ai,/ac-suggestion-item/);assert.match(ai,/<summary><span class="ac-state ac-state-suggested">Suggested<\/span> Test the visit-type check/);assert.doesNotMatch(author,/ac-state-suggested/);}
 else{const s=src.slice(i,src.indexOf('\nfunction',i+5));assert.match(s,/!manual&&choice==='proposed'\?'<span class="ac-state ac-state-suggested">Suggested<\/span> '/);}
});

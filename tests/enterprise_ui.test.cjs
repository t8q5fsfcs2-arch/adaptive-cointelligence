const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const origin={project:'P1',project_title:'Clinic project',domain:'research',domain_label:'Research',entry:'KN-a'};
const proposal=(o={})=>({ref:{id:'EPROPOSAL-1',revision:1},status:'proposed',reach:'enterprise',named:[],reason:'Why',proposed_by:'alex',at:'x',origin,concept:{title:'Visit',definition:'A booked <time>',includes:'Confirmed',excludes:'',not_confused_with:''},decisions:{},waiting:['lead','steward'],mine:[],changed:false,...o});
function ctx(enterprise){
 const c={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,head:(t)=>`<h1>${t}</h1>`,projectHomeDate:()=>'Nov 24',caseGlyph:l=>`<i class="g-${l}"></i>`,
  state:{project:{id:'P1'},actors:{alex:{name:'Sofia Alvarez'},sam:{name:'Jordan Reyes'},priya:{name:'Dana Okafor'}},enterprise:{concepts:[],proposals:[],roles_mine:[],can_view:false,can_admin:false,role_names:{semantic_services:'Semantic services',stewards:'Enterprise steward'},reach_names:{},...enterprise}}};
 vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/enterprise.js'),'utf8'),c);return c;}
test('the overview is closed to people without an enterprise role and shows counts, never project wording',()=>{
 assert.match(vm.runInContext('enterpriseScreen()',ctx({})),/Administrators, Semantic services and enterprise stewards/);
 const c=ctx({can_view:true,roles:{ref:null,roles:{semantic_services:['alex'],stewards:[]}},proposals:[proposal({mine:['steward']})],waiting_on_me:1,
  overview:{domains:[{project:'P1',project_title:'Clinic project',domain:'research',label:'Research',leads:['Jordan Reyes'],concepts:6,bounded:1,curation:'moderate',widest:'domain',waiting:1,mappings:0,knowledge_version:2}],totals:{concepts:6,bounded:1,mappings:0,proposals:1,enterprise:0},reach:{project:5,domain:1,'named-domains':0,enterprise:0}}});
 const html=vm.runInContext('enterpriseScreen()',c);
 for(const s of ['01 · Coverage','02 · Teams','03 · Proposals for wider reach · 1','04 · Enterprise concepts · 0','05 · Reach of meaning','06 · Facilitated sessions','07 · Roles'])assert.ok(html.includes(s),s);
 assert.match(html,/g-moderate/);assert.match(html,/<b>6<\/b> concepts/);assert.match(html,/Widen Visit \(Research\) to the enterprise/);assert.match(html,/data-action="enterprise-decide" data-id="EPROPOSAL-1"/);
 assert.match(html,/Sofia Alvarez/);assert.match(html,/Nobody assigned/);assert.doesNotMatch(html,/enterprise-roles"|style="/);assert.doesNotMatch(html,/A booked/);
});
test('a concept shows its approved wider reach, an open proposal, and the propose control only for Semantic services or the lead',()=>{
 let c=ctx({roles_mine:['semantic_services']});c.e={id:'KN-a',status:'active'};c.domainKnowledgeProfile=()=>({can_edit:false});
 assert.match(vm.runInContext("enterpriseReachControls('research',e)",c),/data-action="enterprise-propose" data-id="research\|KN-a"/);
 c=ctx({});c.e={id:'KN-a',status:'active'};c.domainKnowledgeProfile=()=>({can_edit:false});assert.doesNotMatch(vm.runInContext("enterpriseReachControls('research',e)",c),/enterprise-propose/);
 c=ctx({proposals:[proposal({mine:['lead']})],concepts:[{ref:{id:'ECONCEPT-1',revision:1},status:'active',reach:'named-domains',named:['Clinical access'],origin,approved:{lead:'sam',steward:'priya'}}]});c.e={id:'KN-a',status:'active'};c.domainKnowledgeProfile=()=>({can_edit:true});
 const html=vm.runInContext("enterpriseReachControls('research',e)",c);assert.match(html,/Reaches Clinical access at this wording · approved by Jordan Reyes and Dana Okafor/);assert.match(html,/waiting on team lead and steward/);assert.match(html,/enterprise-decide/);assert.doesNotMatch(html,/enterprise-propose/);
});
test('deciding shows the exact wording, names the capacity, and needs explicit confirmation',async()=>{
 const c=ctx({proposals:[proposal({mine:['steward'],decisions:{lead:{actor:'sam',reason:'Agreed'}}})]});let shown=null;c.modal=(t,b,l,h)=>{shown={b,h};};c.domainText=n=>`<textarea name="${n}"></textarea>`;
 await vm.runInContext("enterpriseAction('enterprise-decide','EPROPOSAL-1')",c);
 assert.match(shown.b,/A booked &lt;time>/);assert.match(shown.b,/Your decision as enterprise steward/);assert.match(shown.b,/Team lead Jordan Reyes approved/);assert.match(shown.b,/name="confirm" required/);
});
test('a team sees enterprise concepts pinned to its version, a newer one flagged, and only the lead can act',()=>{
 const concept={ref:{id:'ECONCEPT-1',revision:2},status:'active',reach:'enterprise',named:[],title:'Visit',definition:'A booked time',includes:'',excludes:'Walk-ins',not_confused_with:'',origin:{project:'P9',project_title:'Other project',domain:'research',domain_label:'Research',entry:'KN-a'},approved:{lead:'sam',steward:'priya'}};
 const other={...concept,ref:{id:'ECONCEPT-2',revision:1},title:'Slot',reach:'named-domains',named:['Billing']},own={...concept,ref:{id:'ECONCEPT-3',revision:1},title:'Own',origin:{...concept.origin,project:'P1',domain:'design'}};
 const c=ctx({concepts:[concept,other,own]});c.state.adoptions={items:[{ref:{id:'ADOPT-1',revision:1},domain:'design',status:'adopted',concept:{id:'ECONCEPT-1',revision:1},wording:{title:'Visit',definition:'A booked time',includes:'',excludes:'',not_confused_with:''},origin:{project_title:'Other project',domain_label:'Research'}}]};
 c.d={key:'design',label:'Design',can_edit:true};let html=vm.runInContext('enterpriseAdoptionPanel(d)',c);
 assert.match(html,/v1 in use · v2 available/);assert.match(html,/data-action="enterprise-adopt" data-id="design\|ECONCEPT-1">Review v2/);assert.match(html,/enterprise-adoption-drop/);
 assert.doesNotMatch(html,/Slot/);assert.doesNotMatch(html,/Own/);   // named for another domain; the team's own concept
 c.d={key:'design',label:'Design',can_edit:false};html=vm.runInContext('enterpriseAdoptionPanel(d)',c);assert.doesNotMatch(html,/data-action=/);
 c.d={key:'billing',label:'Billing',can_edit:true};html=vm.runInContext('enterpriseAdoptionPanel(d)',c);assert.match(html,/Available to adopt \(3\)/);
});
test('a session shows the agenda and the live item; the facilitator gets agenda tools and never a decide control',()=>{
 const item=(o)=>({id:'ITEM-1',title:'Topic',note:'A note',discussed:false,state:'topic',...o});
 const session=(o={})=>({ref:{id:'ESESSION-1',revision:2},title:'Design · meaning alignment',when:'Nov 24',status:'open',facilitator:'alex',summary:'',project:'P1',project_title:'Clinic project',domain:'design',domain_label:'Design',leads:['sam'],agreed:1,can_edit:false,member:true,health:{concepts:5,bounded:1,mappings:0,open:1},linkable:[],
  items:[item({state:'discussed',discussed:true}),item({id:'ITEM-2',title:'Wider reach: Visit',state:'open',status:'proposed',link:{type:'reach',id:'EPROPOSAL-1'},ask:'Reach: Enterprise',reason:'Why',waiting:['lead','steward'],sides:[{team:'Design',concept:{title:'Visit',definition:'A booked <time>'}}]})],...o});
 let c=ctx({sessions:[session({can_edit:true})],roles_mine:['semantic_services'],can_view:true,proposals:[proposal()]});c.caseIcon=()=>'';c.sn=c.state.enterprise.sessions[0];
 let html=vm.runInContext('enterpriseSessionScreen(sn)',c);
 assert.match(html,/1 of 2 settled/);assert.match(html,/02 · Now: Wider reach: Visit/);assert.match(html,/A booked &lt;time>/);assert.match(html,/The facilitator does not decide/);
 assert.match(html,/enterprise-session-add/);assert.match(html,/enterprise-session-close/);assert.doesNotMatch(html,/enterprise-decide/);assert.doesNotMatch(html,/style="/);
 c=ctx({sessions:[session()],proposals:[proposal({mine:['lead']})]});c.caseIcon=()=>'';c.sn=c.state.enterprise.sessions[0];html=vm.runInContext('enterpriseSessionScreen(sn)',c);
 assert.match(html,/data-action="enterprise-decide" data-id="EPROPOSAL-1">Decide as team lead/);assert.doesNotMatch(html,/enterprise-session-add|enterprise-session-remove/);assert.match(html,/>Back</);
 assert.equal(JSON.stringify(vm.runInContext('enterpriseSessionItems(sn)',c)[1]),JSON.stringify({id:'ITEM-2',title:'Wider reach: Visit',note:'A note',discussed:false,link:{type:'reach',id:'EPROPOSAL-1'}}));
});

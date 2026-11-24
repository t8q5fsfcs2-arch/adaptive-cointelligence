const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const side=(domain,id,title)=>({domain,concept:{id,kind:'term',title,definition:title+' definition',includes:'In <scope>',excludes:'',not_confused_with:'',reach:'project'}});
function ctx(items,extra={}){
 const c={esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),button:(t,a,id)=>`<button data-action="${a}" data-id="${id}">${t}</button>`,projectHomeDate:()=>'Nov 24',
  state:{actors:{sam:{name:'Jordan Reyes'}},domain_knowledge:{domains:[{key:'research',label:'Research',entries:[]},{key:'design',label:'Design',entries:[]}]},
   meaning:{items,relations:{'distinct-from':'is distinct from',broader:'is broader than'},can_propose:true,waiting_on_me:items.filter(i=>i.mine?.length).length,...extra}}};
 c.domainKnowledgeInfo=()=>c.state.domain_knowledge;vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static/meaning.js'),'utf8'),c);return c;}
const map=(o={})=>({ref:{id:'MEANING-1',revision:1},type:'mapping',relation:'broader',status:'proposed',reason:'Why',proposed_by:'sam',at:'x',concepts:[side('research','KN-a','Finding'),side('design','KN-b','Offered slot')],deciders:['research','design'],decisions:{},waiting:['design'],mine:[],changed:[],...o});
test('open proposals show who they wait on, and only the deciding lead gets a Decide control',()=>{
 let c=ctx([map()]);c.d={key:'design',label:'Design'};let html=vm.runInContext('meaningPanel(d)',c);
 assert.match(html,/Finding \(Research\) is broader than Offered slot \(Design\)/);assert.match(html,/waiting on Design/);assert.doesNotMatch(html,/meaning-decide/);assert.doesNotMatch(html,/waiting on you/);
 c=ctx([map({mine:['design'],can_withdraw:true})]);c.d={key:'design',label:'Design'};html=vm.runInContext('meaningPanel(d)',c);
 assert.match(html,/1 waiting on you/);assert.match(html,/data-action="meaning-decide" data-id="MEANING-1"/);assert.match(html,/Withdraw/);
 c=ctx([]);c.d={key:'design',label:'Design'};assert.equal(vm.runInContext('meaningPanel(d)',c),'');
});
test('a concept reads its mapping from its own side, and approved shares list for the receiving team',()=>{
 const share={ref:{id:'MEANING-2',revision:2},type:'share',status:'approved',reason:'r',proposed_by:'sam',at:'x',concepts:[side('research','KN-a','Finding')],grantee:'design',deciders:['research'],decisions:{},waiting:[],mine:[],can_retire:false};
 const c=ctx([map({status:'approved',waiting:[]}),share]);c.d={key:'design',label:'Design'};c.e={id:'KN-b',kind:'term',status:'active'};
 const html=vm.runInContext('knowledgeAcrossTeams(d,e)',c);assert.match(html,/meaning-rel">narrower<\/span><span class="meaning-other">Finding/);assert.match(html,/Approved/);assert.match(html,/data-action="meaning-map" data-id="design\|KN-b"/);
 assert.match(vm.runInContext('meaningPanel(d)',c),/Shared with Design:<\/strong> Finding <span class="caption">from Research/);
 c.e={id:'KN-r',kind:'standard',status:'active'};assert.equal(vm.runInContext('knowledgeAcrossTeams(d,e)',c),'');
});
test('deciding shows both wordings, needs explicit confirmation, and a changed concept can only be declined',async()=>{
 const c=ctx([map({mine:['design'],changed:['Offered slot']})]);let shown=null,sent=null;c.modal=(t,b,l,h)=>{shown={b,h};};c.domainText=(n)=>`<textarea name="${n}"></textarea>`;c.command=async(a,d)=>{sent={a,d};};
 await vm.runInContext("meaningAction('meaning-decide','MEANING-1')",c);
 assert.match(shown.b,/Finding definition/);assert.match(shown.b,/In &lt;scope>/);assert.match(shown.b,/Offered slot changed since this was proposed/);assert.doesNotMatch(shown.b,/value="approve"/);assert.match(shown.b,/name="confirm" required/);
 const fd=new Map([['outcome','decline'],['reason','Stale'],['confirm','on']]);await shown.h({get:k=>fd.get(k)??null});
 assert.equal(sent.a,'meaning-decide');assert.equal(sent.d.confirm,true);assert.equal(sent.d.proposal.id,'MEANING-1');
});

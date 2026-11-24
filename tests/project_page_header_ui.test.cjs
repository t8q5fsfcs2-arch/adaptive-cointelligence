const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');

const app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');
const mountSource=app.slice(app.indexOf('function mountProjectPageHeader('),app.indexOf('function projectNavigationContent('));

// Only the DOM operations used by the layout helper are needed. Moving a node
// detaches it, as in the browser, so identity and ordering checks catch cloning.
class Element {
 constructor(className='',children=[]){this.className=className;this.children=[];this.parentElement=null;this.attributes={};this.append(...children);}
 matches(selector){return selector.startsWith('.')&&selector.slice(1).split('.').every(name=>this.className.split(/\s+/).includes(name));}
 append(...nodes){for(const node of nodes){node.detach();node.parentElement=this;this.children.push(node);}}
 detach(){if(this.parentElement){const siblings=this.parentElement.children;siblings.splice(siblings.indexOf(this),1);this.parentElement=null;}}
 before(node){const parent=this.parentElement;node.detach();node.parentElement=parent;parent.children.splice(parent.children.indexOf(this),0,node);}
 descendants(){return this.children.flatMap(node=>[node,...node.descendants()]);}
 querySelector(selector){
  const choices=selector.split(',').map(part=>part.trim());
  return this.descendants().find(node=>choices.some(choice=>{
   const chain=choice.split('>').map(part=>part.trim());
   if(chain[0]!==':scope')return chain.length===1&&node.matches(chain[0]);
   let current=node;
   for(let index=chain.length-1;index>0;index--){if(!current?.matches(chain[index]))return false;current=current.parentElement;}
   return current===this;
  }))||null;
 }
}
const node=(className,...children)=>new Element(className,children);
function harness({view='requirements',main=node('main')}={}){
 const created=[],context={view,$:selector=>selector==='#main'?main:null,document:{createElement(tag){assert.equal(tag,'div');const element=node('');created.push(element);return element;}}};
 vm.createContext(context);vm.runInContext(mountSource,context);
 return {main,created,mount:()=>vm.runInContext('mountProjectPageHeader()',context)};
}
function fixture(kind,{status=true}={}){
 const identity=node('project-page-identity'),statusNode=node('project-status-line is-updated'),actions=node(kind==='sponsor'?'sponsor-heading-actions':'actions'),heading=node(kind==='chat'?'chat-page-head':kind==='sponsor'?'sponsor-heading':'page-head',node('heading-copy'),actions),breadcrumb=node('breadcrumb'),firstModule=node('card first-module');
 const wrapper=kind==='sponsor'||kind==='sponsor-page'?node('sponsor-surface'):kind==='workflow'?node('workflow-page bridge-page'):null;
 const main=node('main',identity,...(status?[statusNode]:[]));
 if(wrapper){wrapper.append(breadcrumb,heading,firstModule);main.append(wrapper);}else main.append(breadcrumb,heading,firstModule);
 statusNode.attributes={'role':'status','aria-live':'polite','aria-atomic':'true'};
 statusNode.onStatusChange=()=> 'retained listener';actions.onClick=()=> 'retained action';
 return {...harness({main}),identity,status:statusNode,actions,heading,breadcrumb,firstModule,wrapper,originalParent:heading.parentElement};
}

test('project title layout moves the exact identity, status and page header nodes while preserving live status and actions',()=>{
 const h=fixture('page'),statusAttributes=h.status.attributes,statusListener=h.status.onStatusChange,actionListener=h.actions.onClick;
 h.mount();
 const intro=h.main.querySelector('.project-page-header'),title=intro.querySelector('.project-title-area'),status=intro.querySelector('.project-status-area');
 assert.deepEqual(title.children,[h.identity,h.heading]);assert.deepEqual(status.children,[h.status]);
 assert.equal(h.status.attributes,statusAttributes);assert.equal(h.status.onStatusChange,statusListener);assert.equal(h.status.className,'project-status-line is-updated');
 assert.equal(h.actions.parentElement,h.heading);assert.equal(h.actions.onClick,actionListener);
 assert.equal(intro.className,'project-page-header has-status');
 assert.deepEqual(h.originalParent.children,[h.breadcrumb,intro,h.firstModule]);
});

for(const kind of ['page','chat','sponsor','sponsor-page','workflow'])test(kind+' header stays in its original page container with the backlink and first module in order',()=>{
 const h=fixture(kind),parent=h.originalParent,headingChildren=[...h.heading.children];
 h.mount();
 const intro=h.main.querySelector('.project-page-header');
 assert.equal(intro.parentElement,parent);assert.equal(h.heading.parentElement.parentElement,intro);
 assert.deepEqual(h.heading.children,kind==='sponsor'?headingChildren.filter(child=>child!==h.actions):headingChildren);
 assert.equal(h.actions.parentElement,kind==='sponsor'?intro.querySelector('.project-status-area'):h.heading);
 assert.deepEqual(parent.children,[h.breadcrumb,intro,h.firstModule]);
 if(h.wrapper){assert.equal(h.wrapper.parentElement,h.main);assert.deepEqual(h.main.children,[h.wrapper]);}
 assert.equal(h.firstModule.parentElement,parent);
});

test('sponsor progress moves intact into the right column after the exact existing status strip',()=>{
 const h=fixture('sponsor'),meter=node('sponsor-meter'),progress=node('progress-content');
 progress.textContent='Completed · 9 / 22';meter.append(progress);h.actions.append(meter);
 const listener=h.actions.onClick,originalContents=[...h.actions.children];
 h.mount();const intro=h.main.querySelector('.project-page-header'),right=intro.querySelector('.project-status-area');
 assert.deepEqual(right.children,[h.status,h.actions]);assert.deepEqual(h.actions.children,originalContents);
 assert.equal(h.actions.onClick,listener);assert.equal(meter.parentElement,h.actions);assert.equal(progress.textContent,'Completed · 9 / 22');
 assert.equal(h.heading.querySelector('.sponsor-heading-actions'),null);assert.equal(h.heading.querySelector('.sponsor-meter'),null);
});

test('sponsor progress remains available in the right column when the project has no status strip',()=>{
 const h=fixture('sponsor',{status:false});h.mount();
 assert.deepEqual(h.main.querySelector('.project-status-area').children,[h.actions]);
 assert.equal(h.main.querySelector('.project-status-line'),null);
});

test('repeated mounting does not duplicate nodes or replace the existing layout',()=>{
 const h=fixture('sponsor');h.mount();const intro=h.main.querySelector('.project-page-header'),created=h.created.length;
 h.mount();
 assert.equal(h.main.querySelector('.project-page-header'),intro);assert.equal(h.created.length,created);
 for(const original of [h.identity,h.status,h.heading,h.actions,h.breadcrumb,h.firstModule])assert.equal(h.main.descendants().filter(item=>item===original).length,1);
 assert.equal(h.main.descendants().filter(item=>item.matches('.project-page-header')).length,1);
});

test('a project without a status strip still keeps its identity and heading without fabricating status',()=>{
 const h=fixture('page',{status:false});h.mount();const intro=h.main.querySelector('.project-page-header');
 assert.equal(intro.className,'project-page-header');assert.deepEqual(intro.querySelector('.project-title-area').children,[h.identity,h.heading]);
 assert.deepEqual(intro.querySelector('.project-status-area').children,[]);assert.equal(h.main.querySelector('.project-status-line'),null);
});

test('nested arbitrary headings and module headers are not promoted into the page title area',()=>{
 for(const heading of [node('page-head'),node('sponsor-heading'),node('chat-page-head'),node('arbitrary-header')]){
  const identity=node('project-page-identity'),status=node('project-status-line'),card=node('card',heading),main=node('main',identity,status,card),h=harness({main});
  h.mount();assert.deepEqual(main.children,[identity,status,card]);assert.equal(heading.parentElement,card);assert.equal(h.created.length,0);
 }
});

test('the existing Decisions & Issues title grid stays owned by its dedicated mount',()=>{
 const identity=node('project-page-identity'),status=node('project-status-line'),heading=node('page-head'),titleArea=node('accountability-title-area',heading),intro=node('accountability-page-intro',titleArea),wrapper=node('workflow-page bridge-page',intro),main=node('main',identity,status,wrapper),h=harness({view:'review',main});
 h.mount();assert.deepEqual(main.children,[identity,status,wrapper]);assert.equal(heading.parentElement,titleArea);assert.equal(h.created.length,0);
});

for(const view of ['projects','thought-partner'])test(view+' remains outside the project title grid even with a recognizable header',()=>{
 const h=fixture('page'),before=[...h.main.children],global=harness({view,main:h.main});
 global.mount();assert.deepEqual(h.main.children,before);assert.equal(global.created.length,0);assert.equal(h.heading.parentElement,h.main);
});

test('missing main is a safe no-op',()=>{const h=harness({main:null});assert.doesNotThrow(h.mount);assert.equal(h.created.length,0);});

test('domain workbench title names the role once while project identity remains the shared anchor',()=>{
 const source=fs.readFileSync(path.join(__dirname,'../src/workbench/static/domain-chat.js'),'utf8');
 for(const label of ['Research','Design','Research & <evaluation>']){
  const context={state:{project:{title:'Exact project anchor',display_title:'Project display label'}},domainProfile:()=>({config:{label}}),esc:value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]))};
  vm.createContext(context);vm.runInContext(source.slice(source.indexOf('function chatHeader('),source.indexOf('function chatContextChanged(')),context);
  const html=vm.runInContext('chatHeader()',context);
  assert.match(html,/<header class="chat-page-head workbench-head"><div><h1 tabindex="-1">/);assert.ok(html.includes(context.esc(label)+' workbench</h1>'));
  assert.equal((html.replace(/<[^>]+>/g,' ').match(/workbench/g)||[]).length,1);assert.match(html,/Private to you until you share/);assert.doesNotMatch(html,/Exact project anchor|Project display label|class="eyebrow"/);
 }
});

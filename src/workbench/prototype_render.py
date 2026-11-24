"""Deterministic editable Figma nodes, never model-generated executable code.

Screens use only native Figma frames, auto layout and text, so they work in any
file without a component library. See docs/decisions/D002.
"""
import json
from html import escape

RENDERER = 'native-prototype-v2'

def figma_code(plan,marker):
    data=json.dumps(plan,ensure_ascii=True);tag=json.dumps(marker)
    return "const spec="+data+"; const marker="+tag+";\n"+CODE

CODE=r"""
const created=[];
const page=figma.currentPage;
// A completed attempt can be reconciled safely by its visible marker.
const existing=page.children.find(n=>n.name===marker+' · complete');
if(existing)return {createdNodeIds:[existing.id],frames:page.children.filter(n=>n.type==='FRAME'&&n.name.startsWith(marker+' / screen / ')).map(n=>({id:n.id,name:n.name})),reused:true};
if(page.children.some(n=>n.name===marker+' · building'))throw Error('An incomplete earlier creation must be reconciled before retrying');
const available=await figma.listAvailableFontsAsync();
const font=available.find(f=>f.fontName.family==='Noto Sans'&&f.fontName.style==='Regular')?.fontName||available.find(f=>f.fontName.family==='Inter'&&f.fontName.style==='Regular')?.fontName;
if(!font)throw Error('Install Noto Sans or Inter before creating the prototype');
const bold=available.find(f=>f.fontName.family===font.family&&f.fontName.style==='Bold')?.fontName||font;
await figma.loadFontAsync(font);await figma.loadFontAsync(bold);
const paint=hex=>({type:'SOLID',color:{r:parseInt(hex.slice(1,3),16)/255,g:parseInt(hex.slice(3,5),16)/255,b:parseInt(hex.slice(5,7),16)/255}});
const track=n=>(created.push(n.id),n);
function stack(parent,name,w,gap=16,pad=0,bg=null){const n=track(figma.createAutoLayout('VERTICAL'));n.name=name;n.resize(w,40);n.primaryAxisSizingMode='AUTO';n.counterAxisSizingMode='FIXED';n.itemSpacing=gap;n.paddingTop=pad;n.paddingBottom=pad;n.paddingLeft=pad;n.paddingRight=pad;n.fills=bg?[paint(bg)]:[];parent.appendChild(n);return n;}
function text(parent,value,size=16,strong=false,color='#333333',width=parent.width-parent.paddingLeft-parent.paddingRight){const n=track(figma.createText());n.fontName=strong?bold:font;n.characters=value;n.fontSize=size;n.lineHeight={unit:'PIXELS',value:size>=24?32:24};n.fills=[paint(color)];n.resize(width,24);n.textAutoResize='HEIGHT';parent.appendChild(n);n.layoutSizingVertical='HUG';return n;}
const right=Math.max(0,...page.children.map(n=>n.x+n.width));
const originX=right+160;
const board=stack(page,marker+' · building',1240,12,24,'#F2F2F2');board.x=originX;board.y=80;
text(board,spec.title,28,true);text(board,'Prototype alternatives for human research. No usability, storage or runtime result is established.',13,false,'#666666');
// Native field and button builders: no external component library is required.
function field(parent,f){const g=stack(parent,f.label,342,6);text(g,f.label,13,true,'#111111');const box=stack(g,'Input',342,0,12,'#FFFFFF');box.cornerRadius=8;box.strokes=[paint('#C9CED6')];box.strokeWeight=1;text(box,f.value,16,false,'#111111');text(g,f.help,13,false,'#5B6270');return g;}
function button(parent,label){const b=track(figma.createAutoLayout('HORIZONTAL'));b.name=label;b.resize(342,48);b.primaryAxisSizingMode='FIXED';b.counterAxisSizingMode='FIXED';b.primaryAxisAlignItems='CENTER';b.counterAxisAlignItems='CENTER';b.cornerRadius=8;b.fills=[paint('#2F5BEA')];parent.appendChild(b);const t=track(figma.createText());t.fontName=bold;t.characters=label;t.fontSize=16;t.fills=[paint('#FFFFFF')];b.appendChild(t);return b;}
const frames=[],links=[];
let variantY=board.y+board.height+48;
for(const variant of spec.variants){
 const group=stack(page,marker+' / '+variant.name,1240,8);group.x=originX;group.y=variantY;text(group,variant.name,24,true);text(group,variant.hypothesis);text(group,'Changed factor: '+variant.change,13,false,'#666666');
 const targets={};let screenIndex=0;const screenY=group.y+group.height+24;
 for(const screen of variant.screens){
  const frame=stack(page,marker+' / screen / '+variant.key+' / '+screen.key+' · '+screen.title,390,0,0,'#FFFFFF');frame.x=originX+screenIndex++*430;frame.y=screenY;frame.resize(390,844);frame.primaryAxisSizingMode='FIXED';frame.clipsContent=true;frame.overflowDirection='VERTICAL';targets[screen.key]=frame;
  const header=stack(frame,'Header',390,4,24,'#111111');text(header,String(spec.title||'Prototype').toUpperCase(),16,true,'#FFFFFF');
  const body=stack(frame,'Task',390,12,24);text(body,screen.title,24,true);text(body,screen.description);
  const status=stack(body,'Visible system status',342,4,16,'#EEF2FD');status.cornerRadius=8;text(status,screen.status,16,true,'#333333');
  for(const f of screen.fields)field(body,f);
  for(const action of screen.actions){const b=button(body,action.label);links.push({button:b,target:action.destination,targets});}
  frames.push({id:frame.id,name:frame.name,variant:variant.key,screen:screen.key,requirement_ids:screen.requirement_ids,brief_section_ids:screen.brief_section_ids});
 }
 variantY=screenY+920;
}
for(const link of links){if(link.targets[link.target]===link.button.parent.parent)continue;await link.button.setReactionsAsync([{trigger:{type:'ON_CLICK'},actions:[{type:'NODE',destinationId:link.targets[link.target].id,navigation:'NAVIGATE',transition:null,preserveScrollPosition:false}]}]);}
const protocol=stack(page,marker+' / Human research protocol',660,12,24,'#FFFFFF');protocol.x=originX+1340;protocol.y=board.y;text(protocol,'Research comparison plan',24,true);text(protocol,'No winning variant selected. Researchers determine method, recruitment and decision authority.',13,false,'#666666');
for(const [key,value] of Object.entries(spec.test_plan)){text(protocol,key.replaceAll('_',' '),16,true);text(protocol,value);}
text(protocol,'Factors and levels',16,true);for(const f of spec.factors)text(protocol,f.name+': '+f.levels.join(' / ')+'. '+f.why);
board.name=marker+' · complete';figma.viewport.scrollAndZoomIntoView([board,...frames.map(f=>page.children.find(n=>n.id===f.id))]);
return {createdNodeIds:created,frames,boardId:board.id,font:font.family,marker,editable:true,limitations:'Static editable screens with navigation links. Inputs, storage, network and runtime instrumentation are not implemented.'};
"""

def html_preview(plan):
    e=escape
    cards=[]
    for v in plan['variants']:
        screens=[]
        for s in v['screens']:
            fields=''.join('<label><b>'+e(f['label'])+'</b><span class="field">'+e(f['value'])+'</span><small>'+e(f['help'])+'</small></label>' for f in s['fields'])
            actions=''.join('<span class="action">'+e(a['label'])+'</span>' for a in s['actions'])
            screens.append('<article class="screen"><header>'+e(plan['title']).upper()+'</header><main><h2>'+e(s['title'])+'</h2><p>'+e(s['description'])+'</p><p class="status">'+e(s['status'])+'</p>'+fields+actions+'</main></article>')
        cards.append('<section><h2>'+e(v['name'])+'</h2><p>'+e(v['hypothesis'])+'</p><p>Changed factor: '+e(v['change'])+'</p><div class="screens">'+''.join(screens)+'</div></section>')
    return '<!doctype html><meta charset="utf-8"><title>'+e(plan['title'])+'</title><style>body{font:16px/1.5 "Noto Sans",sans-serif;background:#f4f5f7;color:#111;margin:32px}h1,h2{color:#000}section{margin:40px 0}.screens{display:flex;gap:40px;align-items:start}.screen{width:390px;min-width:390px;min-height:844px;background:white;border:1px solid #ddd}header{background:#111;color:white;padding:24px;font-weight:bold}main{padding:24px}label{display:block;margin:20px 0}label b,small{display:block}.field{display:block;border:1px solid #999;border-radius:4px;padding:12px;margin:6px 0}small{font-size:13px;color:#666}.status{background:#f0eeff;padding:16px;border-radius:8px}.action{display:block;background:#e6e6e6;padding:12px;margin:16px 0;border-radius:4px;font-weight:bold}</style><h1>'+e(plan['title'])+'</h1><p>Prototype alternatives. Static representations, not research validation.</p>'+''.join(cards)

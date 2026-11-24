const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
function harness(){
 const dialogs=[],calls=[],ctx={state:{actor:'administrator',auth:{administrator:true},global_context:true,csrf:'test'},view:'projects',dirty:false,busy:false,
 esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
 modal:(...args)=>{ctx.dirty=false;dialogs.push(args)},button:(label,action,id)=>`<button data-action="${action}" data-id="${id}">${label}</button>`,
 confirm:()=>true,document:{addEventListener(){}},$:()=>null,settingsTime:t=>t,
 command:async(action,data)=>{calls.push({action,data});return {message:'Saved'}},loadHome:async()=>calls.push('home'),
 };
 vm.createContext(ctx);for(const file of ['settings.js','home.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/workbench/static',file),'utf8'),ctx);
 ctx.loadHome=async()=>calls.push('home');
 return {ctx,dialogs,calls,run:s=>vm.runInContext(s,ctx)};
}
const data=()=>({revision:1,items:[{title:'Draft title',body:'Draft message.'}],pending:true,published:null,history:[]});
test('published Home announcements escape plain text and replace samples without exposing draft content',()=>{
 const h=harness();h.ctx.state.announcements={sample:false,published_at:'2026-11-12T12:00:00Z',items:[{title:'<img onerror=bad>',body:'First paragraph.\nSecond paragraph.'}]};
 const html=h.run('homeAnnouncementsPanel()');assert.match(html,/&lt;img onerror=bad>/);assert.doesNotMatch(html,/<img|Sample updates/);assert.match(html,/Announcements/);assert.match(html,/Updated/);
 h.ctx.state.announcements.items=[];assert.match(h.run('homeAnnouncementsPanel()'),/No announcements right now/);
});
test('Admin opens sitewide editing with Save draft and preview, while other roles have no edit entry',async()=>{
 const h=harness();h.ctx.fetch=async url=>({ok:true,json:async()=>data()});
 await h.run('openAnnouncementsSettings()');const [title,html,save]=h.dialogs.at(-1);assert.equal(title,'Announcements');assert.equal(save,'Save draft');assert.match(h.dialogs.at(-1)[4].footerActions,/settings-announcement-preview/);assert.match(html,/maxlength="500"/);assert.match(html,/Draft changes/);assert.doesNotMatch(html,/data-action="settings-announcement-publish"/);assert.equal(h.calls.length,0);
 h.ctx.state.auth={administrator:false};h.ctx.state.actor='sam';await assert.rejects(h.run('openAnnouncementsSettings()'),/Only the Administrator/);
});
test('preview publishes only the exact saved draft; unsaved text stays in the editor buffer',async()=>{
 const h=harness();h.ctx.fetch=async()=>({ok:true,json:async()=>data()});await h.run('openAnnouncementsSettings()');
 const fields={title:'Draft title',body:'Draft message.'},form={reportValidity:()=>true,querySelectorAll:()=>[{querySelector:s=>({value:s.includes('title')?fields.title:fields.body})}]};h.ctx.$=()=>form;
 h.run('previewAnnouncements()');let dialog=h.dialogs.at(-1);assert.equal(dialog[2],'Publish to Home');assert.equal(h.calls.length,0);
 await dialog[3]();assert.equal(h.calls[0].action,'announcements-publish');assert.equal(h.calls[0].data.expected,1);assert.equal(h.calls[0].data.confirm,true);
 fields.body='Unsaved revision';h.run('previewAnnouncements()');dialog=h.dialogs.at(-1);assert.equal(dialog[3],null);assert.match(dialog[1],/Save this draft before publishing/);assert.match(dialog[1],/Unsaved revision/);
 h.run('showAnnouncementsEditor()');assert.match(h.dialogs.at(-1)[1],/Unsaved revision/);assert.equal(h.ctx.dirty,true);
});
test('removing an update changes only the draft and saving does not call publish',async()=>{
 const h=harness();h.ctx.fetch=async()=>({ok:true,json:async()=>data()});await h.run('openAnnouncementsSettings()');
 h.ctx.$=()=>({querySelectorAll:()=>[{querySelector:s=>({value:s.includes('title')?'Draft title':'Draft message.'})}]});
 await h.run("announcementSettingsAction('settings-announcement-remove','0')");assert.match(h.dialogs.at(-1)[1],/No updates in this draft/);assert.equal(h.calls.length,0);
 h.ctx.$=()=>({querySelectorAll:()=>[]});await h.dialogs.at(-1)[3]();assert.equal(h.calls[0].action,'announcements-save');assert.equal(h.calls[0].data.items.length,0);
});

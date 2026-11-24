// Exercise the application's real presentation helpers without booting the app.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
module.exports=context=>{
 const app=fs.readFileSync(path.join(__dirname,'../src/workbench/static/app.js'),'utf8');
 vm.runInContext(app.slice(app.indexOf('function referenceRecord('),app.indexOf('\nasync function load(')),context);
 const passive=app.match(/^const ref=([^\n]+);$/m);
 if(!passive)throw Error('The shared reference renderer was not found.');
 vm.runInContext('ref='+passive[1]+';',context);
};

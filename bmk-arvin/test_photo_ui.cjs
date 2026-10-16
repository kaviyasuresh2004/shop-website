const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map(),calls=[];let ready;
function element(id){if(!elements.has(id))elements.set(id,{value:'1',files:[],style:{},handlers:{},innerHTML:'',textContent:'',disabled:false,addEventListener(n,f){const previous=this.handlers[n];this.handlers[n]=e=>{previous?.(e);return f(e)}},querySelector(){return element('submit')},querySelectorAll(){return []},click(){this.clicked=true}});return elements.get(id)}
const context={Array,Promise,URL:{createObjectURL:()=> 'blob:local-test',revokeObjectURL(){}},MutationObserver:class{observe(){}},FileReader:class{readAsDataURL(){this.result='data:image/png;base64,dGVzdA==';this.onload()}},confirm:()=>true,document:{addEventListener(n,f){ready=f},getElementById:element},data:{products:[{id:1,photo_urls:[]}]},esc:String,t:k=>k,api:async(k,d)=>{calls.push(d);return {ok:true}},load:async()=>{}};
vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/assets/photos.js','utf8'),context);ready();
(async()=>{
 const drop=element('photoDrop'),form=element('productPhotoForm');let prevented=false;
 drop.handlers.drop({preventDefault(){prevented=true},dataTransfer:{files:[{name:'front.png',size:10,type:'image/png'},{name:'side.jpg',size:20,type:'image/jpeg'}]}});
 assert.ok(prevented);assert.ok(element('photoPreview').innerHTML.includes('front.png'));assert.ok(element('photoPreview').innerHTML.includes('side.jpg'));
 await form.handlers.submit({preventDefault(){}});assert.equal(calls.length,2);assert.ok(calls.every(c=>c.action==='add'&&c.product==='1'));assert.equal(element('photoResult').textContent,'photoSaved');
 drop.handlers.drop({preventDefault(){},dataTransfer:{files:Array.from({length:7},()=>({size:10,type:'image/png'}))}});assert.equal(element('photoResult').textContent,'photoInvalid');
 drop.handlers.drop({preventDefault(){},dataTransfer:{files:[{size:5000001,type:'image/png'}]}});assert.equal(element('photoResult').textContent,'photoInvalid');
 drop.handlers.keydown({key:'Enter',preventDefault(){}});assert.ok(element('photoFile').clicked);
 console.log('PASS: drag-and-drop selection, multi-file uploads, limits and keyboard file picker.');
})().catch(e=>{console.error(e);process.exitCode=1});

const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const dictionary=JSON.parse(fs.readFileSync(__dirname+'/assets/en.json','utf8'));
const elements=new Map(),events={},notifications=[];
function element(id){
 if(['customerProfile','customerPassword'].includes(id)&&!element('infoContent').innerHTML.includes('id="'+id+'"'))return null;
 if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',open:true,closed:false,querySelectorAll(){return []},querySelector(){return {disabled:false}},close(){this.closed=true;this.open=false},showModal(){this.open=true},addEventListener(){},reset(){}});
 return elements.get(id);
}
const context={console,I18n:{t:key=>dictionary[key]||key},document:{getElementById:element,addEventListener:(key,value)=>events[key]=value},FormData:class{constructor(){return new Map([['name','Test'],['email','test@example.test'],['password','Eight888']])}},toast:key=>notifications.push(key)};
vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/assets/customer.js','utf8')+'\nthis.account=CustomerAccount;',context);
const account=context.account;
(async()=>{
 account.customer={name:'Test <name>',email:'test@example.test',phone:'123',address:'Address'};account.mode='overview';account.render();
 assert.ok(element('infoContent').innerHTML.includes('Personal details'));assert.ok(!element('infoContent').innerHTML.includes('id="customerPassword"'));assert.ok(element('infoContent').innerHTML.includes('Test &lt;name&gt;'));
 account.mode='profile';account.render();assert.ok(element('infoContent').innerHTML.includes('id="customerProfile"'));assert.ok(element('infoContent').innerHTML.includes('value="123"'));
 account.mode='security';account.render();assert.ok(element('infoContent').innerHTML.includes('id="customerPassword"'));assert.ok(element('infoContent').innerHTML.includes('name="confirmation"'));
 account.customer=null;account.mode='register';account.render();account.api=async()=>({ok:true});account.refresh=async()=>{account.customer={name:'Test'}};
 await element('customerAuth').onsubmit({preventDefault(){},target:element('customerAuth')});assert.equal(element('infoDialog').closed,true);assert.equal(notifications[0],'accountCreated');
 console.log('PASS: overview, editable details, separate password settings, escaped content, registration returns to shopping.');
})().catch(error=>{console.error(error);process.exitCode=1});

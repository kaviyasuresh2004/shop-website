const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c={window:{},document:{addEventListener(){}},Number,String,Error};vm.createContext(c);vm.runInContext(fs.readFileSync(__dirname+'/assets/staff-inventory.js','utf8'),c);const x=c.window.StaffInventory;
const products=Array.from({length:9165},(_,i)=>({id:i+1,name:'Product '+(i+1),sku:'SKU-'+(i+1),price:1250,category:i%2?'Plumbing':'Electrical'}));
assert.equal(x.filter(products,'','').length,9165);assert.equal(x.filter(products,'Product 9165','')[0].id,9165);assert.ok(x.filter(products,'','Plumbing').every(p=>p.category==='Plumbing'));assert.equal(x.filter(products,'9165','Plumbing').length,0);assert.equal(x.cents('12.50'),1250);assert.equal(x.cents('0.06'),6);assert.equal(x.cents('89'),8900);for(const value of ['-1','NaN','1.234','Infinity'])assert.throws(()=>x.cents(value));console.log('PASS: full inventory search, category filtering and exact BND conversion.');

const elements=new Map();const element=id=>{if(!elements.has(id))elements.set(id,{value:'',innerHTML:'',textContent:'',hidden:false,disabled:false});return elements.get(id)};
const selects=Array.from({length:5},()=>({value:'',innerHTML:''}));
const ui={console,Map,Set,Date,Number,String,Math,Object,JSON,Error,setTimeout,clearTimeout,document:{getElementById:element,querySelectorAll:()=>selects,addEventListener(){}},I18n:{language:'en',t:(k,v)=>k+JSON.stringify(v||{})}};ui.window=ui;vm.createContext(ui);
vm.runInContext(fs.readFileSync(__dirname+'/assets/staff-inventory.js','utf8'),ui);
vm.runInContext(fs.readFileSync(__dirname+'/assets/staff.js','utf8').replace(/^start\(\);$/m,''),ui);
ui.fixture=products;
vm.runInContext("data={products:fixture,companies:[{id:1,name:'Test shop'}],stock:[],setup:false};staff={user:{name:'worker',role:'worker',company:1},inventory_source:[],enquiries:[],orders:[],sales:[],audit:[],promotions:[],report:{}};render()",ui);
assert.equal((selects[0].innerHTML.match(/<option/g)||[]).length,9165,'every product selectable without the old 100-item cap');
assert.ok(selects[0].innerHTML.includes('Product 9165'));assert.ok(element('inventory').innerHTML.includes('BND 12.50'));vm.runInContext('inventoryPage=91;render()',ui);assert.ok(element('inventory').innerHTML.includes('Product 9165'));assert.ok(element('inventoryPages').innerHTML.includes('data-inventory-page="91"'));assert.ok(element('inventoryPages').innerHTML.includes('aria-current="page"'));assert.ok(!element('inventoryPages').innerHTML.includes('data-inventory-page="92"'));
element('inventoryCategory').value='Plumbing';vm.runInContext('inventoryPage=0;render()',ui);assert.ok(!selects[0].innerHTML.includes('Product 9165'));assert.ok(selects[0].innerHTML.includes('Product 9164'));
element('inventoryCategory').value='';element('inventorySearch').value='Product 9165';vm.runInContext('inventoryPage=0;render()',ui);assert.equal((selects[0].innerHTML.match(/<option/g)||[]).length,1);assert.ok(element('inventory').innerHTML.includes('Product 9165'));
console.log('PASS: integrated worker inventory and photo selectors expose all products and respond to category and search filters.');

assert.deepEqual(Array.from(x.pages(92,0)),[0,1,2,3,4,91]);assert.deepEqual(Array.from(x.pages(0,0)),[]);assert.deepEqual(Array.from(x.pages(1,0)),[0]);assert.ok(x.pages(92,50).includes(50));assert.ok(x.pages(92,91).includes(91));console.log('PASS: numbered inventory page navigation and boundary cases.');

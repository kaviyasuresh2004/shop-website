/* Customer cookies and sessions are separate from administrator/worker sessions. */
const CustomerAccount = {
 customer:null, orders:[], active:false, continuation:null, mode:'login',
 async api(path,body){
  let response;
  try { response=await fetch('/api/customer/'+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{cache:'no-store'}); }
  catch {throw Error(I18n.t('networkError'));}
  const result=await response.json();
  if(!response.ok)throw Error(I18n.error(result.error));
  return result;
 },
 async refresh(){
  const response=await fetch('/api/customer/me',{cache:'no-store'});
  if(response.status===401){this.customer=null;this.orders=[];return;}
  if(!response.ok)throw Error(I18n.t('networkError'));
  const result=await response.json();this.customer=result.customer;this.orders=result.orders;
 },
 open(next=null){
  this.active=true;this.continuation=next;this.mode='login';
  document.getElementById('infoContent').innerHTML='<p>'+I18n.t('accountTitle')+'</p>';
  const dialog=document.getElementById('infoDialog');if(!dialog.open)dialog.showModal();
  this.refresh().then(()=>this.render()).catch(error=>{document.getElementById('infoContent').textContent=error.message;});
 },
 render(){
  const t=key=>I18n.t(key), esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const content=document.getElementById('infoContent');
  const label=(key,name,type='text',extra='')=>`<label>${esc(t(key))}<input name="${name}" type="${type}" ${extra}></label>`;
  if(!this.customer){
   const register=this.mode==='register';
   content.innerHTML=`<h2>${esc(t(register?'customerRegister':'customerSignIn'))}</h2><p>${esc(t('accountRequired'))}</p><form id="customerAuth" class="staff-form">${register?label('fullName','name','text','required maxlength="200" autocomplete="name"'):''}${label('email','email','email','required maxlength="254" autocomplete="username"')}${label('password','password','password',`required ${register?'minlength="12"':''} maxlength="256" autocomplete="${register?'new-password':'current-password'}"`)}${register?label('phone','phone','tel','maxlength="80" autocomplete="tel"')+label('address','address','text','maxlength="1000" autocomplete="street-address"'):''}<p>${esc(t('customerPasswordHelp'))}</p><button class="button navy">${esc(t(register?'customerRegister':'login'))}</button><p id="customerError" role="alert"></p></form><button class="text-link" id="customerSwitch">${esc(t(register?'customerSignIn':'customerRegister'))}</button>`;
   document.getElementById('customerSwitch').onclick=()=>{this.mode=register?'login':'register';this.render();};
   document.getElementById('customerAuth').onsubmit=async event=>{
    event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;
    try{await this.api(register?'register':'login',Object.fromEntries(new FormData(event.target)));await this.refresh();if(this.continuation){const next=this.continuation;this.continuation=null;this.active=false;next();}else this.render();}
    catch(error){document.getElementById('customerError').textContent=error.message;button.disabled=false;}
   };
   return;
  }
  content.innerHTML=`<h2>${esc(t('accountTitle'))}</h2><p>${esc(this.customer.name)} · ${esc(this.customer.email)}</p><button id="customerLogout" class="button navy">${esc(t('signOut'))}</button><h3>${esc(t('orderHistory'))}</h3>${this.orders.length?this.orders.map(order=>`<section class="staff-panel"><b>#${order.id} · BND ${(order.total/100).toFixed(2)}</b><p>${esc(order.status)} · ${esc(order.created)}</p>${order.items.map(item=>`<p>${esc(item.sku)} × ${item.qty}</p>`).join('')}</section>`).join(''):`<p>${esc(t('noCustomerOrders'))}</p>`}<h3>${esc(t('changePassword'))}</h3><form id="customerPassword" class="staff-form">${label('currentPassword','current_password','password','required maxlength="256" autocomplete="current-password"')}${label('newPassword','password','password','required minlength="12" maxlength="256" autocomplete="new-password"')}<button class="button navy">${esc(t('changePassword'))}</button></form><p id="customerError" role="status"></p>`;
  document.getElementById('customerLogout').onclick=async()=>{try{await this.api('logout',{});this.customer=null;this.orders=[];this.render();}catch(error){document.getElementById('customerError').textContent=error.message;}};
  document.getElementById('customerPassword').onsubmit=async event=>{event.preventDefault();const button=event.target.querySelector('button');button.disabled=true;try{await this.api('password',Object.fromEntries(new FormData(event.target)));event.target.reset();document.getElementById('customerError').textContent=t('passwordChanged');}catch(error){document.getElementById('customerError').textContent=error.message;}finally{button.disabled=false;}};
 }
};
document.addEventListener('languagechange',()=>{if(CustomerAccount.active&&document.getElementById('infoDialog')?.open)CustomerAccount.render();});
document.addEventListener('DOMContentLoaded',()=>document.getElementById('infoDialog').addEventListener('close',()=>{CustomerAccount.active=false;CustomerAccount.continuation=null;}));

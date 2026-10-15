window.renderWorkerAccounts=function(currentStaff,catalog){
 if(currentStaff.user.role!=='admin')return;
 document.getElementById('workerManagementLink')?.removeAttribute('hidden');
 const roster=currentStaff.accounts||[], selector=document.getElementById('manageAccountName'), selected=selector.value;
 document.getElementById('workerAccounts').innerHTML=table(roster.map(account=>({...account,role:I18n.t(account.role)})),['name','role','company']);
 selector.innerHTML=roster.filter(account=>account.name!==currentStaff.user.name).map(account=>`<option value="${esc(account.name)}">${esc(account.name)} · ${esc(I18n.t(account.role))}</option>`).join('');
 if([...selector.options].some(option=>option.value===selected))selector.value=selected;
 selector.disabled=!selector.options.length;
 document.querySelector('#manage_user button[type="submit"],#manage_user button:not([type])').disabled=!selector.options.length;
};
document.addEventListener('DOMContentLoaded',async()=>{
 await siteReady;
 for(const id of ['login','user','manage_user']){
  const form=document.getElementById(id),input=form.elements.password;
  const toggle=document.createElement('button');toggle.type='button';toggle.className='text-link';toggle.dataset.showPassword='';toggle.setAttribute('aria-pressed','false');toggle.textContent=I18n.t('showPassword');
  const control=document.createElement('div');control.className='password-control';
  input.parentElement.insertBefore(control,input);control.append(input,toggle);
  toggle.onclick=()=>{const visible=input.type==='password';input.type=visible?'text':'password';toggle.setAttribute('aria-pressed',String(visible));toggle.textContent=I18n.t(visible?'hidePassword':'showPassword');};
 }
 const jump=document.createElement('a');jump.id='workerManagementLink';jump.className='button navy';jump.href='#workerAccounts';jump.hidden=typeof staff==='undefined'||staff?.user?.role!=='admin';jump.textContent=I18n.t('staffAccounts');
 document.querySelector('.staff-session').append(jump);
 const action=document.getElementById('manageAccountAction'),password=document.getElementById('manage_user').elements.password;
 action.onchange=()=>{password.required=action.value==='reset';password.disabled=action.value==='delete';if(password.disabled)password.value='';};
 document.addEventListener('languagechange',()=>{jump.textContent=I18n.t('staffAccounts');document.querySelectorAll('[data-show-password]').forEach(button=>{button.textContent=I18n.t(button.getAttribute('aria-pressed')==='true'?'hidePassword':'showPassword');});});
});


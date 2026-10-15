document.addEventListener('DOMContentLoaded',()=>{
 const panel=document.getElementById('recoveryPanel'),form=document.getElementById('recoveryForm'),result=document.getElementById('recoveryResult');
 document.getElementById('openRecovery').onclick=()=>{panel.hidden=!panel.hidden;};
 form.onsubmit=async event=>{
  event.preventDefault();const button=form.querySelector('button');button.disabled=true;result.textContent='';
  try{
   const response=await fetch('/api/recover-admin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(Object.fromEntries(new FormData(form)))});
   const body=await response.json();if(!response.ok)throw Error(I18n.error(body.error));
   form.reset();result.textContent=I18n.t('recoveryDone');
  }catch(error){result.textContent=error.message||I18n.t('networkError');}finally{button.disabled=false;}
 };
});

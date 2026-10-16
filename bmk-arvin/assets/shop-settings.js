window.renderShopSettings=function(currentStaff,catalog){
 if(currentStaff.user.role!=='admin')return;
 const form=document.getElementById('shopSettingsForm'),settings=catalog.shopDetails;
 for(const key of ['legal_name','registered_address','incorporation_date','address','phone','hours','map_url','delivery_policy','returns_policy','privacy_policy'])form.elements[key].value=settings[key]||'';
 for(const key of ['checkout_enabled','catalogue_confirmed'])form.elements[key].checked=!!settings[key];
 for(const region of ['Brunei-Muara','Tutong','Belait','Temburong'])form.elements['fee_'+region].value=(settings.delivery_fees[region]/100).toFixed(2);
};
window.applyShopDetails=function(catalog){
 const details=catalog.shopDetails;
 if(!details)return;
 let legal=document.getElementById('registeredCompanyInfo');if(!legal){legal=document.createElement('p');legal.id='registeredCompanyInfo';document.querySelector('.shop-info')?.append(legal);}legal.textContent=[details.legal_name,details.registered_address?I18n.t('registeredAddress')+': '+details.registered_address:'',details.incorporation_date?I18n.t('incorporationDate')+': '+details.incorporation_date:''].filter(Boolean).join(' | ');
 const info=document.querySelector('[data-t="shopInfoPending"]');
 if(info&&details.address)info.textContent=[details.address,details.phone,details.hours].filter(Boolean).join(' · ');
 const map=document.querySelector('.shop-info .pending');
 if(map&&details.map_url){const link=document.createElement('a');link.className='pending';link.href=details.map_url;link.target='_blank';link.rel='noopener noreferrer';link.textContent=I18n.t('viewMap');map.replaceWith(link);}
 const contact=document.querySelector('[data-t="contactPending"]');
 if(contact&&details.phone)contact.textContent=[details.phone,details.hours].filter(Boolean).join(' · ');
 const strip=document.querySelector('.demo-strip');if(strip)strip.hidden=!catalog.preview;
 if(!catalog.preview)document.querySelectorAll('[data-t="sampleCatalogue"],[data-t="sampleRates"],[data-t="localPreview"]').forEach(node=>node.hidden=true);
 const rows=document.querySelectorAll('.delivery-rates > div:not(.rate-head)');
 ['pickup','Brunei-Muara','Tutong','Belait','Temburong'].forEach((region,index)=>{const amount=rows[index]?.querySelector('b');if(amount)amount.textContent=details.delivery_fees[region]?'BND '+(details.delivery_fees[region]/100).toFixed(2):I18n.t('free');});
 if(details.delivery_policy){const policy=document.querySelector('[data-t="deliveryDisclaimer"]');if(policy)policy.textContent=details.delivery_policy;}
};
document.addEventListener('DOMContentLoaded',()=>{
 const form=document.getElementById('shopSettingsForm');if(!form)return;
 form.onsubmit=async event=>{
  event.preventDefault();const button=form.querySelector('button'),result=document.getElementById('shopSettingsResult');button.disabled=true;result.textContent='';
  try{
   const settings=Object.fromEntries(new FormData(form));
   settings.checkout_enabled=form.elements.checkout_enabled.checked;settings.catalogue_confirmed=form.elements.catalogue_confirmed.checked;
   settings.delivery_fees={pickup:0};
   for(const region of ['Brunei-Muara','Tutong','Belait','Temburong']){settings.delivery_fees[region]=Math.round(Number(settings['fee_'+region])*100);delete settings['fee_'+region];}
   const response=await fetch('/api/shop-settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(settings)});
   if(!response.ok)throw Error(I18n.t('shopSettingsError'));
   await load();result.textContent=I18n.t('shopSettingsSaved');
  }catch(error){result.textContent=error.message||I18n.t('networkError');}finally{button.disabled=false;}
 };
 const jump=document.createElement('a');jump.href='#shopSettingsPanel';jump.className='button navy';jump.textContent=I18n.t('shopSettings');jump.id='shopSettingsJump';jump.hidden=true;document.querySelector('.staff-session').append(jump);
 const showJump=()=>{jump.textContent=I18n.t('shopSettings');jump.hidden=typeof staff==='undefined'||staff?.user?.role!=='admin';};
 document.addEventListener('languagechange',showJump);
 const renderOriginal=window.renderShopSettings;window.renderShopSettings=(...args)=>{renderOriginal(...args);showJump();};showJump();
});

/* Product copy stays separate from stock and selling prices. */
document.addEventListener('DOMContentLoaded',()=>{
 const form=$('productDetailsForm'),select=$('detailsProduct'),search=$('detailsSearch'),result=$('productDetailsResult');
 const fields=['brand','model','material','dimensions','unit','warranty','description_en','description_ms','specifications_en','specifications_ms'];
 let dirty=false,busy=false;
 function selected(){return data?.products.find(p=>String(p.id)===select.value)}
 function populate(){const p=selected();for(const key of fields)form.elements[key].value=p?.[key]||'';form.querySelector('button[type="submit"]').disabled=!p||busy;$('detailsPreview').hidden=!p;$('detailsPreview').href=p?'/?product='+p.id:'#';dirty=false;select.dataset.previous=select.value;}
 function renderPicker(){if(!data||busy)return;const matches=StaffInventory.filter(data.products,search.value,''),previous=select.value;select.innerHTML=matches.map(p=>`<option value="${p.id}">${esc(p.name)} · ${esc(p.sku)}</option>`).join('');select.value=matches.some(p=>String(p.id)===previous)?previous:String(matches[0]?.id||'');select.disabled=!matches.length;$('detailsMatches').textContent=t('photoSearchMatches',{count:matches.length});if(!dirty||previous!==select.value)populate();}
 function mayDiscard(){return !dirty||window.confirm(t('discardProductDetails'))}
 search.addEventListener('input',()=>{if(!mayDiscard()){search.value=search.dataset.previous||'';return}dirty=false;search.dataset.previous=search.value;renderPicker()});
 select.addEventListener('change',()=>{if(!mayDiscard()){select.value=select.dataset.previous||'';return}populate();select.dataset.previous=select.value;result.textContent=''});
 form.addEventListener('input',event=>{if(fields.includes(event.target.name))dirty=true});
 window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue=''}});
 window.renderProductDetailsPicker=renderPicker;renderPicker();
 form.addEventListener('submit',async event=>{event.preventDefault();if(busy||!selected())return;busy=true;search.disabled=true;select.disabled=true;const button=form.querySelector('button[type="submit"]');button.disabled=true;for(const field of fields)form.elements[field].disabled=true;result.textContent='';const payload={product:select.value};for(const field of fields)payload[field]=form.elements[field].value;
 try{await api('product-details',payload);dirty=false;await load();result.textContent=t('productDetailsSaved')}catch(error){result.textContent=errorText(error.message)}finally{busy=false;search.disabled=false;for(const field of fields)form.elements[field].disabled=false;renderPicker()}
 });
});

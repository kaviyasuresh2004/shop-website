window.StaffInventory={
 filter(products,query,category){return products.filter(p=>(!category||p.category===category)&&(p.name+' '+p.sku).toLowerCase().includes(query.toLowerCase().trim()));},
 cents(value){if(!/^\d+(?:\.\d{1,2})?$/.test(String(value)))throw Error('Enter a BND amount with at most two decimal places');const [whole,fraction='']=String(value).split('.');const cents=Number(whole)*100+Number(fraction.padEnd(2,'0'));if(!Number.isSafeInteger(cents)||cents>100000000)throw Error('Invalid selling price');return cents;},
 controls(matches,page){const select=$('inventoryCategory'),value=select.value;const labels=new Map(cats.map(([c,k])=>[c,t(k)]));select.innerHTML=`<option value="">${esc(t('allCategories'))}</option>`+[...new Set(data.products.map(p=>p.category))].sort().map(c=>`<option value="${esc(c)}">${esc(labels.get(c)||c)}</option>`).join('');select.value=value;$('inventoryCount').textContent=t('inventoryPageSummary',{start:matches.length?page*100+1:0,end:Math.min((page+1)*100,matches.length),count:matches.length});$('inventoryPrevious').disabled=page===0;$('inventoryNext').disabled=(page+1)*100>=matches.length;}
};
document.addEventListener('DOMContentLoaded',()=>{
 const form=$('sellingPriceForm'),select=$('sellingPriceProduct');
 function selected(){const p=data?.products.find(p=>String(p.id)===select.value);$('currentSellingPrice').textContent=p?money(p.price):'';form.elements.price_bnd.value=p?(p.price/100).toFixed(2):'';form.querySelector('button').disabled=!p;}
 select.addEventListener('change',selected);new MutationObserver(selected).observe(select,{childList:true});
 form.addEventListener('submit',async event=>{event.preventDefault();const button=form.querySelector('button');button.disabled=true;try{const product=select.value,price=StaffInventory.cents(form.elements.price_bnd.value);await api('product-price',{product,price});await load();selected();$('sellingPriceResult').textContent=t('saved');}catch(error){$('sellingPriceResult').textContent=errorText(error.message);}finally{button.disabled=false;}});
});

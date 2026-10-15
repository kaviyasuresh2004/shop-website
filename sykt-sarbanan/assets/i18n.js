const I18n = {
  language: 'en', dictionaries: {},
  t(key, vars = {}) { let text = this.dictionaries[this.language]?.[key] ?? this.dictionaries.en?.[key] ?? key; for (const [k,v] of Object.entries(vars)) text = text.replaceAll('{'+k+'}', String(v)); return text; },
  detect(language) { return String(language || '').toLowerCase().split('-')[0] === 'ms' ? 'ms' : 'en'; },
  storageGet(key) { try { return localStorage.getItem(key); } catch { return null; } },
  storageSet(key,value) { try { localStorage.setItem(key,value); return true; } catch { return false; } },
  apply() {
    document.documentElement.lang = this.language;
    document.querySelectorAll('[data-t]').forEach(el => el.textContent = this.t(el.dataset.t));
    document.querySelectorAll('[data-ph]').forEach(el => el.placeholder = this.t(el.dataset.ph));
    document.querySelectorAll('[data-aria]').forEach(el => el.setAttribute('aria-label', this.t(el.dataset.aria)));
    const selector=document.getElementById('language'); if(selector) selector.value=this.language;
    document.dispatchEvent(new CustomEvent('languagechange'));
  },
  set(language, persist=true) { this.language = language==='ms'?'ms':'en'; if(persist)this.storageSet('sykt-sarbanan-language',this.language); this.apply(); },
  error(message) { const key = this.dictionaries.en?.backendErrors?.[message]; return key ? this.t(key) : this.t('operationError'); },
  async init() {
    const pairs=await Promise.all(['en','ms'].map(async l=>[l,await (await fetch('/assets/'+l+'.json')).json()])); this.dictionaries=Object.fromEntries(pairs);
    const saved=this.storageGet('sykt-sarbanan-language');this.language=['en','ms'].includes(saved)?saved:this.detect(navigator.languages?.[0] || navigator.language);
    this.apply();document.getElementById('language')?.addEventListener('change',e=>this.set(e.target.value));
    const dialog=document.getElementById('languageDialog');
    if(dialog && !['en','ms'].includes(saved)) {
      let choice=this.language;
      const paint=()=>dialog.querySelectorAll('[data-lang]').forEach(b=>{b.classList.toggle('selected',b.dataset.lang===choice);b.setAttribute('aria-pressed',b.dataset.lang===choice)});
      dialog.querySelectorAll('[data-lang]').forEach(b=>b.addEventListener('click',()=>{choice=b.dataset.lang;this.set(choice,false);paint()}));
      document.getElementById('confirmLanguage').addEventListener('click',()=>{this.set(choice);dialog.close()});
      dialog.addEventListener('cancel',e=>e.preventDefault());paint();dialog.showModal();
    }
  }
};
window.I18n=I18n;window.siteReady=I18n.init();

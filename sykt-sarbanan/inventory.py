"""Authenticated catalogue imports; source inventory never enters public assets."""
import hashlib,json,sqlite3

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS inventory_source(product INTEGER PRIMARY KEY REFERENCES products ON DELETE CASCADE,source_name TEXT,source_quantity TEXT,unit TEXT,hold INTEGER NOT NULL DEFAULT 0)')
 c.execute('CREATE TABLE IF NOT EXISTS catalogue_imports(digest TEXT PRIMARY KEY,result TEXT)')

def available(c,pid):
 return bool(c.execute('SELECT 1 FROM products p JOIN stock s ON s.id=p.id LEFT JOIN inventory_source i ON i.product=p.id WHERE p.id=? AND p.price>0 AND s.company=1 AND s.qty>0 AND COALESCE(i.hold,0)=0',(pid,)).fetchone())

def import_catalogue(domain,user,d):
 if user['role']!='admin':raise ValueError('Administrator required')
 if d.get('source_company')!='SYKT PG. SARBANUN SDN BHD':raise ValueError('Wrong source company')
 if d.get('shop')!=domain.CONFIG['slug'] or d.get('location')!='Main Location':raise ValueError('Wrong shop or location')
 rows=d.get('items');digest=d.get('source_sha256','')
 if not isinstance(rows,list) or not 1<=len(rows)<=20000 or len(digest)!=64:raise ValueError('Invalid import')
 # Include payload in the receipt so a changed payload cannot reuse a receipt.
 receipt=hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()
 with domain.LOCK,domain.connect() as c:
  old=c.execute('SELECT result FROM catalogue_imports WHERE digest=?',(receipt,)).fetchone()
  if old:return json.loads(old['result'])
  backups=domain.DB.parent/'backups';backups.mkdir(exist_ok=True)
  backup=sqlite3.connect(backups/('before-catalogue-'+receipt+'.db'))
  try:c.backup(backup)
  finally:backup.close()
  c.execute('BEGIN IMMEDIATE')
  seen=set();visible=0
  for row in rows:
   name=row['name'];sku=row['sku'];source=row['source_name'];price=domain.integer(row['price_cents']);qty=domain.integer(row['quantity']);hold=row['hold'];raw=row['source_quantity'];unit=row['unit']
   expected='SYKT-TALLY-'+hashlib.sha256(source.encode()).hexdigest()[:16].upper()
   if sku!=expected or sku in seen or not 1<=len(name)<=200 or len(source)>2000 or not 0<=price<=100000000 or not 0<=qty<=1000000000 or type(hold)!=bool or not isinstance(raw,str) or len(raw)>100 or not isinstance(unit,str) or len(unit)>80:raise ValueError('Invalid product row')
   seen.add(sku)
   c.execute("INSERT INTO products(sku,name,category,price) VALUES (?,?,'Uncategorised',?) ON CONFLICT(sku) DO UPDATE SET name=excluded.name,price=excluded.price",(sku,name,price))
   pid=c.execute('SELECT id FROM products WHERE sku=?',(sku,)).fetchone()['id']
   c.execute('INSERT INTO stock VALUES (1,?,?) ON CONFLICT(company,id) DO UPDATE SET qty=excluded.qty',(pid,qty))
   c.execute('INSERT OR REPLACE INTO inventory_source VALUES (?,?,?,?,?)',(pid,source,raw,unit,int(hold)))
   visible+=int(qty>0 and price>0 and not hold)
  # Retire only untouched demonstration SKUs; retain historical records.
  for sku in ('DRILL-001','PAINT-001','CEMENT-001','PIPE-001','HAMMER-001','WIRE-001'):
   c.execute('UPDATE stock SET qty=0 WHERE id IN (SELECT id FROM products WHERE sku=?)',(sku,))
  result={'ok':True,'imported':len(rows),'visible':visible,'hidden':len(rows)-visible}
  c.execute('INSERT INTO catalogue_imports VALUES (?,?)',(receipt,json.dumps(result)))
  domain.audit(c,user['name'],'catalogue imported',{'source_sha256':digest,'location':'Main Location',**result})
  return result

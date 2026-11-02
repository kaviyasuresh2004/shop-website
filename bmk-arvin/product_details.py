"""Staff-maintained product copy, isolated from imported stock and prices."""
import json

FIELDS={'brand':160,'model':160,'material':300,'dimensions':300,'unit':80,'warranty':1000,'description_en':12000,'description_ms':12000,'specifications_en':12000,'specifications_ms':12000}

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS product_details(product INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,content TEXT NOT NULL)')

def load_all(c):
 return {r['product']:dict(json.loads(r['content']),details_saved=True) for r in c.execute('SELECT * FROM product_details')}

def save(domain,user,d):
 if user['role'] not in ('admin','worker'):raise ValueError('Staff access required')
 product=domain.integer(d['product']);content={}
 for field,limit in FIELDS.items():
  value=d.get(field,'')
  if not isinstance(value,str) or len(value)>limit:raise ValueError('Invalid product details: '+field)
  content[field]=value.strip()
 with domain.LOCK,domain.connect() as c:
  if not c.execute('SELECT 1 FROM products WHERE id=?',(product,)).fetchone():raise ValueError('Unknown product')
  c.execute('INSERT INTO product_details(product,content) VALUES (?,?) ON CONFLICT(product) DO UPDATE SET content=excluded.content',(product,json.dumps(content)))
  domain.audit(c,user['name'],'product details updated',{'product':product,'fields':list(content)})
 return {'ok':True}

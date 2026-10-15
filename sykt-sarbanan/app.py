import mimetypes
from datetime import datetime, timezone
from urllib.parse import urlsplit, unquote
import csv, hashlib, hmac, io, json, os, secrets, sqlite3, threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).parent
CONFIG=json.loads((ROOT/'shop.json').read_text())
DB=Path(os.environ.get('DATA_DIR',str(ROOT/'data')))/'shop.db'
COOKIE='session_'+CONFIG['slug']
LOCK=threading.RLock()
SESSIONS={}
@contextmanager
def connect():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON')
 try:
  with c: yield c
 finally: c.close()
def init():
 DB.parent.mkdir(parents=True,exist_ok=True)
 with connect() as c:
  c.executescript("""
  CREATE TABLE IF NOT EXISTS order_details(sale INTEGER PRIMARY KEY REFERENCES sales,channel TEXT,address TEXT,phone TEXT,zone TEXT,status TEXT);
  CREATE TABLE IF NOT EXISTS order_requests(key TEXT PRIMARY KEY,payload TEXT NOT NULL,result TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS companies(id INTEGER PRIMARY KEY,name TEXT);
  CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,sku TEXT UNIQUE,name TEXT,category TEXT,price INTEGER CHECK(price>=0));
  CREATE TABLE IF NOT EXISTS stock(company INTEGER REFERENCES companies,id INTEGER REFERENCES products,qty INTEGER CHECK(qty>=0),PRIMARY KEY(company,id));
  CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY,company INTEGER REFERENCES companies,customer TEXT,items TEXT,total INTEGER,delivery INTEGER,status TEXT DEFAULT 'completed',created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT,action TEXT,detail TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS promotions(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,company INTEGER REFERENCES companies,product INTEGER REFERENCES products,category TEXT,title_en TEXT,title_ms TEXT,description_en TEXT,description_ms TEXT,price INTEGER,start TEXT,end TEXT,active INTEGER DEFAULT 1);
  CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY,salt TEXT,password TEXT,role TEXT,company INTEGER REFERENCES companies);
  CREATE TRIGGER IF NOT EXISTS sales_no_delete BEFORE DELETE ON sales BEGIN SELECT RAISE(ABORT,'Sales cannot be deleted'); END;
  CREATE TRIGGER IF NOT EXISTS sales_no_update BEFORE UPDATE ON sales BEGIN SELECT RAISE(ABORT,'Completed sales are immutable'); END;
  CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'Audit cannot be deleted'); END;
  CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'Audit is immutable'); END;
  """)
  if not c.execute('SELECT 1 FROM companies').fetchone():
   c.executemany('INSERT INTO companies VALUES (?,?)',[(1,CONFIG['name'])])
   c.executemany('INSERT INTO products VALUES (?,?,?,?,?)',[(1,'DRILL-001','Cordless drill kit','Power tools',8900),(2,'PAINT-001','Interior paint · 5 litres','Paint',3200),(3,'CEMENT-001','Portland cement · 50 kg','Building materials',850),(4,'PIPE-001','PVC pipe · 3 metres','Plumbing',650),(5,'HAMMER-001','Claw hammer','Hand tools',1200),(6,'WIRE-001','Electrical cable · 10 metres','Electrical',1800)])
   c.executemany('INSERT INTO stock VALUES (?,?,?)',[(company,p,30 if company==1 else 20) for company in (1,) for p in range(1,7)])
   audit(c,'system','setup','Sample catalogue and stock created; replace before real use')
  companies=c.execute('SELECT id,name FROM companies').fetchall()
  if len(companies)!=1 or companies[0]['id']!=1 or companies[0]['name']!=CONFIG['name']: raise ValueError('Database identity mismatch: use only this shop database')
def audit(c,actor,action,detail): c.execute('INSERT INTO audit(actor,action,detail) VALUES (?,?,?)',(actor,action,json.dumps(detail)))
def password_hash(p,s): return hashlib.pbkdf2_hmac('sha256',p.encode(),s.encode(),200000).hex()
def integer(v):
 if isinstance(v,bool) or str(v).strip()!=str(int(v)): raise ValueError('Use whole numbers')
 return int(v)
def parse_time(value):
 try:
  dt=datetime.fromisoformat(value.replace('Z','+00:00'))
  if dt.tzinfo is None: raise ValueError()
  return dt.astimezone(timezone.utc)
 except (ValueError, AttributeError): raise ValueError('Use valid promotion dates with timezone')
def promotion_valid(row):
 try: return row['active'] and parse_time(row['start'])<=datetime.now(timezone.utc)<parse_time(row['end'])
 except ValueError: return False
def effective_price(c,product,company):
 prices=[product['price']]
 for r in c.execute("SELECT * FROM promotions WHERE active=1 AND kind='discount' AND product=? AND company=?",(product['id'],company)):
  if promotion_valid(r) and 0<=r['price']<product['price']: prices.append(r['price'])
 return min(prices)
def operation(user,kind,d,*,customer_id=None):
 if user['role']=='customer' and kind!='order': raise ValueError('Not authorized')
 with LOCK,connect() as c:
  c.execute('BEGIN IMMEDIATE')
  company=integer(d.get('company',1))
  if company!=1: raise ValueError('Unknown company')
  if user['role']!='admin' and company!=user['company']: raise ValueError('Worker may only manage assigned company')
  if kind=='adjust':
   product=integer(d['product']); delta=integer(d['delta']); reason=d.get('reason','').strip()
   if not reason: raise ValueError('Adjustment reason required')
   if c.execute('UPDATE stock SET qty=qty+? WHERE company=? AND id=? AND qty+?>=0',(delta,company,product,delta)).rowcount!=1: raise ValueError('Invalid product or insufficient stock')
   audit(c,user['name'],'stock adjustment',d)
  elif kind in ('sale','order'):
   request_key=d.get('request_id','') if kind=='order' else ''
   fingerprint=json.dumps({k:v for k,v in d.items() if k!='request_id'},sort_keys=True)
   if request_key:
    if not isinstance(request_key,str) or not 16<=len(request_key)<=128: raise ValueError('Invalid order request ID')
    previous=c.execute('SELECT * FROM order_requests WHERE key=?',(request_key,)).fetchone()
    if previous:
     if previous['payload']!=fingerprint: raise ValueError('Order request ID already used')
     return json.loads(previous['result'])
   items=d['items']; customer=d.get('customer','').strip(); zone=d.get('zone','pickup')
   if not customer or not items: raise ValueError('Customer and items required')
   if not isinstance(items,list) or len(items)>100 or len(customer)>200 or len(d.get('phone',''))>80 or len(d.get('address',''))>1000: raise ValueError('Invalid order details')
   fees={'pickup':0,'Brunei-Muara':500,'Tutong':1000,'Belait':1500,'Temburong':2000}
   if zone not in fees: raise ValueError('Unknown delivery region')
   total=fees[zone]; combined={}
   for item in items:
    p=integer(item['product']); q=integer(item['qty'])
    if q<=0: raise ValueError('Quantity must be positive')
    combined[p]=combined.get(p,0)+q
   lines=[]
   for p,q in combined.items():
    row=c.execute('SELECT * FROM products WHERE id=?',(p,)).fetchone()
    if not row: raise ValueError('Unknown product')
    if c.execute('UPDATE stock SET qty=qty-? WHERE company=? AND id=? AND qty>=?',(q,company,p,q)).rowcount!=1: raise ValueError('Insufficient stock')
    unit_price=effective_price(c,row,company); total+=unit_price*q; lines.append({'product':p,'sku':row['sku'],'qty':q,'unit_price':unit_price})
   sale=c.execute('INSERT INTO sales(company,customer,items,total,delivery) VALUES (?,?,?,?,?)',(company,customer,json.dumps(lines),total,fees[zone])).lastrowid
   c.execute('INSERT INTO order_details(sale,channel,address,phone,zone,status) VALUES (?,?,?,?,?,?)',(sale,'online' if kind=='order' else 'shop',d.get('address','').strip(),d.get('phone','').strip(),zone,'pending' if kind=='order' else 'completed'))
   if customer_id is not None: c.execute('INSERT INTO order_owners VALUES (?,?)',(sale,customer_id))
   result={'sale':sale,'total':total}
   if request_key: c.execute('INSERT INTO order_requests VALUES (?,?,?)',(request_key,fingerprint,json.dumps(result)))
   audit(c,user['name'],'order received' if kind=='order' else 'completed sale',{'sale':sale,'company':company,'zone':zone}); return result
  elif kind=='product':
   sku=d['sku'].strip(); name=d['name'].strip(); category=d['category'].strip(); price=integer(d['price'])
   if not sku or not name or not category or price<0 or price>100000000 or len(sku)>100 or len(name)>200 or len(category)>100: raise ValueError('Product fields and nonnegative price required')
   if d.get('id'):
    if c.execute('UPDATE products SET sku=?,name=?,category=?,price=? WHERE id=?',(sku,name,category,price,integer(d['id']))).rowcount!=1: raise ValueError('Unknown product')
   else:
    pid=c.execute('INSERT INTO products(sku,name,category,price) VALUES (?,?,?,?)',(sku,name,category,price)).lastrowid
    c.execute('INSERT INTO stock VALUES (1,?,0)',(pid,))
   audit(c,user['name'],'product saved',{'sku':sku})
  elif kind=='delete_product':
   if user['role']!='admin': raise ValueError('Only admin can delete products')
   pid=integer(d['product'])
   c.execute('DELETE FROM promotions WHERE product=?',(pid,)); c.execute('DELETE FROM stock WHERE id=?',(pid,)); c.execute('DELETE FROM products WHERE id=?',(pid,))
   audit(c,user['name'],'product deleted',{'product':pid})
  elif kind=='order_status':
   if d['status'] not in ('pending','processing','ready','delivered','completed'): raise ValueError('Invalid order status')
   if c.execute('UPDATE order_details SET status=? WHERE sale=?',(d['status'],integer(d['sale']))).rowcount!=1: raise ValueError('Unknown order')
   audit(c,user['name'],'order status',d)
  elif kind=='import':
   if user['role']!='admin': raise ValueError('Only admin can import stock')
   reason=d.get('reason','').strip()
   if not reason: raise ValueError('Import reason required')
   reader=csv.DictReader(io.StringIO(d['csv'].lstrip('\ufeff')))
   if not reader.fieldnames or not {'SKU','Quantity'}<=set(reader.fieldnames): raise ValueError('CSV columns must include SKU,Quantity')
   seen=set(); count=0
   for row in reader:
    sku=row['SKU'].strip(); qty=integer(row['Quantity'])
    if sku in seen or qty<0: raise ValueError('Duplicate SKU or negative quantity')
    seen.add(sku); product=c.execute('SELECT id FROM products WHERE sku=?',(sku,)).fetchone()
    if not product: raise ValueError('Unknown SKU: '+sku)
    old=c.execute('SELECT qty FROM stock WHERE company=? AND id=?',(company,product['id'])).fetchone()['qty']
    c.execute('UPDATE stock SET qty=? WHERE company=? AND id=?',(qty,company,product['id']))
    audit(c,user['name'],'stock import row',{'company':company,'sku':sku,'before':old,'after':qty,'reason':reason}); count+=1
   if not count: raise ValueError('No import rows')
   return {'imported':count}
  elif kind=='promotion':
   if d.get('id'):
    pid=integer(d['id'])
    if c.execute('UPDATE promotions SET active=0 WHERE id=?',(pid,)).rowcount!=1: raise ValueError('Unknown promotion')
    audit(c,user['name'],'promotion disabled',{'id':pid}); return {'ok':True}
   pk=d.get('kind'); title=d.get('title_en','').strip(); title_ms=d.get('title_ms','').strip()
   if pk not in ('discount','offer','category','banner') or not title or not title_ms: raise ValueError('Promotion type and both titles required')
   begin=parse_time(d.get('start','')); finish=parse_time(d.get('end',''))
   if begin>=finish: raise ValueError('Promotion end must be after start')
   product=None; price=None; category=d.get('category','').strip()
   if pk=='discount':
    product=integer(d['product']); price=integer(d['price']); row=c.execute('SELECT price FROM products WHERE id=?',(product,)).fetchone()
    if not row or price<0 or price>=row['price']: raise ValueError('Discount price must be below original price')
   if pk=='category' and category not in ('Power tools','Hand tools','Building materials','Electrical','Plumbing','Paint','AC & Refrigeration','Fasteners','Safety Equipment'): raise ValueError('Unknown category')
   c.execute('INSERT INTO promotions(kind,company,product,category,title_en,title_ms,description_en,description_ms,price,start,end) VALUES (?,?,?,?,?,?,?,?,?,?,?)',(pk,company,product,category,title,title_ms,d.get('description_en','').strip(),d.get('description_ms','').strip(),price,begin.isoformat(),finish.isoformat()))
   audit(c,user['name'],'promotion created',{'kind':pk,'company':company,'title':title})
  elif kind=='user':
   if user['role']!='admin': raise ValueError('Only admin can create workers')
   name=d['name'].strip(); p=d['password']
   if not name or len(name)>100 or not 12<=len(p)<=256: raise ValueError('Username and password of at least 12 characters required')
   if c.execute('SELECT 1 FROM users WHERE lower(name)=lower(?)',(name,)).fetchone(): raise ValueError('Username already exists')
   salt=secrets.token_hex(16); c.execute('INSERT INTO users VALUES (?,?,?,?,?)',(name,salt,password_hash(p,salt),'worker',company)); audit(c,user['name'],'worker created',{'name':name,'company':company})
  elif kind=='manage_user':
   if user['role']!='admin': raise ValueError('Only admin can manage accounts')
   name=d['name'].strip()
   if name==user['name']: raise ValueError('Cannot remove your own account')
   if d.get('password'):
    if not 12<=len(d['password'])<=256: raise ValueError('Password must be at least 12 characters')
    salt=secrets.token_hex(16)
    if c.execute('UPDATE users SET salt=?,password=? WHERE name=?',(salt,password_hash(d['password'],salt),name)).rowcount!=1: raise ValueError('Unknown account')
   else:
    if c.execute('DELETE FROM users WHERE name=?',(name,)).rowcount!=1: raise ValueError('Unknown account')
   for token in list(SESSIONS):
    if SESSIONS[token]['name']==name: del SESSIONS[token]
   audit(c,user['name'],'account updated',{'name':name})
  else: raise ValueError('Unknown operation')
 return {'ok':True}
class Handler(BaseHTTPRequestHandler):
 def respond(self,data,status=200):
  raw=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(raw)
 def user(self):
  cookie=self.headers.get('Cookie',''); token=next((x.strip()[len(COOKIE)+1:] for x in cookie.split(';') if x.strip().startswith(COOKIE+'=')),None)
  return SESSIONS.get(token)
 def do_GET(self):
  path=unquote(urlsplit(self.path).path)
  if path in ('/', '/staff') or path.startswith('/assets/'):
   target=ROOT/('index.html' if path=='/' else 'staff.html' if path=='/staff' else path.lstrip('/'))
   resolved=target.resolve()
   if path.startswith('/assets/') and not resolved.is_relative_to((ROOT/'assets').resolve()): return self.respond({'error':'Not found'},404)
   if not resolved.is_file(): return self.respond({'error':'Not found'},404)
   raw=resolved.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(str(resolved))[0] or 'application/octet-stream'); self.send_header('Cache-Control','no-cache'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw); return
  with connect() as c:
   if path=='/api/catalog': return self.respond({'companies':[dict(r) for r in c.execute('SELECT * FROM companies')],'products':[dict(r) for r in c.execute('SELECT * FROM products')],'stock':[dict(r) for r in c.execute('SELECT * FROM stock')],'promotions':[dict(r) for r in c.execute('SELECT * FROM promotions WHERE active=1') if promotion_valid(r)],'setup':not bool(c.execute('SELECT 1 FROM users').fetchone())})
   u=self.user()
   if not u: return self.respond({'error':'Sign in required'},401)
   if path=='/api/staff':
    sales=c.execute('SELECT * FROM sales ORDER BY id DESC') if u['role']=='admin' else c.execute('SELECT * FROM sales WHERE company=? ORDER BY id DESC',(u['company'],))
    return self.respond({'user':u,'sales':[dict(r) for r in sales],'audit':[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')] if u['role']=='admin' else [],'orders':[dict(r) for r in c.execute('SELECT * FROM order_details ORDER BY sale DESC')],'report':dict(c.execute('SELECT COUNT(*) AS sales,COALESCE(SUM(total),0) AS total FROM sales').fetchone()),'promotions':[dict(r) for r in c.execute('SELECT * FROM promotions ORDER BY id DESC')]})
  self.respond({'error':'Not found'},404)
 def do_POST(self):
  try:
   origin=self.headers.get('Origin')
   if origin and origin!='http://'+self.headers.get('Host',''): return self.respond({'error':'Invalid origin'},403)
   size=int(self.headers.get('Content-Length',0))
   if size>1000000: raise ValueError('Request too large')
   d=json.loads(self.rfile.read(size)); kind=self.path.removeprefix('/api/')
   if kind in ('setup','login'):
    with LOCK,connect() as c:
     if kind=='setup':
      if c.execute('SELECT 1 FROM users').fetchone(): raise ValueError('Setup already completed')
      p=d['password']; name=d['name'].strip(); d['name']=name
      if not name or len(p)<12: raise ValueError('Use a username and password of at least 12 characters')
      if c.execute('SELECT 1 FROM users WHERE lower(name)=lower(?)',(name,)).fetchone(): raise ValueError('Username already exists')
      salt=secrets.token_hex(16); c.execute('INSERT INTO users VALUES (?,?,?,?,?)',(name,salt,password_hash(p,salt),'admin',1)); audit(c,name,'admin setup',{})
     row=c.execute('SELECT * FROM users WHERE name=?',(d['name'],)).fetchone()
     if not row or not hmac.compare_digest(row['password'],password_hash(d['password'],row['salt'])): return self.respond({'error':'Invalid credentials'},401)
     token=secrets.token_urlsafe(32); SESSIONS[token]={'name':row['name'],'role':row['role'],'company':row['company']}
     self.send_response(200); self.send_header('Set-Cookie',COOKIE+'='+token+'; HttpOnly; SameSite=Strict; Path=/'); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b'{"ok":true}'); return
   if kind=='order':
    if not d.get('phone','').strip() or (d.get('zone','pickup')!='pickup' and not d.get('address','').strip()): raise ValueError('Phone and delivery address required')
    return self.respond(operation({'name':'customer','role':'customer','company':1},'order',d))
   u=self.user()
   if not u: return self.respond({'error':'Sign in required'},401)
   if kind=='logout':
    for token in list(SESSIONS):
     if SESSIONS[token] is u: del SESSIONS[token]
    return self.respond({'ok':True})
   self.respond(operation(u,kind,d))
  except (ValueError,KeyError,TypeError,sqlite3.IntegrityError) as e: self.respond({'error':str(e)},400)
if __name__=='__main__':
 from server import serve
 serve()

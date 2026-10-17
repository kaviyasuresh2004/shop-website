"""Customer accounts and owner-authorized staff recovery; no shared shop data."""
import hashlib, hmac, json, os, re, secrets, sqlite3, time
from flask import request, jsonify

def install(server):
 web, domain = server.web, server.domain
 cookie = 'customer_' + domain.CONFIG['slug']

 def initialize():
  with domain.connect() as c:
   c.executescript('''
   CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY,email TEXT NOT NULL UNIQUE COLLATE NOCASE,name TEXT NOT NULL,phone TEXT NOT NULL,address TEXT NOT NULL,salt TEXT NOT NULL,password TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS customer_sessions(token TEXT PRIMARY KEY,customer INTEGER NOT NULL REFERENCES customers(id),expires INTEGER NOT NULL);
   CREATE TABLE IF NOT EXISTS order_owners(sale INTEGER PRIMARY KEY REFERENCES sales(id),customer INTEGER NOT NULL REFERENCES customers(id));
   CREATE TABLE IF NOT EXISTS used_recovery_tokens(digest TEXT PRIMARY KEY);
   ''')

 def current():
  token = request.cookies.get(cookie, '')
  with domain.connect() as c:
   return c.execute('SELECT c.* FROM customers c JOIN customer_sessions s ON c.id=s.customer WHERE s.token=? AND s.expires>?', (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()

 def session(c, customer):
  token = secrets.token_urlsafe(32)
  c.execute('DELETE FROM customer_sessions WHERE expires<=?', (int(time.time()),))
  c.execute('INSERT INTO customer_sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), customer, int(time.time())+server.SESSION_TTL))
  response = jsonify(ok=True)
  response.set_cookie(cookie, token, max_age=server.SESSION_TTL, httponly=True, secure=server.PRODUCTION, samesite='Strict', path='/')
  return response

 @web.get('/api/customer/me')
 def me():
  customer = current()
  if not customer: return jsonify(error='Customer sign in required'), 401
  with domain.connect() as c:
   orders = [dict(r) for r in c.execute("SELECT s.id,s.items,s.total,s.delivery,s.created,d.status,d.zone,d.address,COALESCE(p.method,'manual') AS payment_method,COALESCE(p.status,'unrecorded') AS payment_status FROM sales s JOIN order_owners o ON o.sale=s.id JOIN order_details d ON d.sale=s.id LEFT JOIN order_payments p ON p.sale=s.id WHERE o.customer=? ORDER BY s.id DESC LIMIT 200", (customer['id'],))]
   orders=domain.delivery.adjust(c,orders)
  for order in orders: order['items'] = json.loads(order['items'])
  return jsonify(customer={k:customer[k] for k in ('id','email','name','phone','address')}, orders=orders)

 @web.post('/api/customer/<kind>')
 def customer_action(kind):
  d = request.get_json(silent=True)
  if not isinstance(d, dict): return jsonify(error='JSON object required'), 400
  try:
   if kind in ('register','login'):
    if server.rate_limited('customer-authentication',20): return jsonify(error='Too many attempts. Try again later.'),429
    email = d['email'].strip().lower(); password = d['password']
    if not isinstance(password,str) or len(password)>256 or len(email)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise ValueError()
    with domain.LOCK, domain.connect() as c:
     if kind=='register':
      name=d['name'].strip(); phone=d.get('phone','').strip(); address=d.get('address','').strip()
      if not name or len(name)>200 or len(phone)>80 or len(address)>1000 or len(password)<8: raise ValueError()
      salt=secrets.token_hex(16)
      c.execute('INSERT INTO customers(email,name,phone,address,salt,password) VALUES (?,?,?,?,?,?)',(email,name,phone,address,salt,domain.password_hash(password,salt)))
     row=c.execute('SELECT * FROM customers WHERE email=?',(email,)).fetchone()
     if not row or not hmac.compare_digest(row['password'],domain.password_hash(password,row['salt'])): return jsonify(error='Invalid credentials'),401
     return session(c,row['id'])
   customer=current()
   if not customer: return jsonify(error='Customer sign in required'),401
   if kind=='profile':
    name=d['name'].strip();phone=d.get('phone','').strip();address=d.get('address','').strip()
    if not name or len(name)>200 or len(phone)>80 or len(address)>1000:raise ValueError()
    with domain.connect() as c:
     if phone!=customer['phone']:
      c.execute('DELETE FROM phone_verified WHERE customer=?',(customer['id'],));c.execute('DELETE FROM phone_challenges WHERE customer=?',(customer['id'],))
     c.execute('UPDATE customers SET name=?,phone=?,address=? WHERE id=?',(name,phone,address,customer['id']))
    return jsonify(ok=True)
   if kind=='logout':
    with domain.connect() as c: c.execute('DELETE FROM customer_sessions WHERE token=?',(hashlib.sha256(request.cookies.get(cookie,'').encode()).hexdigest(),))
    response=jsonify(ok=True); response.delete_cookie(cookie,path='/'); return response
   if kind=='password':
    old=d['current_password']; new=d['password']
    if not isinstance(old,str) or not isinstance(new,str) or not 8<=len(new)<=256: raise ValueError()
    if not hmac.compare_digest(customer['password'],domain.password_hash(old,customer['salt'])): return jsonify(error='Invalid credentials'),401
    with domain.LOCK,domain.connect() as c:
     salt=secrets.token_hex(16)
     c.execute('UPDATE customers SET salt=?,password=? WHERE id=?',(salt,domain.password_hash(new,salt),customer['id']))
     c.execute('DELETE FROM customer_sessions WHERE customer=?',(customer['id'],))
     return session(c,customer['id'])
   return jsonify(error='Unknown operation'),404
  except (ValueError,KeyError,TypeError,AttributeError,sqlite3.IntegrityError):
   return jsonify(error='Check account details or use a different email address.'),400

 @web.post('/api/recover-admin')
 def recover_admin():
  if server.rate_limited('owner-recovery',5): return jsonify(error='Too many attempts. Try again later.'),429
  d=request.get_json(silent=True)
  if not isinstance(d,dict): return jsonify(error='JSON object required'),400
  expected=os.environ.get('ADMIN_RECOVERY_TOKEN','')
  supplied=d.get('recovery_token','')
  if len(expected)<32 or not isinstance(supplied,str) or not hmac.compare_digest(supplied.encode(),expected.encode()): return jsonify(error='Recovery token required'),403
  try:
   name=d['name'].strip(); password=d['password']
   if not isinstance(password,str) or not 8<=len(password)<=256: raise ValueError()
   with domain.LOCK,domain.connect() as c:
    c.execute('BEGIN IMMEDIATE')
    digest=hashlib.sha256(expected.encode()).hexdigest()
    if c.execute('SELECT 1 FROM used_recovery_tokens WHERE digest=?',(digest,)).fetchone(): return jsonify(error='Recovery token required'),403
    rows=c.execute("SELECT * FROM users WHERE lower(name)=lower(?) AND role='admin'",(name,)).fetchall()
    if len(rows)!=1: return jsonify(error='Invalid credentials'),401
    name=rows[0]['name']; salt=secrets.token_hex(16)
    c.execute('UPDATE users SET salt=?,password=? WHERE name=?',(salt,domain.password_hash(password,salt),name))
    c.execute('DELETE FROM web_sessions WHERE username=?',(name,))
    c.execute('INSERT INTO used_recovery_tokens VALUES (?)',(digest,))
    domain.audit(c,name,'administrator recovery',{'sessions_revoked':True})
   return jsonify(ok=True)
  except (ValueError,KeyError,TypeError,AttributeError): return jsonify(error='Invalid request. Check the supplied fields and available stock.'),400

 return initialize, current

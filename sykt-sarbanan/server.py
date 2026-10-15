"""Railway entrypoint. One service/process and persistent volume per shop."""
import hashlib,hmac,json,os,secrets,sqlite3,time
from collections import defaultdict,deque
from urllib.parse import urlsplit
from flask import Flask,request,jsonify,send_from_directory
import app as domain

web=Flask(__name__,static_folder=None)
web.config['MAX_CONTENT_LENGTH']=1_000_000
PRODUCTION=os.environ.get('APP_ENV')=='production'
PREVIEW=os.environ.get('SHOP_MODE','preview')!='live'
PUBLIC_URL=os.environ.get('PUBLIC_URL','').rstrip('/')
DOMAIN=os.environ.get('RAILWAY_PUBLIC_DOMAIN','')
LIMITS=defaultdict(deque)
SESSION_TTL=8*60*60

def initialize():
 if PRODUCTION and not os.environ.get('DATA_DIR'): raise RuntimeError('DATA_DIR must point to this service persistent volume')
 if os.environ.get('RAILWAY_ENVIRONMENT_ID') and os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')!=os.environ.get('DATA_DIR'): raise RuntimeError('Attach a separate Railway volume matching DATA_DIR before starting')
 domain.init()
 initialize_accounts()
 with domain.connect() as c:
  c.execute('CREATE TABLE IF NOT EXISTS web_sessions(token TEXT PRIMARY KEY,username TEXT REFERENCES users(name) ON DELETE CASCADE,expires INTEGER)')

def public_origin():
 if PUBLIC_URL: return PUBLIC_URL
 if DOMAIN: return 'https://'+DOMAIN
 return request.host_url.rstrip('/') if not PRODUCTION else ''

def signed_in():
 token=request.cookies.get(domain.COOKIE,'')
 if not token: return None
 digest=hashlib.sha256(token.encode()).hexdigest()
 with domain.connect() as c:
  row=c.execute('SELECT u.name,u.role,u.company FROM web_sessions s JOIN users u ON u.name=s.username WHERE s.token=? AND s.expires>?',(digest,int(time.time()))).fetchone()
 return dict(row) if row else None

def rate_limited(kind,limit):
 # Trust Railway's edge only in production; do not accept arbitrary proxy headers locally.
 ip=(request.headers.get('X-Forwarded-For','').split(',')[-1].strip() or request.remote_addr) if PRODUCTION else request.remote_addr
 now=time.monotonic(); key=(kind,ip)
 with domain.LOCK:
  if len(LIMITS)>10000:
   for old in list(LIMITS):
    if not LIMITS[old] or LIMITS[old][-1]<now-600: del LIMITS[old]
  hits=LIMITS[key]
  while hits and hits[0]<now-600: hits.popleft()
  if len(hits)>=limit: return True
  hits.append(now)
 return False

@web.before_request
def protect_requests():
 if request.method=='POST':
  origin=request.headers.get('Origin')
  if origin and origin!=public_origin(): return jsonify(error='Invalid origin'),403
  if request.headers.get('Sec-Fetch-Site')=='cross-site': return jsonify(error='Invalid origin'),403
  if not request.is_json: return jsonify(error='JSON request required'),415

@web.after_request
def headers(response):
 response.headers['X-Content-Type-Options']='nosniff'
 response.headers['X-Frame-Options']='DENY'
 response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
 response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
 if request.path.startswith('/api/') or request.path=='/staff': response.headers['Cache-Control']='no-store'
 if PRODUCTION: response.headers['Strict-Transport-Security']='max-age=31536000'
 return response

@web.get('/')
def home(): return send_from_directory(domain.ROOT,'index.html')
@web.get('/staff')
def staff_page(): return send_from_directory(domain.ROOT,'staff.html')
@web.get('/assets/<path:filename>')
def assets(filename): return send_from_directory(domain.ROOT/'assets',filename)
@web.get('/healthz')
def health():
 with domain.connect() as c: c.execute('SELECT 1').fetchone()
 return jsonify(status='ok',shop=domain.CONFIG['slug'])

@web.get('/api/catalog')
def catalog():
 with domain.connect() as c:
  return jsonify(companies=[dict(r) for r in c.execute('SELECT * FROM companies')],products=[dict(r) for r in c.execute('SELECT * FROM products')],stock=[dict(r) for r in c.execute('SELECT * FROM stock')],promotions=[dict(r) for r in c.execute('SELECT * FROM promotions WHERE active=1') if domain.promotion_valid(r)],setup=not bool(c.execute('SELECT 1 FROM users').fetchone()),setupProtected=PRODUCTION,preview=PREVIEW)

@web.get('/api/staff')
def staff():
 user=signed_in()
 if not user: return jsonify(error='Sign in required'),401
 with domain.connect() as c:
  report=dict(c.execute("SELECT COUNT(*) AS sales,COALESCE(SUM(s.total),0) AS total FROM sales s LEFT JOIN order_details d ON d.sale=s.id WHERE d.sale IS NULL OR d.status IN ('delivered','completed')").fetchone())
  report.update(dict(c.execute("SELECT COUNT(*) AS pending_orders,COALESCE(SUM(s.total),0) AS pending_total FROM sales s JOIN order_details d ON d.sale=s.id WHERE d.channel='online' AND d.status NOT IN ('delivered','completed')").fetchone()))
  accounts=[dict(r) for r in c.execute('SELECT name,role,company FROM users ORDER BY role,name')] if user['role']=='admin' else []
  return jsonify(user=user,accounts=accounts,sales=[dict(r) for r in c.execute('SELECT * FROM sales ORDER BY id DESC')],orders=[dict(r) for r in c.execute('SELECT * FROM order_details ORDER BY sale DESC')],audit=[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')] if user['role']=='admin' else [],promotions=[dict(r) for r in c.execute('SELECT * FROM promotions ORDER BY id DESC')],report=report)

@web.post('/api/<kind>')
def action(kind):
 d=request.get_json(silent=True)
 if not isinstance(d,dict): return jsonify(error='JSON object required'),400
 try:
  if kind in ('setup','login'):
   if rate_limited('authentication',20): return jsonify(error='Too many attempts. Try again later.'),429
   name=d['name'].strip();password=d['password']
   if not isinstance(password,str) or len(password)>256: raise ValueError('Invalid credentials')
   with domain.LOCK,domain.connect() as c:
    if kind=='setup':
     if PRODUCTION:
      expected=os.environ.get('SETUP_TOKEN','')
      if not expected or not hmac.compare_digest(str(d.get('setup_token','')),expected): return jsonify(error='Setup token required'),403
     if c.execute('SELECT 1 FROM users').fetchone(): raise ValueError('Setup already completed')
     if not name or len(name)>100 or len(password)<12: raise ValueError('Use a username and password of at least 12 characters')
     salt=secrets.token_hex(16);c.execute('INSERT INTO users VALUES (?,?,?,?,1)',(name,salt,domain.password_hash(password,salt),'admin'));domain.audit(c,name,'admin setup',{})
    rows=c.execute('SELECT * FROM users WHERE lower(name)=lower(?)',(name,)).fetchall()
    row=rows[0] if len(rows)==1 else None
    if not row or not hmac.compare_digest(row['password'],domain.password_hash(password,row['salt'])): return jsonify(error='Invalid credentials'),401
    token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
    c.execute('DELETE FROM web_sessions WHERE expires<=?',(int(time.time()),))
    c.execute('INSERT INTO web_sessions VALUES (?,?,?)',(digest,row['name'],int(time.time())+SESSION_TTL))
   response=jsonify(ok=True);response.set_cookie(domain.COOKIE,token,max_age=SESSION_TTL,httponly=True,secure=PRODUCTION,samesite='Strict',path='/');return response
  if kind=='order':
   customer=current_customer()
   if not customer: return jsonify(error='Customer sign in required'),401
   if PREVIEW: return jsonify(error='Preview only. Customer orders are not enabled.'),403
   if rate_limited('order',10): return jsonify(error='Too many orders. Try again later.'),429
   if not d.get('phone','').strip() or (d.get('zone','pickup')!='pickup' and not d.get('address','').strip()): raise ValueError('Phone and delivery address required')
   if not d.get('request_id'): raise ValueError('Order request ID required')
   d=dict(d); d['customer']=customer['name']
   if not isinstance(d['request_id'],str) or not 16<=len(d['request_id'])<=128: raise ValueError()
   d['request_id']=hashlib.sha256((str(customer['id'])+':'+d['request_id']).encode()).hexdigest()
   return jsonify(domain.operation({'name':customer['email'],'role':'customer','company':1},kind,d,customer_id=customer['id']))
  user=signed_in()
  if not user: return jsonify(error='Sign in required'),401
  if kind=='logout':
   with domain.connect() as c: c.execute('DELETE FROM web_sessions WHERE token=?',(hashlib.sha256(request.cookies.get(domain.COOKIE,'').encode()).hexdigest(),))
   response=jsonify(ok=True);response.delete_cookie(domain.COOKIE,path='/');return response
  result=domain.operation(user,kind,d)
  if kind=='manage_user':
   with domain.connect() as c: c.execute('DELETE FROM web_sessions WHERE username=?',(result['name'],))
  return jsonify(result)
 except (ValueError,KeyError,TypeError,AttributeError,OverflowError,sqlite3.IntegrityError):
  return jsonify(error='Invalid request. Check the supplied fields and available stock.'),400

@web.errorhandler(413)
def too_large(error): return jsonify(error='Request too large'),413
@web.errorhandler(500)
def unexpected(error): return jsonify(error='The request could not be completed. Please try again.'),500

def serve():
 from waitress import serve as run
 initialize();port=int(os.environ.get('PORT',domain.CONFIG['port']))
 print(f"{domain.CONFIG['name']} listening on port {port}",flush=True)
 run(web,host='0.0.0.0' if PRODUCTION else '127.0.0.1',port=port,threads=8)

import accounts
initialize_accounts,current_customer=accounts.install(__import__(__name__))

if __name__=='__main__': serve()

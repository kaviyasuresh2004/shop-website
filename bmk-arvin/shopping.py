"""Delivery links and bulk enquiries stored inside this shop's database."""
import hashlib,json,re,time
from urllib.parse import urlsplit,urlencode
from flask import request,jsonify

class ReviewRequired(ValueError):pass

def initialize(c):
 c.executescript('''
 CREATE TABLE IF NOT EXISTS delivery_locations(sale INTEGER PRIMARY KEY REFERENCES sales(id),map_url TEXT NOT NULL,notes TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS bulk_enquiries(id INTEGER PRIMARY KEY,customer INTEGER NOT NULL REFERENCES customers(id),name TEXT NOT NULL,phone TEXT NOT NULL,details TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'new',created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
 CREATE TABLE IF NOT EXISTS enquiry_requests(key TEXT PRIMARY KEY,payload TEXT NOT NULL,enquiry INTEGER NOT NULL REFERENCES bulk_enquiries(id));
 ''')

def map_link(value):
 if not isinstance(value,str) or len(value)>2000:raise ValueError('Invalid map link')
 value=value.strip()
 if not value:return ''
 u=urlsplit(value)
 allowed=(u.hostname=='maps.app.goo.gl' or u.hostname=='maps.google.com' or (u.hostname in ('google.com','www.google.com') and u.path.startswith('/maps')) or (u.hostname=='goo.gl' and u.path.startswith('/maps/')))
 if not allowed or u.scheme!='https' or u.username or u.password or u.port not in (None,443):raise ValueError('Invalid map link')
 return value

def install(server):
 web,domain=server.web,server.domain
 @web.post('/api/bulk-enquiry')
 def enquire():
  customer=server.current_customer()
  if not customer:return jsonify(error='Customer sign in required'),401
  d=request.get_json(silent=True)
  try:
   if not isinstance(d,dict):raise ValueError()
   phone=d['phone'].strip();details=d['details'].strip();key=d['request_id']
   if not phone or len(phone)>80 or not 10<=len(details)<=4000 or not isinstance(key,str) or not 16<=len(key)<=128:raise ValueError()
   key=hashlib.sha256((str(customer['id'])+':'+key).encode()).hexdigest();fingerprint=json.dumps([phone,details])
   with domain.LOCK,domain.connect() as c:
    c.execute('BEGIN IMMEDIATE')
    previous=c.execute('SELECT * FROM enquiry_requests WHERE key=?',(key,)).fetchone()
    if previous:
     if previous['payload']!=fingerprint:raise ValueError()
     return jsonify(ok=True,enquiry=previous['enquiry'])
    if c.execute("SELECT COUNT(*) FROM bulk_enquiries WHERE customer=? AND created>=datetime('now','-1 hour')",(customer['id'],)).fetchone()[0]>=5:return jsonify(error='Too many enquiries. Please try again later.'),429
    eid=c.execute('INSERT INTO bulk_enquiries(customer,name,phone,details) VALUES (?,?,?,?)',(customer['id'],customer['name'],phone,details)).lastrowid
    c.execute('INSERT INTO enquiry_requests VALUES (?,?,?)',(key,fingerprint,eid));domain.audit(c,customer['email'],'bulk enquiry received',{'enquiry':eid})
   return jsonify(ok=True,enquiry=eid)
  except (ValueError,KeyError,TypeError,AttributeError):return jsonify(error='Check enquiry details.'),400

 @web.post('/api/bulk-status')
 def enquiry_status():
  user=server.signed_in()
  if not user:return jsonify(error='Sign in required'),401
  d=request.get_json(silent=True)
  try:
   status=d['status'];eid=domain.integer(d['enquiry'])
   if status not in ('new','reviewing','quoted','closed'):raise ValueError()
   with domain.LOCK,domain.connect() as c:
    if c.execute('UPDATE bulk_enquiries SET status=? WHERE id=?',(status,eid)).rowcount!=1:raise ValueError()
    domain.audit(c,user['name'],'bulk enquiry updated',{'enquiry':eid,'status':status})
   return jsonify(ok=True)
  except (ValueError,KeyError,TypeError,AttributeError):return jsonify(error='Check enquiry details.'),400

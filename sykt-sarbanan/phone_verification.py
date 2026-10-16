"""Optional paid provider integration. Disabled until explicitly configured."""
import base64,hashlib,json,os,re,time
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from flask import request,jsonify

def enabled():
 return os.environ.get('PHONE_OTP_ENABLED')=='true' and all(os.environ.get(k) for k in ('TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_VERIFY_SERVICE_SID'))

def normalize(value):
 if not isinstance(value,str):raise ValueError()
 phone=re.sub(r'[\s()-]','',value)
 if re.fullmatch(r'\d{7}',phone):phone='+673'+phone
 if not re.fullmatch(r'\+673\d{7}',phone):raise ValueError('Use a Brunei phone number')
 return phone

def initialize(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS phone_verified(customer INTEGER PRIMARY KEY REFERENCES customers(id),phone TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS phone_challenges(customer INTEGER PRIMARY KEY REFERENCES customers(id),phone TEXT NOT NULL,sid TEXT NOT NULL,expires INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0);
 CREATE TABLE IF NOT EXISTS otp_sends(customer INTEGER,phone_hash TEXT,ip_hash TEXT,created INTEGER);
 CREATE INDEX IF NOT EXISTS otp_send_time ON otp_sends(created);''')

def verified(c,customer,phone):
 try:phone=normalize(phone)
 except ValueError:return False
 return bool(c.execute('SELECT 1 FROM phone_verified WHERE customer=? AND phone=?',(customer,phone)).fetchone())

def provider(endpoint,fields):
 service=os.environ['TWILIO_VERIFY_SERVICE_SID']
 if not re.fullmatch(r'VA[0-9a-fA-F]{32}',service):raise ValueError()
 auth=base64.b64encode((os.environ['TWILIO_ACCOUNT_SID']+':'+os.environ['TWILIO_AUTH_TOKEN']).encode()).decode()
 req=Request('https://verify.twilio.com/v2/Services/'+service+'/'+endpoint,data=urlencode(fields).encode(),headers={'Authorization':'Basic '+auth,'Content-Type':'application/x-www-form-urlencoded'},method='POST')
 with urlopen(req,timeout=10) as response:return json.load(response)

def install(server):
 domain=server.domain
 @server.web.get('/api/phone/status')
 def status():
  customer=server.current_customer();is_verified=False
  if customer:
   with domain.connect() as c:is_verified=verified(c,customer['id'],customer['phone'])
  return jsonify(enabled=enabled(),verified=is_verified,channel=os.environ.get('PHONE_OTP_CHANNEL','sms') if enabled() else None)

 @server.web.post('/api/phone/<kind>')
 def phone_action(kind):
  customer=server.current_customer()
  if not customer:return jsonify(error='Customer sign in required'),401
  if not enabled():return jsonify(error='Phone verification is not configured yet.'),503
  try:
   phone=normalize(customer['phone']);d=request.get_json(silent=True)
   if not isinstance(d,dict):raise ValueError()
   now=int(time.time())
   if kind=='send':
    if d.get('consent') is not True:raise ValueError()
    channel=os.environ.get('PHONE_OTP_CHANNEL','sms')
    if channel not in ('sms','whatsapp'):raise ValueError()
    ip=(request.headers.get('X-Forwarded-For','').split(',')[-1].strip() or request.remote_addr) if server.PRODUCTION else request.remote_addr
    ph=hashlib.sha256(phone.encode()).hexdigest();ih=hashlib.sha256((ip or '').encode()).hexdigest()
    with domain.LOCK,domain.connect() as c:
     c.execute('BEGIN IMMEDIATE');c.execute('DELETE FROM otp_sends WHERE created<?',(now-86400,))
     sends=c.execute('SELECT * FROM otp_sends').fetchall()
     if len(sends)>=50 or sum(r['created']>now-3600 and (r['customer']==customer['id'] or r['phone_hash']==ph) for r in sends)>=3 or sum(r['created']>now-3600 and r['ip_hash']==ih for r in sends)>=5 or any(r['created']>now-60 and (r['customer']==customer['id'] or r['phone_hash']==ph) for r in sends):return jsonify(error='Too many verification attempts. Please wait.'),429
     c.execute('INSERT INTO otp_sends VALUES (?,?,?,?)',(customer['id'],ph,ih,now))
    result=provider('Verifications',{'To':phone,'Channel':channel})
    sid=result.get('sid','')
    if result.get('status')!='pending' or not re.fullmatch(r'VE[0-9a-fA-F]{32}',sid):raise ValueError()
    with domain.connect() as c:c.execute('INSERT OR REPLACE INTO phone_challenges VALUES (?,?,?,?,0)',(customer['id'],phone,sid,now+600))
    return jsonify(ok=True)
   if kind=='check':
    code=d.get('code','')
    if not isinstance(code,str) or not re.fullmatch(r'\d{4,10}',code):raise ValueError()
    with domain.LOCK,domain.connect() as c:
     c.execute('BEGIN IMMEDIATE');challenge=c.execute('SELECT * FROM phone_challenges WHERE customer=?',(customer['id'],)).fetchone()
     if not challenge or challenge['phone']!=phone or challenge['expires']<=now or challenge['attempts']>=5:return jsonify(error='Code expired or too many attempts. Request another code.'),400
     c.execute('UPDATE phone_challenges SET attempts=attempts+1 WHERE customer=?',(customer['id'],))
    result=provider('VerificationCheck',{'VerificationSid':challenge['sid'],'Code':code})
    if result.get('status')!='approved':return jsonify(error='Incorrect verification code.'),400
    with domain.LOCK,domain.connect() as c:
     current=c.execute('SELECT phone FROM customers WHERE id=?',(customer['id'],)).fetchone()
     if normalize(current['phone'])!=phone:raise ValueError()
     c.execute('INSERT OR REPLACE INTO phone_verified VALUES (?,?)',(customer['id'],phone));c.execute('DELETE FROM phone_challenges WHERE customer=?',(customer['id'],))
    return jsonify(ok=True)
   return jsonify(error='Unknown operation'),404
  except (HTTPError,URLError,TimeoutError,OSError):return jsonify(error='Verification service unavailable. Please try later.'),503
  except (ValueError,KeyError,TypeError,AttributeError):return jsonify(error='Check your phone number and verification code.'),400

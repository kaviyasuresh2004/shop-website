"""Per-shop public details, delivery settings and cash-on-delivery records."""
import json
from urllib.parse import urlsplit

DEFAULTS={'legal_name':'','registered_address':'','incorporation_date':'','address':'','phone':'','hours':'','map_url':'','delivery_policy':'','returns_policy':'','privacy_policy':'','checkout_enabled':False,'catalogue_confirmed':False,'delivery_fees':{'pickup':0,'Brunei-Muara':500,'Tutong':1000,'Belait':1500,'Temburong':2000}}

def initialize(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS shop_settings(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS order_payments(sale INTEGER PRIMARY KEY REFERENCES sales(id),method TEXT NOT NULL,status TEXT NOT NULL);''')

def load(c,default_enabled=False):
 row=c.execute('SELECT data FROM shop_settings WHERE id=1').fetchone()
 data={**DEFAULTS,'checkout_enabled':default_enabled,'delivery_fees':dict(DEFAULTS['delivery_fees'])}
 if row:data.update(json.loads(row['data']))
 return data

def save(c,d):
 result={}
 old=load(c)
 for key,limit in [('legal_name',200),('registered_address',1000),('incorporation_date',40),('address',1000),('phone',80),('hours',500),('map_url',2000),('delivery_policy',5000),('returns_policy',5000),('privacy_policy',5000)]:
  value=d.get(key,old.get(key,''))
  if not isinstance(value,str) or len(value)>limit:raise ValueError()
  result[key]=value.strip()
 if result['map_url']:
  url=urlsplit(result['map_url'])
  if url.scheme!='https' or not url.netloc or url.username or url.password:raise ValueError()
 for key in ('checkout_enabled','catalogue_confirmed'):
  if not isinstance(d.get(key),bool):raise ValueError()
  result[key]=d[key]
 fees=d['delivery_fees']
 if not isinstance(fees,dict) or set(fees)!=set(DEFAULTS['delivery_fees']):raise ValueError()
 for value in fees.values():
  if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=1000000:raise ValueError()
 if fees['pickup']!=0:raise ValueError()
 result['delivery_fees']=fees
 if result['checkout_enabled'] and (not result['catalogue_confirmed'] or any(not result[k] for k in ('address','phone','hours','delivery_policy','returns_policy','privacy_policy'))):
  raise ValueError()
 c.execute('INSERT INTO shop_settings VALUES (1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(json.dumps(result),))
 return result

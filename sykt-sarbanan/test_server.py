import json,os,sqlite3,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import app,server

class ServerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
  self.original=app.DB;app.DB=Path(self.tmp.name)/'shop.db'
  self.production=server.PRODUCTION;self.preview=server.PREVIEW;self.url=server.PUBLIC_URL
  server.PRODUCTION=False;server.PREVIEW=False;server.PUBLIC_URL='';server.LIMITS.clear()
  server.initialize();server.web.config['TESTING']=True;self.client=server.web.test_client()
  self.client.post('/api/customer/register',json={'email':'test@example.test','name':'Test customer','password':'customer-test-password'})
 def tearDown(self):
  app.DB=self.original;server.PRODUCTION=self.production;server.PREVIEW=self.preview;server.PUBLIC_URL=self.url;self.tmp.cleanup()
 def post(self,kind,data,**kw): return self.client.post('/api/'+kind,json=data,**kw)
 def login(self):
  r=self.post('setup',{'name':' admin ','password':'test-password-123'});self.assertEqual(r.status_code,200);return r
 def order(self):return {'customer':'Test customer','phone':'123','items':[{'product':1,'qty':2}],'request_id':'test-request-id-123456789'}
 def qty(self):
  with app.connect() as c:return c.execute('SELECT qty FROM stock WHERE id=1').fetchone()[0]
 def test_pages_assets_health_brand_and_private_files(self):
  for path in ('/','/staff','/assets/site.js','/assets/staff.js','/assets/en.json','/assets/ms.json','/healthz'):
   r=self.client.get(path);self.assertEqual(r.status_code,200);r.close()
  self.assertEqual(self.client.get('/healthz').json['shop'],app.CONFIG['slug'])
  for path in ('/shop.json','/data/shop.db','/app.py','/assets/../app.py','/assets/%2e%2e/app.py'):
   self.assertEqual(self.client.get(path).status_code,404)
 def test_private_staff_and_worker_permissions(self):
  self.assertEqual(self.client.get('/api/staff').status_code,401);self.login()
  self.assertEqual(self.post('user',{'name':'worker','password':'test-worker-123'}).status_code,200)
  self.post('logout',{});self.assertEqual(self.post('login',{'name':'worker','password':'test-worker-123'}).status_code,200)
  self.assertEqual(self.post('product',{'sku':'TEST','name':'Tool','category':'Hand tools','price':100}).status_code,200)
  for kind,d in [('delete_product',{'product':1}),('user',{'name':'x','password':'test-password-123'}),('import',{'csv':'SKU,Quantity\nDRILL-001,1','reason':'test'}),('transfer',{}),('adjust',{'company':2,'product':1,'delta':1,'reason':'bad'})]:
   self.assertEqual(self.post(kind,d).status_code,400)
  self.assertEqual(self.qty(),30)
 def test_preview_cannot_place_orders(self):
  server.PREVIEW=True;self.assertTrue(self.client.get('/api/catalog').json['preview'])
  self.assertEqual(self.post('order',self.order()).status_code,403);self.assertEqual(self.qty(),30)
 def test_order_retry_is_idempotent_and_mismatch_rejected(self):
  d=self.order();r=self.post('order',d);self.assertEqual(r.status_code,200)
  self.assertEqual(self.post('order',d).json,r.json);self.assertEqual(self.qty(),28)
  d['items'][0]['qty']=3;self.assertEqual(self.post('order',d).status_code,400);self.assertEqual(self.qty(),28)
 def test_server_uses_prices_and_atomic_stock(self):
  d=self.order();d['items'][0]['unit_price']=0;d['total']=1
  self.assertEqual(self.post('order',d).json['total'],17800)
  d=self.order();d['request_id']='another-request-123456';d['items'].append({'product':2,'qty':9999})
  self.assertEqual(self.post('order',d).status_code,400);self.assertEqual(self.qty(),28)
 def test_input_validation_and_delivery(self):
  for raw in ([],None,'text',1):self.assertEqual(self.client.post('/api/order',data=json.dumps(raw),content_type='application/json').status_code,400)
  self.assertEqual(self.client.post('/api/order',data='not json').status_code,415)
  for d in ({},dict(self.order(),phone=''),dict(self.order(),zone='Tutong'),dict(self.order(),items='bad'),dict(self.order(),items=[{'product':1,'qty':True}])):
   self.assertEqual(self.post('order',d).status_code,400)
  d=dict(self.order(),zone='Tutong',address='Test address');r=self.post('order',d)
  self.assertEqual(r.status_code,200);self.assertEqual(r.json['total'],18800)
 def test_https_origin_and_setup_token(self):
  server.PRODUCTION=True;server.PUBLIC_URL='https://bmk.example.test'
  kw={'base_url':server.PUBLIC_URL,'headers':{'Origin':server.PUBLIC_URL}}
  with patch.dict(os.environ,{'SETUP_TOKEN':'test-private-setup-token'}):
   self.assertEqual(self.post('setup',{'name':'admin','password':'test-password-123'},**kw).status_code,403)
   r=self.post('setup',{'name':'admin','password':'test-password-123','setup_token':'test-private-setup-token'},**kw)
   self.assertEqual(r.status_code,200);cookie=r.headers['Set-Cookie'];self.assertIn('Secure',cookie);self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=Strict',cookie)
   self.assertEqual(self.client.get('/api/staff',base_url=server.PUBLIC_URL).status_code,200)
  self.assertEqual(self.post('login',{'name':'admin','password':'test-password-123'},base_url=server.PUBLIC_URL,headers={'Origin':'https://evil.example.test'}).status_code,403)
 def test_sessions_expire_and_password_change_revokes(self):
  self.login()
  with app.connect() as c:c.execute('UPDATE web_sessions SET expires=0')
  self.assertEqual(self.client.get('/api/staff').status_code,401)
  self.post('login',{'name':'admin','password':'test-password-123'});self.post('user',{'name':'worker','password':'test-worker-123'})
  worker=server.web.test_client();worker.post('/api/login',json={'name':'worker','password':'test-worker-123'})
  self.assertEqual(worker.get('/api/staff').status_code,200)
  self.assertEqual(self.post('manage_user',{'name':'worker','password':'new-test-worker-123'}).status_code,200)
  self.assertEqual(worker.get('/api/staff').status_code,401)
 def test_rate_limits(self):
  for _ in range(20):self.post('login',{'name':'missing','password':'test-password-123'})
  self.assertEqual(self.post('login',{'name':'missing','password':'test-password-123'}).status_code,429)
 def test_production_requires_persistent_path(self):
  server.PRODUCTION=True
  with patch.dict(os.environ,{},clear=True):
   with self.assertRaises(RuntimeError):server.initialize()
 def test_pending_order_is_not_completed_sales_revenue(self):
  result=self.post('order',self.order()).json;self.login()
  report=self.client.get('/api/staff').json['report'];self.assertEqual(report['total'],0);self.assertEqual(report['pending_total'],17800)
  self.assertEqual(self.post('order_status',{'sale':result['sale'],'status':'completed'}).status_code,200)
  report=self.client.get('/api/staff').json['report'];self.assertEqual(report['total'],17800);self.assertEqual(report['pending_total'],0)

if __name__=='__main__':unittest.main()

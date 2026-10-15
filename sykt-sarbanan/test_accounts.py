import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import app, server

class AccountsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
  self.old=app.DB; app.DB=Path(self.tmp.name)/'shop.db'
  self.preview=server.PREVIEW; self.production=server.PRODUCTION
  server.PREVIEW=False; server.PRODUCTION=False; server.LIMITS.clear()
  server.initialize(); self.client=server.web.test_client()
 def tearDown(self):
  app.DB=self.old; server.PREVIEW=self.preview; server.PRODUCTION=self.production; self.tmp.cleanup()
 def register(self,client,email='one@example.test'):
  return client.post('/api/customer/register',json={'email':email,'password':'customer-password-123','name':'Customer One','phone':'123','address':'Private address'})
 def order(self,client):
  return client.post('/api/order',json={'customer':'Forged name','phone':'123','items':[{'product':1,'qty':1}],'request_id':'customer-request-12345'})
 def test_registration_login_cookies_and_staff_boundary(self):
  self.assertEqual(self.register(self.client).status_code,200)
  self.assertEqual(self.client.get('/api/customer/me').json['customer']['email'],'one@example.test')
  self.assertEqual(self.client.get('/api/staff').status_code,401)
  for kind in ('adjust','product','user','manage_user'):
   self.assertEqual(self.client.post('/api/'+kind,json={}).status_code,401)
  self.client.post('/api/customer/logout',json={})
  self.assertEqual(self.client.get('/api/customer/me').status_code,401)
  self.assertEqual(self.client.post('/api/customer/login',json={'email':' ONE@EXAMPLE.TEST ','password':'customer-password-123'}).status_code,200)
  self.assertEqual(self.register(server.web.test_client(),'ONE@example.test').status_code,400)
 def test_checkout_requires_customer_and_orders_are_private(self):
  self.assertEqual(self.order(self.client).status_code,401)
  self.client.post('/api/setup',json={'name':'admin','password':'admin-password-123'})
  self.assertEqual(self.order(self.client).status_code,401)
  self.register(self.client); other=server.web.test_client(); self.register(other,'two@example.test')
  first=self.order(self.client); self.assertEqual(first.status_code,200)
  self.assertEqual(self.order(self.client).json,first.json)
  self.assertEqual(self.client.get('/api/customer/me').json['orders'][0]['id'],first.json['sale'])
  self.assertEqual(other.get('/api/customer/me').json['orders'],[])
  second=self.order(other);self.assertNotEqual(first.json['sale'],second.json['sale'])
  with app.connect() as c:
   self.assertEqual(c.execute('SELECT customer FROM sales WHERE id=?',(first.json['sale'],)).fetchone()[0],'Customer One')
   self.assertEqual(c.execute('SELECT qty FROM stock WHERE id=1').fetchone()[0],28)
  server.PREVIEW=True;self.assertEqual(self.order(other).status_code,403)
 def test_customer_password_change_revokes_other_sessions(self):
  self.register(self.client);other=server.web.test_client()
  other.post('/api/customer/login',json={'email':'one@example.test','password':'customer-password-123'})
  self.assertEqual(self.client.post('/api/customer/password',json={'current_password':'wrong','password':'new-password-123'}).status_code,401)
  self.assertEqual(self.client.post('/api/customer/password',json={'current_password':'customer-password-123','password':'new-password-123'}).status_code,200)
  self.assertEqual(other.get('/api/customer/me').status_code,401)
  self.assertEqual(self.client.get('/api/customer/me').status_code,200)
 def test_staff_case_matching_and_safe_owner_recovery(self):
  self.client.post('/api/setup',json={'name':'Owner@Example.test','password':'owner-password-123'})
  self.client.post('/api/user',json={'name':'Worker','password':'worker-password-123'})
  self.client.post('/api/logout',json={})
  self.assertEqual(self.client.post('/api/login',json={'name':' OWNER@example.test ','password':'owner-password-123'}).status_code,200)
  self.assertEqual(self.client.get('/api/staff').json['user']['name'],'Owner@Example.test')
  payload={'name':'owner@example.test','password':'new-owner-password-123','recovery_token':'owner-token-for-test-1234567890123456'}
  self.assertEqual(self.client.post('/api/recover-admin',json=payload).status_code,403)
  with patch.dict(os.environ,{'ADMIN_RECOVERY_TOKEN':payload['recovery_token']}):
   self.assertEqual(self.client.post('/api/recover-admin',json=dict(payload,name='Worker')).status_code,401)
   self.assertEqual(self.client.post('/api/recover-admin',json=payload).status_code,200)
   self.assertEqual(self.client.get('/api/staff').status_code,401)
   self.assertEqual(self.client.post('/api/recover-admin',json=payload).status_code,403)
  self.assertEqual(self.client.post('/api/login',json={'name':'Owner@example.test','password':'new-owner-password-123'}).status_code,200)
 def test_persistence_and_invalid_requests(self):
  self.register(self.client);server.initialize()
  self.assertEqual(self.client.get('/api/customer/me').status_code,200)
  self.assertEqual(self.client.post('/api/customer/register',json={'email':'bad','name':'X','password':'short'}).status_code,400)
  self.assertEqual(self.client.post('/api/customer/register',json=[]).status_code,400)
  self.assertEqual(self.client.post('/api/customer/login',json={'email':7,'password':[]}).status_code,400)
 def test_secure_cookies_and_cross_origin_rejected(self):
  server.PRODUCTION=True
  r=self.register(self.client);self.assertIn('Secure',r.headers['Set-Cookie']);self.assertIn('HttpOnly',r.headers['Set-Cookie'])
  self.assertEqual(self.client.post('/api/customer/login',json={'email':'one@example.test','password':'customer-password-123'},headers={'Origin':'https://evil.test'}).status_code,403)

if __name__=='__main__': unittest.main()

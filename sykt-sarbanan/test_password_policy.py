import os,unittest
from unittest.mock import patch
import test_accounts

class PasswordPolicyTests(unittest.TestCase):
 setUp=test_accounts.AccountsTests.setUp
 tearDown=test_accounts.AccountsTests.tearDown
 def test_staff_setup_create_reset_and_recovery_boundary(self):
  def post(kind,data):return self.client.post('/api/'+kind,json=data)
  self.assertEqual(post('setup',{'name':'admin','password':'Seven77'}).status_code,400)
  self.assertEqual(post('setup',{'name':'admin','password':'Eight888'}).status_code,200)
  self.assertEqual(post('user',{'name':'worker','password':'Seven77'}).status_code,400)
  self.assertEqual(post('user',{'name':'worker','password':'Eight888'}).status_code,200)
  self.assertEqual(post('manage_user',{'name':'worker','password':'Seven77'}).status_code,400)
  self.assertEqual(post('manage_user',{'name':'worker','password':'Reset888'}).status_code,200)
  with patch.dict(os.environ,{'ADMIN_RECOVERY_TOKEN':'synthetic-recovery-token-for-tests-12345'}):
   payload={'name':'admin','password':'Seven77','recovery_token':os.environ['ADMIN_RECOVERY_TOKEN']}
   self.assertEqual(post('recover-admin',payload).status_code,400)
   payload['password']='Reset888';self.assertEqual(post('recover-admin',payload).status_code,200)
  self.assertEqual(post('login',{'name':'admin','password':'Reset888'}).status_code,200)
 def test_customer_registration_and_password_change_boundary(self):
  def post(kind,data):return self.client.post('/api/customer/'+kind,json=data)
  payload={'name':'Customer','email':'customer@example.test','password':'Seven77'}
  self.assertEqual(post('register',payload).status_code,400)
  payload['password']='Eight888';self.assertEqual(post('register',payload).status_code,200)
  self.assertEqual(post('password',{'current_password':'Eight888','password':'Seven77'}).status_code,400)
  self.assertEqual(post('password',{'current_password':'Eight888','password':'Reset888'}).status_code,200)
  post('logout',{});self.assertEqual(post('login',{'email':payload['email'],'password':'Reset888'}).status_code,200)

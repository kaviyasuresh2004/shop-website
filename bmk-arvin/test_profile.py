import unittest
import test_accounts

class ProfileTests(unittest.TestCase):
 setUp=test_accounts.AccountsTests.setUp
 tearDown=test_accounts.AccountsTests.tearDown
 register=test_accounts.AccountsTests.register
 def test_profile_is_private_and_changes_only_signed_in_customer(self):
  self.assertEqual(self.client.post('/api/customer/profile',json={'name':'Changed'}).status_code,401)
  self.register(self.client)
  other=self.client.application.test_client();self.register(other,'other@example.test')
  result=self.client.post('/api/customer/profile',json={'name':'Updated Name','phone':'+673 1234567','address':'Updated address','id':2,'email':'other@example.test','role':'admin'})
  self.assertEqual(result.status_code,200)
  profile=self.client.get('/api/customer/me').json['customer']
  self.assertEqual(profile['name'],'Updated Name');self.assertEqual(profile['phone'],'+673 1234567');self.assertEqual(profile['address'],'Updated address');self.assertEqual(profile['email'],'one@example.test')
  self.assertEqual(other.get('/api/customer/me').json['customer']['name'],'Customer One')
  self.assertEqual(self.client.get('/api/staff').status_code,401)
 def test_invalid_profile_does_not_erase_saved_details(self):
  self.register(self.client)
  for payload in [{'name':''},{'name':'A','phone':[]},{'name':'A','address':'x'*1001},{'name':'x'*201}]:
   self.assertEqual(self.client.post('/api/customer/profile',json=payload).status_code,400)
  self.assertEqual(self.client.get('/api/customer/me').json['customer']['name'],'Customer One')

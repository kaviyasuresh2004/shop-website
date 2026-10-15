import unittest
import test_server

class CommerceTests(unittest.TestCase):
 setUp=test_server.ServerTests.setUp
 tearDown=test_server.ServerTests.tearDown
 login=test_server.ServerTests.login
 post=test_server.ServerTests.post
 order=test_server.ServerTests.order
 qty=test_server.ServerTests.qty
 def settings(self):
  return {'address':'Test shop address','phone':'123','hours':'9–5','map_url':'https://maps.example.test/shop','delivery_policy':'Test delivery policy','returns_policy':'Test returns policy','privacy_policy':'Test privacy policy','checkout_enabled':True,'catalogue_confirmed':True,'delivery_fees':{'pickup':0,'Brunei-Muara':750,'Tutong':1000,'Belait':1500,'Temburong':2000}}
 def test_shop_settings_admin_only_validated_and_persistent(self):
  self.assertEqual(self.post('shop-settings',self.settings()).status_code,401)
  self.login()
  self.assertEqual(self.post('shop-settings',dict(self.settings(),catalogue_confirmed=False)).status_code,400)
  self.assertEqual(self.post('shop-settings',dict(self.settings(),map_url='javascript:alert(1)')).status_code,400)
  self.assertEqual(self.post('shop-settings',self.settings()).status_code,200)
  catalog=self.client.get('/api/catalog').json;self.assertFalse(catalog['preview']);self.assertEqual(catalog['shopDetails']['address'],'Test shop address')
  import server;server.initialize();self.assertEqual(self.client.get('/api/catalog').json['shopDetails']['phone'],'123')
  self.post('user',{'name':'worker','password':'Worker888'});self.post('logout',{});self.post('login',{'name':'worker','password':'Worker888'})
  self.assertEqual(self.post('shop-settings',self.settings()).status_code,403)
 def test_cod_amount_payment_status_and_no_double_stock_deduction(self):
  self.login();self.post('shop-settings',self.settings())
  payload=dict(self.order(),zone='Brunei-Muara',address='Delivery address',payment_method='cod',delivery=0)
  result=self.post('order',payload);self.assertEqual(result.status_code,200);self.assertEqual(result.json['total'],18550)
  history=self.client.get('/api/customer/me').json['orders'];self.assertEqual(history[0]['payment_method'],'cod');self.assertEqual(history[0]['payment_status'],'pending')
  self.assertEqual(self.post('order',payload).json,result.json);self.assertEqual(self.qty(),28)
  self.post('order_status',{'sale':result.json['sale'],'status':'delivered'})
  self.assertEqual(self.client.get('/api/customer/me').json['orders'][0]['payment_status'],'pending')
  self.assertEqual(self.post('payment_received',{'sale':result.json['sale']}).status_code,200)
  self.assertEqual(self.client.get('/api/customer/me').json['orders'][0]['payment_status'],'paid');self.assertEqual(self.qty(),28)
 def test_unsupported_payment_rolls_back_and_disabled_checkout_blocks(self):
  self.login();self.post('shop-settings',self.settings())
  self.assertEqual(self.post('order',dict(self.order(),payment_method='bank')).status_code,400);self.assertEqual(self.qty(),30)
  self.post('shop-settings',dict(self.settings(),checkout_enabled=False))
  self.assertTrue(self.client.get('/api/catalog').json['preview']);self.assertEqual(self.post('order',self.order()).status_code,403)

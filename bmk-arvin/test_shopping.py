import copy,os,unittest
from unittest.mock import patch
import app,server,test_server
from datetime import datetime,timedelta,timezone

class ShoppingTests(unittest.TestCase):
 setUp=test_server.ServerTests.setUp
 tearDown=test_server.ServerTests.tearDown
 login=test_server.ServerTests.login
 post=test_server.ServerTests.post
 order=test_server.ServerTests.order
 qty=test_server.ServerTests.qty
 def test_delivery_map_and_complete_order_visible_to_worker(self):
  payload=dict(self.order(),map_url='https://maps.app.goo.gl/TestPin',delivery_notes='Gate beside the blue house',zone='Tutong',address='House 12, test road',reviewed_total=18800,payment_method='cod')
  result=self.post('order',payload);self.assertEqual(result.status_code,200)
  self.assertEqual(self.post('order',payload).json,result.json);self.assertEqual(self.qty(),28)
  self.login();self.post('user',dict(name='worker',password='Worker123'));self.post('logout',{});self.post('login',dict(name='worker',password='Worker123'))
  orders=self.client.get('/api/staff').json['orders'];self.assertEqual(orders[0]['sale'],result.json['sale']);self.assertEqual(orders[0]['map_url'],payload['map_url']);self.assertEqual(orders[0]['delivery_notes'],payload['delivery_notes']);self.assertEqual(orders[0]['status'],'pending');self.assertEqual(orders[0]['payment_status'],'pending')
 def test_invalid_map_and_stale_price_roll_back(self):
  for link in ('javascript:alert(1)','https://google.com.evil.test/maps/x','https://user:pass@maps.google.com/maps','https://maps.app.goo.gl:99/pin'):
   self.assertEqual(self.post('order',dict(self.order(),map_url=link)).status_code,400);self.assertEqual(self.qty(),30)
  self.assertEqual(self.post('order',dict(self.order(),reviewed_total=1)).status_code,409);self.assertEqual(self.qty(),30)
  self.assertEqual(self.post('order',dict(self.order(),reviewed_total=17800)).status_code,200)
 def test_enquiry_is_private_idempotent_and_does_not_use_stock(self):
  payload=dict(phone='+673 1234567',details='Please quote 50 drills with delivery.',request_id='bulk-request-unique-1234')
  first=self.post('bulk-enquiry',payload);self.assertEqual(first.status_code,200);self.assertEqual(self.post('bulk-enquiry',payload).json,first.json);self.assertEqual(self.qty(),30)
  self.assertEqual(self.post('bulk-enquiry',dict(payload,details='Different quote request')).status_code,400)
  self.assertEqual(self.client.get('/api/staff').status_code,401);self.assertNotIn('enquiries',self.client.get('/api/catalog').json)
  self.login();result=self.client.get('/api/staff').json;self.assertEqual(result['enquiries'][0]['details'],payload['details']);self.assertEqual(result['sales'],[])
  self.assertEqual(self.post('bulk-status',dict(enquiry=first.json['enquiry'],status='quoted')).status_code,200)
  self.assertEqual(self.client.get('/api/staff').json['enquiries'][0]['status'],'quoted')
 def test_phone_disabled_never_calls_provider(self):
  with patch.dict(os.environ,{'PHONE_OTP_ENABLED':'false'}),patch('phone_verification.provider') as provider:
   self.assertFalse(self.client.get('/api/phone/status').json['enabled']);self.assertEqual(self.post('phone/send',dict(consent=True)).status_code,503);provider.assert_not_called()
 def test_phone_verified_challenge_limits_and_number_change(self):
  env=dict(PHONE_OTP_ENABLED='true',TWILIO_ACCOUNT_SID='AC'+'a'*32,TWILIO_AUTH_TOKEN='test-only',TWILIO_VERIFY_SERVICE_SID='VA'+'a'*32)
  self.post('customer/profile',dict(name='Test customer',phone='+673 1234567',address='Test house'))
  with patch.dict(os.environ,env),patch('phone_verification.provider') as provider:
   self.assertEqual(self.post('order',dict(self.order(),phone='+6731234567')).status_code,403)
   self.assertEqual(self.post('phone/send',{}).status_code,400);provider.assert_not_called()
   provider.return_value=dict(status='pending',sid='VE'+'b'*32)
   self.assertEqual(self.post('phone/send',dict(consent=True)).status_code,200);self.assertEqual(self.post('phone/send',dict(consent=True)).status_code,429)
   provider.return_value=dict(status='pending');self.assertEqual(self.post('phone/check',dict(code='123456')).status_code,400)
   provider.return_value=dict(status='approved');self.assertEqual(self.post('phone/check',dict(code='654321')).status_code,200)
   self.assertTrue(self.client.get('/api/phone/status').json['verified']);self.assertEqual(self.post('phone/check',dict(code='654321')).status_code,400)
   self.assertEqual(self.post('order',dict(self.order(),phone='+6731234567')).status_code,200)
   self.post('customer/profile',dict(name='Test customer',phone='+6737654321',address='Test house'));self.assertFalse(self.client.get('/api/phone/status').json['verified'])
 def test_wrong_code_attempt_limit_and_expiry(self):
  env=dict(PHONE_OTP_ENABLED='true',TWILIO_ACCOUNT_SID='AC'+'a'*32,TWILIO_AUTH_TOKEN='test-only',TWILIO_VERIFY_SERVICE_SID='VA'+'a'*32)
  self.post('customer/profile',dict(name='Test customer',phone='1234567',address=''))
  with patch.dict(os.environ,env),patch('phone_verification.provider',return_value=dict(status='pending',sid='VE'+'a'*32)) as provider:
   self.assertEqual(self.post('phone/send',dict(consent=True)).status_code,200)
   for _ in range(5):self.assertEqual(self.post('phone/check',dict(code='111111')).status_code,400)
   provider.reset_mock();self.assertEqual(self.post('phone/check',dict(code='111111')).status_code,400);provider.assert_not_called()
   with app.connect() as c:c.execute('UPDATE phone_challenges SET expires=0,attempts=0')
   self.assertEqual(self.post('phone/check',dict(code='111111')).status_code,400);provider.assert_not_called()
 def test_scheduled_discount_applies_to_checkout_only_in_period(self):
  self.login();now=datetime.now(timezone.utc)
  promotion=dict(kind='discount',company=1,product=1,price=6900,title_en='Weekend deal',title_ms='Tawaran hujung minggu',start=(now+timedelta(days=1)).isoformat(),end=(now+timedelta(days=2)).isoformat())
  self.assertEqual(self.post('promotion',promotion).status_code,200)
  self.assertEqual(self.post('order',dict(self.order(),reviewed_total=17800)).json['total'],17800)
  with app.connect() as c:c.execute('UPDATE promotions SET start=?,end=?',((now-timedelta(hours=1)).isoformat(),(now+timedelta(hours=1)).isoformat()))
  payload=dict(self.order(),request_id='discounted-order-new-123',reviewed_total=13800)
  result=self.post('order',payload);self.assertEqual(result.status_code,200);self.assertEqual(result.json['total'],13800)
  with app.connect() as c:c.execute('UPDATE promotions SET end=?',((now-timedelta(minutes=1)).isoformat(),))
  self.assertEqual(self.post('order',dict(payload,request_id='expired-order-new-123')).status_code,409)

if __name__=='__main__':unittest.main()

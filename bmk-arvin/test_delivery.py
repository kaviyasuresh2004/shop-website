import unittest
import app,test_server
class DeliveryTests(unittest.TestCase):
 setUp=test_server.ServerTests.setUp
 tearDown=test_server.ServerTests.tearDown
 login=test_server.ServerTests.login
 post=test_server.ServerTests.post
 order=test_server.ServerTests.order
 qty=test_server.ServerTests.qty
 def enable(self):
  self.login()
  self.assertEqual(self.post('shop-settings',dict(checkout_enabled=True,catalogue_confirmed=True,delivery_charge_mode='estimate',delivery_fees=dict(app.commerce.DEFAULTS['delivery_fees']))).status_code,200)
 def quote_order(self):
  d=dict(self.order(),zone='Brunei-Muara',address='Test delivery address',payment_method='cod')
  r=self.post('order',d);self.assertEqual(r.status_code,200);self.assertTrue(r.json['delivery_estimated'])
  self.assertEqual(self.post('order',d).json,r.json)
  return r.json['sale']
 def test_worker_agreed_fee_updates_customer_totals_and_reports_only(self):
  self.enable();sale=self.quote_order();self.assertEqual(self.qty(),28)
  history=self.client.get('/api/customer/me').json['orders'][0];self.assertTrue(history['delivery_pending']);self.assertEqual(history['total'],18300)
  for kind,data in [('order_status',dict(sale=sale,status='ready')),('payment_received',dict(sale=sale))]:self.assertEqual(self.post(kind,data).status_code,400)
  self.post('user',dict(name='worker',password='Worker888'));self.post('logout',{});self.post('login',dict(name='worker',password='Worker888'))
  self.assertEqual(self.post('delivery_quote',dict(sale=sale,fee_cents=700,customer_confirmed=True)).status_code,200)
  history=self.client.get('/api/customer/me').json['orders'][0];self.assertFalse(history['delivery_pending']);self.assertEqual(history['total'],18500)
  staff=self.client.get('/api/staff').json;self.assertEqual(staff['report']['pending_total'],18500);self.assertEqual(staff['sales'][0]['total'],18500)
  self.assertEqual(self.post('order_status',dict(sale=sale,status='delivered')).status_code,200)
  self.assertEqual(self.post('payment_received',dict(sale=sale)).status_code,200)
  self.assertEqual(self.client.get('/api/staff').json['report']['total'],18500);self.assertEqual(self.qty(),28)
  with app.connect() as c:self.assertEqual(c.execute('SELECT total FROM sales WHERE id=?',(sale,)).fetchone()[0],18300)
  self.assertEqual(self.post('delivery_quote',dict(sale=sale,fee_cents=500,customer_confirmed=True)).status_code,400)
 def test_consent_validation_customer_permissions_and_pickup(self):
  self.enable();sale=self.quote_order()
  for data in [dict(sale=sale,fee_cents=700),dict(sale=sale,fee_cents=-1,customer_confirmed=True),dict(sale=999,fee_cents=700,customer_confirmed=True)]:self.assertEqual(self.post('delivery_quote',data).status_code,400)
  pickup=self.post('order',dict(self.order(),request_id='pickup-order-unique-1234'));self.assertFalse(pickup.json['delivery_estimated'])
  self.assertEqual(self.post('delivery_quote',dict(sale=pickup.json['sale'],fee_cents=700,customer_confirmed=True)).status_code,400)
  self.post('logout',{});self.assertEqual(self.post('delivery_quote',dict(sale=sale,fee_cents=700,customer_confirmed=True)).status_code,401)
if __name__=='__main__':unittest.main()

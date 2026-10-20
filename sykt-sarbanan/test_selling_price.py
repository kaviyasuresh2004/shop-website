import unittest
import app,test_server
class SellingPriceTests(unittest.TestCase):
 setUp=test_server.ServerTests.setUp
 tearDown=test_server.ServerTests.tearDown
 login=test_server.ServerTests.login
 post=test_server.ServerTests.post
 def test_worker_price_only_update_and_customer_denied(self):
  self.assertEqual(self.post('product-price',dict(product=1,price=1250)).status_code,401)
  self.login();self.post('user',dict(name='worker',password='Worker888'));self.post('logout',{});self.post('login',dict(name='worker',password='Worker888'))
  with app.connect() as c:
   c.execute("INSERT INTO product_gallery VALUES (1,'test-existing-photo',?,0)",(b'existing-photo-bytes',))
   before=dict(c.execute('SELECT * FROM products WHERE id=1').fetchone());stock=[tuple(r) for r in c.execute('SELECT * FROM stock')];photos=[tuple(r) for r in c.execute('SELECT * FROM product_gallery')]
  self.assertEqual(self.post('product-price',dict(product=1,price=1250)).status_code,200)
  with app.connect() as c:
   after=dict(c.execute('SELECT * FROM products WHERE id=1').fetchone());self.assertEqual(after,{**before,'price':1250});self.assertEqual(stock,[tuple(r) for r in c.execute('SELECT * FROM stock')]);self.assertEqual(photos,[tuple(r) for r in c.execute('SELECT * FROM product_gallery')]);self.assertIn('previous_price',c.execute("SELECT detail FROM audit WHERE action='selling price updated'").fetchone()[0])
  for value in [-1,1.5,True,100000001]:self.assertEqual(self.post('product-price',dict(product=1,price=value)).status_code,400)
  self.assertEqual(self.post('product-price',dict(product=999999,price=100)).status_code,400)
if __name__=='__main__':unittest.main()

import unittest
import app,server,categorisation,test_accounts

class CategoryTests(unittest.TestCase):
 setUp=test_accounts.AccountsTests.setUp
 tearDown=test_accounts.AccountsTests.tearDown
 def test_clear_and_ambiguous_names(self):
  for name,category in [('PVC pipe 20mm','Plumbing'),('PIPE WRENCH 12 inch','Hand tools'),('SELF DRILLING SCREW','Fasteners'),('HAMMER DRILL 20V','Power tools'),('LED BULB 10W','Electrical'),('PAINT BRUSH 2 inch','Paint'),('ROOFING SHEET','Building materials'),('SAFETY HELMET','Safety Equipment'),('AIRCON R410A','AC & Refrigeration'),('SOCKET 20MM',None),('000000',None)]:
   self.assertEqual(categorisation.suggest(name),category,name)
 def login(self):self.assertEqual(self.client.post('/api/setup',json={'name':'admin','password':'test-password'}).status_code,200)
 def test_bulk_preserves_manual_categories_prices_stock_and_shop_identity(self):
  self.login()
  with app.connect() as c:
   c.execute("UPDATE products SET category='Uncategorised' WHERE id=1")
   before=[tuple(r) for r in c.execute('SELECT id,price FROM products')];stock=[tuple(r) for r in c.execute('SELECT * FROM stock')]
  payload={'shop':app.CONFIG['slug']};preview=self.client.post('/api/categorise',json=payload).json
  self.assertEqual(preview['count'],1)
  self.assertEqual(self.client.post('/api/categorise',json={**payload,'shop':'another-shop'}).status_code,400)
  self.assertEqual(self.client.post('/api/categorise',json={**payload,'apply':True,'digest':'stale'}).status_code,400)
  self.assertEqual(self.client.post('/api/categorise',json={**payload,'apply':True,'digest':preview['digest']}).status_code,200)
  with app.connect() as c:
   self.assertEqual(c.execute('SELECT category FROM products WHERE id=1').fetchone()[0],'Power tools')
   self.assertEqual([tuple(r) for r in c.execute('SELECT id,price FROM products')],before)
   self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM stock')],stock)
  self.assertEqual(self.client.post('/api/categorise',json=payload).json['count'],0)
 def test_permissions_and_category_only_edit(self):
  self.assertEqual(self.client.post('/api/product-category',json={'product':1,'category':'Plumbing'}).status_code,401)
  self.login();self.client.post('/api/user',json={'name':'worker','password':'worker-password','company':1})
  self.client.post('/api/logout',json={});self.client.post('/api/login',json={'name':'worker','password':'worker-password'})
  self.assertEqual(self.client.post('/api/categorise',json={'shop':app.CONFIG['slug']}).status_code,403)
  self.assertEqual(self.client.post('/api/product-category',json={'product':1,'category':'Plumbing','price':0,'qty':0}).status_code,200)
  with app.connect() as c:self.assertEqual(c.execute('SELECT price FROM products WHERE id=1').fetchone()[0],8900)
  self.assertEqual(self.client.post('/api/product-category',json={'product':1,'category':'invalid'}).status_code,400)
 def test_registered_details_are_separate_and_preserved(self):
  self.login()
  with app.connect() as c:settings=app.commerce.load(c)
  settings.update(legal_name='Registered company',registered_address='Registered office',incorporation_date='03-May-2014')
  self.assertEqual(self.client.post('/api/shop-settings',json=settings).status_code,200)
  public=self.client.get('/api/catalog').json['shopDetails'];self.assertEqual(public['registered_address'],'Registered office');self.assertEqual(public['address'],'');self.assertFalse(public['checkout_enabled'])
  del settings['legal_name'];del settings['registered_address'];del settings['incorporation_date']
  self.client.post('/api/shop-settings',json=settings)
  self.assertEqual(self.client.get('/api/catalog').json['shopDetails']['legal_name'],'Registered company')

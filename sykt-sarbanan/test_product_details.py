import hashlib,unittest
import app,server,test_server

class ProductDetailsTests(unittest.TestCase):
 setUp=test_server.ServerTests.setUp
 tearDown=test_server.ServerTests.tearDown
 login=test_server.ServerTests.login
 post=test_server.ServerTests.post
 def test_authenticated_edit_public_roundtrip_validation_and_audit(self):
  payload=dict(product=1,brand='Test brand',description_en='Line one\nLine two',description_ms='Penerangan',specifications_en='<script>plain text</script>',model='M-1',dimensions='25 mm')
  self.assertEqual(self.post('product-details',payload).status_code,401)
  self.login();self.post('user',dict(name='worker',password='Worker888'));self.post('logout',{});self.post('login',dict(name='worker',password='Worker888'))
  with app.connect() as c:
   stock=[tuple(r) for r in c.execute('SELECT * FROM stock')];products=[tuple(r) for r in c.execute('SELECT * FROM products')]
  self.assertEqual(self.post('product-details',payload).status_code,200)
  server.initialize()
  product=next(p for p in self.client.get('/api/catalog').json['products'] if p['id']==1)
  for key in ('brand','description_en','description_ms','specifications_en','model','dimensions'):self.assertEqual(product[key],payload[key])
  with app.connect() as c:
   self.assertEqual(stock,[tuple(r) for r in c.execute('SELECT * FROM stock')]);self.assertEqual(products,[tuple(r) for r in c.execute('SELECT * FROM products')]);self.assertTrue(c.execute("SELECT 1 FROM audit WHERE action='product details updated' AND actor='worker'").fetchone())
  for bad in (dict(payload,product=999999),dict(payload,brand='x'*161),dict(payload,description_en=12),dict(payload,product=True)):
   self.assertEqual(self.post('product-details',bad).status_code,400)
  self.assertEqual(next(p for p in self.client.get('/api/catalog').json['products'] if p['id']==1)['brand'],'Test brand')
  self.assertEqual(self.post('product-details',dict(product=1)).status_code,200)
  self.assertEqual(next(p for p in self.client.get('/api/catalog').json['products'] if p['id']==1)['brand'],'')
 def test_details_survive_catalogue_reimport(self):
  self.login();source='Test imported screw';sku='BMK-TALLY-'+hashlib.sha256(source.encode()).hexdigest()[:16].upper()
  item=dict(name=source,source_name=source,sku=sku,price_cents=350,quantity=10,source_quantity='10',unit='pcs',hold=False)
  payload=dict(shop=app.CONFIG['slug'],source_company=app.CONFIG['name'],location='Main Location',source_sha256='a'*64,items=[item])
  # This fixture uses the BMK import prefix; other shops use their own prefix.
  if app.CONFIG['slug']!='bmk-arvin':item['sku']='SYKT-TALLY-'+hashlib.sha256(source.encode()).hexdigest()[:16].upper()
  self.assertEqual(self.post('catalogue-import',payload).status_code,200)
  with app.connect() as c:pid=c.execute('SELECT id FROM products WHERE sku=?',(item['sku'],)).fetchone()[0]
  self.assertEqual(self.post('product-details',dict(product=pid,brand='Saved brand',description_en='Saved copy')).status_code,200)
  item['quantity']=12;self.assertEqual(self.post('catalogue-import',payload).status_code,200)
  product=next(p for p in self.client.get('/api/catalog').json['products'] if p['id']==pid)
  self.assertEqual(product['description_en'],'Saved copy');self.assertEqual(product['brand'],'Saved brand')

if __name__=='__main__':unittest.main()

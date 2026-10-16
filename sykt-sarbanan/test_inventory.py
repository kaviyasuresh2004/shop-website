import copy,hashlib,json,unittest
from pathlib import Path
import app,test_server

class InventoryTests(unittest.TestCase):
 setUp=test_server.ServerTests.setUp
 tearDown=test_server.ServerTests.tearDown
 login=test_server.ServerTests.login
 post=test_server.ServerTests.post
 def payload(self):
  items=[]
  for name,qty,price,raw,hold in [('Ready',4,100,'4',False),('Negative',0,100,'-3',False),('No price',2,0,'2',False),('Fractional',0,60,'16.5',True)]:
   items.append(dict(name=name,source_name=name,sku='SYKT-TALLY-'+hashlib.sha256(name.encode()).hexdigest()[:16].upper(),quantity=qty,price_cents=price,source_quantity=raw,hold=hold,unit='NOS'))
  return dict(shop=app.CONFIG['slug'],source_company='SYKT PG. SARBANUN SDN BHD',location='Main Location',source_sha256='a'*64,items=items)
 def test_import_permissions_visibility_restock_idempotency_and_rollback(self):
  d=self.payload();self.assertEqual(self.post('catalogue-import',d).status_code,401);self.login()
  self.assertEqual(self.post('catalogue-import',dict(d,shop='other')).status_code,400)
  self.assertEqual(self.post('catalogue-import',dict(d,source_company='BMK ARVIN SDN BHD')).status_code,400)
  wrong=copy.deepcopy(d);wrong['items'][0]['sku']=wrong['items'][0]['sku'].replace('SYKT-TALLY-','BMK-TALLY-')
  self.assertEqual(self.post('catalogue-import',wrong).status_code,400)
  r=self.post('catalogue-import',d);self.assertEqual(r.status_code,200);self.assertEqual(r.json['imported'],4);self.assertEqual(r.json['visible'],1)
  products=self.client.get('/api/catalog?staff=1').json['products'];ids={p['name']:p['id'] for p in products}
  self.post('adjust',dict(product=ids['Negative'],delta=3,reason='restocked'))
  self.assertEqual(self.post('catalogue-import',d).json,r.json)
  with app.connect() as c:self.assertEqual(c.execute('SELECT qty FROM stock WHERE id=?',(ids['Negative'],)).fetchone()[0],3)
  self.post('logout',{});public=self.client.get('/api/catalog').json['products'];self.assertEqual({p['name'] for p in public},{'Ready','Negative'})
  order=dict(phone='123',request_id='hidden-product-order-1234',items=[dict(product=ids['No price'],qty=1)])
  self.assertEqual(self.post('order',order).status_code,400)
  self.post('login',dict(name='admin',password='test-password-123'));bad=copy.deepcopy(d);bad['items'][0]['quantity']=99;bad['items'][-1]['price_cents']=-1
  self.assertEqual(self.post('catalogue-import',bad).status_code,400)
  with app.connect() as c:self.assertEqual(c.execute('SELECT qty FROM stock WHERE id=?',(ids['Ready'],)).fetchone()[0],4)
  self.post('user',dict(name='worker',password='Worker123'));self.post('logout',{});self.post('login',dict(name='worker',password='Worker123'))
  self.assertEqual(self.post('catalogue-import',d).status_code,403)

if __name__=='__main__':unittest.main()

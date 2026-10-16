import base64,io,unittest
from PIL import Image
import app,server,test_accounts

class PhotoTests(unittest.TestCase):
 setUp=test_accounts.AccountsTests.setUp
 tearDown=test_accounts.AccountsTests.tearDown
 def payload(self,color='red'):
  output=io.BytesIO();Image.new('RGB',(30,20),color).save(output,'PNG')
  return {'product':1,'image':base64.b64encode(output.getvalue()).decode()}
 def login(self):
  self.assertEqual(self.client.post('/api/setup',json={'name':'admin','password':'test-password'}).status_code,200)
 def test_customer_cannot_upload(self):
  self.assertEqual(self.client.post('/api/product-photo',json=self.payload()).status_code,401)
  test_accounts.AccountsTests.register(self,self.client)
  self.assertEqual(self.client.post('/api/product-photo',json=self.payload()).status_code,401)
 def test_worker_upload_public_view_replacement_and_persistence(self):
  self.login();self.client.post('/api/user',json={'name':'worker','password':'worker-password','company':1})
  self.client.post('/api/logout',json={});self.assertEqual(self.client.post('/api/login',json={'name':'worker','password':'worker-password'}).status_code,200)
  result=self.client.post('/api/product-photo',json=self.payload());self.assertEqual(result.status_code,200)
  url=result.json['photo_url'];server.initialize()
  public=server.web.test_client();response=public.get(url);self.assertEqual(response.status_code,200);self.assertEqual(response.mimetype,'image/jpeg')
  self.assertEqual(Image.open(io.BytesIO(response.data)).size,(30,20))
  self.assertEqual(next(p for p in public.get('/api/catalog').json['products'] if p['id']==1)['photo_url'],url)
  replacement=self.client.post('/api/product-photo',json=self.payload('blue'));self.assertNotEqual(replacement.json['photo_url'],url)
  self.assertEqual(public.get(url).status_code,404)
 def test_reject_invalid_files_product_and_cross_origin(self):
  self.login()
  for payload in [{'product':1,'image':'not base64'},{'product':1,'image':base64.b64encode(b'<svg/>').decode()},{**self.payload(),'product':999999}]:
   self.assertEqual(self.client.post('/api/product-photo',json=payload).status_code,400)
  self.assertEqual(self.client.post('/api/product-photo',json=self.payload(),headers={'Origin':'https://evil.example'}).status_code,403)

 def test_gallery_limit_duplicates_cover_remove_and_other_product(self):
  self.login();urls=[]
  for color in ['red','blue','green','black','white','yellow']:
   result=self.client.post('/api/product-photo',json={**self.payload(color),'action':'add'})
   self.assertEqual(result.status_code,200);urls.append(result.json['photo_url'])
  self.assertEqual(self.client.post('/api/product-photo',json={**self.payload('red'),'action':'add'}).status_code,200)
  self.assertEqual(self.client.post('/api/product-photo',json={**self.payload('purple'),'action':'add'}).status_code,400)
  def gallery():return next(p for p in self.client.get('/api/catalog').json['products'] if p['id']==1)
  self.assertEqual(gallery()['photo_urls'],urls)
  digest=urls[-1].split('/')[-1][:-4]
  self.assertEqual(self.client.post('/api/product-photo',json={'product':2,'action':'remove','digest':digest}).status_code,400)
  self.assertEqual(self.client.post('/api/product-photo',json={'product':1,'action':'cover','digest':digest}).status_code,200)
  self.assertEqual(gallery()['photo_url'],urls[-1])
  self.assertEqual(self.client.post('/api/product-photo',json={'product':1,'action':'remove','digest':digest}).status_code,200)
  self.assertEqual(len(gallery()['photo_urls']),5)
  self.assertEqual(self.client.get(urls[-1]).status_code,404)
  self.assertEqual(self.client.post('/api/product-photo',json={**self.payload('purple'),'action':'add'}).status_code,200)
 def test_existing_photo_migration_is_preserved_once(self):
  self.login()
  result=self.client.post('/api/product-photo',json=self.payload());url=result.json['photo_url']
  with app.connect() as c:
   row=c.execute('SELECT product,digest,image FROM product_gallery').fetchone()
   c.execute('CREATE TABLE product_photos(product INTEGER PRIMARY KEY,digest TEXT,image BLOB)')
   c.execute('INSERT INTO product_photos VALUES (?,?,?)',tuple(row))
   c.execute('DELETE FROM product_gallery')
  server.initialize();self.assertEqual(self.client.get(url).status_code,200)
  self.client.post('/api/product-photo',json={'product':1,'action':'remove','digest':row['digest']})
  server.initialize();self.assertEqual(self.client.get(url).status_code,404)

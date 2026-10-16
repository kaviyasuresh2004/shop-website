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

import base64,io,unittest
from PIL import Image
import app,server,test_accounts

class CompanyControlsTests(unittest.TestCase):
 setUp=test_accounts.AccountsTests.setUp
 tearDown=test_accounts.AccountsTests.tearDown
 def logo(self,color='blue'):
  output=io.BytesIO();Image.new('RGB',(60,40),color).save(output,'PNG')
  return {'image':base64.b64encode(output.getvalue()).decode()}
 def setup_roles(self):
  self.admin=self.client
  self.admin.post('/api/setup',json={'name':'admin','password':'test-password'})
  self.admin.post('/api/user',json={'name':'worker','password':'worker-password','company':1})
  self.worker=server.web.test_client();self.worker.post('/api/login',json={'name':'worker','password':'worker-password'})
 def test_parallel_sessions_do_not_share_administrator_access(self):
  self.setup_roles()
  self.assertEqual(self.admin.get('/api/staff').json['user']['role'],'admin')
  self.assertEqual(self.worker.get('/api/staff').json['user']['role'],'worker')
  with app.connect() as c:settings=app.commerce.load(c)
  settings.update(email='shop@example.test',registration_number='RC123',company_description='About this shop',whatsapp='+6731234567',facebook_url='https://www.facebook.com/example',instagram_url='https://www.instagram.com/example')
  self.assertEqual(self.admin.post('/api/shop-settings',json=settings).status_code,200)
  self.assertEqual(self.worker.post('/api/shop-settings',json={**settings,'role':'admin'}).status_code,403)
  self.assertEqual(self.worker.post('/api/company-logo',json={**self.logo(),'role':'admin'}).status_code,403)
  self.assertEqual(self.worker.get('/api/inventory-audit').status_code,403)
  self.assertEqual(self.worker.get('/api/staff').json['accounts'],[])
  self.assertEqual(self.admin.get('/api/staff').json['user']['role'],'admin')
  self.admin.post('/api/logout',json={})
  self.assertEqual(self.worker.get('/api/staff').json['user']['role'],'worker')
 def test_logo_persistent_public_replacement_and_upload_validation(self):
  self.assertEqual(self.client.post('/api/company-logo',json=self.logo()).status_code,401)
  self.setup_roles()
  self.assertEqual(self.admin.post('/api/company-logo',json=self.logo()).status_code,200)
  public=server.web.test_client();url=public.get('/api/catalog').json['logo_url'];self.assertTrue(url.startswith('/company-logo/'))
  server.initialize();self.assertEqual(public.get(url).mimetype,'image/jpeg')
  self.assertEqual(Image.open(io.BytesIO(public.get(url).data)).size,(60,40))
  self.assertEqual(self.admin.post('/api/company-logo',json=self.logo('red')).status_code,200)
  self.assertNotEqual(public.get('/api/catalog').json['logo_url'],url)
  self.assertEqual(self.admin.post('/api/company-logo',json={'image':base64.b64encode(b'<svg/>').decode()}).status_code,400)
 def test_company_links_validation_and_existing_fields_preserved(self):
  self.setup_roles()
  with app.connect() as c:settings=app.commerce.load(c)
  for fields in [{'email':'bad email@example.test'},{'facebook_url':'javascript:alert(1)'},{'instagram_url':'https://user:secret@example.test'}]:
   self.assertEqual(self.admin.post('/api/shop-settings',json={**settings,**fields}).status_code,400)
  self.assertEqual(self.admin.post('/api/shop-settings',json={**settings,'registration_number':'RC123','email':'shop@example.test'}).status_code,200)
  self.assertEqual(self.admin.post('/api/shop-settings',json=settings).status_code,200)
  self.assertEqual(self.admin.get('/api/catalog').json['products'][0]['price'],8900)

import http.client,json,tempfile,threading,unittest
from pathlib import Path
import app
class HTTPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();app.DB=Path(self.tmp.name)/'http.db';app.SESSIONS.clear();app.init()
  self.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self): self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def request(self,path,data=None,cookie=None):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port);headers={'Content-Type':'application/json'}
  if cookie:headers['Cookie']=cookie
  c.request('POST' if data is not None else 'GET',path,None if data is None else json.dumps(data),headers);r=c.getresponse();raw=r.read();result=(r.status,r.getheader('Set-Cookie'),raw);c.close();return result
 def test_checkout_and_private_staff(self):
  self.assertEqual(self.request('/api/staff')[0],401)
  status,_,raw=self.request('/api/order',{'customer':'Test','phone':'test','company':2,'items':[{'product':1,'qty':1}]});self.assertEqual(status,400)
  status,_,raw=self.request('/api/order',{'customer':'Test','phone':'test','items':[{'product':1,'qty':1}]});self.assertEqual(status,200);self.assertEqual(json.loads(raw)['total'],8900)
 def test_cookie_namespace_and_staff_endpoints(self):
  status,cookie,_=self.request('/api/setup',{'name':'test-admin','password':'test-only-password'});self.assertEqual(status,200);self.assertTrue(cookie.startswith(app.COOKIE+'='))
  self.assertEqual(self.request('/api/staff',cookie=cookie)[0],200)
  self.assertEqual(self.request('/api/staff',cookie=cookie.replace(app.COOKIE,'session_other-shop'))[0],401)
  self.assertEqual(self.request('/api/transfer',{'company':1,'product':1,'qty':1},cookie)[0],400)
 def test_pages_and_brand(self):
  for path in ('/','/staff','/assets/site.js','/assets/en.json','/assets/ms.json'):
   self.assertEqual(self.request(path)[0],200)
if __name__=='__main__':unittest.main()

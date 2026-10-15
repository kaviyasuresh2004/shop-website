import unittest
import test_server

class WorkerFlowTests(unittest.TestCase):
 setUp=test_server.ServerTests.setUp
 tearDown=test_server.ServerTests.tearDown
 login=test_server.ServerTests.login
 post=test_server.ServerTests.post
 order=test_server.ServerTests.order
 qty=test_server.ServerTests.qty
 def test_worker_roster_reset_and_signin(self):
  self.login()
  result=self.post('user',{'name':' BMK-ARVIN ','password':'worker-first-password-123'})
  self.assertEqual(result.status_code,200);self.assertEqual(result.json['name'],'BMK-ARVIN')
  roster=self.client.get('/api/staff').json['accounts']
  self.assertEqual({r['name'] for r in roster},{'admin','BMK-ARVIN'})
  for account in roster:self.assertEqual(set(account),{'name','role','company'})
  self.assertEqual(self.post('user',{'name':'bmk-arvin','password':'worker-other-password-123'}).status_code,400)
  worker=self.client.application.test_client()
  self.assertEqual(worker.post('/api/login',json={'name':'bmk-arvin','password':'worker-first-password-123'}).status_code,200)
  self.assertEqual(worker.get('/api/staff').json['accounts'],[])
  self.assertEqual(self.post('manage_user',{'name':' bmk-arvin ','password':'worker-new-password-123','action':'reset'}).status_code,200)
  self.assertEqual(worker.get('/api/staff').status_code,401)
  self.assertEqual(worker.post('/api/login',json={'name':'BMK-ARVIN','password':'worker-first-password-123'}).status_code,401)
  self.assertEqual(worker.post('/api/login',json={'name':'bmk-arvin','password':'worker-new-password-123'}).status_code,200)
  self.assertEqual(self.post('manage_user',{'name':'bmk-arvin','password':'','action':'reset'}).status_code,400)
  self.assertEqual(worker.get('/api/staff').status_code,200)
 def test_delivered_counts_once_without_second_stock_deduction(self):
  result=self.post('order',self.order()).json;self.login()
  self.assertEqual(self.qty(),28)
  self.assertEqual(self.post('order_status',{'sale':result['sale'],'status':'delivered'}).status_code,200)
  report=self.client.get('/api/staff').json['report'];self.assertEqual(report['sales'],1);self.assertEqual(report['total'],17800);self.assertEqual(report['pending_orders'],0)
  self.post('order_status',{'sale':result['sale'],'status':'completed'})
  report=self.client.get('/api/staff').json['report'];self.assertEqual(report['sales'],1);self.assertEqual(report['total'],17800);self.assertEqual(self.qty(),28)

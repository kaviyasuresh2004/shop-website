import unittest
from unittest.mock import patch
import app,server,test_accounts

class InventoryAuditTests(unittest.TestCase):
 setUp=test_accounts.AccountsTests.setUp
 tearDown=test_accounts.AccountsTests.tearDown
 def test_export_is_admin_only_and_contains_no_customer_or_credentials(self):
  self.assertEqual(self.client.get('/api/inventory-audit').status_code,401)
  self.client.post('/api/setup',json={'name':'admin','password':'test-password'})
  response=self.client.get('/api/inventory-audit');self.assertEqual(response.status_code,200)
  self.assertEqual(response.json['shop'],app.CONFIG['slug']);self.assertEqual(len(response.json['products']),6)
  self.assertEqual(response.headers['Cache-Control'],'no-store');self.assertIn('attachment',response.headers['Content-Disposition'])
  for key in ['users','sessions','customers','orders','sales']:self.assertNotIn(key,response.json)
  self.client.post('/api/user',json={'name':'worker','password':'worker-password','company':1})
  self.client.post('/api/logout',json={});self.client.post('/api/login',json={'name':'worker','password':'worker-password'})
  self.assertEqual(self.client.get('/api/inventory-audit').status_code,403)
 def test_explicit_legal_name_migration_preserves_inventory(self):
  with app.connect() as c:
   c.execute("UPDATE companies SET name='SYKT SARBANAN SDN BHD' WHERE id=1")
   products=[tuple(r) for r in c.execute('SELECT * FROM products')];stock=[tuple(r) for r in c.execute('SELECT * FROM stock')]
  with patch.dict(app.CONFIG,slug='sykt-sarbanan',name='SYKT PG. SARBANUN SDN BHD'):
   app.init();app.init()
   with app.connect() as c:
    self.assertEqual(c.execute('SELECT name FROM companies').fetchone()[0],app.CONFIG['name'])
    self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM products')],products)
    self.assertEqual([tuple(r) for r in c.execute('SELECT * FROM stock')],stock)
    self.assertEqual(c.execute("SELECT COUNT(*) FROM audit WHERE action='company name corrected'").fetchone()[0],1)
    c.execute("UPDATE companies SET name='BMK ARVIN SDN BHD' WHERE id=1")
   with self.assertRaises(ValueError):app.init()

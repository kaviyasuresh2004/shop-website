import tempfile,unittest,sqlite3
from pathlib import Path
import app
class IsolationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.a=Path(self.tmp.name)/'bmk.db'; self.b=Path(self.tmp.name)/'sarbanan.db'
  for db in (self.a,self.b): app.DB=db; app.init()
  app.DB=self.a; self.admin={'name':'admin','role':'admin','company':1}; self.worker={'name':'worker','role':'worker','company':1}
 def tearDown(self): self.tmp.cleanup()
 def quantity(self,db):
  app.DB=db
  with app.connect() as c: return c.execute('SELECT qty FROM stock WHERE id=1').fetchone()[0]
 def test_separate_inventory_prices_accounts(self):
  app.operation(self.worker,'adjust',{'product':1,'delta':-2,'reason':'count'})
  app.operation(self.worker,'product',{'id':1,'sku':'DRILL-001','name':'Drill','category':'Power tools','price':100})
  app.operation(self.admin,'user',{'name':'only-bmk','password':'test-password-123'})
  self.assertEqual(self.quantity(self.a),28); self.assertEqual(self.quantity(self.b),30)
  with app.connect() as c:
   self.assertEqual(c.execute('SELECT price FROM products WHERE id=1').fetchone()[0],8900)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],0)
 def test_no_company_switch_or_transfer(self):
  for actor in (self.admin,self.worker):
   with self.assertRaises(ValueError): app.operation(actor,'adjust',{'company':2,'product':1,'delta':1,'reason':'bad'})
   with self.assertRaises(ValueError): app.operation(actor,'transfer',{'product':1,'qty':1,'reason':'bad'})
 def test_worker_permissions(self):
  app.operation(self.worker,'product',{'sku':'NEW','name':'New','category':'Hand tools','price':120})
  with self.assertRaises(ValueError): app.operation(self.worker,'delete_product',{'product':1})
  with self.assertRaises(ValueError): app.operation(self.worker,'user',{'name':'bad','password':'test-password-123'})
 def test_order_atomic_and_report_details(self):
  with self.assertRaises(ValueError): app.operation(self.worker,'order',{'customer':'Test','items':[{'product':1,'qty':1},{'product':2,'qty':999}]})
  self.assertEqual(self.quantity(self.a),30)
  result=app.operation(self.worker,'order',{'customer':'Test','phone':'test','items':[{'product':1,'qty':2}]})
  self.assertEqual(self.quantity(self.a),28)
  app.operation(self.worker,'order_status',{'sale':result['sale'],'status':'processing'})
  with app.connect() as c:
   self.assertEqual(c.execute('SELECT status FROM order_details').fetchone()[0],'processing')
   with self.assertRaises(sqlite3.IntegrityError): c.execute('DELETE FROM sales')
 def test_import_atomic_and_local(self):
  with self.assertRaises(ValueError): app.operation(self.admin,'import',{'csv':'SKU,Quantity\nDRILL-001,3\nUNKNOWN,1','reason':'Tally snapshot'})
  self.assertEqual(self.quantity(self.a),30)
  app.operation(self.admin,'import',{'csv':'SKU,Quantity\nDRILL-001,3','reason':'Tally snapshot'})
  self.assertEqual(self.quantity(self.a),3);self.assertEqual(self.quantity(self.b),30)
 def test_database_identity_guard(self):
  with app.connect() as c: c.execute("INSERT INTO companies VALUES (2,'Other business')")
  with self.assertRaises(ValueError): app.init()
 def test_offline_migration_filters_company(self):
  import migrate_legacy
  with app.connect() as c:
   c.execute("INSERT INTO companies VALUES (2,'Legacy second company')")
   c.execute('INSERT INTO stock VALUES (2,1,7)')
  source=self.a;app.DB=Path(self.tmp.name)/'migrated.db'
  migrate_legacy.migrate(source,2)
  with app.connect() as c:
   self.assertEqual(c.execute('SELECT COUNT(*) FROM companies').fetchone()[0],1)
   self.assertEqual(c.execute('SELECT qty FROM stock WHERE id=1').fetchone()[0],7)
   self.assertEqual(c.execute('SELECT COUNT(*) FROM products').fetchone()[0],1)
  with self.assertRaises(ValueError): migrate_legacy.migrate(source,2)
if __name__=='__main__': unittest.main()

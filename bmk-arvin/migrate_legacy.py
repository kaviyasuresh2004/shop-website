"""Offline migration. Stop both servers and back up first. Never overwrites a database."""
import argparse,sqlite3
from pathlib import Path
import app
def migrate(source,company):
 if app.DB.exists(): raise ValueError('Destination database already exists; refusing to overwrite')
 source=Path(source).resolve()
 if not source.is_file(): raise ValueError('Legacy database not found')
 old=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);old.row_factory=sqlite3.Row
 if not old.execute('SELECT 1 FROM companies WHERE id=?',(company,)).fetchone(): raise ValueError('Source company not found')
 app.init()
 with app.connect() as c:
  c.execute('DELETE FROM stock');c.execute('DELETE FROM products')
  for row in old.execute('SELECT p.* FROM products p JOIN stock s ON s.id=p.id WHERE s.company=?',(company,)):
   c.execute('INSERT INTO products VALUES (?,?,?,?,?)',tuple(row))
  for row in old.execute('SELECT id,qty FROM stock WHERE company=?',(company,)): c.execute('INSERT INTO stock VALUES (1,?,?)',tuple(row))
  for row in old.execute('SELECT * FROM sales WHERE company=?',(company,)):
   d=dict(row);d['company']=1
   keys=list(d);c.execute('INSERT INTO sales('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',list(d.values()))
   c.execute("INSERT INTO order_details VALUES (?,'shop','','','pickup','completed')",(row['id'],))
  for row in old.execute('SELECT * FROM promotions WHERE company=?',(company,)):
   d=dict(row);d['company']=1;keys=list(d)
   c.execute('INSERT INTO promotions('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',list(d.values()))
  # No credentials or mixed-company audit records are copied.
  app.audit(c,'migration','legacy company imported',{'source_company':company,'source':str(source),'pricing':'copied from legacy shared catalogue; review independently'})
 old.close()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('--company',type=int,choices=(1,2),required=True);args=parser.parse_args();migrate(args.source,args.company)

"""Delivery estimates and agreed fees, without rewriting immutable sale items."""
def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS delivery_confirmations(sale INTEGER PRIMARY KEY REFERENCES sales(id),fee INTEGER CHECK(fee>=0),confirmed_at TEXT)')

def pending(c,sale):
 return bool(c.execute('SELECT 1 FROM delivery_confirmations WHERE sale=? AND fee IS NULL',(sale,)).fetchone())

def adjust(c,rows,key='id'):
 quotes={r['sale']:dict(r) for r in c.execute('SELECT * FROM delivery_confirmations')}
 original={r['id']:r['delivery'] for r in c.execute('SELECT id,delivery FROM sales')}
 for row in rows:
  quote=quotes.get(row[key]);row['delivery_pending']=bool(quote and quote['fee'] is None)
  if quote:
   row['delivery_fee']=quote['fee']
   if quote['fee'] is not None and 'total' in row:
    row['total']+=quote['fee']-original[row[key]];row['delivery']=quote['fee']
 return rows

def confirm(domain,c,user,d):
 sale=domain.integer(d['sale']);fee=domain.integer(d['fee_cents'])
 if d.get('customer_confirmed') is not True or not 0<=fee<=1000000:raise ValueError('Confirm delivery charge with customer')
 row=c.execute("SELECT d.status,p.status AS payment,q.fee FROM delivery_confirmations q JOIN order_details d ON d.sale=q.sale LEFT JOIN order_payments p ON p.sale=q.sale WHERE q.sale=?",(sale,)).fetchone()
 if not row or row['status'] in ('ready','delivered','completed') or row['payment']=='paid':raise ValueError('Delivery charge cannot be changed')
 c.execute('UPDATE delivery_confirmations SET fee=?,confirmed_at=CURRENT_TIMESTAMP WHERE sale=?',(fee,sale))
 domain.audit(c,user['name'],'delivery charge confirmed',{'sale':sale,'previous_fee':row['fee'],'fee':fee,'customer_confirmed':True})
 return {'ok':True}

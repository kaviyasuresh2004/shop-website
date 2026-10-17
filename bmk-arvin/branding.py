"""Company logo managed only by the administrator, in this shop's own database."""
import hashlib
import photos

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS company_logo(id INTEGER PRIMARY KEY CHECK(id=1),digest TEXT NOT NULL,image BLOB NOT NULL)')

def url(c):
 row=c.execute('SELECT digest FROM company_logo WHERE id=1').fetchone()
 return '/company-logo/'+row['digest']+'.jpg' if row else ''

def save(domain,user,d):
 if user['role']!='admin':raise ValueError('Administrator access required')
 content=photos.normalise(d['image']);digest=hashlib.sha256(content).hexdigest()
 with domain.LOCK,domain.connect() as c:
  c.execute('INSERT INTO company_logo VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET digest=excluded.digest,image=excluded.image',(digest,content))
  domain.audit(c,user['name'],'company logo updated',{})
 return {'ok':True}

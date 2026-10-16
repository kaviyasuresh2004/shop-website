"""Validated product photos stored alongside each shop's persistent inventory."""
import base64, binascii, hashlib, io, warnings
from PIL import Image, ImageOps, UnidentifiedImageError

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS product_gallery(product INTEGER REFERENCES products(id) ON DELETE CASCADE,digest TEXT NOT NULL,image BLOB NOT NULL,position INTEGER NOT NULL,PRIMARY KEY(product,digest))')
 if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_photos'").fetchone():
  c.execute('INSERT OR IGNORE INTO product_gallery SELECT product,digest,image,0 FROM product_photos')
  c.execute('DROP TABLE product_photos')

def save(domain,user,d):
 if user['role'] not in ('worker','admin'): raise ValueError('Staff access required')
 product=int(d['product'])
 action=d.get('action','replace')
 if action in ('remove','cover'):
  with domain.LOCK,domain.connect() as c:
   digest=d.get('digest','')
   if not c.execute('SELECT 1 FROM product_gallery WHERE product=? AND digest=?',(product,digest)).fetchone():raise ValueError('Unknown photo')
   if action=='remove':c.execute('DELETE FROM product_gallery WHERE product=? AND digest=?',(product,digest))
   else:
    ordered=[r['digest'] for r in c.execute('SELECT digest FROM product_gallery WHERE product=? ORDER BY position,digest',(product,))]
    ordered.remove(digest);ordered.insert(0,digest)
    for index,value in enumerate(ordered):c.execute('UPDATE product_gallery SET position=? WHERE product=? AND digest=?',(index,product,value))
   domain.audit(c,user['name'],'product photo '+action,{'product':product})
  return {'ok':True}
 if action not in ('add','replace'):raise ValueError('Invalid photo action')
 encoded=d['image']
 if not isinstance(encoded,str) or len(encoded)>7_000_000: raise ValueError('Photo too large')
 try:
  raw=base64.b64decode(encoded,validate=True)
  if not raw or len(raw)>5_000_000: raise ValueError('Photo too large')
  with warnings.catch_warnings():
   warnings.simplefilter('error',Image.DecompressionBombWarning)
   with Image.open(io.BytesIO(raw)) as source:
    if source.format not in ('JPEG','PNG','WEBP') or source.width*source.height>12_000_000: raise ValueError('Unsupported photo')
    source.load()
    image=ImageOps.exif_transpose(source).convert('RGBA')
    image.thumbnail((1600,1600))
    background=Image.new('RGB',image.size,'white');background.paste(image,mask=image.getchannel('A'))
    output=io.BytesIO();background.save(output,format='JPEG',quality=85,optimize=True)
    content=output.getvalue()
 except (binascii.Error,UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:
  raise ValueError('Invalid photo') from exc
 digest=hashlib.sha256(content).hexdigest()
 with domain.LOCK,domain.connect() as c:
  if not c.execute('SELECT 1 FROM products WHERE id=?',(product,)).fetchone(): raise ValueError('Unknown product')
  exists=c.execute('SELECT 1 FROM product_gallery WHERE product=? AND digest=?',(product,digest)).fetchone()
  if action=='replace':c.execute('DELETE FROM product_gallery WHERE product=?',(product,))
  count=c.execute('SELECT COUNT(*) FROM product_gallery WHERE product=?',(product,)).fetchone()[0]
  if action=='add' and not exists and count>=6:raise ValueError('Maximum six photos')
  position=c.execute('SELECT COALESCE(MAX(position),-1)+1 FROM product_gallery WHERE product=?',(product,)).fetchone()[0]
  c.execute('INSERT OR IGNORE INTO product_gallery VALUES (?,?,?,?)',(product,digest,content,position))
  domain.audit(c,user['name'],'product photo updated',{'product':product})
 return {'ok':True,'photo_url':f'/product-photos/{product}/{digest}.jpg'}

def urls(c):
 result={}
 for r in c.execute('SELECT product,digest FROM product_gallery ORDER BY product,position,digest'):
  result.setdefault(r['product'],[]).append(f"/product-photos/{r['product']}/{r['digest']}.jpg")
 return result

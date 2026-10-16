"""Validated product photos stored alongside each shop's persistent inventory."""
import base64, binascii, hashlib, io, warnings
from PIL import Image, ImageOps, UnidentifiedImageError

def initialize(c):
 c.execute('CREATE TABLE IF NOT EXISTS product_photos(product INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,digest TEXT NOT NULL,image BLOB NOT NULL)')

def save(domain,user,d):
 if user['role'] not in ('worker','admin'): raise ValueError('Staff access required')
 product=int(d['product'])
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
  c.execute('INSERT INTO product_photos VALUES (?,?,?) ON CONFLICT(product) DO UPDATE SET digest=excluded.digest,image=excluded.image',(product,digest,content))
  domain.audit(c,user['name'],'product photo updated',{'product':product})
 return {'ok':True,'photo_url':f'/product-photos/{product}/{digest}.jpg'}

def urls(c):
 return {r['product']:f"/product-photos/{r['product']}/{r['digest']}.jpg" for r in c.execute('SELECT product,digest FROM product_photos')}

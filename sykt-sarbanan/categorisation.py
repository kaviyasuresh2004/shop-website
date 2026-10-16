"""Conservative name-based suggestions; only uncategorised products are changed."""
import hashlib,json,re,sqlite3

CATEGORIES=('Power tools','Hand tools','Building materials','Electrical','Plumbing','Paint','AC & Refrigeration','Fasteners','Safety Equipment')
RULES=[
 ('Safety Equipment',r'\b(SAFETY (HELMET|GLASS|GOGGLE|SHOE|BOOT|VEST|HARNESS)|HARD HAT|GOGGLES?|RESPIRATOR|EAR (PLUG|MUFF)|FIRE EXTINGUISHER|WORK GLOVES?|WELDING (MASK|HELMET))\b'),
 ('AC & Refrigeration',r'\b(AIR\s*CON(DITION(ER|ING))?|AIRCON(DITIONER)?|REFRIGERANT|REFRIGERATION|R\s*410A|R\s*134A|R\s*22|MANIFOLD GAUGE|VACUUM PUMP|FLARING TOOL)\b'),
 ('Paint',r'\b(PAINT|EMULSION|ENAMEL|VARNISH|LACQUER|THINNER|WOOD STAIN|PRIMER|TURPENTINE|SAND\s*PAPER|SANDING PAPER|PAINTBRUSH|PAINT BRUSH|PAINT ROLLER|ROLLER (BRUSH|TRAY|REFILL)|MASKING TAPE)\b'),
 ('Electrical',r'\b(LED|CFL|BULB|LIGHT(ING)?|DOWN\s*LIGHT|SPOT\s*LIGHT|FLOOD\s*LIGHT|SWITCH|SWITCHGEAR|CIRCUIT BREAKER|MCB|RCCB|ELCB|CONTACTOR|DISTRIBUTION BOARD|ELECTRIC(AL)? (CABLE|WIRE|SOCKET)|CABLE (TIE|REEL|CLIP|LUG)|EXTENSION (CORD|SOCKET)|POWER (SOCKET|STRIP)|PLUG TOP|WALL SOCKET|CEILING FAN|EXHAUST FAN|VOLTAGE|MULTIMETER|INSULATION TAPE|ELECTRICAL TAPE)\b'),
 ('Plumbing',r'\b(PVC|UPVC|HDPE|PPR|POLY PIPE|PIPE|ELBOW|FAUCET|TOILET|SHOWER|BASIN|SINK|BIDET|CISTERN|FLUSH|BALL VALVE|GATE VALVE|CHECK VALVE|STOP (COCK|VALVE)|WATER (TAP|VALVE|PUMP|HEATER|METER)|BIB (COCK|TAP)|PILLAR (COCK|TAP)|FLOOR (TRAP|DRAIN)|PTFE|TEFLON|GARDEN HOSE|WATER HOSE|HOSE (CONNECTOR|CLIP)|FLEXIBLE HOSE|GI (SOCKET|TEE)|BRASS (TEE|SOCKET|NIPPLE|ELBOW))\b'),
 ('Power tools',r'\b(DRILL|DRILLING|DRILLBIT|SDS|HSS|AUGER BIT|HOLE SAW|CUTTING DISC|GRINDING (DISC|WHEEL)|DIAMOND (DISC|BLADE)|CORDLESS|IMPACT DRIVER|ANGLE GRINDER|BENCH GRINDER|JIG\s*SAW|CIRCULAR SAW|MIT(RE|ER) SAW|RECIPROCATING SAW|CHAIN\s*SAW|ROTARY HAMMER|DEMOLITION HAMMER|HEAT GUN|NAIL GUN|ELECTRIC (PLANER|SANDER|SAW)|PRESSURE WASHER|WELDING MACHINE)\b'),
 ('Hand tools',r'\b(SCREWDRIVER|SCREW DRIVER|SPANNER|WRENCH|RATCHET|PLIERS?|PLIER|HAMMER|MALLET|CHISEL|TROWEL|HACK\s*SAW|HAND\s*SAW|HAND SAW|UTILITY KNIFE|MEASURING TAPE|TAPE MEASURE|SPIRIT LEVEL|PRUNING (SHEAR|SAW)|BOLT CUTTER|PIPE CUTTER|WIRE CUTTER|GLASS CUTTER|ALLEN KEY|HEX KEY|PUTTY KNIFE|SCRAPER|STEEL FILE|HAND FILE|TIN SNIP|BENCH VICE)\b'),
 ('Fasteners',r'\b(SCREWS?|BOLTS?|NAILS?|NUTS?|WASHERS?|RIVETS?|WALL PLUG|WALL ANCHOR|THREADED ROD|RAWL(PLUG|BOLT))\b'),
 ('Building materials',r'\b(CEMENT|CONCRETE|MORTAR|GROUT|PLASTER|PLASTERBOARD|PLYWOOD|TIMBER|ROOFING|LOW\s*DECK|SPEED\s*DECK|SPEEDECK|LORATILE|COLOURDECK|RIDGE CAPPING|FLASHING|CORRUGATED|GYPSUM|WALL TILE|FLOOR TILE|TILE ADHESIVE|REBAR|BRC MESH|DOOR (LOCK|HINGE|HANDLE|BOLT)|PADLOCK|TOWER BOLT)\b'),
]

RULES.insert(3,RULES.pop(6))
RULES.insert(3,RULES.pop(6))

def suggest(name):
 text=re.sub(r'[^A-Z0-9]+',' ',name.upper()).strip()
 if re.search(r'\b(DRILLING SCREW|SELF DRILLING|SELF TAPPING)\b',text):return 'Fasteners'
 for category,pattern in RULES:
  if re.search(pattern,text):return category
 return None

def plan(c):
 rows=[];remaining=0;counts={category:0 for category in CATEGORIES};examples={category:[] for category in CATEGORIES}
 for row in c.execute("SELECT id,sku,name FROM products WHERE category='Uncategorised' ORDER BY id"):
  category=suggest(row['name'])
  if not category:remaining+=1;continue
  rows.append([row['id'],row['sku'],category]);counts[category]+=1
  if len(examples[category])<4:examples[category].append(row['name'])
 digest=hashlib.sha256(json.dumps(rows).encode()).hexdigest()
 return rows,{'count':len(rows),'remaining':remaining,'counts':counts,'examples':examples,'digest':digest}

def run(domain,user,d):
 if user['role']!='admin' or d.get('shop')!=domain.CONFIG['slug']:raise ValueError('Wrong shop or permissions')
 with domain.LOCK,domain.connect() as c:
  rows,result=plan(c)
  if d.get('apply') is True:
   if d.get('digest')!=result['digest']:raise ValueError('Catalogue changed; preview again')
   if rows:
    path=domain.DB.parent/'backups';path.mkdir(exist_ok=True)
    backup=sqlite3.connect(path/('before-categories-'+result['digest']+'.db'))
    try:c.backup(backup)
    finally:backup.close()
    for pid,sku,category in rows:c.execute("UPDATE products SET category=? WHERE id=? AND sku=? AND category='Uncategorised'",(category,pid,sku))
    domain.audit(c,user['name'],'products categorised',{'count':len(rows),'counts':result['counts']})
   result['applied']=True
 return result

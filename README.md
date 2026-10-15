# Independent hardware shop websites

Two separate business websites, with reusable source and strict shop separation:

| Folder | Business | Local address |
|---|---|---|
| `bmk-arvin/` | BMK ARVIN SDN BHD | http://127.0.0.1:8081 |
| `sykt-sarbanan/` | SYKT SARBANAN SDN BHD | http://127.0.0.1:8082 |

Each app has its own database, inventory, products, prices, discounts, customer orders, in-shop sales, staff accounts, administrator, login cookies, cart storage and language preference. There are no company transfers, shared inventory or combined dashboard. English/Malay first-visit selection is included.

## Continue on another laptop

Install Git, Python 3.10+ (3.12 recommended), and Node.js 20+ for frontend checks. Node is not needed to serve the websites. Clone this repository while signed into an authorized GitHub account:

```powershell
git clone https://github.com/kaviyasuresh2004/shop-website.git
cd shop-website
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r bmk-arvin/requirements.txt
.\.venv\Scripts\python.exe bmk-arvin/app.py
```

Open http://127.0.0.1:8081. In a second terminal from the same repository:

```powershell
.\.venv\Scripts\python.exe sykt-sarbanan/app.py
```

Open http://127.0.0.1:8082. On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` instead. Create each shop's own local administrator through `/staff`; no passwords are supplied.

Each app creates `data/shop.db` inside its own folder on first startup. The first database contains clearly labelled sample products/stock. Existing laptop databases, account passwords, Tally exports and business records are deliberately not included in Git. If existing records must move, use a separate secure backup/transfer process and reconcile each shop independently; do not commit databases or credentials.

## Current launch status

Both shops are deployed separately on Railway in preview mode, each with its own persistent volume. BMK: https://bmk-arvin-production.up.railway.app — Sarbanan: https://sykt-sarbanan-production.up.railway.app. Idle sleeping is enabled.

Both shop apps default to `SHOP_MODE=preview`, which blocks customer checkout on the server. Sample catalogue, BND currency, delivery rates, business contact details and policy placeholders must be verified before real orders. Run each shop in a separate Railway service with its own persistent volume; configure that service's Root Directory to its corresponding folder in this repository. Never deploy the combined repository root as one shop, and never share database volumes. See each folder's `RAILWAY_DEPLOYMENT.md` for production setup, protected first-admin setup, HTTPS origins, health checks and backups.

Manual payment arrangements only. Customer registration, login, private order history, and account-required checkout are implemented. See ACCOUNT_SETUP.md for protected administrator recovery and limitations. No online payment provider, automated Tally connection, financial reversal workflow or full purchase/accounting reports are implemented. The existing Tally-compatible stock importer supports CSV UTF-8 `SKU,Quantity` snapshots for existing products. Full catalogue/price import mapping awaits separately supplied exports from each company.

## Verification

From each shop folder, with the virtual environment active:

```text
python -m unittest -v test_isolation test_server
node test_frontend.cjs
node --check assets/site.js
node --check assets/staff.js
node --check assets/i18n.js
```

At the last local review, 18 backend checks passed per shop, frontend logic/syntax checks passed, both Docker images built, and disposable container tests verified protected staff/setup endpoints, disabled preview checkout, persistence through restart and separate shop stock. Visual browser/mobile inspection remains incomplete.

## Protect secrets and data

Keep this repository private. Never commit `.env` files, tokens, private keys, local databases, Tally exports, customer information or backups. Production credentials belong in the hosting provider's protected variables. Each website requires its own administrator and staff accounts.

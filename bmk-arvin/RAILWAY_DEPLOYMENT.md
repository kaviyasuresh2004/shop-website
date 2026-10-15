# Railway deployment — separate shops

Status: prepared for public PREVIEW. Sample catalogue, BND currency, Brunei delivery regions and rates remain unverified. Checkout is blocked on the server by default. Do not describe this preview as ready to accept real orders.

## Local run

Python 3.10+ is required. Install `pip install -r requirements.txt` once, then `python app.py`. BMK uses port 8081 and Sarbanan uses port 8082. The app now starts Flask through Waitress instead of the development HTTP server. Keep each shop's own existing data folder. Database upgrades create new tables without replacing existing records. Old in-memory sessions will require a fresh login.

## Create two Railway services

Use one service for this shop and a different service for the other. Deploy only the respective shop folder; never upload the combined parent directory. The Dockerfile allowlist excludes local databases, logs, credentials and test fixtures. `.railwayignore` also excludes database and secret files.

1. Create the service from this directory using Railway CLI or a private source repository. The supplied `railway.json` selects Docker, `/healthz`, one replica and restart on failure. No externally supplied PORT value is hard-coded: Railway's `PORT` is used automatically.
2. Attach a separate persistent volume to EACH service at `/data`. Never reuse a database or volume across shops. `DATA_DIR=/data` and `APP_ENV=production` are already set in the image. Startup refuses a Railway deployment without the matching mounted volume. The entrypoint grants the application user ownership of the volume directory, then drops root privileges.
3. Set `SHOP_MODE=preview`. This is also the default. Generate a private random `SETUP_TOKEN` in Railway's protected variables for each shop. No token or administrator password is supplied in source. If no setup token is configured, first-admin setup remains blocked.
4. Generate each service's Railway domain. `RAILWAY_PUBLIC_DOMAIN` is used to allow same-origin HTTPS actions. For a custom domain, set `PUBLIC_URL=https://your-exact-domain` without a trailing slash. Set this separately for each service. Do not use wildcard origins. Access the public staff workspace only through HTTPS.
5. Deploy. Verify `/healthz` returns the correct shop slug, storefront and staff page load, customer orders are blocked, and each staff workspace requires its own sign-in. Create each shop's initial administrator yourself using its own private setup token, then remove `SETUP_TOKEN` from Railway variables. The token is only needed once. Avoid entering secrets in chats or committed files.
6. Enable and verify Railway volume backups. SQLite needs one replica and one process per shop. Test a restore before accepting orders. Local databases are deliberately not automatically uploaded to Railway.

Railway publishing has not been performed by preparing these files. It requires an authenticated Railway connection, available hosting capacity and confirmed service/volume state. Docker image build must pass in Railway (or locally with Docker running) before launch is verified.

## Tally data and real shop cutover

Export BMK and Sarbanan separately. Provide each company’s stock-item export with the actual column headers, SKU/item code, name, category, units, closing quantity, selling price, currency and tax treatment where available. Tally export layouts vary; mapping should be implemented against the supplied sample rather than guessed. Do not include credentials or unnecessary customer/staff personal data.

The existing staff stock importer accepts only CSV UTF-8 `SKU,Quantity` for already-existing SKUs and replaces quantities atomically. It is not a full catalogue importer or a live Tally integration. Validate any fractional units and currency conversion before importing; current quantities are whole numbers and prices are integer cents. A separate offline migration utility remains available for the old combined database; it refuses to overwrite a destination database and filters by company.

Before enabling `SHOP_MODE=live`, import/reconcile the independent real catalogues, quantities and prices; configure approved delivery coverage/fees and contact details; complete privacy/returns/delivery policy text; create workers; verify payments arranged manually and order processing. Online payments, automated Tally synchronization, purchasing/accounting reports and financial reversals are not implemented. Do not enable live checkout while sample data or placeholder policies remain.

## Verification

`python -m unittest -v test_isolation test_server` checks isolation, migration, role boundaries, stock rollback, HTTPS origins, protected setup, durable/expiring sessions, password-change session revocation, checkout preview block, rate limiting, duplicate orders, server-side pricing, pending-order reporting and path traversal. `node test_frontend.cjs` checks both dictionaries, static UI references, language preference, cart behavior, discounts and preview checkout logic. `node --check` verifies script syntax.

Browser visual inspection was blocked by the browser tool's URL security policy. Automated script checks are not a substitute for an end-to-end browser/mobile accessibility inspection. Review both desktop and mobile layouts before live cutover.

Customer accounts and owner-authorized administrator recovery are now available. See ../ACCOUNT_SETUP.md. ADMIN_RECOVERY_TOKEN is optional, must contain at least 32 random characters, and must be removed after recovery. Existing accounts and records are preserved.

# Account setup and recovery

Each shop runs independently. Customer tables, staff tables, cookies, sessions and order ownership are stored only in that shop's own database. Existing staff, stock and sales are retained; startup creates additional tables without replacing records.

## Staff login

Use the account's assigned password, not a setup token. Usernames now ignore letter case and surrounding spaces; passwords still match exactly. Existing stored usernames are retained. If a legacy database contains two names differing only by case, login refuses that ambiguous match rather than choosing an account. After 20 authentication attempts in ten minutes, wait ten minutes before retrying.

## Recover an existing administrator

1. In the correct Railway service, add `ADMIN_RECOVERY_TOKEN` with a new random secret of at least 32 characters. Keep it private. Deploy and wait for Online.
2. Open that shop's `/staff` page and choose **Recover administrator access**.
3. The owner enters the existing administrator username, a new password of 8–256 characters, and the recovery token. This must be done by the owner; do not put the credentials in chat or source files.
4. Sign in using the new password. Recovery revokes all prior staff sessions for that administrator and records an audit entry. It does not create an administrator or reset worker accounts.
5. Remove `ADMIN_RECOVERY_TOKEN` from Railway and deploy again. The database also prevents reuse of a consumed token. A subsequent recovery requires a different secret.

Workers ask their administrator to reset their password using account management. First-time administrator creation continues to use `SETUP_TOKEN`; it cannot reset an existing administrator.

The administrator's Staff accounts table shows saved usernames, roles and shops without exposing password hashes. Select the worker, choose Reset password, enter a new password and save. Use Show password while entering it if needed. The previous password stops working and existing worker sessions are revoked. Test using the displayed username at `/staff` after signing out or in another browser. Saved passwords cannot be retrieved later; reset them if lost. Removing an account is a separate explicit action and is never triggered by leaving the reset-password field blank.

Delivered and Completed online orders both count once in completed-sales totals. Changing order status does not deduct stock again. The manual completed-sale form remains for physical-shop sales; do not record a website order a second time there.

## Customers

The storefront Account button now offers registration and login. Customers register with their name, email and a password of at least 8 characters; phone and delivery address can also be saved at registration. Customers can see only their own new online orders and change their password using their current password. Customer sessions cannot access staff endpoints, and staff sessions cannot substitute for a customer at checkout. There is no email verification or forgotten-customer-password email service yet; do not represent email addresses as verified.

Customer login is enforced on the server before an online order can be placed. Order ownership is written in the same transaction as the order and stock adjustment. Previous guest orders are not linked to customers by guessing names or email addresses. Preview mode still blocks all customer orders, including orders by registered customers. Keep `SHOP_MODE=preview` until the genuine catalogue, prices, delivery details and policies are approved.

## Local checks

In each shop folder, using Python with its requirements installed:

```
python -m unittest -v test_accounts test_server test_isolation
node test_frontend.cjs
node --check assets/customer.js
node --check assets/recovery.js
```

Tests use disposable databases and synthetic credentials. Do not upload local test databases to production.

Account settings: registration returns to shopping. The Account button opens Overview, Personal details, Orders and Password settings. Signed-in customers can update their own name, phone and address. Email is displayed but cannot be changed. Password settings require the current password and confirmation of the new password; email-based recovery remains deferred.

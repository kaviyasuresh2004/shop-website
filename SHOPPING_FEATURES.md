# Shopping and delivery

Each shop keeps its own database, customers, orders and enquiries.

## Deals

In Staff → Manage promotions, choose Product discount, select a product, set the reduced BND price and start/end times, and supply the two language titles. Search inventory to narrow product selectors. During a valid offer, product cards and details show the current price, crossed-out regular price, percentage savings, amount saved and actual end time in Brunei. Regular prices come from inventory; no comparison prices or artificial deadlines are generated. Low/high price sorting uses the current discounted price. The catalogue refreshes each minute when no checkout/account dialog is open. A checkout with a changed total is rejected for review, with stock rolled back.

## Checkout and Buy now

Buy now opens checkout for the selected item and preserves other cart items. Quantity and delivery region can be changed inside checkout. Cash on delivery and cash on collection are supported. Orders require a signed-in customer. Required delivery addresses, optional Google Maps shared pin links and delivery instructions are stored with the order. Only HTTPS Google Maps links are accepted. The server never follows or fetches a submitted link. Opening a map sends the selected address/pin to Google; no Google API key or paid Maps API is used. A link is not proof that an address is correct.

Worker order rows show the customer, products/quantities, total, phone, written address, map link, instructions, status and cash-payment status. Delivery and receipt of cash remain separate actions. Completed sales remain immutable. Customer order retries use an idempotency key and cannot create a second sale for the same request.

Checkout remains inactive on production until the administrator completes Shop settings and enables cash orders. This upgrade does not invent business policies, enable checkout automatically or alter real stock.

## Bulk enquiries

Signed-in customers submit a phone number and product/quantity/delivery requirements. Staff see enquiries in a separate queue and can mark New, Reviewing, Quoted or Closed. An enquiry does not create a sale or reserve stock. Duplicate network retries reuse a receipt; a customer is limited to five new enquiries per hour. Customer data is available only to this shop's staff.

## Phone OTP: prepared, inactive by default

Phone codes need a separate verification-provider account and paid delivery. No provider account, credentials or billing was supplied for this upgrade. Both production services should keep `PHONE_OTP_ENABLED` unset/false. The UI clearly states that verification is unavailable; it never marks an unverified phone as verified.

The prepared adapter uses Twilio Verify and supports SMS or WhatsApp. After confirming Brunei availability and pricing, configure each Railway service privately with `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, its own `TWILIO_VERIFY_SERVICE_SID`, `PHONE_OTP_CHANNEL` (`sms` or `whatsapp`) and `PHONE_OTP_ENABLED=true`. Use separate Verify services for isolation. Never put tokens into Git, browser code or chat. Perform a real delivery/verification test before enabling it for shoppers. WhatsApp availability and approval must be checked with the provider; SMS can be used when a customer lacks WhatsApp. No fallback sends automatically.

When enabled, customers verify their saved account phone in Personal details or checkout; orders require that verified number. Changing the account number revokes approval. This initial integration accepts only Brunei numbers (+673 and seven digits). Codes are checked by the provider, expire locally after ten minutes, allow five checks per challenge and are not stored or logged by the website. The website reserves send attempts before calling the provider, requires customer action/consent, waits at least 60 seconds between resends, and caps sends at three per account/number per hour, five per IP per hour and fifty per shop per day. These limits reduce abuse; they are not a provider-side spending guarantee. Configure provider spending/geo controls as part of activation.

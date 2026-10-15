# Shop details and cash checkout

Sign in to the shop's `/staff` page as its administrator and open **Shop settings**. Each shop stores its own settings in its own database. Workers can process orders and record cash received, but cannot change shop settings.

You can edit the address, phone, opening hours, HTTPS map link, delivery charges in BND, and delivery/returns/privacy policy text. These details appear on the storefront after refreshing. Product names, categories and prices remain in the separate product editor. Custom product and shop photo uploads are not implemented by this change.

## Before accepting real orders

Replace the sample catalogue, quantities and prices. Complete the shop contact information and all policies, check currency and delivery charges, then tick the confirmation and **Accept cash-on-delivery / cash-on-collection orders** and save. Settings can be saved as a draft without enabling checkout. The server refuses activation with missing contact information/policies or without catalogue confirmation. Do not confirm while sample stock/prices are still being used.

The checkout form shows items, delivery cost, total and cash payment. Customers must sign in. The server calculates prices and delivery charges, rejects unsupported payment methods, and records order ownership and payment status with the stock update. Repeated submission of the same request does not create a second order. Cash on collection is used for pickup; cash on delivery is used for deliveries.

Cash is initially **pending**. Staff should use **Mark cash collected** only after receiving payment. Marking an order Delivered includes it in completed-sales totals but does not imply cash was received and does not deduct stock again. The manual completed-sale form is for physical shop sales; do not enter a website order again there.

Saved shop settings take precedence over the original SHOP_MODE default. Until settings are saved, the existing environment default is retained. Existing orders remain unchanged; older orders without a payment record are labelled manual / payment not recorded rather than assumed paid or COD.

Bank transfer remains deferred. A future version can show verified company bank details and record staff confirmation of receipt. No bank integration or automatic bank reconciliation is included now.

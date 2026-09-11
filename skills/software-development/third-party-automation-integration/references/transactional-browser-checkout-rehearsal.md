# Transactional Browser Checkout Rehearsal

Use this reference when validating a checkout-capable browser automation without creating an order.

## Safe rehearsal sequence

1. Load an allowlist entry containing stable product ID, exact name/variant, quantity, currency, maximum unit price, and maximum final total.
2. Verify the product page exposes the exact identity and an in-stock purchase control.
3. Add the permitted quantity, then authenticate to the merchant if required.
4. Re-open and normalize the authenticated cart: remove every foreign line, reset the target quantity, and reject stock warnings.
5. Advance through shipping and payment selection only with explicitly known non-final controls such as `Continue`.
6. Select the intended payment method through its visible UI, then verify the underlying radio/control state changed; do not force hidden controls through DOM mutation.
7. Stop immediately on the merchant's final review/confirmation route. Do not accept terms, click the final order control, or follow the redirect that creates the order.
8. Validate exact product, quantity, currency, and the final labeled total. Save a metadata-only result and privacy-safe evidence.
9. Close context and browser in `finally`, then verify no automation browser process remains.

## Common checkout behavior

- Merchant authentication may be mandatory before payment selection; payment-provider credentials alone are insufficient.
- Anonymous carts may merge into a saved account cart at login. A stale out-of-stock item can block checkout even when the target item is available.
- Responsive templates may duplicate hidden and visible forms. Prefer visible controls and verify resulting URL/stage rather than selecting the first text match blindly.
- Styled payment rows may hide the underlying radio. Click the visible row/label and assert the expected radio is checked.
- Legacy PayPal integrations may redirect only after a merchant `Confirm Order` action, but PayPal Smart Buttons can render provider UI directly on the final review page. Inspect the live implementation before deciding which control is the commit boundary; never assume a hidden legacy button is the intended path.
- Product-page price, cart subtotal, shipping-stage total, and final review total can differ. Validate the labeled final total rather than taking the last number on the page, which may be a phone number, postcode, or copyright year.

## PayPal Smart Buttons and safe handoff

- Inspect the merchant's inline PayPal `createOrder` and `onApprove` callbacks. Some integrations create only a provider-side order session when the PayPal button is clicked and submit the merchant order only inside `onApprove`; model these as distinct states.
- Terms widgets may auto-open a modal. Use the visible `Accept` control and wait for concrete postconditions: the required checkbox is checked, the modal is hidden, and the PayPal container is enabled. Do not force hidden checkboxes or call form submission directly.
- The real PayPal control may be a cross-origin iframe element such as `div[role="link"][aria-label="PayPal"]`, not a native button or anchor. Interact through the frame's accessible role and verify the provider window opens.
- Capture the popup with Playwright `context.expect_page()` around the button click. Do not discover checkout by scanning for the first PayPal-hosted frame: `/smart/buttons`, `/smart/message`, and credit-presentment experiment frames are technical or ephemeral and can detach immediately.
- Track at least: payment method selected, provider order session created, PayPal checkout reached, PayPal login completed, payment authorized, merchant order submitted, and payment completed. Never infer later states from an earlier one.
- Detect CAPTCHA or security challenges before pressing login continuation controls. Stop with an explicit challenge state; do not bypass the challenge or repeatedly create abandoned provider sessions.
- Provider checkout screenshots can expose payer email, shipping address, and amount. Keep them local with mode `0600` unless cropped or redacted.
- A screenshot of the full review page may expose delivery and billing data. Crop to product/total or redact before delivery; keep raw evidence mode `0600` if it must exist locally.

## Safety assertions worth testing

- Exact-name and stable-ID mismatch reject the transaction.
- Out-of-stock state rejects the transaction.
- Unit price and final total above ceiling reject the transaction.
- Final-review URLs always trigger a rehearsal stop.
- Text such as `Confirm Order`, `Pay now`, `Place order`, or localized equivalents is classified as a final action.
- The idempotency claim succeeds once and fails on a duplicate product/order key.
- Terms remain unchecked and no final control is clicked.
- Result states distinguish review reached, order created, payment started, and payment completed.

## Browser cleanup verification

Inspect process executable names rather than searching full command text. A process-list command can otherwise match its own search string and produce a false positive. Restrict checks to actual browser process names plus headless/automation flags.

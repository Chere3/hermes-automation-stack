# Alexa OAuth proxy 404 after transaction approval

Use this note when an `alexa-cookie2` loopback enrollment accepts the account identifier but Amazon then shows a 404 during transaction approval or OTP verification.

## Safe evidence signature

Capture exactly one bounded trace containing only method, status, host/path, and redirect host/path. Strip query strings, fragments, credentials, cookies, headers, bodies, authorization codes, and tokens.

A useful signature is:

```text
POST /www.amazon.com/ap/signin -> 302 /www.amazon.com/ap/challenge
GET  /www.amazon.com/ap/challenge -> 302 /www.amazon.com/ap/cvf/transactionapproval
GET  /ap/cvf/approval/poll -> 302 /www.amazon.com/a/c/404
POST /ap/cvf/approval/verifyOtp -> 302 /www.amazon.com/a/c/404
```

Stop the portal after the trace and confirm that no private pending-registration file exists. Do not ask the user to keep repeating credentials.

## Root-cause boundary

In `alexa-cookie2` 5.0.5, the proxy can restore proxied `Referer` values yet still forward loopback URLs embedded inside URL-encoded POST form fields or query parameters. Amazon then receives a callback/return URL pointing at `127.0.0.1` and can redirect the CVF flow to `/a/c/404`.

`alexa-cookie2` 5.0.6 adds:

- `fixEmbeddedProxyUrls(...)` for query parameters;
- full buffering/parsing of `application/x-www-form-urlencoded` POST bodies;
- restoration of embedded loopback proxy URLs before re-sending the body.

Pin at least 5.0.6 for this flow. If a local compatibility patch also rewrites `Referer` on GET requests, make its installer version/layout-checked and fail closed on package drift.

## Regression seam

A focused test should execute the installed `lib/proxy.js` through stubs and prove that a POST body such as:

```text
openid.return_to=http://127.0.0.1:3456/www.amazon.com/ap/maplanding
```

is forwarded as:

```text
openid.return_to=https://www.amazon.com/ap/maplanding
```

Run the focused POST-body test, the separate GET-Referer test, the OAuth manager tests, and then one live human enrollment. Treat unit success as request-construction evidence, not proof that Amazon accepted the live enrollment. After live completion, persist the registration securely and validate with a read-only Alexa inventory request before enabling briefs or playback.

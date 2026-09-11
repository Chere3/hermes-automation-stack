# OAuth proxy login-loop debugging

Use this when a loopback/reverse-proxied login accepts credentials or MFA but lands on a generic 404 or restarts authentication.

## Safe evidence capture

Instrument one reproduction and record only:

- request method;
- host and path, with query strings/fragments removed;
- response status;
- redirect host and path, also stripped.

Do **not** record headers, cookies, request/response bodies, authorization codes, OAuth state, OTPs, tokens, or query values. Stop the temporary portal after the reproduction.

A useful sequence distinguishes stages such as:

```text
POST /provider/ap/signin -> 302
GET  /provider/ap/challenge -> 302
GET  /provider/ap/cvf/transactionapproval -> 200
GET  /ap/cvf/approval/poll -> 302 /provider/a/c/404
```

The credential POST succeeded; the break is the relative polling request. Do not blame the password, region, or callback without additional evidence.

## Hidden failure mode: method-scoped header restoration

Proxy implementations often encode the upstream host in the browser-visible path and later restore upstream `Referer`/`Origin`. Check whether that restoration is incorrectly nested under `if method == POST`.

Modern MFA pages may poll with GET. If GET retains a loopback referer such as:

```text
http://127.0.0.1:PORT/provider/ap/cvf/transactionapproval
```

provider anti-abuse checks can redirect to a generic 404. Restore the upstream referer for every method; keep POST-only body/origin handling scoped to POST unless evidence requires otherwise.

## Durable dependency repair

1. Build a VM/mock or seam-level regression that invokes the installed dependency's proxy request hook with a GET polling request and loopback referer.
2. Assert RED: the referer remains loopback.
3. Move only referer restoration outside the POST block.
4. Assert GREEN: the outbound referer is the upstream HTTPS URL.
5. Persist via an idempotent post-install patch script:
   - exact pinned dependency version;
   - exact old/new source blocks;
   - no-op if already patched;
   - fail closed if neither block matches;
   - atomic file replacement.
6. Run the focused regression plus the integration's full tests/type-check. Report unrelated pre-existing failures separately.
7. Repeat one human login with sanitized trace enabled, confirm the expected callback/pending state, then disable trace and close the portal.

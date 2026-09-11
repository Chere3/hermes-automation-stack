# Alexa OAuth cookie renewal

Use this reference when a cookie-authenticated Alexa integration must survive expiration without repeatedly copying browser cookies.

## Core distinction

- Browser cookies such as `ubid-main` and `at-main` authenticate current web requests, but they cannot by themselves be upgraded into a refresh token.
- Silent renewal requires a one-time mobile-app-style OAuth device registration that yields a refresh token plus persistent registration identity.
- Implementations commonly exchange the refresh token through `POST https://api.amazon.com/auth/token` (or the account-region equivalent), requesting either `access_token` or `auth_cookies`. This is an internal Amazon flow, not a stable public Alexa automation API; fail closed and expect future protocol changes.

## Recommended architecture

1. Perform one interactive OAuth enrollment from the user's PC.
   - Bind the login proxy only to `127.0.0.1` on the automation host.
   - Reach it through an SSH local-forward; do not expose it on the LAN or install a MITM CA when a loopback enrollment proxy is sufficient.
   - Allow password, MFA and CAPTCHA to remain between the user, browser and Amazon. Never pass them through chat or agent logs.
2. Persist the complete registration object, not just cookies.
   - Preserve the same device identity on every refresh to avoid creating abandoned Alexa app-device registrations.
   - At minimum, renewal libraries generally require a refresh token and prior login/device registration material; retain the complete library-returned object unless its schema explicitly documents a smaller stable subset.
3. Store durable OAuth material as a concealed password-manager field. A compact base64-encoded JSON field avoids multiline dotenv parsing problems; base64 is transport encoding, not encryption.
4. Keep the runtime service account read-only. A personally authorized one-time CLI session can write enrollment state; routine automation only reads it.
5. Derive fresh cookies into an ephemeral runtime directory (`0700`) and file (`0600`). Never rewrite cookie values into source files, shell arguments or logs.
6. Refresh before expiry (for example every five days when observed cookie validity is roughly fourteen days), then validate using a read-only device/inventory request.
7. Reload long-lived processes after successful renewal. Updating an ephemeral file does not change credentials already loaded into a daemon's memory.
8. Alert only when refresh or read-only validation fails persistently, especially for revoked refresh tokens, MFA/CAPTCHA requirements or protocol changes. Never use audible playback as the authentication probe.

## Maintained implementation note

- `alexa-cookie2` 5.x implements proxy-assisted device registration and `refreshAlexaCookie`; pin an audited exact version instead of using an open dependency range.
- Its documentation describes Alexa cookies as roughly fourteen-day credentials and recommends refreshing within approximately 5–13 days. A five-day cadence leaves recovery margin but must still be validated against the live account.

### Proxy callback lifecycle in `alexa-cookie2` 5.x

In proxy-only registration, `generateAlexaCookie(options, callback)` invokes the callback more than once:

1. After the loopback proxy starts, it calls back with an `Error` whose message says to open `http://<proxyOwnIp>:<proxyPort>/`. This is a readiness notification, not terminal failure.
2. After the human finishes Amazon login/MFA/CAPTCHA, it calls back again with the completed registration object or a real terminal error.

A wrapper must not mark the operation complete or call `stopProxyServer` on the readiness callback. Ignore only the exact expected readiness message for the configured loopback IP and port; reject every other error. Keep the promise/process pending until the second callback, then validate the full registration object, write it atomically, and stop the proxy. Add a regression fixture that emits readiness first and success on a later tick—single-callback fakes miss this lifecycle bug.

## Persisting enrollment state without exposing it

- Store Amazon password, MFA and recovery material only in the human's personal 1Password context; never place them in the service-account-readable automation item.
- The automation item should contain only current derived cookies plus one concealed `ALEXA_OAUTH_STATE_B64` field holding the complete validated registration object.
- Derive the target vault/item from existing immutable 1Password item references for `UBID_MAIN` and `AT_MAIN`, and require both to resolve to the same item.
- To add or replace `ALEXA_OAUTH_STATE_B64`, fetch the item as JSON, modify it in memory, and pipe the complete JSON to `op item edit`. Never place the encoded state in assignment arguments, logs, terminal scrollback or chat.
- Keep the runtime service account read-only. 1Password service-account vault access and permissions are immutable after creation, so do not tell the user to temporarily widen an existing read-only identity. Use either a personally authenticated one-time CLI session or a separate short-lived service account scoped only to the intended vault with `read_items,write_items`; finalize, validate read-only, then revoke/delete the temporary identity.
- Verify the writer path before starting OAuth when possible. If enrollment has already completed, preserve the mode-0600 pending registration while correcting writer access; do not force the user through Amazon login again.
- Preserve the pending registration file on every write or validation failure. Delete it only after 1Password persistence, reference update, cookie derivation and a canonical read-only Alexa inventory check all succeed.

## Diagnosing a post-login loop safely

If Amazon shows an inactive-page message and `Continue` returns to login, do not ask the user to repeat credentials indefinitely and do not infer that registration succeeded merely because authentication occurred.

1. Stop the enrollment portal and verify metadata-only whether a private pending registration file exists. If none exists, the OAuth callback did not complete.
2. Reproduce once with a bounded safe trace on the loopback proxy.
3. Record only HTTP method, response status, hostname and path. Strip query strings, fragments, URL userinfo, cookies, headers, authorization codes and tokens before writing logs.
4. Use that trace to isolate the failing boundary (`/ap/signin`, `/ap/maplanding`, callback exchange, or regional redirect) before changing configuration.
5. Rank and test one hypothesis at a time. Do not change `amazonPage`, `baseAmazonPage`, locale and proxy host together.
6. Disable the diagnostic trace after use, stop the portal on timeout, and keep all pending files mode `0600`.

A useful regression seam is a pure URL sanitizer: an input containing URL userinfo, a query and a fragment must yield only `{host, path}`. Instrumentation should consume that sanitizer rather than logging raw request or `Location` values.

## Concurrency and durability

- Serialize refresh with a persistent `flock` or equivalent lock.
- Give every wrapper invocation a unique dotenv path; a shared `dev.vars` creates deletion and replacement races between concurrent commands.
- Do not `source` or `eval` a secret-injected dotenv. Parse strict `KEY=value` lines, reject malformed or duplicate keys, export quoted assignments, and propagate the unique runtime path to the child.
- Atomically replace cache and dotenv files: private temporary file, flush/fsync where available, rename, then verify mode.
- Do not overwrite a valid cache when a refresh attempt fails.
- Keep static current cookies as a short-lived fallback for transient refresh failures, but report the refresh failure separately so fallback does not hide eventual expiry.

## Secret-handling pitfalls

- Some Alexa cookie libraries log complete request options, refresh tokens or response bodies through their logger callback. Supply a no-op logger and sanitize every surfaced error for cookie, token and Authorization patterns.
- Do not print the registration object, even for debugging or successful enrollment confirmation. Emit metadata only (`ready`, `completed`, `refreshed`, timestamps).
- Do not put secrets in `op item edit` arguments. Use a protected template/stdin workflow under a personally authenticated 1Password CLI session.
- Duplicate 1Password item titles make `op inject` references ambiguous. Resolve metadata only and use immutable item IDs in references; never delete the older item without explicit permission.

## Verification checklist

- Unit tests cover required-cookie extraction, malformed registration state, refresh due/not due, atomic writes, redaction, stale-cache preservation and proxy cleanup.
- A fake integration harness proves concurrent wrapper invocations use different files and clean them afterward.
- Enrollment proxy is loopback-only and closes on success, timeout, SIGINT and SIGTERM.
- A real forced refresh succeeds, followed by read-only inventory using the derived cookies.
- Scheduled brief dry-runs pass and no audio is produced without explicit authorization.
- The long-running MCP/service is restarted only after a successful refresh and then passes a read-only call.

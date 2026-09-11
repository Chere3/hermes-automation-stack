# Human-in-the-loop OAuth Refresh-Token Rotation

Use this pattern when a provider deliberately expires refresh tokens in a non-production/testing state and unattended renewal is impossible without a new user grant.

## Security boundary

Automate scheduling, authorization-URL generation, callback capture, code exchange, token storage, verification, and notification. Keep these steps human:

- account login and password entry;
- MFA or passkey approval;
- review of requested scopes;
- the final consent/Allow action.

Do not preserve a browser profile solely to click consent unattended, scrape a private authorization UI, or attempt to keep a testing token alive through artificial use.

## One-click renewal architecture

1. Determine renewal due time from explicit issuance metadata where possible; file `mtime` is an acceptable fallback only when the token file is changed exclusively by rotation.
2. Start or retain a callback listener bound only to loopback.
3. Put TLS/private-network routing in front of it only when the registered redirect URI requires HTTPS. Prefer a private tailnet/VPN route over a public endpoint; do not silently enable public tunneling.
4. Generate a cryptographically random `state` (at least 256 bits), store it in a mode-`0600` one-time record, and expire it after 10–15 minutes.
5. Build the authorization URL with the exact existing scopes, `response_type=code`, `access_type=offline`, and provider-required consent parameters. Never add write scopes merely to broaden coverage.
6. Deliver the URL to the user. Reuse one still-valid pending URL rather than replacing its `state` on every scheduler tick.
7. The callback must:
   - accept only the exact allowlisted path;
   - require exactly one `code` and one `state`;
   - compare `state` in constant time;
   - reject expiry, replay, missing parameters, and a second successful capture;
   - suppress HTTP request logging because the query contains the authorization code;
   - catch client disconnects such as `BrokenPipeError` while writing generic success/failure pages so routine browser cancellation does not emit a traceback; never include the request line or query in exception logging;
   - return `Cache-Control: no-store` and `Referrer-Policy: no-referrer`;
   - immediately replace browser history with a clean path after rendering the result.
8. Exchange the code server-side. Keep client secrets out of process arguments and stdout.
9. Validate the new grant with the smallest read-only API probe. Then atomically replace the authoritative token (`mkstemp` in the same directory, mode `0600`, `fsync`, `os.replace`). Preserve rollback only if the provider permits the previous token to remain valid.
10. Do not keep the browser callback waiting for a multi-minute full synchronization. After code exchange, grant validation, atomic token storage, and one-time state consumption, return a short generic page immediately. Its wording must distinguish “authorization accepted; verification is running” from “synchronization completed.” Queue the normal synchronization/health check in a background worker owned by the long-lived service.
11. The background verifier must atomically write one mode-`0600` status marker: a sanitized success timestamp or a fixed failure identifier plus timestamp. Remove stale opposite-state markers before each run, never write exception text/provider bodies, and ensure a scheduler/watchdog reports unresolved failure. Catch browser disconnects independently; a `BrokenPipeError` after successful exchange must not change OAuth state or produce a secret-bearing traceback.
12. On failure, retain a still-valid pending state only if retrying the same authorization code is valid. Otherwise invalidate it and issue a new URL. Never print provider error bodies before redacting secret-bearing fields.

## Scheduler behavior

- Run a lightweight due check daily; print nothing when renewal is not due so script-only cron delivery stays silent.
- Notify before the provider's hard expiry with enough margin for the user to consent.
- If routing or redirect registration is incomplete, keep the reminder paused rather than sending a broken link.
- Alert on unresolved `invalid_grant`, `redirect_uri_mismatch`, `access_denied`, missing refresh token, callback timeout, or scope mismatch.

## Read-only secret-store constraint

A read-only machine identity can fetch the OAuth client credentials but cannot write the newly issued refresh token back to the password manager. Choose before authorization:

- store the rotating token in a narrowly protected local mode-`0600` file consumed by only the service; or
- use a separately scoped write target that cannot modify unrelated items; or
- require a user-mediated import.

Do not widen an otherwise read-only vault identity during the short-lived callback window.

## Systemd and private HTTPS notes

- Reject a callback with missing/duplicate/empty `code` or `state` **before** loading password-manager credentials or calling any network-backed secret provider. This keeps malformed probes fast and prevents an unavailable secret store from turning a simple `400` into a hung callback.
- When `ProtectHome`/`ProtectSystem` and `ReadWritePaths=` are used, create every allowlisted writable directory before starting the service. A missing path fails at systemd's namespace step before the application runs.
- Verify both layers: direct loopback HTTP first, then the private HTTPS hostname. Test the exact callback path with no query and require an immediate sanitized `400`; do not stop at testing only `/` or a different path.
- Some private-network HTTPS products require a one-time tailnet/admin enablement. Treat this as a human infrastructure approval; leave related cron jobs paused until HTTPS verification succeeds.
- Tailscale Serve configuration may require root even after the tailnet feature is enabled. Prefer a one-time narrowly scoped `sudo tailscale serve ...` over permanently granting the automation user Tailscale operator privileges unless ongoing reconfiguration is truly required.
- The serving node might not resolve its own MagicDNS name even though tailnet clients can. Verify TLS and routing without changing DNS by resolving the hostname to the node's tailnet IP for the probe (for example, curl's `--resolve host:443:TAILNET_IP`); still test from the actual user device before depending on the flow.
- Confirm the process listens only on loopback and that no public Funnel/tunnel was enabled accidentally.
- Register and save the exact HTTPS callback URI in the OAuth client before enabling reminders. A working private proxy does not prove the provider accepts the redirect.

## Google Health example (August 2026)

Google Health API v4 exposed nine read-only scopes in the examined consent grant:

- `googlehealth.activity_and_fitness.readonly`
- `googlehealth.ecg.readonly`
- `googlehealth.health_metrics_and_measurements.readonly`
- `googlehealth.irn.readonly`
- `googlehealth.location.readonly`
- `googlehealth.nutrition.readonly`
- `googlehealth.profile.readonly`
- `googlehealth.settings.readonly`
- `googlehealth.sleep.readonly`

The official discovery document showed profile, settings, IRN, data-point, paired-device, and subscription methods but no public Health Coach endpoint. Build non-clinical coaching from authorized read-only metrics; do not scrape a private Fitbit/Google coaching interface. Avoid retaining raw ECG waveforms or precise GPS tracks unless the user explicitly needs them and the use case justifies that sensitivity.

# Local Worker services and mobile-session capture

## Running a local JavaScript/Worker service under systemd

A development runtime such as Wrangler/Miniflare can be made persistent, but hardening must be verified against its real filesystem and network needs.

Recommended sequence:

1. Pin the project-compatible CLI version and complete install/type-check/lint before creating the unit.
2. Bind explicitly to `127.0.0.1`; do not rely on framework defaults.
3. Store provider credentials in a Git-ignored file with mode `0600` and use a separate bearer token between Hermes and the service.
4. Enable the user unit, then wait for an actual readiness log or health response. `active (running)` alone is insufficient when the runtime is still bundling or restarting.
5. Verify health `200`, unauthenticated functional/MCP `401`, authenticated MCP discovery, loopback listener, and a clean recent journal.

### Hardening pitfalls

`ProtectSystem=strict` and `ProtectHome=read-only` are useful, but Worker development runtimes may need narrow exceptions:

- Wrangler logs under a path such as `~/.config/.wrangler/logs`.
- Local Worker state under the project `.wrangler` directory.
- Miniflare may create a temporary `.mf` directory under `node_modules` in older compatible releases.
- Node's `uv_interface_addresses()` may require `AF_NETLINK`; omitting it from `RestrictAddressFamilies` can produce error 97 even when only loopback TCP is intended.

Create required writable directories before starting the unit and whitelist only those exact paths with `ReadWritePaths`. Add `AF_NETLINK` without broadening the listening address. After every unit change, restart and inspect logs from the new invocation only so resolved errors from earlier restarts are not mistaken for current failures.

## Secure mobile-session capture

When an unofficial integration needs session cookies, never ask the user to paste them into chat. A safer pattern is a temporary local intercepting proxy with a purpose-built addon:

- Bind the proxy to the laptop's LAN address and a temporary port.
- Filter by an exact allowlist of legitimate parent domains; reject suffix tricks such as `amazon.com.evil.test`.
- Read only the named cookie fields required by the integration.
- Do not inspect, print, or persist request bodies, passwords, OTPs, or general flow archives.
- Accumulate required cookies in memory, update the secret file atomically with mode `0600`, and shut down immediately once complete.
- Keep the service on dummy credentials until a read-only provider request validates the captured session.

### Mobile guidance and diagnosis

Guide phone setup one checkpoint at a time; long blocks are easy to miss in messaging clients. Confirm each of these independently:

1. The proxy is listening.
2. A host-side `curl --proxy` receives mitmproxy's certificate-install page.
3. The phone actually opens a TCP connection to the proxy port.
4. The user CA is installed and Chrome can open an HTTPS test page.
5. Only then open the target app.

If `mitm.it` says traffic is not going through mitmproxy and the server sees no phone connection, the phone is bypassing the proxy. Check Wi-Fi proxy host/port, blank bypass list, mobile data, VPN/ad blockers, saving the network config, reconnecting Wi-Fi, and an incognito retry.

Chrome trusting the user CA does not prove the target app will trust it. Android apps may use certificate pinning or a network security policy that rejects user CAs, producing TLS `certificate unknown` for the app's own host. Do not automatically patch/re-sign the APK or weaken the phone. Prefer a browser-authenticated session if it satisfies the endpoint, or discuss emulator/root/instrumentation only as an explicit higher-risk option.

### OTP and sign-in sequencing

Do not leave the intercepting proxy enabled while requesting a login OTP. Code delivery, push messaging, and account-verification components may use pinned TLS or otherwise fail behind the user CA, even when Chrome itself works. Use this sequence instead:

1. Set the phone's Wi-Fi proxy to `None` while leaving the temporary CA installed.
2. Complete the provider login and OTP challenge directly on the phone.
3. After the authenticated page is visible, re-enable the manual proxy.
4. Refresh only the authenticated provider pages needed to emit the session cookies.
5. Let the capture addon shut down as soon as all required cookies are saved.

If the proxy exits immediately after the refresh, inspect its completion signal before restarting it: an auto-exit often means capture succeeded, not that the process failed. Tell the user that result directly. In messaging workflows, give one checkpoint at a time and honor short operational requests (for example, “open the process again”) before resuming unrelated validation or bug-fixing work.

## Side-effect scope verification

Before exercising an automation tool, compare its public schema/description with the handler that constructs the upstream request. Community integrations may describe a field as a target selector while the implementation uses it as sender metadata and broadcasts account-wide.

- Treat the actual upstream payload as authoritative.
- If requested scope and implemented scope differ, stop before the side effect and obtain explicit confirmation.
- For a single-device voice test, first query device inventory read-only, require one exact online match, and use a provider operation that carries that device's type and serial.
- Report transport acceptance separately from physical confirmation: an upstream `HTTP 200` proves acceptance, while the user hearing the message proves delivery.

## Cleanup

Whether capture succeeds or is abandoned:

- Stop the proxy and confirm the port is closed.
- Restore the Android Wi-Fi proxy to `None`.
- Remove the temporary user CA from Android.
- Remove temporary CA private-key material from the laptop unless it will be reused intentionally.
- Validate that secrets remain absent from Git status, logs, and chat.

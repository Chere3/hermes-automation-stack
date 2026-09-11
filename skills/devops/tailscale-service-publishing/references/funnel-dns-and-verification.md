# Funnel DNS and verification notes

## Validated behavior

After enabling Funnel, the local configuration can immediately show `Funnel on` while public recursive resolvers still return NXDOMAIN. Tailscale documents that public DNS records can take up to ten minutes to appear. Negative caching can make a recursive resolver lag behind the authoritative zone.

A reliable verification sequence is:

1. Read `tailscale funnel status --json` and confirm the intended `AllowFunnel` host:port.
2. Confirm `funnel-ingress-node` peers are present and online in `tailscale status --json`.
3. Query a public recursive resolver for A/AAAA records.
4. If it still returns NXDOMAIN, identify the authoritative nameserver for the tailnet domain and query it directly.
5. Once an authoritative A record exists, bypass stale recursive DNS without bypassing TLS:

```bash
curl -sS -L \
  --resolve 'node.tailnet.ts.net:8443:PUBLIC_INGRESS_IP' \
  -o response.html \
  -w 'http_code=%{http_code}\nremote_ip=%{remote_ip}\nssl_verify=%{ssl_verify_result}\n' \
  'https://node.tailnet.ts.net:8443/login'
```

Expected verification properties:

- HTTP status matches the application (often 200 for a login page).
- `remote_ip` is a public Funnel ingress IP, not the node's Tailscale IP or loopback address.
- `ssl_verify_result=0`.
- The retrieved login page contains the expected identity fields.

## Authentication checks

A public landing page with a `/login` link does not prove authentication is enforced for protected application data. Verify the actual login route and, where safe, request a known protected route while unauthenticated and confirm it redirects to login or returns the intended denial.

If registration must remain closed, verify the application's rendered configuration or UI rather than assuming it from deployment environment names. Do not submit credentials or attempt a login merely to prove that email/password inputs exist.

## Configuration preservation

Serve and Funnel entries can coexist on different ports. After changing one port, compare the complete read-back configuration and ensure:

- only the intended host:port is in `AllowFunnel`;
- other HTTPS listeners are unchanged;
- no reset operation erased unrelated routes.

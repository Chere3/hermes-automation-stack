# Private Tailnet Self-Hosting with Rootless Podman

Use this pattern for a single-user web application that should be reachable from the user's devices but not exposed to the public Internet.

## Deployment contract

- Audit the upstream license, maintenance state, image source, authentication defaults, registration behavior, data providers, and geographic coverage before deploying.
- Pin the application OCI image to an immutable manifest digest. A tag may be used only for discovery; deploy the resolved digest.
- Bind the application port explicitly to loopback, e.g. `127.0.0.1:18881:80`. Do not publish database, Redis, or worker ports.
- Keep generated application keys and database passwords in a mode-`0600`, gitignored environment file. Generate them directly into the file without printing them to tool output.
- When Compose interpolates `${...}` values for multiple services, pass the same file with `--env-file`; `env_file:` alone injects variables into a container but does not supply Compose-time interpolation.
- Disable optional telemetry, email campaigns, subscriptions, and unused integrations until intentionally configured.

## Tailscale Serve

Use Tailscale Serve as the only remote ingress:

```bash
sudo tailscale serve --bg --https=8443 http://127.0.0.1:18881
```

Choose an alternate HTTPS port when the hostname's default route already fronts another service. Verify that `tailscale serve status` says `tailnet only` and that the loopback listener remains bound only to `127.0.0.1`.

If the deployment host cannot resolve its own MagicDNS name, do not treat that as an application failure. Verify the exact HTTPS route and certificate using the current Tailscale IPv4 address:

```bash
host=example.tailnet.ts.net
ip=$(tailscale ip -4)
curl --resolve "$host:8443:$ip" "https://$host:8443/"
```

Use the public-looking MagicDNS URL only after the request is proven to traverse the Tailscale-only Serve route.

## Rootless persistence

Compose restart policies are not sufficient evidence of post-reboot recovery for rootless containers. Add a user systemd oneshot unit that runs `podman-compose ... up -d`, stops with `... down`, and uses `RemainAfterExit=yes`. Then:

- enable the unit under `default.target`;
- confirm `loginctl show-user <user> -p Linger` is `yes`;
- start the unit once and verify it is both `active` and `enabled`;
- re-run the HTTP readiness check after systemd takes ownership.

Do not reboot merely to test persistence unless the user explicitly authorizes it.

## Backups

For a MySQL-backed app with mutable application storage:

1. Run `mysqldump --single-transaction --quick` inside the database container without placing the password in host command arguments or output.
2. Export the application storage volume with `podman volume export`.
3. Compress into a temporary directory, compute SHA-256 checksums, then atomically move completed files into a mode-private backup directory.
4. Use a persistent user timer and a bounded retention policy.
5. Execute one backup immediately, verify every checksum, and inspect owner/mode/size before claiming backups work.

A timer being enabled is not backup verification; a successfully restored or at least checksummed first artifact is required. Restoration should be rehearsed before the dataset becomes valuable.

## Single-user onboarding

Registration may remain temporarily enabled only while the service is tailnet-only and the first user creates an account. After the user confirms the account exists:

- disable registration in configuration;
- recreate/restart only the application container as required;
- verify the login route still works and the registration route no longer accepts new accounts.

Never mark “registration closed” complete before this read-back verification.

## Verification checklist

- Application and database containers are healthy/running.
- Application responds on loopback and through the exact Tailscale HTTPS URL.
- Brand/configuration expected by the user appears in returned HTML.
- Listener is `127.0.0.1` only; database has no host port.
- Serve status is `tailnet only` and does not overwrite adjacent routes.
- User service is active/enabled; linger is enabled.
- First database and storage backups exist, are mode `0600`, and pass checksums.
- Registration state matches the actual onboarding stage.
- Provider availability claims are grounded in the provider's current supported-country catalog, not a marketing bank-name list.

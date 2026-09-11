# Podman Compose finance-app upgrade example

Validated pattern from a stateful self-hosted Laravel finance application. Values are illustrative; substitute the deployment's actual paths, names, tables, and endpoints.

## Deployment shape

- Git checkout on `main`.
- `podman-compose` launched by a `systemd --user` oneshot unit with `RemainAfterExit=yes`.
- App image from GHCR, pinned by digest in a private Compose override.
- MySQL 8 named volume mounted at `/var/lib/mysql`.
- App storage named volume mounted at `/app/storage`.
- Private env file remains untracked and mode-restricted.
- Backup timer dumps MySQL and exports app storage.

## Preflight

```bash
git status --short --branch
git remote -v
git branch -vv
git fetch --prune origin
git rev-list --left-right --count HEAD...origin/main
systemctl --user show APP.service \
  -p ActiveState -p SubState -p ExecMainStatus -p FragmentPath
podman ps --format '{{.Names}}|{{.Status}}|{{.Image}}'
```

Read the unit and Compose files before deciding how to restart. Confirm named-volume destinations and identify local untracked overrides.

## Backup verification

The working backup sequence was:

1. `mysqldump --single-transaction --quick --routines --events` from inside MySQL;
2. gzip the SQL stream;
3. `podman volume export APP_storage | gzip`;
4. SHA-256 both artifacts;
5. recompute hashes and fully decompress both gzip files;
6. retain the manifest with the artifacts.

A successful systemd backup service plus valid hashes and gzip streams provided a recovery point before deployment.

## Baseline data

Query stable business entities before and after, emitting sorted TSV. For a finance app these included users, spaces, accounts, transactions, categories, labels, budgets, and savings goals. Capture migration count separately.

Programmatically compare the two TSV maps while excluding `migrations` from strict equality. Avoid session, cache, queue, mail-log, or sync-log tables.

Also capture:

```bash
podman exec APP sh -c 'find /app/storage -type f | wc -l; du -sb /app/storage'
```

Exact storage bytes may change at startup; investigate only meaningful differences.

## Image-to-source proof

```bash
podman pull ghcr.io/OWNER/APP:latest
podman image inspect ghcr.io/OWNER/APP:latest \
  --format 'Digest={{.Digest}} Created={{.Created}} Revision={{index .Labels "org.opencontainers.image.revision"}}'
```

Require `Revision` to equal the fetched Git HEAD. Pin the reported registry digest in the private Compose file, then restart through the existing user unit.

Pulling this application image took roughly half an hour and emitted long quiet intervals. A single background pull completed correctly; launching repeated pulls would only waste bandwidth and complicate state.

## Post-deploy proof

```bash
systemctl --user show APP.service \
  -p ActiveState -p SubState -p Result -p ExecMainStatus
podman ps --format '{{.Names}}|{{.Status}}|{{.Image}}'
podman inspect APP_app_1 --format '{{range .Mounts}}{{.Name}}:{{.Destination}};{{end}}'
podman inspect APP_mysql_1 --format '{{range .Mounts}}{{.Name}}:{{.Destination}};{{end}}'
podman logs --since 10m APP_app_1
podman exec APP_app_1 supervisorctl status
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:PORT/
```

Verify the database reports healthy, startup migrations succeed, all Supervisor programs run, and volume names remain unchanged.

For a tailnet-only TLS listener bound to the Tailscale IP, loopback cannot test that port. If hostname resolution on the server is temporarily unhealthy, preserve TLS verification with:

```bash
curl --resolve HOSTNAME:PORT:TAILSCALE_IP \
  -sS -o /dev/null \
  -w '%{http_code}|tls=%{ssl_verify_result}\n' \
  https://HOSTNAME:PORT/
```

Expected `ssl_verify_result` is `0`. Do not use `-k` for the final verification.

## Completion evidence

Report only concise, verified facts:

- old and new Git revisions;
- new OCI revision/digest match;
- backup location and integrity status;
- unchanged named volumes;
- stable data-count comparison result;
- container/process health;
- local and external endpoint status;
- unrelated infrastructure warnings separately.

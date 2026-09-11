# Remote VPS Secret Bootstrap Pattern

Use this pattern when a human must enter a provider API key into an application running on a VPS.

## UX contract

- The user stays on their own device.
- The agent prepares the configurator on the VPS.
- The user runs one command:

```bash
ssh -t USER@STABLE_HOST 'python3 /absolute/path/configure_secret.py'
```

Prefer a stable Tailscale/MagicDNS name and offer the Tailscale IP as fallback. Resolve both from live state; do not guess.

## Configurator requirements

1. Read with `getpass.getpass()` so input is not echoed.
2. Strip only surrounding whitespace/quotes; never print any key fragment.
3. Validate through a minimal read-only provider operation before persistence, such as `GET /v1/models`.
4. On HTTP failure, parse only safe fields (`error.message`, error code, request ID), replace any occurrence of the supplied key with `[REDACTED]`, collapse whitespace, and truncate the message.
5. Persist atomically:
   - create a temporary file in the destination directory;
   - set mode `0600` before writing;
   - preserve unrelated existing variables;
   - flush and `fsync`;
   - `os.replace` into place;
   - enforce final mode `0600`.
6. Print the destination path and success metadata, never the value.

## Verification from the agent session

After the user reports completion, independently verify:

- expected variable name is present and non-empty;
- expected file path, owner, and mode are correct;
- modification time changed during the setup window;
- a downstream authenticated probe succeeds without printing its response body if it may contain sensitive data.

Do not treat “listo” as proof. The user may have reached a rejection/error screen or connected to a different host.

## Failure diagnosis

Distinguish these before asking for a new key:

- `401`: malformed, revoked, copied key ID instead of secret, or wrong auth header;
- `403`: valid identity lacking project/model entitlement, account restriction, or policy/region block;
- `404`: wrong endpoint/model ID or unavailable model;
- `429`: rate limit or trial quota;
- network/TLS: DNS, egress, proxy, certificate, or service outage.

When the first script collapses all failures into “key rejected,” improve the diagnostics and rerun. Do not repeatedly ask the user to regenerate keys without the provider's sanitized reason.

## Security pitfalls

- Never embed the key in the SSH command, heredoc, `curl -H` argv, chat message, or shell history.
- Do not use a remote graphical terminal merely to display a hidden prompt.
- Avoid proving success by `echo $KEY` or printing the destination file.
- Environment files are acceptable only as protected runtime stores when no stronger OS/service credential facility is available; prefer systemd credentials or a scoped secret manager for unattended production use.

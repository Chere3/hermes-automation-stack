# 1Password CLI and Service Accounts

Condensed provider-specific notes for secure interactive and unattended access. Commands and limitations were verified against 1Password CLI 2.x help and official Service Account documentation; re-check current docs when behavior matters.

## Desktop integration

For interactive local use:

1. Open and unlock the 1Password desktop app manually.
2. In Settings > Security, enable the platform authentication option where supported.
3. In Developer > Settings, enable **Integrate with 1Password CLI**.
4. Run `op signin`; it is idempotent and prompts only when authentication is needed.
5. Verify with `op whoami --format=json`, but expose only a sanitized boolean/account type/host—not email, IDs, or tokens.

A running app process is not proof that CLI integration is enabled or authenticated. If `op whoami` cannot connect, confirm app unlock and the Developer integration setting before changing credentials.

## Manual sign-in over SSH

Do not place the account password in a command or `.env`. Add the account using non-secret metadata and let `op` prompt interactively:

```bash
eval "$(op account add --signin \
  --address my.1password.com \
  --email USER@example.com \
  --shorthand personal)"
```

The prompt collects the Secret Key and account password with hidden input. For later shells:

```bash
eval "$(op signin --account personal)"
```

Manual sign-in creates an `OP_SESSION` token in the current shell. In the observed CLI help, it expires after 30 minutes of inactivity. End it explicitly when appropriate:

```bash
op signout --account personal
unset OP_SESSION
```

Do not use `echo PASSWORD | ...`, `export OP_PASSWORD=...`, shell arguments, or expect scripts that embed the password.

## Service Account limitations

Official 1Password documentation states that Service Accounts cannot be granted access to built-in:

- Personal vaults
- Private vaults
- Employee vaults
- the default Shared vault

This is a provider restriction, not a CLI bug. Service Accounts also require a compatible account/plan and a sufficiently recent CLI (official docs cite CLI 2.18.0 or later).

## Recommended setup

1. Create a non-built-in shareable vault such as `Automation`.
2. Select only the items the automation actually needs.
3. Copy/move those items deliberately and document which copy is authoritative.
4. Create a Service Account scoped to that vault with `read_items` only.
5. Do not grant `write_items` or `share_items` unless a concrete workflow requires them.
6. Capture the one-time Service Account token directly into a protected credential store; never print it into chat or logs.
7. Supply it to the process as `OP_SERVICE_ACCOUNT_TOKEN` only at runtime.
8. Verify an allowed metadata/read operation without printing secret values, then verify an excluded vault is inaccessible.

1Password Service Account creation supports vault permission specifications such as `read_items`; `write_items` and `share_items` require broader authority. Exact creation syntax can change, so inspect `op service-account create --help` immediately before creation.

## Storage options

Preferred order for a local Linux service:

1. systemd credentials or another service-native secret injection mechanism
2. OS keychain/secret service
3. mode-0600 root/service-owned file sourced only at process start
4. plaintext `.env` only as a last resort, with strict permissions and no source control/backups

The token remains powerful even if scoped read-only. Rotation and revocation should be tested before depending on unattended access.

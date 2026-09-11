# 1Password Service Accounts

Use this reference for unattended 1Password CLI access. Check the current official docs before applying it because private-vault restrictions, CLI flags, and account requirements can change.

Official starting point: `https://developer.1password.com/docs/service-accounts/get-started/`

## Hard vault restriction

1Password Service Accounts cannot be granted access to these built-in vaults:

- `Personal`
- `Private`
- `Employee`
- The default `Shared` vault

Do not promise a workaround through permissions. Create a separate non-built-in vault and copy only the items required by the automation. A full mirror is possible only by duplicating items into a shareable vault, which increases exposure and synchronization burden.

## Desktop integration versus service accounts

- **Desktop integration:** interactive. The user unlocks the app and enables **Settings → Developer → Integrate with 1Password CLI**. The agent must not enter the account password, approve biometrics, or click MFA/security prompts.
- **Service account:** unattended. The CLI authenticates with `OP_SERVICE_ACCOUNT_TOKEN`; it does not unlock the human desktop app or grant access to built-in personal/private vaults.

If `op whoami` reports that it cannot connect to the desktop app while the app process is running, check whether the app is unlocked and CLI integration is enabled. Treat this as setup state, not as evidence that the CLI or app is broken.

## Least-privilege setup

1. User unlocks 1Password and enables CLI integration.
2. Create a non-built-in vault such as `Hermes Automation`.
3. Identify exact item/field references needed by each automation.
4. Copy only those items into the automation vault without displaying their values.
5. Create a Service Account with `read_items` only for that vault.
6. Service-account vault access and permissions are immutable after creation. Do not plan to add `write_items` later. When a concrete one-time write workflow exists, create a separate short-lived account for the exact vault with `read_items,write_items`; do not grant `share_items`, vault creation, deletion, or administration.
7. Verify that unrelated vaults are invisible. For the durable read-only identity, verify writes fail; for a temporary writer, verify effective write permission before the time-sensitive enrollment when possible, then revoke/delete it after persistence and read-only validation.

## Token creation and capture

Current CLI families expose a command shaped like:

```text
op service-account create <name> --expires-in <duration> --vault "<vault>:read_items"
```

Confirm exact flags with the installed CLI and official docs before execution.

The token is shown once. Never let it enter conversational stdout. Prepare a protected destination first, set a restrictive umask, and redirect creation output directly to that destination. Do not pass the token as a command-line argument. If a UI is the only creation path, the user handles the one-time token manually.

For Linux services, prefer a service-manager credential facility or a mode-0600 file readable only by the service user. Inject `OP_SERVICE_ACCOUNT_TOKEN` into only the target process. A project `.env` is a last-resort compatibility choice, not the default.

## Generated-secret handoff with read-only identities

A read-only service account can consume existing OAuth client credentials but cannot persist a newly issued refresh token. Decide and verify the handoff before starting a short-lived authorization-code flow:

1. Keep the durable service account read-only. Because 1Password service-account permissions are immutable, do not plan to widen it during enrollment.
2. Prefer a user-mediated local handoff into one exact password-manager item. If the automation host receives the token first, stage it only in a mode-`0600` file outside the repository, transfer it through an authenticated channel to the user's device, import it into the intended item, verify metadata-only retrieval, then securely remove the staging file.
3. If a machine-assisted one-time write is necessary, create a separate expiring service account scoped to the intended non-built-in vault with explicit `read_items,write_items`. Accept its one-time token only through hidden input on the trusted terminal; never through chat, arguments, logs, screenshots, or captured tool output. Remove any temporary token file after the subprocess exits, whether it succeeds or fails.
4. If item read succeeds but `op item edit` is denied, classify it as missing effective write permission—not a lookup problem. Preserve the staged mode-`0600` OAuth/rotation artifact, create a correctly scoped writer, and retry persistence without repeating upstream authorization.
5. Delete staged secret material only after durable persistence and canonical read-only validation succeed. Revoke/delete the temporary writer immediately afterward.
6. If unattended token rotation truly requires recurring writes, create a separate narrowly scoped item/vault and grant only the minimum item-write capability supported by the provider. Verify unrelated writes remain denied.

## Item lookup robustness

- Resolve durable automation references to item UUID + vault UUID when possible; titles are human labels and may contain trailing/invisible characters or later be renamed.
- If exact-title lookup fails but metadata listing shows the item, filter metadata narrowly, require exactly one match, take its UUID, and fetch by UUID. Do not fall back to broad exports or print field values.
- Verify required field labels as a set and report only missing labels/booleans, never values.

## Safe verification

Verify without exposing secret values:

- `op whoami` succeeds under the service-account environment.
- Vault listing contains only the intended automation vault(s).
- Item metadata/title lookup works for an expected item.
- A write attempt against a disposable fixture is denied for read-only access, or permissions are inspected from the service-account overview when even a fixture write is undesirable.
- Clear temporary environment variables and remove temporary files after testing.

Never run broad item exports or print JSON item documents merely to prove access; those outputs may contain concealed and non-concealed sensitive fields.

## Rotation and revocation

- Record the service-account name, vault scope, permissions, token creation/expiry, and consuming services—never the token.
- Rotate before expiry and update one consumer at a time.
- Verify the new token, then revoke the old token.
- If compromise is suspected, revoke immediately and audit the service account's recent activity from 1Password.com.

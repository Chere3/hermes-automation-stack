# Multi-workspace and identity-linked API keys

Use this when an existing provider credential must be reused by another local service and the credential can act across multiple workspaces/projects.

## Safe discovery and transfer

1. Inspect only credential metadata first: provider, label, auth type, source, status, and whether a secret field is populated.
2. Select the intended credential deterministically. Do not take the first token in a mixed OAuth/API-key pool.
3. Keep the secret inside one local process: read the protected source, write or inject the destination, and emit only `<present:true>`, mode, and path metadata.
4. Preserve the destination before editing, use an atomic replace, and enforce mode `0600` for environment-file fallbacks.
5. Never print the credential, place it in shell arguments, or copy OAuth tokens intended for a first-party client into an unrelated application.

## Anthropic identity-linked keys

Personal and service-account keys may be identity-linked and span several workspaces. Such a key can authenticate yet return HTTP 400 with:

`anthropic-workspace-id is required when authenticating with an identity-linked API key`

Working sequence:

1. Ask only for the workspace ID (`wrkspc_...`), not another API key. Validate and preserve the identifier literally.
2. Send `anthropic-workspace-id` on model-list and message requests alongside `x-api-key` and `anthropic-version`.
3. Query `/v1/models` and select the exact available model ID requested by the user; do not infer the current alias from memory.
4. Run a minimal message request and verify HTTP success, returned model, stop reason, and a tiny deterministic response.

A workspace ID is routing metadata, not the API secret, but avoid publishing it unnecessarily.

## Frameworks without a workspace environment variable

Inspect the installed provider client before assuming an environment variable exists. If the client accepts additional headers but its published config exposes only key and URL:

- Prefer an application-owned provider config override that adds the workspace header.
- For immutable prebuilt containers, mount that config file read-only rather than editing files inside the running container.
- Base the override on the config shipped by the deployed package version so unrelated provider settings remain intact.
- Re-check the override whenever the dependency or container image is upgraded; copied package config can become stale.
- Avoid an extra reverse proxy solely to add one header when the application client already supports additional headers.

## Verification

After restart/recreation:

- Confirm the secret file remains mode `0600` and the config mount is read-only.
- Inspect effective provider/model/header-presence values without printing secrets or workspace IDs.
- Confirm workers and HTTP health.
- Execute one real request through the application's own AI abstraction, not only a direct provider probe.
- Check user-data counts or other persistence invariants if the deployment restart touched stateful containers.

## Provider-ready is not feature-ready

A successful model call proves only the provider seam. Before claiming the application's AI capability is enabled, trace the complete user-visible path:

1. **Global switches:** provider credentials, provider/model config, and any broad subsystem switch such as workers, scheduled jobs, or mail/drip delivery.
2. **Feature rollout:** environment defaults plus persisted feature-flag rows. Some flag systems cache the first resolved value, so changing the environment alone may leave existing users disabled.
3. **Per-user gates:** consent, plan/entitlement, onboarding state, opt-in preferences, and account restrictions.
4. **Data prerequisites:** minimum record counts, eligible uncategorized items, a closed reporting period, or another artifact the UI requires.
5. **Execution trigger:** import event, queue dispatch, scheduler window, or explicit command. A configured capability may not run until this fires.
6. **Presentation:** verify where the feature actually appears. Some applications expose no general “AI” menu and render a link or banner only after the first result exists.

Use the application's own dry-run or status command as the tight loop. If it reports zero work, inspect the command's source and each gate before changing configuration. Do not trust help text blindly: validate whether a user selector expects an email, UUID, username, or database primary key.

After triggering one real feature run, verify all of these before reporting success:

- the expected database artifact exists;
- AI output and generation timestamp are populated without printing private content;
- the queue is empty and failed-job count is zero;
- the user-visible route or controller now receives the artifact;
- the provider request succeeded, preferably with a request ID or usage metadata.

Tiny smoke calls may cost far below the billing console's display precision or update asynchronously. Explain that distinction; an unchanged rounded balance does not refute a request confirmed by provider request ID and application-persisted output.

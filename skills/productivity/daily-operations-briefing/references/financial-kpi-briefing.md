# Financial KPI Sources in Daily Briefs

Use this pattern when a recurring written or spoken brief needs personal-finance signals from a finance application.

## Access boundary

Prefer the application's own authenticated API or MCP server over direct database reads. Create a dedicated machine credential with read-only scope only; never reuse a broad interactive token and never request the plaintext token in chat. For unattended jobs, store it in a password-manager automation vault or a mode-0600 credential file outside the repository, then inject it only into the collector process.

For MCP, verify the real authorization boundary:

1. An unauthenticated functional request is denied.
2. An SDK client can initialize and list tools.
3. The credential exposes the intended read tools.
4. A write/destructive tool is unavailable or denied.
5. A metadata-only check records successful use without printing the token.

If the product offers `read` and `read_write`, choose `read`. Do not accept annotations such as `IsReadOnly` as the access-control proof; verify the token's effective abilities.

## Minimal tool allowlist

A useful collector usually needs only:

- cashflow for an explicit date range, including previous-period comparison;
- net worth and direction over a bounded range;
- spending grouped by root category, drilling down only when a root change is material;
- current budgets with allocated, spent, and remaining values;
- account metadata only when needed to interpret freshness or currency.

Avoid transaction search by default. Merchant names, free-text descriptions, notes, account names, IDs, and individual charges rarely belong in a spoken brief.

## Deterministic collector contract

Keep retrieval and narration separate. The collector should:

- compute periods in the user's explicit timezone;
- call a fixed read-only tool allowlist with bounded dates;
- normalize money into one declared currency and unit;
- retain `null` for missing figures;
- emit source timestamps and a freshness status;
- precompute comparisons only when both periods are present;
- bound category and budget arrays to material exceptions;
- return a safe unavailable sentinel on auth/network failure rather than falling back to raw database access;
- print JSON only, with no credentials or protocol debug dumps.

For morning briefs, previous-day finance can be misleading when imports or bank sync are delayed. Prefer month-to-date cashflow plus a freshness marker unless the source proves the prior day complete. Evening briefs may use the current cutoff but must call it partial when the day is still open.

## Editorial selection

Blend finance into the same adaptive narrative as operations, health, and weather. Do not create a permanent “finance section” or recite a dashboard.

Good spoken signals:

- savings rate changed materially versus the comparable period;
- spending moved because one root category changed materially;
- net worth direction changed across a meaningful window;
- a budget is exceeded or close enough to require action;
- a source is stale enough that no conclusion is justified.

Prefer direction, percentage, and consequence over exact balances. Speak at most one or two finance observations plus one grounded action. Exact balances, merchant names, debts, or account names require explicit user preference because audible delivery can be overheard.

## Delivery-channel changes

When a user says “send briefs only to the speaker,” pause the written brief job itself. Do not disable its silent data syncs, device-auth preflights, delivery-receipt watchdogs, or genuine failure alerts unless the user also requests silence from alerts. Verify the device jobs remain enabled and the written job is paused.

## Whisper Money specifics (validated)

Whisper Money (Laravel) exposes a streamable-HTTP MCP server at `/mcp`, authenticated with Sanctum personal access tokens. A token created with scope `read` carries only `mcp:read`; `read_write` adds `mcp:write`. Write tools remain *visible* in `list_tools` regardless of scope — `WriteTool::respond()` rejects them at call time with `This token is read-only.` So tool visibility is not the access boundary; call-time refusal is.

If a user pastes a token that was created as `read_write`, do not silently accept it. Downgrade the abilities server-side (Sanctum `personal_access_tokens.abilities`) to `["mcp:read"]` and re-verify by calling a write tool and expecting the read-only refusal.

Useful read tools: `get_cashflow(from,to)`, `get_net_worth(from,to,granularity)`, `list_budgets()`, `spending_by_category`, `search_transactions(limit=1)` for a freshness probe. Money values come back as **minor units** (divide by 100); currency is reported separately.

When the deployment has no bank connector (e.g. Enable Banking lacking coverage), the data is import-driven: derive freshness from the newest transaction date and mark `stale` past ~7 days, so briefs suppress conclusions instead of reporting a real zero.

Python client note: with recent `mcp` SDKs, `streamable_http_client(url, http_client=...)` yields **two** values, and tool schemas are on `tool.input_schema` (not `inputSchema`).

## Verification

Before enabling live delivery:

1. Run the finance collector and inspect periods, units, freshness, null handling, and bounded output.
2. Verify read-only MCP discovery and one real KPI call through the same credential path the cron will use.
3. Add the normalized finance block to every relevant brief collector and update each prompt's evidence/privacy rules.
4. Run parser/tests and both collectors manually.
5. Exercise the voice renderer in dry-run mode; do not trigger audible playback outside the authorized window.
6. After the first scheduled run, verify the speaker receipt and the connector's metadata-only `last_used_at` or equivalent audit evidence.

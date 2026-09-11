# Internal Alexa CLI, MCP Core, and Endpoint Inventory

Use this pattern when repeated Alexa operations have started accumulating as one-off scripts.

## Architecture pattern

Build one runtime-neutral core and thin adapters:

- `transport`: injected `fetch`, cookie headers, status handling; no Node-only APIs so Cloudflare Workers and Node can share it.
- `devices`: case-insensitive exact-name resolution; reject partial, missing, duplicate, non-Echo, and offline targets.
- `policy`: classify operations as `read`, `write`, or `global-write`; reads are allowed, writes dry-run by default, live writes require explicit confirmation, and global writes require a separate authorization gate.
- `redaction`: recursively remove serial/DSN, customer, endpoint/entity/appliance IDs, cookies, authorization and token fields from every public result and error.
- domain modules: alarms, volume, DND, smart-home state/control, behaviors.
- `client`: reusable operations implementing read → optional one write → bounded verification.
- CLI adapter: JSON-only stdout, stable error codes, nonzero failures, credential injection from local secret wrapper.
- MCP adapter: calls the same client directly; do not make MCP tools call REST routes that call Alexa again.

## Command safety contract

- Make writes dry-run unless `--confirm` (or equivalent typed MCP field) is supplied.
- Resolve and validate the exact device during dry-run.
- Do not automatically retry a live behavior: a timeout can still have caused audio or a state change.
- Check idempotence before writing. For a recurring alarm, return `already_exists` instead of creating a duplicate.
- After an accepted write, re-read the relevant state and require exactly the intended result.
- Keep account-wide announcements out of the normal CLI allowlist. A descriptive `name` field is not a device selector.

## Hardened shared transport

The shared transport is a security boundary, not a generic HTTP helper:

- Accept only relative paths rooted at `/`; reject absolute URLs, scheme-relative URLs, backslashes, and control characters. Construct with `new URL(path, pinnedBase)` and assert the final origin even after the path precheck.
- Pin the Amazon host in code, set `redirect: "error"`, and attach an explicit abort timeout. Classify caller cancellation separately from timeout and generic network failure.
- Normalize caller headers with `new Headers(init.headers)`, then set protected `Cookie`, CSRF, and user-agent values afterward so callers cannot override credentials or authentication context.
- Reject empty successful responses by default. Add an explicit per-request `allowEmptyResponse` option only for upstream writes documented to return an empty `2xx/204`; never enable it on inventory or state reads.
- Parse successful non-empty bodies inside the transport and convert malformed JSON into a stable invalid-response error rather than leaking a raw parser exception.
- Validate required response arrays at each inventory boundary. Missing `devices`, `notifications`, volumes, DND statuses, smart-home endpoints, or state arrays are invalid upstream responses, not empty inventories. This prevents an incomplete notifications response from being interpreted as “no alarm exists” and triggering a duplicate write.
- Convert network, timeout, malformed-response, and non-2xx failures into stable public error codes. Do not include upstream response bodies, URLs with identifiers, or credential values in messages.
- Redact sensitive assignments embedded inside strings as well as sensitive object keys; apply redaction to both success and error envelopes in CLI and MCP adapters.
- Do not automatically retry behavior preview or physical writes. A timeout can mean the action happened and the response was lost.

## Strict CLI argument parsing

For a safety-oriented internal CLI, a hand-written `args.indexOf(flag) + 1` parser is insufficient: `--text --confirm` can treat `--confirm` as the text while also authorizing the live write.

- Reject a value-taking flag when the next token is missing or begins with `--`.
- Reject duplicate value-taking flags.
- Parse and validate all authorization-relevant values before any write.
- Keep boolean authorization flags separate from value-taking flags.
- Add a regression test showing malformed arguments cannot reach the transport.

## Exact smart-home identity binding

For lights and other appliances, resolving a friendly name and later asking a separate “primary device” helper for an ID can act on the wrong endpoint. Bind all identifiers from the same discovered record:

1. Query Nexus `CustomerSmartHome` and filter by the exact primary category.
2. Match the friendly name case-insensitively by equality; reject partial, zero, and duplicate matches.
3. Preserve each identifier family without substituting one for another: Nexus `endpointId`, CHRS `entityId`, `legacyAppliance.applianceId`, and `mergedApplianceIds` may serve different APIs.
4. If state discovery requires trying several identifiers, try only variants belonging to that same exact endpoint in one bounded read. Associate the returned state with the identifier that produced it.
5. Use the state-producing identifier for Phoenix control and the bound endpoint ID for Nexus mutations. Never resolve a separate “primary” appliance after resolving the friendly name.
6. Pre-read and post-read the same bound target. If none of that endpoint's identifiers returns usable state, fail closed with `STATE_UNAVAILABLE`; do not issue a blind write merely because discovery succeeded.
7. Public output contains only the friendly name, category, capabilities, and sanitized state.

Prefer the control family proven for that capability. Existing source code or mocked tests are not live verification that Phoenix and Nexus are interchangeable for power, brightness, color, or thermostat operations. A discovered endpoint plus mocked request construction is not enough to authorize a physical write when live pre-state is unavailable.

## Preserving MCP names while hardening behavior

Legacy MCP tool names may be retained as compatibility aliases, but their implementation should become a thin adapter over the core. Update descriptions and schemas at the same time so they no longer promise optional IDs or first-device fallback. Treat changed input fields as an explicit compatibility change and test tool registration plus invocation, not just TypeScript compilation.

## Recurring weekday alarms

A safe fallback when cookie auth is available but bearer-authenticated alerts v2 is not:

1. Read uncached notifications and check for an existing exact-device alarm.
2. Submit one exact-device `Alexa.TextCommand` behavior using a natural-language recurrence request.
3. Re-read notifications and verify one active alarm at the requested time.
4. Normalize weekday representations. A verified Spanish-locale response used `recurringPattern: XXXX-WD`; other generations may expose weekly `rRuleData.byWeekDays` or `trigger.recurrence.byDay`.

## Endpoint reverse-engineering inventory

“Exhaustive” must always be scoped to evidence. Prefer a reproducible generator over a hand-maintained list:

1. Scan the project source plus a pinned public-client source snapshot.
2. Extract literal and template paths passed to transport helpers.
3. Normalize dynamic segments and query values.
4. Deduplicate by host and normalized route.
5. Record inferred methods, source files, occurrence counts, and evidence level.
6. Emit machine-readable JSON and a human-readable table.
7. Maintain a much smaller curated operational allowlist separately.

Evidence vocabulary:

- `live-verified`: sanitized read or separately authorized write observed on the current account.
- `source-verified`: reviewed implementation exists, but not necessarily called live.
- `source-observed`: static extractor found the route; host/method/payload may still be ambiguous.

Never equate a source-snapshot inventory with all private Amazon APIs. Never call every discovered route merely to “verify” it. Unknown routes stay research-only; POST GraphQL is `write-or-query` until its operation body is classified.

## Testing and verification

Use TDD for the core safety contracts:

- exact target resolution and rejection cases;
- write/global-write authorization gates;
- recursive redaction;
- recurrence normalization;
- transport error sanitization;
- dry-run does not issue a write;
- idempotent alarm creation.

Then run full unit tests, type-check, lint, dependency audit, CLI help/registry checks, and live read-only device/alarm calls. Re-run the complete gate after the final code edit; an earlier green run does not validate later patches. If an execution/tool limit interrupts before that rerun, report the artifact as unverified and resume with the gate first. A successful compile is not proof the MCP runtime is active; restart/deploy and exercise MCP separately only with authorization for that service action.

For physical controls, distinguish four evidence levels in the report: static source support, mocked unit test, live dry-run/read verification, and separately authorized live write plus post-read. Do not promote one level into another.

## Dependency audit rule

Treat dependency audit findings as blockers or explicit debt, especially in an authenticated MCP service. Upgrade in a separate compatibility-tested change when major framework versions may affect Cloudflare Workers or MCP transports; do not silently bundle risky framework upgrades into unrelated Alexa behavior work.

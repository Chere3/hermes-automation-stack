# Connected health devices: private cloud APIs and BLE

Use this reference when a consumer health device has no public developer API but its mobile app exposes account history and the device also broadcasts or serves BLE data.

## Discovery order

1. Verify whether a documented public/partner API exists. Search official developer portals, support/privacy/export pages, app-store disclosures, and first-party integrations.
2. Check official OS health bridges (Health Connect, Google Fit, Apple Health) and user data export before reverse engineering.
3. Map the mobile architecture without credentials: runtime discovery service, authentication provider, API protocol, regional endpoints, and app package assets.
4. Audit active community clients as protocol evidence, not trusted deployment artifacts. Read implementation, maintenance history, tests, license, host validation, pagination, error handling, and mutations.
5. Compare cloud and local BLE semantics before choosing a source.

## Cloud vs BLE

Prefer a private cloud read-only connector when the user needs historical sessions and the official app already uploads them. Cloud schemas may expose timestamps, duration, mode, score, pressure distribution, coverage, and per-zone summaries, but model-dependent fields can be null.

Use BLE when the user needs live telemetry, wants cloud independence, or cloud fields are absent. Distinguish:

- passive advertisements: least intrusive, usually timer/state/mode/coarse pressure;
- direct GATT: richer pressure, battery, retained-session and motion data, but may occupy the device's only connection slot;
- a charger/base bridge: can preserve the phone/device connection while forwarding local data, if the model supports it.

A remote VPS cannot directly collect household BLE reliably. Use an on-premise collector such as an Android companion, Home Assistant/ESPHome proxy, or small local gateway, then send normalized read-only events to the VPS over an authenticated private channel.

## Do not confuse pacer sectors with physical position

A sequential `sector` or pacer interval often means only elapsed routine timing. It is not proof of a physical mouth/body zone. Physical-position features may require raw IMU windows plus a proprietary classifier in the vendor app. Treat cloud fields such as `coveragePercentage` or `zonedBrushTime` as vendor-derived metrics, and label them separately from directly measured BLE values.

Before promising zones:

- identify the exact hardware model and charger/base;
- confirm whether the official app shows a zone map for that session;
- query whether advanced fields are populated for that model;
- never relabel timed pacer sectors as physical coverage;
- do not redistribute proprietary model assets.

## Official health bridges, exports, and app storage

- Verify both that the vendor app integrates with the health platform **and** that the platform has a semantically appropriate record type. A generic app-store declaration that an app collects “health information” does not prove Health Connect, Google Fit, or Fitbit synchronization.
- A downstream health API cannot produce a device metric unless an upstream app actually writes it. Check deprecation timelines, and do not force unsupported wellness events into unrelated record types.
- Treat a data-subject access/portability archive as a manual import seam until its schema, completeness, and repeatability have been inspected. Rights and terminology vary by jurisdiction; do not label every request “GDPR.”
- Modern Android app-private storage normally requires app support, backup eligibility, a debuggable build, root, or instrumentation. Treat it as a research seam, not a durable production API, and first determine whether passive/local telemetry already supplies the required metrics.
- Absence from a store description is not proof of impossibility. Report “no current public documentation or verifiable evidence found,” separating marketing text, developer-declared data safety, observed behavior, and captured protocol evidence.

## Safe Android-to-VPS collector

- Collect locally with a visible foreground service where Android background rules require it; build sessions on-device, queue offline, and upload minimized summaries rather than raw motion streams by default.
- Pseudonymize hardware addresses, preserve parser version/provenance, and distinguish complete, partial, missing, and unsynchronized records.
- Enroll with a one-time QR or short-lived code. Generate a non-exportable device key in Android Keystore and authenticate uploads with mTLS or signed requests; no vendor password is required for BLE collection.
- Provide deletion, export, revocation, retention limits, encrypted transport/backups, idempotent ingestion, and least-privilege scopes.

## Legal and evidence discipline

- Link first-party privacy/export pages, platform documentation, source repositories, and the current official statute—not search snippets.
- Interoperability exceptions are normally conditional on lawful access, good faith, independent implementation, narrow purpose, and no broader infringement. They do not automatically override contracts, privacy law, unauthorized-access rules, or anti-circumvention limits. Label legal discussion as non-legal advice.
- Keep work read-only and confined to the user's own account and hardware. Do not distribute vendor code, keys, certificates, proprietary assets, or captured credentials.

## Safe architecture for an unofficial cloud connector

- Perform onboarding locally; never request account password, MFA, refresh token, app token, or captured traffic through chat.
- Prefer a one-time local mobile login observation that yields a renewable session over storing the account password. Verify certificate pinning behavior on the current app before planning capture.
- Store renewable credentials in a secrets manager; runtime service accounts should be read-only.
- Allowlist exact discovery, identity-provider, and API hosts. Validate discovered endpoints before sending any token; configuration tampering must not become token exfiltration.
- Implement only named read operations. Omit mutations from the client entirely rather than relying on caller discipline.
- Bound pagination, date windows, response size, retries, and concurrency.
- Sanitize failures: do not print response bodies that may contain tokens, health records, or identifiers.
- Normalize provenance per metric (`cloud_vendor_derived`, `ble_advertisement`, `ble_gatt`, `local_inferred`) and preserve null for unsupported fields.
- Store sensitive health-adjacent history locally with restrictive permissions and a minimal retention policy.
- Treat community one-file clients and embedded app constants as protocol references; rebuild the production connector with tests and host guards.

## Provenance-aware reconciliation

Keep immutable source observations separate from normalized sessions. Each normalized metric should retain `value`, `source`, `observed_at`, and completeness/quality. Recommended source handling:

- vendor cloud/app output is authoritative for guided coverage and zone maps;
- a retained GATT summary can refine aggregate duration/pressure when valid;
- passive BLE preserves the live timeline and remains evidence even after cloud enrichment;
- conflicts are retained and surfaced rather than silently overwritten.

Deduplicate with bounded tolerances over device pseudonym, start time, duration, mode, and stable source IDs. Ambiguous matches fail closed. Re-run a rolling lookback after every sync so delayed vendor enrichment updates prior sessions idempotently; 72 hours is a practical starting point for twice-daily brief pipelines. Never delete raw evidence merely because normalized rows were recomputed.

Use `null`/`unavailable` for absent fields and distinguish `complete`, `partial`, `basic`, and `unsynchronized` sessions. A missing coverage map is not `0%`, and an absent zone is not an unbrushed zone.

## Brief recommendations from device telemetry

Expose normalized summaries and trends to the agent by default; retain raw BLE/GATT/IMU evidence locally for reconciliation and debugging. Separate outputs explicitly:

```text
observation -> trend -> suggestion
```

Recommendations must be completeness-aware:

- suppress zone/coverage advice for unguided or incomplete sessions;
- suppress pressure advice when pressure evidence or sampling is insufficient;
- permit bounded suggestions for repeated short duration, repeated high-pressure exposure, missed routine, or recurring guided-zone gaps;
- never infer disease, damage, diagnosis, or treatment.

Include a non-clinical disclaimer whenever a suggestion is emitted. Align sync times with downstream briefs rather than using an arbitrary exact interval, and do not activate cron until a guided and unguided physical session have reconciled successfully and two consecutive production syncs are idempotent.

## Oral-B iO evidence snapshot (verified 2026-08-31)

- Google Play package `com.pg.oralb.oralbapp` declared optional health-information and device-ID collection, encrypted transit, and deletion requests. This indicated collection, not a public API or Health Connect integration.
- No current public documentation or verifiable evidence was found for Oral-B brushing-session sync to Health Connect, Google Fit, or Fitbit; Health Connect had no dedicated dental-brushing type, and Google Fit support was scheduled to end in 2026.
- P&G exposed a Mexico rights portal at `https://preferencecenter.pg.com/es-mx/datarequests/`; it is suitable for manual access/portability requests, but archive format and recurring automation must not be promised.
- MIT-licensed `Bluetooth-Devices/oralb-ble` demonstrated passive parsing of timer, pacer sector, pressure, mode, state, and signal. `thomasgregg/oralb-ha` documented local read/notify characteristics plus retained latest-session summary `FF29`, and a typical one-client BLE slot that can make direct reads compete with the app or iO Sense.
- Mexico's official Ley Federal del Derecho de Autor art. 114 Quáter(I) contained a narrow good-faith interoperability exception for a legally obtained program copy. Use it only as a counsel-review boundary, not blanket permission.

## Persistent Android BLE collectors

“Always in background” on modern Android must be implemented as a user-visible, policy-compliant operating mode, not a hidden daemon:

- The user explicitly enables collection once; persist that choice and use a visible foreground-service notification while scanning.
- Request only modern nearby-device permissions (`BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT`), notification permission, and the exact foreground-service type needed. Do not request location merely as a legacy BLE workaround when the target/runtime API does not require it.
- Queue sessions locally first and upload idempotent batches with WorkManager so network loss does not lose brushing/activity data.
- A `BOOT_COMPLETED` receiver may restore a previously enabled collector only where the OS permits that foreground-service type. Catch `ForegroundServiceStartNotAllowedException` and surface `requires_intervention` rather than looping or silently failing.
- “Always” cannot override force-stop, revoked permissions, Bluetooth-off state, or OEM battery management. Expose health states such as `running`, `degraded`, `permission_missing`, `bluetooth_off`, and `requires_intervention`.
- Never hide the notification or use accessibility/device-admin tricks to evade lifecycle policy. Offer battery-optimization guidance only when observed runtime evidence shows the collector is being killed.
- Test process restart, boot restoration, Doze, permission revocation, Bluetooth toggles, offline queueing and user-stopped foreground-service behavior on the physical device before calling the collector durable.

## Verification

- Run fixtures covering pagination, null advanced metrics, regional endpoints, stale/revoked refresh tokens, malformed sessions, and timestamp/time-zone bucketing.
- Prove every functional operation is read-only at the GraphQL/REST operation allowlist.
- Probe one recent session and compare timestamp, duration, mode, pressure/coverage, and zone values against the official app.
- If BLE is added, test coexistence with the phone app/base and document whether the device supports one or multiple simultaneous clients.
- Keep medical interpretation out of the ingestion layer; analytics and recommendations must be clearly non-diagnostic.

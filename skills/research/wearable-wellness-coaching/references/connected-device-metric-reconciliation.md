# Connected-device metric reconciliation and non-clinical gating

Condensed from building a read-only Oral-B iO Series 6 metrics pipeline (cloud + passive BLE + optional post-session GATT summary) feeding twice-daily Spanish briefs. The patterns generalize to any multi-source consumer health device.

## Source landscape for connected oral care

No public official Oral-B/P&G developer API existed at time of research — no OpenAPI spec, SDK, OAuth scopes, or partner portal that can be verified or requested publicly. That absence does not prove no private contracts exist; it means there is nothing a third party can legitimately sign up for. Verify current state before repeating this claim.

| Source | Identifier | Realistically provides | Caveats |
|---|---|---|---|
| Vendor cloud (app backend) | `cloud` | Timestamp, duration, mode, model, battery, score, coverage %, per-zone time, pressure distribution | Private API; can change without notice; advanced fields often `null` unless the app was connected and the session was guided |
| Passive BLE advertisements | `ble_passive` | Session start/end, elapsed time, mode, pressure normal/high flag, pacer interval, state, battery | No history — only what you observe live; does not consume the device's single connection slot |
| Post-session GATT read | `gatt_ff29` | Last-session summary: duration, high/low pressure totals and events, mode, ending battery | Competes for the device's single BLE client slot; must be opt-in, short-timeout, and disabled on contention |

Health Connect / Google Fit / Fitbit had no documented brushing integration and no standard tooth-brushing data type. Do not architect around them.

## The pacer trap

Community BLE parsers expose `sector_1..sector_8`. This is the **timer/pacer interval**, i.e. which quadrant-slot the countdown is in — not where the brush physically is in the mouth. The vendor app derives real mouth position from accelerometer/gyroscope streams through a proprietary classifier whose weights are not in any community library.

Name the field `pacerSector` in code and document it inline. Real zone data must come from the cloud's `zonedBrushTime` / `coveragePercentage`, or be reported as unavailable.

## Schema shape that held up

```
raw_observations      -- immutable; UNIQUE(source, source_id) and UNIQUE(source, content_hash)
normalized_sessions   -- rewritten per reconciliation window
metric_provenance     -- (session_id, metric_name) -> value, source, observed_at, quality
sync_ledger           -- source, started_at, completed_at, status, error_code
```

Reconciliation deletes and reinserts only `normalized_sessions` rows whose `start_at` falls inside the window; `raw_observations` is append-only. `metric_provenance` cascades from the normalized row so a rewrite cannot leave orphaned provenance.

Set the database file to `0600` and its parent directory to `0700` during migrate.

## Reconciliation algorithm

1. Build a compatibility graph over observations: different source, same device id, start times within ~90 s, durations within ~30 s, same mode.
2. Take connected components.
3. If a component contains two observations from the *same* source, it is ambiguous — explode it into singletons rather than guessing.
4. Derive a stable `session_id` from the sorted member `source_id`s (hash), so repeated runs converge on the same identity.
5. Per-field precedence: guided cloud wins coverage/zones; FF29 wins aggregate pressure; passive BLE wins timeline; otherwise fall back to the primary (cloud if present).
6. Status is `complete` only when multiple sources corroborate; a lone observation stays `partial`.

Test that `reconcile(list) == reconcile(reversed(list))` — order independence catches most precedence bugs.

## Brief rendering rules that prevent false alarms

- Absent duration/pressure/coverage renders as `no disponible`, never `0`. A test asserting `"0%" not in text` is cheap and catches regressions.
- Report guided vs unguided counts separately; they carry different data richness.
- Report pending-reconciliation count so the user knows a number may still improve.
- Completeness ladder: `basic` (no sessions) → `partial` (sessions but missing enrichment) → `complete` (nothing pending, coverage and zones present).

## Recommendation engine gating

Structure every suggestion as three explicit fields: `observed` → `trend` → `suggestion`. This keeps the measurement separable from the advice and makes the disclaimer honest.

Gates that proved necessary:

- Minimum history (3 days) before any rule fires; below that, return zero suggestions and `disclaimer_required: false`.
- A rule fires only when a majority of qualifying days (≈60%, minimum 2) meet the condition — never on a single day.
- Pressure rules require days that actually carry pressure data. No pressure source → no pressure suggestion.
- Coverage rules require days where `zones_status == "reported"`. If zero guided days exist, emit only a `guided_session_hint` telling the user how to obtain a map — do not critique coverage that was never measured.
- Attach the disclaimer to the result *and* set `disclaimer_required` when any suggestion exists.

Guard the vocabulary in tests. A test that scans every emitted string for `gingivitis`, `caries`, `enfermedad`, `diagnóstic`, `tratamiento` is a cheap, durable brake on scope creep into clinical claims.

Spanish disclaimer used for this user:

> Orientación informativa basada en el dispositivo; no es diagnóstico ni sustituye atención dental.

## Sequencing

Build and verify against fixtures before touching the user's real account. Order that worked: domain → reconciliation → storage → brief → recommendations → hardened cloud client (fixtures only) → signed private ingestion. Physical-device and live-credential steps come last, are driven by the user locally, and never involve credentials passing through chat.

Do not enable scheduled syncs until a real session has been captured and reconciled end to end. A cron firing against an unvalidated parser produces confident, wrong history.

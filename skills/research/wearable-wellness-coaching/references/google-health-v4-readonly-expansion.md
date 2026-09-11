# Google Health API v4 read-only expansion audit

Use this note when auditing a Google Health connector against all granted read-only scopes while minimizing retained sensitive data.

## Authoritative inspection workflow

1. Inspect the live Discovery document rather than relying on remembered Fitbit/Google APIs:
   - `https://health.googleapis.com/$discovery/rest?version=v4`
   - Record `revision` because methods, scopes, and schemas can drift.
2. Recursively enumerate every method under `resources`, including method ID, HTTP verb, path, and declared OAuth scopes.
3. Treat `schemas.DataPoint.properties[*].description` as the authoritative source of exact kebab-case collection IDs. Do not confuse supporting structures (`Food`, measurement units) with recorded data-type collections.
4. Derive supported rollup identifiers separately from the union properties of:
   - `DailyRollupDataPoint`
   - `RollupDataPoint`
   A collection in `DataPoint` is not necessarily rollup-capable, and some identifiers such as `total-calories` exist only as rollups.
5. Inspect method descriptions for type-specific filtering rules. Important examples:
   - ECG list filtering supports `electrocardiogram.interval.start_time >= ...`; end-time filtering is not supported.
   - Sleep list filtering is by physical or civil end time.
   - `exportExerciseTcx` requires both activity and location consent and `?alt=media` for raw TCX.
6. Compare official IDs and methods against source code with exact file/line references. Separate “parser exists” from “type is actually fetched”; dead parsers can create a false impression of coverage.
7. Search the complete Discovery JSON for alleged product endpoints such as coach/coaching. A zero-result method/schema/resource search supports the bounded claim “no endpoint exists in this Discovery revision,” not a timeless claim about every Google product.

## Scope and schema caveats

- The generic data-point methods declare broad accepted scopes, but the Discovery does not publish a definitive `scope -> dataType` matrix. Label semantic grouping as such rather than presenting it as an explicit official mapping.
- As observed in revision `20260805`, nutrition read schemas and rollups existed while `googlehealth.nutrition.readonly` was absent from both `auth.oauth2.scopes` and the generic read-method scope lists. Surface this as an official-schema inconsistency and recommend a token-safe status-only probe before production reliance. Never compensate by requesting write permission.
- Location has no standalone coordinate `DataPoint` collection. Precise exercise GPS is exposed through TCX export; ordinary exercise summaries already carry useful distance metrics.
- Sleep is a direct session collection but is absent from the rollup unions. Read `Sleep.summary`; do not invent a sleep rollup call.

## Privacy-preserving daily design

- **ECG:** retain session count and, only if needed, classification counts/aggregate average BPM. Drop waveform samples, scaling factor, sampling rate, exact timestamps, and device identifiers before persistence.
- **IRN:** retain notification count and coarse onboarding/enrollment state. Drop alert windows, heartbeat sequences, exact intervals, and device metadata. Do not reinterpret SaMD output as a diagnosis.
- **Location:** prefer not fetching TCX when exercise summary distance is sufficient. If a concrete feature requires TCX, process it transiently for coarse distance/elevation or route-present counts, then discard coordinates, point timestamps, route IDs, and raw TCX.
- **Nutrition:** retain daily totals and completeness/log count, not food names or event times. Suppress coaching when logs are incomplete.
- **Sleep/activity/metrics:** prefer official summaries or daily rollups. Do not retain stage segments, laps, splits, free-text notes, or raw physiological samples when aggregate fields satisfy the use case.
- **Profile/settings:** these are context resources, not daily data types. Cache minimally (for example units, timezone, coarse age band, stride settings) instead of duplicating them in every daily row.

## Reporting checklist

- State that no authenticated calls were made if the task was schema-only.
- State explicitly that no credentials, tokens, authorization codes, or payloads were printed.
- Include both local source file/line references and official source URLs.
- Distinguish already fetched, merely parsed, and wholly unused categories.
- Give exact official method IDs and kebab-case identifiers, with caveats for identifiable-only `get` and rollup support.
- For a Health Coach question, inspect resources/methods/schemas/scopes and report whether the endpoint exists in the inspected revision; recommend local, non-clinical coaching if absent.

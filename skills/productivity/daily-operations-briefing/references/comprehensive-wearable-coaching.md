# Comprehensive wearable coaching for daily briefs

Use this reference when a user expects Google Health/Fitbit analysis beyond steps and distance.

## Editorial contract

- Treat wearable data as a longitudinal decision-support stream, not a dashboard.
- Integrate only material signals into the main narrative; never create a mandatory health mini-brief.
- Consider activity, active-zone minutes, exercise, sedentary time, sleep/stages, heart rate/resting heart rate, HRV, respiratory rate, nocturnal SpO2, temperature deviation, energy, body measurements, hydration and nutrition when actually present.
- Convert evidence into one or two concrete actions for the day/week. Explain the personal pattern supporting each action.
- Never infer `0` from missing data, assume an authorized scope has records, or treat a partial day as complete.
- Do not diagnose, prescribe treatment, assert causality, or label one wearable reading normal/abnormal. Persistent patterns or symptoms may justify suggesting professional review.

## Discovery and ingestion

1. Use the current Google Health API v4 discovery document as the source of truth.
2. Derive candidate data-type IDs from the `DataPoint` union property descriptions; there is no general list-data-types endpoint.
3. Probe each candidate read-only with `pageSize=1`. Record only sanitized availability metadata during inventory; do not log values, tokens, IDs or raw payloads.
4. Distinguish endpoint families:
   - `dataPoints:dailyRollUp` for supported interval/sample/log types.
   - `dataPoints.list` with civil-date filters for daily summaries and sessions such as exercise/sleep.
   - `reconcile` only when overlapping interval sources require de-duplication.
5. A type appearing in the rollup union may still reject a particular request/account. Validate each endpoint against the linked account and fall back to a compatible read path rather than forcing it.
6. Normalize official units explicitly: protobuf durations to minutes, millimeters to kilometers, grams to kilograms, milliliters as logged, and documented kcal/bpm/ms/percent fields.
7. Store normalized daily summaries, not raw heartbeats, food entries, GPS traces, ECG waveforms or event identifiers unless the user explicitly needs that retention.
8. Reject non-finite numeric values (`NaN`, positive/negative infinity) as missing before JSON/SQLite persistence.

## Snapshot shape and quality

- Keep `day`, `schema_version`, normalized metrics, and a `data_availability` manifest with `present`/`missing` keys.
- Preserve `null` for absent metrics.
- Mark the current civil day partial using the user's timezone.
- Include previous-day deltas, week-to-date aggregates and per-metric observation counts.
- A calendar backfill row is not evidence that a metric exists on that day. Baseline readiness must count actual finite observations per metric.

## Personal baselines and coaching

- Prefer a rolling personal median (for example 28 days) over universal thresholds.
- Require at least seven prior finite observations before calling a personal trend ready; include count and window in evidence.
- With shorter history, label conclusions low-confidence and use transparent week-to-date observations rather than pretending a mature baseline exists.
- Combine signals when possible. Example: lower HRV plus elevated resting heart rate plus reduced sleep supports a conservative recovery suggestion more than any one signal alone.
- Do not penalize a single partial day for low activity.
- Logged hydration/nutrition are records, not proof of total intake. Say “registrado” when completeness is unknown.
- Weight changes over one or two days are fluctuations, not body-composition conclusions.

## Skill and source hygiene

- Prefer official, inspectable fitness/nutrition skills and authoritative public-health sources.
- Do not install community skills merely because they claim “doctor”, “medical-grade” or “functional medicine”. Audit code, credential requirements, outbound services, storage and clinical claims first.
- Keep third-party exercise/nutrition lookup services separate from private wearable storage; never send the user's health history unless explicitly authorized and necessary.

## Verification

- TDD parsers with representative official response shapes, missing fields, partial records and non-finite values.
- Run the real snapshot in memory first and print only metric names/counts.
- Verify database mode, schema version, present/missing counts and collector propagation without printing health values.
- Exercise every brief collector in dry-run/context-only mode and confirm it includes longitudinal trends and personalized insights.

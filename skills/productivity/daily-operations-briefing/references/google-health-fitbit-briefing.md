# Google Health + Fitbit in Daily Briefs

Use this pattern when Google Health is linked to Fitbit and the user wants health/activity KPIs incorporated into recurring written and spoken briefs.

## Architecture

1. Keep OAuth/API synchronization separate from briefing collection.
2. Run a deterministic, silent sync shortly before each brief. Refresh the access token in memory, fetch both the current and previous local calendar day to absorb delayed Fitbit synchronization, and upsert normalized snapshots.
3. Persist snapshots in a mode-0600 SQLite database inside a mode-0700 directory. Do not log tokens, identity IDs, or raw medical payloads.
4. Make briefing collectors read SQLite with `mode=ro`; they must not refresh OAuth or mutate health state.
5. Feed the model the requested day, previous day, source update timestamp, `day_complete`, normalized KPI values, and precomputed deltas.

## Scheduling Pattern

For briefs at 06:00, 20:45, and 21:10 in one timezone, a practical sync schedule is 05:35 and 20:35. The morning brief reads the prior closed day. Both evening briefs may share the 20:35 snapshot, explicitly labeled partial.

Verify the scheduler's timezone and `next_run_at`. A successful sync should emit no stdout; nonzero exit or stderr should alert.

## Data Semantics

- `null` means no data. Never turn it into zero.
- Authorized scopes prove permission, not that Fitbit supplied records. Report unavailable streams as absent data, not authorization failure.
- `day_complete=false` means steps, distance, calories, and other totals are partial at the snapshot cutoff.
- Only compare days when both values exist. Precompute deltas deterministically; do not ask the model to infer them from prose.
- Keep units explicit and normalized, for example steps, km, kcal, and kg.
- Report observations only. Do not diagnose, classify values as healthy/abnormal, infer causality, or give medical advice.
- Spoken briefs should mention only a compact subset of useful available KPIs; omit missing fields rather than reading a long absence inventory.

## Editorial Integration and Weekly Recommendations

- Health/activity data belongs inside the same adaptive operational narrative. Do not create a fixed health section, transition, heading, or source-specific mini-brief unless the day's evidence genuinely makes that structure useful and the user has not prohibited it.
- Expose a deterministic `week_to_date` summary: local week start, snapshot count, complete-day count, totals that explicitly include any partial day, and an average computed only from complete days.
- The model may suggest practical next steps for the remaining days of the same week when complete-day activity or the available complete-day average is clearly low—for example, reserving time for a walk or prioritizing general movement.
- Frame these as concrete planning and general-wellbeing suggestions, not medical advice. Do not diagnose, prescribe intensity, classify a value as healthy/abnormal, or invent a clinical target.
- Never make a low-activity judgment from an early partial day alone. Near an evening cutoff, a partial value may support only a light, non-alarmist suggestion for the rest of the week, explicitly recognizing that the day is incomplete.
- Structure, ordering, emphasis, and length remain the model's daily editorial responsibility; channel and safety constraints must not turn into a recurring template.

## Secret Boundary

A read-only 1Password service account can supply client ID and client secret. If that identity cannot write the OAuth refresh token back, keep the refresh token in a dedicated local mode-0600 file until a human performs the durable 1Password write. Never weaken 1Password permissions merely to automate that write, and never expose tokens in chat, command arguments, logs, or brief context.

## Verification

- Exercise a real identity call and at least one real data query.
- Prefer Google Health `dailyRollUp` or reconciled all-source data to avoid duplicate source totals.
- Compare one rollup against reconciled segments before trusting the normalization.
- Test snapshot composition, missing-data handling, unit conversion, SQLite permissions, read-only brief collection, and previous-day deltas.
- Run every written/spoken collector manually.
- Validate Alexa scripts with `--dry-run` and a health-bearing sample; do not perform live playback merely to test integration.

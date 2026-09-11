# Targeted Alexa Delivery for a Daily Operations Brief

Use this pattern when an existing source-grounded written briefing must also be spoken on one specific Echo.

## Architecture

1. Keep source collection deterministic and read-only. Collect current weather separately from operational data, and define the reporting window explicitly (for a 06:00 brief, usually current weather plus the prior local calendar day's operations).
2. Export a shared collector function that accepts an explicit calendar date. Written and spoken jobs should call the same durable journal/state/artifact collector directly, aggregating across any number of changing operator sessions.
3. Do not make the spoken job read a prior briefing's rendered output by cron job ID when the durable sources are available. Direct date-scoped collection avoids session coupling and cron-to-cron coupling.
4. Let the model consolidate facts into a short spoken script; do not let it discover operational facts ad hoc.
5. Save the exact script to an audit file before playback.
6. Validate the script locally, then send it through a device-targeted playback endpoint.
7. Keep scheduler delivery local if Alexa is the only requested output, avoiding a duplicate chat message.

## Targeting Safety

- Do not assume an `announce` API targets the device named in a `name` field. Some Alexa implementations use that field as the sender name and broadcast account-wide.
- For one-Echo delivery, query the device inventory, match the exact `accountName`, require `deviceFamily == ECHO`, require `online == true`, and require exactly one match.
- Use the selected device's internal type, serial, and customer ID only inside the local request. Never print them.
- Reject groups and account-wide targets unless the user explicitly authorizes a broadcast.
- Pin the expected target name in the playback helper rather than accepting an arbitrary target from generated model output.

A proven targeted speech request uses Alexa's behaviors preview endpoint with a sequence containing one `Alexa.Speak` operation and the selected device identifiers. A successful request returns HTTP 200; an empty response body can still be normal.

## Spoken-Brief Contract

- Require an exact opening phrase when the user specifies one.
- Bound the script by characters and intended duration. Roughly 700–1,200 Spanish characters is suitable for a 60–90 second executive brief; enforce a hard maximum.
- Use natural spoken prose: no Markdown, bullets, URLs, file paths, IDs, emojis, or implementation jargon.
- Recommended order: greeting; date/current weather; one practical weather recommendation; executive operational outcomes; intentional holds/risks; current vacancies or monitored changes; anonymous product-change counts; one or two priorities; short close.
- If a project or company name must remain private, remove it from the model's source context where possible and also reject it in the final playback helper. Prompt-only suppression is insufficient.
- If a source is missing or stale, say so briefly rather than synthesizing a plausible update.

## Freshness and Change Windows

- Morning briefs should not blindly reuse an evening snapshot. Perform fresh read-only checks before speech when practical, compare them with the latest baseline, and do not mutate the monitor's baseline from the briefing collector.
- Keep separate fields for changes recorded during the prior calendar day and changes observed since the last monitor run. This avoids double-counting.
- Weather must be current for the listener's confirmed location and timezone; include temperature, apparent temperature, daily high/low, precipitation probability, and wind only when available.

## Scheduler and Playback Guardrails

- Schedule in the user's timezone and verify the scheduler's computed `next_run_at` offset.
- Restrict the playback helper to a narrow local-time window around the scheduled run. Dry-run validation should bypass this time gate but never contact Alexa.
- Validate in this order: source collector succeeds; script syntax compiles; script length/opening/privacy checks pass; dry-run passes; live request returns HTTP 200.
- Do not manually run the live scheduled job late at night merely to test it. Test the collector and dry-run path, then let the first authorized scheduled window exercise playback.
- The host, scheduler, network, Alexa session, and target Echo must be available at run time. Mention this dependency to the user.
- Limit retries after an ambiguous playback response to prevent duplicate spoken briefs.

## Interaction Pitfall

When the user asks to reopen a short-lived capture process, perform that requested action directly and pause unrelated debugging or cleanup. If the process is designed to exit after a successful capture, explain that behavior only after reopening it and observing the result.

# Google Calendar in Scheduled Spoken Briefs

Use this pattern when a daily brief needs actionable calendar context without turning the brief into a calendar mutator.

## Authorization and durability

- Request only the Calendar service when no other Google data is needed. A calendar write scope enables later approved event changes, but the brief collector itself stays read-only.
- Store the OAuth client, PKCE state, and refresh token with mode `0600`; remove temporary transfer copies.
- Treat OAuth consent as permission, not proof of API availability. Verify with a real read.
- External consent apps left in Testing can issue refresh tokens that expire after seven days for non-basic scopes. Publish to Production and reauthorize once before calling a recurring brief durable.
- Personal accounts enrolled in Advanced Protection may block an unverified private OAuth client. Do not recommend disabling protection; for Calendar-only use, share the intended calendar with a service account instead.

## Deterministic collector

1. Resolve an explicit IANA timezone and construct a half-open window `[local midnight, next local midnight)`. Morning briefs normally use today; evening briefs normally preview tomorrow.
2. Enumerate every calendar and paginate both calendar and event lists. Exclude cancelled events and invitations where the authenticated user declined.
3. Normalize timed events into local ISO timestamps. Preserve all-day end dates as exclusive, and preserve tentative/accepted status.
4. Emit bounded fields only: title, start, end, all-day flag, useful location, sanitized calendar label, status, self-response, generation time, and source window. Omit descriptions, attendee email addresses, meeting URLs, event IDs, and raw calendar IDs unless the user explicitly needs them.
5. Detect every timed overlap pair. Also flag consecutive gaps under 30 minutes; set `locations_differ` only when both locations exist and differ. Never estimate travel duration from names alone.
6. Return `status=unavailable` with a non-secret error class when authentication or API access fails. Absence is not an empty agenda.

## Editorial contract

- Blend events into the brief rather than reading every calendar row.
- Morning: prioritize all-day commitments, the next timed event, material locations, conflicts, and tight transitions for today.
- Evening: preview tomorrow's actionable commitments, conflicts, and preparation needs.
- Say that tentative events are tentative. Do not revive cancelled or declined events.
- Never speak calendar names that contain account addresses, attendee addresses, IDs, links, or implementation paths.
- A brief request never authorizes creating, editing, or deleting an event.

## Verification

- Unit-test all-day/timed normalization, cancelled and self-declined filtering, overlap detection, and tight-transition boundaries.
- Run one live read and inspect only counts, windows, availability, and conflict totals in logs; do not dump private titles during verification.
- Run the speech renderer in dry-run mode with valid length/opening constraints. Do not trigger audible playback outside the authorized schedule.
- Read back the cron job: correct timezone, morning/evening windows, enabled state, and device-only delivery must remain unchanged.

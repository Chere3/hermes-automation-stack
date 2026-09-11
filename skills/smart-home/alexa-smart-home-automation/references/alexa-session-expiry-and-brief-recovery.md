# Alexa session expiry and scheduled-brief recovery

Use this when a scheduled exact-Echo brief generates successfully but no audio plays.

## Failure isolation

Treat these as separate outcomes:

1. Scheduler fired.
2. Collector produced source context.
3. Model generated and validated speech text.
4. Exact-device helper attempted the private Alexa API call.
5. Amazon accepted the request (`HTTP 200`).
6. The Echo physically rendered audio.

A cron run can report `ok` when the agent itself completed and accurately reported a nested playback failure. The authoritative playback evidence is the side-effect helper's exit code plus its per-date ledger, not the outer cron status alone. Record states such as `started`, `accepted`, and `uncertain_or_failed` and suppress automatic retries after ambiguous failures.

## Ephemeral runner migration pitfall

When a secure runner injects credentials into a unique `dev.vars.XXXXXX` file and deletes it after the child exits, do not leave scheduled helpers pointed at a fixed project `.dev.vars` path or a symlink to `$XDG_RUNTIME_DIR/.../dev.vars`. That fixed path will be absent by design.

- Scheduled live helpers must invoke the secure runner themselves and consume only its `ALEXA_VARS_PATH`.
- Direct transport execution without `ALEXA_VARS_PATH` should fail explicitly with “secure runner required,” not search the project tree.
- Never use `.migration-backup`, `.old`, or discovered dotenv files as an automatic fallback; they can contain expired credentials and bypass the current secret source.
- Remove dangling project symlinks and stale credential backups after the migration is verified.
- Add two independent silent checks: a read-only inventory preflight shortly before delivery and a post-delivery watchdog that requires a durable `accepted` receipt for the exact Echo and HTTP 200.

## Diagnosing HTTP 401 safely

An Alexa `HTTP 401` means the current mobile-session cookies are no longer accepted, even when:

- 1Password injection succeeds.
- Both required fields exist and are nonempty.
- The collector and dry-run pass.
- Bridge or tunnel services remain active.

Before diagnosing, anchor the incident to the workflow timezone and inspect the ledger for that exact calendar date. A reply to a watchdog alert may arrive just after the next scheduled run; reading yesterday's receipt can produce a plausible but wrong explanation. Correlate the same-day ledger's `attempted_at` with the matching cron output, then inspect the nested speaker result rather than the outer cron status.

Verify without exposing values:

1. Confirm the 1Password service-account token and reference file exist with restrictive permissions.
2. Inject into a temporary mode-0600 file.
3. Report only whether required keys are present/nonempty/not placeholders.
4. Run the canonical read-only exact-device checker through the same secure 1Password runner used by scheduled playback. Its output should expose only a sanitized HTTP code or exception type.
5. If that request returns `401`, classify the cookies as expired/invalid; do not blame volume, DND, ngrok, NLU, or the brief renderer.

A generic adapter error such as `ALEXA_NETWORK_ERROR` is not specific enough to distinguish authentication from transport failure. Do not stop there: use the canonical secure-runner checker. When it returns an exact `HTTP 401`, that result supersedes the generic network label for root-cause reporting. Keep the report layered: brief generated, exact-device helper exited nonzero, no Amazon `HTTP 200` receipt, and current read-only authentication check returned `401`.

## Safe Android recapture after secret-store migration

Do not assume an old capture addon still writes to the automation's current secret source. If cron now injects from 1Password, a capturer that writes a project `.dev.vars` is stale and will not restore the job.

Preferred sequence:

1. Capture only `ubid-main` and `at-main` through a temporary, allowlisted mitmproxy addon.
2. Save them atomically to a dedicated pending dotenv file outside the repository, with parent mode `0700` and file mode `0600`; never log values.
3. Shut the proxy down automatically when both cookies are captured.
4. Validate the pending credentials with a read-only Alexa device query before changing the durable secret item.
5. Update only those two fields in 1Password using the human's authenticated write-capable identity. Keep the unattended service account read-only.
6. Re-inject from 1Password and repeat the read-only query.
7. Perform audible playback only with explicit current authorization.
8. Remove the pending file, stop the proxy, restore Android Wi-Fi proxy to `None`, and remove the temporary user CA.

Complete login and OTP with the proxy disabled. Re-enable it only after the authenticated page is visible, then refresh the minimal Amazon/Alexa page needed to emit cookies. If the user becomes unavailable, close the temporary listener rather than leaving it exposed indefinitely; preserve no partial cookie values.

## Alerting lesson

Alexa-only cron delivery can hide playback failures from chat. For operationally important briefs, add a separate failure signal based on the playback ledger or make the outer job fail when playback fails. Do not infer voice success from `last_status: ok` on an agent-driven cron job.

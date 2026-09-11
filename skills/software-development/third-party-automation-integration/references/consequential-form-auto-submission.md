# Consequential form auto-submission

Use this reference for job applications, registrations, claims, intake forms, and other submissions that create a durable external record but do not involve payment.

## Architecture

Keep four stages independent and idempotent:

1. **Discovery** records canonical first-party URLs and source IDs.
2. **Evaluation** checks title, explicit geography, eligibility, legitimacy, fit, and required facts.
3. **Staging** writes a durable record with `pending | apply | skip | applied`, field answers, warnings, blockers, and artifact paths.
4. **Submission** consumes only `apply` records and revalidates the live posting before touching the form.

A generic word such as `Remote` never overrides an explicit incompatible country or region. Unknown geography is `eligibility unconfirmed`, not eligible. Aggregator URLs may aid discovery, but submission requires the canonical first-party ATS URL.

## Standing authorization versus hard stops

When the user grants standing authorization such as “always apply,” encode it once in the user-layer policy and stop asking for approval on each eligible record. Resolve stable defaults there (salary strategy, contractor/startup acceptance, notice period, work authorization, sponsorship, optional demographics).

Standing authorization does **not** permit:

- invented or embellished facts;
- CAPTCHA, MFA, password, magic-link, or permission-dialog handling without the user;
- submission with unresolved required fields or ambiguous eligibility;
- duplicate/cross-channel applications;
- automatic retries after an ATS rejection or rate limit;
- marking `applied` without durable first-party confirmation.

Report only the irreducible user inputs as short bullets: login/magic link/MFA/CAPTCHA, a factual answer absent from the profile, or a genuine material ambiguity. Do not re-ask choices already covered by policy.

## Reliable unattended runner

- Use a non-blocking filesystem lock (`flock -n`) so scheduler ticks cannot overlap.
- Put hard bounds around reasoning subprocesses, e.g. `timeout --signal=TERM --kill-after=30s 600s ...`.
- Keep evaluation batches small enough to finish inside one scheduler session; submission of already-staged records must continue even when no new evaluation finishes.
- Do not start bounded evaluation in the background from an agent cron. Foreground execution plus timeout makes completion and cleanup observable.
- Rebuild and validate the staging index after partial or timed-out runs.
- Track every browser, evaluator, and helper process started by the run; close them in cleanup while preserving only the dedicated browser profile.
- Test the runner contract: exclusion lock, triage timeout, evaluation timeout, auto-apply decision rule, and bounded batch size.

## Exact-bound browser interaction on Linux

For a visible dedicated Chromium profile controlled through Linux AT-SPI/CUA, launch with:

```bash
google-chrome-stable \
  --ozone-platform=x11 \
  --force-renderer-accessibility \
  --no-first-run \
  --no-default-browser-check \
  --user-data-dir="$PROFILE" \
  --new-window "$URL"
```

`--force-renderer-accessibility` is the key step that exposes page controls instead of only the top-level browser frame. Add `--remote-debugging-port=0` only when an exact, locally owned DevTools binding is needed; bind and authorize the exact PID/window/session rather than attaching heuristically.

Interaction loop:

1. Start one declared CUA session and bind the exact native `(pid, window_id)`.
2. Prefer a reusable driver-owned `isolated_named` profile for unattended work. Prepare it before asking the user to authenticate; never copy a personal profile into it.
3. For direct CLI preparation, `browser-approve` requires a genuine local interactive approval. A chat message granting intent does not satisfy that host gate and must never be converted into an agent-sent `APPROVE` keystroke through `tmux`, PTY automation, or token scraping. The agent may stage a terminal session that is visibly waiting, but the user must attach and type the confirmation. Keep token handling entirely in that same local terminal: guide the user through both approval and `browser_prepare` there, using a hidden shell variable if needed, then verify only the resulting prepared profile. Do not ask the user to send the token through chat, do not read it from a terminal pane, and do not stop at “token generated” without giving a safe local consumption path.
4. Capture/reindex the exact window and prefer typed semantic refs when the bind is exact and `mutation_allowed=true`.
5. If the typed bind is heuristic or `mutation_allowed=false`, do not treat that alone as a total automation failure. Switch to the native, snapshot-bound ladder: AX element action; then pixel action from the same fresh screenshot after a real no-op/refusal; then `delivery_mode:"foreground"` only after background delivery is proven ineffective or refused.
6. Act once and re-capture after every action. Never reuse element tokens or pixel coordinates after a new snapshot/navigation.
7. If an AX write reports success but the field remains visually empty, treat it as failure. Do not repeat blind typing; advance one rung and verify the rendered field.
8. A navigation/scroll action, form-open action, final submit, and first-party confirmation are distinct states. Only the final success page or durable ATS reference proves submission.

Authentication is a prerequisite, not a submission failure. The handoff should require the user to perform only passwords, magic links, MFA, CAPTCHA, or a genuinely missing factual answer. Preserve the reusable isolated profile, resume the staged record automatically afterward, and keep form completion/submission on the agent side. Report the handoff as short bullets with one immediate action per blocker; put the action summary at the end.

## Upgrades with local integrations

Before running a project updater, inspect its system-path manifest. If it includes locally modified providers, scanners, or tests, do not update blindly. Create a recoverable WIP ref/branch, apply the upstream update in isolation, reapply local changes, and rerun focused regressions plus the full suite. An available update is not itself a production blocker.

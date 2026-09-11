# Session-chain escalation pattern

This reference captures a proven pattern for a controller launched by a user systemd unit, wrapped in tmux, and driven by a self-chained Claude Code `/loop`.

## Failure mode

A scheduled turn can wake correctly, fail on its first API call, and abort before scheduling the next wakeup. The Claude process remains alive at an idle prompt, so process-only supervisors report healthy forever. The durable liveness signal is the active controller transcript mtime, not process existence.

Resolve the transcript as:

1. Find `~/.claude/sessions/<pid>.json` entries whose `cwd` exactly matches the controller root.
2. Require the PID to be alive and `/proc/<pid>/cmdline` to still identify the expected controller executable; this rejects stale mappings after PID reuse.
3. Validate non-empty string `sessionId` and normalize `startedAt` before choosing the newest valid session.
4. Map the controller root to Claude’s dashed project directory.
5. Check `<sessionId>.jsonl` mtime against the maximum legitimate loop delay.
6. Propagate internal probe/parser exceptions as a non-zero service result. `DEAD` is a valid verdict; an exception is not.

## Claude API-error extraction

Claude Code transcripts place the marker at the event top level, not inside `message`:

```json
{
  "type": "assistant",
  "isApiErrorMessage": true,
  "message": {
    "role": "assistant",
    "content": [
      {"type": "text", "text": "Please run /login · API Error: 401 OAuth access token has expired."}
    ]
  }
}
```

Scan line by line and keep the last parsed event satisfying both:

- `event.type == "assistant"`
- `event.isApiErrorMessage is true`

A cheap candidate prefilter may search for the key name, but never require exact JSON spacing. Support `message.content` as either a string or a list of text parts. Collapse newlines and bound the final length.

Before sending, redact common credential forms: bearer values, `sk-...` keys, JWTs, and explicit API/access/refresh-token or secret assignments. The diagnostic should explain remediation without becoming a secret-exfiltration path.

## Hermes/WhatsApp delivery

A verified command shape is:

```bash
rc=0
timeout 30 "$HERMES_BIN" send \
  --to whatsapp:Alias --quiet \
  --subject "Controller requires intervention" \
  --file "$message_file" || rc=$?
```

Before invoking it, parse `${HERMES_HOME:-$HOME/.hermes}/gateway_state.json` and require:

```text
platforms.whatsapp.state == connected
```

The CLI’s existence is insufficient because WhatsApp delivery depends on the Hermes gateway. Log disconnected state separately from a non-zero CLI exit. Validate `mktemp`, `chmod 0600`, body write, and cleanup; notification preparation failures must never reach Hermes with an empty/partial body.

## Minimal state machine

Suggested files under the agent metrics directory:

- `.watchdog.lock`
- `.last_watchdog_restart`
- `.watchdog_consecutive_restarts`
- `.watchdog_failure_since`
- `.watchdog_last_alert_attempt`
- `.watchdog_last_alert`
- `.watchdog_recovery_pending`
- `.watchdog_recovery_attempt`
- `watchdog.log`

Use a non-blocking `flock` across liveness evaluation, cooldown, restart, and all state transitions. This protects against a manual invocation racing the systemd timer even though systemd serializes the same oneshot unit.

### Alert attempt versus delivery

A disconnected gateway is a preflight failure: do not create an attempt marker, so the next bounded restart can retry immediately after reconnection.

Once preflight succeeds, persist `.watchdog_last_alert_attempt` *before* invoking Hermes. This is an idempotency fence. A timeout is ambiguous because the backend may have accepted the message; therefore any actual CLI invocation consumes the repeat window. Exit `0` additionally writes `.watchdog_last_alert`.

If the success-state write fails after exit `0`, the attempt marker still blocks rapid duplicates. Re-alert only after the configured repeat interval. Apply the same attempt fence to recovery notifications.

### Recovery

On `OK`:

1. Read whether an alert was delivered or ambiguously attempted.
2. Reset count and episode start.
3. Create recovery-pending state.
4. Clear escalation timestamps.
5. Attempt the concise recovery send using its own attempt marker.
6. Remove pending and attempt state only after exit `0`; ambiguous failures wait for the repeat interval, while a disconnected gateway remains immediately retryable.

## State integrity

- Set `umask 077` before creating operational state.
- Use temp-file-plus-rename atomic writes.
- Persist the restart timestamp before issuing `systemctl restart`; abort the restart if cooldown persistence fails, otherwise disk errors can cause restart thrash.
- Validate numeric knobs before any liveness or restart action.
- Absence can mean the documented initial value. Corruption must be logged and replaced with a conservative value: preserve cooldown, suppress duplicate alerts, and avoid silently losing a failure count.
- Return non-zero for internal probe failures or unknown verdicts so systemd does not record a false success.

## Isolated test harness details

Use a temporary `HOME`, `HERMES_HOME`, controller root, fake `systemctl`, and fake Hermes binary. Explicitly override `HERMES_HOME`; otherwise a test can accidentally read the operator’s real connected gateway.

Create a fake long-lived process with `argv[0]` identifying the controller, point the session mapping at that PID, and manipulate transcript mtime. Set restart cooldown to zero only in test scenarios that need repeated recovery attempts. Capture fake CLI arguments and `--file` body.

Cover:

- threshold, repeat interval, reset, and recovery;
- gateway disconnected then reconnected;
- CLI non-zero/timeout ambiguity;
- two simultaneous watchdog invocations;
- invalid numeric config and malformed state;
- flexible JSON whitespace and credential redaction;
- actionable command/message content.

Do not run the production watchdog manually while a controller action is in flight. After isolated tests pass, allow the existing systemd timer to execute one natural healthy check and verify exit `0`, no restart, and no new incident state.

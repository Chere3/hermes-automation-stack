# LinkedIn + Claude Browser Daily Brief Example

This reference records a concrete implementation pattern for a LinkedIn community-manager workflow operated by Claude Code with browser integration. Adapt paths, fields, and headings rather than copying them blindly.

## Operational Shape

- Project root: `~/linkedin`
- Operator: one or more Claude Code root sessions with Chrome integration; sessions may close, restart, or change during the reporting day
- Human timezone: `America/Mexico_City`
- Active window: 08:00–23:00 local time
- Daily brief delivery: 23:15 local time, after the active window
- Delivery surface: originating WhatsApp conversation

Never pin the briefing pipeline to one Claude session ID. Discover every root transcript associated with the project and reporting date, then consolidate them as one operational day. Session boundaries are implementation details, not downtime or reportable events.

## Sources of Truth

- `metrics/session_log.md`: append-only, newest-first journal. Each `## YYYY-MM-DD ...` block records a tick or session, its actions, rationale, holds, metrics, and sync result.
- `metrics/STATE.md`: generated live-state snapshot containing profile totals, today's counts, pending invites, caps, and Sync Health warnings.
- `comments/published/*.md`: comment artifacts; today's records use `published_at`.
- `posts/published/*.md`: post artifacts; today's records use `published_at`.
- `invites/pending/*.md`: invitation artifacts; today's records use `sent_at`, not `published_at`.
- `~/.claude/projects/<project>/*.jsonl`: optional supplementary root-session transcripts discovered dynamically by project and local reporting date. Do not recurse into subagent transcript copies unless the root transcript lacks their result.

The journal is authoritative for what Claude did and why. STATE is authoritative for current numbers but may include cumulative values. Artifact metadata is a cross-check. Transcripts may supply reasoning, decisions, and omitted detail, but a requested, planned, or attempted action is not proof of completion. If a transcript conflicts with the persistent project records, the journal/state/artifacts hierarchy wins.

## Collector Logic

A read-only Python collector should:

1. Compute `TODAY` with `datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()`.
2. Find all level-2 headings matching `^## (YYYY-MM-DD)` in `session_log.md`.
3. Slice every block whose heading date equals `TODAY`; this works with a newest-first journal and multiple ticks.
4. Include the complete current `STATE.md` and preserve its generated timestamp.
5. Scan artifact frontmatter with per-type semantic timestamp fields:
   - comments/posts: `published_at`
   - invitations: `sent_at`
6. Discover all root `*.jsonl` transcripts for the project; parse each record's timestamp into `America/Mexico_City`, retain date-matching user/assistant text, and label sessions ordinally without emitting UUIDs.
7. Exclude slash-command expansion boilerplate and duplicated subagent transcripts. Bound each excerpt and the aggregate transcript section so the cron context stays predictable.
8. Print `No hay entradas persistentes para la fecha` only when the journal is empty; separately state whether transcript excerpts were found.

Do not use modification times to count activity: snapshot refreshes can update old JSONL and dashboard files without publishing anything. A session change is neither downtime nor evidence of lost context. Aggregate every discovered session, but require durable corroboration before reporting an outbound action as completed.

## Brief Semantics

The executive brief should consolidate repeated autonomous ticks. For example:

- Several snapshots become one net metrics paragraph.
- Multiple feed scans that found no qualified candidate become one quality-based hold.
- Invite suppression at the pending threshold becomes one explicit risk/cap decision.
- Repeated Rule-13 checks with nothing new become a single engagement-maintenance status.

Useful distinctions:

- **No outbound actions:** sessions ran, inspected the feed/notifications, and intentionally held.
- **No recorded sessions:** the journal has no entries; this may indicate downtime or simply no run and should not be described as a deliberate hold.
- **Current cumulative state:** totals such as all-time reach or total tracked comments.
- **Today's observed delta:** impression movement, new replies, invitations, comments, or followers explicitly timestamped/journaled today.

## Recommended WhatsApp Output

Use short headings and bullets, no tables:

- `📊 Brief LinkedIn — <fecha>`
- `Resumen ejecutivo`
- `Acciones realizadas`
- `Resultados y señales`
- `Decisiones y holds`
- `Estado operativo`
- `Siguiente foco`

Target roughly 250–500 Spanish words. Include names/topics when available, but do not reproduce every tick.

## Hermes Cron Notes

- Collector location: `~/.hermes/scripts/linkedin_daily_context.py`
- Cron `script` value: `linkedin_daily_context.py` (relative path only)
- Suggested schedule: `15 23 * * *` when host time matches Mexico City; always verify `next_run_at` offset.
- Set `workdir` to `~/linkedin`.
- Use an LLM-driven job (`no_agent=False`, the default) because the script supplies facts and the model performs consolidation.
- `attach_to_session=True` makes follow-up questions about the brief continuable.
- After creation, trigger `run` and verify `last_status`, `execution_success`, and `last_delivery_error`.

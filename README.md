# Hermes Automation Stack

Public, sanitized blueprint of a personal Hermes Agent deployment: deterministic collectors, scheduled executive briefs, Alexa delivery safeguards, career automation handoff, health/calendar/mail/finance context, and reusable operational skills.

## Included

- `scripts/` — collectors and watchdogs for Alexa briefs, Google Calendar, Google Health/Fitbit, LinkedIn, Proton Mail, finance freshness, career staging, job postings and auction changes.
- `scripts/tests/` — deterministic parser and safety tests.
- `skills/` — the reusable skills developed around daily briefings, autonomous watchdogs, staged career applications, consumer-wellness data and Alexa automation.
- `prompts/` — morning, evening and WhatsApp brief contracts.
- `cron/jobs.example.yaml` — sanitized schedules and routing templates; IDs are intentionally generated per installation.
- `config/hermes-config.example.yaml` and `.env.example` — safe starting points with placeholders only.

## Deliberately absent

- All live secrets, OAuth material, messaging identifiers, transcripts, memories, personal state and databases.
- All generated health, finance, email, calendar, career and browser data.
- The excluded private product-monitoring/buying subsystem and every direct dependency on it.
- Independent companion applications; scripts reference them through local project paths or environment variables.

## Setup

1. Install [Hermes Agent](https://github.com/NousResearch/hermes-agent).
2. Copy only the scripts and skills you need into your active `$HERMES_HOME`.
3. Create a local `.env` from `.env.example`; replace placeholders without committing it.
4. Install optional Python integrations in a virtual environment: `python -m pip install -r requirements.txt`.
5. Recreate schedules from `cron/jobs.example.yaml` using Hermes cron tooling, adjusting delivery and workdirs for your machine.
6. Keep `security.redact_secrets=true` and run your own secret scan before every public push.

## Validation

```bash
python -m compileall -q scripts
python -m unittest discover -s scripts/tests -p 'test_*.py'
```

Some collectors depend on companion projects or authenticated local services; their network/live checks are intentionally not run in CI.

## License

MIT for the material in this repository. External services and companion projects retain their own licenses and terms.

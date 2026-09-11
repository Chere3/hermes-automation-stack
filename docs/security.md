# Security boundary

This repository is a sanitized blueprint, not a backup of `~/.hermes`.

Never commit these live files or directories:

- `.env`, `auth.json`, OAuth client/token files, password-manager tokens
- `config.yaml` copied verbatim (it may contain channel IDs and local routing)
- `state.db`, cron execution databases, transcripts, memories, logs, caches
- messaging-platform sessions, pairing data or browser profiles
- generated state, health, finance, mail, calendar or career records

The checked-in `.gitignore` blocks common forms, but it is not a substitute for a secret scan. Keep runtime credentials in the local Hermes secret store or a password manager and reference them through environment variables.

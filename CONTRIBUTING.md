# Contributing

Thanks for helping make Hermes automations safer and easier to reuse.

## Good contributions

- read-only collectors for useful data sources;
- transition-only watchdogs that stay silent while healthy;
- deterministic fixtures for parser and failure-mode coverage;
- cross-platform path, packaging, and setup improvements;
- redaction, authorization-boundary, and state-integrity tests;
- clearer examples and documentation.

Open an issue before adding a new live write path, private/undocumented API, or dependency that requires credentials.

## Development

```bash
git clone https://github.com/Chere3/hermes-automation-stack.git
cd hermes-automation-stack
python -m pip install -r requirements-dev.txt
python -m compileall -q scripts skills
PYTHONPATH=scripts python -m unittest discover -s scripts/tests -p 'test_*.py' -v
PYTHONPATH=scripts python scripts/validate_docs.py
```

Optional dependencies can be installed in a virtual environment from `requirements.txt`.

## Pull-request checklist

- [ ] The change is scoped and documented.
- [ ] New behavior has deterministic tests.
- [ ] Fixtures contain no real personal data, identifiers, cookies, or tokens.
- [ ] Failure paths preserve the last valid state and fail closed.
- [ ] Side effects have an explicit authorization boundary and post-action verification.
- [ ] `python -m compileall -q scripts skills` passes.
- [ ] The unit suite passes.
- [ ] A secret scanner reports no findings in the proposed diff.

## Style

- Prefer Python standard-library solutions in collectors.
- Keep collector output bounded, structured, and date-scoped.
- Healthy/no-change watchdog runs should produce empty stdout.
- Never infer completion from a requested or attempted action.
- Use environment variables for deployment-specific values.
- Explain why a safety check exists; do not remove one merely to make a test pass.

## Commit and PR titles

Use a short imperative title, for example:

- `Add transition-only calendar auth watchdog`
- `Harden auction parser against partial pages`
- `Document exact-device delivery verification`

By contributing, you agree that your contribution is licensed under the repository's MIT License.

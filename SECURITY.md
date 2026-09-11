# Security policy

## Supported version

Security fixes target the current `main` branch.

## Reporting a vulnerability

Please do **not** open a public issue for leaked credentials, authentication bypasses, unsafe device writes, secret-redaction failures, or vulnerabilities that expose personal data.

Use GitHub's private vulnerability reporting for this repository:

1. Open the repository's **Security** tab.
2. Choose **Advisories** → **Report a vulnerability**.
3. Include the affected file/flow, impact, reproduction steps, and a suggested mitigation if available.

If private reporting is unavailable, open a public issue containing no exploit details or secrets and ask the maintainer for a private contact channel.

## Scope

Especially relevant reports include:

- committed or logged secrets and OAuth material;
- collectors leaking personal records into errors or alerts;
- exact-target checks that can widen into account-wide actions;
- duplicate side effects after timeout or retry;
- state corruption or invalid snapshots replacing valid baselines;
- command or prompt injection crossing an authorization boundary;
- unsafe handling of password-manager or messaging credentials.

Never include real tokens, cookies, personal records, or active exploit payloads in a report. Use synthetic fixtures.

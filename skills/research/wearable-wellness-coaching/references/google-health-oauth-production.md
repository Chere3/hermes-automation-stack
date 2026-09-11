# Google Health OAuth and production-readiness playbook

Use this reference when a Google Health/Fitbit connector stops refreshing, when moving an OAuth client from testing to production, or when deciding whether Google verification and CASA are required.

## First principles

- Distinguish **production infrastructure** from the Google OAuth consent screen's **Publishing status**. Running a private service on a production VPS does not by itself make the app publicly available.
- Preserve least privilege. Diagnose before changing scopes, audience, client type, or publishing status.
- Never print or persist client secrets, access tokens, refresh tokens, authorization codes, cookies, or full OAuth error bodies. Redact them as `[REDACTED]`.
- Treat connection troubleshooting as operational integrity, not as permission to inspect or summarize health values.
- Check current Google Health and Google Identity documentation before acting; scope classifications, onboarding, limits, CASA tiers, and fees can change.

## Safe diagnostic ladder

1. Identify the concrete API and endpoint. Do not conflate Google Health API, legacy Google Fit, Health Connect, and Fitbit Web API.
2. Check scheduler state and last run result without changing it.
3. Check credential-file existence, ownership, permissions, size, and modification time only. Do not read values into chat or logs.
4. Check the normalized database's latest day, latest update timestamp, and row count in read-only mode. Do not print health payloads unless the user explicitly requests them.
5. Run the normal synchronizer once with the smallest useful date range.
6. If it suppresses details, use a temporary redacted probe that reports only the stage, HTTP status, and safe OAuth error identifier:
   - secret store lookup;
   - OAuth refresh;
   - one read-only API method at a time.
7. Delete the temporary probe and close browser tabs/processes after diagnosis.

### Interpreting `invalid_grant`

`HTTP 400 invalid_grant` at the token endpoint means the refresh credential cannot be used. Common causes include revocation, client mismatch, session-control policy, or expiration. Do not automatically claim revocation.

A strong seven-day pattern is:

- token was issued while the OAuth consent screen was `External` + `Testing`;
- non-basic scopes were requested;
- it worked for roughly seven days, then refresh began returning `invalid_grant`.

Google documents that refresh tokens for an External app in Testing expire after seven days unless only basic identity scopes are requested. Correlate token creation time and last successful/first failed sync before concluding this is the cause.

An expired or revoked refresh token cannot be repaired. Obtain a new authorization code and refresh token after correcting the project state. Use `access_type=offline` and `prompt=consent` when a new refresh token is required, then store it atomically with restrictive permissions.

## Minimal Google Health scopes

Select scopes from the current API discovery document and the exact data types used. A read-only wellness summary commonly needs only:

- `https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly`
- `https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly`
- `https://www.googleapis.com/auth/googlehealth.sleep.readonly`

Do not request `cloud-platform`, write-only scopes, location, ECG, irregular-rhythm notification, or profile scopes unless a concrete implemented feature requires each one. Method discovery documents list all scopes a method can accept; they do **not** prove that every listed scope is required for every data type.

## Private production versus public launch

Current Google Health guidance distinguishes these paths:

### Private or limited-use client

For a personal/private integration below Google's user cap:

- Audience can remain `External`.
- Use the client type recommended by the Google Health setup guide (currently Web Server/Web application for its server flow).
- Move Publishing status from `Testing` to `In production` to avoid seven-day testing refresh tokens.
- Reauthorize the permitted user once and verify refresh plus API reads.
- An unverified client may retain a user cap and show an unverified-app warning. Confirm the current console behavior and policy rather than promising that review is never required.

This is often the proportionate route for a single-user private automation. It is not a way to evade verification for an app actually offered to the public.

### Public app or more than the allowed users

Google Health says most of its scopes are restricted. Public launch or support beyond the unverified user limit requires the Google process current at submission time, typically:

1. OAuth brand/app verification by Trust & Safety.
2. A verified domain, application home page, privacy policy, and terms of service.
3. Exact per-scope justifications tied to visible product features.
4. An in-app disclosure shown in normal use—not only in a privacy policy—that identifies the health/fitness data accessed and explains use/sharing.
5. A working deletion process for user data.
6. A demonstration of the consent flow and each requested scope.
7. A third-party CASA security assessment when directed, with periodic/annual reassessment for restricted scopes.

Do not start CASA before Google's Trust & Safety team instructs the developer. Timing and assessor fees vary; check the current official page.

## Truthful use-case dossier

Before entering the Cloud Console verification form, prepare concise, consistent answers:

- **Application category:** personal wellness/consumer health analytics, not diagnosis or clinical decision support.
- **Architecture:** server-side read-only connector; state where processing and storage occur without overstating encryption or certifications.
- **Users:** current and planned user counts; distinguish one private owner from a publicly offered product.
- **Data flow:** source → OAuth consent → API → normalized daily aggregates → user-facing brief.
- **Retention:** state the actual retention period and whether raw events are discarded. If no formal policy exists, create one before applying.
- **Sharing:** explicitly state whether data is shared, sold, used for advertising, or used to train models. Never make claims not supported by the implementation.
- **Deletion:** explain how the user revokes access and deletes stored aggregates.
- **Scope justification:** one distinct explanation per scope; avoid duplicated boilerplate.

A suitable disclosure pattern is:

> `{App name}` accesses activity, health measurement, and sleep data to generate private daily summaries and personal wellness trends. It does not diagnose conditions or make clinical decisions.

Adapt this to the actual product. Do not call a chatbot, WhatsApp brief, or backend pipeline an “in-app disclosure” unless users genuinely encounter the disclosure during normal authorization/use.

## Verification after any change

1. Confirm the consent screen audience, publishing status, and exact configured scopes.
2. Generate a fresh refresh token without exposing it.
3. Exchange it for an access token successfully.
4. Call each required read-only data category independently.
5. Run one minimal synchronization and confirm the normalized database timestamp advances.
6. Run the project's tests.
7. Confirm no write, location, ECG, profile, or broad cloud scopes were introduced.
8. Confirm logs contain only safe error classes/statuses, not credential values or health payloads.
9. Keep the old token invalidated or securely removed; do not retain credential copies in temporary files.

## Authoritative pages to re-check

- Google Health API setup: `https://developers.google.com/health/setup`
- Google Health app verification: `https://developers.google.com/health/app-verification`
- Google Health developer checklist: `https://developers.google.com/health/developer-checklist`
- Google Health scopes: `https://developers.google.com/health/scopes`
- Google Identity token expiration: `https://developers.google.com/identity/protocols/oauth2#expiration`
- Restricted scope verification: `https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification`

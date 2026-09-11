# Cloud health-data OAuth integrations

Use this reference when connecting a personal health-data provider through a cloud API, especially Google Health API / Fitbit.

## Current Google/Fitbit direction

- Google Health API is the next generation of Fitbit Web API and uses Google OAuth 2.0.
- Fitbit's legacy Web API is scheduled for deprecation in September 2026. Prefer Google Health API for new integrations.
- Google Health API can unify metrics from Fitbit, Pixel Watch, and supported third-party sources.
- Access requires a Google Cloud project, the Google Health API enabled, and an OAuth 2.0 web client.

## Safe onboarding sequence

1. Establish the exact KPI categories before requesting scopes.
2. Give the user one browser checkpoint at a time. On messaging platforms, put every actionable instruction in the final user-facing response—not only in progress/commentary surrounding tool calls—then wait for the exact screen they see. Repeat the complete immediate action in final if tools were used first.
3. The user signs in and handles consent/MFA personally. Never request Google passwords, authorization codes, client secrets, refresh tokens, or health records through chat.
4. Create or select a Cloud project; configure an OAuth web client and an authorized redirect URI supported by the implementation. Google's Health setup wizard currently demonstrates `https://www.google.com` for its initial authorization-code walkthrough.
5. Add the user's account as a test user only while the consent screen is in Testing. If the app is already In Production, do not send the user searching for a Test users control that is absent.
6. Add only approved Google Health scopes on the Data Access page.
7. Transfer downloaded OAuth credentials directly from the user's PC to the target host over a protected channel such as SCP, or place individual fields in a dedicated least-privilege password-manager item. Store local material with mode `0600` outside the repository.
8. Request offline access and use `prompt=consent` only when obtaining a refresh token or changing scopes. Generate a cryptographically random OAuth `state`, persist it with mode `0600`, and validate it before exchanging the code.
9. Do not ask the user to paste a callback URL or authorization code into chat. Prefer a registered one-time callback listener bound to loopback and reached through a verified private HTTPS route; validate `state`, suppress request logging, and clean browser history immediately. If no callback listener is possible and a temporary password-manager field is unavoidable, treat the entire callback URL as secret-bearing input: consume it in-process without printing generic item JSON or field values, exchange immediately, and remove the field after success.
10. Exchange and store tokens without printing them, then verify with the smallest read-only query.
11. Revoke and remove pending material if onboarding is abandoned.

### Redirect URI exactness

- Google compares redirect URIs exactly. Register the URI under **Authorized redirect URIs**, not Authorized JavaScript origins, and use the same string in both authorization and token-exchange requests.
- A root redirect registered as `https://www.google.com` may return in the browser as `https://www.google.com/?code=...`. A callback validator may normalize only an empty root path and `/` as equivalent after confirming HTTPS and the exact host; do not broadly relax path matching.
- Always send the originally registered redirect string—not the browser-canonicalized callback URL—to the token endpoint.
- On `redirect_uri_mismatch`, inspect scheme, host, path, client type, selected Cloud project, and which redirect-URI section contains the value. Do not regenerate credentials blindly.

## Read-only scope catalogue

All scopes start with `https://www.googleapis.com/auth/googlehealth`.

- `.activity_and_fitness.readonly`
- `.health_metrics_and_measurements.readonly`
- `.sleep.readonly`
- `.profile.readonly`
- `.nutrition.readonly`
- `.location.readonly`
- `.ecg.readonly`
- `.irn.readonly`
- `.settings.readonly`

Default to activity, health metrics, sleep, and profile. Nutrition, precise GPS routes, ECG, and irregular-rhythm notifications are more sensitive and require explicit user approval. Do not request any `writeonly` scope for KPI reporting.

## Token-lifetime pitfall

- OAuth apps in Testing receive refresh tokens that expire after seven days.
- In Production, refresh tokens generally remain valid until revoked or left unused for a prolonged period (typically around six months).
- Do not claim durable automation while the app remains in Testing. Plan publishing status, revocation, health checks, and reauthorization alerts.
- Unverified apps are limited to 100 users; supporting more requires additional review. A private single-user integration should remain narrowly scoped.

## Google Health API v4 read patterns

Base URL: `https://health.googleapis.com/v4`.

- Verify linkage first with `GET /users/me/identity`. Store both `healthUserId` and `legacyUserId` without logging their values.
- Detailed records use `/users/me/dataTypes/{kebab-case-type}/dataPoints`; filter-field names use snake case inside filter expressions.
- Do not sum raw records from multiple providers for user-facing totals. Use `GET .../dataPoints:reconcile` with `dataSourceFamily=users/me/dataSourceFamilies/all-sources` (or a narrower explicitly chosen family) to prevent duplicate Fitbit/Google/third-party data.
- For daily metrics that support it, prefer `POST .../dataPoints:dailyRollUp`. Supply a civil-day range and `windowSizeDays: 1`; this handles travel, UTC-offset changes, and daylight-saving transitions better than client-side duration arithmetic.
- Steps rollups return `rollupDataPoints[].steps.countSum`. Other rollup payloads use type-specific fields and units, so normalize through an explicit per-type map rather than guessing field names.
- Common daily-specific types such as `daily-heart-rate-variability`, `daily-oxygen-saturation`, `daily-respiratory-rate`, `daily-resting-heart-rate`, `daily-sleep-temperature-derivations`, and `daily-vo2-max` use list/reconcile rather than `dailyRollUp`.
- Preserve `null`/missing separately from numeric zero. An empty result can mean no wearable support, no sync, no measurement, or no data for that date; it does not prove a true zero.
- Persist daily summaries rather than raw event streams by default. Keep raw responses only ephemerally with restrictive permissions when needed to validate schemas.

## Data minimization

- Prefer daily aggregates and trends over retaining raw event streams.
- Keep source timestamps and provenance so “zero,” “missing,” and “not synchronized yet” remain distinguishable.
- Treat GPS, ECG, irregular-rhythm data, sleep stages, and body measurements as highly sensitive.
- Encrypt data in transit, restrict local files to the consuming identity, redact logs, and provide a deletion/revocation path.
- Start read-only and validate that no endpoint or token carries write scopes.

## Verification

- Confirm granted scopes from token metadata without printing tokens.
- Query one bounded date range and verify account/timezone interpretation.
- Check data presence separately from numeric zero.
- Confirm refresh succeeds before scheduling unattended collection.
- Exercise revocation and ensure the collector fails closed with an actionable alert.

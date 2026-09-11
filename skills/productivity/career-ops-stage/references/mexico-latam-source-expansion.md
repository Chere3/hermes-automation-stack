# Mexico/LATAM job-source expansion

Use this procedure when career-ops produces a pipeline dominated by Remote-US or one employer despite Mexico-only eligibility.

## Diagnose the funnel

1. Distinguish monitored listings, title/location-filtered listings, pending pipeline entries, staged applications, and confirmed submissions. Do not infer source coverage from staged records alone.
2. Inspect the active `portals.yml`, last scan output, pipeline, and timer. Verify whether `search_queries` are executed automatically or merely emitted as agent handoffs.
3. Measure the baseline before editing: companies/boards scanned, total jobs, title rejects, location rejects, duplicates, and new offers.

## Source priority for the user

The goal is **connected coverage**, not a list of sources left for manual review. Before downgrading an important source to a search handoff, exhaust the legitimate read-only channels in this order:

1. Public first-party or job-board APIs/RSS feeds that expose Mexico/LATAM eligibility.
2. Public employer ATS boards with verified live slugs and Mexico operations.
3. Public app data channels used by the board itself, including guest endpoints and cookie/CSRF-backed read APIs whose session is obtained anonymously from the public bootstrap page.
4. Public server-rendered listing HTML with canonical job URLs and stable pagination.
5. A real browser with bounded pagination, throttling, persistent authorized sessions where appropriate, and automatic cleanup.
6. Official saved-search email alerts ingested read-only.
7. Indexed-search discovery followed by verification against the original posting.

Useful high-signal categories:

- Mexico-focused technology board: Hireline.
- LATAM technology/startup boards: Get on Board and KASZEK portfolio jobs.
- Public LinkedIn guest listing cards for small Mexico/Guadalajara query families; canonicalize to the stable job ID and do not fetch profiles.
- Official ATS feeds for Mexico/LatAm employers such as Kueski, Kavak, Wizeline, Bitso, and Clara, but verify each live endpoint before configuration. Treat ATS slugs as case-sensitive until proven otherwise.
- OCC, Computrabajo, Indeed México, and Portal del Empleo through browser/session, official alerts, or indexed discovery when their public HTTP path enforces access controls.

Do not equate an HTTP `403` with “manual forever.” Test the source’s public browser flow, guest endpoint, official alerts, and first-party ATS links. However, never solve or bypass CAPTCHA/MFA, forge authorization, use proxies to evade an access decision, or automate authenticated access without the user’s authorized session. Record blocked sources as connected-degraded/watchdog rather than claiming complete coverage.

## Query and title vocabulary

Cover English and Mexican Spanish terms, including:

- AI/ML Engineer; Applied AI; AI Automation; Agentic AI
- Ingeniero/Desarrollador de IA; Ingeniero de Machine Learning; Científico de Datos
- Arquitecto/Ingeniero de Soluciones; Ingeniero de Preventa
- Power Platform/Power Apps/Power Automate
- Backend, Python, Cloud, automatización, hiperautomatización

Avoid broad keywords such as bare `Agent`; they admit customer-service/backoffice roles. Prefer `AI Agent` and `Agentic`. Add precise negatives for recurring irrelevant categories rather than weakening location policy.

## Location safety

- Allow Mexico/México, Guadalajara, Zapopan, Jalisco, Tlaquepaque, Tlajomulco, LATAM/Latin America, and genuinely global/Anywhere roles.
- Reject explicit foreign-country remote locations unless Mexico or LATAM is also explicitly eligible.
- Treat a bare `Remote` from an aggregator as eligibility unconfirmed; verify the individual posting before staging or submitting.
- If an aggregator supplies no location and does not explicitly mark the role remote, emit a sentinel such as `Eligibility unconfirmed` and block it from the pipeline. Do not let the scanner’s normal “missing location passes” behavior silently authorize it.
- A narrowly recognized place in the title may recover location (`São Paulo/SP`, CDMX, Guadalajara), but do not infer geography from company headquarters or language.
- Do not treat `Remote-US` as global remote.

## Building a public listing/data provider

Use TDD and a deterministic fixture first. Require:

- HTTPS and an exact hostname allowlist for every request.
- Canonical job URLs or stable job IDs with tracking parameters removed.
- Bounded pagination, response size, timeouts, and query-family count.
- Deduplication across pages and overlapping queries.
- Extraction only from public listing cards or the public app’s own read endpoint; no per-job side effects.
- Fail-closed behavior when expected structure disappears or geography is missing.
- No challenge solving, credential capture, profile access, or application actions.

For public apps that bootstrap an anonymous session:

1. Fetch the public listing page and obtain its ephemeral CSRF token and `Set-Cookie` values.
2. Preserve **each** `Set-Cookie` header separately. A generic fetch implementation may collapse multiple cookies into one ambiguous string; expose a `getSetCookie()`-style array from the shared transport and test it with multiple cookies.
3. Send only cookie name/value pairs to the fixed same-origin read endpoint. Keep them in memory for one run; never log or persist them.
4. Follow opaque pagination cursors with a page cap and reject repeated cursors.
5. If the same request without its anonymously issued session returns `INVALID_CSRF`, treat that as a transport-fidelity bug to reproduce—not proof that the public source cannot be connected.

For public guest search endpoints such as LinkedIn listings:

- Use small title/location families and a freshness window rather than one huge query.
- Keep request frequency low and bounded.
- Canonicalize every result to its stable posting ID and avoid profile/company-page fetches.
- Treat the visual login wall and the public guest listing feed as separate surfaces; test both before deciding the source requires authentication.

Then test one live page/query, inspect normalized title/company/location/date fields, and run the provider-specific test suite.

## Verification

1. Validate configuration (`validate-portals.mjs`).
2. Run provider fixture tests.
3. Run one production scan and record the before/after funnel.
4. Remove obvious false positives from both pipeline and scan history only when changing the filter so they will be deterministically rejected on the next run.
5. Run a second scan: it must add zero duplicates.
6. Confirm explicit foreign-country remote roles do not reappear while Mexico/LATAM roles remain.
7. Run `git diff --check` and report any unrelated pre-existing portal failures separately.

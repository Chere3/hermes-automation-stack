# Researching official APIs for connected consumer devices

Use this checklist when asked whether a manufacturer offers a public or partner API for device telemetry or health-adjacent data.

## Evidence ladder

1. Inspect first-party product/app pages for the data the product actually records.
2. Search first-party developer surfaces for API references, SDKs, OAuth authorization, scopes, OpenAPI files, webhooks, partner onboarding, terms, and contact routes.
3. Inspect official site maps and robots-declared sitemap indexes. Search URL inventories for `api`, `developer`, `sdk`, `oauth`, `partner`, `integration`, and product/app terms. Treat this as coverage evidence, not absolute proof of nonexistence.
4. Inspect the official App Store/Google Play listing and its data-safety/privacy links. Record app version/update date, supported device families, collected data categories, deletion rights, and support coordinates.
5. Inspect the manufacturer's current privacy policy and regional data-request/preference center. Distinguish access, deletion, correction, and portability rights from programmatic API access.
6. Inspect first-party support pages and localized contact channels. If no public partner intake exists, identify support as the channel for written confirmation rather than implying that support itself grants API access.
7. Use community libraries only as contrast evidence. Label BLE clients, Home Assistant integrations, reverse-engineered cloud endpoints, and GitHub SDKs as unofficial unless the manufacturer explicitly endorses them.

## Classification

Report one of these states:

- **Public API verified:** current first-party docs, authentication method, scopes, endpoint base URL, and onboarding are accessible.
- **Partner API verified:** first-party material confirms availability and gives a real application/contact path; state access restrictions and whether docs require login/NDA.
- **Private integration suggested, not verifiable:** first-party wording implies commercial integrations but no publicly verifiable onboarding or technical scope exists.
- **No public offering found:** a bounded search of official developer, product, app-store, privacy, sitemap, and support surfaces found no API documentation or partner program. Never shorten this to “the API does not exist.”

## Scope table

Keep three concepts separate:

| Concept | What it proves | What it does not prove |
|---|---|---|
| App displays a metric | The product/app records or derives it for users | Third parties can retrieve it |
| Privacy/data export right | A user may request access/copy/deletion under applicable law | Continuous access, stable schema, JSON/CSV, or per-session granularity |
| API documentation and scopes | Programmatic access is offered to the documented audience | Every metric visible in the app is exposed |

For each requested metric, report: recorded in app, export explicitly promised, API field/scope documented, supported models/regions, and any model-specific limitation. Use **“not documented”** instead of inferring availability.

## Dates and provenance

- Record the research date and each policy/app update or effective date shown by the source.
- Prefer deep, directly verifiable URLs over search-result links.
- Separate first-party manufacturer evidence from platform-hosted declarations (for example, Google Play data safety) and from community evidence.
- Do not use guessed developer subdomains as positive or negative evidence; DNS redirects and wildcard corporate infrastructure are ambiguous.

## Deliverable pattern

1. One-sentence conclusion with calibrated confidence.
2. Table of official URLs, observed date/status, and what each source establishes.
3. Metric/scope matrix.
4. Data export/privacy routes.
5. Support/partner inquiry route.
6. Explicit limitations: bounded search, gated/NDA programs may exist, and no claims based on unofficial code.

# Official career-feed discovery patterns

Use these patterns when a configured careers URL or ATS slug has gone stale.

## Establish provenance before trusting a feed

Build a first-party chain rather than accepting a search result as proof:

1. Open the company’s current official careers/about page.
2. Follow or extract the careers-board link, embed script, application-form configuration, or first-party runtime config.
3. Derive the ATS tenant/slug from that official evidence.
4. Probe the public jobs endpoint and record HTTP status plus a real job count.
5. Inspect returned locations before describing regional coverage.

A working ATS slug discovered only by guessing is a candidate, not verified official coverage, until the company’s own site or runtime configuration ties the company to it.

## Useful public endpoint patterns

### Greenhouse

A current official page may expose a new slug in an embed such as `...?for={slug}`. Probe:

`https://boards-api.greenhouse.io/v1/boards/{slug}/jobs`

Localized custom careers sites may publish a first-party config route mapping locales to several Greenhouse boards. Prefer the primary/default-language board and check whether localized boards duplicate its jobs before combining them.

### Ashby

Custom careers pages can hide Ashby behind local application URLs. Look for:

- `ashby_jid={uuid}` parameters;
- `ashbyBaseJobBoardUrl` in embedded application-form configuration;
- Ashby embed scripts on individual job pages.

Then probe:

`https://api.ashbyhq.com/posting-api/job-board/{slug}`

Slug capitalization may change while routing remains case-insensitive. Record the spelling used by first-party evidence.

### Teamtailor

A custom Teamtailor domain commonly exposes:

`https://{custom-careers-host}/jobs.rss`

The RSS may include namespaced fields such as `remoteStatus`, `locations`, and `department`; inspect those fields rather than relying only on title and description.

### First-party/Factorial ATS pages

Some official ATS portals render complete jobs server-side but expose no separate public JSON API. Count unique canonical `/job_posting/` links from the live board and parse job detail JSON-LD for location. A sitemap is useful for discovery and recovery, but it may lag the rendered board; report the board count and note material sitemap drift.

### WordPress career sites

A WordPress jobs archive may expose `/forto-jobs/feed/` or another custom-post-type RSS path. The feed can be limited to the default page size even when the archive has more jobs. If individual pages reveal an underlying ATS embed, prefer that ATS public API for complete retrieval; otherwise paginate and bound the RSS/archive explicitly.

## Regional relevance

Do not infer Mexico/LATAM eligibility from:

- an unqualified `Remote` location;
- company offices or headquarters;
- Portuguese- or Spanish-language role titles;
- a locale-specific board.

Use explicit job locations, applicant-location requirements, or job-detail JSON-LD. Report ambiguous `Remote` as eligibility unconfirmed. When an SSR board groups jobs under location headings, preserve the group-to-job association and verify regional candidates on their detail pages.

## Reporting a stale-portal audit

For each company, report:

- official careers page;
- provider and exact tenant/slug;
- recommended machine-readable endpoint, or official SSR board when no feed exists;
- observed HTTP status and live count with timestamp;
- explicit Mexico/LATAM relevance;
- keep, watchdog, or disable recommendation.

Do not recommend disabling an empty source merely because it has zero jobs if it is still an official, stable portal. Classify it as an empty-source watchdog. Recommend disabling only when no stable legitimate unattended source remains.

# Job Catalog and ATS Integration Patterns

## Session-bootstrap APIs

Some public catalogs require an anonymous bootstrap page before their search API works:

1. GET the official board page with redirects constrained.
2. Extract the board identifier and public CSRF token from first-party state.
3. Preserve every `Set-Cookie` header separately. A comma-joined header is lossy because cookie attributes may themselves contain commas.
4. Send only cookie name/value pairs to the fixed same-host API endpoint.
5. Follow opaque pagination cursors exactly; detect repeated cursors and enforce a hard page cap.
6. Keep cookies and CSRF material memory-only.

A successful browser request is useful diagnostic evidence, but reproduce it with the application's native HTTP transport before declaring the connector complete. Differences in repeated response headers are a common cause of “browser works, code fails.”

## Public guest search endpoints

When a site exposes a first-party guest listing endpoint underneath a login-walled UI:

- Use only the public listing endpoint, not authenticated profiles or application forms.
- Keep query combinations and pagination small.
- Normalize stable listing IDs and strip tracking parameters.
- Use several narrowly configured title/location combinations, then rely on global title, geography, and deduplication filters.
- Treat endpoint availability as version-sensitive and retain a watchdog/fallback plan.

## ATS migrations

A board that returns 404 for several runs may have migrated rather than closed.

1. Fetch the company's official careers page.
2. Search its actual links and embedded data for current ATS hosts.
3. Extract the exact tenant/slug from the official page.
4. Probe the corresponding public API/RSS endpoint and record a real count.
5. Change configuration only after the new feed returns valid records.
6. Re-run the normal scanner and confirm the target disappears from the unhealthy list.

Common migrations include Greenhouse → Ashby, Greenhouse → Teamtailor RSS, Lever → custom SSR, and a changed slug within the same ATS.

## Location fidelity

### Unknown location

Do not treat missing location as eligible. Use a sentinel such as `Eligibility unconfirmed` and include it in the location block list. Narrow title-based inference is acceptable for explicit strings such as `São Paulo/SP`, `Mexico City`, `Guadalajara`, or `Zapopan`; do not infer from company headquarters.

### Remote plus explicit geography

Separate work-model authorization from geographic authorization:

- `Remote` alone may pass if policy permits globally ambiguous remote roles.
- `Remote - Mexico`, `LATAM`, and `Anywhere in the World` pass through explicit permitted geography.
- `Remote - California`, `Remote - Denmark`, `Remote - South Korea`, and multi-location foreign strings fail unless a permitted geography is also genuinely listed.

A raw substring rule where `allow: [Remote]` wins is unsafe.

### Secondary enrichment failure

If a provider reports only `Remote`, `Hybrid`, or `In-Office` and a secondary endpoint supplies actual offices, a failed secondary request must not preserve the broad work-model string. Mark the location unconfirmed. Otherwise an upstream timeout can turn a US-only role into an apparently global remote role and cause it to resurface after deduplication.

## Production verification

After focused tests:

1. Validate configuration.
2. Run formatting/diff checks.
3. Run a real scan.
4. Re-evaluate every pending record with the current location policy.
5. Remove historical false positives by exact canonical URL from both pending output and scan history.
6. Run a second consecutive scan.
7. Inspect any additions from run two. Distinct stable IDs may indicate real rotating/paginated upstream results; identical roles or degraded locations indicate a dedup/enrichment bug.
8. Run the full suite with the project's required runtime and test-only environment overrides, rather than interpreting unrelated environment failures as regressions.

## Scaling

Adding several large Workday or aggregator feeds can create aborts in previously stable sources. Prefer reducing global concurrency and retaining provider-level pacing/retries before raising timeouts. Validate complete pagination caps for large tenants and heed truncation warnings.

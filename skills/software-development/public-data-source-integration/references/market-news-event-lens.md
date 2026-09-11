# Public market-price and news event-lens pattern

Use this pattern for dashboards that place company or product events on a traded security's candle chart. It is an **event-study aid**, not a causal attribution engine.

## Source architecture

- Put every upstream behind a small parser seam and inject the byte-fetcher in tests.
- Prefer a documented market-data API. If using an unofficial public chart endpoint, label it honestly, bound response size/time, restrict HTTPS hosts, validate the final redirect host, and expose source health.
- Treat news aggregators as discovery sources, not authoritative event registries. Preserve headline, publisher, publication timestamp, brand/query provenance, and the aggregator URL.
- Query each subsidiary or brand separately, then deduplicate by `(brand, publication timestamp, normalized title)` or a stronger canonical identifier.
- A failed brand query should mark the news source `degraded` while preserving valid market data and other successful brands.

## Event-to-session alignment

1. Convert a timestamp to the exchange timezone.
2. If it falls on a trading day before market close, align it to that session.
3. If it is after close, on a weekend, or on a holiday, align it to the next available candle/session.
4. If no next candle exists in the selected range, mark it `outside_market_range`; never force it onto the last candle.
5. Keep date-only events explicitly less precise than timestamped events.

Useful descriptive metrics:

- close-to-close session return;
- opening gap versus previous close;
- open-to-close intraday return;
- prior-window volume z-score;
- forward cumulative returns after 1, 3, and 5 sessions;
- optionally benchmark-adjusted return against a broad index.

Always state that temporal proximity and abnormal movement do not prove causation or constitute investment advice.

## Chart and list density

Raw news volume can make an otherwise correct chart unusable.

- Aggregate chart markers to one marker per trading session; show a count instead of every headline label.
- Keep brand filters available so users can isolate subsidiaries.
- Render the event list progressively (for example 30 at a time) while retaining the full count and the ability to load more.
- Lazy-load a heavy chart library so the dashboard shell and source-health information render first.
- Preserve direct source links in the detail list; aggregation belongs on the chart, not in the evidence record.

## Verification recipe

- Fixture tests: malformed market rows, source error payload, unsafe URL, missing timestamp, weekend event, after-close event, out-of-range event, and one failed brand feed.
- Live low-volume probe: verify HTTP status, candle count, event count, represented brands, and each source state.
- UI test: loading, recoverable API error, ticker/price rendering, and at least one event.
- Chart regression: multiple headlines on one date must produce exactly one session marker.
- Production build: run typecheck and inspect chunk sizes; use dynamic import when a chart library dominates the initial bundle.
- Visual QA: verify the loaded live state, chart legibility, responsive columns, console errors, and progressive list control. Inspect a single browser tab serially rather than racing multiple browser tools against shared state.

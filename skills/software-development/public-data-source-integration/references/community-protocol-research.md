# Community protocol and implementation research

Use this reference for surveys of unofficial SDKs, device integrations, reverse-engineered APIs, and history-export projects.

## Evidence hierarchy

Prefer claims supported by, in order:

1. executable source and tests;
2. captured protocol documentation with identified hardware/firmware;
3. framework manifests and pinned dependencies;
4. package-registry metadata and release records;
5. README statements and repository descriptions;
6. search-result snippets.

Label protocol findings as **captured**, **reconstructed**, or **inferred** when the project provides that distinction. Do not collapse an implementation's model map into a claim of hardware validation.

## Discovery matrix

Search independently across:

- GitHub repository search with product, transport, framework, API, cloud, history, export, and protocol terms;
- PyPI, npm, or the language-specific package registry;
- upstream frameworks such as Home Assistant, ESPHome, openHAB, or device libraries;
- source files for UUIDs, characteristic maps, model IDs, packet offsets, queries, and fixtures;
- releases/tags plus the latest substantive commit;
- license files, not merely the repository API's guessed license.

A package may be actively maintained while an older similarly named integration is stale. Trace dependency relationships and forks before treating them as independent implementations.

## Data-plane classification

Keep these layers separate in both notes and final tables:

### Passive/live broadcast

No connection or account. Usually provides status, coarse measurements, identifiers, and rapidly changing fields. It cannot be assumed to contain battery, exact pressure, retained records, or historical sessions.

### Active local protocol

GATT, serial, LAN, or another connected request-response path. Record connection-slot limits, pairing/authentication requirements, polling/notification rates, and whether active access interferes with the official app or another hub.

### Retained device data

A latest-session summary or small device-side cache is not a history export. Document retention depth, when data becomes readable, and whether timestamps depend on a drifting device clock.

### App/cloud history

Document authentication, discovery/config endpoints, API technology, fields actually queried, pagination, nullability, and whether the tool exports data or merely syncs an aggregate into another service. Private APIs are brittle and should be labeled unofficial.

## Metric semantics

For every metric, state whether it is:

- directly transmitted;
- decoded from flags or packed fields;
- locally extrapolated;
- aggregated after a session;
- classified by proprietary app logic;
- derived later from persisted sessions.

Watch especially for semantic traps:

- a sequential timer/pacer sector is not necessarily physical position;
- raw inertial samples are not classified zones;
- a motor target word is not RPM or frequency until units are demonstrated;
- a device-family/protocol ID is not always a retail model number;
- a daily frequency metric may be derived by counting sessions rather than transmitted directly.

## Maintenance and licensing

Report:

- latest package version and publication date;
- latest release/tag;
- latest substantive source activity;
- archived status;
- license SPDX identifier and presence of a license file;
- maturity indicators such as tests, downstream adoption, stars/forks only as weak context.

Do not call a project maintained solely because repository metadata was touched recently. Conversely, distinguish a stable published dependency used by a major framework from an abandoned standalone predecessor.

## Recommended result structure

1. Executive distinction between live/local, retained-device, and cloud/app history.
2. Comparison table: project, models/evidence, transport, metrics, maintenance, license, canonical URL.
3. Protocol section: services, characteristics/endpoints, packet layouts, access mode.
4. Metric-availability matrix with semantic caveats.
5. History/export section explaining retention depth and output format.
6. Practical recommendations by use case.
7. Explicit gaps: unsupported models, proprietary classifiers, unverified units, absent exporters.

Use canonical repository, package, framework documentation, and release URLs. Keep temporary research checkouts outside the user's working tree when possible and remove them after inspection without requiring deletion outside the created scope.

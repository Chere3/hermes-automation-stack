# Native passive-BLE diagnostic collector

Use this reference when an APK must continuously collect manufacturer advertisements without taking a peripheral's GATT connection slot.

## TDD vertical slices

1. Bootstrap and build an empty signed APK before BLE code. This separates toolchain/manifest failures from feature failures.
2. RED→GREEN the advertisement parser with sanitized byte fixtures. Include valid idle/running samples plus wrong manufacturer, truncation, unknown protocol/model, and invalid field values.
3. RED→GREEN a pure JVM session state machine before Android service integration. Cover duplicates, reordering, idle timeout, sample gaps, and a running packet arriving after the prior timeout.
4. Compile Room schema, then integrate scanner/service/UI. Finish with the full unit suite, lint, clean build, and artifact inspection.

A timeout-closing API may need to both return the completed prior session **and process the current running advertisement** to open its replacement. Returning early drops the first packet of the new session.

## Passive BLE boundaries

- Use `BluetoothLeScanner` with a manufacturer-data filter; do not call `connectGatt`, discover services, read characteristics, or write characteristics.
- For Oral-B, the Bluetooth SIG manufacturer ID is P&G `0x00DC`. The maintained MIT protocol reference is `Bluetooth-Devices/oralb-ble`; its wire-format notes document 9/11-byte layouts and iO fixtures.
- For a diagnostic collector scoped to a known model/protocol, fail closed on unsupported protocol, model, length, state, or mode instead of guessing.
- Name the advertisement's sector/pacer field `pacerSector` (or equivalent) and explicitly document that it is a pacing interval/indicator, not an anatomical mouth zone.
- Serialize scanner callback processing before mutating a session state machine; callbacks persisted on a multi-threaded dispatcher can race.

## Persistence and identity

- Persist immutable raw evidence separately from normalized sessions.
- Store a payload hash and parsed protocol fields. Avoid storing the real MAC by default.
- Derive a stable pseudonym with an HMAC key generated in Android Keystore. Do not use an unhashed MAC or a plain unkeyed hash as the device identifier.
- Deduplicate normalized sampling by monotonic brush elapsed time, while preserving raw observations for diagnostics.

## Foreground-service lifecycle

- Declare `FOREGROUND_SERVICE` and the specific `FOREGROUND_SERVICE_CONNECTED_DEVICE` permission, and set `android:foregroundServiceType="connectedDevice"` on the service.
- Start foreground immediately with an ongoing, low-importance notification. Require notification permission when the product requirement says the notification must remain visibly present.
- Do not auto-enable collection after install. Persist only an explicit user opt-in.
- A `BOOT_COMPLETED` receiver may restore collection only when opt-in and required runtime permissions still exist.
- Gate foreground startup on Bluetooth runtime permissions; connected-device foreground startup can fail if its prerequisite permission was revoked.
- Handle Bluetooth state changes, `START_STICKY` process restart, permission revocation, and service teardown. Guard receiver teardown if creation exited before registration.
- Lint may not infer helper-based permission checks around scanner APIs. Suppress `MissingPermission` only on the narrow method after explicit runtime checks and exception handling are present.

## Artifact verification

Run a clean verification pass:

```bash
./gradlew clean testDebugUnitTest lintDebug assembleDebug --no-daemon
apksigner verify --verbose --print-certs app-debug.apk
aapt dump badging app-debug.apk
aapt dump permissions app-debug.apk
aapt dump xmltree app-debug.apk AndroidManifest.xml
sha256sum app-debug.apk
stat --printf='size_bytes=%s\n' app-debug.apk
adb devices -l
```

Confirm package/version/min-target SDK, BLE feature optionality, exact permissions, service type, receiver export state, signing identity, digest, and size. If no device is attached, distinguish build/artifact verification from physical BLE and Android lifecycle validation.

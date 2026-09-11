# Alexa Private API Patterns

Sanitized implementation notes for Alexa web/mobile private APIs. These interfaces are undocumented and can change; inspect live responses before relying on a stored schema.

## Authentication Headers

Typical requests use locally stored `ubid-main` and `at-main` cookie values plus a CSRF cookie/header:

```text
Cookie: csrf=1; ubid-main=<local secret>; at-main=<local secret>
Csrf: 1
Accept: application/json
Content-Type: application/json
User-Agent: PitanguiBridge/...-[PLATFORM=Android]
```

Nexus GraphQL commonly also expects:

```text
X-Amzn-Marketplace-Id: ATVPDKIKX0DER
X-Amzn-Client: AlexaApp
X-Amzn-Os-Name: android
```

Never print the completed Cookie header.

## Echo Discovery

```http
GET https://alexa.amazon.com/api/devices-v2/device?cached=false
```

Useful response fields include account/friendly name, `deviceFamily`, online status, device type, serial number, and owner customer ID. Keep identifiers internal. For exact-device speech, select one online `ECHO` with a case-insensitive exact name match.

## Exact-Device Speech

Account-wide announcement endpoints can broadcast. To speak on one Echo, submit a behavior preview:

```http
POST https://alexa.amazon.com/api/behaviors/preview
```

Outer payload:

```json
{
  "behaviorId": "PREVIEW",
  "sequenceJson": "<serialized sequence object>",
  "status": "ENABLED"
}
```

Sequence object:

```json
{
  "@type": "com.amazon.alexa.behaviors.model.Sequence",
  "startNode": {
    "@type": "com.amazon.alexa.behaviors.model.OpaquePayloadOperationNode",
    "type": "Alexa.Speak",
    "operationPayload": {
      "deviceType": "<internal>",
      "deviceSerialNumber": "<internal>",
      "locale": "es-MX",
      "customerId": "<internal>",
      "textToSpeak": "<validated text>"
    }
  }
}
```

A successful call observed in practice returned HTTP 200 with an empty body. Treat status 200 as command acceptance; ask the user or use available playback state if physical confirmation is required.

### Manual briefs and screen-capable Echos

Keep scheduled and manually authorized speech modes separate. A scheduled helper may require a fixed opening and narrow local-time window. For an ad hoc brief, add a distinct `manual-brief` mode and require an explicit outside-window flag for live playback; do not globally remove the scheduled safeguards. The same audit-file → dry-run → one live call sequence still applies.

`devices-v2` may report capabilities such as `EFDCARDS` on an Echo with a screen. This confirms display/card capability at the device level, but an `Alexa.Speak` behavior response does not confirm that a visual card or transcription rendered. Report independently:

- exact target found and online,
- voice behavior accepted (for example HTTP 200), and
- visual rendering unverified unless a separate card/display API response or observable device state proves it.

Do not imply a persistent card was shown merely because the target has a screen. If no verified display operation is available, send targeted voice and state the limitation plainly.

## Smart-Home Discovery via Nexus

```http
POST https://alexa.amazon.com/nexus/v1/graphql
```

Useful query shape:

```graphql
query CustomerSmartHome {
  endpoints(endpointsQueryParams: { paginationParams: { disablePagination: true } }) {
    items {
      endpointId
      friendlyName
      displayCategories { all { value } primary { value } }
      legacyIdentifiers { chrsIdentifier { entityId } }
      legacyAppliance {
        applianceId
        applianceTypes
        friendlyName
        entityId
        capabilities
      }
    }
  }
}
```

`legacyAppliance.capabilities[].interfaceName` identifies supported controls. Verify writable properties (`readOnly: false`) where supplied.

Do not rely on this endpoint for smart-home friendly names:

```http
POST https://alexa.amazon.com/api/smarthome/v2/endpoints
```

It may return only Echo transport records with keys such as `identifier`, `serialNumber`, and `endpointDecorators`, while `endpointRepresentationsByContext` is null.

## Read Appliance State

```http
POST https://alexa.amazon.com/api/phoenix/state
```

Payload pattern:

```json
{
  "stateRequests": [{
    "entityId": "<legacy appliance ID>",
    "entityType": "APPLIANCE",
    "properties": [
      {"namespace": "Alexa.PowerController", "name": "powerState"},
      {"namespace": "Alexa.TemperatureSensor", "name": "temperature"},
      {"namespace": "Alexa.ThermostatController", "name": "targetSetpoint"},
      {"namespace": "Alexa.ThermostatController", "name": "thermostatMode"},
      {"namespace": "Alexa.EndpointHealth", "name": "connectivity"}
    ]
  }]
}
```

`deviceStates[].capabilityStates` can be an array of JSON-encoded strings. Parse each element independently and key it by `namespace.name`; skip malformed entries without losing the entire response.

## Power Control via Nexus

Mutation:

```graphql
mutation togglePowerFeatureForEndpoint(
  $endpointId: String,
  $featureOperationName: FeatureOperationName!
) {
  setEndpointFeatures(
    setEndpointFeaturesInput: {
      featureControlRequests: [{
        endpointId: $endpointId,
        featureName: power,
        featureOperationName: $featureOperationName
      }]
    }
  ) {
    featureControlResponses { endpointId __typename }
    errors { endpointId code __typename }
    __typename
  }
}
```

Variables for power on:

```json
{
  "endpointId": "<internal endpoint ID>",
  "featureOperationName": "turnOn"
}
```

Use `turnOff` only with explicit authorization. Check all three layers:

1. HTTP status.
2. Top-level GraphQL `errors`.
3. `data.setEndpointFeatures.errors`.

Then re-read Phoenix state. Poll at most a few times with a short delay to allow propagation. If pre-state and post-state are both `ON`, report “already on; command accepted,” not “turned on from off.”

## Thermostat Mode and Setpoint Control

Use separate writes and verify each one. If the mode already matches, do not resend it.

Phoenix mode control was observed to work with:

```http
PUT https://alexa.amazon.com/api/phoenix/state
```

```json
{
  "controlRequests": [{
    "entityId": "<legacy appliance ID>",
    "entityType": "APPLIANCE",
    "parameters": {
      "action": "setThermostatMode",
      "thermostatMode": "COOL"
    }
  }]
}
```

For target temperature, do **not** trust Phoenix HTTP acceptance alone. In observed integrations, both `setTargetSetpoint` and `setTargetTemperature` returned HTTP 200 while `targetSetpoint` remained unchanged. Use Nexus `setEndpointFeatures` instead:

```graphql
mutation setThermostatSetpoint($endpointId: String, $payload: JSON) {
  setEndpointFeatures(
    setEndpointFeaturesInput: {
      featureControlRequests: [{
        endpointId: $endpointId,
        featureName: thermostat,
        featureOperationName: setTargetSetpoint,
        payload: $payload
      }]
    }
  ) {
    featureControlResponses { endpointId __typename }
    errors { endpointId code __typename }
  }
}
```

Variables for 20 °C:

```json
{
  "endpointId": "<internal endpoint ID>",
  "payload": {
    "targetSetpoint": {
      "value": 20,
      "scale": "CELSIUS"
    }
  }
}
```

This contract was confirmed through GraphQL introspection:

- `FeatureName` contains `thermostat`.
- `FeatureOperationName` contains `setTargetSetpoint` and `setThermostatMode`.
- `FeatureControlRequest` accepts `endpointId`, `featureName`, `featureOperationName`, optional `instance`, and a JSON `payload`.

After the mutation, check top-level and nested errors, then poll Phoenix state until both `thermostatMode` and `targetSetpoint` match or the bounded retry budget expires. Report failure if HTTP 200 is returned but state does not change.

## Exact-device recurring weekday alarm

When cookie authentication is available but the newer alerts API bearer token is not, prefer an exact-device `Alexa.TextCommand` behavior over hand-crafting a private alarm payload:

1. Read `GET /api/notifications?cached=false` and resolve one exact online Echo through `devices-v2`.
2. Check whether that device already has an active 06:00 weekday alarm; do not modify old one-off or disabled alarms.
3. Submit one `PREVIEW` sequence with `type: Alexa.TextCommand`, `skillId: amzn1.ask.1p.tellalexa`, exact device identifiers, locale, and a natural-language command such as “pon una alarma a las seis de la mañana de lunes a viernes”.
4. Do not automatically retry an ambiguous behavior response.
5. Re-read uncached notifications and require exactly one matching active alarm on the same device.

In a verified Spanish-locale response, a Monday-through-Friday alarm appeared with:

```text
originalTime: 06:00:00.000
status: ON
recurringPattern: XXXX-WD
```

Treat `XXXX-WD` as the weekday marker. Other response generations may expose `rRuleData.frequency: WEEKLY` plus weekday codes or `trigger.recurrence`; normalize and verify these representations rather than assuming one schema forever. A behavior HTTP 200 is only command acceptance; the notification re-read proves alarm creation.

## Scheduled Spoken Brief Pattern

A robust job uses two helpers:

1. **Collector:** emits source-grounded JSON with current weather, prior-day operational summaries, live monitor comparisons, timestamps, and speech constraints. It must not mutate monitor baselines.
2. **Speaker:** validates exact opening, character bounds, forbidden terms, one exact online Echo target, and local-time window; supports dry-run and a separate explicit manual-test override.

Recommended execution sequence:

1. Generate prose from collector output.
2. Save exact speech to a local audit file.
3. Run speaker in dry-run mode.
4. If valid, perform one live playback.
5. Do not automatically repeat live playback after ambiguous network failures.

When the brief is Alexa-only, configure scheduler delivery as local to avoid a duplicate chat message.

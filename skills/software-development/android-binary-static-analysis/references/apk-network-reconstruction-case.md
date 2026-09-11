# APK network reconstruction case

Condensed evidence pattern from an authorized local base APK and split set. Credential-like values are intentionally omitted.

## Discovery reconstruction

- A Retrofit interface declared `GET api/v3/app`.
- Its suspend method accepted an authorization-like token and a country value.
- The coroutine called `Locale.getCountry()` and forwarded it to Retrofit.
- A Moshi adapter mapped the response into region, user/identity pools, app client configuration, MQTT, CA, firmware, API, marketing, and analytics fields.
- The response was serialized to application preferences, proving a cached configuration path.

Technique: combine the Retrofit interface, coroutine `invokeSuspend`, Kotlin metadata, constructor order, and generated adapter. Any one source is incomplete.

## Dynamic AWS configuration

A utility constructed an in-memory AWS configuration from discovery fields:

```json
{
  "Version": "1.0",
  "CognitoUserPool": {
    "Default": {
      "AppClientSecret": "[REDACTED]",
      "AppClientId": "<discovery.appClientId>",
      "PoolId": "<discovery.userPoolId>",
      "IdentityPoolId": "<discovery.identityPoolId>",
      "Region": "<discovery.region>"
    }
  }
}
```

That object initialized `AWSMobileClient`; the discovered API URL separately fed `ApolloClient.Builder.serverUrl(...)`. Backend and Cognito selection were therefore dynamic.

## Authentication flow selection

The wrapper called `AWSMobileClient.signIn(email, password, null)`. The bundled SDK selected `CUSTOM_AUTH` or `USER_PASSWORD_AUTH` only when configured; otherwise it explicitly constructed the default `USER_SRP_AUTH` details. The generated AWS configuration did not set `Auth.authenticationFlowType`, so SRP was code-backed while account-specific challenges/MFA remained runtime UNKNOWN.

## Proving the AppSync token type

The authorization callback called `AWSMobileClient.getTokens()`, selected the second token getter, then its token string. Proof that this was the ID token:

1. `CognitoUserSession` fields were typed ID, access, and refresh.
2. The SDK converted them into its generic container in access, ID, refresh order.
3. The interceptor selected the second getter.

Thus GraphQL used the Cognito ID token, not the access token.

## Exact GraphQL extraction

Full Apollo documents survived as DEX strings. Extracting lines beginning with `query`, `mutation`, `subscription`, or `fragment` and deduplicating them exposed exact resolver/field names. This invalidated a provisional local schema: resolver and field names differed, pressure/zones were serialized fields, and no guessed continuation token appeared.

Rule: when generated documents exist, update the local client from them before any live request.

## Tool fallback that worked

Without JADX:

- `apkanalyzer dex code --class ...` produced focused smali.
- SDK baksmali produced a searchable corpus after building a recursive cmdline-tools JAR classpath and invoking `com.android.tools.smali.baksmali.Main` directly.
- Kotlin metadata and generated adapters recovered semantics despite R8 one-letter names.

This reconstructed discovery → configuration → Cognito → Apollo authorization without network access.

## Transition from static proof to a minimal live probe

When the user later authorizes network access, do not jump directly to account login. Validate discovery first as a separate, bounded step:

1. Re-read the Retrofit parameter annotations to prove the exact header and query names. In this case they were `Authorization` and `countryCode`; Kotlin metadata alone had preserved only the semantic names.
2. Trace the embedded application authorization value to its construction site. Extract it programmatically from the local artifact at runtime rather than copying it into chat, shell history, or tool output.
3. Send one `GET` to the exact discovered host/path with redirects disabled and a short timeout.
4. Validate only the required configuration keys and endpoint shapes before accepting the response.
5. Store the complete response atomically in a private directory/file (`0700`/`0600`) because discovery may return client secrets, API tokens, or other credential-like configuration.
6. Print only sanitized metadata: HTTP status, country, region, endpoint host, field names, destination path, and file mode.

A successful discovery probe does **not** authorize account access. Cognito credentials, MFA, password-manager unlocks, and private GraphQL queries remain a separate human authentication boundary; never move those secrets through chat.

## Updating a provisional client after extraction

Use tests to encode the generated document before changing production code, then observe RED on every provisional mismatch. In this case the durable correction pattern was:

- resolver `sessions(...)`, not a guessed `getBrushingSessions(...)`;
- official session field names such as `sessionId`, `sessionStartTime`, and `brushingDuration`;
- pressure split across distribution, duration, event count, and zoned pressure fields;
- zoned data accepted as AWSJSON that may arrive serialized or already decoded;
- no continuation token unless the extracted document actually requests one;
- AppSync authorization with the Cognito **ID token**, while refresh still uses the refresh-token flow.

For nullable enrichment, infer a guided session only from positive cloud evidence such as non-null coverage or zoned brush data. Preserve absent metrics as `None`; do not manufacture zero coverage or empty zones. Run the focused client tests first, then the full suite and dependency check before any account-specific probe.

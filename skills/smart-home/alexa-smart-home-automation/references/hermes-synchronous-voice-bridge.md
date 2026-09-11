# Hermes synchronous voice bridge for Alexa

Use this pattern when an Alexa custom skill must call Hermes and return speech in the same request.

## Official ASK constraints

### Free-form voice input

Use one `AMAZON.SearchQuery` phrase slot for relatively open-ended input. Amazon currently lists Spanish ES, MX, and US support. A skill can use no more than one phrase slot per intent; `SearchQuery` cannot be combined with another intent slot in the same sample utterance, and normal samples require carrier text such as `pregunta {query}` or `consulta {query}`. This is search-like open input, not unrestricted dictation. See the official [slot type reference](https://developer.amazon.com/en-US/docs/alexa/custom-skills/slot-type-reference.html).

### Web endpoint and request verification

The custom web service must be Internet-accessible over HTTPS on port 443, use a certificate whose SAN contains its domain, and implement the ASK JSON interface. Self-signed certificates are for testing only; publishing requires a trusted CA.

Prefer an ASK SDK adapter. If validating manually, preserve the raw body and validate `SignatureCertChainUrl` before fetching it: normalized HTTPS URL, exact host `s3.amazonaws.com`, case-sensitive `/echo.api/` path prefix, and port 443 if present. Validate the X.509 chain, validity dates, trusted root, and leaf SAN `echo-api.amazon.com`; then verify `Signature-256` over the raw body with SHA-256. Reject timestamps more than 150 seconds from current time. Also require the expected application ID and deduplicate `requestId`. See [Host a Custom Skill as a Web Service](https://developer.amazon.com/en-US/docs/alexa/custom-skills/host-a-custom-skill-as-a-web-service.html).

### Hard response deadline

Alexa allows approximately eight seconds for the complete response. Progressive responses do **not** extend this deadline; at most five are allowed per request, only for `LaunchRequest` and `IntentRequest`, and all must precede the final response. Keep the bridge deadline shorter, normally 5–6.5 seconds. See [Progressive Responses](https://developer.amazon.com/en-US/docs/alexa/custom-skills/send-the-user-a-progressive-response.html) and the [REST API reference](https://developer.amazon.com/en-US/docs/alexa/custom-skills/progressive-response-api-reference.html).

Alexa response limits include 8,000 characters for `outputSpeech`, 8,000 total card-text characters, and 2,000 characters per image URL. Embedded `<audio>` limits do not extend the processing deadline. Prefer short spoken summaries and continuation intents. See the [request/response JSON reference](https://developer.amazon.com/en-US/docs/alexa/custom-skills/request-and-response-json-reference.html).

### Sessions and long-running jobs

`shouldEndSession: false` reopens the microphone only for a few seconds; include a reprompt. Session attributes disappear when the Alexa session ends. Keep a bridge-owned conversation ID in durable storage and use session attributes only for compact transient references. Alexa `userId` stays stable while the skill remains enabled but changes after disable/re-enable. See [Manage Skill Sessions](https://developer.amazon.com/en-US/docs/alexa/custom-skills/manage-skill-session-and-session-attributes.html).

For work that cannot finish before the deadline, enqueue a persistent job, return an acknowledgement, and expose status/result/cancel intents. Proactive Events require opt-in and predefined schemas/templates, while Reminders require permission plus explicit consent and a trigger time; neither is a generic channel for speaking arbitrary completed Hermes output. See [Proactive Events](https://developer.amazon.com/en-US/docs/alexa/smapi/proactive-events-api.html) and [Reminders](https://developer.amazon.com/en-US/docs/alexa/smapi/alexa-reminders-overview.html).

## Recommended boundary

Keep the Alexa bridge as a standalone external service or standalone plugin repository. Do not expose Hermes directly or add Amazon-specific protocol handling to core. The bridge owns Alexa request verification, authorization, replay protection, voice response shaping, and latency policy; Hermes remains behind its existing API Server.

```text
Alexa Skill -> narrow HTTPS bridge -> Hermes API Server on loopback/private network
```

The public bridge should expose only the Alexa webhook. Keep Hermes bound to loopback when possible. Store `API_SERVER_KEY` only at the private bridge-to-Hermes hop. Do not enable browser CORS for this server-to-server flow.

## Interaction model for open-ended speech

Use a custom intent with exactly one `AMAZON.SearchQuery` slot for relatively free-form utterances. This slot is search-like recognition, not unrestricted dictation, so design the language model deliberately:

- Use one `AMAZON.SearchQuery` slot per intent.
- Do not combine it with another slot in that intent's sample utterances.
- Include carrier phrases such as `pregunta {query}`, `dile a Hermes {query}`, and `consulta {query}`; a bare `{query}` sample is not a normal valid utterance.
- Treat `publishingInformation.locales[*].examplePhrases` as display metadata only. It does not add NLU samples. Keep every advertised command synchronized with an actual intent sample and cover that mapping with a JSON regression test.
- Account for invocation grammar stripping the skill name and wrapper. For example, `Alexa, dile a Hermes personal que diga hola` normally leaves an in-skill utterance shaped like `diga hola`; include `diga {query}` if that command is advertised.
- Add locale-specific variants and test on the actual Echo. `AMAZON.SearchQuery` availability and recognition quality vary by locale.
- Keep launch, stop/cancel, confirmation, and approval intents separate from the free-form query intent.

### Natural-question UX without a canned topic list

Do not confuse a carrier phrase with a closed question list. `AMAZON.SearchQuery` accepts open-ended slot content, but Amazon requires carrier text in every normal sample utterance; a bare `{query}` is not valid. Therefore, do not promise guaranteed one-shot grammar of `Alexa, <invocation> <arbitrary text>`.

Offer two honest interaction modes:

1. **One shot:** use Alexa's supported invocation wrapper, for example `Alexa, pregúntale a Hermes personal cómo se forman las nubes`.
2. **Two turns:** launch with `Alexa, Hermes personal`; return `shouldEndSession: false` plus a reprompt; while the microphone remains open, let the user ask a natural question.

For direct natural questions, define one `AMAZON.SearchQuery` intent per question carrier because Alexa omits the carrier from the slot value:

```json
{"name":"AskHermesHowIntent","slots":[{"name":"query","type":"AMAZON.SearchQuery"}],"samples":["cómo {query}"]}
```

Map the intent back to its stripped prefix before Hermes dispatch (`AskHermesHowIntent -> "cómo"`). Use separate mappings for `qué`, `cuál`, `cómo`, `cuándo`, `dónde`, `quién`, and `por qué`; do not combine a second carrier slot with `SearchQuery`. Test both the JSON model and event-to-query reconstruction, submit asynchronously, poll `interactionModel` to `SUCCEEDED`, then read the remote model back and count the expected intents.

Treat phrases used during setup as probes, not the product interface. A test such as `que diga <text>` can confirm routing but should not be presented as the only way to ask Hermes anything.

### Multi-Echo routing and the closed-assistant boundary

Enabling a development/custom Skill on an Amazon account can make it available from compatible Echo devices on that account, but it does not replace Alexa's default dispatcher. Distinguish three boundaries:

1. **Before invocation:** Amazon owns wake-word handling, ASR, intent arbitration, and which capability receives the utterance. A routine can match named phrases but cannot forward a wildcard tail; `AMAZON.FallbackIntent` sees only utterances spoken after the Skill is already active.
2. **Inside the Skill:** the signed envelope includes `context.System.device.deviceId`. Derive an opaque per-Echo conversation key with HMAC (include the Skill ID/domain separator), never persist or log the raw device ID, and keep Alexa user authorization as a separate check. The final ASK response naturally returns to the Echo that originated the request; no private exact-device speech call is needed for the synchronous turn.
3. **Outside ASK:** private web/mobile APIs can discover devices, control supported capabilities, and trigger exact-device speech, but they do not provide a stable supported stream of microphone audio or arbitrary recognized utterances and cannot reconfigure an Echo's primary cloud endpoint.

Do not overstate Name-Free Interaction. Verify current official eligibility before designing around it. In Amazon's July 2026 documentation, the NFI toolkit was limited to hidden Alexa Smart Properties skills and English locales; Alexa selected among eligible skills using its own signals, certification/publication could take weeks to learn routing, and the developer could not force all utterances to one handler. This did not provide a universal `es-MX` catch-all.

If the requirement is truly `Hermes <arbitrary speech>` with no Amazon-controlled invocation grammar, use a separate voice satellite: local wake word, microphone/STT, authenticated Hermes request, TTS, and a local speaker. An Echo may be used as an output speaker where appropriate, but do not assume its closed microphones can be repurposed. Keep this architecture distinct from ASK and from private exact-device speech automation.

### Diagnose timely HTTP 200 with a silent Echo

When a physical Echo lights up but remains silent, inspect the latest real request before changing code:

1. Confirm a new signed `POST /alexa`, status, and duration in the tunnel inspector.
2. Decode the inspector's Base64-encoded raw HTTP response locally; never print request headers, signatures, certificate values, user IDs, or full private payloads.
3. Report only safe fields: request type, intent name, slot presence, response version, `outputSpeech.type`, bounded speech text/length, reprompt presence, and `shouldEndSession`.
4. A timely `HTTP 200` containing valid nonempty `PlainText`/SSML proves recognition, Hermes dispatch, bridge serialization, and delivery to Amazon's HTTP boundary. Silence after that point is downstream rendering—not evidence that NLU or Hermes failed.
5. Isolate the Echo path with a built-in request such as asking the time, then check exact-device volume, DND, connectivity, and Amazon service health. Do not automatically change volume or play test speech without current authorization. Retry the Skill once only after the ordinary Alexa audio path is known to work.

If no POST exists, return to invocation/NLU diagnosis. If the POST is slow or lacks speech, debug Hermes/bridge. If it is `401`, retain fail-closed verification and classify signature, timestamp, application ID, user allowlist, or replay failure without weakening security.

When AWS Lambda is the Custom Skill endpoint, constrain the Lambda permission to the exact Alexa Skill ID so Amazon handles the public invocation boundary. If using a custom HTTPS service instead, validate Alexa's certificate/signature chain, timestamp, application ID, and request replay controls yourself. Lambda still needs a private authenticated route to Hermes; do not expose the raw API Server merely because the Alexa-facing function is trusted.

## No-AWS development path and local harness

A personal developer can use an ordinary Amazon account to enroll in Alexa Developer and choose a custom HTTPS web-service endpoint; a separate AWS account is not required. For same-day development, a free ngrok account with a stable development domain can front a narrow local facade:

```text
Echo -> Alexa Custom Skill -> ngrok HTTPS -> 127.0.0.1:<facade-port>/alexa -> Hermes 127.0.0.1:8642
```

Do **not** tunnel Hermes port 8642 directly. Bind the Alexa facade to loopback, expose only `/alexa` (plus an inert `/health` if needed), cap the body, disable payload logging, and keep the Hermes bearer secret only on the private facade-to-Hermes hop.

For Python custom web services, `ask-sdk-webservice-support` can be reused without adopting the entire ASK intent framework. Preserve the raw body, deserialize it as `ask_sdk_model.RequestEnvelope`, then run both `RequestVerifier` and `TimestampVerifier` before JSON dispatch. After SDK verification, enforce the exact `applicationId`, user/account allowlist, and request-ID replay cache in the facade. Tests may inject fake verifiers into a pure request processor, but the public server must never start with signature or timestamp verification disabled.

Recommended local harness layers:

1. Pure event-to-response bridge with an injected Hermes client.
2. Pure request processor that verifies the raw request before dispatch.
3. Loopback-only HTTP server with one Alexa POST route, bounded body size, no-store responses, and sanitized errors.
4. Real local E2E using a simulated Alexa event against Hermes `/v1/responses`; record latency and require margin below Alexa's deadline.
5. Public tunnel only after exact Skill ID and live SDK verification are configured.

Keep ngrok credentials out of chat, source, shell history, and process arguments. Prefer a local hidden-input helper that atomically writes `~/.config/ngrok/ngrok.yml` with mode `0600`; validate only with `ngrok config check`, never print the token. A safe ngrok v3 config shape is:

```yaml
version: "3"
agent:
  authtoken: "<hidden local input>"
```

Use a stable reserved development domain so the Alexa endpoint does not change on each run. Free ngrok accounts may currently receive domains under `.ngrok-free.dev` as well as older `.ngrok-free.app`/`.ngrok.app` suffixes; validate HTTPS and an expected ngrok suffix rather than hard-coding one historical domain.

For a private development Skill whose ASK `userId` is unknown before the first live invocation, use a one-time enrollment gate rather than logging or asking the user to paste the raw ID:

1. Verify Amazon signature/certificate and timestamp over the raw body.
2. Require the exact expected Skill/application ID.
3. Hash the authenticated `userId` with SHA-256 and atomically create a mode-0600 allowlist file (`O_CREAT | O_EXCL`); never persist the raw ID.
4. Authorize later requests only when their hash is present, and reject all other users.
5. Disable enrollment after the first successful invocation. Keep the Skill in development/private testing while enrollment is enabled.
6. Apply replay protection after identity authorization but before Hermes dispatch so duplicate `requestId` values cannot compute or mutate twice.

When testing the loopback facade, bind explicitly to `127.0.0.1` and inspect the listener including PID and bound address. Another process can legitimately use the same numeric port on a Tailscale/LAN address; do not kill it or infer that the bridge is public. Configure ngrok against the explicit loopback URL, not an ambiguous hostname or bare port.

The official ASK CLI can automate interaction-model and endpoint configuration after `ask configure` completes its browser OAuth callback on localhost. Human login, MFA, Developer enrollment, and consent remain user-owned boundaries. ASK CLI v2 may continue waiting after browser success until its terminal prompt is explicitly confirmed; then, for a custom HTTPS/no-AWS route, decline AWS association so it does not create an IAM user or access keys.

Install the CLI as an isolated development tool, inspect its dependency audit, and do not add it to the runtime bridge environment; package-manager prefix installs may require explicitly linking the package's declared `bin` entry into the user's executable path. Verify Skill access with `ask smapi get-skill-manifest --skill-id <id> --stage development` rather than assuming older `get-skill` examples still exist.

Before replacing an interaction model, save the current model as a rollback artifact. Apply the new model with `ask smapi set-interaction-model --interaction-model file:<path>`. This operation is asynchronous: poll `ask smapi get-skill-status --skill-id <id> --resource interactionModel` to `SUCCEEDED` or `FAILED`, then read it back with `get-interaction-model` and verify invocation name, intent names, and the `AMAZON.SearchQuery` slot. A successful submit response alone is not deployment verification.

For a custom HTTPS endpoint, also preserve the current manifest, set `apis.custom.endpoint.uri` to `<stable-ngrok-url>/alexa`, and choose `sslCertificateType` from the certificate shape—not merely from whether a public CA issued it:

- Use the exact case-sensitive enum `Wildcard` when the endpoint hostname is covered by a wildcard CN/SAN such as `*.ngrok-free.dev`.
- Use `Trusted` when the trusted certificate names the endpoint without relying on a wildcard.
- Use `SelfSigned` only for the corresponding development-only case.

For ngrok free domains backed by `*.ngrok-free.dev`, declaring `Trusted` can make Alexa fail with `SSL certificate verification failed` before sending an HTTP request; the ngrok request log will therefore remain empty. Upload with `ask smapi update-skill-manifest`, poll the manifest resource to `SUCCEEDED`, then read back both the default and any regional endpoint and confirm the exact `sslCertificateType`. A misspelled/case-variant value such as `WildCard` is rejected by SMAPI; the valid enum is `Wildcard`.

Verify that an unsigned POST to `/alexa` returns `401` before enabling the development Skill with `set-skill-enablement` and confirming via `get-skill-enablement-status`.

Do not treat SMAPI `simulate-skill` as proof of the cryptographic ingress boundary. In an observed custom-HTTPS development flow, SMAPI reached `/alexa` without `Signature` or `SignatureCertChainUrl`; the correctly hardened bridge returned `401`. Never disable signature verification just to make the simulator green. Verify unsigned rejection separately, then perform the signing, first-user enrollment, and spoken-response E2E from the real Echo or another ASK path proven to carry those headers. During diagnosis, inspect only HTTP status and header names—not header values, signatures, raw bodies, or ASK user IDs.

### Diagnose “Alexa cannot connect” by traffic boundary

Classify the failure before editing bridge code:

- Query ngrok's local request API and report only method, path, status, and whether both signature header names are present.
- If a new request reached `/alexa`, debug the returned status at the facade. A signed `401` points to signature/timestamp/identity checks; an unsigned `401` can be a simulator limitation.
- If no request reached ngrok, the failure is upstream of the bridge. Verify model and manifest are `SUCCEEDED`, read back the exact endpoint and certificate-shape-appropriate SSL type (`Wildcard` for ngrok wildcard domains), confirm development enablement, and check that the Skill appears under `Alexa app → Tus skills → Dev`. If Alexa's app/test UI exposes technical diagnostics, inspect them before changing locales or bridge code: `SSL certificate verification failed` plus a wildcard CN/SAN is decisive evidence that ASK's `sslCertificateType` is wrong even though ordinary `curl` HTTPS health checks pass.
- **Do not assume the Dev Skill detail page has a Launch/Open button.** Some current Android Alexa app builds show only `DISABLE`, example invocation phrases, and the bottom `Ask Alexa` text field. In that UI, type the exact invocation into `Ask Alexa` to bypass microphone/ASR uncertainty, or invoke it from the Echo; record Alexa's exact response and immediately re-check ngrok traffic.
- Treat the Skill page's generic notice that language support is limited for Alexa+ customers as a compatibility clue, not proof that the account uses Alexa+ or that Alexa+ caused the failure. Establish account/device generation through an authoritative read-only source when available; otherwise label it unresolved.
- A successful model/manifest build proves accepted configuration, not physical-device routing. A successful SMAPI simulation proves NLU selection, not signed Echo delivery.
- After changing an endpoint, disable and re-enable only that development Skill to refresh stale enablement. For a Mexican/North American Echo, keep the default endpoint and, when routing remains ambiguous, declare the same narrow endpoint explicitly under `apis.custom.regions.NA.endpoint`; poll and read it back before retrying.
- Do not infer device locale from `devices-v2` when it returns `language: null`. Correlate the exact device internally with read-only `/api/device-preferences?cached=false`; report only locale/country and never serials, owner/customer IDs, or cookies.
- If app launch and spoken launch both produce no ngrok request despite matching locale and confirmed enablement, investigate Amazon account/Dev-Skill visibility, propagation/cache, and regional routing rather than weakening verifier security.

When enabling Hermes API Server from an active Hermes gateway conversation, persist `API_SERVER_ENABLED` and a strong `API_SERVER_KEY`, then have the user issue the native `/restart` command. Do not try to restart the gateway from a child process of that same gateway; self-restart protection intentionally blocks it and killing the parent can strand the active session. After restart, verify `/health`, authenticated `/v1/capabilities`, and that the listener remains on loopback.

## Endpoint choice

For short synchronous turns, prefer `POST /v1/responses` with `stream: false`. During diagnosis, exercise the bridge's actual `HermesClient` against the live API with the same bearer source and response parser; `/health` proves only process availability, and probing a guessed route such as `/api/chat` can create a false diagnosis. Record only status, text presence/length, and elapsed time—never the bearer or full private response.

```json
{
  "model": "hermes-agent",
  "input": "<normalized utterance>",
  "conversation": "alexa:<opaque conversation id>",
  "instructions": "Answer briefly in the user's locale for spoken delivery.",
  "store": true,
  "stream": false
}
```

Use three separate identifiers:

- `conversation`: HMAC of `skillId || Alexa sessionId`; short-lived voice-dialog continuity.
- `X-Hermes-Session-Key`: HMAC-derived stable user/channel scope for long-term memory; never send the raw Amazon user ID.
- `Idempotency-Key`: HMAC-derived Alexa `requestId` for retry deduplication.

Serialize requests per conversation. Named-conversation lookup/update is not a substitute for a per-conversation mutex when two turns can arrive concurrently.

`/v1/responses` named conversations use the persistent `response_store.db`, but the current default is a global 100-response LRU. Treat them as short-session continuity, not unlimited durable storage. For larger-scale durable transcripts, track the returned `X-Hermes-Session-Id` and use the session-continuity path or Sessions API.

## Per-surface low-latency model routing

When Alexa works end to end but approaches its response deadline, route only the voice surface to a fast model rather than changing the user's global Hermes/WhatsApp model. The API Server supports `model_routes` aliases advertised by `/v1/models`; the bridge sends the alias in the normal Responses API `model` field. Keep the stable named `conversation` and memory/session scope unchanged: model selection and conversation continuity are separate concerns.

A safe rollout sequence is:

1. Exercise the bridge's actual client against the current model and record total latency, text presence/length, and error class without logging prompts, private responses, or bearer values.
2. Configure the candidate provider credential locally with hidden input, validate it read-only against the provider's model-list endpoint, and keep it in the profile's mode-0600 secret store.
3. Add an API Server alias such as `alexa-fast`; do not change the global model.
4. Benchmark current and candidate routes with the same voice instruction, same bounded context, and several cold/warm requests. Measure time to first token when streaming is available, total time, success rate, and spoken-answer quality. A provider's advertised output tokens/second does not measure prompt-prefill or network latency.
5. Only after the benchmark, switch the bridge's `model` field to the alias. Preserve a rollback alias/config and run a real Echo E2E.
6. If the fast route fails, return a short deterministic Alexa fallback or attempt at most one fallback model only when enough deadline remains. Never let provider retries consume Alexa's entire response window.

Prefer named-provider credential resolution over embedding an upstream key in `platforms.api_server.extra.model_routes`. In gateway versions where that platform block is loaded with raw `yaml.safe_load`, a literal `${PROVIDER_API_KEY}` inside `extra.model_routes.*.api_key` may not be expanded. A route with `provider: custom:<name>` can instead resolve the corresponding named custom provider through Hermes' normal credential chain. Verify the effective alias via authenticated `/v1/models` and a real request after gateway restart; do not infer routing from configuration text alone.

"Use all context" does not mean unlimited or zero-cost context. Long prompts still add prefill latency and are bounded by the candidate model's context window. Keep the Alexa profile/system prompt compact, rely on Hermes named-conversation persistence and memory, permit compression, and use provider prompt caching when supported. As of July 2026, Cerebras documented production `gpt-oss-120b` at approximately 3000 output tokens/s, with 65k context on the free tier and 131k on paid tiers, plus tool calling and prompt caching; re-check the provider's official model documentation before deployment because model availability, limits, and deprecations change.

For voice, use low/minimal reasoning when the selected provider and Hermes request path explicitly support and honor it. Verify the actual request/runtime behavior rather than assuming a `reasoning_effort` field in one API format propagates through every route.

### Custom-provider route propagation and Cerebras rollout traps

A custom provider's configuration is not proof that its per-request options reach an API Server `model_routes` alias. Verify the resolved runtime and the live response path:

- A provider-level `extra_body: {reasoning_effort: low}` may normalize to `request_overrides.extra_body.reasoning_effort`, not a flat `request_overrides.reasoning_effort`. Inspect the effective runtime shape without printing credentials.
- Some Hermes versions resolved a named provider for a route but copied only credentials/base URL/transport, dropping `request_overrides` and provider output caps. Add a regression around `_resolve_runtime_agent_kwargs_for_provider()` and ensure API Server agent construction receives the resolved overrides.
- Put a validated positive `max_tokens` on the route when the installed API Server supports it. Do not assume a legacy custom-provider `max_output_tokens` field survives config normalization; read the route back and exercise the live alias.
- Keep the upstream key in a mode-0600 secret store and reference it with `key_env`; never place it inline in `model_routes`.

Large Hermes prompts and tool schemas can exhaust a free-tier tokens-per-minute quota even when generation itself is extremely fast. A `429` may trigger a provider retry around 60 seconds later, long after Alexa's caller has timed out. During rollout:

1. Space full-context benchmark calls by at least the provider's quota window instead of launching many consecutive E2Es.
2. Treat `429`, retry sleeps, and client disconnects as separate from generation latency.
3. For a synchronous voice route, prefer no long provider retry; return the deterministic spoken fallback within the bridge deadline. Ensure abandoned HTTP requests do not continue expensive retries or writes unnoticed.
4. Limit the API Server toolsets for the Alexa surface to the tools actually needed. “All context” does not require every tool schema on every request. Before changing `platform_toolsets.api_server`, inventory every consumer of that API Server because this setting is platform-wide, not inherently alias-specific. Prefer a dedicated Alexa profile/API Server if other clients need broader capabilities. An explicit configurable list reduces native schemas; include only the exact MCP server names required to make them an allowlist, or use `no_mcp` when none are needed. If no MCP name is explicitly listed, all globally enabled MCP servers may still be added by default. Measure the resolved toolsets and prompt size after configuration rather than inferring savings from YAML alone.

Use isolated, disposable conversation IDs for deployment E2Es. Reusing a failed test conversation can preserve tool calls or malformed assistant output and make a later clean build appear broken. Test with a neutral factual or greeting prompt; a phrase such as “prueba de voz” can be interpreted by a tool-capable model as an instruction to invoke Alexa speech recursively. The voice instruction should explicitly say that the bridge—not the model—renders the final text, and the bridge should reject/fallback on empty, malformed, reasoning-leaking, or overlong output. Do not require exact-string obedience as the only success criterion for an agentic model; also gate on nonempty clean speech, no fallback, session state, latency, and absence of unintended tools.

Run the bridge and public tunnel as independent supervised user services, not as session-scoped children of the Hermes gateway. Otherwise a gateway restart can silently stop both. Use loopback-only bridge/ngrok inspector listeners, `Restart=on-failure`, no inline secrets, startup health polling, and a post-start assertion that the live tunnel URL exactly matches every default/regional Skill manifest endpoint before asking for a physical Echo test.

## Latency and timeout contract

A synchronous Alexa turn has a small end-to-end response budget. Give Hermes a shorter bridge-side deadline (typically 5-6 seconds) so the bridge can still construct a valid Alexa response. Keep answers bounded for speech.

A client timeout does **not** prove that Hermes performed no tool action. Therefore:

- Never blindly retry writes after a timeout.
- Use a stable idempotency key for retries.
- Prefer read-only, low-latency tools on this route.
- Return a deterministic spoken fallback when the deadline expires.
- Do not offer background work unless another delivering surface exists; the API Server marks request/response routes as non-async-delivering.

### Long work with exact-Echo delivery

When the installation already has a verified exact-device speech path, long work can remain independent of WhatsApp:

1. Submit through `POST /v1/runs` with a stable idempotency/correlation key.
2. Wait only within the bridge's short synchronous budget. If unfinished, answer Alexa with a truthful acknowledgement such as “Hermes sigue trabajando; te aviso aquí al terminar.”
3. Persist `run_id`, target Echo's sanitized friendly-name selector, originating user scope, and expiration in a local queue. Never persist raw bearer tokens or internal Echo identifiers in the queue record.
4. A local worker polls/consumes run events and, on one terminal completion, resolves the exact Echo again from live discovery before using the targeted speech path.
5. Validate and bound the spoken result, then perform one playback. Do not broadcast and do not automatically repeat after an ambiguous playback timeout.
6. Mark delivery separately from computation: `run_completed`, `speech_accepted`, and `speech_verified` are distinct states.

Do not use a private exact-device speech API as the Alexa request ingress; use the supported Custom Skill ingress for voice capture. The private API is only a narrowly scoped optional delivery surface and must retain its own exact-target and verification safeguards.

## Approvals

Synchronous `/v1/responses` and `/v1/chat/completions` are not a usable interactive approval channel. A guarded operation can produce a pending-approval outcome, but the caller has no run-scoped approval endpoint for that synchronous request.

For a minimal voice bridge, use a dedicated Hermes profile with read-only or narrowly allowlisted tools and keep `approvals.mode: smart`; never solve the problem with approvals off.

If true interactive approval is required, use the Runs API:

1. `POST /v1/runs` and retain `run_id`.
2. Poll status or consume events within the Alexa turn budget.
3. On `waiting_for_approval`, ask a verbal confirmation and retain `run_id` in Alexa session attributes.
4. On a later affirmative intent, `POST /v1/runs/{run_id}/approval` with `{"choice":"once"}`.
5. Poll for completion; expose neither `session` nor `always` approval scopes through voice.

The bridge must manage any context needed by the run path; `session_id` is correlation/grouping and does not by itself load named-conversation history.

## Security checklist

- Validate Alexa's signature/certificate chain, application ID, and timestamp; reject replayed request IDs.
- Use a user/account allowlist for a private household skill.
- Put the public endpoint behind valid TLS, rate limiting, and a small body limit.
- Keep prompts, raw IDs, bearer tokens, and tool payloads out of logs.
- Keep Hermes on loopback/private networking; if remote access is required, tunnel to a narrow facade rather than exposing port 8642.
- Use a strong random bearer secret. A bearer token grants broad API Server access and is not endpoint-scoped, so the facade must restrict paths.
- Run a dedicated Hermes profile with minimal toolsets, a confined working directory, low `gateway.api_server.max_concurrent_runs`, and a sandboxed terminal backend if terminal access is unavoidable.
- Explicit verbal confirmation is required before physical, destructive, financial, or privacy-sensitive actions.

## Verification gates

1. Alexa signature, timestamp, app ID, allowlist, and replay tests.
2. Duplicate `requestId` produces one Hermes computation/action.
3. Concurrent turns for one conversation are serialized.
4. Bridge timeout returns valid speech and does not auto-retry a write.
5. Raw Amazon IDs and secrets never appear in Hermes headers, logs, or responses.
6. Hermes is unreachable publicly except through the restricted facade.
7. Read-only sync path works within the latency budget.
8. Approval path, if enabled, supports `once`, denial, timeout, and stale `run_id` without widening scope.

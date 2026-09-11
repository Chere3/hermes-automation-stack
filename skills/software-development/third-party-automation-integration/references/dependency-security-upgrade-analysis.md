# Dependency security upgrades: resolved-tree analysis

Use this note when an integration repository needs the **minimum secure and compatible** package versions rather than merely the first individually patched releases.

## Core rule

Determine safety from the installed dependency graph, not from top-level declarations or advisory ranges in isolation. A direct patched dependency does not neutralize a vulnerable exact transitive dependency; package managers can install both versions.

## Procedure

1. Record current direct and transitive versions from the manifest and lockfile.
2. Query registry metadata for candidate releases: dependencies, peer dependencies, engines, exports, and available versions.
3. Find the first release of the parent package whose own dependency range/version resolves to the patched child.
4. Build a disposable repository copy outside the working tree. Change only candidate versions there and regenerate the lockfile.
5. Inspect the resolved graph (`pnpm list <packages> --depth 3` and `pnpm why <package>`).
6. Inspect peer-dependency warnings and the versions the package manager actually installed. Auto-installed peers can select an older major, leave an unmet peer, or introduce a newly vulnerable branch even when the originally targeted packages are secure. If the application does not import the peer but the framework requires it, pin a compatible safe peer explicitly rather than ignoring the warning.
7. Run a production audit after the final peer resolution. Confirm every vulnerable path is absent, not merely that the direct package is patched.
8. Run type-check, tests, and the platform's real build/bundle dry-run. Dependency upgrades often expose generated-environment type constraints that unit tests miss.
9. Separate API findings into:
   - mandatory compile/runtime changes;
   - deprecated but still compatible APIs;
   - optional modernization.
10. Re-run graph inspection and audit after every lockfile-changing fix; an earlier clean disposable test does not prove the final working tree resolved identically.
11. Leave the source repository untouched when the task is analysis-only, and explicitly report that the validation occurred in a disposable copy.

## Useful commands

```bash
npm view PACKAGE@VERSION dependencies peerDependencies engines exports --json
pnpm list PARENT CHILD --depth 3
pnpm why CHILD
pnpm audit --prod --json
pnpm type-check
pnpm test
pnpm exec wrangler deploy --dry-run   # Cloudflare Worker example
```

Avoid forcing an exact transitive dependency with overrides unless there is no upstream-compatible release and the override is tested explicitly. Prefer the first parent release that natively resolves the patched child.

## MCP/Cloudflare example (February 2026 advisory)

`@modelcontextprotocol/sdk` versions `>=1.10.0 <=1.25.3` were affected by CVE-2026-25536 / GHSA-345p-7cg4-v4c7; `1.26.0` is patched. Although `agents@0.3.10` satisfied a separate minimum-version recommendation, it pinned SDK `1.25.2`, producing this unsafe graph even with a direct SDK `1.26.0`:

```text
@modelcontextprotocol/sdk 1.26.0
agents 0.3.10
└── @modelcontextprotocol/sdk 1.25.2
```

The first safe native pair was SDK `1.26.0` plus `agents@0.4.0`, whose dependency is SDK `1.26.0`.

That pair can still resolve an unsafe peer graph if the package manager chooses an older `ai` peer. In one pnpm working tree, `agents@0.4.0` required `ai@^6` but retained an auto-installed `ai@5.0.44`; the framework build and tests passed while `pnpm audit --prod` reported advisories in `ai` and `@ai-sdk/provider-utils`. Pinning a current compatible `ai@6` resolved the peer warning and produced a clean production audit. The durable lesson is to treat peer warnings plus the *post-install* audit as part of the security result; do not copy a “clean” conclusion from a disposable graph without checking the final lockfile.

Upgrading `agents` also changed `McpAgent`'s environment generic to `Env extends Cloudflare.Env`. For a local Zod-inferred application type that omits generated Durable Object bindings, preserve the application type and constrain only the agent:

```ts
export class MyMCP extends McpAgent<Cloudflare.Env & AppEnv> {}
```

Do not automatically intersect `Cloudflare.Env` into a broadly used parsed-env alias: values returned by the runtime schema parser may then incorrectly be required to contain platform bindings.

In SDK `1.26.0`, `McpServer.tool()` and `.prompt()` still work but are deprecated in favor of `registerTool()` and `registerPrompt()`. Report these as modernization, not mandatory migration. Likewise, `McpAgent.serveSSE()` remains available as a legacy API while `serve()` is preferred for Streamable HTTP.

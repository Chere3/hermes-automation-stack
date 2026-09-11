# Community MCP adoption notes

## High-value audit checks

- Inspect route dispatch before framework middleware. MCP and SSE paths may be handled before the REST app and therefore bypass its authentication.
- Search for every use of the documented auth variable. An environment schema containing `API_KEY` does not prove enforcement.
- Compare credential claims across README, setup guide, environment examples, and source. Cookie formats obtained from a normal website may not authorize private mobile endpoints.
- Treat reverse-engineered announcement/control endpoints and session cookies as fragile and privileged.
- If an MCP tool calls the same service's REST endpoint through `API_BASE`, adding auth middleware requires adding authorization to that internal call too.

## Safe local pattern

- Bind the development/runtime server explicitly to `127.0.0.1`.
- Require `Authorization: Bearer <token>` on REST, `/mcp`, `/sse`, and SSE message paths.
- Leave only a data-free health endpoint unauthenticated.
- Avoid global permissive CORS.
- Use dummy provider credentials and a test bearer token until all access-control checks pass.

## Protocol verification

A useful sequence is:

1. Health request returns `200`.
2. Functional REST route without token returns `401`.
3. MCP route without token returns `401`.
4. Functional route with token reaches application routing.
5. MCP SDK client connects with authorization headers and lists tools.
6. `ss -ltnp` confirms the intended bind address.
7. Stop the temporary server.

A raw authenticated GET to a Streamable HTTP MCP endpoint may return `406` when the client does not advertise `text/event-stream`; that can show auth was passed, but only an SDK initialization validates MCP behavior.

## Toolchain drift

A repository created with an older CLI can declare a caret range that installs a much newer release requiring a newer runtime. Pin the version known to match the project's runtime, then type-check and lint again. Record the pin rather than upgrading the host runtime opportunistically.

## Filesystem-corruption isolation

When install retries produce `Unknown system error -74` or `Bad message` and kernel logs report ext4 inode checksum errors:

- Do not keep pruning or reinstalling in the affected directory.
- Check `findmnt -T <path>`, `stat <exact-path>`, and recent kernel logs.
- Avoid offline repair actions while the user is actively working; obtain explicit approval for reboot or `fsck` planning.
- For diagnostic continuation, extract tracked source to `/dev/shm`, set the command's working directory to that path, and place package store/cache/data in tmpfs too.
- Before install, print and assert `pwd` equals the tmpfs project path. This prevents a common mistake where source is copied to RAM but the package manager still runs against the damaged disk checkout.
- Run build/type-check/security tests in RAM. Do not describe this as a durable installation, and stop temporary services afterward.

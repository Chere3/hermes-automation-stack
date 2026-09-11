# Hermes/Cua browser route for autonomous ATS applications

Use this route when an approved application must be completed autonomously and the base `browser_*` toolset does not expose file upload.

## Safety and scope

- One approved requisition per run; bind only the dedicated career browser window/profile.
- Never use VPNs, proxies, CAPTCHA bypasses, stealth toggles, direct ATS submission APIs/replay, or unrestricted driver mode. Public ATS APIs remain allowed for read-only job discovery only.
- Reuse the private persistent career profile at `~/.local/share/hermes/career-ops/chrome-profile` so ordinary first-party cookies and storage survive between unrelated applications. Never attach to the user's personal profile.
- CDP must remain loopback-only and is for exact binding, snapshots, and supported trusted input. Do not use Playwright/page evaluation to mutate applicant fields or submit.
- Final Submit must use a trusted visible UI action: Cua/browser trusted click, exact-bound native click, or keyboard activation on the focused visible button. Never use `input_route:dom_event`, `element.click()`, JavaScript dispatch, or an ATS API for Submit.
- A browser action result proves dispatch, not business completion. Re-snapshot and verify postconditions.
- Close the dedicated browser, driver daemon, tabs, and ephemeral scripts/screenshots after completion or blocker. Preserve the persistent profile; delete/rotate it only for corruption, compromise, or explicit user direction.

## Linux X11 exact-binding recipe

Cua Driver's typed browser mutations require all three:

- `status: "ok"`
- `binding_quality: "exact"`
- `mutation_allowed: true`

On a Wayland desktop with XWayland available, run the dedicated Cua daemon with `WAYLAND_DISPLAY` removed so its Linux platform adapter uses the X11 proof path (`_NET_WM_PID` plus endpoint-owner PID). Keep `DISPLAY` intact.

```bash
env -u WAYLAND_DISPLAY cua-driver serve \
  --socket "$HOME/.cache/cua-driver/cua-driver.sock" \
  --no-overlay --permission-mode standard
```

Prepare and launch the persistent career profile with the tested helper. Start `launch` through a tracked foreground process (`terminal(background=true)`); do not wrap it in `nohup`, `disown`, `setsid`, or `&`.

```bash
~/.hermes/skills/productivity/career-ops-stage/scripts/career-browser-session.sh prepare
~/.hermes/skills/productivity/career-ops-stage/scripts/career-browser-session.sh launch
```

The helper enforces a private `0700` profile at `~/.local/share/hermes/career-ops/chrome-profile`, loopback-only CDP on fixed port `9333`, X11 exact binding, a normal visible window, and no headless/stealth flags. It refuses launch when port `9333` is already occupied rather than attaching ambiguously.

Then:

1. `cua-driver call list_windows` and select the dedicated Chrome's exact `(pid, window_id)`.
2. Call `browser_prepare` for that PID. An already-owned loopback endpoint should report `already_prepared` and prove ownership, without changing browser state.
3. Call `get_browser_state` with `(pid, window_id, session)`.
4. Proceed only on exact binding and `mutation_allowed:true`; never weaken the check.
5. Keep one stable `session`, `target_id`, and `tab_id`. Navigation or a newer snapshot invalidates prior refs.

Generic Wayland shell/AT-SPI discovery may report useful windows but intentionally gives read-only heuristic bindings when compositor geometry cannot be attested. The durable recovery is to select a supported exact route (validated compositor or X11 proof path), not to use unrestricted mode.

## Form workflow

1. Navigate the exact bound tab to the approved regional `applyUrl`.
2. Take a `semantic_v2` snapshot and use only refs whose actions include the intended operation.
3. Fill staged text with `browser_type(..., replace:true)`.
4. Upload the exact staged CV through a ref with action `upload` using `browser_set_input_files`; use absolute regular-file paths.
5. Uploads and reactive controls may rerender the form. Take a fresh snapshot afterward and re-check every required field. A previous `browser_type` success is not proof the value persisted.
6. Resolve comboboxes/radios from fresh semantic refs or bounded visual coordinates, then snapshot again. Never claim a country/source option is selected merely because it was intended or visible.
7. Before Submit, verify required values, CV filename, regional role identity, and no new unanswered question. If any value is `null`/empty, correct it using a fresh ref.
8. Always press Submit for an approved application, but only through a trusted visible UI action. Prefer `browser_click` when its action reports a trusted route; otherwise use an exact-bound native click or focus the visible button and press Enter/Space. If Cua cannot produce trusted input, stop as a tooling blocker—never downgrade Submit to `input_route:dom_event`, Playwright/JavaScript click, or ATS API. Verify a requisition-specific confirmation or confirmation email before recording `applied`.
9. Distinguish client validation from a submission attempt. A banner such as “form needs corrections” or “missing required field” means the request did not leave the form: correct the already-covered value, re-verify it, and press Submit again. Once the ATS/server returns a response, or the result is ambiguous, do not repeat Submit except under the anti-abuse policy below.
10. If CAPTCHA/MFA appears, or an anti-abuse rejection remains after an explicitly authorized native-browser attempt, stop and report the blocker. Do not evade.

## Controlled React fields and radio groups

Use this recovery ladder when a semantic ref exists but the intended value does not persist:

1. Retry from a fresh `semantic_v2` snapshot, choosing `insert_text` or `keystrokes` as appropriate.
2. Inspect the exact window with `get_window_state`; a current AT-SPI `element_token` can provide a second grounded route for the same control. Re-snapshot afterward rather than trusting action dispatch.
3. If both semantic and AT-SPI routes refuse or fail to persist a controlled field, use the exact-bound visible UI: scroll the element into view, focus it with a native click, and type with native keyboard input. CDP/Playwright may inspect state read-only for diagnosis but must not fill, check, click, evaluate, or submit on the ATS form. If native visible input still cannot persist the value, stop as a tooling blocker rather than synthesizing framework state.

For React radio groups, hidden-input `checked:true` and AT-SPI `selected:true` may still fail to prove that the framework's form state accepted the value. Prefer a real transition through the visible label. If the intended hidden radio is already checked but the form reports it missing, select another option in the same group and then click the approved visible label; verify the intended radio is checked and that the correction banner clears. The ATS's client-validation result is authoritative: fix a reported missing field before treating the form as ready.

## Anti-abuse retry policy

A `possible spam` response blocks blind retries and API/Playwright replay. It does not force a permanent manual handoff when the user explicitly requests Hermes-native autonomous navigation. With fresh explicit authorization, one guarded retry may use the official exact-bound native browser route above, on the normal network and without evasion. If that attempt is rejected or ambiguous, stop; do not click Submit again without new authorization.

## Verification language

Report only observed facts:

- "typed" means the action dispatched;
- a fresh snapshot value proves persistence;
- a selected/checked state proves the DOM choice, but a controlled required group also needs framework acceptance (no missing-field validation after Submit);
- a displayed CV filename proves attachment;
- ATS confirmation or confirmation email proves submission.

Do not compress these into "form complete" until every required postcondition is observed.

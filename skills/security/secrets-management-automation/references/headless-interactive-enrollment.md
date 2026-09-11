# Interactive secret enrollment on headless hosts

Use this pattern when an automation runs on a VPS/headless host but initial login requires a human password, MFA, recovery key, mailbox password, or one-time enrollment token.

## Goal

Let the user cross the authentication boundary directly over their own SSH session while the agent prepares and verifies everything around it without seeing secret values.

## Safe workflow

1. **Prepare before authentication.** Install the trusted client, create private directories, identify the exact interactive command, and test non-secret prerequisites first.
2. **Verify the real prompt and exact launcher syntax.** Start the client without credentials and confirm that it reaches its actual command prompt. Some packaged GUI launchers delegate to a CLI/backend and may display a banner while merely echoing stdin. Do not assume a documented short flag is equivalent to a long flag: package launchers can overload options such as `-c` while the backend expects `--cli`. Confirm the installed launcher’s exact invocation from local help, a known-good prior run, or a credential-free test. Do not ask the user to type secrets until input processing is proven.
3. **Start the multiplexer server-side before handing it to the user.** Create a private named `tmux`/`screen` session in detached mode, verify that the session remains alive, and—before authentication begins—capture the pane once to confirm the real prompt. Then give the user a simple SSH attach command such as `ssh -t HOST "tmux attach-session -t SESSION"`. This avoids making the user repeatedly execute an unverified nested launcher command. Do not assume the setup session survives reboot; configure a deliberate service separately after enrollment.
4. **Handle terminal compatibility without broad changes.** If the remote host lacks the user's local terminfo entry, attach with a compatible value such as `TERM=xterm-256color`. Installing terminfo is optional, not required for a one-time enrollment.
5. **User enters secrets directly.** The user attaches, enters password/MFA/token in the application, then detaches. Never relay values through chat or agent-controlled stdin.
6. **Do not observe the authentication pane.** Once credential entry can begin, do not call pane capture, screenshot, console logging, process polling that includes stdout, or transcript tools. Multiplexer scrollback is a secret sink even when password input itself is hidden: usernames, one-time codes, generated credentials, and recovery prompts may be echoed.
7. **Clear local scrollback after enrollment.** Clear the multiplexer history and redraw the pane without dumping it. Do not claim this removes copies already written to an external session/tool log.
8. **Transfer generated app credentials locally.** If the enrolled client produces a revocable app/bridge password, the user copies it locally into a silent prompt (`read -s`) that stores it in Secret Service, `pass`, a service credential store, or another command-backed secret provider. Never put it in TOML, shell history, command arguments, project files, or chat.
9. **Verify metadata and behavior only.** Confirm that the account is connected, local ports/services are bound as expected, the secret lookup returns a non-empty value, and one minimal authenticated operation succeeds. Never print the credential.

## Secret Service handoff pattern

First test Secret Service with a disposable value and remove it. Then let the user store the real generated credential without echo:

```bash
printf 'disposable' | secret-tool store --label='Disposable test' service test-id
value="$(secret-tool lookup service test-id)"
test "$value" = disposable
unset value
secret-tool clear service test-id

read -r -s APP_PASSWORD
printf '\n'
printf '%s' "$APP_PASSWORD" | secret-tool store \
  --label='Automation app credential' application example account primary
unset APP_PASSWORD
```

The consuming client should use a password command such as:

```text
secret-tool lookup application example account primary
```

Do not place the lookup inside debug/trace logging that could print command output.

## Multiplexer discipline

- Before authentication: agent may inspect the pane only to verify the real prompt.
- During and after credential entry: no `capture-pane`, screenshots, transcript export, or automated keystroke injection.
- Check attachment state using metadata (`session_attached`, process name), not pane contents.
- If troubleshooting requires output, ask the user to provide only the exact non-secret error line with explicit instructions to omit account names, tokens, MFA, recovery data, and generated passwords.
- If a user reports that an SSH + `tmux new-session ... CLIENT` command immediately prints `[exited]`, first check whether the tmux session exists and whether the client created a fresh log. No session and no fresh client log usually means the launcher exited before the backend started—revalidate the exact CLI flag instead of asking the user to retry the same command.
- Restarting a broken wrapper is safe only after terminating the exact setup process and confirming no duplicate backend remains; preserve enrolled account data unless the user explicitly requests reset.

## Verification checklist

- The human typed secrets only in their SSH-attached client
- The real CLI prompt was proven before credential entry
- No pane capture or logging occurred after authentication began
- Multiplexer scrollback was cleared after enrollment
- Generated app credential went directly into a protected secret store
- Configuration contains only a secret lookup command, not a raw value
- Listener/service exposure is scoped (loopback where applicable)
- One minimal authenticated operation succeeded without printing sensitive content
- Persistence and restart behavior are tested separately

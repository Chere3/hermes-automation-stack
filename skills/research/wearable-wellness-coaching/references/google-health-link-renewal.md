# Google Health short-lived authorization-link renewal

Use this when the user says the Google Health consent link expired and asks for another one.

## Identify the target before acting

Do not confuse Google Health/Fitbit OAuth with Google Calendar OAuth or a Calendar event link. If the preceding context does not identify the product, ask one short disambiguation question. Once the user says Google Health, use the connector's own reauthorization flow.

## Proven local flow

Project: `~/proyectos/google-health-kpis`

1. Confirm the callback receiver is running without printing credentials:

   ```bash
   systemctl --user is-active google-health-oauth-callback.service
   ```

2. Generate a new pending OAuth state and URL:

   ```bash
   python ~/proyectos/google-health-kpis/google_health_reauth.py prepare --force
   ```

   `--force` is required when replacing an expired link before the normal renewal-due check. Creating a new pending state makes the previous URL unusable.

3. Send the newly printed URL exactly as generated. In the same WhatsApp message say:
   - it is for Google Health;
   - it must be opened from a device connected to Tailscale;
   - it is valid for 15 minutes.

   Keep the URL on its own plain-text line so WhatsApp does not damage it. Never save the URL in durable notes or quote it later: its `state` value is short-lived.

4. After the browser callback, verify success before saying the connector is renewed:
   - callback returned the connector's success page;
   - the durable success marker advanced and no failure marker was written;
   - refresh-token exchange succeeds;
   - a minimal read-only sync succeeds and the normalized database freshness advances.

## Safety and scope discipline

- Do not print access tokens, refresh tokens, authorization codes, full callback URLs, OAuth response bodies, or health payloads in diagnostics.
- Regenerating a URL is not evidence that authorization completed.
- Preserve the connector's implemented scope set during a straight renewal. Scope reduction or expansion is a separate change that requires implementation review and post-change category verification.
- If the callback service is inactive, restore that prerequisite before generating the link; otherwise the user can authorize successfully at Google but land on a dead callback.

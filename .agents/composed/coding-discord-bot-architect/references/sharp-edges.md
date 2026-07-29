# Sharp Edges

Operational gotchas, ordered by severity. Read when debugging or preparing a bot for production.

## Critical

- [edge-interaction-timeout](edge-interaction-timeout.md) - The 3-second acknowledgment rule and how deferring buys 15 minutes.
- [edge-privileged-intents](edge-privileged-intents.md) - Members, presences, and message-content intents need portal enablement plus a code request.
- [edge-token-exposed](edge-token-exposed.md) - Bot tokens grant full control. Keep them in env vars and rotate on leak.

## High

- [edge-command-registration](edge-command-registration.md) - Command registration is rate limited. Deploy from a script, not on startup.
- [edge-commands-scope](edge-commands-scope.md) - Slash commands need the applications.commands OAuth scope, not just bot.

## Medium

- [edge-global-propagation](edge-global-propagation.md) - Global commands take up to an hour to propagate. Use guild commands for testing.
- [edge-gateway-disconnections](edge-gateway-disconnections.md) - Blocking the event loop drops heartbeats. Stay async and handle reconnects.
- [edge-modal-first-response](edge-modal-first-response.md) - A modal must be the first response to an interaction. Never defer first.

## Validation and collaboration

- [validation-collaboration](validation-collaboration.md) - Linter-style checks, delegation triggers, when-to-use, and limitations.

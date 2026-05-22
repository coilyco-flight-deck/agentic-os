---
name: tooling-openclaw-workspace
description: OpenClaw workspace mechanics - startup (use runtime-provided context first, don't manually reread AGENTS.md/SOUL.md/USER.md), proactivity rules (heartbeat for batched/loose-timing, cron for exact timing, stay quiet when nothing changed), related-file map (USER.md / SOUL.md / TOOLS.md / HEARTBEAT.md). Triggers - openclaw, heartbeat, HEARTBEAT.md, SOUL.md, BOOTSTRAP.md, TOOLS.md, openclaw startup, openclaw proactivity, openclaw workspace, openclaw memory.
---

# OpenClaw workspace

## Startup

Use runtime-provided startup context first. It may already include `AGENTS.md`, `SOUL.md`, and `USER.md`.

Do not manually reread startup files unless:

- The user explicitly asks.
- The provided context is missing something needed.
- A deeper follow-up read is required for the task.

`BOOTSTRAP.md` is starter scaffolding. If it still exists, read it only for OpenClaw mechanics, then prefer the durable rules in `AGENTS.md`.

## Proactivity

Heartbeats can be useful, but keep them bounded and public-safe in this workspace.

- **Use heartbeat for** - Batched checks, conversational context, loose timing, and background maintenance.
- **Use cron for** - Exact timing, isolated execution, one-shot reminders, or different model/effort settings.
- **Stay quiet when** - Nothing changed, the timing is poor, or a check happened recently.
- **Prefer useful work** - Update docs, inspect project state, or improve entrypoints when it matches the user's priorities.

Do not store private personal logs in `<personal-os-repo>/openclaw/memory/`.

## Related files

- `USER.md` - public-safe profile for the user.
- `SOUL.md` - OpenClaw-specific tone and agent identity.
- `TOOLS.md` - OpenClaw tool notes and local command entrypoints.
- `HEARTBEAT.md` - small heartbeat checklist if OpenClaw uses one.

# Frontmatter aliases

Lead with the canonical name plus 2-3 natural-language phrasings a user might reach for. **500-byte hard ceiling on the whole `description:` field.** If a skill needs more trigger surface than that, the fix is a better name, a router parent (see `coily-meta`, `ops-social-gws-gmail`, `kai-execution-mode` for the pattern), or splitting the skill. Not a longer description.

**Router-parent carve-out:** a router skill claiming a broad domain keyword surface (so child skills can stay terse) may exceed 500 bytes when the extra surface is doing real routing work, not alias-packing. The router shape has to be load-bearing - "router with two children" does not qualify. The Gmail and Google Calendar parents both do, today.

**Why:** the `description` field is eager-loaded into every Claude turn forever. Aliases are paid only per invocation. At ~100 skills, the eager surface already crowds the catalog, and the system-reminder skill catalog truncates past ~80 entries, so selection accuracy degrades from sheer surface size before token cost even enters the picture. Alias-packing is the most expensive possible layer to solve discoverability at. Filed as [agentic-os-kai#583](https://github.com/coilysiren/agentic-os-kai/issues/583); the cap dropped from 600 to 500 after the post-#583 sweep (only 3 outliers remained over 500, all trimmable).

**How to apply:** when authoring a new skill, write `description:` as one sentence of purpose plus 2-3 phrasings. When tempted to add a fourth alias, rename the skill or hoist a router parent instead. LUCA-driven cold-skill pruning (future audit chain) will validate whether existing aliases earn their bytes.

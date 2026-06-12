# Auto-reach: the Luca stack (staging by default)

Three servers are **implicitly** in-scope and the agent should reach for them whenever they are even vaguely relevant, without asking permission:

* **repo-recall-staging** - cross-session corpus of repos, sessions, commits. Tools include `recall_search` (free-text across all three), `recall_dashboard`, `recall_session`, `recall_ticket_history`. Use when Kai says "when did I talk about X", "did that land", "find the session where", "what does repo-recall know", "ask luca", or any past-work-recall shape.
* **luca-staging** - natural-language consumer over repo-recall data. Use for cross-run synthesis and "what are the agents doing"-shaped questions.
* **session-lattice-staging** - per-session detail and lattice navigation. Use when the question is about a specific session, agent run, or session-to-session links.

When the agent uses any of these, it **tells Kai which one and which tool**, so she can document.

Kai will say "prod" explicitly when she wants the prod variants (`repo-recall`, `luca`, `session-lattice`). Default is staging.

Every other MCP (playwright, terraform, sentry, honeycomb, phoenix, gcal, gmail, eco, elevenlabs, shortcut, amplitude) stays explicit: Kai names it by CLI name before the agent reaches for it. The lazy-CLI design holds for those.

`honeycomb` is the Honeycomb Intelligence MCP server at `https://mcp.honeycomb.io/mcp` (OAuth, streamable HTTP). Available on Free / Pro / Enterprise via Honeycomb Intelligence. The Enterprise gate is on the REST `/1/query_results` endpoint, not on MCP. First-time auth: `mcporter auth honeycomb`.

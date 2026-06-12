# Playwright invocation

The Playwright MCP server is already wired through mcporter (`config/mcporter.json` → `playwright`). Resolve at call time via `mcp__playwright__*` tools.

Flow per query run:

1. Fetch cookie from SSM:
   ```
   ward ops aws ssm get-parameter --name /coilysiren/honeycomb/session-cookie --with-decryption --query Parameter.Value --output text
   ```
2. Open a Playwright browser context. Parse the cookie header into Playwright's array form: split on `; `, then split each pair on the first `=`. Domain `.honeycomb.io`, path `/`, `secure: true`. Inject all cookies before the first navigation.
3. Navigate to the dataset query builder. URL shape:
   ```
   https://ui.honeycomb.io/<team-slug>/environments/<env-slug>/datasets/<dataset-slug>?query=<urlencoded-json>
   ```
   For the battleships workshop: `team-slug=coilysiren`, `env-slug=o11y-con-2026`, `dataset-slug=battleships`. Honeycomb will redirect to `/<dataset>/result/<view-id>` after the server-side query stamp; the `result/` segment is **not** a path you supply yourself, supplying it returns 404.
4. The `query` URL param accepts a JSON query spec directly - same shape as the Query Data API would have taken (calculations, breakdowns, filters, time_range). No need to click into the Query Builder form.
5. Wait for the result panel to render. Scrape:
   - **Table-shaped results** (group-by queries): DOM `table` under the results panel. Headers in `<thead>`, rows in `<tbody>`.
   - **Heatmap or visualization-only**: take a screenshot, pass the image to the LLM for read-out.
6. If the page redirects to `/login`, the cookie expired. Prompt for a fresh handoff.

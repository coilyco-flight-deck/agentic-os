---
name: tooling-honeycomb-ui
description: Cookie-driven Playwright fallback for reading Honeycomb data when the official Honeycomb MCP server can't answer. Triggers - honeycomb ui scrape, honeycomb playwright, MCP fallback.
---

# tooling-honeycomb-ui

**Primary path is the Honeycomb MCP server**, not this skill. `https://mcp.honeycomb.io/mcp` is wired through mcporter as `honeycomb` (OAuth, streamable HTTP). Honeycomb Intelligence is on all plans (Free / Pro / Enterprise), so MCP works on Kai's Free account. Use `mcp__honeycomb__*` tools first.

The earlier framing that "the REST Query Data API requires Enterprise so the only programmatic path is driving the UI" conflated two separate surfaces. The `/1/query_results` REST endpoint is still Enterprise-gated, but MCP is a separate Intelligence-backed surface that doesn't go through that endpoint. Correction tracked in agentic-os-kai (see "See also").

This skill stays as the **cookie-driven Playwright fallback**: use it only when MCP can't answer a specific question that the UI can (heatmap visualization scrapes, DOM-shaped data the MCP doesn't expose, etc.).

## Why cookie-handoff, not SSO-in-Playwright

Kai's Honeycomb login is Google SSO to `coilysiren@gmail.com`. Logging in from a fresh Playwright Chrome means Claude touches that Google session. Copying a Honeycomb cookie out of an already-authenticated browser hands over a Honeycomb-scoped session only, with no path back to Google. Stronger security story for the same automation surface.

## One-time auth handoff

When the skill fires with no usable cookie in SSM (first run, or expired), walk Kai through these steps and pause until done.

Honeycomb's login flow embeds Google SSO, so a logged-in reload of `ui.honeycomb.io` shows requests to **both** `ui.honeycomb.io` **and** `accounts.google.com` in the Network panel. Copying the Cookie header from the wrong row produces a silent failure: the cookie stashes, `build-honeycomb-storage` writes the file, Playwright loads, and navigation just redirects to `/login`. Filter discipline is load-bearing.

1. Open `https://ui.honeycomb.io/` in her main browser (already logged in).
2. **DevTools → Network tab → type `ui.honeycomb.io` into the filter box → reload the page → click any request in the filtered list.** The filter is the step that prevents the wrong-row copy.
3. Under **Request Headers**, find the `Cookie:` line. Copy the entire value (everything after `Cookie: `, no leading space, no trailing newline). Verify the copied string contains the substring `hny=`, that is Honeycomb's session cookie. If it doesn't, you're looking at a Google-SSO row. Go back to step 2 and re-filter.
4. Drop the value into a temp file (avoids long-secret-in-argv hazards) and stash:
   ```
   coily ops aws ssm put-parameter --overwrite --name /coilysiren/honeycomb/session-cookie --type SecureString --value file:///tmp/honeycomb-cookie.txt
   shred -u /tmp/honeycomb-cookie.txt
   ```
5. Rebuild the Playwright storage-state file from the new SSM value:
   ```
   coily exec build-honeycomb-storage
   ```
   (Once [agentic-os-kai#652](https://github.com/coilysiren/agentic-os-kai/issues/652) lands, this command will refuse to write the file if the cookie value lacks `hny=`, so a malformed handoff fails fast at build time rather than at navigation time.)
6. Cookie has a finite lifetime (typically hours to days). When the skill detects a redirect to `/login`, prompt for a fresh copy.

## Playwright invocation

The Playwright MCP server is already wired through mcporter (`config/mcporter.json` → `playwright`). Resolve at call time via `mcp__playwright__*` tools.

Flow per query run:

1. Fetch cookie from SSM:
   ```
   coily ops aws ssm get-parameter --name /coilysiren/honeycomb/session-cookie --with-decryption --query Parameter.Value --output text
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

## Trace-view URL surface

Parallel to the `?query=<json>` knob on the dataset query builder, the trace view has its own URL surface that is more useful for the human-readability iteration loop this skill exists to support. Three knobs:

1. **Base shape**:
   ```
   https://ui.honeycomb.io/<team>/environments/<env>/datasets/<dataset>/trace?trace_id=<hex>
   ```
   The `/trace/<view-id>/` segment Honeycomb stamps into the URL after interaction is a server-side view-state token. Drop it from shareable URLs, it isn't needed and changes per session.

2. **`fields[]=<col>&fields[]=<col>...`** replaces the default `Name / Service Name` columns in the waterfall table with arbitrary span attribute columns. Honeycomb auto-prefixes `c_` server-side, so `fields[]=shot.result` becomes `c_shot.result` in the canonical URL. Either form works on input.

   Sharp edge: a single `fields[]` set applies to every row, so on heterogeneous-span traces, picking columns for the common span type blanks out the cells for outlier span types. The right-pane Fields panel adapts per focused span and is the escape hatch. Pick the columns that read best for the common case, accept that outliers will look empty in the table, and let the reader click the outlier to see its actual fields in the right pane.

3. **`span=<hex>`** pre-focuses a specific span. The right-pane Fields panel renders that span's attributes immediately, which is how you make a deep-link land on "the thing that matters" instead of "the first span in the trace."

Worked example, battleships, pre-focusing the dominant TIMED_OUT engagement with shot-shaped columns:

```
.../datasets/battleships/trace?trace_id=<hex>&fields[]=shot.result&fields[]=shot.row&fields[]=shot.col&span=<engagement-span-id>
```

Shot rows render as `MISS | 1 | 9 | 1.092s` (highly scannable). The focused row is empty in the table because engagement spans don't carry `shot.*`. The right pane fills in with `engagement.outcome=TIMED_OUT` etc. because focus adapts per span.

Repo-side recipe with workshop worked examples lives at `coilysiren/honeycomb-battleships/docs/sharing-traces.md` (see honeycomb-battleships#29).

## Battleships dataset reference

The four canonical queries from `coilysiren/honeycomb-battleships/docs/reading-honeycomb.md`:

```yaml
misses:
  calculations: [{op: COUNT}]
  breakdowns: [shot.row, shot.col]
  filters:
    - {column: name, op: '=', value: fire}
    - {column: shot.result, op: '=', value: MISS}
  orders: [{op: COUNT, order: descending}]

breakdown:
  calculations: [{op: COUNT}]
  breakdowns: [shot.result]
  filters: [{column: name, op: '=', value: fire}]

score-trend:
  calculations: [{op: AVG, column: game.score}]
  breakdowns: [game.number]
  filters: [{column: name, op: '=', value: game}]
  orders: [{column: game.number, order: ascending}]

opponents:
  calculations: [{op: AVG, column: game.score}]
  breakdowns: [game.opponent]
  filters: [{column: game.opponent, op: exists}]
  orders: [{op: AVG, column: game.score, order: ascending}]
```

Origin and full prose interpretation lives in `honeycomb-battleships/docs/reading-honeycomb.md` (the handoff doc - read it before driving the UI for that dataset).

## Boundaries

- **Cookie scope**: the session cookie is Honeycomb-scoped. It cannot reach Google, cannot mint Google tokens, cannot read mail. If the cookie leaks, rotate by signing out of Honeycomb on Kai's main browser (which invalidates server-side) and re-stashing.
- **Do not** keep a Playwright context alive across turns. Each query run opens fresh, loads cookies, runs, closes.
- **Do not** log full cookie values to chat or to scrape files. Print the rendered table or screenshot only.
- The skill is read-only against Honeycomb. Do not click Save Query / Save to Board / Trigger create buttons without explicit ask.

## See also

- `coilysiren/honeycomb-battleships/docs/reading-honeycomb.md` - workshop dataset shape and query semantics.
- `coilysiren/honeycomb-battleships/scripts/query.py` - REST Query Data API attempt, still Enterprise-gated. The MCP path supersedes this for most reads.
- `tooling-mcp-servers` → `honeycomb` entry - primary path. Run `mcporter auth honeycomb` once to mint the OAuth session.
- `tooling-claude-in-chrome` - sibling skill for the live-Chrome MCP. Use this skill instead of that one when a one-shot scrape is enough and a fresh logged-in headless context is cleaner.
- `tooling-mcp-servers` - lazy MCP resolution via mcporter; the `playwright` server is registered there.

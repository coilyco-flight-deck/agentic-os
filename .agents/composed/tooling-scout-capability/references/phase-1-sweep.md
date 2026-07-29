# Phase 1 - Grounded sweep + speculative ideation

Walk the user's working surface and build a verbose candidate list. Two
sub-passes, in order, kept separate so speculation does not drown out
real signal.

**Grounded pass.** For each repo in the AGENTS repo registry, read:

- `README.md` (top-level)
- `AGENTS.md` if present
- Recent commit subjects (`git log --oneline -50`)
- Open issues (`gh issue list -R <owner>/<repo> --state open --limit 30`)

Plus any user-supplied notes, ideas, or task files that are in scope. Do not
deep-read code.

For each grounded item, write a one-line candidate: `- {kind}: {bare
name} - because: {one-sentence rationale tied to a specific repo or
note}`. Kind is `skill` or `mcp`.

**Speculative pass.** After the grounded pass, brainstorm 10-30
additional entries that **don't currently exist**. The point is to
surface things the user might want to ask people about (eg. "no Reddit MCP
exists, would be cool, the user doesn't know anyone there" vs "no Discord
MCP for X workflow, the user knows someone there"). Mark these
`speculative: true` and include a **required** `nudge:` field naming
who or where to ask. Valid values include a specific contact ("friend
at Discord"), a project owner ("Anthropic official"), a build path
("self-build"), or `no known leverage` for entries the user might want but
has no contact for. An entry without a nudge value is half a thought.
The speculative pass exists primarily to surface "who could I ask about
this" candidates, so the leverage question must be answered up front.

Output: `YYYY-MM-DD-capability-scout-1-candidates.md` (markdown) plus
`YYYY-MM-DD-capability-scout-1-candidates.yaml` (machine-readable for
phase 2 consumption). Bare names only at this stage. No Org / Url /
Description yet.

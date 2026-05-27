---
name: tooling-capability-scout
description: Capability gap analysis for skills and MCP servers. Sweeps repos, hydrates against skillsmp and glama, security-audits silver/gold tiers, installs one-issue-one-commit.
---

# capability-scout

## Triggers

capability scout, find me skills, find me mcps, gap analysis, missing capabilities.

Six-phase routine. Each phase runs independently and checkpoints to a
single-day vault inbox file, so the user can dictate "capability-scout phase 3"
from the train and resume without re-running phase 1.

**Why six phases:** the full pipeline is too large for one model run, and
each phase has a different cost/risk profile. Phase 1 is open-ended
ideation, phase 4 is a security gate, phase 6 mutates the user's personal-OS repo. Mixing
them into one invocation either blows context or makes the security gate
easier to skip. Splitting forces an explicit checkpoint between
"speculate" and "install."

**Outputs go to the notes/scratch location, not the personal-OS repo.** Speculative discovery
incidentally surfaces private repo intent and personal context. Only the
final per-install commits land in the personal-OS repo. Inbox path:
`<notes-dir>/YYYY-MM-DD-capability-scout-{phase}.md` (parameterize to the user's scratch/notes location).

## Phase 1 - Grounded sweep + speculative ideation

Walk the user's working surface and build a verbose candidate list. Two
sub-passes, in order, kept separate so speculation does not drown out
real signal.

**Grounded pass.** For each repo in the AGENTS repo registry, read:

- `README.md` (top-level)
- `AGENTS.md` if present
- Recent commit subjects (`git log --oneline -50`)
- Open issues (`gh issue list -R <owner>/<repo> --state open --limit 30`)

Plus the vault: the user's notes index, the most
recent 14 days of inbox content, and any ideas/tasks files
specifically. Do not deep-read code.

For each grounded item, write a one-line candidate: `- {kind}: {bare
name} - because: {one-sentence rationale tied to a specific repo or
note}`. Kind is `skill` or `mcp`.

**Speculative pass.** After the grounded pass, brainstorm 10-30
additional entries that *don't currently exist*. The point is to
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

## Phase 2 - Hydration

For each candidate from phase 1, fetch:

- Skills: `<skillsmp-search> <name>` and `coily pkg skillsmp
  ai-search <name>`. Take the top result if it's a strong match; record
  multiple if ambiguous.
- MCPs: `<glama-list-servers>` (paginate) and
  `<glama-list-servers>-by-namespace-by-slug` for
  exact matches.
- **Backstop:** also `WebFetch` 2-3 well-known awesome-lists
  (travisvn/awesome-claude-skills, ComposioHQ/awesome-claude-skills,
  claudefa.st's MCP list) as a sanity check that no obvious entry was
  missed by the registries. This is a cheap regression net, not the
  primary source.

Hydrate each into: `Org / Name / Url / Description (1 sentence)`. Keep
the original bare name in a `bare_name` field for traceability.

**Do not filter Codex/Claude/OpenClaw-only entries.** the user uses all three.

If hydration fails (no match anywhere), keep the entry with
`hydration: not_found`. Speculative entries from phase 1 stay
unhydrated by definition - record them as `hydration: speculative` with
the nudge intact.

**Dedup against existing installs.** Before emitting the hydrated file,
read `<personal-os-repo>/config/mcporter.json` (existing MCP entries) and
`ls <personal-os-repo>/.agents/skills/` (existing skills). For each candidate,
fuzzy-match against installed names and aliases. If a probable
duplicate is found, mark the entry `dedup: existing` and include the
matched name in a `matches:` field. Dedup'd entries skip phase 4 audit
and phase 5 presentation but stay in the file for visibility (eg.
"sentry-mcp surfaced but you already have it").

Output: `YYYY-MM-DD-capability-scout-2-hydrated.yaml`.

## Phase 3 - Categorize and rank

Categorize entries semantically (eg. game-server-ops, gmail, calendar,
gaming, observability, dev-tools, social, finance, ai-infrastructure,
speculative-asks, etc.). Then rank globally - not within categories -
at 3:2:1 ratio: 🥉 50%, 🥈 33%, 🥇 17%. A sparse category may end up
entirely 🥉; that's expected and intentional.

Ranking criteria, in priority order:

1. Direct fit to current repo work or open issues across the user's repo set.
2. Reduces a manual workflow the user is currently doing by hand.
3. Reusable across multiple projects.
4. Speculative entries the user has personal leverage on (someone they know)
   rank higher than ones they don't.

Prepend the medal emoji to each entry. Output:
`YYYY-MM-DD-capability-scout-3-ranked.yaml`. Group by category, but
keep the global rank labels intact.

## Phase 4 - Security audit (🥈 and 🥇 only)

**BLOCKED ON #185.** The audit rubric below is provisional. Phase 4 has
been red-flagging third-party MCPs that overlap a coily wrapper (Cloudflare,
GitHub, k8s, Tailscale, AWS, Discord-admin) on coily-bypass grounds, but
mcporter is the actual execution path and may itself be the audit choke
point. Once mcporter execution is verified (#185), revise this rubric:
🔴 should narrow to real supply-chain audit failures (malicious code,
abandoned projects, anonymous maintainers writing privileged tools),
not "duplicates a coily wrapper." Until then, treat the coily-overlap
red flag with skepticism and surface the call to the user instead of
auto-rejecting.

For every 🥈 and 🥇 entry, run the `supply-chain-audit` skill. 🥉
entries are skipped (we will not install them, no need to spend the
audit budget).

Map results to a `🟢🟡🔴` prefix:

- 🔴 - audit failed (suspicious maintainer, malicious code patterns,
  abandoned/unmaintained, dependency-confusion-style risk, or zero
  downstream adoption with high-privilege scope). 🔴 entries are never
  installed regardless of any later approval.
- 🟡 - audit passed but the domain is theoretically dangerous (banking,
  payments, cloud-write, secrets handling, code execution, browser
  automation against authenticated sessions). Cautious-by-domain even
  when the implementation is clean.
- 🟢 - audit passed and the domain is benign (read-only catalog, public
  APIs, narrow-scope data fetchers, documentation tooling, file format
  conversion).

Speculative entries (no code to audit) get 🟡 by default since "I'd ask
someone about it" is not "I'd install it tomorrow."

Output: `YYYY-MM-DD-capability-scout-4-audited.yaml`. Preserve the
medal emoji; prepend the safety emoji. Final per-entry prefix shape:
`{category-emoji}{medal}{safety} ` followed by `Category / Org / Name /
Url / Description`.

## Phase 5 - Present 🥇🟢 inline

Flatten the 🥇🟢 entries (only that combination) into a single chat
list. Drop category nesting; prepend a per-entry category emoji
instead. Expand each Description from 1 sentence to 2-4 sentences.

Final shape per line:

```
🎮🥇🟢 game-server-ops / Org / Name / Url / Description (2-4 sentences)
```

Approval model is **explicit-deny**. After presenting, wait for the user to
name entries to drop. Anything they don't deny is approved by default.
A null/empty response means approve all.

Do not present 🥈, 🥉, 🟡, 🔴, or speculative entries here. They live
in the phase 4 file for the user to review at their own pace.

## Phase 6 - Install approved entries

Detail in [`references/install-and-notes.md`](references/install-and-notes.md): per-entry issue + commit + push shape, fast-forward of marketplace clones, the Notes section.

---
name: kai-tech-prefs
description: Kai's technical preferences - Go CLI defaults (urfave/cli), Charm TUI stack, dead-repo check, doc conventions, default license. Triggers - cli, tui, library, dependency, recommend tool.
---

# Technical preferences

## Stack

Python, AWS, Kubernetes, Terraform. Distributed systems, platform engineering, o11y-heavy. LLM APIs and production-grade AI systems.

## Go CLI

Kai is/was a maintainer of [urfave/cli](https://github.com/urfave/cli). **Default to urfave/cli over cobra/kong.** When in doubt about Go CLI tooling, check what urfave/cli does first.

## Charm (preferred TUI/CLI styling family)

[Charm](https://charm.land/) ([github.com/charmbracelet](https://github.com/charmbracelet)) is Kai's preferred TUI/CLI-styling family. Reach for:

- bubbletea (TUI framework)
- gum (shell-script prompts/styling)
- glow (markdown render)
- lipgloss (styling)
- huh (forms)
- vhs (terminal recording)
- soft-serve (self-hosted git)
- wish (SSH apps)
- mods (LLM CLI)
- freeze, melt

When a coily/repo-recall/eco tool needs interactive prompts, fancy output, or a TUI, bias toward this stack over hand-rolled ANSI or rivals like tview/promptui. Cotton-candy aesthetic, MIT-licensed, very actively maintained, plays nicely with urfave/cli for the imperative-CLI-with-occasional-TUI shape.

## Don't suggest dead or dormant repos

Before recommending an OSS project, library, tool, brew formula, plugin, or dependency, **verify it has had commits in the last 12 months**. Quick check:

```bash
curl -sL "https://api.github.com/repos/<owner>/<name>/commits?per_page=1" | grep '"date"'
```

No recent commits → don't surface it, or surface it explicitly framed as "this is dormant, here's why I'm flagging it anyway."

Applies to upstream libraries, dev tools, alternatives lists ("modern X replacements"), CLI helpers, browser extensions, anything actively recommended.

**Reason:** Kai has had Claude pitch her dead projects often enough to formalize the rule. The 12-month window is the bright line; project archived/maintenance-mode notices in the README count as dead regardless of last commit date.

## Don't shorten common command names

No `k=kubectl`, `gst=git status`, `kgp=kubectl get pods`, etc. Kai dislikes shortened-name aliases on principle: they make examples, screen recordings, and shared snippets inaccurate, and they break the "wrapper API mirrors the real CLI" instinct that drives coily's design.

- Multi-word convenience functions (e.g. `git-merge-default-branch`) are fine.
- Aliases that *flag* a command (`alias ls='ls -GFh'`) are fine.
- Aliases that *rename* it are not. Don't suggest them, don't add them to dotfiles, don't propose them in code review.

## No pagers

Pagers are a hard-no. `less`, `more`, `bat`'s default pager, `git`'s pager, anything that traps output behind a modal scroll surface gets configured off. The block-mode terminal already gives clean scrollback per command, so paging adds friction without adding value.

**Why:** every paged output requires `q` to exit, which interrupts the flow of dictation-friendly terminal work and breaks Warp's block model. Surfaced as a hard preference during the Warp walkthrough (coilysiren/agentic-os#56) and the bat-workflow recon (coilysiren/agentic-os#57).

**How to apply:**
- Any tool with a default pager gets configured off when wrapping or aliasing. `--no-pager` for git, `--paging=never` for bat, `PAGER=cat` for general escape, etc.
- When proposing CLI ergonomics, default to non-paged dumps. Don't pipe through `less` by default.
- If output is genuinely too long for the terminal, suggest piping through a pager explicitly rather than enabling one by default. The block model handles long blocks fine.

## Docs

No "Repo layout" / "Project structure" sections in README. Filesystem is self-documenting. If a dir layout needs *explanation* (non-obvious separation, unusual build output), brief prose under a purpose-focused heading, not an ASCII tree.

## Licensing

Three tiers by repo intent - MIT for shareable, AGPL-3.0 for deployment-of-one, proprietary All-Rights-Reserved for private personal repos. Default to **MIT** when intent is unclear. Full policy: [`coding-licenses`](../coding-licenses/SKILL.md).

## JSON-twin discoverability for dashboards

Whenever a dashboard you build has a JSON variant (whether via `Accept: application/json` content negotiation, a `?format=json` param, or a separate route), surface three discovery mechanisms so a cold-start LLM agent can find it without probing:

1. `<link rel="alternate" type="application/json" href="..." title="...">` in the HTML head.
2. `Vary: Accept` and a `Link: ...; rel="alternate"; type="application/json", ...; rel="service-desc"; type="application/json"` response header on every route.
3. A `GET /openapi.json` returning OpenAPI 3.1.

Reference implementation: [repo-recall@4e4c3ba](https://github.com/coilysiren/repo-recall/commit/4e4c3ba).

**Why:** agents land on `/` and have no way to infer JSON exists; guessing `Accept: application/json` works but is a probe, not an inference.

**How to apply:** every new internal dashboard with a machine-readable surface gets all three. Skip only when there is no JSON twin.

## Configs go in SSM, not in skills or code

When a skill, script, or piece of code needs a config-shaped value (an account id, a voice id, a default channel, a board id, a URL, anything that might rotate or vary per host/account), stash it in AWS SSM and reference the parameter name. Do not hardcode the value into a SKILL.md body, a Python constant, a YAML default, or a checked-in JSON.

**Why:** single source of truth, rotatable without a code change, audit-trail via `coily ops aws ssm`, swap-without-edit for environment changes, no stale duplicates across files. Hardcoded values rot silently the moment the upstream changes.

**How to apply:**
- Stash with `coily ops aws ssm put-parameter --name /<vendor>/<key> --type SecureString --value <v>`. Convention: vendor-scoped path, kebab-case leaf, SecureString even for non-secrets.
- Record the entry in `SSM.md` (canonical inventory at `~/projects/coilysiren/agentic-os-kai/SSM.md`) in the same commit.
- Reference it from code via `aws ssm get-parameter` or, for shell sessions, the `ssm-load` env var (`/foo/bar-baz` → `FOO_BAR_BAZ`).
- In a SKILL.md, name the parameter and show the fetch command. Never paste the value into the body.

Applies to api keys (already obvious), but also to non-secret config: voice ids, channel ids, board ids, zone ids, agent ids, account-scoped identifiers. The bright line is "would I have to edit a file if this value changed". If yes, it goes in SSM.

## No parallelism for rate-limited batch jobs

When a batch job's primary failure mode is upstream rate limiting (`gh` secondary limits, mod.io, ElevenLabs, Bluesky, Reddit, GitHub Search), serial execution is the correct default. Don't reach for `xargs -P`, GNU parallel, or goroutines as a "go faster" lever. A parallel run that trips the rate limit midway is strictly worse than a slow run that finishes cleanly - it leaves partial state across both sides and is harder to resume. If real throughput pressure exists, fix it with batched/bulk endpoints (GraphQL multi-query, batch APIs) before reaching for concurrency.

## Coily wrapper rules

When about to run a privileged op against kai-server, AWS, or k8s, or when wrapping a new sub-CLI inside coily, read `~/projects/coilysiren/coily/AGENTS.md` for full rules.

# Features: managed AGENTS.md pointer block

Every per-repo `AGENTS.md` opens with a one-line pointer at the workspace base. Hand-written, that line drifted into three styles and several dangled: `See ../AGENTS.md` resolves to a non-existent `coilyco-bridge/AGENTS.md`, because the repos live in different org dirs with no guaranteed sibling layout. The canonical content already loads globally via `~/.claude/CLAUDE.md`, so the pointer's real job is to orient a reader **without** that load point - a foreign agent, a single-repo clone, CI. For that reader a relative path is useless and "loads globally" is false, so only an absolute URL is true.

## What it renders

`generate-agents-pointer` is the single source of truth for the pointer, rendered as a marker-delimited managed block (`<!-- BEGIN managed by ... -->` / `<!-- END ... -->`). Each org points at its own base, on the host that fits its trust tier:

- **`coilyco-flight-deck/*`** - the public base on its GitHub mirror (`coilyco-flight-deck/agentic-os/AGENTS.md`), the public face an unauthenticated reader can open.
- **`coilyco-bridge/*`** - the same public base, with the private `agentic-os-kai/AGENTS.md` overlay on canonical Forgejo layered on top. The wording carries the layering: aos-pub is the foundation, aos-kai layers Kai-specific context over it.

The canonical base repos themselves (`agentic-os`, `agentic-os-kai`) are exempt - a base does not point at itself. `coilysiren/*` stays **deliberately unmanaged**: it is Kai's public personal org outside the coilyco-* fleet, and its handful of repos are `.agentic-os-ignore`-exempt and hand-authored (the profile repo `coilysiren/coilysiren` carries a bespoke bootstrap, not a one-line pointer). Those repos are hand-maintained per-repo rather than templated, so `coilysiren/website` gets the same hand-fix the profile repo got instead of a generator branch.

## Enforcement and application

- **`agents-pointer`** (pre-commit hook) regenerates the expected block offline from the repo's org, derived from its git remotes, and fails on drift, a missing block, or a legacy intro line lingering beside it. It no-ops for unmanaged orgs, exempt base repos, a symlinked `AGENTS.md`, or a repo with no root `AGENTS.md`.
- **`apply-agents-pointer`** injects or refreshes the block in place. Idempotent: it strips any prior managed block and known legacy intro lines, then inserts the fresh block right after the first H1.

This repo ships the validator and the applier. The fleet rollout that lands the block on every managed repo's canonical `main` is `scripts/agents-pointer-migrate.py` in infrastructure (`ward exec agents-pointer-migrate`), per the authoring-vs-rollout split. (The earlier report-only Ansible `agents-pointer` role was retired when fleet pre-commit and pointer rollout moved onto the ward container.)

## See also

- [features-release-tooling.md](features-release-tooling.md) - the cross-repo pre-commit baseline this hook joins.
- [docs/features-agents-pointer.md](features-agents-pointer.md) - design and schema.

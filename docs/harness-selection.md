# Which harness when

Kai runs five agent harnesses. Picking one is two decisions, not one: the **model tier** sets the capability ceiling, the **harness** sets how you drive it. The two are orthogonal - any harness binds any model it supports.

## First: pick the model tier

The ceiling, lowest to highest:

- **Trivial local** (`models-qwen`) - small Qwen3 4B/8B quant, ~25k context, exact-string-match skill pick. Closed slot-filling only, escalate by default. This is the confined `qwen-opencode` agent.
- **Capable local** (`models-qwen-coder`) - Qwen3 30B-A3B (`qwen3-coder:30b`), 32k context, tool use, real in-repo coding on a 24GB-class GPU. Escalate only for cloud-grade judgment.
- **Cloud** ([`agents-claude`](../.agents/skills/agents-claude/SKILL.md) / [`agents-codex`](../.agents/skills/agents-codex/SKILL.md)) - large context, semantic skill pick, multi-step judgment. The escalation target the local tiers hand up to.

Rule of thumb: stay as low as the task allows. Local keeps the work on Kai's own hardware. Escalate when the task needs judgment, large context, or a privileged op the local tier cannot reach.

## Then: pick the harness

Two harnesses are fixed to a cloud model:

- **Claude** (she/her, [`agents-claude`](../.agents/skills/agents-claude/SKILL.md)) - the default capable agent. Semantic skill selection, large context, the primary escalation target.
- **Codex** (he/him, [`agents-codex`](../.agents/skills/agents-codex/SKILL.md)) - cloud GPT peer to Claude. Reach for it when you want a second cloud opinion, or are already in an OpenAI-auth flow.

Three float over a swappable model (cloud or local Ollama). On Kai's stack they run the capable local coder by default:

- **OpenCode** (they/them, [`agents-opencode`](../.agents/skills/agents-opencode/SKILL.md)) - the default interactive local-coding TUI. Reach for it for a general session when no other floater clearly fits.
- **Aider** (they/them, [`agents-aider`](../.agents/skills/agents-aider/SKILL.md)) - the scalpel. Reach for it when the edit is surgical and you can name the files: diff-by-diff, one commit per change, inside a git repo.
- **Goose** (she/her, [`agents-goose`](../.agents/skills/agents-goose/SKILL.md)) - the multi-step loop. Reach for it when the task needs tool use and broader autonomy: MCP extensions and recipes, not just edits.

## Quick decision

- Trivial slot-fill, heartbeat ack, one-line status - trivial local via `qwen-opencode`.
- Local coding, named files, reviewable commits - Aider on the capable coder.
- Local coding, exploratory or tool-driven - Goose on the capable coder.
- Local coding, just want a session - OpenCode on the capable coder.
- Needs judgment, large context, or a privileged op - escalate to Claude (or Codex).

## See also

- [features-agents-sessions.md](features-agents-sessions.md) - self-name and pronoun slug per harness.
- Model tiers: `models-qwen`, `models-qwen-coder`.

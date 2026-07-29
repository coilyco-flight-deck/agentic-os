# Handbook: Description budgets in detail

Continues the description-budget rules in [`handbook-frontmatter.md`](handbook-frontmatter.md).

**The hard cap is `categories.yaml:max_description_bytes`, not these bands.** The bands below are soft authoring targets written against the public agentic-os default of 500 bytes. A repo that tightens the validator wins: agentic-os-kai enforces 200, so there the upper bands (and the "400-500" exception) are unreachable - aim for pointer/normal-task sizing and treat 200 as the wall. Check your repo's `categories.yaml` before sizing, not these numbers from memory.

Target bands (public 500-byte default):

* **Pointer skills** - under 160 chars. Use this when the body mostly points at a canonical doc elsewhere.
* **Normal task skills** - 120-200 chars. Most coding, writing, gaming, and tool-usage skills should fit here.
* **Complex task skills** - 220-300 chars. Use this for skills with several adjacent trigger phrasings or one important boundary.
* **Router/meta skills** - 250-400 chars. A router earns extra surface only when it prevents many child skills from carrying broad aliases.
* **Rare exceptions** - 400-500 chars for public-safety, MCP routing, or cross-repo failure handling where false negatives are expensive.
* **Cleanup signal** - over 500 chars means fix the description or explicitly justify a router/meta role in `categories.yaml`.

What belongs in `description`:

* The main user intent or task shape.
* A few concrete trigger phrases Kai actually says.
* Critical disambiguators that prevent the wrong skill from opening.
* Router fan-out surface, only for true router skills.

What belongs in the body instead:

* Procedure, command sequences, examples, checklists, policy rationale, historical incidents, implementation details, path inventories, and "why this exists" context.

Alias discipline:

* Lead with the canonical noun phrase, then 3-8 high-signal aliases.
* Stop adding aliases when the next one is just a spelling variant, a synonym the model already knows, or a phrase Kai rarely says.
* If a skill needs more than 8-12 aliases, rename the skill, add a router parent, or split the domain.

Templates:

```yaml
description: Use when Kai asks to <verb> <domain>, especially <2-4 concrete trigger phrases>.
```

```yaml
description: Router for <domain> skills. Use when Kai asks about <broad domain>, then open the child skill for the specific verb or system.
```

```yaml
description: Pointer for <rule/domain>. Use when Kai asks about <trigger>; read <canonical file> for the full procedure.
```

Audit baseline from a 2026-05-21 Codex scan of 103 local skills:

* Average description length was 384 chars.
* 96 descriptions were over 240 chars.
* 66 descriptions were over 360 chars.
* 4 descriptions were over 500 chars.

That baseline is workable for Claude, but it is too chatty for a Codex-optimized lazy-loading surface. When touching a skill, shorten the description before expanding the body.

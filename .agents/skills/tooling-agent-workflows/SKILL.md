---
name: tooling-agent-workflows
description: The five-tier information model for agent-facing CLI commands - description, body, intro, help, outro - plus push-short/pull-long. Use when documenting a CLI agents invoke, not humans.
---

# Agent-facing CLI documentation

How an agent-facing CLI command carries its own documentation. The motivating command is `coily dispatch`. The model generalizes to every command an agent invokes and a human does not.

## The premise: these commands are agent-parsed, not human-read

Markdown skills are the human-to-agent interface. They earn their keep on fuzzy matching - aliases, synonyms, typo tolerance. A command like `coily dispatch` is different. It is hard-triggered. The agent runs `coily dispatch`, not something it might confuse for another command, so there is no synonym work to do. A human never runs it directly either, because the privileged op is wrapped for a reason.

That means the documentation for the command is entirely agent-parsed. It does not need to read like a skill. It needs to reach the agent at the right moment, and a skill markdown can only deliver once, at trigger time.

## The model

- [The five tiers](references/five-tiers.md) - the five distinct information surfaces (Description, Body, Intro, Help, Outro) and who reads each when.
- [Rule: push short, pull long](references/push-short-pull-long.md) - why pushed Intro stays short and pulled Help can be exhaustive.
- [Rule: top and bottom never collapse into one](references/intro-outro-distinct.md) - why Intro and Outro are two times, not two styles.
- [Where the docs live in code](references/docs-in-code.md) - embed one markdown file per surface, what stays in the skill, and applying it to `coily dispatch`.

Origin: [agentic-os-kai#711](https://github.com/coilysiren/agentic-os-kai/issues/711).

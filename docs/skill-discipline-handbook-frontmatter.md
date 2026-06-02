# Skill Discipline Handbook - Frontmatter, Status, Sections

## 3. SKILL.md frontmatter

Every SKILL.md begins with YAML frontmatter. Two fields required:

```yaml
---
name: <directory-name>
description: <one paragraph; pack keyword aliases for discoverability>
---
```

Rules (validator-enforced):

* `name` MUST equal the directory name.
* `description` MUST be non-empty.
* `description` is what an agent harness keyword-matches when deciding whether to invoke the skill. Lead with the canonical name, then pack 5-10 natural-language phrasings users (and agents) might reach for. End with a packed `Triggers - foo, bar, baz.` line.

Bias toward over-triggering. Harnesses tend to under-invoke skills.

## 4. The status line (where enforced)

Per-category. If `enforce_status: true` in the spec, every SKILL.md in that category needs a status line directly under the H1:

```markdown
# <Title>

Status: <emoji> <Kind> | Last <updated|tested>: YYYY-MM-DD
```

The emoji is part of the canonical format and pairs one-to-one with the kind. The validator rejects any other pairing. Pick kinds for your taxonomy (e.g. `Active 🟢`, `Stub ⚪`, `Runbook 🛠`, `Router 🗺`) in `categories.yaml`.

Categories without status enforcement are free-form. Add a status line voluntarily if it carries information (e.g. a digest skill noting when its data sources last changed shape), but the validator does not require one.

## 5. Required H2 sections (where enforced)

Per category and per status kind. If `required_sections.by_status` is set for a category, every SKILL.md of that status kind must contain the listed H2s. Section names match case-insensitively, leading and trailing whitespace ignored. Order is recommended but not enforced.

Use this for shaped categories where a missing section is a real problem (a runbook with no procedure, a router with no routing table). Free-form categories should leave this alone.

# Authoring walkthrough: capture intent, draft, validate

This is the operational walkthrough for drafting a new skill. The personal-OS-specific rules in the parent SKILL.md still apply.

## Capture intent

Start by understanding what the user wants. The current conversation often already contains the workflow (an investigation that worked, a recurring debug pattern, a checklist the user keeps redoing). Extract from history first: tools used, sequence of steps, corrections, input/output formats observed. Confirm with the user before drafting.

Five questions to pin down before writing:

1. What should this skill enable Claude to do?
2. When should this skill trigger? (user phrasings, contexts, scheduled routines)
3. What's the expected output format? (vault inbox file, GitHub issue, in-session report, terminal command, files on disk)
4. Which prefix fits (see `categories.yaml` for the canonical list)? Or do we need a new category (require justification)?
5. Will it touch live systems (kubectl, AWS writes, Trello, Discord, Bluesky)? If yes, route through `coily` and design test prompts that stay read-only or dry-run by default.

## Interview and research

Ask about edge cases, input/output, example artifacts, success criteria, dependencies. Don't write test prompts until this part is settled.

If research helps (existing similar skills, related docs, prior investigations), use the Agent tool with `subagent_type=Explore` for read-only codebase exploration. Reference existing skills before authoring a new one. There's almost always prior art worth cross-linking.

## Write the SKILL.md

Start by copying the appropriate template from [`../templates/`](../templates/) when one exists. For free-form categories (most of them), draft from scratch using a similar existing skill as a model.

Frontmatter rules (validator-enforced):

* **name** must equal the directory name.
* **description** non-empty, the primary triggering field. Include both what the skill does and concrete trigger phrasings. End with `Triggers - keyword1, keyword2, keyword3.`. Bias toward over-triggering since Claude under-triggers skills.

Status line (where enforced - currently `ops-investigation-*` and `ops-investigation`): directly under the H1, format `Status: <emoji> <Kind> | Last <updated|tested>: YYYY-MM-DD`. See handbook §4.

Required H2 sections per category: see handbook §5.

Body length: hard cap in [`check_documentation_layout.py`](../../../../agentic_os/check_documentation_layout.py). SKILL.md is not exempt. If it's growing past that, split into sibling reference files alongside SKILL.md and link from the SKILL.md.

## Anatomy of a skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
├── scripts/        - executable code for deterministic / repetitive tasks
├── references/     - docs loaded into context as needed
├── assets/         - files used in output (templates, snippets)
└── results/        - dated writeups for skills that run periodically
```

## Progressive disclosure

Skills load in three tiers:

1. **Metadata** (name + description) - always in context (~100 words).
2. **SKILL.md body** - in context whenever the skill triggers (cap in `check_documentation_layout.py`, same as all Markdown).
3. **Bundled resources** - pulled in as needed; scripts can execute without their source loading.

Patterns:

* Reference files clearly from SKILL.md with guidance on when to read them.
* For large reference files (over 300 lines), include a table of contents.
* For domain-spanning skills, organize by variant and route from the SKILL.md.

## Writing style

Imperative voice. Explain the why behind each instruction. Today's models respond to reasoning better than to ALL-CAPS MUSTs. If you find yourself writing rigid scaffolding, that's a yellow flag - reframe and explain instead.

Voice-match the personal-OS AGENTS.md: no em-dashes, no italics, no semicolons in prose, no tables. Bullet lists in the shape `* anchor - tag1 / tag2 - detail`.

## Validate before commit

```sh
python3 scripts/validate_skills.py <skill-name>
python3 scripts/check_dead_links.py .agents/skills/<skill-name>/
```

Both run automatically in pre-commit. Run them by hand during iteration to keep the feedback loop tight.

## Wrap-up

* Run `./setup.sh` from the personal-OS repo root to refresh `~/.claude/skills/<name>` symlinks.
* Restart Claude Code so the loader picks up the new skill.
* File the GitHub issue first if you haven't (every commit closes one).
* Commit, push to main, the commit message closes the issue.

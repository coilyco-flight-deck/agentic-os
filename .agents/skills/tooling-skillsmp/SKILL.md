---
name: tooling-skillsmp
description: Discover and install skills from skillsmp.com (the Claude skill marketplace). Route through this skill, never raw curl - the harness denies direct skillsmp.com fetches.
---

# skillsmp Skill Discovery

Handle the full loop: notice a skill might help, search the marketplace, vet what comes back,
show the user the skill's public page, confirm before install, and drop the skill into
`<personal-os-repo>/.agents/skills/` so future sessions pick it up automatically.

## When to consider reaching for this skill

Read this broadly. **When a task sounds like "the kind of thing someone has probably written a skill for", check the marketplace first.**

Concrete triggers:

- The user explicitly mentions skillsmp, "the skill marketplace", or asks to "find a skill for ..." or "install a skill that ...".
- "Is there a skill for X?" / "does a skill exist for Y?" - answer by actually looking.
- "Can you ..." requests describing a narrow, specialized task that feels like a packaged capability: parsing a niche format, integrating with a specific API, a recognized workflow in some domain.
- **Reinvention check.** You (the agent) are mid-task and notice you're about to hand-roll something that sounds like a packaged capability - pause and check the marketplace before continuing. The 30-second search beats 10 minutes of reimplementing. Concrete shape of the moment: you're about to write a helper that parses ICS calendar files, generates QR codes, extracts EXIF metadata, converts EDIFACT, fetches OpenGraph tags - that's when to stop and run the search step. If search comes up empty, carry on and build it yourself; the point is to **look**, not to force a skill where none fits.

What NOT to trigger on:

- Very generic requests ("write me a function that adds two numbers").
- Tasks where a skill already exists locally (`<personal-os-repo>/.agents/skills/`) - use those first.
- Requests where the user has said "do it yourself" or "don't use external tools".

Before searching, scan existing skills in `<personal-os-repo>/.agents/skills/` - if a matching one is already there, skip the marketplace.

## The API at a glance

The marketplace endpoints, auth, rate limits, response shape, and the `stars` caveat live in [`references/api.md`](references/api.md). Read it before issuing queries.

## The workflow

The full multi-step skillsmp workflow (search shape, review shape, vetting checklist, install, commit conventions, marketplace fast-forward) lives in [`references/workflow.md`](references/workflow.md). Read it before installing a marketplace skill.

## On announcing the search

When you decide a task warrants a marketplace check, say so in one short sentence before searching - e.g., "Before I roll my own, let me check skillsmp for an existing skill." Lets the user redirect if they'd rather you just do it. Don't monologue about the decision process.

## Commit after install

The installed skill lives under `<personal-os-repo>/.agents/skills/` and is version-controlled. Per the personal-OS git workflow, commit the new skill directory directly to `main` and push after install. One commit per skill (installs are "purely additive").

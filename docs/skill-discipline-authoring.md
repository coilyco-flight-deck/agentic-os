# Authoring walkthrough

How to draft a new skill, validate it, and ship it. Pairs with [`skill-discipline-handbook.md`](skill-discipline-handbook.md), which carries the structural rules this walkthrough assumes. The validate, commit, and iterate steps live in [`skill-discipline-authoring-shipping.md`](skill-discipline-authoring-shipping.md).

## Capture intent

Start by understanding what the skill should do. Often the current conversation already contains the workflow: an investigation that worked, a recurring debug pattern, a checklist that keeps coming back. Extract from history before writing: which tools were used, the sequence of steps, the corrections, the input and output formats.

Five questions to pin down before writing anything:

1. **What should this skill enable an agent to do?** One sentence.
2. **When should it trigger?** Concrete user phrasings, contexts, scheduled routines.
3. **What is the expected output?** A vault note, a GitHub issue, an in-session report, a terminal command, a file on disk.
4. **Which category does it fit?** Pick the prefix or exact-name family up front. If none fits, you are committing to update the spec first, before authoring.
5. **Does it touch live systems?** Writes, deletions, network calls with side effects. If yes, design the skill to default to read-only or dry-run, and require an explicit opt-in for destructive operations.

Don't draft until those five are settled.

## Interview and research

Ask the author about edge cases. What inputs are valid? What outputs are correct? What are the success criteria? What are the dependencies (other skills, MCP servers, external services)?

If similar skills exist in the repo, read them. There is almost always prior art worth cross-linking, and copying a successful skill's shape is faster than designing from scratch.

If the repo provides templates under (typically) a `templates/` directory, start from the closest one. Validator-enforced structure is documented in [`skill-discipline-handbook.md`](skill-discipline-handbook.md) sections 4 and 5.

## Draft the SKILL.md

Create the directory: `.agents/skills/<skill-name>/`. Add a `SKILL.md` with frontmatter and body.

Frontmatter rules (validator-enforced):

* `name` MUST equal the directory name.
* `description` MUST be non-empty. This is the primary triggering field. Include both what the skill does and concrete trigger phrasings. End with a packed `Triggers - foo, bar, baz.` line. Bias toward over-triggering since agent harnesses tend to under-invoke.

Status line: only if the category enforces it. Format is `Status: <emoji> <Kind> | Last <updated|tested>: YYYY-MM-DD`, directly under the H1. The emoji must pair with the kind exactly as declared in `categories.yaml`.

Required H2 sections: only if the category enforces them, dispatched by status kind. The validator names the missing section in its error output; that is usually enough to know what to add.

Body length: see [`check_documentation_layout.py`](../agentic_os/check_documentation_layout.py) for the cap. SKILL.md is not exempt. If you outgrow either limit, split into sibling `<skill>/<topic>.md` files linked from the SKILL.md, not inlined.

## Voice

Follow your project's voice rules (the ones in [`skill-discipline-handbook.md`](skill-discipline-handbook.md) section 6 are a starting point if you have none yet). Bullets are usually clearer than dense prose. Imperative voice ("Run X. Check Y.") beats hedged voice ("you might consider running X"). Explain the why, not just the what.

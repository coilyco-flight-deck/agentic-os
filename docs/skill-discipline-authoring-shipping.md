# Authoring walkthrough - Validate, Commit, Iterate

Continues [`skill-discipline-authoring.md`](skill-discipline-authoring.md). Once the SKILL.md is drafted, validate it locally, commit it through the hooks, and iterate after it ships.

## Validate locally

Before staging:

```sh
pre-commit run skill-conventions --all-files
pre-commit run dead-cross-links --all-files
```

Both should exit 0. If they don't, fix the reported issues. The error messages name the line and the rule.

## Commit

Stage the new directory and commit. The pre-commit hooks run automatically:

* `skill-conventions` re-runs the validator.
* `dead-cross-links` re-runs the cross-link checker.

If any hook fails, fix the underlying issue and commit again. **Do not use `--no-verify`.** The hooks are the discipline; bypassing them defeats the point.

## Iterate

A skill that ships and gets used always reveals gaps. Common patterns after the first invocation:

* The trigger description was too narrow: the agent did not pick the skill up when it should have. Pack more aliases into `description`.
* The body assumed context the agent did not have. Add the missing assumption to a body section, or split it into a `references/` file.
* A new edge case appeared. Add it to the relevant section with the why and the fix.

The validator and the dead-link checker catch structural drift. Voice and usefulness drift you have to catch yourself, usually by re-reading a skill cold after a few weeks.

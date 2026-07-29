---
name: writing-voice-guide-linter
description: Lint prose against Kai's voice rules - no em-dashes, no italics, no semicolons, no prose tables, she/her. Triggers - voice lint, voice check, lint prose, em-dash check, pronoun check.
low-context: required
---

# voice-guide-linter

Pre-flight check for prose Kai writes - commits, PRs, READMEs, issues,
blog posts, and knowledge notes. Catches the high-frequency voice-rule slips
before they ship.

## Procedure

```sh
python3 <loaded-skill-dir>/writing-voice-guide-linter/lint.py <file-or-dir> [--strict]
```

Reports each violation as `path:line: [rule] 'span' - hint`.

Resolve `<loaded-skill-dir>` from the current harness's native skill root.
The source checkout keeps the helper under `.agents/composed/`, while
agent-compose promotes it into the selected role's native skills bundle.

Default mode reports all rules. `--strict` exits non-zero on any
violation, suitable for pre-commit hook integration.

## Rules checked

- **em-dash** - U+2014 anywhere. Suggest replacement: ` - `.
- **italics-asterisk** / **italics-underscore** - markdown italics
  outside code fences.
- **prose-semicolon** - `;` outside code fences.
- **prose-table** - markdown `|`-delimited table rows in narrative text.
- **wrong-pronoun-he / wrong-pronoun-they** - `he`, `him`, `his`,
  `they`, `them`, `their`. Flagged for human review since pronouns
  may legitimately refer to someone else; the linter cannot resolve
  the referent.
- **email-leak** - `coilysiren@gmail.com` in any file. Allowed only
  in resume + website.

## Notes

- The skill does NOT enforce the "no people's names in public
  artifacts" rule - that needs context the regex doesn't have. Kept
  as a separate human-review concern per AGENTS.
- Voice guide source: the active composed or project-local voice guide.
- The pronoun rules over-flag by design. Better to surface false
  positives than miss a real slip about Kai.
- Pre-commit-hook integration is a separate piece of work; the linter
  is callable today either way.

# Encoded leak guard

`leak-guard` is a pre-commit hook that rejects plaintext occurrences of terms
that should not be grep-bait. It exists because most leaks are not secrets, they
are *awkward*: an employer name hardcoded in a config path, a partner's name in
a comment, a private repo named in a public README. None of these trip a secret
scanner, but any of them turns `rg <term>` into a harvesting tool. See
the recovered inbox corpus.

## The one primitive

Three leak/coupling classes reduce to a single rule shape - *a string S must not
appear in scope T, and the rule is stored encoded so grepping the rule reveals
neither S nor the coupling*:

- **sensitive data** - an employer or personal name that should never be
  grep-bait. The threat model is `rg <name> | mail-merge`, not decryption, so a
  reversible encoding is the right grade.
- **private to public leak** - a bridge (private) identifier referenced from a
  flight-deck (public) repo. The wrong direction for data lockdown.
- **dependency cycle** - one direction of a repo-to-repo reference banned so the
  edge stays one-way.

## How it stays leak-safe

The ruleset (`agentic_os/pre_commit/leak_guard_rules.py`) stores every term as
lowercase **hex**, never plaintext. Hex was chosen over base64 because it is
exclusively `[0-9a-f]` with no padding, copy-pastes cleanly, and decodes in one
line in every language. The hook decodes each term **only in memory** to build
its matcher, and a violation prints the rule id, path, line, and remediation -
**never the term**. So neither the ruleset nor the hook output is itself a leak.

Terms match on word boundaries by default, so a rule for `ward` does not fire on
`forward` or `awkward`.

## Adding a term

Encode it without the plaintext landing in shell history (the helper reads
stdin):

```
leak-guard-encode            # type or pipe the term, copy the hex back
leak-guard-encode --decode <hex>   # round-trip a hex term back to text
```

Then add a rule to `leak_guard_rules.py`:

```python
{
    "id": "example",
    "term_hex": "6e6565646c65",   # leak-guard-encode of the term
    "repos": ["cli-guard"],        # omit / None to fire in every repo
    "only_globs": ["go.mod"],      # fire ONLY in these paths (optional)
    "allow_globs": ["**/resume.md"], # paths where the term is permitted (optional)
    "message": "remediation text - never name the term here",
},
```

`only_globs` and `allow_globs` are duals: `only_globs` narrows a rule to a few
paths (enforce the front-page README alone, or `go.mod` alone); `allow_globs`
exempts known-legitimate paths (a public bio surface). Path globs follow the
same semantics as every other catalog hook (`is_excluded`): a `dir/**` prefix, a
trailing-slash directory, or an fnmatch pattern, matched against repo-relative
POSIX paths. Note `**/x` does not match a top-level `x` - list `x` explicitly for
root files.

Per-repo, opt whole paths out with `[tool.agentic-os.leak-guard] excludes = [...]`
in that repo's `pyproject.toml`.

## Scope and rollout

Rule scope is matched against the current repo, resolved from `origin` (so it is
worktree-safe). A rule with `repos` set fires only in those repos; a rule with no
`repos` fires everywhere it is installed. The hook is authored and dogfooded here
in agentic-os; fleet rollout to other repos is a deliberate ansible step, run
after each target repo's existing occurrences are cleaned or allowlisted - the
guard is staged, never flipped on fleet-wide in one move.

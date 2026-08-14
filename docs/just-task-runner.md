# `just` task runner

Spike for [inbox#365](https://forgejo.coilysiren.me/coilysiren/inbox/issues/365).

`ward exec` has good ergonomics, but it makes every repo depend on ward to run
its own tasks. Ward is out-of-band flight control, and a repo should mention it
in passing rather than route its whole build through it. Clone this repo without
ward on `PATH` today and nothing runs.

The [`justfile`](../justfile) carries the same verbs, runnable with a
third-party tool. This is additive: `.ward/ward.yaml` still exists, `ward exec`
still works, and no CI has been switched over.

## Usage

```bash
just              # list every verb, same discoverability as bare `ward exec`
just aos-test
just agent-id -n 3
```

Trailing arguments reach the underlying command directly, so the `--` separator
`ward exec` required is gone: `ward exec agent-id -- -n 3` becomes
`just agent-id -n 3`. Recipes run at the repo root regardless of the invoking
directory, matching `ward exec`.

## Parity

All 69 verbs are present with identical names and command lines. None contained
shell metacharacters, braces, quotes, or newlines - ward's own argv policy had
already normalized the corpus, which is what made the conversion mechanical.

Verified on this branch:

* `just agent-id` runs, and resolves to the repo root when invoked from `docs/`.
* `just agent-id -n 3` passes flags through without a separator.
* `just agent-terminal-test` and `just aos-lint` pass.

## Known gaps

- **Duplication.** Both `.ward/ward.yaml` and `justfile` declare all 69 verbs, so
  a verb added to one will drift. This is why the spike is additive.
- **Not installed everywhere.** `just` now installs into the dev-base image
  (`docker/dev-base/install-common.sh`, pinned by `JUST_VERSION`), but is still
  absent from the Homebrew formulae and the Scoop bucket. CI can switch once
  dev-base republishes. Host installs are still manual.
- **Descriptions run long.** `just` reads only the **last** comment line above a
  recipe, so wrapping silently truncates a doc to its tail fragment. They stay
  on one line, and `just --list` rows reach ~144 characters.
- **No echoed command.** Recipes are `@`-prefixed, because just would otherwise
  echo the recipe line with an unexpanded `"$@"`, misrepresenting the real argv.

## What this does not carry over

`ward exec`'s argv pre-validation is gone - just recipes run through `sh`. That
is deliberate: the containment boundary is the container (`aos` / `ward agent`),
not the task runner.

Audit rows for task verbs also go away. Nothing depends on them. There are no
non-doc references to `--audit-override-dirty` or the clean-tree gate here.

## Remaining migration

Executable coupling to `ward exec` here is small - `scripts/run-workflow-ward.sh`,
`scripts/ci/aos-cli-release.sh`, and the release workflow script asserted by
`tests/test_aos_cli_release.py`. The rest of the ~97 mentions are prose:
docstrings, error-message hints, and generated-file headers.

`.ward/ward.yaml` also carries `agent:` and `catalog:` blocks, which are
metadata rather than task definitions and are destined for `.aos/aos.yaml`.

This doc is absent from [FEATURES](FEATURES.md), which sits 32 characters below
its own 4000-char cap and cannot absorb a new entry until it is split.

## See also

- [README](../README.md)
- [AGENTS](../AGENTS.md)
- [FEATURES](FEATURES.md)

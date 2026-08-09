# Default TODO destination and flake discipline

## Default TODO destination

When the operator asks to file a todo without naming a destination, default to a Forgejo issue on `coilyco-bridge/agentic-os-kai` (forgejo.coilysiren.me, the canonical tracker). If it clearly belongs elsewhere, file there and say so. Close it from a commit with a full same-repo Forgejo URL (`closes https://forgejo.coilysiren.me/<owner>/<repo>/issues/N`) - encouraged house style now that the `closes-issue` hook is retired.

Kai's own work routes through Forgejo. GitHub issues on external-facing `coilysiren/*` repos are an inbox for external contributors only; agents never file there. Split by `hasIssuesEnabled` flag: on = external-facing, off = deployment-of-one or private. Either way, route to Forgejo.

**Never ask whether to file an issue. Just file it.** If you're about to ask "should I file an issue for X" or offer it as a choice, the answer is always yes - file it and mention in one line what you filed. Issues are post-it notes: cheap, swept up by backlog routines. Asking is pure overhead, and at Kai's pace a deferred "want me to file this?" is something she will miss. Applies to any issue surfaced mid-task.

## Test flake discipline

Every flaky-test sighting in a `coilysiren/*` repo becomes a same-repo issue, no exceptions (flaky = failed then passed on re-run with no code change, or non-deterministic across two runs). File immediately, even mid-task: test name, both runs' output, candidate causes. Don't paper over by re-running until green.

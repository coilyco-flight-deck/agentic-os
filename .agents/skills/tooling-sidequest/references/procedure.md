# Sidequest procedure (single repo - the default)

1. **Wait for the work description.** The trigger phrase alone is not enough - she still needs to describe the actual engineering work. If she hasn't yet, acknowledge briefly and wait.
2. **Decide scope.** Single repo or multi-repo fan-out (see [fan-out](fan-out.md)). Default to single repo. Fan out only when the fan-out trigger is met.
3. **Pick the repo.** Use `data/repo-registry.md` and `data/repo-digests/` to pick the most plausible `coilysiren/*` repo from the content. Fall back to `coilyco-bridge/agentic-os-kai`. Do not ask which repo unless two are genuinely tied.
4. **Infer a title.** Short, imperative, matches the repo's existing issue style. No emojis unless the repo's own issues use them.
5. **File the issue.**
   ```bash
   ward ops gh issue create --repo coilysiren/<repo> --title "<inferred title>" --body-file /tmp/sidequest-body.md
   ```
   Body in Kai's voice rules (no em-dashes, no italics, no semicolons in prose). Quote her description, then add any obvious next-action bullets. End the body with the **completion contract** block (see [completion-contract](completion-contract.md)) so the dispatched session inherits it. Use `--body-file` - issue bodies routinely contain parens and other shell metacharacters the ward policy gate rejects in inline `--body`.
6. **Echo the issue.** Use the GitHub issue echo format (`[title](url)` + blockquote snippet) so the audit trail lands in chat.
7. **Dispatch.**
   ```bash
   ward dispatch interactive coilysiren/<repo>#<N>
   ```
   Always `interactive` for sidequests - Kai's eyes are on the spawned session. See `kai-ward-dispatch-shorthand` for the dispatch mode rationale.
8. **Resume.** If the sidequest interrupted other work in this session, pick it back up where you left off after the dispatch lands. Name what you're resuming.

See [fan-out](fan-out.md) for the multi-repo variant.

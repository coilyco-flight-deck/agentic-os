# Sidequest procedure (single repo - the default)

1. **Wait for the work description.** The trigger phrase alone is not enough - she still needs to describe the actual engineering work. If she hasn't yet, acknowledge briefly and wait.
2. **Decide scope.** Single repo or multi-repo fan-out (see [fan-out](fan-out.md)). Default to single repo. Fan out only when the fan-out trigger is met.
3. **Pick the repo.** Use `data/repo-registry.md` and `data/repo-digests/` to pick the most plausible `coilysiren/*` repo from the content. Fall back to `coilyco-bridge/agentic-os-kai`. Do not ask which repo unless two are genuinely tied.
4. **Infer a title.** Short, imperative, matches the repo's existing issue style. No emojis unless the repo's own issues use them.
5. **File the issue.**
   ```bash
   ward ops forgejo issue create coilysiren <repo> --title "<inferred title>" --body-file /tmp/sidequest-body.json
   ```
   Forgejo, not GitHub - ward resolves Forgejo refs, and the GitHub queue is for external contributors. Body in Kai's voice rules (no em-dashes, no italics, no semicolons in prose). Quote her description, then add any obvious next-action bullets. Write the request body to a JSON file for `--body-file`, then end it with the **completion contract** block (see [completion-contract](completion-contract.md)) so the spawned session inherits it. Use `--body-file` - issue bodies routinely contain parens and other shell metacharacters the policy gate rejects in inline `--body`.
6. **Echo the issue.** Use the issue echo format (`[title](url)` + blockquote snippet) so the audit trail lands in chat.
7. **Spawn.**
   ```bash
   warded engineer coilysiren/<repo>#<N>
   ```
   Always the interactive engineer surface for sidequests - Kai's eyes are on the spawned session. The ward dispatch runs containerized (fresh clone, reaper-backed) in its own session.
8. **Resume.** If the sidequest interrupted other work in this session, pick it back up where you left off after the spawn lands. Name what you're resuming.

See [fan-out](fan-out.md) for the multi-repo variant.

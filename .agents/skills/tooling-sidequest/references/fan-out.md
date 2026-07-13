# Multi-repo fan-out

**When to fan out.** Either of these:

- Kai says so - "parallelize across repos", "fan this out", "this spans multiple repos", or similar.
- You determine it yourself - the described work spans 2+ `coilysiren/*` repos and the per-repo pieces are each independently filable as a real unit of work. A change that merely touches a second repo in passing is still single-repo. Genuine separate deliverables per repo is fan-out.

**What to do.** Replace steps 3-7 of the [single-repo procedure](procedure.md) with:

1. **File the parent issue.** An umbrella issue capturing the whole through-line - the goal, the chain, and the per-repo split. File it against the repo that owns the orchestration or the bottom of the dependency chain. This is the design issue a reader lands on first.
2. **File one child issue per repo.** Each child is scoped to exactly that repo's deliverable, in that repo. Title imperative, body quoting the relevant slice of Kai's description plus next-action bullets. Each child body links the parent (`coilysiren/<parent-repo>#<N>`) and ends with the completion contract block. The parent issue does NOT get the block - it is a tracker, never dispatched.
3. **Link children to the parent.** After filing, link each child as a sub-issue of the parent on Forgejo so the parent shows the fan-out tree. If sub-issue linking is unavailable, edit the parent body to list the children as a checklist instead.
4. **Determine build order.** Some fan-outs are fully parallel, some have a dependency chain (build bottom to top). Work it out from the description.
5. **Spawn the unblocked children.** `warded engineer <ref>` for every child whose dependencies are already satisfied - all of them if fully parallel. Children blocked on an earlier child stay filed and linked but are NOT spawned yet. Note them in chat as blocked-on-`#N`.
6. **Echo everything.** Parent and every child, issue echo format. State which were spawned and which are blocked.

Do not spawn the parent itself - it is a tracking issue, not a unit of work. Step 8 (resume) of the single-repo procedure still applies.

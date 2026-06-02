---
name: writing-to-issues
description: Break a plan, PRD, or oversized issue into independently-grabbable tracer-bullet vertical slices, tagged HITL/AFK. Also fires when a session opens with a bare oversized issue ref. Triggers - convert to issues, make tickets, break this down, decompose, split #N.
---

# To Issues

Break a plan into independently-grabbable GitHub issues using vertical slices (tracer bullets).

## Process

### 0. Size-check (only on oversized-opener path)

If this skill fired because the session opened with a bare issue reference, fetch the issue with `gh issue view <number>` and assess size before doing anything else:

- Single, narrow acceptance criterion - not oversized. Decline politely, hand control back, let the normal flow run.
- Multiple unrelated acceptance criteria, vague scope, or estimated to touch many files across layers - oversized. Tell the user you flagged it as oversized and ask if they want to split before executing. If yes, continue to step 1. If no, hand control back.

The point of this gate is to avoid splitting issues that don't need it. The skill is the right tool when an issue would otherwise burn a whole session on orientation plus mid-task compaction.

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a GitHub issue number or URL as an argument, fetch it with `gh issue view <number>` (with comments).

### 2. Explore the codebase (optional)

If you have not already explored the codebase, do so to understand the current state of the code.

### 3. Draft vertical slices

Break the plan into **tracer bullet** issues. Each issue is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

Slices may be 'HITL' or 'AFK'. HITL slices require human interaction, such as an architectural decision or a design review. AFK slices can be implemented and merged without human interaction. Prefer AFK over HITL where possible.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

### 4. Quiz the user

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices (if any) must complete first
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked as HITL and AFK?

Iterate until the user approves the breakdown.

### 5. Create the GitHub issues

- [Create the GitHub issues](references/create-issues.md) - issue body template and dependency-order creation.

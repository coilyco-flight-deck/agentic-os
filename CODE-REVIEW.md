# Code review contract

Code review here defends repo-local invariants and historical issues.

## Localized invariants

Review the smallest repo-local surface that can fail, and name the invariant it protects.

## Historical issues

Carry forward fixes for issues that have already recurred, or that showed up
large enough to stop the work.

* Dev-base manifest inspections stay bounded per call. A Buildx client stall
  must consume the short retry budget, not the outer image-build budget.
  Definitive registry 404 responses are immediate checkpoint misses.
* Native workspace cleanup compares live leases and Git worktrees by resolved
  filesystem identity. Lexical aliases must not make an active worktree appear
  unleased to the fleet sweep (agentic-os#858). Dead leases remain protected
  until their 24-hour recovery grace expires (agentic-os#882).

## Update triggers

Refresh this file when the same issue re-occurs or when a work stop exposes a wider pattern.

## Out of scope

Generic-purpose review advice, like variable-naming trivia, belongs somewhere else.

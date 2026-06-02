# Phase 3 - Categorize and rank

Categorize entries semantically (eg. game-server-ops, gmail, calendar,
gaming, observability, dev-tools, social, finance, ai-infrastructure,
speculative-asks, etc.). Then rank globally - not within categories -
at 3:2:1 ratio: 🥉 50%, 🥈 33%, 🥇 17%. A sparse category may end up
entirely 🥉; that's expected and intentional.

Ranking criteria, in priority order:

1. Direct fit to current repo work or open issues across the user's repo set.
2. Reduces a manual workflow the user is currently doing by hand.
3. Reusable across multiple projects.
4. Speculative entries the user has personal leverage on (someone they know)
   rank higher than ones they don't.

Prepend the medal emoji to each entry. Output:
`YYYY-MM-DD-capability-scout-3-ranked.yaml`. Group by category, but
keep the global rank labels intact.

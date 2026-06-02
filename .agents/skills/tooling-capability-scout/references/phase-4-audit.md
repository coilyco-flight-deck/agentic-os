# Phase 4 - Security audit (🥈 and 🥇 only)

**BLOCKED ON #185.** The audit rubric below is provisional. Phase 4 has
been red-flagging third-party MCPs that overlap a coily wrapper (Cloudflare,
GitHub, k8s, Tailscale, AWS, Discord-admin) on coily-bypass grounds, but
mcporter is the actual execution path and may itself be the audit choke
point. Once mcporter execution is verified (#185), revise this rubric:
🔴 should narrow to real supply-chain audit failures (malicious code,
abandoned projects, anonymous maintainers writing privileged tools),
not "duplicates a coily wrapper." Until then, treat the coily-overlap
red flag with skepticism and surface the call to the user instead of
auto-rejecting.

For every 🥈 and 🥇 entry, run the `supply-chain-audit` skill. 🥉
entries are skipped (we will not install them, no need to spend the
audit budget).

Map results to a `🟢🟡🔴` prefix:

- 🔴 - audit failed (suspicious maintainer, malicious code patterns,
  abandoned/unmaintained, dependency-confusion-style risk, or zero
  downstream adoption with high-privilege scope). 🔴 entries are never
  installed regardless of any later approval.
- 🟡 - audit passed but the domain is theoretically dangerous (banking,
  payments, cloud-write, secrets handling, code execution, browser
  automation against authenticated sessions). Cautious-by-domain even
  when the implementation is clean.
- 🟢 - audit passed and the domain is benign (read-only catalog, public
  APIs, narrow-scope data fetchers, documentation tooling, file format
  conversion).

Speculative entries (no code to audit) get 🟡 by default since "I'd ask
someone about it" is not "I'd install it tomorrow."

Output: `YYYY-MM-DD-capability-scout-4-audited.yaml`. Preserve the
medal emoji; prepend the safety emoji. Final per-entry prefix shape:
`{category-emoji}{medal}{safety} ` followed by `Category / Org / Name /
Url / Description`.

# Role-composed skills and methods

AOS can carry deep knowledge only selected roles receive, invisible to harness
discovery until agent-compose builds a role bundle.

## Source layout

Ordinary knowledge stays globally discoverable at
`.agents/skills/<name>/SKILL.md`. Role-scoped knowledge uses a distinct root
and entrypoint, `.agents/composed/<name>/COMPOSED.md`.

The two roots share the taxonomy in `.agents/skills/categories.yaml`. A name
cannot exist in both, and no composed source may contain `SKILL.md`, including
in nested support directories.

## Role binding

AOS owns the allowlist in `.agents/roles.kdl`, where each `role <name>` block
carries one or more `composed-skill <name>` lines naming an existing directory
under `.agents/composed/`. Duplicate roles, duplicate bindings, unknown roles,
and missing sources fail composition, and every deployed role has a block with
at least one source.

A binding may use a quoted shell-style glob for a homogeneous family, such as
`composed-skill "coding-*"`, keeping unrelated sources exact. Agent-compose
expands matches in lexical order and fails on an invalid, empty, or overlapping
pattern. A future source matching the family is admitted without a role edit.

Role slices follow the boundaries recorded in `.agents/roles.kdl`. The matrix
and coverage audit below record rationale without duplicating that config.

## Composition

Agent-compose selects ordinary skills for every role, then adds only the current
role's composed allowlist, copying each into the isolated output and renaming
`COMPOSED.md` to `SKILL.md`. No unselected composed source appears in the role's
catalog, files, manifest, or selection trace, so the boundary is about context
load and role focus rather than routing hints.

`.agents/roles.kdl` grants knowledge only, never commands, credentials, network
access, mounts, or runtime permissions. Ward remains the authority layer.

## Validation

`check-skills` validates ordinary sources and `check-composed-skills` validates
composed layout and content. `documentation-layout`, `dead-cross-links`, and
`source-doc-refs` understand both entrypoint names.

## House taste in the public catalogue

`.agents/composed/` carries a small set of sources describing Coilyco's taste
rather than a person's: `writing-kai-voice` and the `personal-preference-*`
family. They are public because a consumer outside Kai's personal fleet needs
them, the first being
[sirens-echo](https://forgejo.coilysiren.me/coilyco-gaming/sirens-echo), whose
Discord agent composes a bundle and cannot reach a private catalogue.

An organization can own a favorite colour, and owning one still does not answer
for an agent: a composed agent's own favorite colour is the one on its identity
card. It cannot own a person's social accounts, career, or job search. A source
qualifies when its body is true of anyone writing under the Coilyco name, and
when an agent adopting it states house taste rather than a biographical fact.
Sources that fail stay in `coilyco-bridge/agentic-os-kai`: the `kai-` family,
including `personal-preference-social`, which shares a prefix with sources that
qualify and still fails, because social accounts are a member's.

`writing-kai-voice` keeps its name through promotion so existing `roles.kdl`
selectors keep resolving, even though the name now understates its scope.
Selection stays with each repository's own `roles.kdl`, and a consumer that
must bound what it receives uses a request `source` with `declaration=` rather
than `root=`.

## Role-composed methods and coverage

## Role-composed principal methods

Principal workflow methods stay out of roles that do not use them. AOS owns
the role allowlists in [`.agents/roles.kdl`](../.agents/roles.kdl).

## Matrix

Selection lives in `.agents/roles.kdl`. In summary: **Director** takes core Git,
licensing, supply-chain, and architecture guidance plus decision architecture,
PM methods, prioritization, scouts, observer voice, voice linting,
system-improvement vocabulary, issue decomposition, and skill authoring.
**Engineer**, **QA**, and **Ops** share Git workflow and supply-chain audit,
with QA adding code review, Engineer and Content Creator adding
public-repository writing, and Engineer and Ops adding system-improvement
vocabulary. **Designer** takes the PM family, design methods, and the frontend
coding pair. **Executive Strategist** takes deduplicated advisor, PM, and CEO
methods for evidence synthesis, portfolio allocation, program decomposition,
scouts, skill authoring, and issue writing. **Content Creator** takes the whole
writing family plus the Discord and customer-success methods it inherited when
Community stopped being a deployed role.

## Handoffs

Executive Strategist owns scout discovery, ranking, and portfolio
recommendations, recording returned evidence without inheriting execution
authority. Engineer or ops owns verification, implementation, validation, and
landing. Content Creator owns routine member interaction and a clean handoff,
and human stewards retain moderation.

Composition grants knowledge only. Ward's fixed workflow and the separately
selected AOSguard surface still control tools, credentials, and write
authority. Role composition is the current coarse gate for skill authoring,
refined by
[agent-compose#70](https://forgejo.coilysiren.me/coilyco-flight-deck/agent-compose/issues/70)
and
[agentic-os#716](https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/issues/716):
deterministic structure checks stay the required gate, with budget-bounded
evaluation offered for admission decisions.

## Coverage audit

A 2026-08 pass moved a handful: Director narrowed to decision-relevant coding
while gaining the PM family, Design gained signal triangulation, Content Creator
took the social editorial loop and gave issue decomposition to the decision
roles, and AI Engineer received the coding family behind benchmark runners.
`.agents/roles.kdl` stays the authoritative selection.

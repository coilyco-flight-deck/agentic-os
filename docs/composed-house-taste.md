# House taste in the public catalogue

`.agents/composed/` carries a small set of sources that describe Coilyco's own
taste and style rather than a person's: `writing-kai-voice` and the
`personal-preference-*` family.

They live here, in the public catalogue, because a consumer outside Kai's
personal fleet needs them. The first is
[sirens-echo](https://forgejo.coilysiren.me/coilyco-gaming/sirens-echo), a
public repository whose Discord agent composes a role bundle and cannot reach a
private catalogue.

## The rule that decides placement

An organization can own a favorite colour. It cannot own a person's social
accounts, career, or job search.

A source qualifies for this catalogue when its body is true of anyone writing
or building under the Coilyco name, and when an agent adopting it is stating
house taste rather than reporting a biographical fact about a member. Each
promoted source already reads that way: "These are CoilyCo's, held in common by
everyone who works under the name."

Sources that fail the rule stay in
`coilyco-bridge/agentic-os-kai`: `kai-career`, `kai-job-search`,
`kai-linkedin-voice`, `kai-linkedin-video`, `personal-preference-social`, and
the rest of the `kai-` family. `personal-preference-social` is the instructive
one. It shares a prefix with sources that qualify and still fails, because
social accounts are a member's, not the organization's.

## Naming

`writing-kai-voice` keeps its name through the promotion so every existing
`roles.kdl` selector and cross-repository reference keeps resolving. The name
now understates its scope, since the body is Coilyco house style. Renaming it
is a separate, wider change.

## Consumers

Selection stays with each repository's `.agents/roles.kdl`. A consumer that
must bound what it receives uses a request `source` with `declaration=` rather
than `root=`, which enumerates admitted skills explicitly instead of inheriting
the provider's role bindings.

## See also

* [FEATURES.md](FEATURES.md) - shipped capabilities.
* [catalog-caps-reference.md](catalog-caps-reference.md) - validation caps.

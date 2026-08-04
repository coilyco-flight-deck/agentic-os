# dev-base build cache

Every multi-architecture payload and full-image build reuses a persistent
Buildx builder on its dedicated runner. The publish action creates a builder
only when it is absent and recreates it only when bootstrap fails.

Each language payload reads and writes a stable `type=registry` cache at
`agentic-os:lang-<language>-buildcache`. The full image uses
`agentic-os:buildcache`. Cache export uses `mode=max`, so intermediate language
layers remain reusable across workflow runs, runners, and days even though the
payload draft manifests are commit-scoped.

Cache writes use `ignore-error=true`. A registry cache fault therefore does not
discard an otherwise valid image, but the next run may be colder. The payload
draft manifest and the cache ref have separate jobs: the draft gives the full
job an exact same-commit input, while the stable cache accelerates later
builds.

Pull-request validation uses the persistent single-architecture
`aos-pr-builder` instead of registry cache export. Buildx Bake links the five
payload targets directly into `full`, keeps their outputs cache-only, and loads
only `full` for the smoke check. Cleanup removes local image tags and prunes
that builder to a configured maximum size.

See also:

* [dev-base image](dev-base-image.md)
* [PR build validation](pr-dev-base-build-validation.md)
* [release workflow](release.md)

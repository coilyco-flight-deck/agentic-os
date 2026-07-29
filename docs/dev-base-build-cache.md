# dev-base build cache

Every multi-architecture image reuses a persistent Buildx builder on the
dedicated image runners. The publish action creates a builder only when it is
absent and recreates it only when bootstrap fails.

Each tier reads and writes its own `type=registry` cache:
`agentic-os:<tier>-buildcache` for specialists and
`agentic-os:buildcache` for full. A cache write uses `ignore-error=true`, so a
registry cache fault does not discard an otherwise valid image. The build
helper probes the cache manifest afterward and emits a warning when the write
did not land.

The workflow step summary records the cache key, source, destination, and
source-manifest provenance before the expensive build starts. A cold cache is
therefore visible as a cache event instead of only as a slow build.

Pull-request validation uses the persistent single-architecture
`aos-pr-builder` instead of registry cache export. Buildx Bake links the
specialist targets directly into `full`, keeps their outputs cache-only, and
loads only `full` for the smoke check. Every run removes its local image tags
and prunes that builder with a configured maximum cache size. The PR path keeps
warm layers but cannot perform the production multi-architecture cache
fan-out.

See also:

* [dev-base image](dev-base-image.md)
* [PR build validation](pr-dev-base-build-validation.md)
* [release workflow](release.md)

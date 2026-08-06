# Dev-base publish resume

The dev-base publish graph is artifact-resumable. A workflow dispatch accepts
a commit SHA, optional tag, and artifact selection. It checks the target
registry manifest first and skips any payload or full image whose exact
checkpoint already exists.

Selecting `full` builds any missing language payloads before the fan-in image.
Selecting one language rebuilds only that payload. Stable per-language
`buildcache` refs remain independent of commit-scoped draft tags, so a resumed
or later build can reuse layers produced on another runner or day.

An `all` or `full` resume continues into the root release after the full draft
passes verification. A single-language resume stops after that payload. The
separate release dispatch remains available for idempotent retag or metadata
recovery and explicit version overrides.

## Cross-architecture verification

Both publish modes verify the full tier by running one container per published
platform, so the foreign-architecture leg needs a binfmt handler. Build mode
installs it while setting up the buildx builder. Promote mode skips that setup
and runs on the `docker` runner rather than `docker-build`, so it inherits no
handler from a build-mode run and installs binfmt itself before verifying.

See also:

* [dev-base container image](dev-base-image.md)
* [Release pipeline](release.md)

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

## Verify before the tags move

Promote verifies the draft manifest by its source tag and only then stamps the
version tag and the moving `release` and `latest` aliases onto it. The draft is
already pushed and addressable at that point, so verification never needs the
release tags to exist. A verification failure therefore leaves the aliases on
the last image that passed, and promotion stays the final step, which is the
property that makes the job safe to retry.

Build mode verifies the draft it just pushed, because the image cannot be
verified before it exists. That ordering is safe because the build-mode publish
stamps only the commit-scoped draft tag, never a fleet alias.

## Cross-architecture verification

Both publish modes verify the full tier by running one container per published
platform, so the foreign-architecture leg needs a binfmt handler. Build mode
installs it while setting up the buildx builder. Promote mode skips that setup
and runs on the `docker` runner rather than `docker-build`, so it inherits no
handler from a build-mode run and installs binfmt itself before verifying.

See also:

* [dev-base container image](dev-base-image.md)
* [Release pipeline](release.md)

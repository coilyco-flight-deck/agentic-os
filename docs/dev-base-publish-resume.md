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

See also:

* [dev-base container image](dev-base-image.md)
* [Release pipeline](release.md)

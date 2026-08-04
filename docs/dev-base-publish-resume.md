# Dev-base publish resume

The dev-base publish graph is artifact-resumable. A workflow dispatch accepts
a commit SHA, optional tag, and artifact selection. It checks the target
registry manifest first and skips any payload or full image whose exact
checkpoint already exists.

Selecting `full` builds any missing language payloads before the fan-in image.
Selecting one language rebuilds only that payload. Stable per-language
`buildcache` refs remain independent of commit-scoped draft tags, so a resumed
or later build can reuse layers produced on another runner or day.

The release retry promotes only the full manifest. It accepts the same
commit-derived source tag, keeps retries idempotent through manifest checks,
and applies an explicit timeout to every promotion.

See also:

* [dev-base container image](dev-base-image.md)
* [Release pipeline](release.md)

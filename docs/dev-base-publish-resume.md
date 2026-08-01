# Dev-base publish resume

The dev-base publish path is tier-resumable. A workflow dispatch accepts a
commit SHA, optional tag, and tier. It checks the target registry manifest
first and skips any language or full image whose exact checkpoint already
exists. Selecting `full` builds any missing language prerequisites before the
fan-in image. Selecting one language rebuilds only that specialist.

The release retry accepts the same commit-derived source tag and promotes the
language manifests in parallel with the full manifest. Checkpoint inspection
keeps retries idempotent, and each build or promotion has an explicit timeout.

See also:

* [dev-base container image](dev-base-image.md)
* [Release pipeline](release.md)

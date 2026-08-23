#!/usr/bin/env bash
# Install Ward from its release artifacts, never from source. The image does the
# same in docker/dev-base/full/Dockerfile. See docs/aos-cli.md.
set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
ref="${1:-$(
  PYTHONPATH="${repo_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m agentic_os.prod_install_ref ward
)}"
out="${2:-/usr/local/bin/ward}"
tmpdir="$(mktemp -d)"

cleanup() {
  rm -rf "${tmpdir}"
}
trap cleanup EXIT

# The release publishes one binary per Linux architecture under its own name,
# so the runner's `uname -m` picks the asset rather than a build selecting it.
host_arch="$(uname -m)"
case "${host_arch}" in
  x86_64 | amd64) asset_arch=amd64 ;;
  aarch64 | arm64) asset_arch=arm64 ;;
  *)
    echo "unsupported architecture for the ward release: ${host_arch}" >&2
    exit 1
    ;;
esac

asset="ward-linux-${asset_arch}"
base="https://forgejo.coilysiren.me/coilyco-flight-deck/ward/releases/download/${ref}"
curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
  "${base}/${asset}" -o "${tmpdir}/${asset}"
curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
  "${base}/SHA256SUMS" -o "${tmpdir}/SHA256SUMS"
# Fails closed: an absent line makes grep exit non-zero under `set -e`, so a
# missing checksum is never the same as a passing one.
(cd "${tmpdir}" && grep "[[:space:]]${asset}\$" SHA256SUMS | sha256sum -c -)
install -m 0755 "${tmpdir}/${asset}" "${out}"
"${out}" --version

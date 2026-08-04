#!/usr/bin/env bash

set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
specgen_bin=${SPECGEN_BIN:-specgen}
if ! command -v "$specgen_bin" >/dev/null 2>&1; then
  tmpdir=$(mktemp -d)
  cleanup() {
    rm -rf "$tmpdir"
  }
  trap cleanup EXIT HUP INT TERM

  specgen_version=$(
    sed -n 's/^ARG SPECGEN_VERSION=//p' \
      "$repo_root/docker/dev-base/full/Dockerfile" | tr -d '\r'
  )
  if [ -z "$specgen_version" ]; then
    echo "Dockerfile does not pin specgen" >&2
    exit 1
  fi

  host_os=$(uname -s | tr '[:upper:]' '[:lower:]')
  case "$host_os" in
    linux) asset_os=linux ;;
    darwin) asset_os=darwin ;;
    mingw*|msys*|cygwin*) asset_os=windows ;;
    *)
      echo "unsupported host OS for specgen bootstrap: $host_os" >&2
      exit 1
      ;;
  esac
  host_arch=$(uname -m)
  case "$host_arch" in
    x86_64|amd64) asset_arch=amd64 ;;
    aarch64|arm64) asset_arch=arm64 ;;
    armv7l) asset_arch=armv7 ;;
    *)
      echo "unsupported host architecture for specgen bootstrap: $host_arch" >&2
      exit 1
      ;;
  esac
  asset="specgen-${asset_os}-${asset_arch}"
  if [ "$asset_os" = windows ]; then
    asset="${asset}.exe"
    specgen_path="$tmpdir/specgen.exe"
  else
    specgen_path="$tmpdir/specgen"
  fi

  base="https://forgejo.coilysiren.me/coilyco-flight-deck/cli-guard/releases/download/v${specgen_version}"
  curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
    "${base}/${asset}" -o "$tmpdir/$asset"
  curl --retry 5 --retry-all-errors --retry-delay 2 -fsSL \
    "${base}/SHA256SUMS" -o "$tmpdir/SHA256SUMS"
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$tmpdir" && grep "[[:space:]]${asset}$" SHA256SUMS | sha256sum -c -)
  else
    (cd "$tmpdir" && grep "[[:space:]]${asset}$" SHA256SUMS | shasum -a 256 -c -)
  fi
  mv "$tmpdir/$asset" "$specgen_path"
  chmod 0755 "$specgen_path"
  export PATH="$tmpdir:$PATH"
  specgen_bin="$specgen_path"
fi

uv run pytest
pre-commit run --all-files

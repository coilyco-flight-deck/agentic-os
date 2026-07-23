#!/bin/sh
# Cross-compile version-stamped aos binaries from the owning target manifest.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
targets="$repo_root/aos/release-targets.txt"
version=${AOS_RELEASE_VERSION:-$(
    git -C "$repo_root" describe --tags --exact-match --match 'aos-v*' 2>/dev/null ||
        git -C "$repo_root" rev-parse --short HEAD
)}
if [ -n "${AOS_RELEASE_DIST:-}" ]; then
    dist=$AOS_RELEASE_DIST
else
    dist="$repo_root/dist"
    rm -rf "$dist"
fi

checksum() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1"
    else
        shasum -a 256 "$1"
    fi
}

mkdir -p "$dist"

while IFS= read -r target || [ -n "$target" ]; do
    case "$target" in
        ""|\#*) continue ;;
    esac
    goos=${target%%/*}
    goarch=${target#*/}
    if [ "$goos" = "$target" ] || [ "$goarch" = "$target" ] ||
        [ -z "$goos" ] || [ -z "$goarch" ]; then
        echo "invalid release target: $target" >&2
        exit 1
    fi
    case "$goos/$goarch" in
        *[!a-z0-9/_-]*|*/*/*)
            echo "unsafe release target: $target" >&2
            exit 1
            ;;
    esac
    out="$dist/aos-${goos}-${goarch}"
    if [ "$goos" = "windows" ]; then
        out="${out}.exe"
    fi
    if [ -e "$out" ]; then
        echo "duplicate release output: $out" >&2
        exit 1
    fi
    (
        cd "$repo_root/aos"
        GOOS="$goos" GOARCH="$goarch" CGO_ENABLED=0 \
            go build -trimpath -ldflags "-s -w -X main.version=${version}" \
            -o "$out" .
    )
    echo "$out"
done < "$targets"

(
    cd "$dist"
    for asset in aos-*; do
        checksum "$asset"
    done > SHA256SUMS
)
echo "$dist/SHA256SUMS"
echo "version: $version"

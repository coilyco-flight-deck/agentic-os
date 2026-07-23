#!/bin/sh
# Verify checksums, package metadata, and the native release binary.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
dist=${AOS_RELEASE_DIST:-"$repo_root/dist"}
version=${AOS_RELEASE_VERSION:?AOS_RELEASE_VERSION is required}
bare=${version#aos-v}

(
    cd "$dist"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum -c SHA256SUMS
    else
        shasum -a 256 -c SHA256SUMS
    fi
)

target_count=$(awk '!/^[[:space:]]*(#|$)/ { count++ } END { print count+0 }' \
    "$repo_root/aos/release-targets.txt")
checksum_count=$(wc -l < "$dist/SHA256SUMS" | tr -d ' ')
if [ "$target_count" -ne "$checksum_count" ]; then
    echo "checksum count does not match release target count" >&2
    exit 1
fi

python3 -m json.tool "$dist/aos.json" >/dev/null
if command -v ruby >/dev/null 2>&1; then
    ruby -c "$dist/aos.rb" >/dev/null
fi
grep -F "version \"${bare}\"" "$dist/aos.rb" >/dev/null
grep -F "\"version\": \"${bare}\"" "$dist/aos.json" >/dev/null

case "$(uname -s)/$(uname -m)" in
    Darwin/arm64) native="$dist/aos-darwin-arm64" ;;
    Linux/x86_64) native="$dist/aos-linux-amd64" ;;
    Linux/aarch64 | Linux/arm64) native="$dist/aos-linux-arm64" ;;
    *) native="" ;;
esac
if [ -n "$native" ]; then
    actual=$("$native" version)
    if [ "$actual" != "$version" ]; then
        echo "native binary reports $actual, expected $version" >&2
        exit 1
    fi
fi

echo "verified aos release $version"

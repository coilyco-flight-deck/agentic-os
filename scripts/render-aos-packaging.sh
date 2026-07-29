#!/bin/sh
# Render Homebrew and Scoop metadata from the version-stamped aos binaries.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
dist=${AOS_RELEASE_DIST:-"$repo_root/dist"}
version=${AOS_RELEASE_VERSION:-$(
    git -C "$repo_root" describe --tags --exact-match --match 'aos-v*'
)}
bare=${version#aos-v}
base="https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/releases/download/${version}"

if ! printf '%s\n' "$version" | grep -Eq '^aos-v[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "aos release version must match aos-vMAJOR.MINOR.PATCH: $version" >&2
    exit 1
fi

sha() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum < "$1" | cut -d' ' -f1
    else
        shasum -a 256 < "$1" | cut -d' ' -f1
    fi
}

darwin_arm64=$(sha "$dist/aos-darwin-arm64")
linux_amd64=$(sha "$dist/aos-linux-amd64")
linux_arm64=$(sha "$dist/aos-linux-arm64")
windows_amd64=$(sha "$dist/aos-windows-amd64.exe")
aosguard_darwin_arm64=$(sha "$dist/aosguard-darwin-arm64")
aosguard_linux_amd64=$(sha "$dist/aosguard-linux-amd64")
aosguard_linux_arm64=$(sha "$dist/aosguard-linux-arm64")
aosguard_windows_amd64=$(sha "$dist/aosguard-windows-amd64.exe")

cat > "$dist/aos.rb" <<EOF
class Aos < Formula
  desc "Agent runtime composition root for Agentic OS"
  homepage "https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os"
  version "${bare}"
  license "MIT"

  on_macos do
    on_arm do
      url "${base}/aos-darwin-arm64"
      sha256 "${darwin_arm64}"
      resource "aosguard" do
        url "${base}/aosguard-darwin-arm64"
        sha256 "${aosguard_darwin_arm64}"
      end
    end
  end
  on_linux do
    on_intel do
      url "${base}/aos-linux-amd64"
      sha256 "${linux_amd64}"
      resource "aosguard" do
        url "${base}/aosguard-linux-amd64"
        sha256 "${aosguard_linux_amd64}"
      end
    end
    on_arm do
      url "${base}/aos-linux-arm64"
      sha256 "${linux_arm64}"
      resource "aosguard" do
        url "${base}/aosguard-linux-arm64"
        sha256 "${aosguard_linux_arm64}"
      end
    end
  end

  def install
    bin.install Dir["aos-*"].first => "aos"
    resource("aosguard").stage { bin.install Dir["aosguard-*"].first => "aosguard" }
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/aos version")
    assert_match version.to_s, shell_output("#{bin}/aosguard --version")
  end
end
EOF

cat > "$dist/aos.json" <<EOF
{
    "version": "${bare}",
    "description": "Agent runtime composition root for Agentic OS",
    "homepage": "https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os",
    "license": "MIT",
    "architecture": {
        "64bit": {
            "url": "${base}/aos-windows-amd64.exe",
            "hash": "${windows_amd64}",
            "bin": [
                ["aos-windows-amd64.exe", "aos"],
                ["aosguard-windows-amd64.exe", "aosguard"]
            ]
        }
    },
    "pre_install": [
        "Invoke-WebRequest -Uri '${base}/aosguard-windows-amd64.exe' -OutFile \"\$dir/aosguard-windows-amd64.exe\"; if ((Get-FileHash \"\$dir/aosguard-windows-amd64.exe\" -Algorithm SHA256).Hash -ne '${aosguard_windows_amd64}') { throw 'aosguard checksum mismatch' }"
    ]
}
EOF

echo "$dist/aos.rb"
echo "$dist/aos.json"

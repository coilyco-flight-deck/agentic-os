#!/usr/bin/env bash
# Set Warp as the default macOS app for prose and source files.
#
# Requires: macOS, Warp.app installed, `duti` on PATH (`brew install duti`).
#
# What it does:
#   1. Rebuilds the LaunchServices database so Warp's Info.plist claims
#      (CFBundleTypeExtensions: .go, .tsx, .cjs, ...) are picked up directly.
#   2. Sets Warp as the explicit handler for the UTIs and extensions that
#      LaunchServices won't infer from Warp's plist on its own.
#
# Known gap: .pyi stays bound to Apple's IDLE.app. Apple's Python framework
# registers a stronger claim than Warp's plist, and duti returns error -50 on
# the dynamic UTI macOS generates for the extension. Right-click -> Open With
# -> Warp still works.
#
# Idempotent. Safe to re-run.

set -uo pipefail

BUNDLE_ID="dev.warp.Warp-Stable"

if ! command -v duti >/dev/null 2>&1; then
  echo "duti not found. Install with: brew install duti" >&2
  exit 1
fi

if [ ! -d "/Applications/Warp.app" ]; then
  echo "Warp.app not found in /Applications. Install Warp first." >&2
  exit 1
fi

echo "==> Rebuilding LaunchServices database (this can take ~30s)..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
  -r -domain local -domain system -domain user

# Targets: UTI or extension. duti accepts both. Extensions without a registered
# UTI fall back to dynamic UTIs that duti can't bind; those are handled by the
# lsregister rebuild above via Warp's Info.plist claims.
TARGETS=(
  # markdown
  "net.daringfireball.markdown"

  # python
  "public.python-script"
  ".py"

  # go
  ".go"

  # javascript / typescript
  "com.netscape.javascript-source"
  ".js"
  ".mjs"
  ".cjs"
  ".jsx"
  ".ts"
  ".tsx"
  ".json"

  # plain text + generic source fallback
  "public.plain-text"
  "public.source-code"
  ".txt"
)

echo "==> Setting Warp as default handler..."
ok=0; fail=0
for t in "${TARGETS[@]}"; do
  if out=$(duti -s "$BUNDLE_ID" "$t" all 2>&1); then
    printf "  OK    %s\n" "$t"
    ok=$((ok+1))
  else
    printf "  SKIP  %s  (%s)\n" "$t" "$out"
    fail=$((fail+1))
  fi
done

echo
echo "==> Verifying current defaults:"
for ext in md py go js mjs cjs jsx ts tsx json txt; do
  printf "  .%-4s  %s\n" "$ext" "$(duti -x "$ext" 2>/dev/null | head -1)"
done

echo
echo "Done. $ok set explicitly, $fail relied on LaunchServices inference."
echo "Known gap: .pyi stays on IDLE.app. Right-click -> Open With -> Warp to override per-file."

#!/usr/bin/env bash
# Set Warp Preview as default macOS app for prose and source files.

set -uo pipefail

BUNDLE_ID="${WARP_DEFAULT_EDITOR_BUNDLE_ID:-dev.warp.Warp-Preview}"
APP_PATH="${WARP_DEFAULT_EDITOR_APP_PATH:-/Applications/WarpPreview.app}"

if ! command -v duti >/dev/null 2>&1; then
  echo "duti not found. Install with: brew install duti" >&2
  exit 1
fi

if [ ! -d "$APP_PATH" ]; then
  echo "$APP_PATH not found. Install with: ward pkg brew install --cask warp@preview --allow-untapped" >&2
  exit 1
fi

echo "==> Rebuilding LaunchServices database (this can take ~30s)..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
  -r -domain local -domain system -domain user

# UTI or extension. Extensions without a registered UTI fall back to lsregister.
TARGETS=(
  "net.daringfireball.markdown"
  "public.python-script"
  ".py"
  ".go"
  "com.netscape.javascript-source"
  ".js"
  ".mjs"
  ".cjs"
  ".jsx"
  ".ts"
  ".tsx"
  ".json"
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

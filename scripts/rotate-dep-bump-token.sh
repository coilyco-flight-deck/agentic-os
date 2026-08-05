#!/usr/bin/env bash
# Rotate the forgejo push token the dev-base auto-bump workflow uses
# (.forgejo/workflows/dep-bump.yml). The token is owned by the coilyco-ops bot,
# scoped write:repository, and lands in two places: SSM
# (/forgejo/coilyco-ops/dep-bump-token, the durable record) and the repo Actions
# secret DEP_BUMP_TOKEN (what the workflow's checkout pushes main with).
#
# Why this token exists: dep-bump pushes ARG bumps to main, and the resulting
# push must enqueue promotion and the dev-base publish chain so the image
# republishes. Some Forgejo versions suppress workflow runs from the auto-issued
# job token (the same anti-recursion guard GitHub applies), so a real-user PAT
# push is the reliable trigger. The token needs write:repository (push commits),
# not write:package like the registry token. See docs/dev-base-image.md
# ("Auto-bump").
#
# Mirrors scripts/rotate-registry-token.sh: forgejo only mints tokens via
# POST /users/{username}/tokens under HTTP basic auth, so this authenticates as
# the bot with /forgejo/coilyco-ops/password to mint, then uses the attended
# FORGEJO_ADMIN_TOKEN only to write the repo Actions secret. The minted token
# never reaches stdout. The guarded SSM surface requires a file source, so the
# token uses a mode-600 temporary file that the exit trap removes afterward.
set -euo pipefail

HOST="forgejo.coilysiren.me"
BOT_USER="coilyco-ops"
REPO="coilyco-flight-deck/agentic-os"
SECRET_NAME="DEP_BUMP_TOKEN"
SSM_PATH="/forgejo/coilyco-ops/dep-bump-token"
# Token names are unique per user; stamp the name so re-runs never collide.
TOKEN_NAME="dep-bump-push-$(date +%Y%m%d%H%M%S)"

api="https://${HOST}/api/v1"

aosguard_ssm() { aosguard ops aws ssm "$@"; }

admin_token="${FORGEJO_ADMIN_TOKEN:-}"
[ -n "$admin_token" ] || {
  echo "FORGEJO_ADMIN_TOKEN is required; load it with the attended infrastructure forgejo-admin-token helper" >&2
  exit 1
}
bot_password="$(aosguard_ssm get-parameter --name /forgejo/${BOT_USER}/password \
  --with-decryption --query Parameter.Value --output text)"
[ -n "$bot_password" ] || { echo "no /forgejo/${BOT_USER}/password in SSM" >&2; exit 1; }

echo "Minting write:repository token '${TOKEN_NAME}' for ${BOT_USER} ..."
mint_resp="$(curl -fsS -X POST \
  -u "${BOT_USER}:${bot_password}" \
  -H "Content-Type: application/json" \
  "${api}/users/${BOT_USER}/tokens" \
  -d "{\"name\":\"${TOKEN_NAME}\",\"scopes\":[\"write:repository\"]}")"

new_token="$(printf '%s' "$mint_resp" | python3 -c 'import sys,json; print(json.load(sys.stdin)["sha1"])')"
[ -n "$new_token" ] || { echo "mint returned no sha1" >&2; exit 1; }
echo "  minted (value withheld)"

secret_dir="$(mktemp -d)"
token_file="${secret_dir}/token"
trap 'rm -f "${token_file}"; rmdir "${secret_dir}"' EXIT
printf '%s' "$new_token" >"$token_file"
chmod 600 "$token_file"

echo "Stashing to SSM ${SSM_PATH} ..."
aosguard_ssm put-parameter --name "$SSM_PATH" --type SecureString \
  --value "file://${token_file}" --overwrite >/dev/null
echo "  stored"

echo "Setting repo Actions secret ${SECRET_NAME} on ${REPO} ..."
curl -fsS -X PUT \
  -H "Authorization: token ${admin_token}" \
  -H "Content-Type: application/json" \
  "${api}/repos/${REPO}/actions/secrets/${SECRET_NAME}" \
  -d "{\"data\":$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$new_token")}" >/dev/null
echo "  set"

echo "Done. The next dep-bump run pushes main as ${BOT_USER} and republishes the image."

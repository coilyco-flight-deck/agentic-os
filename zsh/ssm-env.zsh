# In-process AWS SSM secret loader. Ported from nu/ssm-env.nu.
#
# Pulls every SSM parameter under / from the named profile and loads
# them into the current zsh process environment. Never writes to disk.
#
# Var name derivation matches the nu version: /foo/bar-baz -> FOO_BAR_BAZ
#
# Usage (interactive):   ssm-load
# Usage (quiet, used by zshrc auto-load): ssm-load --quiet
# Usage (other profile): ssm-load other us-west-2
# Usage (one var only):  ssm-get /foo/bar-baz

ssm-load() {
  local quiet=0
  if [[ "$1" == "--quiet" ]]; then
    quiet=1
    shift
  fi
  local profile="${1:-default}"
  local region="${2:-us-east-1}"
  local json count
  json=$(AWS_PROFILE="$profile" AWS_REGION="$region" \
    aws ssm get-parameters-by-path --path "/" --recursive --with-decryption \
    --query 'Parameters[].{Name:Name,Value:Value}' --output json) || return 1
  while IFS=$'\t' read -r name value; do
    local key
    key=$(printf '%s' "${name#/}" | tr '/-' '__' | tr '[:lower:]' '[:upper:]')
    export "$key=$value"
  done < <(printf '%s' "$json" | jq -r '.[] | [.Name, .Value] | @tsv')
  count=$(printf '%s' "$json" | jq 'length')
  (( quiet )) || printf 'loaded %s SSM exports into env\n' "$count"
}

ssm-get() {
  local name="$1"
  local profile="${2:-default}"
  local region="${3:-us-east-1}"
  AWS_PROFILE="$profile" AWS_REGION="$region" \
    aws ssm get-parameter --name "$name" --with-decryption \
    --query 'Parameter.Value' --output text
}

#!/usr/bin/env bash
set -euo pipefail

fixture_owner="coilyco-flight-deck"
fixture_repo="ward-qa-fixture"
fixture_slug="${fixture_owner}/${fixture_repo}"
fixture_label="qa-fixture"
fixture_url="https://forgejo.coilysiren.me/${fixture_slug}.git"
preserve_on_failure=false
issue_number=""
action="run"

usage() {
  echo "usage: ward exec qa-verification-fixture -- [run [--preserve-on-failure] | bootstrap]" >&2
}

if [[ $# -gt 0 && "$1" != -* ]]; then
  action="$1"
  shift
fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    --preserve-on-failure)
      preserve_on_failure=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

bootstrap() {
  local label=""

  if ! aosguard ops forgejo repo get \
    "${fixture_owner}" "${fixture_repo}" \
    --query full_name \
    --output text >/dev/null 2>&1; then
    aosguard ops forgejo org-repo create \
      "${fixture_owner}" \
      --name "${fixture_repo}" \
      --auto_init \
      --default_branch main \
      --description "Disposable public fixture for bounded Ward director, engineer, and QA verification." \
      --readme Default >/dev/null
    echo "qa fixture: created ${fixture_slug}" >&2
  fi

  label="$(
    aosguard ops forgejo org-label list \
      "${fixture_owner}" \
      --limit 100 \
      --query "[?name=='${fixture_label}'].name | [0]" \
      --output text
  )"
  if [[ "${label}" != "${fixture_label}" ]]; then
    aosguard ops forgejo org-label create \
      "${fixture_owner}" \
      --name "${fixture_label}" \
      --color "7057ff" \
      --description "Disposable issue admitted to the bounded Ward QA verification lane." >/dev/null
    echo "qa fixture: created ${fixture_label} organization label" >&2
  fi

  echo "qa fixture: bootstrap ready" >&2
}

case "${action}" in
  bootstrap)
    if [[ "${preserve_on_failure}" == true ]]; then
      usage
      exit 2
    fi
    bootstrap
    exit 0
    ;;
  run)
    ;;
  *)
    usage
    exit 2
    ;;
esac

if ! aosguard ops forgejo repo get \
  "${fixture_owner}" "${fixture_repo}" \
  --query full_name \
  --output text >/dev/null 2>&1; then
  echo "qa fixture: ${fixture_slug} is missing; an authorized Ops session must run the tracked bootstrap subcommand" >&2
  exit 1
fi
label="$(
  aosguard ops forgejo org-label list \
    "${fixture_owner}" \
    --limit 100 \
    --query "[?name=='${fixture_label}'].name | [0]" \
    --output text
)"
if [[ "${label}" != "${fixture_label}" ]]; then
  echo "qa fixture: ${fixture_label} is missing; an authorized Ops session must run the tracked bootstrap subcommand" >&2
  exit 1
fi

cleanup() {
  local exit_status=$?
  local issue_ref=""
  local branch=""

  if [[ -z "${issue_number}" ]]; then
    return
  fi
  issue_ref="${fixture_slug}#${issue_number}"
  branch="issue-${issue_number}"

  ward agent stop "${issue_ref}" >/dev/null 2>&1 || true

  if [[ ${exit_status} -ne 0 && "${preserve_on_failure}" == true ]]; then
    echo "qa fixture: preserved ${issue_ref} and ${branch} after failure; the workload was stopped" >&2
    return
  fi

  if git ls-remote --exit-code --heads "${fixture_url}" "refs/heads/${branch}" >/dev/null 2>&1; then
    git push "${fixture_url}" --delete "${branch}"
  fi
  aosguard ops forgejo issue close \
    "${fixture_owner}" "${fixture_repo}" "${issue_number}" >/dev/null
  echo "qa fixture: cleaned ${issue_ref} and ${branch}" >&2
}
trap cleanup EXIT

started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
issue_title="Ward QA verification fixture ${started_at}"
issue_body="Append a section named \`Ward QA verification ${started_at}\` to README.md. Under it, state that the director, engineer, and QA fixture chain reached the remote branch. Commit and push only the deterministic issue branch. Do not open a pull request, merge, release, or deploy."

issue_number="$(
  aosguard ops forgejo issue create \
    "${fixture_owner}" "${fixture_repo}" \
    --title "${issue_title}" \
    --body "${issue_body}" \
    --query number \
    --output text
)"
if [[ ! "${issue_number}" =~ ^[1-9][0-9]*$ ]]; then
  echo "qa fixture: issue creation returned invalid number ${issue_number@Q}" >&2
  exit 1
fi

aosguard ops forgejo issue-label add \
  "${fixture_owner}" "${fixture_repo}" "${issue_number}" \
  --labels "${fixture_label}" \
  --labels headless \
  --labels P4 >/dev/null

issue_ref="${fixture_slug}#${issue_number}"
branch="issue-${issue_number}"
echo "qa fixture: created ${issue_ref}" >&2

if ward agent engineer \
  "${fixture_owner}/agentic-os#781" \
  --verification-fixture \
  --print >/dev/null 2>&1; then
  echo "qa fixture: non-fixture repository denial unexpectedly passed" >&2
  exit 1
fi

if ward agent engineer \
  "${issue_ref}" \
  --verification-fixture \
  --workflow merge-remote-main \
  --print >/dev/null 2>&1; then
  echo "qa fixture: merge workflow denial unexpectedly passed" >&2
  exit 1
fi

ward agent director \
  "${issue_ref}" \
  --burndown \
  --verification-fixture \
  --max-cycles 2 \
  --poll-interval 5s

branch_ready=false
for _ in $(seq 1 180); do
  if git ls-remote --exit-code --heads "${fixture_url}" "refs/heads/${branch}" >/dev/null 2>&1; then
    branch_ready=true
    break
  fi
  sleep 10
done
if [[ "${branch_ready}" != true ]]; then
  echo "qa fixture: ${branch} did not appear within 30 minutes" >&2
  exit 1
fi

ward agent qa "${issue_ref}" --verification-fixture

qa_comments="$(
  aosguard ops forgejo issue view \
    "${fixture_owner}" "${fixture_repo}" "${issue_number}" \
    --query "comments[].body" \
    --output text
)"
if ! grep -q "WARD-WORKFLOW: qa-done" <<<"${qa_comments}"; then
  echo "qa fixture: QA did not record a passing verdict on ${issue_ref}" >&2
  exit 1
fi

echo "qa fixture: director, engineer, and QA proof passed on ${branch}" >&2

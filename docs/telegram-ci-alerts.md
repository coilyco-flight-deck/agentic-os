# Telegram CI failure alerts

`actions/telegram-alert` is the reusable primitive for posting a high-priority
Telegram alert when a CI job fails on `main`. A push to canonical Forgejo
`main` publishes the action directly. Forgejo consumers use its fully qualified
URL, so action resolution does not depend on an instance-wide default or the
downstream GitHub mirror.

## Contract

- The caller passes `TELEGRAM_BOT_TOKEN` and `TELEGRAM_RED_CHAT_ID` as secrets.
- The action formats the repo, workflow, job, ref, commit SHA, and run URL.
- The message is plain text, so there is no markdown escaping surface.
- The sender honors `FORGEJO_EGRESS_PROXY` when the runner supplies it.
- The alert does nothing special on branches or pull-request refs. The caller
  gates it with `if: ${{ failure() && github.ref == 'refs/heads/main' }}`.

## Shape

```yaml
- name: Alert Telegram on main failure
  if: ${{ failure() && github.ref == 'refs/heads/main' }}
  continue-on-error: true
  uses: https://forgejo.coilysiren.me/coilyco-flight-deck/agentic-os/actions/telegram-alert@main
  with:
    bot-token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
    chat-id: ${{ secrets.TELEGRAM_RED_CHAT_ID }}
```

The action defaults `repo`, `workflow`, `job`, `ref`, `sha`, and `run-url`
from the GitHub / Forgejo context, so most call sites only pass the two secrets.
It also defaults the Telegram API base URL. The caller keeps
`continue-on-error: true`, so a Telegram outage does not obscure the job that
originally failed.

## Published defaults

[`defaults.json`](../actions/telegram-alert/defaults.json) is the
machine-readable rollout contract. It owns the canonical `uses:` URL, the
`main` ref, the non-fatal caller policy, both Actions secret names, and these
SSM sources:

- `TELEGRAM_BOT_TOKEN` from `/coilysiren/telegram/bot-token`
- `TELEGRAM_RED_CHAT_ID` from `/coilysiren/telegram/red-chat-id`

The action never receives AWS authority and never reads SSM during CI.
`ward exec sync-actions-secrets` reads the manifest and copies each value from
SSM into the repository's write-only Forgejo Actions secret. A rollout tool can
consume the same manifest instead of restating those deployment defaults.

The repo's own workflows inline the same payload so a failure before checkout
can still alert. The inline form follows the published message, proxy, and
redaction contract.

## Dry run

The helper script under the action path accepts `--dry-run` and prints the
message without posting. The unit tests use that path, so the test suite never
talks to Telegram.

## See also

- [features-release-tooling.md](features-release-tooling.md)
- [README.md](../README.md)

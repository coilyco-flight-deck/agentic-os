# Telegram CI failure alerts

`actions/telegram-alert` is the reusable primitive for posting a high-priority
Telegram alert when a CI job fails on `main`. The repo's own workflows inline
the same alert payload so failure-path notifications do not depend on local
action resolution in a stale mirror.

## Contract

- The caller passes `TELEGRAM_BOT_TOKEN` and `TELEGRAM_RED_CHAT_ID` as secrets.
- The action formats the repo, workflow, job, ref, commit SHA, and run URL.
- The message is plain text, so there is no markdown escaping surface.
- The send retries with backoff (3 attempts) before failing, so one flaky TLS
  handshake cannot eat the alert (aos#490). The inline workflow copies carry
  the same retry loop.
- The alert does nothing special on branches or pull-request refs. The caller
  gates it with `if: ${{ failure() && github.ref == 'refs/heads/main' }}`.

## Shape

```yaml
- name: Alert Telegram on main failure
  if: ${{ failure() && github.ref == 'refs/heads/main' }}
  uses: coilyco-flight-deck/agentic-os/actions/telegram-alert@main
  with:
    bot-token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
    chat-id: ${{ secrets.TELEGRAM_RED_CHAT_ID }}
```

The action defaults `repo`, `workflow`, `job`, `ref`, `sha`, and `run-url`
from the GitHub / Forgejo context, so most call sites only pass the two secrets.
The inline workflow version follows the same message contract.

## Dry run

The helper script under the action path accepts `--dry-run` and prints the
message without posting. The unit tests use that path, so the test suite never
talks to Telegram.

## See also

- [features-release-tooling.md](features-release-tooling.md)
- [README.md](../README.md)

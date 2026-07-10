# Telegram CI failure alerts

`actions/telegram-alert` is the reusable primitive for posting a high-priority
Telegram alert when a CI job fails on `main`.

## Contract

- The caller passes `TELEGRAM_BOT_TOKEN` and `TELEGRAM_RED_CHAT_ID` as secrets.
- The action formats the repo, workflow, job, ref, commit SHA, and run URL.
- The message is plain text, so there is no markdown escaping surface.
- The action does nothing special on branches or pull-request refs. The caller
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

## Dry run

The helper script under the action path accepts `--dry-run` and prints the
message without posting. The unit tests use that path, so the test suite never
talks to Telegram.

## See also

- [features-release-tooling.md](features-release-tooling.md)
- [README.md](../README.md)

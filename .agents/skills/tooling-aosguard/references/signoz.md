# SigNoz and CI alerting

`aosguard ops signoz` exposes the approved SigNoz MCP read surface through
fixed mcporter calls. Each command addresses exactly one tool on the
pre-authenticated `signoz` server selected by AOS convergence. Forgejo,
kubectl, and server evidence remain separate operator command families.

## Commands

The guarded surface groups the deployed tools as follows:

* `metrics list|query|top|usage|cardinality`
* `fields keys|values`
* `alerts active|rules|get|history`
* `dashboards list|get|templates`
* `services list|operations`
* `views list|get`
* `docs search|fetch`
* `logs aggregate|search`
* `traces aggregate|search|get`
* `channels list`

`aosguard ops signoz --help` lists the groups, and each group has its own
`--help` inventory with leaf descriptions. The SigNoz MCP tool schema remains
authoritative for argument names, required fields, defaults, limits, and
validation.

## Arguments

Pass simple native MCP arguments as `key=value` tokens:

```text
aosguard ops signoz services list timeRange=30m limit=1
```

mcporter also coerces JSON-shaped values for native array arguments:

```text
aosguard ops signoz metrics usage 'metricNames=["metric.one","metric.two"]'
```

`--help` is the only caller-controlled flag. The KDL policy fixes `mcporter
call`, the `signoz.<tool>` selector, and JSON output for every leaf. Flags
that could replace the server, tool, configuration, transport, headers, or
output are not exposed.

## Configuration and boundary

AOS convergence writes the selected MCP inventory to
`~/.mcporter/mcporter.json`. mcporter resolves the fixed `signoz` entry
from that inventory. A command fails if the server is unavailable, the tool is
not deployed, or SigNoz rejects its native arguments. There is no fallback to
Forgejo, kubectl, or a server shell.

The deployed MCP allowlist intentionally omits
`signoz_execute_builder_query` and `signoz_get_notification_channel`.
AOSguard has no leaves for either tool.

## Telegram CI failure alerts

`aosguard ops telegram alert` posts a CI or CD failure to the in-cluster
`signoz-telegram` mapper. It is the target shape for every repo: one verb, no
arguments, and no alert program checked into any repository.

## Shape

```yaml
- name: Alert Telegram on main failure
  if: ${{ failure() && github.ref == 'refs/heads/main' }}
  continue-on-error: true
  run: aosguard ops telegram alert
```

The message is exactly three lines:

```
coilyco-bridge/deploy CI failing
workflow: deploy-galaxy-gen
run: https://forgejo.coilysiren.me/coilyco-bridge/deploy/actions/runs/4821
```

## Contract

- The caller passes nothing. Every field is read from the runner's own
  `GITHUB_*` environment, and a missing one degrades to `?` rather than
  raising, because a partial alert beats no alert.
- `ALERT_KIND=CD` switches the first line for a deploy job. `REPO`, `WORKFLOW`,
  `RUN_URL`, `FORGE_URL`, and `ALERT_URL` override their defaults.
- The run link is built from the forge `ROOT_URL`. `GITHUB_SERVER_URL` is the
  cluster-local name the runner registered against, so a link built from it is
  unreachable from a phone.
- No caller holds a Telegram credential. The mapper resolves the API base URL
  and chat id from pod environment.
- The leaf is `sealed`, so it forwards its pinned command exactly and takes no
  trailing arguments. The program is embedded in the binary rather than read
  from disk.
- Alert delivery is non-blocking. Keep `continue-on-error: true` so a mapper
  outage cannot obscure the job that originally failed.

## Availability

The verb needs `aosguard` on the job. Every workflow that sets
`container: forgejo.coilysiren.me/coilyco-flight-deck/agentic-os:release` has
it. A job on the `deploy:host` executor does not, because host-executor steps
run in the runner pod rather than that image.

## Migration

The verb replaces four hand-rolled implementations of this alert across the
fleet. Consumers migrate only after it ships in a released image, so the
sequencing is: land the verb, let the image republish, then move call sites.
The rollout, and the list of what is left to move, lives in
`coilyco-flight-deck/infrastructure`.

# SigNoz reads

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

## See also

* [AOSguard](aosguard.md)
* [AOS convergence](aos-convergence.md)
* [Forgejo Actions logs](forgejo-actions-logs.md)

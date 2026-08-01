# SigNoz logs

`aosguard ops signoz logs` searches bounded log records through the
pre-authenticated SigNoz MCP server selected by AOS convergence. The command
reads SigNoz only. Forgejo, kubectl, and server evidence remain separate
operator command families.

## Command

```text
aosguard ops signoz logs \
  [--query EXPR] \
  [--service NAME] \
  [--severity LEVEL] \
  [--search-text TEXT] \
  [--time-range DURATION | --start UNIX_MS --end UNIX_MS] \
  [--limit N] \
  [--offset N] \
  [--max-bytes N]
```

The command calls only the SigNoz MCP `signoz_search_logs` tool. It emits the
tool result as JSON on stdout. Diagnostics go to stderr, and failures leave
stdout empty so callers never mistake a partial response for log data.

## Bounds

* Query window - defaults to `1h` and accepts at most seven days.
* Result count - defaults to 100 records and accepts at most 1,000.
* Pagination - accepts an offset from zero through 1,000,000.
* Response size - defaults to 4 MiB and accepts at most 16 MiB.
* Inputs - query and search fields have fixed length limits before transport.

Relative queries use `--time-range`. Absolute queries require both `--start`
and `--end` as Unix milliseconds. The two forms cannot be combined.

## Configuration

AOS convergence writes the selected MCP inventory to
`~/.mcporter/mcporter.json`. This command resolves the fixed `signoz` entry
from that inventory and accepts no endpoint override. The entry must use an
HTTP or HTTPS URL and may carry converged request headers.

The command fails closed when the inventory is absent, the `signoz` entry is
missing or malformed, the MCP exchange fails, or the response exceeds the
configured byte bound. It never falls back to Forgejo, kubectl, or a server
shell.

## Examples

Search recent error records for one service:

```text
aosguard ops signoz logs --service forgejo-runner --severity error --time-range 30m
```

Search an absolute window with deterministic pagination:

```text
aosguard ops signoz logs \
  --search-text "job failed" \
  --start 1785542400000 \
  --end 1785546000000 \
  --limit 100 \
  --offset 100
```

## See also

* [AOSguard](aosguard.md)
* [AOS convergence](aos-convergence.md)
* [Forgejo Actions logs](forgejo-actions-logs.md)

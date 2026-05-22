---
name: coding-shape-observability
description: Category umbrella for observability work. Kai's professional spine - Datadog, Prometheus, Grafana, Sentry, CloudWatch, New Relic across multiple employers. Current edge is OTel + LLM consumers (luca substrate). Metrics + traces + logs as a unified surface. Triggers - observability, o11y, monitoring, metrics, traces, logs, datadog, prometheus, grafana, sentry, cloudwatch, new relic, opentelemetry, otel, fluent-bit, fluentd, vector, loki, tempo, jaeger, victoriametrics.
---

# coding-shape-observability

Umbrella for any observability work. Spans metrics, traces, logs, dashboards, alerting, SLOs.

## Vendor familiarity (from resume)

- **Datadog** - Textio (custom Datadog + Fluent-bit setup), Bluelink-adjacent.
- **New Relic** - Kapwing, Nava.
- **Prometheus + Grafana** - homelab default, also Textio-adjacent.
- **Sentry** - personal stack, every coilysiren/* service ships a DSN.
- **CloudWatch** - whenever AWS-native is the right reach.
- **OpenTelemetry** - current edge of work, see luca substrate.

## Defaults

- **Metrics**: Prometheus exposition format. RED method for services (Rate, Errors, Duration), USE for resources (Utilization, Saturation, Errors).
- **Traces**: OpenTelemetry. Span-per-tool-call when instrumenting agent code. luca consumes spans via VictoriaMetrics + per-session buffers.
- **Logs**: structured JSON. One event per line. Correlation IDs in every line.
- **Dashboards**: Grafana for personal, vendor-native (Datadog/New Relic) when an employer pays for it.
- **Alerting**: SLO-driven. Burn-rate alerts on multi-window, multi-burn-rate (Google SRE workbook).
- **Errors**: Sentry. DSN per service in SSM (`/sentry-dsn/<project>` convention).

## LLM consumers are first-class

Kai's current edge: design observability for LLM consumers, not human dashboards. Raw event streams accessible via MCP. luca is the canonical example - MCP tools (`luca-inspect`, `tooling-luca-meta-loop`) consume the substrate, not just humans visiting Grafana.

When designing new observability surfaces, ask: how does an LLM agent consume this? If the answer is "open Grafana and look", that's incomplete.

## Anti-patterns

- Logging at every function boundary (logspam, useless).
- Metrics without dashboards (write-only telemetry).
- Dashboards without alerts (read-only telemetry).
- Alerts without runbooks (paging without action).
- Per-employer vendor lock that doesn't transfer (favor OTel and standard exposition formats).

## When this skill is active

Designing instrumentation, building dashboards, configuring alerts, debugging via observability surfaces, or wiring a new service into the o11y stack.

## See also

- [`tooling-luca-meta-loop`](../../../../luca/skills/tooling-luca-meta-loop/SKILL.md) - the LLM-consumer substrate.
- [`coding-shape-web-server`](../coding-shape-web-server/SKILL.md) - `/metrics` endpoint conventions.
- `agentic-os-kai/SSM.md` - `/sentry-dsn/*` parameter inventory.

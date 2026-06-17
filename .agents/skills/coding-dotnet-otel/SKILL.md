---
name: coding-dotnet-otel
description: Concrete C#/.NET OpenTelemetry tracing - ActivitySource spans, OTLP export, semantic tags, .NET 8 vs Framework 4.8 split. Triggers - otel, opentelemetry, ActivitySource, span, OTLP, instrument .net.
---

# .NET / C# OpenTelemetry instrumentation

The concrete instrumentation layer under [coding-shape-observability](../coding-shape-observability/SKILL.md) (the observability umbrella) and [coding-csharp](../coding-csharp/SKILL.md) (the C# umbrella). Use when wiring traces into a C# service or an Eco modkit game-server mod, where the .NET Framework path matters as much as modern .NET.

## Core APIs

- **`ActivitySource`** - one per service/component. `source.StartActivity(name, kind)` opens a span.
- **`Activity`** - the span. `SetTag()`, `RecordException()`, `SetStatus()` add context.
- **`ActivityKind`** - `Server` (incoming), `Client` (outgoing), `Internal`, `Producer`, `Consumer`.
- Always null-check: `activity` is null when disabled, sampled out, or no listener is registered. Use `activity?.SetTag(...)` and `using var activity = ...` for disposal.

## Setup - the .NET 8 vs Framework 4.8 split

**ASP.NET Core (.NET 8):**

- `builder.Services.AddOpenTelemetry().WithTracing(t => t.AddAspNetCoreInstrumentation().AddHttpClientInstrumentation().AddSource("YourService").AddOtlpExporter())`.
- Endpoint from `OTEL_EXPORTER_OTLP_ENDPOINT`. HTTP server + client spans are then automatic.

**ASP.NET / .NET Framework 4.8 (the Eco-mod-relevant path):**

- Build the provider in `Application_Start()` via `Sdk.CreateTracerProviderBuilder()`.
- Sampler: `TraceIdRatioBasedSampler(arg)` - watch locale-specific decimal parsing (`"0,1"` must become `0.1`).
- Wrap init in try/catch - **a telemetry misconfig must never crash the host**.
- No auto-instrumentation: open Activities manually at HTTP boundaries (`Application_BeginRequest` / `Application_EndRequest`) and for SOAP/WCF via an `IClientMessageInspector` (`BeforeSendRequest` -> `AfterReceiveReply`).

## OTLP exporter config

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=1.0   # dev 100%, prod <=0.1
```

## Semantic tags (OTel conventions)

- **HTTP** - `http.method`, `http.url`, `http.status_code`, `http.route`, `net.peer.name`.
- **DB** - `db.system`, `db.name`, `db.operation`, `db.statement` (sanitized), `db.rows_affected`.
- **RPC/SOAP** - `rpc.system`, `rpc.service`, `rpc.method`, `rpc.status_code`.
- **Errors** - `error` (bool), `error.type`, `error.message`; `activity?.RecordException(ex)` then `SetStatus(ActivityStatusCode.Error, msg)`.
- **Never tag** - passwords, tokens, API keys, full payloads.

## Patterns

- **Helper class** (e.g. `TraceabilityHelper`) for consistent tag names + null checks across the codebase.
- **Business ops** - parent Activity with child Activities per sub-step; let exceptions propagate and record on the owning span.
- **Status** - `ActivityStatusCode.Ok` on success, `.Error` with a message on failure.

## Feature gating

Gate all instrumentation behind an `OTEL_ENABLED` env var checked at startup. When off, return null Activities and let callers no-op - the mod ships dark by default and lights up only where wanted.

## See also

- Distilled from [`whitebeardit/.cursor`](https://github.com/whitebeardit/.cursor) `skills/dotnet/skill-opentelemetry-instrumentation` (MIT, community-maturity) - not vendored.
- [coding-shape-observability](../coding-shape-observability/SKILL.md) - the observability umbrella.
- [coding-csharp](../coding-csharp/SKILL.md) - the C# umbrella.

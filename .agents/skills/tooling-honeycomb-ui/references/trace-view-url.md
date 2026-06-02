# Trace-view URL surface

Parallel to the `?query=<json>` knob on the dataset query builder, the trace view has its own URL surface that is more useful for the human-readability iteration loop this skill exists to support. Three knobs:

1. **Base shape**:
   ```
   https://ui.honeycomb.io/<team>/environments/<env>/datasets/<dataset>/trace?trace_id=<hex>
   ```
   The `/trace/<view-id>/` segment Honeycomb stamps into the URL after interaction is a server-side view-state token. Drop it from shareable URLs, it isn't needed and changes per session.

2. **`fields[]=<col>&fields[]=<col>...`** replaces the default `Name / Service Name` columns in the waterfall table with arbitrary span attribute columns. Honeycomb auto-prefixes `c_` server-side, so `fields[]=shot.result` becomes `c_shot.result` in the canonical URL. Either form works on input.

   Sharp edge: a single `fields[]` set applies to every row, so on heterogeneous-span traces, picking columns for the common span type blanks out the cells for outlier span types. The right-pane Fields panel adapts per focused span and is the escape hatch. Pick the columns that read best for the common case, accept that outliers will look empty in the table, and let the reader click the outlier to see its actual fields in the right pane.

3. **`span=<hex>`** pre-focuses a specific span. The right-pane Fields panel renders that span's attributes immediately, which is how you make a deep-link land on "the thing that matters" instead of "the first span in the trace."

Worked example, battleships, pre-focusing the dominant TIMED_OUT engagement with shot-shaped columns:

```
.../datasets/battleships/trace?trace_id=<hex>&fields[]=shot.result&fields[]=shot.row&fields[]=shot.col&span=<engagement-span-id>
```

Shot rows render as `MISS | 1 | 9 | 1.092s` (highly scannable). The focused row is empty in the table because engagement spans don't carry `shot.*`. The right pane fills in with `engagement.outcome=TIMED_OUT` etc. because focus adapts per span.

Repo-side recipe with workshop worked examples lives at `coilysiren/honeycomb-battleships/docs/sharing-traces.md` (see honeycomb-battleships#29).

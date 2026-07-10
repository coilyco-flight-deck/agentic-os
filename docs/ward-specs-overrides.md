# Ward Spec Overrides

The per-harness `agent <name> { ... }` overlay lives in `.ward/roles.kdl`.
`director`, `advisor`, and `ops` retune `claude` and `codex` there with
per-harness `model` and `reasoning-effort` overrides.

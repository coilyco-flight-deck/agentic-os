# How to invoke `cargo` / `npm` / etc. above board

The environment routes package-manager actions through `coily` to enforce argv validation and audit logging. Bare `cargo` / `npm` / `pip` / `gem` / `bundle` / `pnpm` / `yarn` / `pipx` / `poetry` / `uv` are denied at the lockdown layer. Use the wrapper:

```sh
coily pkg cargo fetch
coily pkg cargo build
coily pkg cargo test
coily pkg npm install
coily pkg pip install <pkg>
```

The wrappers are thin pass-throughs - they take the same args verbatim and only enforce shell-metachar and audit-log discipline. Use them whenever you would have used the bare binary. This applies to every package-manager step in this audit (e.g. `coily pkg cargo audit`, `coily pkg cargo deny check`).

The deny exists because adding a dep means executing untrusted build scripts on the user's machine. The audit (this skill) and the wrapper-based execution are complementary: the audit answers "should this code run at all," the wrapper records "when it ran and what it asked for."

# Build script and proc-macro red flags

Build scripts run on every consumer's machine, with the consumer's full environment. They are the highest-leverage attack surface in a package, and the most commonly missed during review. Read every build script before approving a dep.

## Rust: `build.rs`

Run:

```sh
gh api repos/<owner>/<name>/contents/build.rs --jq '.content' | base64 -d
```

Also check workspace member crates: each subcrate can have its own `build.rs`.

### Patterns that are normal

- Calling `cc::Build::new()` to compile bundled C/C++ sources
- Using `prost-build` / `tonic-build` to generate code from `.proto`
- Reading `OUT_DIR` and writing generated `.rs` files there
- Re-running on `rerun-if-changed=...` for source files
- Detecting target features via `cargo:rustc-cfg=...`
- Reading `CARGO_*` env vars

### Patterns that are red flags

- `reqwest::get(...)`, `ureq::get(...)`, `curl`, `wget`, `std::net::TcpStream` - network calls during build. Pinning a downloaded artifact's sha256 and erroring on mismatch is acceptable for, say, bundled platform binaries (e.g. tree-sitter grammars) but the artifact URL must be a domain you trust. Anonymous-CDN downloads are red.
- `std::fs::write` to paths outside `OUT_DIR` (writing to the user's home dir, /tmp, /etc, etc.).
- `std::process::Command::new("sh")` / `bash` / `cmd` / `powershell` - shelling out at build time. Especially red if the args come from env vars or downloaded data.
- Reading `~/.ssh/`, `~/.aws/`, `~/.config/`, `~/.kube/`, env vars matching `*TOKEN*` / `*SECRET*` / `*KEY*` / `AWS_*` / `GITHUB_*`.
- Base64-decoding or hex-decoding a hardcoded blob, then executing it.
- Writing files into `~/.cargo/registry/` or `~/.cargo/bin/`.
- Conditional behavior based on user/host (`whoami`, `hostname`, `$USER`) - almost always benign, but if combined with any of the above, escalate.

## Rust: proc-macro crates

Proc macros run inside `rustc` at compile time. A malicious proc macro can read your filesystem and embed the result in the compiled artifact (or just write to disk).

Find them via `[lib] proc-macro = true` in the dep's Cargo.toml, or via path-deps with `proc-macro` in the name. Read the macro's source.

Same red flags as `build.rs`. Additional flags specific to proc macros:

- `std::fs::read_to_string` of a path outside `CARGO_MANIFEST_DIR` and current crate sources.
- `std::env::var` on anything beyond `CARGO_*` and the standard rustc-set vars.
- Network calls (extremely red - proc macros should not need the network).

## Other ecosystems

npm install hooks, Python `setup.py` / `pyproject.toml` build hooks, Go `go:generate` and `init()`, the cargo feature-hidden-payload baseline, and the quick command set continue in [`build-script-redflags-ecosystems.md`](build-script-redflags-ecosystems.md).

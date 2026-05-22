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

## npm: `scripts.preinstall` / `install` / `postinstall`

Run on `npm install` / `pnpm install` / `yarn install` of *any* downstream consumer. Read these from `package.json`.

### Normal

- Running a known build tool: `node-gyp rebuild`, `tsc`, `vite build`
- Setting permissions on bundled binaries: `chmod +x ./bin/foo`
- Generating types from a schema

### Red flags

- `curl ... | sh` / `wget ... | bash` - pipe-to-shell from anywhere. Always red.
- Downloading binaries from non-publisher domains.
- Writing to `~/.bashrc`, `~/.profile`, `~/.zshrc`, or any global config.
- Reading `~/.npmrc`, `~/.aws/`, `~/.ssh/`, env tokens.
- Encoded blobs decoded then exec'd (the eslint-scope / event-stream pattern).
- Posting to a remote endpoint with hostname/user info "for telemetry" - even when benign, this is the typosquat attacker's exfil path.

## Python: `setup.py` and `pyproject.toml` build hooks

Modern projects favor `pyproject.toml` and a build backend (`setuptools`, `hatchling`, `flit`, `poetry-core`, `pdm-backend`) over a custom `setup.py`. A custom `setup.py` with non-trivial code is itself a yellow flag (rare in well-maintained projects); read every line.

Pip can run arbitrary code at install via:

- `setup.py` top-level statements
- A custom build backend that does anything beyond reading/writing source files
- Entry-point scripts auto-installed into the user's PATH (`[project.scripts]`)

Red flags:

- `subprocess.run(["sh", "-c", ...])` in setup.py
- Network calls in setup.py outside of a documented "compile a known artifact" path
- `__import__` of unusual names
- Writes to `~/.config/`, `~/.local/`, `/etc/`

## Go: `go:generate` and `init()`

Go is mostly safe-by-default at build time (the `go build` toolchain doesn't run user code), but watch for:

- `go:generate` directives that shell out to non-standard tools. These run on `go generate`, not `go build`, but contributors often run both.
- `init()` functions in published packages that do anything beyond simple registration. Init runs on `import`, in any consumer.

## Cargo features that hide build behavior

Some malicious crates have hidden their payload behind a non-default feature. The audit baseline is: read the crate as if every feature were enabled. If a feature called `experimental` or `unstable` does network IO at build time, document that, even if the consumer won't enable it.

## Quick command set

```sh
# List all build.rs in a Rust workspace
gh api repos/<owner>/<name>/git/trees/<branch>?recursive=1 --jq '.tree[] | select(.path | endswith("build.rs")) | .path'

# Read each
for path in $(...); do
  gh api repos/<owner>/<name>/contents/$path --jq '.content' | base64 -d
done

# List proc-macro crates in workspace
grep -lA1 "proc-macro = true" $(find . -name Cargo.toml)

# npm install hooks
gh api repos/<owner>/<name>/contents/package.json --jq '.content' | base64 -d \
  | python3 -c "import sys,json; s=json.load(sys.stdin).get('scripts',{}); [print(k,'->',v) for k,v in s.items() if 'install' in k]"
```

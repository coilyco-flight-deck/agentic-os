# Pinned Rust toolchains

The Rust payload installs `stable` as its default and additionally bakes every
toolchain in `RUST_PINNED_VERSIONS`, a space-separated list declared in
[`docker-bake.hcl`](../docker/dev-base/docker-bake.hcl) and threaded to both
Dockerfiles.

This exists because a consumer pinning a channel in `rust-toolchain.toml`
otherwise downloads it from `static.rust-lang.org` on the first cargo call of
every CI run. That request has no cache, and when the runner's egress to that
host degrades, every Rust repo goes red on a network fault rather than on its
own code. galaxy-gen#84 is the worked example: three retries over ten minutes
all timed out from inside the runner while the same URL answered in 0.16s from
outside.

Each baked toolchain gets `clippy`, `rustfmt`, and the
`wasm32-unknown-unknown` target. **The components are the point** - baking a
bare toolchain still leaves rustup fetching components at first use, which is
the same download in a different place. The full image verifies each pin end to
end and fails if the list arrives empty, so an unplumbed build arg cannot make
that check a silent pass.

Adding a pin is one edit to the `RUST_PINNED_VERSIONS` default. Consumers keep
owning their own `rust-toolchain.toml`; this only decides what is already
resident when they ask.

## See also

* [dev-base image](dev-base-image.md)
* [CI parity](ci-in-dev-base.md)

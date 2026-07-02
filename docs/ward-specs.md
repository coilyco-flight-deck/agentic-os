# Ward Spec Bundle

`ward-specs/` is the aos-hosted deployment bundle for ward's coilyco build
input. It carries the forgejo guardfile, the signoz and ollama guardfiles, the
fleet manifest, and the spec locks the ward build consumes.

The bundle is the canonical deployment source for the ward-side flip. Ward now
copies it from the sibling `agentic-os/ward-specs/` checkout before locking and
embedding.

See [../ward-specs/README.md](../ward-specs/README.md).

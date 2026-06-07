# agentic-os

![Sombra hacking skull](static/wallpaper.jpg)

Cross-platform shell + terminal setup plus the cross-repo pre-commit hooks that keep coilysiren/* repos in shape. Zsh on Mac, Linux, and Windows (Git Bash). Warp on Mac and Windows; both configs (`warp/settings.toml`, `warp/tab_configs/startup_config.toml`) symlinked into `~/.warp/`.

## Layout

- `zsh/` - cross-platform shell config: `zshrc` entry, `env.zsh`, per-host `hosts/<os>.zsh`, `config.zsh`, and the in-process SSM secret loader `ssm-env.zsh`.
- `warp/` - Warp config (`settings.toml`, `tab_configs/`) plus the `coily exec warp` Go module.
- `scripts/` - portable utilities (gpg-ssm signing wrapper, agent-name + session-pulse hooks, aws-config lint, verbatim-echo).
- `.agents/skills/` - SKILL.md docs for the configs that live here. agentic-os-kai's `setup.sh` walks this dir as a peer skill source.
- `agentic_os/` - the catalog pre-commit hooks this repo ships and dogfoods.

Full breakdown: [docs/repo-layout.md](docs/repo-layout.md).

## Install

```bash
./setup.sh                # zsh + gpg-ssm symlinks
coily exec warp apply     # warp config (see docs/warp.md)
```

`setup.sh` is idempotent. It detects the host via `uname -s`, symlinks `~/.zshrc` and the gpg-ssm wrapper, and wires the agent self-name plus session-pulse hooks into `~/.claude/settings.json`. Pre-existing real files are backed up to `<path>.bak` on first run. Per-host steps and the git gpg wiring: [docs/install.md](docs/install.md).

## Secrets pattern

The current pattern keeps secrets off disk entirely:

```bash
ssm-load                          # pull every / parameter into the current shell env
ssm-get /eco/server-api-token     # fetch one value without storing it
```

No disk write at any point. Same call works on Mac, Linux, Windows. AWS profile defaults to `default`; override with `ssm-load <profile> <region>`. For secrets at shell startup, append `ssm-load` to the end of `zsh/config.zsh`. The legacy cleartext-on-disk dump (`~/.cache/ssm-env.sh`) was deleted.

## agent-compose

Opt-in tooling that composes global agent context and symlinks each harness load point to it. Sources are shared unless optional `harnesses` frontmatter selects a harness-specific slice. Inert until `~/.config/agent-compose/agent-compose.yaml` exists. See [docs/FEATURES.md](docs/FEATURES.md).

**Prior art.** The idea is fresh in the agentic space but well-trodden in config management, and agent-compose is best understood as **Hiera-for-agent-doctrine, deployed Stow-style, scoped chezmoi-style**:

- **[GNU Stow](https://www.gnu.org/software/stow/)** - symlink-farm manager. The "one canonical file, N symlinks" deployment mechanism.
- **[chezmoi](https://www.chezmoi.io/)** - dotfile manager with per-machine targeting. The model for scoping context to each host.
- **[Hiera](https://github.com/puppetlabs/hiera)** (Puppet) - hierarchical, scope-based data lookup. The conceptual twin of the machine-scope intersection that selects which sources compose.

**Naming.** The field's vocabulary is **weave / layer / compose / overlay / blend**. We chose `compose` over the working name `meld`, which collides with [GNOME Meld](https://meldmerge.org/) on both search and semantics.

## Credits

- `static/wallpaper.jpg` - Sombra hacking skull, from the [Overwatch](https://overwatch.blizzard.com) Sombra ARG promotional materials, Blizzard Entertainment, circa 2016. All Overwatch art and iconography © Blizzard Entertainment. Used here for personal terminal decoration only.

## See also

- [AGENTS.md](AGENTS.md) - public-safe agent operating conventions and the global load point.
- [docs/FEATURES.md](docs/FEATURES.md) - inventory of what ships today.
- [.coily/coily.yaml](.coily/coily.yaml) - allowlisted dev commands. Agents route through coily.

Cross-reference convention from [coilysiren/agentic-os#59](https://github.com/coilysiren/agentic-os/issues/59).

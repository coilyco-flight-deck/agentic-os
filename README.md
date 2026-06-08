# agentic-os

![Sombra hacking skull](static/wallpaper.jpg)

Cross-platform shell + terminal setup plus the cross-repo pre-commit hooks that keep coilysiren/* repos in shape. Zsh on Mac, Linux, and Windows (Git Bash). Warp on Mac and Windows; both configs (`warp/settings.toml`, `warp/tab_configs/startup_config.toml`) symlinked into `~/.warp/`.

## Layout

- `shell/` - cross-platform shell config. Shared `common.sh` (env, per-host PATH, aliases, git helpers, SSM loader) sourced by thin `zshrc` + `bashrc`, so bash and zsh match. `warp.zsh` is the zsh-only Warp dispatcher.
- `warp/` - Warp config (`settings.toml`, `tab_configs/`) plus the `coily exec warp` Go module.
- `scripts/` - portable utilities (gpg-ssm wrapper, agent-name + session-pulse hooks, aws-config lint).
- `.agents/skills/` - SKILL.md docs for the configs that live here. agentic-os-kai's skill mount walks this dir as a peer skill source.
- `agentic_os/` - the catalog pre-commit hooks this repo ships.

Full breakdown: [docs/repo-layout.md](docs/repo-layout.md).

## Install

Host config is converged by Ansible (the rollout lives in the infrastructure repo, per the authoring-vs-rollout split in [AGENTS.md](AGENTS.md)). Manual fallback:

```bash
ln -sf "$PWD/shell/zshrc"  ~/.zshrc      # both source shell/common.sh
ln -sf "$PWD/shell/bashrc" ~/.bashrc
ln -sf "$PWD/scripts/gpg-ssm" ~/.local/bin/gpg-ssm
coily exec warp apply                     # warp config
```

Agent self-name + session-pulse hooks, per-host steps, and gpg wiring: [docs/install.md](docs/install.md).

## Secrets pattern

The current pattern keeps secrets off disk entirely:

```bash
ssm-load                          # pull every / parameter into the current shell env
ssm-get /eco/server-api-token     # fetch one value without storing it
```

No disk write at any point. Same call works on Mac, Linux, Windows. AWS profile defaults to `default`; override with `ssm-load <profile> <region>`. For secrets at shell startup, append `ssm-load` to the end of `shell/common.sh`. The legacy cleartext-on-disk dump (`~/.cache/ssm-env.sh`) was deleted.

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

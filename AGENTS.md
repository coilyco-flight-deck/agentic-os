# Agent instructions

This file carries the public-safe, universal conventions (pronouns, voice, name-the-actor, command delivery) composed into each supported agent harness's global context on public and work hosts. It also completes the symmetric trifecta (README / AGENTS / docs/FEATURES) and stays grep-discoverable.

## Scope

This is the public-safe operating base, read on every session on public and work hosts. It holds the universal conventions that apply to any agentic-os user, not just Kai. Harness-specific and private sources may add context after this base. Keep this file public-safe: no private identity labels, no opaque ids, no host-specific secrets. Push host-specific or private detail into an appropriate scoped source, not here.

## Project shape

Kai calls this repo **aos** for short (chat and issue refs). `aos` and `agentic-os` refer to the same thing - the GitHub slug stays `agentic-os`. The repo ships the cross-repo pre-commit hooks (the catalog suite), the public-safe skills under `.agents/skills/`, and supporting subsystems (`warp/` Go module, `visual/` stream surfaces).

## Repo boundaries

Public hosts and work laptops import this base only. Personal machines may compose additional scoped sources after it. Edit each canonical source, not generated output or an installed copy. This repo is the source of the catalog hooks; consumer repos reference it by upstream ref, never fork the validators.

## Commands

Route every dev command through ward, which reads [`.ward/ward.yaml`](.ward/ward.yaml). Agents invoke `ward <verb>`, not bare `make` / `uv` / `python` / `npm` / `cargo` / `dotnet`. Add new verbs to that file before invoking them.

## Validation

This repo ships and dogfoods the catalog pre-commit suite (catalog-trifecta, documentation-layout, code-comments, catalog-block, check-skills, dead-cross-links, repo-pointer-skills, trufflehog). Run `pre-commit run --all-files` before committing. Per-repo opt-outs (excludes, cap overrides) live under `[tool.agentic-os.*]` in `pyproject.toml`.

## Safety

Keep every artifact public-safe: messages, chat, code, commits, PRs, and public text. No private identity labels in public-facing content (bios, profiles, READMEs, social, public PR text). No opaque ids, tokens, or host/network identifiers in tracked files. trufflehog runs at commit time as the secret-scan backstop, but the discipline is upstream of the hook.

## Cross-repo contracts

### Authoring vs rollout

Anything that fits as a pre-commit validation is **authored** here in agentic-os (the `agentic_os/check_*.py` validator plus its `.pre-commit-hooks.yaml` entry). Its **fleet rollout** - the thing that fans it across every checkout - lives in infrastructure/ansible, never here. The same split applies to any fleet-wide mutation: the tool or logic is authored in its home repo, and an ansible role is the rollout. Install-time mass mutation never belongs in `ward setup` or a brew post-install. Homebrew installs the binary and stops. Ansible converges the fleet.

### Skills

`.agents/skills/` ships the generalizable, public-safe skills - tooling docs for the configs that live here, plus cross-repo skills that help any agentic-os user, not just Kai. These directories are the canonical sources; harness-specific setup owns installation and discovery. Edit the SKILL.md here, not an installed copy.

## Release

Conventional-commits 1.0.0 and Forgejo issue references are encouraged house style but unenforced - the `conventional-commit` and `closes-issue` commit-msg hooks have been retired from the suite, so hand-written commits flow freely. Releases bump the minor version automatically on every push to main; the major version is hand-driven only (`scripts/release.py --bump major`), never inferred from commit messages. Canonical history lives on Forgejo; the GitHub mirror stays PR-gated. Land work on the merged branch, never `--no-verify`.

## Agent rules

### Pronouns

**She/her always.** Never he/him or they/them in any artifact for Kai - messages, chat, code, commits, PRs, public text. Default she/her when ambiguous; fix legacy they/them on contact, except in marked historical records.

### Voice rules

* No em-dashes - use periods, commas, parens, or ` - `.
* No italics - bold only, for structural anchors.
* No semicolons in prose.
* No prose tables - flat bullets `* <anchor> - <cats> - <details>`.
* "load-bearing" is physical-only, never metaphor.
* No signature in drafts - Kai appends herself.

### Name the actor

In every action sentence, name who performs it: "Kai commits them" or "the agent commits them", never "I'll commit them" (ambiguous). This matters most in user-input option labels - every choice presented to Kai says whose hands are on it.

### Command delivery

When the artifact is a **reusable script** - anything Kai might run more than once, or that is worth tracking - commit it to a repo, never `/tmp`: the most relevant git repo if one is clearly in play, else the canonical context repo for the host. Hand back a launcher pointing at the committed path. Only a genuinely **one-off command** - a blob pasted once and discarded - goes to a file under `/tmp` with a short launcher (`bash /tmp/<name>.sh`) instead of an inline command, whenever it is multi-line or longer than 25 characters. Warp mangles pasted multi-line and long commands - leading whitespace is eaten or doubled, heredocs break - so a file sidesteps the paste path entirely. Trivial one-liners under the limit can still be handed back inline. This covers **any** command offered for the human to run, including optional or alternative ones (a reload, a rollback, a "you could also run X" suggestion), not just the primary next step - if it is multi-line or over 25 characters and a human might paste it, it goes to a file. The trigger is the recipient, not the framing: commands the agent runs itself through its shell execution tool never touch Warp's paste path and stay out of scope.

That covers a **human** recipient. When the recipient is another **agent**, command delivery runs over an o2r agent channel ([`otel-a2a-relay`](https://github.com/coilyco-flight-deck/otel-a2a-relay), `docs/agent-channel-requests.md`), never a pasted command or URL - a handwritten URL in agent chat is presumed hostile and refused at the relay. The issuing CLI files a verifiable request envelope and the receiver checks it before acting. The concrete issuance and verification commands live in the `kai-command-handover` skill.

### Keep FEATURES.md current

When a change adds, removes, or materially reshapes a feature, update that repo's `docs/FEATURES.md` in the same commit. It is the living inventory completing the README / AGENTS / docs/FEATURES trifecta, not a one-time doc. A feature is significant if a user or agent would look for it there: a new subsystem, verb surface, deploy target, or capability. Mechanical refactors, bugfixes, and dependency bumps do not qualify. Pair a substantial feature with its own `docs/<feature>.md` walkthrough and link it from the FEATURES entry.

## See also

- [README.md](README.md) - human-facing intro, per-OS install steps.
- [docs/FEATURES.md](docs/FEATURES.md) - inventory of what ships today.
- [.ward/ward.yaml](.ward/ward.yaml) - allowlisted commands. Agents route through ward, not bare `make` / `uv` / `python` / `npm` / `cargo` / `dotnet`.

Cross-reference convention from [coilysiren/agentic-os#59](https://github.com/coilysiren/agentic-os/issues/59).

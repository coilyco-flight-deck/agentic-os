# Changelog

## [0.3.0](https://github.com/coilysiren/agentic-os/compare/v0.2.3...v0.3.0) (2026-05-20)


### Features

* add claude-dispatch-interactive Warp launch config ([fed1496](https://github.com/coilysiren/agentic-os/commit/fed149643f8b4a6c7a0194d7852df402d96ce32f)), closes [#105](https://github.com/coilysiren/agentic-os/issues/105)
* **hammerspoon:** Wispr Flow auto-submit in Warp, closes [#95](https://github.com/coilysiren/agentic-os/issues/95) ([be26896](https://github.com/coilysiren/agentic-os/commit/be26896e34e243d774669a467515a9c5e2cbd286))
* run Warp Preview as the Mac daily-driver channel ([5c7f35a](https://github.com/coilysiren/agentic-os/commit/5c7f35ac53a9d0da0f456e013eca6bd69f5bfceb)), closes [#107](https://github.com/coilysiren/agentic-os/issues/107)
* **warp:** add claude-dispatch-interactive tab_config ([1f960db](https://github.com/coilysiren/agentic-os/commit/1f960db0eedbbac4793a92488f301a92866d7fe7))
* **warp:** default editor binding script, closes [#98](https://github.com/coilysiren/agentic-os/issues/98) ([b09ca44](https://github.com/coilysiren/agentic-os/commit/b09ca449ba09ea2e6c7e9e206ec8362affe02a69))
* **warp:** echo `<ref>: <title>` self-id header before exec claude, closes [#119](https://github.com/coilysiren/agentic-os/issues/119) ([4d84514](https://github.com/coilysiren/agentic-os/commit/4d84514d6dd797391c78d3411435a3c7dc4b77d6))
* **warp:** enable login item, closes [#96](https://github.com/coilysiren/agentic-os/issues/96) ([e706650](https://github.com/coilysiren/agentic-os/commit/e70665089b5d49f2ac9d537ea7a7986fd36b5faf))
* **warp:** header chips, zoom 125, kai-server subshell, session cwd config ([aef9a20](https://github.com/coilysiren/agentic-os/commit/aef9a207a3267d7a2111560e613be092b7fadcd4)), closes [#91](https://github.com/coilysiren/agentic-os/issues/91)
* **warp:** launch &lt;name&gt; &lt;tab-args&gt; runs a single tab's script, closes [#101](https://github.com/coilysiren/agentic-os/issues/101) ([eb4817d](https://github.com/coilysiren/agentic-os/commit/eb4817d35d76128e1206eae2c343213655b20d5e))
* **warp:** launch configurations and zsh helper, closes [#97](https://github.com/coilysiren/agentic-os/issues/97) ([ce09257](https://github.com/coilysiren/agentic-os/commit/ce09257973449618a6a5613d4c8efa2f7d2d25f5))
* **warp:** per-repo edit tabs replace third scratch tab in claude-luca ([be7f4eb](https://github.com/coilysiren/agentic-os/commit/be7f4ebd3ff01ebe779e46c8e4211044603fa58f)), closes [#103](https://github.com/coilysiren/agentic-os/issues/103)
* **warp:** render-warp-paths.py for cross-host theme/wallpaper paths, closes [#120](https://github.com/coilysiren/agentic-os/issues/120) ([4faafce](https://github.com/coilysiren/agentic-os/commit/4faafce2b7c82abec2716ade7d9f1aa725520aa0))
* **warp:** warp tab subverb + tab_config URI pattern docs, closes [#123](https://github.com/coilysiren/agentic-os/issues/123) ([642d467](https://github.com/coilysiren/agentic-os/commit/642d467f1918fd4046a8d5058e7e988595951072))
* **zsh:** auto-cd interactive shells into ~/projects/coilysiren, closes [#117](https://github.com/coilysiren/agentic-os/issues/117) ([9d0310c](https://github.com/coilysiren/agentic-os/commit/9d0310cbcd61e4add2c4c9ee56662173cbdf3a7b))
* **zsh:** auto-run ssm-load at interactive shell startup ([1ec3a02](https://github.com/coilysiren/agentic-os/commit/1ec3a026c478cea5d19a97dc42d53d7f7c607d33)), closes [#102](https://github.com/coilysiren/agentic-os/issues/102)
* **zsh:** export BAT_PAGER="" to suppress bat's pager ([18ed5d7](https://github.com/coilysiren/agentic-os/commit/18ed5d7cbd2338c82ee2a87b8b878ab2da25675c)), closes [#92](https://github.com/coilysiren/agentic-os/issues/92)


### Bug Fixes

* **skills:** strip mangle variants from tooling-mcp-servers triggers ([ff2686d](https://github.com/coilysiren/agentic-os/commit/ff2686de96f9363e8f99cde9456ce50225cb983b)), closes [#111](https://github.com/coilysiren/agentic-os/issues/111)
* **warp:** render-warp-paths: lambda repl for backslash paths, robust git lookup ([f9100f5](https://github.com/coilysiren/agentic-os/commit/f9100f50568c44061ac474d4fcb7ab0091e0cfde))
* **warp:** rewrite dispatch shim to FIFO queue + jq parse ([576f7a7](https://github.com/coilysiren/agentic-os/commit/576f7a7a580efc6a043e2e0b0978d312cb982439))
* **warp:** tab_config commands take bare strings not inline tables ([21a3cbe](https://github.com/coilysiren/agentic-os/commit/21a3cbe734882e5fcbd0dba32b7fb4816976700a))


### Reverts

* **zsh:** drop eager ssm-load at shell startup, leaked too many secrets ([f7e16c5](https://github.com/coilysiren/agentic-os/commit/f7e16c5d0c33db11615c212475b1949b754c0dc1)), closes [#104](https://github.com/coilysiren/agentic-os/issues/104)


### Documentation

* **FEATURES:** rewrite as capability description ([3a37d54](https://github.com/coilysiren/agentic-os/commit/3a37d547a3c9df59430d033887b30998f4eedeaa)), closes [#82](https://github.com/coilysiren/agentic-os/issues/82)
* **tooling-mcp-servers:** document cross-cwd resolution + merge wire-up ([1adddf0](https://github.com/coilysiren/agentic-os/commit/1adddf074aad659cdef88b51d7a4bdfb567b506c)), closes [#93](https://github.com/coilysiren/agentic-os/issues/93)
* **tooling-mcp-servers:** mention honeycomb intelligence mcp server, closes [#127](https://github.com/coilysiren/agentic-os/issues/127) ([3d3f7c2](https://github.com/coilysiren/agentic-os/commit/3d3f7c26fd9ac484580033d5f9972ef9f2ccb278))
* **warp:** correct tab_config URI handler build-date claim ([bde5981](https://github.com/coilysiren/agentic-os/commit/bde59810bbbd0dd4dfe2a0f066b378204e9008f5))
* **warp:** replace placeholder examples in tab_config READMEs, closes [#124](https://github.com/coilysiren/agentic-os/issues/124) ([1863a23](https://github.com/coilysiren/agentic-os/commit/1863a23b6fc9d9146c1b136f259332e2a01b5d1f))

## [0.2.3](https://github.com/coilysiren/agentic-os/compare/v0.2.2...v0.2.3) (2026-05-16)


### Documentation

* repoint archived claude-skill-discipline refs to coilysiren/agentic-os ([0030b1c](https://github.com/coilysiren/agentic-os/commit/0030b1c05a9061c51cb5054474182d265a600fde)), closes [#71](https://github.com/coilysiren/agentic-os/issues/71)
* skill-authoring co-location uses apply-agentic-os-hooks ([b3b21da](https://github.com/coilysiren/agentic-os/commit/b3b21da3b7cbc7dea481d00deb4c5e98cfab0a06)), closes [#73](https://github.com/coilysiren/agentic-os/issues/73)
* strip historical-context prose per agentic-os-kai[#574](https://github.com/coilysiren/agentic-os/issues/574) ([ff55668](https://github.com/coilysiren/agentic-os/commit/ff556683d43b0a4d1a1a243dd97a8a96c90bff81)), closes [#68](https://github.com/coilysiren/agentic-os/issues/68)

## [0.2.2](https://github.com/coilysiren/agentic-os/compare/v0.2.1...v0.2.2) (2026-05-16)


### Bug Fixes

* catalog-trifecta accepts .agent-guard/agent-guard.yaml as catalog yaml ([54da912](https://github.com/coilysiren/agentic-os/commit/54da912092b66868ef56dba3dc03b4fa0cdb1302))
* rollout skips agentic-os itself, drop duplicate upstream-ref block ([4a2e7cf](https://github.com/coilysiren/agentic-os/commit/4a2e7cf27ee896a07863e3e3f8cd77ec0bc93d1c))

## [0.2.1](https://github.com/coilysiren/agentic-os/compare/v0.2.0...v0.2.1) (2026-05-16)


### Bug Fixes

* validate-skills + dead-cross-links no-op on missing .claude/skills/ ([c77f884](https://github.com/coilysiren/agentic-os/commit/c77f884d370b44d0c2e360768bdab204659017d9))

## [0.2.0](https://github.com/coilysiren/agentic-os/compare/v0.1.0...v0.2.0) (2026-05-16)


### Features

* auto-versioning via release-please + conventional-commit hook ([c79260d](https://github.com/coilysiren/agentic-os/commit/c79260dca6ee29d7310dca9720278ef775ded1b0))

# Weekly-priorities menu-bar banner (SwiftBar)

A native macOS menu-bar item showing your week's top-3 priorities, always visible
on every space. Built on [SwiftBar](https://github.com/swiftbar/SwiftBar), which
renders an executable plugin's stdout as a menu-bar item that macOS lays out for
you (so it dodges the notch and other items with no pixel-tuning).

## What you see

In the menu bar, between the app menus and the status icons:

```
ship release / fix flaky tests / write docs
```

Click it for the full descriptions (one line each, no repeated label), plus
actions to **Edit prios** (opens the file), open this **Guide**, and **Refresh**:

```
1. cut the 2.0 release and announce it
2. track down and fix the three flaky CI tests
3. write the getting-started guide
```

(Those are illustrative - your actual priorities come from your own file.)

A priority line naming a repo (the optional third field, below) is clickable - it opens `https://forgejo.coilysiren.me/<owner>/<repo>`.

## Editing the priorities

The priorities are a plain file, one per line, in
`label :: description :: owner/repo` form - the short label drives the menu-bar
title (its first word), the description fills the dropdown, and the optional
third field links the line to that Forgejo repo. The last two fields are
optional. The first three non-empty lines show:

```
ship release :: cut the 2.0 release and announce it :: coilyco-flight-deck/agentic-os
fix flaky tests :: track down and fix the three flaky CI tests :: coilyco-flight-deck/infrastructure
write docs :: write the getting-started guide
```

```sh
$EDITOR ~/.config/prios.txt
```

The plugin re-reads it every 30s (the `30s` in the filename), so no restart is
needed. This file is the source of truth and is intentionally not tracked in the
repo, so it stays local and can be driven by whatever updates your weekly plan.

## How it is wired

- `swiftbar/prios.30s.sh` - the canonical plugin. Emits the menu-bar title plus a
  `---`-separated dropdown. The `30s` refresh interval is encoded in the filename.
- SwiftBar's plugin folder is `~/.config/swiftbar`, and the plugin inside it is a
  symlink to the repo file (`~/.config/swiftbar/prios.30s.sh` ->
  `<repo>/swiftbar/prios.30s.sh`), so the repo stays the source of truth.

The plugin folder must contain only plugin files - point SwiftBar at a dedicated
`~/.config/swiftbar`, never at a docs or source directory, or it will try to run
every file there as a plugin.

The menu-bar title is plain ASCII with `/` separators because the macOS menu bar
font renders emoji and some punctuation as missing-glyph boxes (the dropdown is a real menu and renders unicode fine).

## Install (per host)

```sh
brew install --cask swiftbar
mkdir -p ~/.config/swiftbar
ln -sfn <repo>/swiftbar/prios.30s.sh ~/.config/swiftbar/prios.30s.sh
defaults write com.ameba.SwiftBar PluginDirectory ~/.config/swiftbar
defaults write com.ameba.SwiftBar MakePluginExecutable -bool false
open -a SwiftBar
```

Note the bundle id is `com.ameba.SwiftBar`. Turning off `MakePluginExecutable`
stops SwiftBar from chmod-ing files in the plugin folder. Then enable "Launch at
Login" from SwiftBar's menu so it survives a reboot. Fleet rollout of these steps
belongs in infrastructure/ansible, not here.

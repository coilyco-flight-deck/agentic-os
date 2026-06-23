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

Click it for the full numbered list and an "Edit prios" shortcut:

```
1. ship release
2. fix flaky tests
3. write docs
```

(Those are illustrative - your actual priorities come from your own file.)

## Editing the priorities

The priorities are a plain file, one per line; the first three non-empty lines
are shown (the menu-bar title uses each line's first word):

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

## Title is ASCII-only

The macOS menu bar font renders emoji and some punctuation (for example the
middle dot) as missing-glyph boxes, so the menu-bar title is plain ASCII with
`/` separators. The dropdown is a real menu and renders unicode fine.

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

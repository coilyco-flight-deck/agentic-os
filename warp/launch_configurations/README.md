# Warp launch configurations

YAML files in this directory are auto-loaded by Warp when symlinked into `~/.warp/launch_configurations/`. Each file defines one window with one or more tabs.

Profile-specific design notes live as a comment block at the top of the YAML itself. This README is the cross-profile reference.

## Launching

- URI: `warp://launch/<name>` (where `<name>` matches the file's `name:` field).
- Shell: `open warp://launch/<name>`.
- The `warp launch` zsh helper in this repo wraps that plus a control-cmd-f keystroke to fullscreen, since the schema has no window-state field.

## Schema

| Key | Where | Notes |
| --- | --- | --- |
| `name` | top-level | Config identifier. Matches the URI. |
| `active_window_index` | top-level | Which window starts focused. |
| `windows[].active_tab_index` | window | Which tab starts focused. Alternative to per-tab `is_active`. |
| `tabs[].title` | tab | Initial title. Warp's auto-rename may overwrite. |
| `tabs[].color` | tab | `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`. **Lowercase only.** |
| `tabs[].is_active` | tab | Boolean. Sets focused tab at launch. |
| `tabs[].layout.cwd` | layout | **Absolute path only.** `~` and empty string don't work. |
| `tabs[].layout.commands[].exec` | layout | Shell command. Chain with `&&`. |
| `tabs[].layout.split_direction` | layout | `vertical` or `horizontal`. For pane splits. |
| `tabs[].layout.panes[]` | layout | Nested splits. Each pane accepts `cwd`, `commands`, `is_focused`, `split_direction`. |

## Sharp edges

- **No per-tab `env:` field.** Workaround: prepend `VAR=value` or `export VAR=value && cmd` to the exec string.
- **A tab cannot launch a GUI app as the tab itself.** `open -a Foo ...` spawns a side window; the tab stays a shell.
- **No CLI hook for Warp's built-in editor / markdown viewer.** Workaround: print clickable file paths and click them.
- **Commands chain with `&&`.** Anything after an `ssh` may not execute.
- **`cwd` must be absolute.** No `~`.
- **`color:` values are lowercase.** Capitalized values silently reject the entire config with no error.
- **Auto-rename can stomp `title`.** Disable in Settings -> Features -> Session, or prepend `printf '\033]0;TITLE\007'` to the exec.
- **No fullscreen / window-state field.** Use the `warp launch` zsh helper for full-screen behavior.

## Docs

- [Launch Configurations](https://docs.warp.dev/features/sessions/launch-configurations)
- [URI Scheme](https://docs.warp.dev/terminal/more-features/uri-scheme)
- [All settings reference](https://docs.warp.dev/terminal/settings/all-settings)

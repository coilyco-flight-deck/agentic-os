# Crash-resilient Alacritty workspace

Alacritty owns the window, rendering, and keyboard transport. Zellij owns tabs,
panes, and the long-lived terminal session. Closing or crashing an Alacritty
client therefore leaves the shell processes and their working directories in
the Zellij server.

The default session is named `main`. Every ordinary Alacritty window attaches
to it, creating it only when it does not exist. Zellij uses its native tab bar,
so the terminal keeps its full width instead of reserving a sidebar.

## Daily controls

The direct shortcuts make the move from a GUI terminal less abrupt:

* `Ctrl+Shift+T` creates a tab.
* `Ctrl+Tab` and `Ctrl+Shift+Tab` move between tabs.
* `Alt+1` through `Alt+9` select a tab directly.
* `Ctrl+Shift+D` splits down.
* `Ctrl+Shift+E` splits right.
* `Ctrl+Shift+F` toggles the focused pane full screen.
* `Ctrl+Q` detaches the client and leaves the session running.

Zellij's native modal controls remain available. `Ctrl+T` enters tab mode,
`Ctrl+P` enters pane mode, and `Ctrl+O` enters session mode. The one-row status
bar shows the actions available in the active mode.

Dragging over terminal text selects and copies it. Hold `Shift` while using the
mouse when an application inside a pane needs the raw mouse event.

## Recovery

Opening Alacritty after a client crash reattaches to `main`. If the Zellij
server itself stopped, the next launch creates `main` and Zellij offers any
serialized sessions through its session manager. Pane viewports and up to
10,000 scrollback lines are serialized once per second.

To leave the workspace alive, detach with `Ctrl+Q` or close the Alacritty
window. Killing the Zellij session is an explicit administrative action.

## Ownership

[`zellij/config.kdl`](../zellij/config.kdl) owns portable behavior and keyboard
bindings. Infrastructure installs Zellij, adds the native Git Bash path, and
renders the host-local Alacritty entry point.

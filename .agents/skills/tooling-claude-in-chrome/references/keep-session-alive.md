# Keep the session alive

Two rules keep a Claude-in-Chrome session usable.

## 1. JS over mouse

The `computer` tool (mouse clicks, typing) frequently errors with `Cannot access a chrome-extension:// URL of different extension`. Cause: another Chrome extension (1Password, Find Unreplied, etc.) holds activeTab focus, and `chrome.debugger` cannot attach across extensions. The error wedges every subsequent call in that tab.

Use `mcp__Claude_in_Chrome__javascript_tool` instead:

* `find` + ref clicks - avoid, they go through the mouse path.
* `form_input` - sometimes works, but React-controlled inputs ignore it (the value change doesn't fire React's onChange).
* `javascript_tool` calling `el.click()` - reliable.

## 2. Never leave a form dirty

If a form has unsaved state and you navigate or close-tab, Chrome shows the native **"Leave site? Changes you made may not be saved."** modal. The extension cannot dismiss it. Every subsequent call errors until the user clicks Leave by hand.

Recovery: ask the human to click Leave. Prevention: only ever leave a form by submitting it (the post-submit redirect counts as a clean exit) or by clearing every input you touched before navigating.

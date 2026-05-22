---
name: tooling-claude-in-chrome
description: Drive the live Chrome browser via the Claude_in_Chrome MCP for web automation on logged-in sessions. Use JS over mouse (mouse trips a chrome-extension boundary that wedges the session), never leave a form dirty (Chrome's "Leave site?" modal blocks the extension until dismissed). Triggers - claude in chrome, chrome mcp, browser automation, remote browser, drive chrome, browser_batch, javascript_tool, scrape page, Codex environments, "different extension" error, Leave site dialog.
---

# claude-in-chrome

The `mcp__Claude_in_Chrome__*` MCP attaches to a live local Chrome via the Claude in Chrome extension. Real auth, real cookies, real session state. Use it when a target has no usable API and clicking through is the only option (Codex env creation, OpenAI settings, recruiter portals, vendor dashboards).

## When to reach for it

* The site has no public/working API for the action.
* The action depends on a logged-in browser session that lives only in the user's Chrome.
* The repetition count is high enough that a checklist isn't faster (rough rule: 8+ identical clicks).

If fewer than ~5 clicks, just hand the user a checklist with deep links. Browser automation has setup cost.

## Two rules that keep the session alive

### 1. JS over mouse

The `computer` tool (mouse clicks, typing) frequently errors with `Cannot access a chrome-extension:// URL of different extension`. Cause: another Chrome extension (1Password, Find Unreplied, etc.) holds activeTab focus, and `chrome.debugger` cannot attach across extensions. The error wedges every subsequent call in that tab.

Use `mcp__Claude_in_Chrome__javascript_tool` instead:

* `find` + ref clicks - avoid, they go through the mouse path.
* `form_input` - sometimes works, but React-controlled inputs ignore it (the value change doesn't fire React's onChange).
* `javascript_tool` calling `el.click()` - reliable.

### 2. Never leave a form dirty

If a form has unsaved state and you navigate or close-tab, Chrome shows the native **"Leave site? Changes you made may not be saved."** modal. The extension cannot dismiss it. Every subsequent call errors until the user clicks Leave by hand.

Recovery: ask the user to click Leave. Prevention: only ever leave a form by submitting it (the post-submit redirect counts as a clean exit) or by clearing every input you touched before navigating.

## React-controlled input pattern

Setting `.value` directly doesn't trigger React's controlled-component update. Use the native setter so React sees the input event:

```js
const inp = document.querySelector('input[placeholder="Search"]');
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
setter.call(inp, 'whatever-you-want');
inp.dispatchEvent(new Event('input', {bubbles: true}));
```

Then wait 2-3 seconds for the async filter/query to settle before reading the resulting DOM.

## Reliable per-row flow

For a list-driven UI (Codex env creation, GitHub repo picker), the loop is:

1. `navigate` to the create/form URL.
2. `wait` 4s.
3. `javascript_tool` to set the search input (native-setter pattern).
4. `wait` 2-3s for the filtered results.
5. `javascript_tool` to find the matching row button and `.click()` it. Match on `button.textContent.trim()` - the visible text is often label-concatenated (e.g. `homebrew-tapPublic` with no space).
6. `javascript_tool` to find the submit button by exact text and `.click()` it. Guard against `.disabled`.
7. `wait` 5s for the redirect.
8. `javascript_tool` returning `location.pathname` to verify the success URL (typically not `/create`).

Each iteration ends on a clean page state (post-submit redirect), so the next `navigate` doesn't trip the Leave-site modal.

## When the session wedges anyway

Symptoms: every call returns `Cannot access a chrome-extension:// URL of different extension` even though `tabs_context_mcp` works.

In order of cost:

1. `select_browser` with the deviceId from `list_connected_browsers` - sometimes nudges the session back. Cheap, try first.
2. Ask the user to click on the target tab to refocus it, and dismiss any extension popup.
3. Ask the user to **Cmd+Q Chrome** and relaunch, then reattach the Claude in Chrome extension by clicking its toolbar icon. The Bash path to quit Chrome (`osascript ... quit`) is in the harness deny list.

Don't loop on a wedged session - it stays wedged until human intervention.

## Other gotchas

* `browser_batch` is significantly faster than serial calls. Use it whenever 2+ steps have no inter-dependency. The runtime nags about this.
* `tabs_close_mcp` can hang ("did not respond in time") if a Chrome dialog is up. Resolve the dialog first.
* Repo lists, dropdowns, and async-loaded UIs need explicit waits after the trigger event. `await`/promises inside `javascript_tool` return their resolved value, so polling with `setTimeout` + `Promise` works.

## Anti-signals

* "Just click the button" - if the button is part of a React controlled form, click via JS.
* "It worked once with the mouse" - one success doesn't mean the path is reliable; the wedge is non-deterministic and triggered by extension focus shifts you can't observe.
* "I'll navigate away and come back" - if the form is dirty, the Leave site modal will fire.

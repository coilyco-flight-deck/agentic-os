# React-controlled input pattern and per-row flow

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

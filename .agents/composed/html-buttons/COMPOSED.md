---
name: html-buttons
description: Foundational button and link design for web interfaces. Covers native semantics, forms, accessible names, interaction states, focus, keyboard behavior, and testing.
---

# HTML buttons

Use native interactive elements and preserve their platform behavior.

## Choose the element

* Use `<button>` for an action that changes application state.
* Use `<a href>` for navigation to a location.
* Do not use clickable `<div>` or `<span>` elements.
* Add `type="button"` unless the button intentionally submits its form.

## Names and state

* Give every button a concise accessible name from visible text or `aria-label`.
* Keep icon-only names stable when the icon or tooltip changes.
* Use `disabled` for unavailable native controls.
* Use `aria-pressed` only for toggle buttons.
* Use `aria-expanded` with `aria-controls` for disclosure buttons.
* Keep loading controls named and expose progress without moving focus.

## Interaction

* Preserve Enter and Space activation supplied by native buttons.
* Show a visible `:focus-visible` indicator with sufficient contrast.
* Provide hover, active, focus, disabled, and busy visual states.
* Keep the hit target comfortably large without nesting interactive elements.
* Prevent duplicate submissions in logic, not by permanently hiding state.

## Verification

Test keyboard activation, focus visibility, accessible name and state, form
submission behavior, and screen-reader announcement after dynamic changes.

---
name: html-a11y
description: Foundational accessible HTML design. Covers semantic structure, names and labels, keyboard and focus behavior, dynamic feedback, forms, media, and verification.
---

# Accessible HTML

Start with semantic HTML, then add ARIA only where native semantics cannot
express the interaction.

## Structure

* Declare the document language and use a unique, descriptive page title.
* Use landmarks and one logical heading hierarchy.
* Use lists, tables, buttons, links, and form controls for their native purpose.
* Preserve a useful reading and tab order when CSS changes visual placement.

## Names and input

* Give every control a programmatic name that matches its visible label.
* Associate instructions and errors with the relevant control.
* Group related controls with `fieldset` and `legend`.
* Support zoom, reflow, text spacing, keyboard input, and touch targets.
* Never encode meaning through color, position, shape, or motion alone.

## Focus and feedback

* Keep focus visible and move it only when the interaction creates a new task.
* Return focus when a modal, popover, or temporary surface closes.
* Announce asynchronous status and errors without stealing focus.
* Respect reduced-motion preferences and provide controls for moving content.

## Media and verification

Provide useful alternative text, captions or transcripts where needed, and
empty alternative text for decorative images. Verify the result with keyboard
navigation, the browser accessibility tree, automated checks, zoom and reflow,
and at least one screen reader for interaction-heavy surfaces.

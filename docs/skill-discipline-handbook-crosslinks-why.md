# Skill Discipline Handbook - Cross-links and the Why

## 8. Cross-links

Two valid forms for in-prose references to other skills:

* **Bare backticks** `` `skill-name` `` for passing mentions in prose. Not navigable.
* **Markdown link** `` [`skill-name`](../skill-name/SKILL.md) `` for navigable references.

Either form: if the name does not resolve to a real skill in the repo, `check_dead_links.py` flags it. A cross-repo reference (a skill or file living in a sibling repo) cannot be a navigable link - it would escape the repo root, which is now a hard violation - so use the bare-backtick form with a parenthetical, e.g. `` `kai-tech-prefs` (in agentic-os-kai) ``.

External URLs, mailto links, and bare anchors (`#section`) are out of scope for the dead-link check. A `../` link is no longer skipped: an internal one is existence-checked, and one that escapes the repo root fails.

## 9. Encode the why, not just the what

Every agent session starts cold. There is no human in the loop to ask "why was this rule written?" Undocumented reasoning gets re-derived badly, or the rule gets deleted by an agent who cannot see why it mattered.

When you write a rule, lead with the rule, then write a **Why:** line (the incident, constraint, or prior failure mode that produced it), then a **How to apply:** line (when the rule fires). Date-stamp the flag where useful so future readers can judge whether the why is still load-bearing.

Framing reference: [The end of "just ask Sarah"](https://simme.dev/posts/the-end-of-just-ask-sarah/).

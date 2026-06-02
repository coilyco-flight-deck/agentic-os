# Skill Discipline Handbook - Cross-links and the Why

## 8. Cross-links

Two valid forms for in-prose references to other skills:

* **Bare backticks** `` `skill-name` `` for passing mentions in prose. Not navigable.
* **Markdown link** `` [`skill-name`](../skill-name/SKILL.md) `` for navigable references.

Either form: if the name does not resolve to a real skill in the repo, `check_dead_links.py` flags it.

External URLs, mailto links, bare anchors (`#section`), and paths that escape the repo via `../` are out of scope for the dead-link check.

## 9. Encode the why, not just the what

Every agent session starts cold. There is no human in the loop to ask "why was this rule written?" Undocumented reasoning gets re-derived badly, or the rule gets deleted by an agent who cannot see why it mattered.

When you write a rule, lead with the rule, then write a **Why:** line (the incident, constraint, or prior failure mode that produced it), then a **How to apply:** line (when the rule fires). Date-stamp the flag where useful so future readers can judge whether the why is still load-bearing.

Framing reference: [The end of "just ask Sarah"](https://simme.dev/posts/the-end-of-just-ask-sarah/).

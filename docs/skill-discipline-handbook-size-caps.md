# Skill Discipline Handbook - Size Caps

## 7. Size caps

Three size caps in `categories.yaml`, all with built-in defaults that apply when unset. Set any value to `0` to disable that specific check.

* `max_skill_md_lines` (default `500`) and `max_skill_md_bytes` (default `10000`) cap the SKILL.md file itself. Past either, agent harnesses degrade: the loader either refuses the file or drops it from context. Push detail into `<skill>/references/<topic>.md` files when a SKILL.md fills up. Reference files are not capped.
* `max_description_bytes` (default `500`) caps the frontmatter `description` field. Every skill's description is loaded into every agent session for keyword matching, so descriptions are pure always-on context cost. 500 fits a canonical-name + one sentence of trigger phrasings; past that you're paying for padding.
  * **Router/meta exception**: skills whose category declares `role: router` or `role: meta` get **2x** the cap (default 1000). Routers genuinely need wider keyword surface to fan out to all the skills they cross-link. The validator applies the multiplier automatically.

### Description budget targets

The validator enforces a hard byte cap, but the practical target should be lower. Treat `description` as routing metadata, not documentation. Codex and Claude both see this text before deciding whether to open the skill body.

* **Pointer skills** - under 160 chars. Use this when the body mostly points at a canonical doc elsewhere.
* **Normal task skills** - 120-200 chars. Most coding, writing, gaming, vault, and tool-usage skills should fit here.
* **Complex task skills** - 220-300 chars. Use this for skills with several adjacent trigger phrasings or one important boundary.
* **Router/meta skills** - 250-400 chars normally. A router earns extra surface only when it prevents many child skills from carrying broad aliases.
* **Rare exceptions** - 400-500 chars for public-safety, MCP routing, or cross-repo failure handling where false negatives are expensive.

Put the main task shape, a few trigger phrases, and critical disambiguators in `description`. Put procedure, examples, policy rationale, command sequences, implementation details, and historical context in the body or `references/`.

If a skill needs more than 8-12 aliases in the description, rename the skill, add a router parent, or split the domain.

### Frozen-archive exemption

`archive_path_components` (default `[]`) lists path components that mark a frozen archive. Any `.md` whose path contains one of these is skipped from the size caps - but only the size caps. Stale-ref, forbidden-body-string, and frontmatter checks still apply.

The motivation: investigation writeups, per-incident case libraries, and ticket-stamped diagnoses are loaded by name when an agent revisits the incident, not by the loader on trigger. Forcing splits on a 28KB rollout analysis destroys narrative for zero loader benefit. The convention this enables: park frozen content under a directory whose name is in the list (`results/`, `archive/`, etc.) and the cap stops applying.

```yaml
archive_path_components:
  - results
```

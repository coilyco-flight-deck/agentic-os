# Per-glyph color map and unreachable colors

For arbitrary Unicode glyphs (e.g. braille `⣿`) placed inside fenced blocks in the default desktop theme, the reachable colors are:

- **Green** - diff `+` lines, string literals in any language (`"⣿⣿⣿"`).
- **Red** - diff `-` lines, numeric literals.
- **Orange** - keywords (`def`, `return`, `const`, `class`). Also covers the regex-flag position (`/.../g`).
- **Orange-yellow** - regex content (`/⣿⣿⣿/`). Distinct from keyword-orange but in the same hue family. Less contrast than expected.
- **Blue** - CSS tokens, markdown headings inside fences.
- **Gray** - comments (`#`, `//`).
- **Purple** - class names in class declarations (e.g. `class forest:` colors `forest` purple). Some highlighters also color decorator names purple. Reachable for braille if you put it in a class-name position.
- **White** - plain identifiers, default text. Function names usually fall here.

Your theme will differ. Run the probe blocks in [examples.md](examples.md) and re-map.

## What's unreachable

- **Per-character color within a single line.** Highlighters tokenize, they don't paint sub-tokens. You get one color per token, not per glyph.
- **Multi-color art in a single fence with diff colors.** `diff` is its own language. You can't mix red diff lines with yellow regex content in the same block.
- **True yellow as a separate color from orange** in this theme. They're shades, not separate hues.
- **Putting orange on a braille glyph directly.** Orange is the keyword class. Braille won't tokenize as a keyword, so braille payload can never be orange. Orange paints the syntax around the braille (e.g. `class ⣿⣿⣿:` colors `class` orange and leaves the braille white).

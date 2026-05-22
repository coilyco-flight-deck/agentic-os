---
name: claude-code-render
description: Color and visual output for the Claude Code Desktop client by exploiting the fenced-block syntax highlighter (no ANSI). Triggers - render, colorful, color, terminal colors, chart, sparkline, ASCII art, braille art, visualization, syntax highlight trick, diff coloring, chat art, glyph palette.
---

# Claude Code Desktop Render Tricks

Empirically-mapped rendering capabilities of the Claude Code Desktop client. Theme-specific; your palette may differ. Other clients (Chrome web, Android, terminal) likely differ too. Methodology in the repo [README](../../README.md). Worked examples in [references/examples.md](references/examples.md).

## What renders, what doesn't

**Renders:**

- CommonMark + GitHub-flavored markdown: headings, bold, italic, strikethrough, lists, task lists, blockquotes, tables, fenced code blocks with syntax highlighting, footnotes, autolinks.
- Markdown links, including file links with `:line` anchors.
- Inline code with monospace.
- Unicode glyphs of any kind, including braille (`⣿`), box-drawing, block elements, shade blocks.

**Does not render:**

- Images, GIFs, video, audio. No `![](...)` embedding. Linking only.
- Raw HTML (stripped or shown as literal text). No `<img>`, `<iframe>`, `<details>`, `<video>`, `<svg>`.
- LaTeX / MathJax.
- Mermaid, PlantUML, or any fenced-block-to-diagram extension.
- ANSI escape codes inside fenced output (shown literally).
- Custom fonts, colors, sizes outside what markdown structurally implies.

## The color trick

Fenced code blocks get syntax highlighting based on the language tag. Highlighters assign colors to tokens. Unicode glyphs placed in syntactically-meaningful positions inherit token color "for free." No ANSI needed.

### Per-glyph color map (default desktop theme)

For arbitrary Unicode glyphs (e.g. braille `⣿`) placed inside fenced blocks, the reachable colors are:

- **Green** - diff `+` lines, string literals in any language (`"⣿⣿⣿"`).
- **Red** - diff `-` lines, numeric literals.
- **Orange** - keywords (`def`, `return`, `const`, `class`). Also covers the regex-flag position (`/.../g`).
- **Orange-yellow** - regex content (`/⣿⣿⣿/`). Distinct from keyword-orange but in the same hue family. Less contrast than expected.
- **Blue** - CSS tokens, markdown headings inside fences.
- **Gray** - comments (`#`, `//`).
- **Purple** - class names in class declarations (e.g. `class forest:` colors `forest` purple). Some highlighters also color decorator names purple. Reachable for braille if you put it in a class-name position.
- **White** - plain identifiers, default text. Function names usually fall here.

Your theme will differ. Run the probe blocks in [references/examples.md](references/examples.md) and re-map.

### What's unreachable

- **Per-character color within a single line.** Highlighters tokenize, they don't paint sub-tokens. You get one color per token, not per glyph.
- **Multi-color art in a single fence with diff colors.** `diff` is its own language. You can't mix red diff lines with yellow regex content in the same block.
- **True yellow as a separate color from orange** in this theme. They're shades, not separate hues.
- **Putting orange on a braille glyph directly.** Orange is the keyword class. Braille won't tokenize as a keyword, so braille payload can never be orange. Orange paints the syntax around the braille (e.g. `class ⣿⣿⣿:` colors `class` orange and leaves the braille white).

## Composition patterns

### Single-fence multi-color (JavaScript)

Densest reliable palette in one block: gray comments, green strings, white identifiers, orange-y regex content.

```javascript
// ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿       gray sky
const ⣿⣿⣿ = /⣿⣿⣿⣿⣿⣿⣿⣿/g;
"⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿"
"⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿"
```

### Structural scaffolding (Python)

Orange keywords and red numerics paint around a green-string-braille payload, contributing to overall composition without coloring the payload itself.

```python
class ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿:
    "⣿⣿⣿⣿⣿⣿⣿⣿"
    "⣿⣿⣿⣿⣿⣿⣿⣿"
    return 42424242
```

### Diff-block stripes

For red+green only. Two-color horizontal banding. Well-known on GitHub READMEs; works the same way here.

````
```diff
+ ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
- ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
```
````

### Stacked-fences (does NOT work in desktop)

Tried sequential fences in different languages to fuse a multi-color landscape. **Failed.** The desktop client puts substantial vertical padding between fences, so they read as separate blocks with empty space between them, not as a stitched image. Multi-color art must live inside a single fence.

### Density gradients

Within a single color, mix glyph weights for shading:

- `⣿` full
- `⠿` medium
- `⠶` light
- `⠁` single dot

Combined with one color, gives a per-cell gradient inside one hue. Real `chafa`-style photo rendering relies on this.

## Practical takeaways

- Stay inside one fence. Stacking fences for multi-color composition doesn't work in desktop.
- JavaScript and Python both reach 4+ braille colors per fence. Python adds purple class names; JavaScript adds orange-yellow regex content. Pick the one whose tokens fit the picture's structural needs.
- Diff is the only path to red-braille and green-braille payload simultaneously, but it caps at 2 colors.
- For more than 5 colors, accept that fences will be siblings, not fused.
- Density variation within one color is the underused trick. 8 sub-pixels per braille glyph, plus 4+ weight levels, gives surprising photographic detail without needing color at all.

## Glyph palette reference

- ASCII shades, low to high density: `. : - = + * # % @`
- Box-drawing: `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ╔ ╗ ╚ ╝ ║ ═ ╠ ╣ ╦ ╩ ╬`
- Block elements: `█ ▓ ▒ ░ ▀ ▄ ▌ ▐ ▖ ▗ ▘ ▝ ▙ ▟ ▛ ▜`
- Sparklines: `▁ ▂ ▃ ▄ ▅ ▆ ▇ █`
- Braille: full Unicode block U+2800 to U+28FF. Each glyph is a 2×4 dot grid (8 sub-pixels per cell). Highest text-rasterization density possible.

## Open questions

- Does the palette differ in Chrome web client, Android client, or terminal?
- Can fenced-block-inside-quoted-string nesting unlock per-character color via injection? Unlikely but untested.
- Does `**bold**` inside a markdown fence render bold? Heading-coloring inside a `markdown` fence is confirmed to NOT work (see [examples §VI](references/examples.md)), so the broader "markdown-inside-fence inherits markdown rendering" hypothesis is mostly disproved.

## Provenance

Probe session 2026-05-13 against Claude Code Desktop. Mapped empirically through probe blocks, with screenshot-confirmed corrections of initial overclaims. The "stacked fences" idea was the main retraction.

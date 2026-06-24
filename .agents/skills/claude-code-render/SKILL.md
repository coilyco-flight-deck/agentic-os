---
name: claude-code-render
description: Color and visual output for the Claude Code Desktop client by exploiting the fenced-block syntax highlighter (no ANSI). Triggers - render, colorful, color, terminal colors, chart, sparkline, ASCII art, braille art, visualization, syntax highlight trick, diff coloring, chat art, glyph palette.
---

# Claude Code Desktop Render Tricks

Empirically-mapped rendering capabilities of the Claude Code Desktop client. **Claude-Code-Desktop-specific - on another harness (e.g. the Codex TUI) these tricks do not apply, so skip this skill there.** Theme-specific, your palette may differ. Other clients (Chrome web, Android, terminal) likely differ too. Methodology in the repo [README](../../../README.md). Worked examples in [references/examples.md](references/examples.md).

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

- [Per-glyph color map](references/color-map.md) - which token positions reach which colors, and the colors that stay unreachable.

## Composition

- [Composition patterns](references/composition-patterns.md) - single-fence multi-color, structural scaffolding, diff stripes, the failed stacked-fences experiment, and density gradients.

## Practical takeaways

- Stay inside one fence. Stacking fences for multi-color composition doesn't work in desktop.
- JavaScript and Python both reach 4+ braille colors per fence. Python adds purple class names; JavaScript adds orange-yellow regex content. Pick the one whose tokens fit the picture's structural needs.
- Diff is the only path to red-braille and green-braille payload simultaneously, but it caps at 2 colors.
- For more than 5 colors, accept that fences will be siblings, not fused.
- Density variation within one color is the underused trick. 8 sub-pixels per braille glyph, plus 4+ weight levels, gives surprising photographic detail without needing color at all.

## Reference

- [Glyph palette and open questions](references/glyph-palette.md) - ASCII shades, box-drawing, block elements, sparklines, braille, plus unresolved probes and provenance.
- [Worked examples](references/examples.md) - six confirmed probe blocks, one per render technique.

# Glyph palette reference and open questions

## Glyph palette

- ASCII shades, low to high density: `. : - = + * # % @`
- Box-drawing: `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ╔ ╗ ╚ ╝ ║ ═ ╠ ╣ ╦ ╩ ╬`
- Block elements: `█ ▓ ▒ ░ ▀ ▄ ▌ ▐ ▖ ▗ ▘ ▝ ▙ ▟ ▛ ▜`
- Sparklines: `▁ ▂ ▃ ▄ ▅ ▆ ▇ █`
- Braille: full Unicode block U+2800 to U+28FF. Each glyph is a 2x4 dot grid (8 sub-pixels per cell). Highest text-rasterization density possible.

## Open questions

- Does the palette differ in Chrome web client, Android client, or terminal?
- Can fenced-block-inside-quoted-string nesting unlock per-character color via injection? Unlikely but untested.
- Does `**bold**` inside a markdown fence render bold? Heading-coloring inside a `markdown` fence is confirmed to NOT work (see [example VI](example-markdown-negative.md)), so the broader "markdown-inside-fence inherits markdown rendering" hypothesis is mostly disproved.

## Provenance

Probe session 2026-05-13 against Claude Code Desktop. Mapped empirically through probe blocks, with screenshot-confirmed corrections of initial overclaims. The "stacked fences" idea was the main retraction.

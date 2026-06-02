# Example VI. markdown-headings-inside-fence (NEGATIVE RESULT)

Probed whether markdown-source inside a `markdown`-tagged fence colors headings blue. **It does not.** Confirmed via screenshot 2026-05-13.

````
```markdown
# ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
## ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
### ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
plain ⣿⣿⣿⣿⣿⣿⣿⣿⣿
```
````

Actual rendering: every line uniform white. The markdown highlighter does not apply heading-level colors to source inside a fenced block (in this theme at least). The "blue for markdown headings inside fences" claim in earlier drafts of this skill was wrong.

This kills one of the open questions outright. Recorded as a negative example so future probers don't retry without context.

## How to reproduce

1. Open Claude Code Desktop and start a new chat or open any surface that renders markdown.
2. Paste the fenced block (including the triple-backtick delimiters and language tag) verbatim.
3. Send the message or save the markdown file. The fenced block renders with syntax highlighting applied to the contained Unicode glyphs.
4. If colors do not match the expected rendering, verify the language tag spelling, that no characters have been substituted (especially the braille glyphs U+2800 to U+28FF), and that the renderer in use is the desktop client.

## Provenance

Built on 2026-05-13 during the same probe session that produced the render-tricks doc. Visually confirmed via screenshots from Kai's Claude Code Desktop client.

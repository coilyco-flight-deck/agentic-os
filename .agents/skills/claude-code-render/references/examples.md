# Claude Code Desktop Render Examples

Six numbered probe blocks built on the techniques documented in [the SKILL body](../SKILL.md). The first five render as described; the sixth is a confirmed negative result kept for honesty. Visually confirmed in the Claude Code Desktop client on 2026-05-13.

Reproducing these requires the Claude Code Desktop client with the syntax highlighter active. Other clients (Chrome web, Android, terminal) may render differently. Paste the fenced block as-is into a chat message or notes surface that runs the same renderer.

## I. sunrise()

A function whose body is also a landscape. Comments are clouds, identifiers form mountains, regex content is the sun, string returns are layered water. The function "returns the sunrise" three times because oceans have depth.

Technique: four-color composition in one fence. The semantic names (`halo`, `core`, `horizon`) double as labels for parts of the picture.

````
```javascript
function sunrise() {
  // ⢀⣠⣤⣄⡀                            ⢀⣠⣤⣄⡀
  // ⠘⠿⠿⠟⠁                            ⠈⠻⠿⠟⠁
  //
  //                  ⢀⣀⣤⣤⣄⡀
  //               ⢀⣴⣾⣿⣿⣿⣿⣷⡆
  const halo = /⢠⣾⣿⣿⣿⣿⣿⣿⣿⣷/g;
  const core = /⠈⠻⠿⣿⣿⣿⣿⠿⠟⠁/g;
  //
  let horizon = ⣀⣀⣀⣠⣤⣴⣶⣾⣿⣿⣷⣶⣶⣶⣦⣤⣄⣀⣀⣀;
  //
  return "⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶";
  return "⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶";
  return "⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿";
}
```
````

Expected rendering:

- Gray clouds (comment lines).
- Orange-yellow sun (regex contents inside `/.../g`).
- White mountain silhouette (identifier characters after `let horizon =`).
- Green water bands (three string returns).
- Orange keywords (`function`, `const`, `let`, `return`) and the `=`, `(`, `)`, `{`, `}`, `;` punctuation form structural scaffolding.

Repro notes:

- Language tag must be `javascript`. `js` may or may not work depending on highlighter aliases.
- The braille identifier after `let horizon =` is non-standard JS. The highlighter accepts it as identifier-class anyway because it tokenizes by character class, not strict JS lexer rules.
- Multiple `return` statements are unreachable but parse. They are required to get three lines of green water.

## II. Phases

A crescent moon. No color, just density. The bright crescent uses dense braille (`⣿`, `⠿`), the dark side uses sparse single-dot glyphs (`⠁`, `⠂`, `⠠`, `⠈`) to suggest earthshine — light bouncing back from earth onto the moon's shadow side. The eye fills in the curvature.

Technique: density-only rendering inside an unlabeled fence. Eight sub-pixels per braille cell × four glyph weights yields enough resolution for shape and lighting without color.

````
```
           ⢀⣠⣶⣾⣶⣦⣄⡀
        ⢀⣴⣾⣿⣿⣿⣿⣿⣿⣷⣦⡀
      ⢀⣴⣿⣿⣿⣿⡿⠟⠛⠛⠛⠻⢿⣿⣆
     ⣰⣿⣿⣿⣿⡿⠋    ⠁  ⠂  ⠁
    ⣸⣿⣿⣿⣿⠟      ⠠
    ⣿⣿⣿⣿⣿       ⠈   ⠂
    ⣿⣿⣿⣿⣿⡆   ⠠         ⠁
    ⢹⣿⣿⣿⣿⡇     ⠈   ⠠
    ⠈⣿⣿⣿⣿⣷⡀   ⠂
     ⠘⣿⣿⣿⣿⣿⣦⡀         ⠂
      ⠈⠻⣿⣿⣿⣿⣿⣦⣄⡀
        ⠈⠛⠿⣿⣿⣿⣿⣿⣷⣶⣶⣶⡆
          ⠈⠉⠛⠛⠿⠿⠿⠿⠿⠟⠋
```
````

Expected rendering:

- Entire image in white (the default identifier color).
- Crescent body solid and bright on the left side.
- Right side empty except for a few faint single-dot braille glyphs scattered to suggest the dark hemisphere lit by earthshine.

Repro notes:

- No language tag. Adding one (e.g. `python`) might tokenize sparse glyphs differently and could break the uniform-white effect.
- Glyph palette used, low to high density: `⠁ ⠂ ⠠ ⠈ ⠉ ⠋ ⠟ ⠿ ⣿`. Mixing weights within one color is how the moon gets surface texture without color shift.

## III. Strawberry

Two-color diff with density texture inside one color. Seeds aren't a third hue. They are the same red rendered at lower density, which the eye reads as small dark spots.

Technique: red+green diff iconography. Bluntest tool in the palette, earns its keep through instantly-recognizable shape.

````
```diff
+         ⡀  ⢀⡀  ⡀
+        ⣿⣆⣸⣷⣄⣿
+     ⢀⣀⣸⣿⣿⣿⣿⣿⣇⣀⡀
-    ⢀⣴⣿⣿⠟⠛⠉⠛⠻⣿⣿⣦⡀
-   ⢀⣾⣿⡿⠋ ⠶   ⠈⠻⣿⣷⡀
-   ⣾⣿⡟  ⠶   ⠶  ⠈⢿⣿⣄
-   ⣿⣿⠁ ⠶   ⠶   ⠶ ⢸⣿⣿
-   ⢿⣿⣆  ⠶   ⠶   ⠶ ⣿⣿⡏
-   ⠘⢿⣿⣆ ⠶   ⠶  ⠶ ⣸⣿⠟
-    ⠈⠻⣿⣷⣄    ⢀⣴⣿⠋
-       ⠙⠻⣿⣿⣶⣿⣿⠟⠁
-           ⠙⠻⠟⠁
```
````

Expected rendering:

- Top three lines (with `+` prefix) render green: three small leaf tufts above a leaf-band.
- Bottom lines (with `-` prefix) render red: round strawberry body coming to a point.
- The `⠶` glyphs inside the body remain red (same line, same color) but lower density, so they read as seeds rather than as color variation.

Repro notes:

- Language tag must be `diff`.
- Prefix character must be `+ ` or `- ` (followed by a space) for line-level coloring to fire. A bare `+` or `-` with no space may not trigger.
- Leading whitespace after the prefix is significant for shape and is preserved by the renderer.

## IV. forest()

A pine-tree silhouette. Demonstrates the Python structural-scaffolding pattern: orange keywords (`class`, `return`) plus a red numeric trunk frame a green-string braille canopy. Also a palette correction: class names render purple, not white as previously claimed.

Technique: Python multi-color in one fence with explicit role separation. Each `leaves`/`canopy`/`crown` assignment is one green string row; together they cone outward then taper. The numeric `trunk` line is the only red.

````
```python
class forest:
    canopy = "⢀⣠⣤⣶⣾⣷⣶⣤⣄⡀"
    crown  = "⢠⣾⣿⣿⣿⣿⣿⣿⣿⣷⡄"
    leaves = "⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿"
    leaves = "⠈⠻⣿⣿⣿⣿⣿⣿⣿⠟⠁"
    trunk  = 11111111
    return canopy
```
````

Expected rendering:

- `class`, `return` orange.
- `forest` (class name) purple.
- All four `"..."` strings green, stacking into a tree silhouette.
- `11111111` red, forming a centered trunk numeral.
- Identifier names (`canopy`, `crown`, `leaves`, `trunk`) white.

Screenshot: [`forest.png`](../forest.png).

Repro notes:

- Re-using the variable name `leaves` twice is intentional. Python won't complain at parse time; the highlighter doesn't care.
- The trunk needs enough digits to span under the canopy. Eight `1`s align under a ~10-glyph crown reasonably well.

## V. heartbeat

A three-beat EKG pulse. Demonstrates: density-only rendering with sparkline glyphs (`▁▂▃▄▅▆▇█`) inside an unlabeled fence. No color, just shape.

Technique: same single-color density trick as the moon, but with sparkline glyphs instead of braille. Sparklines are taller and narrower per cell, so they give a horizontal time-series feel rather than the dot-grid feel braille has.

````
```
▁▁▂▃▅█▇▄▂▁▁▁▁▂▃▅█▇▄▂▁▁▁▁▂▃▅█▇▄▂▁▁
```
````

Expected rendering:

- All glyphs in the default identifier/text color (white-ish).
- Reads as three repeating heartbeat pulses with a baseline between.
- Each pulse: gentle rise (`▁▂▃`), sharp spike (`▅█`), gradual fall (`▇▄▂▁`).

Screenshot: [`heartbeat.png`](../heartbeat.png).

Repro notes:

- No language tag. A tag like `python` may tokenize the sparkline glyphs unpredictably.
- Sparkline glyph ordering is `▁▂▃▄▅▆▇█` low to high. Mirror to get the falling edge.
- Works equally well unfenced (plain markdown). Fenced gives a monospace card; unfenced inlines with surrounding prose.

## VI. markdown-headings-inside-fence (NEGATIVE RESULT)

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

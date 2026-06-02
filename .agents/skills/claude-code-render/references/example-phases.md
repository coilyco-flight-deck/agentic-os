# Example II. Phases

A crescent moon. No color, just density. The bright crescent uses dense braille (`⣿`, `⠿`), the dark side uses sparse single-dot glyphs (`⠁`, `⠂`, `⠠`, `⠈`) to suggest earthshine - light bouncing back from earth onto the moon's shadow side. The eye fills in the curvature.

Technique: density-only rendering inside an unlabeled fence. Eight sub-pixels per braille cell times four glyph weights yields enough resolution for shape and lighting without color.

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

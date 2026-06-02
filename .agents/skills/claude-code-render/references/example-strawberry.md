# Example III. Strawberry

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

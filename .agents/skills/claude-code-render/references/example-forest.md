# Example IV. forest()

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

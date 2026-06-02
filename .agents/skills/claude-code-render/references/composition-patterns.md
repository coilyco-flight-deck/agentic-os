# Composition patterns

## Single-fence multi-color (JavaScript)

Densest reliable palette in one block: gray comments, green strings, white identifiers, orange-y regex content.

```javascript
// ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿       gray sky
const ⣿⣿⣿ = /⣿⣿⣿⣿⣿⣿⣿⣿/g;
"⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿"
"⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿"
```

## Structural scaffolding (Python)

Orange keywords and red numerics paint around a green-string-braille payload, contributing to overall composition without coloring the payload itself.

```python
class ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿:
    "⣿⣿⣿⣿⣿⣿⣿⣿"
    "⣿⣿⣿⣿⣿⣿⣿⣿"
    return 42424242
```

## Diff-block stripes

For red+green only. Two-color horizontal banding. Well-known on GitHub READMEs; works the same way here.

````
```diff
+ ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
- ⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
```
````

## Stacked-fences (does NOT work in desktop)

Tried sequential fences in different languages to fuse a multi-color landscape. **Failed.** The desktop client puts substantial vertical padding between fences, so they read as separate blocks with empty space between them, not as a stitched image. Multi-color art must live inside a single fence.

## Density gradients

Within a single color, mix glyph weights for shading:

- `⣿` full
- `⠿` medium
- `⠶` light
- `⠁` single dot

Combined with one color, gives a per-cell gradient inside one hue. Real `chafa`-style photo rendering relies on this.

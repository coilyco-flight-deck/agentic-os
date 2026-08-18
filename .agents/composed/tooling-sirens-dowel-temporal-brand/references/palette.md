# Temporal palette

Exact values, split by how much authority each layer carries. The published
layer is the brand. The token layer is one implementation of it and can move.

## Published brand colors

These three, and only these three, appear on
[`temporal.io/brand`](https://temporal.io/brand) as brand colors.

* **UV** - `#444CE7` - rgb(68 76 231) - the brand accent, also written as ultraviolet in the site's own class names.
* **Space Black** - `#141414` - rgb(20 20 20) - the default ground.
* **Off White** - `#F8FAFC` - rgb(248 250 252) - primary text and the inverse surface.

The utility class names built on them are `bg-ultraviolet`, `bg-space-black`,
and `text-off-white`, which confirms the token names map straight to the
published color names.

## Named gradients

Two-stop linear ramps declared in the site's inline SVG definitions. The name
is Temporal's, taken from the gradient id.

* **purple-ultraviolet-gradient** - `#B664FF` to `#444CE7`
* **pink-gradient** - `#FF5555` to `#B664FF`
* **green-gradient** - `#C3FF62` to `#1FF1A5`
* **mist** - `#34D399` to `#FF6BFF`

Standalone stops worth naming because they recur: `#B664FF` bright purple,
`#FF5555` coral red, `#C3FF62` acid lime, `#1FF1A5` spring green, `#34D399`
emerald (also exposed directly as `--color-emerald`), `#FF6BFF` hot pink.

## Semantic token layer

Declared as space-separated RGB triplets so alpha can be composed at use time.
Hex is given here for reading convenience, and the triplet is the authoritative
form.

### Surface

* `--color-surface-background` - rgb(20 20 20) - `#141414` - Space Black, the page ground.
* `--color-surface-primary` - rgb(0 0 0) - `#000000` - true black, reserved for the deepest layer rather than the page.
* `--color-surface-secondary` - rgb(248 250 252) - `#F8FAFC` - Off White.
* `--color-surface-inverse` - rgb(248 250 252) - `#F8FAFC`
* `--color-surface-subtle` - rgb(55 71 97) - `#374761`
* `--color-surface-table` - rgb(36 51 73) - `#243349`
* `--color-surface-brand` - rgb(68 76 231) - `#444CE7` - UV.
* `--color-surface-information` - rgb(26 28 76) - `#1A1C4C`
* `--color-surface-information-loud` - rgb(63 67 219) - `#3F43DB`
* `--color-surface-success` - rgb(0 143 83) - `#008F53`
* `--color-surface-success-loud` - rgb(0 225 117) - `#00E175`
* `--color-surface-warning` - rgb(253 113 10) - `#FD710A`
* `--color-surface-danger` - rgb(199 29 0) - `#C71D00`

### Text

* `--color-text-primary` - rgb(248 250 252) - `#F8FAFC` - Off White on the dark ground.
* `--color-text-inverse` - rgb(20 20 20) - `#141414`
* `--color-text-secondary` - rgb(70 90 120) - `#465A78`
* `--color-text-subtle` - rgb(70 90 120) - `#465A78` - identical to secondary in the shipped build.
* `--color-text-white` - rgb(255 255 255) - `#FFFFFF`
* `--color-text-black` - rgb(0 0 0) - `#000000`
* `--color-text-brand` - rgb(68 76 231) - `#444CE7`
* `--color-text-information` - rgb(68 76 231) - `#444CE7`
* `--color-text-success` - rgb(0 225 117) - `#00E175`
* `--color-text-warning` - rgb(254 193 24) - `#FEC118`
* `--color-text-danger` - rgb(255 100 60) - `#FF643C`
* `--color-text-pink` - rgb(227 0 230) - `#E300E6`

### Border

* `--color-border-primary` - rgb(124 143 177) - `#7C8FB1`
* `--color-border-secondary` - rgb(70 90 120) - `#465A78`
* `--color-border-subtle` - rgb(55 71 97) - `#374761`
* `--color-border-table` - rgb(36 51 73) - `#243349`
* `--color-border-inverse` - rgb(20 20 20) - `#141414`
* `--color-border-information` - rgb(68 76 231) - `#444CE7`
* `--color-border-focus-info` - rgb(63 67 219) - `#3F43DB`
* `--color-border-focus-danger` - rgb(251 62 20) - `#FB3E14`
* `--color-border-success` - rgb(0 204 106) - `#00CC6A`
* `--color-border-warning` - rgb(254 180 18) - `#FEB412`
* `--color-border-danger` - rgb(255 100 60) - `#FF643C`

### Interactive

Each interactive family runs surface, hover, active, which makes the state
progression explicit rather than derived at use time.

* `--color-interactive-surface` - rgb(63 67 219) - `#3F43DB`
* `--color-interactive-hover` - rgb(53 56 207) - `#3538CF`
* `--color-interactive-active` - rgb(28 13 178) - `#1C0DB2`
* `--color-interactive-secondary-surface` - rgb(102 124 161) - `#667CA1`
* `--color-interactive-secondary-hover` - rgb(36 51 73) - `#243349`
* `--color-interactive-secondary-active` - rgb(55 71 97) - `#374761`
* `--color-interactive-ghost-hover` - rgb(70 90 120) - `#465A78`
* `--color-interactive-ghost-active` - rgb(36 51 73) - `#243349`
* `--color-interactive-danger-surface` - rgb(255 130 95) - `#FF825F`
* `--color-interactive-danger-hover` - rgb(255 100 60) - `#FF643C`
* `--color-interactive-danger-active` - rgb(255 69 24) - `#FF4518`

Note that the primary interactive surface is `#3F43DB` rather than UV itself.
The brand color anchors identity and a slightly deeper neighbor carries the
control, so a button never competes with a logo.

## Not brand

Values that appear in the same markup and are not part of the system.

* `#dbff4b` - the top announcement bar background, set per campaign alongside its own text and link colors. It changes with the campaign.
* `#0066FF` - an embedded third-party privacy-consent widget icon.

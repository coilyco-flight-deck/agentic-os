---
name: tooling-discord-emoji-assets
description: Produce a custom Discord emoji from a brand mark the community already has the right to use, choosing the format that survives upload and verifying it at the size Discord actually renders. Use when asked for a server emoji, an animated emote, or a transparent variant of either.
---

# Discord emoji assets

Use this skill to turn a mark into an uploadable emoji. It covers the platform
limits, the format fork that decides whether transparency is even possible, and
the checks that catch a wrong asset before a human uploads it.

## Know the limits before choosing a shape

* 128x128 is the working size, and 256KB is the hard cap on the uploaded file.
* An unboosted server holds 50 static emoji and a separate 50 animated.
* Using an animated emoji in another server needs Nitro. Inside a boosted
  server it is free to every member, so read the guild's own feature flags
  rather than asking. `ROLE_ICONS`, `AUDIO_BITRATE_256_KBPS` and
  `MAX_FILE_SIZE_50_MB` are boost-tier perks and settle it.
* Discord renders an inline emoji near 22px and a jumbo one near 48px. The tile
  is 128 so it downscales hard, and thin strokes are the first thing lost.

## Pick the format from what the art needs

* Static, any background - PNG.
* Animated on an opaque plate - GIF.
* Animated with transparency - animated WebP. This is the only combination
  that works.

GIF transparency is one bit, so a soft glow, a feathered edge, or any partial
alpha binarizes into a hard fringe. Building it and looking at it is faster
than reasoning about it, and the result is unusable rather than merely worse.
APNG carries full alpha but Discord does not accept it for emoji, though it
does for stickers. Animated WebP carries full alpha and uploads as animated.

Verify a WebP kept its alpha instead of trusting the encoder:

```
magick 'out.webp[12]' frame.png
magick frame.png -alpha extract -format '%k\n' info:   # >2 means continuous
```

## Source the mark from the owner's own site

A store page ships marketing art, which is usually a wordmark. A wordmark
crushed to 128px is a smear at 22px and cannot be rescued by cropping. The
site's favicon is the square emblem the owner already designed for a tiny
square, so read the page's icon links first.

```
curl -sL -A 'Mozilla/5.0' https://<site>/ -o home.html
grep -oiE '<link[^>]*rel=["'"'"'][^"'"'"']*icon[^"'"'"']*["'"'"'][^>]*>' home.html
```

Prefer the shipped raster over rendering the SVG. A vector whose background is
its own filled path can render with the alpha inverted, which produces a mark
that silently comes out as a hole.

## Prove polarity rather than assuming it

A mask built from luminance is trivially invertible, and an inverted one looks
plausible on a dark plate. Composite the layer over magenta once. The error is
then unmissable instead of subtle.

```
magick -size 256x256 xc:magenta sigil_rgba.png -compose Over -composite proof.png
```

Check the mask's mean against the source. A mark covering roughly a tenth of
its tile should give an alpha mean near 0.1, not near 0.5.

## Make one file work in both themes

A viewer's Discord is light or dark, and the emoji cannot know which. A white
mark on transparency is crisp on dark and invisible on white.

Put a dark contour under the mark: spread the mask outward, fill it near-black,
and lay the mark on top. On a dark background the contour disappears into it,
and on white it gives the strokes an edge. One file then covers both.

```
magick mask.png -morphology Dilate Disk:3 -blur 0x2 contour_mask.png
magick -size 256x256 xc:'#06111c' -alpha off contour_mask.png \
  -compose CopyOpacity -composite contour.png
```

## Encode a GIF without wrecking it

* Never run `-layers OptimizeTransparency` over an opaque plate. It punches
  holes the coalesced frames reveal and a casual look does not.
* Quantize against one global palette with dithering. Per-frame local palettes
  contour-band a smooth gradient into visible rings.
* Coalesce the finished file and look at the frames. Disposal bugs only appear
  after the optimizer has run.

```
magick frames/f_*.png -append +dither -colors 254 -unique-colors +repage pal.png
magick -delay 6 -loop 0 frames/f_*.png -dither FloydSteinberg -remap pal.png \
  -layers OptimizeFrame out.gif
magick out.gif -coalesce co_%02d.png
```

## Judge it at the size it ships at

A 128px tile flatters everything. Render the candidate at 22px, blow it back up
with a point filter, and put it on both theme backgrounds before recommending
one. Report what the small size costs rather than hiding it, since thickening
strokes to survive 22px stops the asset being the literal mark.

```
magick out.png -resize 22x22 -filter point -resize 400% inline_sim.png
```

## Hand the upload over

Creating an emoji needs `MANAGE_GUILD_EXPRESSIONS` on the bot, and a read-only
Discord surface has no write tool regardless of permission. Decode the guild
permission bitfield rather than guessing, then hand the file to a human with
its absolute path and the destination, which is Server Settings > Emoji.

Keep the produced binary out of a tracked repository when the mark belongs to
someone else. Store it where the community's other assets live and reference it
by URL, so the repository carries the method and not the artwork.

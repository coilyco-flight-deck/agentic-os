# Example V. heartbeat

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

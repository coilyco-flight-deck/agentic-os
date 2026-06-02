# Rule: push short, pull long

Intro and Help share one subject. They are not the same length.

Intro is pushed - emitted on every invocation whether asked or not. It pays a context cost every run, so it stays short: a two-to-three-line head plus a pointer.

Help is pulled - loaded only when the agent runs `coily X help` because it wants to know. It pays nothing on a normal run, so it can be exhaustive.

**Why:** a pushed surface that is long taxes every invocation forever, the same failure mode as alias-packing a skill description. A pulled surface that is short forces the agent to guess or re-run. Match the length to the delivery.

**How to apply:** when writing Intro, if it runs past three lines, the overflow belongs in Help. When writing Help, do not trim it for length - it is the place length is free.

# Driving a local Qwen3 quant via Ollama

## Invocation

When calling Qwen3-4B/8B programmatically as a classifier or scorer, the OpenAI-compat `/v1/chat/completions` endpoint is a trap. Qwen3 routes its chain-of-thought into a separate `reasoning` field, ignores a `/no_think` directive, and returns an empty `content` when it hits the token cap mid-reasoning. A small `max_tokens` then yields nothing usable.

Reliable recipe - use Ollama's native `/api/chat` with two knobs:

- `"think": false` to suppress the reasoning pass (roughly 20x faster on short tasks).
- a JSON-schema `"format"` grammar to constrain output to a clean structured object that stops cleanly. For classification, an `enum` on the label field pins it to the allowed set.

## Performance profile (Qwen3 Q4, single consumer GPU)

- Warm generation - 4B around 80 tok/s, 8B around 58 tok/s. Both are real GPU speeds. A few tok/s instead means CPU fallback, usually from VRAM pressure.
- Cold load - paging the weights into VRAM costs several seconds on first call and after eviction. At trickle request rates set a long `keep_alive` (or pin the model resident) so each call does not re-pay cold load. A misleading slow-per-request number is almost always cold load, not inference.
- An 8GB card holds one of these quants resident at a time, not both. Designs that need two models continuously should share one model or sequence by schedule, not pin both.

# Driving a local Qwen3 quant via Ollama

## Invocation

When calling Qwen3-4B/8B programmatically as a classifier or scorer, the OpenAI-compat `/v1/chat/completions` endpoint is a trap. Qwen3 routes its chain-of-thought into a separate `reasoning` field, ignores a `/no_think` directive, and returns an empty `content` when it hits the token cap mid-reasoning. A small `max_tokens` then yields nothing usable.

Reliable recipe - use Ollama's native `/api/chat` with two knobs:

- `"think": false` to suppress the reasoning pass (roughly 20x faster on short tasks).
- a JSON-schema `"format"` grammar to constrain output to a clean structured object that stops cleanly. For classification, an `enum` on the label field pins it to the allowed set.

## Where the weights live

Ollama stores models as content-addressed blobs plus manifests under its models dir, not as named `.gguf` files. Default dir by host:

- **Windows** - `%USERPROFILE%\.ollama\models`.
- **Linux** - `/usr/share/ollama/.ollama/models` for the service user, or `~/.ollama/models` for a user-run daemon.
- **macOS** - `~/.ollama/models`.

`OLLAMA_MODELS` overrides the default - check it before assuming the path (`[Environment]::GetEnvironmentVariable("OLLAMA_MODELS","User")` on Windows). `ollama list` shows the served tags and sizes, `ollama ps` shows what is resident in VRAM right now. The host that actually holds the quants is a deployment detail - on Kai's fleet it is the local-LLM tower (see `machine-kai-desktop-tower`).

## Performance profile (Qwen3 Q4, single consumer GPU)

- Warm generation - 4B around 80 tok/s, 8B around 58 tok/s. Both are real GPU speeds. A few tok/s instead means CPU fallback, usually from VRAM pressure.
- Cold load - paging the weights into VRAM costs several seconds on first call and after eviction. At trickle request rates set a long `keep_alive` (or pin the model resident) so each call does not re-pay cold load. A misleading slow-per-request number is almost always cold load, not inference.
- An 8GB card holds one of these quants resident at a time, not both. Designs that need two models continuously should share one model or sequence by schedule, not pin both.

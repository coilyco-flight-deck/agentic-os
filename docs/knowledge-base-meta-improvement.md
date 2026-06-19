# Knowledge-base meta-improvement - action scratch

**Status:** scratch / WIP. Not committed yet. Action capture for the knowledge-base meta-improvement thread.

**Spawning instance (2026-06-19):** ward-kdl discovery gap. A cold `claude -p` agent asked for the Forgejo CLI command answered `coily ops forgejo issue create` (deprecated name, confident, wrong) from prior alone. When allowed to explore it self-corrected to `ward ops forgejo issue create` in ~12 turns. Lesson that generalized the thread: **stale-and-confident knowledge is strictly worse than absent**, and ecosystem speed has pushed asserted-fact half-life below hand-maintenance cadence.

**Operating frame:** grade every fact by decay class and push it down-gradient.

- **Asserted** - hand-written claim. Highest decay, no test. (the `coily ops` refs)
- **Pointer** - states where to get it fresh, not the fact. Decay near zero, defers lookup to runtime.
- **Derived** - rendered from a ground-truth source (`describe`, schema, `--help`). Cannot drift past its source, regenerable, diffable - it has a test.

---

## Action items

### 1. Detection layer - freshness CI for knowledge

The unsolved piece. Code has CI that catches drift loud. Knowledge has nothing, so rot is silent. Build the trigger that catches a rotted fact.

- Candidate primitive: scheduled cold-agent probe (the `claude -p` move from today), assert-then-verify, diff the answer against ground truth, flag drift.
- Candidate primitive: source-diff - when a self-describing surface (`ward-kdl ... describe`) changes, flag every doc that asserted the old shape.
- My read: highest leverage of the three, because classification and the generator both depend on seeing decay you currently cannot see.

### 2. Classification - audit the eager context now

Walk AGENTS.md, global CLAUDE.md, and skill descriptions for asserted-and-rotting facts. Grade each by decay class. The eager layer gets the most aggressive discipline because every agent reads it every session, so one stale fact poisons every run.

- Immediate hit list already known: 16+ stale `coily ops` references across skills and AGENTS files.
- Companion move: add provenance as a first-class field (`as-of: <date>, source: <where>`) so an agent can self-discount a stale-looking claim at runtime. `coily ops` had no as-of marker, so the cold agent had no signal it was old.

### 3. Merge point - self-describing surface to rendered generator

The reusable pattern where code meta-improvement and knowledge meta-improvement become the same lever. The surface describes itself, code renders that into agent context on every rollout, the fact cannot go stale because it is re-derived.

- Concrete instance: `ward-kdl ... describe` -> rendered reference committed to repo (travels off-disk, greppable without running the binary) -> one-line eager pointer that points at it. Regenerated at ansible/brew converge time.
- Generalize past ward-kdl: any tool whose verbs drift faster than the training cutoff and are absent from eager context is the same class.

---

---

## Dimensions added (2026-06-19, round 2)

### Half-life is a second axis, orthogonal to decay-class

Decay-class (asserted/pointer/derived) is *how* a fact is stored. Half-life is *how fast the world rewrites it*. The second decides how much machinery a fact is worth.

- **Fast-decay** (verbs, SDK APIs, model IDs, pricing, ToS) - worth the expensive solve: derive/point + freshness detection.
- **Slow-decay** (voice rules, she/her, doctrine, project shape, taste, decision-rationale) - hand-assertion is correct, maintenance cadence beats decay. Heavy machinery here is waste.

Aim freshness CI and generators only at the fast quadrant.

### Org-shape sets the affordable solve

- **Low-velocity large team** - solve is governance (ownership, review, wikis). Productized tooling targets this (Packmind, Tessl, Ruler "industrialize context at org scale").
- **High-velocity solo (Kai)** - solve is aggressive derivation + agent-as-maintainer + bake-your-own-taste. Underserved quadrant. Most off-the-shelf KM tooling does not fit.

### Three storage tiers, keyed to half-life

- **Parametric (fine-tune qwen)** - slow-decay, high-value, always-needed, context-expensive: taste, voice, doctrine, project shape, tool *shape*. Always-on, zero token cost, raises the context-budget ceiling. Cost: opaque, ungreppable, undiffable, decays silently. Safe ONLY for genuinely slow knowledge.
- **Eager context (asserted)** - slow, small, must be exact and auditable. AGENTS.md doctrine.
- **Runtime (pointer/derived via MCP/RAG)** - fast-decay. Context7 for public libs, `ward-kdl ... describe` for private tools, SSM for ids. Never baked.

### Ecosystem landscape (validated by search, past Jan-2026 cutoff)

- **Context engineering** - formalized by Anthropic Applied AI, Sept 2025. "Better prompts" era declared over by early 2026.
- **Context7** - MCP serving live library docs. Names the exact failure as "confidently using an API that changed two versions ago" - i.e. probe 1. The pointer tier, bought off the shelf.
- **Agent memory field** - mem0, LangGraph (semantic/episodic/procedural). Names "memory staleness... confidently wrong... deprecated APIs" as a "harder, open problem." Confirms no-auto-memory was right and freshness CI is an open frontier.
- **Fine-tuning gone solo-affordable** - Unsloth/Axolotl, 3-7B on a single 12GB GPU, an afternoon. "Fine-Tuned Small Models Beat RAG: The 2026 Economics."

### Build/buy line for a solo operator

- **Buy** the fast-public-knowledge layer (Context7, Exa). No reason to build live-docs-for-React.
- **Build/bake** the private slow-knowledge layer (describe-render-generator, qwen fine-tune). No product exists for Kai's taste and Kai's tools.

### Action item 4 - qwen fine-tune as context-budget buyback (GATED on item 2)

A qwen fine-tuned on the **slow-decay subset** of Kai's knowledge base is an always-on you-shaped pair, freeing the "~3 large skills at once" working-context ceiling for fast/task-specific knowledge. Trap: training on the *whole* base bakes fast-decay facts (verbs, ids) into weights = parametric staleness, the worst kind (silent, ungreppable, confidently wrong). So the fine-tune cannot start until item 2 grades knowledge by half-life. **Classification feeds the fine-tune.**

---

## Context7 + spinoff ecosystem (2026-06-19, round 3)

### Context7 itself

- By **Upstash**. Hosted oracle of up-to-date, version-specific docs for **public** libraries, served over MCP.
- Two MCP tools: `resolve-library-id` (name -> ID) then `get-library-docs` (fetch relevant sections, version-pinned). Newer **CLI + Skills** mode (`ctx7`) too, so not MCP-only.
- Backed by a private crawl-and-index engine over official docs + code examples.
- Pricing: free for public libs, Pro $7/seat/mo, private-repo parsing $25/1M tokens, API beyond free $10/1k calls. Self-host is enterprise-sales-only.
- **Architectural tell:** `resolve-id` then `get-docs` is the same primitive as `ward-kdl <group> <noun> describe` - resolve the entity, fetch its live surface. Upstash productized for the public world the exact pattern being built here for private tools.
- **Limits:** crawl-and-index (freshness bounded by crawl cadence, not truly live), closed backend, community libs carry an explicit no-accuracy guarantee, queries go to a third party. Narrows staleness, does not end it.
- **Fit:** occupies exactly one matrix cell - fast-decay x public x runtime-fetch. Useless and unsafe for private tools (collides with SSM/leak rules). For public fast-moving libs (Terraform, AWS SDK, k8s) it is a reasonable free-tier buy.

### Layer 1 - OSS self-hostable clones (zoomed, 2026-06-19) - three DIFFERENT mechanisms, one dead

- **`arabold/docs-mcp-server`** - MIT, 1.5k stars, 72 releases, v2.4.2 June 2026, active. **RAG indexer** (crawl/embed/vector-search). Embeddings optional: Ollama = fully local/offline, or keyword-only - clears the leak bar. Sources: web/GitHub/npm/PyPI/local/archives, 90+ formats incl Terraform. Probes `llms.txt`. Tools `scrape_docs`/`search`/`fetch_url`, UI :6280. **VERDICT: the real adoptable tool. Fits private-prose-at-scale.**
- **`rakuv3r/open-context7`** - MIT, 7 stars, 2 commits, no releases. RAG-over-Qdrant skeleton, abandoned. **VERDICT: dead, skip. docs-mcp-server dominates it.**
- **`yamadashy/repomix`** - MIT, 26.4k stars, 97 releases, most mature by far. **NOT RAG - a packer.** Renders a repo into one LLM artifact (XML/MD/JSON), tree-sitter ~70% token cut, MCP `pack_codebase`/`grep_repomix_output`/`read_repomix_output`. Deterministic snapshot at pack-time, no index. Built-in Secretlint (matches leak discipline), emits Claude Agent Skills format, fully local. **NOT Context7-compatible (earlier claim was wrong).** **VERDICT: the surprise - closest off-the-shelf cousin of the describe-render-generator. Fits bounded private surfaces (tools, skills, AGENTS files) better than RAG, which would re-add index-lag staleness.**
- **ContextMCP** (contextmcp.ai) - not evaluated; OSS status unverified.

**Cell mapping:** big private prose corpus needing semantic search -> docs-mcp-server (RAG). Bounded private surface wanting a deterministic fresh snapshot -> repomix (pack). Live binary surface (verbs) -> still bespoke `describe`-generator, the one part repomix cannot do.

### Repomix -> docs-mcp-server pipeline (Kai's idea, 2026-06-19)

Compose them as two stages, not competitors: **Repomix = ETL** (curate / Secretlint-scrub / tree-sitter-compress) -> **docs-mcp-server = load+serve** (embed + semantic retrieval). Derive-then-index hybrid: a deterministic scrubbed snapshot feeds RAG.

- **Why specifically for Kai:** docs-mcp-server can ingest local files directly, so Repomix-in-front is needless middleware for most. It earns its place on the leak constraint - Secretlint scrubs before anything embeds, so the vector store provably never holds an opaque id. agentic-os-kai is leak-tolerant + SSM-id-dense, so the scrub gate is the difference between a trustable index and not.
- **Caveat to verify:** do not flatten to one blob then index - hurts chunk boundaries. Feed Repomix **structured** (XML/JSON, per-file) output and confirm the indexer chunks on those boundaries.
- **When to drop stage 2:** bounded surface that fits budget after compression -> Repomix-pack straight into context, skip the indexer. RAG only earns its keep when the corpus is too big to hold.
- **Bonus:** the pack doubles as the provenance/as-of marker action item 2 wanted - the index knows which pack, from when.
- **Decision rule:** large+leaky+needs-search -> pipeline. bounded+leaky -> repomix-pack only. live-binary -> describe-generator.

### Layer 2 - hosted competitors

- **Docfork** - MIT, 9,000+ libs, single-call vs Context7's two-step.
- **GitMCP** - give it a GitHub URL, hits GitHub API directly, privacy-framed.
- **Deepcon** - claims 90% accuracy vs Context7's 65%, ~1k tokens/response.
- **Nia, Ref.Tools** - commercial, same lane.

### Layer 3 - the deep spinoff: `llms.txt` supply-side standard

Context7 is the consumption side. `llms.txt` is the supply side - a sitemap-for-LLMs convention sites publish so agents get clean structured docs instead of scraping HTML. Tooling: Mintlify (auto-gen llms.txt/llms-full.txt/per-page .md), Firecrawl `llmstxt-generator`, llms-txt.io, docusaurus-plugin-llms, mkdocs-llmstxt. Adoption registry at directory.llmstxt.cloud.

### Frame updates from the ecosystem

- **The "build" column is now partly buy.** The private-tools cell is no longer all bespoke: self-hosted clones (docs-mcp-server, open-context7, Repomix) index private repos leak-safe. May not need to build a private-docs indexer from scratch.
- **RAG-indexer vs derived-describe is load-bearing.** The clones are RAG-over-docs (crawl, embed, vector-search, reindex) - fits private **prose** (markdown docs, FEATURES, skill bodies at scale), but lags its own index. `ward-kdl describe` is **derived** - deterministic, zero index, always live - fits **structured tool surfaces**. So the private-fast-decay tier splits:
  - Private prose docs -> self-hosted Context7 clone (RAG). Buy.
  - Private structured tool surfaces (verbs) -> describe-render-generator. Build. RAG here would re-introduce staleness over a surface queryable live for free.
- **Supply-side move:** publish `llms.txt`/`llms-full.txt` from own repos, auto-generated at converge time - the regeneration pattern from action item 3, applied to docs.

---

## Constraints / open tensions

- **Derive-vs-point budget.** Deriving everything is heavy. Pointing everything makes every session pay runtime lookup cost, and that cost is already metered (`ward exec context-budget`). Decay-class assignment is an optimization under a token budget, not a blanket rule.
- **Already-latent discipline.** SSM cache-on-first-lookup (derived ids), no-auto-memory (rejected the worst asserted surface), and the catalog knowledge-validators (dead-cross-links, repo-pointer-skills) are this discipline already running. The gap is the positive program, not the instinct.

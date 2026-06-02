# skillsmp API at a glance

Base: `https://skillsmp.com/api/v1/skills`

Auth: handled by `coily skillsmp` (see [`workflow-search.md`](workflow-search.md) step 1). The bearer token lives in AWS SSM at `/skillsmp/api-key` (SecureString); the wrapper fetches it per call through the audited shell.Runner, so the key never ends up in a session env var or the audit log.

Rate limits: **500 requests/day, 30 requests/min.** Budget accordingly.

Response envelope:
```json
{ "success": true, "data": { ... }, "meta": { "requestId": "...", "responseTimeMs": N } }
```

**Keyword search** - `GET /search?q=<query>&sortBy=stars` - returns `data.skills[]` with fields:

- `id` - stable identifier (slug-like, includes author/repo/path).
- `name` - the skill's own name.
- `author` - GitHub org/user that published it.
- `description` - from the skill's SKILL.md frontmatter.
- `githubUrl` - full GitHub URL, usually a `.../tree/main/...` path to the skill's dir.
- `skillUrl` - public page on skillsmp.com. **The URL you show the user to inspect.**
- `stars` - **stars of the host repo, not the skill** - see caveats below.
- `updatedAt` - unix timestamp string.

plus `data.pagination` (`page, limit, total, totalPages, hasNext, hasPrev`).

**AI search** - `GET /ai-search?q=<natural language>` - semantic search returning an OpenAI-vector-store-style response (`data.data[]`). Try if keyword search comes up empty.

**Skill detail** - no individual GET endpoint exists. The search response already has everything needed (description, githubUrl, skillUrl). Don't waste requests trying to fetch a detail endpoint.

## Caveats about `stars`

`stars` is the GitHub star count of the repo the skill lives in, not the skill itself. A skill inside a collection repo (`someorg/awesome-skills`) inherits the whole repo's stars, so a 30k-star skill from a massive collection isn't more vetted than a 50-star one from a focused repo.

Use `stars >= 5` as a weak first-pass filter to cull abandoned repos, but don't treat high stars as a safety signal. Real vetting happens in [`workflow-vetting.md`](workflow-vetting.md).

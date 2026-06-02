# Workflow steps 1-2: auth and search

## Step 1: Auth is handled by `coily skillsmp`

There is no env-var setup. Every call goes through `coily skillsmp <verb> ...`, which fetches `/skillsmp/api-key` from SSM per call and adds it as a Bearer token. Same flow on Mac and Windows (MSYS path-mangling is solved inside the wrapper).

If the wrapper fails with `ParameterNotFound`, the key hasn't been provisioned on this account. Tell the user once:

> `/skillsmp/api-key` isn't set in SSM on this account. Put it there with `coily ops aws ssm put-parameter --name /skillsmp/api-key --type SecureString --value "$SKILLSMP_API_KEY"` (set the env var locally first - don't paste the key into chat), then ask me again.

If the wrapper fails with auth errors (`UnauthorizedOperation`, expired creds), tell the user their AWS creds need refreshing and stop. Don't retry blindly.

One mention per conversation - don't nag.

## Step 2: Search

Pick the shortest keyword that captures the capability (e.g. `postmark`, `edifact`, `google-calendar`). Query:

```sh
coily skillsmp search <query>
```

**Exact-match filter (client-side):** the API doesn't support exact match - `match=exact` is silently ignored. Filter in your head: keep only results where `name` equals the query (case-insensitive), or where the query appears as a whole word in `name`/`description`. For a query like `postmark`, `postmark-automation` and `postmark-webhooks` both qualify; a skill named `email-sender` that happens to mention Postmark in its description should not.

**Star-floor filter (client-side):** drop anything with `stars < 5`. The API has no `minStars` param.

If nothing clears both filters, try:
- `ai-search` with a natural-language phrasing: `coily skillsmp ai-search <phrase>`
- a broader keyword

If still nothing, report to the user ("No marketplace skill at ≥5 stars matches - want me to just do it from scratch, or search differently?") and stop.

Next: [Step 3 automated vetting](workflow-vetting.md).

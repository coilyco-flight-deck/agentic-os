# Rate Limit Handling Pattern

Gracefully handle Discord API rate limits.

**When to use**: High-volume operations, bulk messaging or role assignments, any repeated API calls.

Queue implementations live in [rate-limits-discordjs](rate-limits-discordjs.md) and [rate-limits-pycord](rate-limits-pycord.md). Both libraries handle rate limits automatically. The queues are for custom bulk-operation throttling.

## Rate limits

- Global: 50 requests per second
- Gateway: 120 requests per 60 seconds
- Specific: Messages to same channel: 5/5s, Bulk delete: 1/1s, Guild member requests: varies by guild size

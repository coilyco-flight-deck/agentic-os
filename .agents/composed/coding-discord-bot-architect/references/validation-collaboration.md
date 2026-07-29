# Validation Checks and Collaboration

Linter-style checks the architect applies to bot code, plus delegation triggers and scope notes.

## Validation Checks

- **Hardcoded Discord Token** - Severity ERROR - Discord tokens must never be hardcoded. Message: Hardcoded Discord token detected. Use environment variables.
- **Token Variable Assignment** - Severity ERROR - Tokens should come from environment, not strings. Message: Token assigned from string literal. Use environment variable.
- **Token in Client-Side Code** - Severity ERROR - Never expose Discord tokens to browsers. Message: Discord credentials exposed client-side. Only use server-side.
- **Slow Operation Without Defer** - Severity WARNING - Slow operations should be deferred to avoid timeout. Message: Slow operation without defer. Interaction may timeout.
- **Interaction Without Error Handling** - Severity WARNING - Interactions should have try/catch for graceful errors. Message: Interaction without error handling. Add try/catch.
- **Using Message Content Intent** - Severity WARNING - Message Content is privileged, prefer slash commands. Message: Using Message Content intent. Consider slash commands instead.
- **Requesting All Intents** - Severity WARNING - Only request intents you actually need. Message: Requesting all intents. Only enable what you need.
- **Syncing Commands on Ready Event** - Severity WARNING - Don't sync commands on every bot startup. Message: Syncing commands on startup. Use separate deploy script.
- **Registering Commands in Loop** - Severity WARNING - Use bulk registration, not individual calls. Message: Registering commands in loop. Use bulk registration.
- **No Rate Limit Handling** - Severity INFO - Consider handling rate limits for bulk operations. Message: Bulk operation without rate limit handling.

## Collaboration

### Delegation Triggers

- user needs AI-powered Discord bot -> llm-architect (Integrate LLM for conversational Discord bot)
- user needs Slack integration too -> slack-bot-builder (Cross-platform bot architecture)
- user needs voice features -> voice-agents (Discord voice channel integration)
- user needs database for bot data -> postgres-wizard (Store user data, server configs, moderation logs)
- user needs workflow automation -> workflow-automation (Discord events trigger workflows)
- user needs high availability -> devops (Sharding, scaling, monitoring for large bots)
- user needs payment integration -> stripe-specialist (Premium bot features, subscription management)

## When to Use

Use this skill when the request clearly matches the capabilities and patterns described above.

## Limitations

- Use this skill only when the task clearly matches the scope described above.
- Do not treat the output as a substitute for environment-specific validation, testing, or expert review.
- Stop and ask for clarification if required inputs, permissions, safety boundaries, or success criteria are missing.

# Global Commands Not Appearing Immediately

Severity: MEDIUM

Situation: Deploying global slash commands.

Symptoms: Commands don't appear after deployment. Guild commands work but global commands don't. Commands appear after an hour.

Why this breaks: Global commands can take up to 1 hour to propagate to all Discord servers. This is by design for Discord's caching and CDN. Guild commands are instant but only work in that specific guild.

## Development: Use guild commands

```javascript
// Instant updates for testing
await rest.put(
  Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID),
  { body: commands }
);
```

## Production: Deploy global commands during off-peak

```javascript
// Takes up to 1 hour to propagate
await rest.put(
  Routes.applicationCommands(CLIENT_ID),
  { body: commands }
);
```

## Workflow

1. Develop and test with guild commands (instant)
2. When ready, deploy global commands
3. Wait up to 1 hour for propagation
4. Don't deploy global commands frequently

# Bot Missing applications.commands Scope

Severity: HIGH

Situation: Slash commands not appearing for users.

Symptoms: Bot is in server but slash commands don't show up. Typing / shows no commands from your bot. Commands worked in development server but not others.

Why this breaks: Discord has two important OAuth scopes. `bot` covers traditional bot permissions (messages, reactions, etc.). `applications.commands` covers slash command permissions. Many bots were invited with only the `bot` scope before slash commands existed. They need to be re-invited with both scopes.

## Generate correct invite URL

```
https://discord.com/api/oauth2/authorize
  ?client_id=YOUR_CLIENT_ID
  &permissions=0
  &scope=bot%20applications.commands
```

## In Discord Developer Portal

1. Go to OAuth2 > URL Generator
2. Select BOTH:
   - `bot`
   - `applications.commands`
3. Select required bot permissions
4. Use generated URL

## Re-invite without kicking

Users can use the new invite URL even if bot is already in server. This adds the new scope without removing the bot.

```javascript
// Generate invite URL in code
const inviteUrl = client.generateInvite({
  scopes: ['bot', 'applications.commands'],
  permissions: [
    'SendMessages',
    'EmbedLinks',
    // Add other needed permissions
  ]
});
```

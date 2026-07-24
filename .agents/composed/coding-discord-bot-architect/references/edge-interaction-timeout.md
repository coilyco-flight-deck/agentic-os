# Interaction Timeout (3 Second Rule)

Severity: CRITICAL

Situation: Handling slash commands, buttons, select menus, or modals.

Symptoms: User sees "This interaction failed" or "The application did not respond." Command works locally but fails in production. Slow operations never complete.

Why this breaks: Discord requires ALL interactions to be acknowledged within 3 seconds (slash commands, button clicks, select menu selections, context menu commands). If you do ANY slow operation (database, API, file I/O) before responding, you miss the window. Discord shows an error even if your bot processes the request correctly afterward. After acknowledgment, you have 15 minutes for follow-up responses.

## Acknowledge immediately, process later

```javascript
// Discord.js - Defer for slow operations
module.exports = {
  async execute(interaction) {
    // DEFER IMMEDIATELY - before any slow operation
    await interaction.deferReply();
    // For ephemeral: await interaction.deferReply({ ephemeral: true });

    // Now you have 15 minutes
    const result = await slowDatabaseQuery();
    const aiResponse = await callLLM(result);

    // Edit the deferred reply
    await interaction.editReply(`Result: ${aiResponse}`);
  }
};
```

```python
# Pycord
@bot.slash_command()
async def slow_command(ctx):
    await ctx.defer()  # Acknowledge immediately
    # await ctx.defer(ephemeral=True)  # For private response

    result = await slow_operation()
    await ctx.followup.send(f"Result: {result}")
```

## For components (buttons, menus)

```javascript
// If you're updating the message
await interaction.deferUpdate();

// If you're sending a new response
await interaction.deferReply({ ephemeral: true });
```

# Deferred Response Pattern

Handle slow operations without timing out.

**When to use**: Operation takes more than 3 seconds, database queries, API calls, LLM responses, file processing or generation.

```javascript
// Discord.js - Deferred response
module.exports = {
  data: new SlashCommandBuilder()
    .setName('slow-task')
    .setDescription('Performs a slow operation'),

  async execute(interaction) {
    // Defer immediately - you have 3 seconds!
    await interaction.deferReply();
    // For ephemeral: await interaction.deferReply({ ephemeral: true });

    try {
      // Now you have 15 minutes to complete
      const result = await slowDatabaseQuery();
      const aiResponse = await callOpenAI(result);

      // Edit the deferred reply
      await interaction.editReply({
        content: `Result: ${aiResponse}`,
        embeds: [resultEmbed]
      });
    } catch (error) {
      await interaction.editReply({
        content: 'An error occurred while processing your request.'
      });
    }
  }
};

// For components (buttons, select menus)
collector.on('collect', async i => {
  await i.deferUpdate();  // Acknowledge without visual change
  // Or: await i.deferReply({ ephemeral: true });

  const result = await slowOperation();
  await i.editReply({ content: result });
});
```

```python
# Pycord - Deferred response
@bot.slash_command(name="slow-task")
async def slow_task(ctx: discord.ApplicationContext):
    # Defer immediately
    await ctx.defer()
    # For ephemeral: await ctx.defer(ephemeral=True)

    try:
        result = await slow_database_query()
        ai_response = await call_openai(result)

        await ctx.followup.send(f"Result: {ai_response}")
    except Exception as e:
        await ctx.followup.send("An error occurred")
```

## Timing

- Initial response: 3 seconds
- Deferred followup: 15 minutes
- Ephemeral note: Can only be set on initial response, not changed later

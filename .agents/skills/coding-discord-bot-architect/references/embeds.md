# Embed Builder Pattern

Rich embedded messages for professional-looking content.

**When to use**: Displaying formatted information, status updates, help menus, logs, data with structure (fields, images).

```javascript
const { EmbedBuilder, Colors } = require('discord.js');

// Basic embed
const embed = new EmbedBuilder()
  .setColor(Colors.Blue)
  .setTitle('Bot Status')
  .setURL('https://example.com')
  .setAuthor({
    name: 'Bot Name',
    iconURL: client.user.displayAvatarURL()
  })
  .setDescription('Current status and statistics')
  .addFields(
    { name: 'Servers', value: `${client.guilds.cache.size}`, inline: true },
    { name: 'Users', value: `${client.users.cache.size}`, inline: true },
    { name: 'Uptime', value: formatUptime(), inline: true }
  )
  .setThumbnail(client.user.displayAvatarURL())
  .setImage('https://example.com/banner.png')
  .setTimestamp()
  .setFooter({
    text: 'Requested by User',
    iconURL: interaction.user.displayAvatarURL()
  });

await interaction.reply({ embeds: [embed] });

// Multiple embeds (max 10)
await interaction.reply({ embeds: [embed1, embed2, embed3] });
```

```python
# Pycord
embed = discord.Embed(
    title="Bot Status",
    description="Current status and statistics",
    color=discord.Color.blue(),
    url="https://example.com"
)
embed.set_author(
    name="Bot Name",
    icon_url=bot.user.display_avatar.url
)
embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
embed.add_field(name="Users", value=len(bot.users), inline=True)
embed.set_thumbnail(url=bot.user.display_avatar.url)
embed.set_image(url="https://example.com/banner.png")
embed.set_footer(text="Requested by User", icon_url=ctx.author.display_avatar.url)
embed.timestamp = discord.utils.utcnow()

await ctx.respond(embed=embed)
```

## Limits

- 10 embeds per message
- 6000 characters total across all embeds
- 256 characters for title
- 4096 characters for description
- 25 fields per embed
- 256 characters per field name
- 1024 characters per field value

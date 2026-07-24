# Command Registration Rate Limited

Severity: HIGH

Situation: Registering slash commands.

Symptoms: Commands not appearing. 429 errors when deploying. "You are being rate limited" messages. Commands appear for some guilds but not others.

Why this breaks: Command registration is rate limited. Global commands: 200 creates/day, updates take up to 1 hour to propagate. Guild commands: 200 creates/day per guild, instant update. Common mistakes: registering commands on every bot startup, registering in every guild separately, making changes in a loop without delays.

## Use a separate deploy script (not on startup)

```javascript
// deploy-commands.js - Run manually, not on bot start
const { REST, Routes } = require('discord.js');

const rest = new REST().setToken(process.env.DISCORD_TOKEN);

async function deploy() {
  // For development: Guild commands (instant)
  if (process.env.GUILD_ID) {
    await rest.put(
      Routes.applicationGuildCommands(
        process.env.CLIENT_ID,
        process.env.GUILD_ID
      ),
      { body: commands }
    );
    console.log('Guild commands deployed instantly');
  }

  // For production: Global commands (up to 1 hour)
  else {
    await rest.put(
      Routes.applicationCommands(process.env.CLIENT_ID),
      { body: commands }
    );
    console.log('Global commands deployed (may take up to 1 hour)');
  }
}

deploy();
```

```python
# Pycord - Don't sync on every startup
@bot.event
async def on_ready():
    # DON'T DO THIS:
    # await bot.sync_commands()

    print(f"Ready! Commands should already be registered.")

# Instead, sync manually or use a flag
if __name__ == "__main__":
    if "--sync" in sys.argv:
        # Only sync when explicitly requested
        bot.sync_commands_on_start = True
    bot.run(token)
```

## Testing workflow

1. Use guild commands during development (instant updates)
2. Only deploy global commands when ready for production
3. Run deploy script manually, not on every restart

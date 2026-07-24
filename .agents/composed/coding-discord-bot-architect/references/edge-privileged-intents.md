# Missing Privileged Intent Configuration

Severity: CRITICAL

Situation: Bot needs member data, presences, or message content.

Symptoms: Members intent: member lists empty, on_member_join doesn't fire. Presences intent: statuses always unknown/offline. Message content intent: message.content is empty string.

Why this breaks: Discord has 3 privileged intents that require manual enablement:
1. **GUILD_MEMBERS** - Member join/leave, member lists
2. **GUILD_PRESENCES** - Online status, activities
3. **MESSAGE_CONTENT** - Read message text (deprecated for commands)

These must be enabled in Discord Developer Portal > Bot > Privileged Gateway Intents AND requested in your bot code. At 100+ servers, you need Discord verification to keep using them.

## Step 1: Enable in Developer Portal

```
1. Go to https://discord.com/developers/applications
2. Select your application
3. Go to Bot section
4. Scroll to Privileged Gateway Intents
5. Toggle ON the intents you need
```

## Step 2: Request in code

```javascript
// Discord.js
const { Client, GatewayIntentBits } = require('discord.js');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,       // PRIVILEGED
    // GatewayIntentBits.GuildPresences,  // PRIVILEGED
    // GatewayIntentBits.MessageContent,  // PRIVILEGED - avoid!
  ]
});
```

```python
# Pycord
intents = discord.Intents.default()
intents.members = True       # PRIVILEGED
# intents.presences = True   # PRIVILEGED
# intents.message_content = True  # PRIVILEGED - avoid!

bot = commands.Bot(intents=intents)
```

## Avoid Message Content Intent if possible

Use slash commands, buttons, and modals instead of message parsing. These don't require the Message Content intent.

# Patterns

Full pattern catalogue for Discord bots. Each entry covers the Discord.js (JavaScript) and Pycord (Python) shapes side by side.

## Foundations

- [foundation-discordjs](foundation-discordjs.md) - Discord.js v14 client setup with command and event loaders.
- [foundation-discordjs-commands](foundation-discordjs-commands.md) - Discord.js slash command handler and interaction-dispatch event.
- [foundation-discordjs-deploy](foundation-discordjs-deploy.md) - Standalone Discord.js command-registration script.
- [foundation-pycord](foundation-pycord.md) - Pycord (Python) bot setup with application commands.
- [foundation-pycord-cog](foundation-pycord-cog.md) - Pycord command-group cog example.

## Interaction patterns

- [components](components.md) - Interactive components overview and limits.
- [components-discordjs](components-discordjs.md) - Discord.js buttons, select menus, and modal forms.
- [components-pycord](components-pycord.md) - Pycord views, selects, and modals.
- [deferred-response](deferred-response.md) - Defer slow operations to beat the 3-second timeout.
- [embeds](embeds.md) - Rich embedded messages and their character limits.

## Scaling and reliability

- [rate-limits](rate-limits.md) - Rate-limit ceilings, with [Discord.js](rate-limits-discordjs.md) and [Pycord](rate-limits-pycord.md) queue implementations.
- [sharding](sharding.md) - Scale past 2500 guilds, with [Discord.js](sharding-discordjs.md) and [Pycord](sharding-pycord.md) implementations.

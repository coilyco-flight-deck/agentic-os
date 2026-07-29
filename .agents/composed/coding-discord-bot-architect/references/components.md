# Interactive Components Pattern

Using buttons, select menus, and modals for rich UX.

**When to use**: Need interactive user interfaces, collecting user input beyond slash command options, building menus, confirmations, or forms.

- [components-discordjs](components-discordjs.md) - Discord.js buttons and select menus.
- [components-discordjs-modals](components-discordjs-modals.md) - Discord.js modal forms and submission handling.
- [components-pycord](components-pycord.md) - Pycord views, confirm dialogs, and selects.
- [components-pycord-modals](components-pycord-modals.md) - Pycord modal forms.

## Limits

- 5 ActionRows per message/modal
- 5 buttons per ActionRow
- 1 select menu per ActionRow (takes all 5 slots)
- 5 select menus max per message
- 25 options per select menu
- Modal must be first response (cannot defer first)

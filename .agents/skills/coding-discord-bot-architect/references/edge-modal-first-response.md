# Modal Must Be First Response

Severity: MEDIUM

Situation: Showing a modal from a slash command or button.

Symptoms: "Interaction has already been acknowledged" error. Modal doesn't appear. Works sometimes but not others.

Why this breaks: Modals have a special requirement: showing a modal MUST be the first response to an interaction. You cannot defer() then showModal(), reply() then showModal(), or think for more than 3 seconds then showModal().

## Show modal immediately

```javascript
// CORRECT - modal is first response
async execute(interaction) {
  const modal = new ModalBuilder()
    .setCustomId('my-modal')
    .setTitle('Input Form');

  // Show immediately - no defer, no reply first
  await interaction.showModal(modal);
}
```

```javascript
// WRONG - deferred first
async execute(interaction) {
  await interaction.deferReply();  // CAN'T DO THIS
  await interaction.showModal(modal);  // Will fail
}
```

## If you need to check something first

```javascript
async execute(interaction) {
  // Quick sync check is OK (under 3 seconds)
  if (!hasPermission(interaction.user.id)) {
    return interaction.reply({
      content: 'No permission',
      ephemeral: true
    });
  }

  // Show modal (still first interaction response for this path)
  await interaction.showModal(modal);
}
```

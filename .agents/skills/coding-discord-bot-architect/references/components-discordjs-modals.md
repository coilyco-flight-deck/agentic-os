# Discord.js Modal Forms

Modal form and submission handling. See [components-discordjs](components-discordjs.md) for buttons and select menus.

```javascript
// Modals (forms)
const {
  SlashCommandBuilder,
  ActionRowBuilder,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle
} = require('discord.js');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('feedback')
    .setDescription('Submit feedback'),

  async execute(interaction) {
    const modal = new ModalBuilder()
      .setCustomId('feedback-modal')
      .setTitle('Submit Feedback');

    const titleInput = new TextInputBuilder()
      .setCustomId('feedback-title')
      .setLabel('Title')
      .setStyle(TextInputStyle.Short)
      .setRequired(true)
      .setMaxLength(100);

    const bodyInput = new TextInputBuilder()
      .setCustomId('feedback-body')
      .setLabel('Your feedback')
      .setStyle(TextInputStyle.Paragraph)
      .setRequired(true)
      .setMaxLength(1000)
      .setPlaceholder('Describe your feedback...');

    modal.addComponents(
      new ActionRowBuilder().addComponents(titleInput),
      new ActionRowBuilder().addComponents(bodyInput)
    );

    // Show modal - MUST be first response
    await interaction.showModal(modal);
  }
};

// Handle modal submission in interactionCreate
if (interaction.isModalSubmit()) {
  if (interaction.customId === 'feedback-modal') {
    const title = interaction.fields.getTextInputValue('feedback-title');
    const body = interaction.fields.getTextInputValue('feedback-body');

    await interaction.reply({
      content: `Thanks for your feedback!\n**${title}**\n${body}`,
      ephemeral: true
    });
  }
}
```

# Pycord Modals

Modal form with input fields. See [components-pycord](components-pycord.md) for views and selects.

```python
import discord

class FeedbackModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Submit Feedback")

        self.add_item(discord.ui.InputText(
            label="Title",
            style=discord.InputTextStyle.short,
            required=True,
            max_length=100
        ))
        self.add_item(discord.ui.InputText(
            label="Feedback",
            style=discord.InputTextStyle.long,
            required=True,
            max_length=1000
        ))

    async def callback(self, interaction):
        title = self.children[0].value
        body = self.children[1].value
        await interaction.response.send_message(
            f"Thanks!\n**{title}**\n{body}",
            ephemeral=True
        )

@bot.slash_command(name="feedback")
async def feedback(ctx: discord.ApplicationContext):
    await ctx.send_modal(FeedbackModal())
```

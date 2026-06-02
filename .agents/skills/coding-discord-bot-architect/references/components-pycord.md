# Pycord Views and Selects

Buttons, confirm views, and select menus. See [components](components.md) for limits. Modals live in [components-pycord-modals](components-pycord-modals.md).

```python
# Pycord - Buttons and Views
import discord

class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, button, interaction):
        self.value = True
        await interaction.response.edit_message(content="Confirmed!", view=None)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, button, interaction):
        self.value = False
        await interaction.response.edit_message(content="Cancelled", view=None)
        self.stop()

@bot.slash_command(name="confirm")
async def confirm_cmd(ctx: discord.ApplicationContext):
    view = ConfirmView()
    await ctx.respond("Are you sure?", view=view)

    await view.wait()  # Wait for user interaction
    if view.value is None:
        await ctx.followup.send("Timed out")

# Select Menu
class RoleSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Developer", value="dev", emoji="💻"),
            discord.SelectOption(label="Designer", value="design", emoji="🎨"),
        ]
        super().__init__(
            placeholder="Select roles...",
            min_values=1,
            max_values=2,
            options=options
        )

    async def callback(self, interaction):
        await interaction.response.send_message(
            f"You selected: {', '.join(self.values)}",
            ephemeral=True
        )

class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(RoleSelect())
```

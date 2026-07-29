# Pycord Cog Example

A command-group cog for the [Pycord foundation](foundation-pycord.md). Loaded via `bot.load_extension`.

```python
# cogs/general.py
import discord
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="info", description="Bot information")
    async def info(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="Bot Info",
            description="A helpful Discord bot",
            color=discord.Color.blue()
        )
        embed.add_field(name="Servers", value=len(self.bot.guilds))
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms")
        await ctx.respond(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Requires Members intent (PRIVILEGED)
        channel = member.guild.system_channel
        if channel:
            await channel.send(f"Welcome {member.mention}!")

def setup(bot):
    bot.add_cog(General(bot))
```

# Pycord Sharding

AutoShardedBot handles sharding automatically. See [sharding](sharding.md) for the scaling guide.

```python
# Pycord - AutoShardedBot
import discord
from discord.ext import commands

# Automatically handles sharding
bot = commands.AutoShardedBot(
    command_prefix="!",
    intents=discord.Intents.default(),
    shard_count=None  # Auto-determine
)

@bot.event
async def on_ready():
    print(f"Logged in on {len(bot.shards)} shards")
    for shard_id, shard in bot.shards.items():
        print(f"Shard {shard_id}: {shard.latency * 1000:.2f}ms")

@bot.event
async def on_shard_ready(shard_id):
    print(f"Shard {shard_id} is ready")

# Get guilds per shard
for shard_id, guilds in bot.guilds_by_shard().items():
    print(f"Shard {shard_id}: {len(guilds)} guilds")
```

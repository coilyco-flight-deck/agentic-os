# Discord.js Sharding

Sharding manager plus cross-shard helpers. See [sharding](sharding.md) for the scaling guide.

```javascript
// Discord.js Sharding Manager
// shard.js (main entry)
const { ShardingManager } = require('discord.js');

const manager = new ShardingManager('./bot.js', {
  token: process.env.DISCORD_TOKEN,
  totalShards: 'auto',  // Discord determines optimal count
  // Or specify: totalShards: 4
});

manager.on('shardCreate', shard => {
  console.log(`Launched shard ${shard.id}`);

  shard.on('ready', () => {
    console.log(`Shard ${shard.id} ready`);
  });

  shard.on('disconnect', () => {
    console.log(`Shard ${shard.id} disconnected`);
  });
});

manager.spawn();

// bot.js - Modified for sharding
const { Client } = require('discord.js');

const client = new Client({ intents: [...] });

// Get shard info
client.on('ready', () => {
  console.log(`Shard ${client.shard.ids[0]} ready with ${client.guilds.cache.size} guilds`);
});

// Cross-shard data
async function getTotalGuilds() {
  const results = await client.shard.fetchClientValues('guilds.cache.size');
  return results.reduce((acc, count) => acc + count, 0);
}

// Broadcast to all shards
async function broadcastMessage(channelId, message) {
  await client.shard.broadcastEval(
    (c, { channelId, message }) => {
      const channel = c.channels.cache.get(channelId);
      if (channel) channel.send(message);
    },
    { context: { channelId, message } }
  );
}
```

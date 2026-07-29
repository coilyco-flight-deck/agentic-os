# Frequent Gateway Disconnections

Severity: MEDIUM

Situation: Bot randomly goes offline or misses events.

Symptoms: Bot shows as offline intermittently. Events are missed (member joins, messages). Reconnection messages in logs.

Why this breaks: Discord gateway requires regular heartbeats. Issues include blocking operations preventing heartbeat, network instability, memory pressure causing GC pauses, and too many guilds without sharding (2500+ requires sharding).

## Never block the event loop

```javascript
// BAD - blocks event loop
const data = fs.readFileSync('file.json');

// GOOD - async
const data = await fs.promises.readFile('file.json');
```

## Handle reconnections gracefully

```javascript
client.on('shardResume', (id, replayedEvents) => {
  console.log(`Shard ${id} resumed, replayed ${replayedEvents} events`);
});

client.on('shardDisconnect', (event, id) => {
  console.log(`Shard ${id} disconnected`);
});

client.on('shardReconnecting', (id) => {
  console.log(`Shard ${id} reconnecting...`);
});
```

## Implement sharding at scale

```javascript
// Required at 2500+ guilds
const manager = new ShardingManager('./bot.js', {
  token: process.env.DISCORD_TOKEN,
  totalShards: 'auto'
});
manager.spawn();
```

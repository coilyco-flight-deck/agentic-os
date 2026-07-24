# Sharding Pattern

Scale bots to 2500+ servers with sharding.

**When to use**: Bot approaching 2500 guilds (required), want horizontal scaling, memory optimization for large bots.

Implementations live in [sharding-discordjs](sharding-discordjs.md) and [sharding-pycord](sharding-pycord.md).

## Scaling guide

- 1-2500 guilds: No sharding required
- 2500+ guilds: Sharding required by Discord
- Recommended: ~1000 guilds per shard
- Memory: Each shard runs in separate process

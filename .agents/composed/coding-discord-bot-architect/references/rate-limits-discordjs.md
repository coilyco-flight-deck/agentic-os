# Discord.js Rate Limit Queue

Custom rate-limit handling and a bulk-operation queue. See [rate-limits](rate-limits.md) for the ceilings.

```javascript
// Discord.js handles rate limits automatically, but for custom handling:
const { REST } = require('discord.js');

const rest = new REST({ version: '10' })
  .setToken(process.env.DISCORD_TOKEN);

rest.on('rateLimited', (info) => {
  console.log(`Rate limited! Retry after ${info.retryAfter}ms`);
  console.log(`Route: ${info.route}`);
  console.log(`Global: ${info.global}`);
});

// Queue pattern for bulk operations
class RateLimitQueue {
  constructor() {
    this.queue = [];
    this.processing = false;
    this.requestsPerSecond = 40; // Safe margin below 50
  }

  async add(operation) {
    return new Promise((resolve, reject) => {
      this.queue.push({ operation, resolve, reject });
      this.process();
    });
  }

  async process() {
    if (this.processing || this.queue.length === 0) return;
    this.processing = true;

    while (this.queue.length > 0) {
      const { operation, resolve, reject } = this.queue.shift();

      try {
        const result = await operation();
        resolve(result);
      } catch (error) {
        reject(error);
      }

      // Throttle: ~40 requests per second
      await new Promise(r => setTimeout(r, 1000 / this.requestsPerSecond));
    }

    this.processing = false;
  }
}

const queue = new RateLimitQueue();

// Usage: Send 200 messages without hitting rate limits
for (const user of users) {
  await queue.add(() => user.send('Welcome!'));
}
```

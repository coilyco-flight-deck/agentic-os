# Pycord Rate Limit Queue

Custom rate-limit handling and a bulk-operation queue. See [rate-limits](rate-limits.md) for the ceilings.

```python
# Pycord/discord.py handles rate limits automatically
# For custom handling:
import asyncio
from collections import deque

class RateLimitQueue:
    def __init__(self, requests_per_second=40):
        self.queue = deque()
        self.processing = False
        self.delay = 1 / requests_per_second

    async def add(self, coro):
        future = asyncio.Future()
        self.queue.append((coro, future))
        if not self.processing:
            asyncio.create_task(self._process())
        return await future

    async def _process(self):
        self.processing = True
        while self.queue:
            coro, future = self.queue.popleft()
            try:
                result = await coro
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)
            await asyncio.sleep(self.delay)
        self.processing = False

queue = RateLimitQueue()

# Usage
for member in guild.members:
    await queue.add(member.send("Welcome!"))
```

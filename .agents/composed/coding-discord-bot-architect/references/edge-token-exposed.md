# Bot Token Exposed

Severity: CRITICAL

Situation: Storing or sharing bot token.

Symptoms: Unauthorized actions from your bot. Bot joins random servers. Bot sends spam or malicious content. "Invalid token" after Discord invalidates it.

Why this breaks: Your bot token provides FULL control over your bot. Attackers can send messages as your bot, join servers, create invites, access all data your bot can access, and potentially take over servers where the bot has admin. Discord actively scans GitHub for exposed tokens and invalidates them. Common exposure points: committed to Git, shared in Discord itself, in client-side code, in public screenshots.

## Never hardcode tokens

```javascript
// BAD - never do this
const token = 'MTIzNDU2Nzg5MDEyMzQ1Njc4.ABCDEF.xyz...';

// GOOD - environment variables
require('dotenv').config();
client.login(process.env.DISCORD_TOKEN);
```

## Use .gitignore

```
# .gitignore
.env
.env.local
config.json
```

## If token is exposed

1. Go to Developer Portal immediately
2. Regenerate the token
3. Update all deployments
4. Review bot activity for unauthorized actions
5. Check git history and force push to remove if needed

## Use environment variables properly

```bash
# .env (never commit)
DISCORD_TOKEN=your_token_here
CLIENT_ID=your_client_id
```

```javascript
// Load with dotenv
require('dotenv').config();
const token = process.env.DISCORD_TOKEN;
```

# Slack PM Assistant MCP Server

An MCP server that provides Slack integration for Product Managers.

## Features

- 🔍 **Search Messages**: Find conversations across channels
- 📜 **Channel History**: Get and summarize recent activity
- 💬 **Post Messages**: Share updates and standups
- ✅ **Extract Action Items**: Identify tasks from conversations
- 🧵 **Thread Context**: Follow conversation threads
- 📊 **Channel Summaries**: Quick overview of channel activity
- 📋 **Standup Reports**: Generate standup summaries

## Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name it (e.g., "PM Assistant") and select your workspace

### 2. Configure Bot Permissions

Go to **OAuth & Permissions** and add these Bot Token Scopes:

**Required:**
- `channels:history` - View messages in public channels
- `channels:read` - View basic channel info
- `chat:write` - Post messages
- `users:read` - View user info

**Recommended:**
- `groups:history` - View messages in private channels
- `groups:read` - View private channel info
- `reactions:read` - View message reactions

**For Search (requires User Token):**
- `search:read` - Search messages

### 3. Install to Workspace

1. Go to **Install App** in your Slack app settings
2. Click "Install to Workspace"
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
4. (Optional) For search, also copy the **User OAuth Token** (starts with `xoxp-`)

### 4. Install Dependencies

```bash
npm install
```

### 5. Build

```bash
npm run build
```

### 6. Configure Environment

Set these environment variables:

```bash
export SLACK_BOT_TOKEN=xoxb-your-bot-token
export SLACK_USER_TOKEN=xoxp-your-user-token  # Optional, for search
```

### 7. Add to MCP Config

Add to your Cursor or Claude Desktop config:

```json
{
  "mcpServers": {
    "slack-pm-assistant": {
      "command": "node",
      "args": ["/path/to/slack-pm-assistant/dist/index.js"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
        "SLACK_USER_TOKEN": "xoxp-your-user-token"
      }
    }
  }
}
```

## Available Tools

### search_messages
Search for messages across Slack channels (requires user token).

```
"Search for messages about the Q2 roadmap"
"Find discussions about authentication bugs"
```

### get_channel_history
Get recent messages from a channel.

```
"Get the last 50 messages from #product-team"
"Show me what was discussed in #engineering today"
```

### get_thread
Get all replies in a thread.

```
"Get the full thread from this conversation"
```

### list_channels
List available Slack channels.

```
"List all public channels"
"Show me the private channels I'm in"
```

### get_channel_info
Get detailed information about a channel.

```
"Get info about the #platform-team channel"
```

### post_message
Post a message to a Slack channel.

```
"Post a standup update to #engineering"
"Reply to this thread with a summary"
```

### summarize_channel
Get a summary of recent channel activity.

```
"Summarize activity in #product-team for the last 24 hours"
"What's been happening in #engineering this week?"
```

### extract_action_items
Extract action items and tasks from messages.

```
"Find action items from today's #sprint-planning discussion"
"What tasks were assigned in #team-standup?"
```

### get_user_messages
Get recent messages from a specific user.

```
"Show me Sarah's messages in #product-team"
```

### find_channel_by_name
Find a channel by name.

```
"Find channels related to 'platform'"
```

### get_standup_summary
Generate a standup summary from channel activity.

```
"Generate a standup summary from #engineering"
```

## Example Usage

### Daily Standup Summary

```
"Generate a standup summary from #engineering-team for the last 24 hours, 
including who was active and what action items were discussed"
```

### Meeting Prep

```
"Summarize the #product-planning channel from the last week. 
What decisions were made and what's still being discussed?"
```

### Action Item Tracking

```
"Extract all action items from #sprint-45-planning and list them by owner"
```

### Cross-Channel Search

```
"Search for all discussions about 'API deprecation' in the last month"
```

### Post Status Update

```
"Post to #team-updates: 
🚀 Sprint 45 Complete!
- Shipped notification preferences
- Fixed 12 bugs
- Started API v2 planning"
```

## Troubleshooting

### "Missing required scope" Error

Your Slack app doesn't have the required permissions. Go to your app's **OAuth & Permissions** and add the missing scope, then reinstall the app.

### Can't See Private Channels

Ensure your bot has:
1. `groups:history` and `groups:read` scopes
2. Been invited to the private channel (`/invite @YourBotName`)

### Search Not Working

Message search requires a User Token (`xoxp-`), not just a Bot Token. Add `search:read` to your app's user token scopes.

### Rate Limiting

Slack has rate limits. If you hit them:
- The server will return an error message
- Wait a few seconds and retry
- Consider caching results for repeated queries

### Bot Can't Post

Ensure:
1. Bot has `chat:write` scope
2. Bot has been invited to the channel (`/invite @YourBotName`)

## Security

- Never commit tokens to git
- Use environment variables or secure credential storage
- Consider using a dedicated PM bot account
- Review channel access permissions regularly
- Rotate tokens if exposed

## Token Types

| Token Type | Prefix | Use Case |
|------------|--------|----------|
| Bot Token | `xoxb-` | Most operations, posting, reading |
| User Token | `xoxp-` | Message search, user-level actions |

## Rate Limits

Slack API has tier-based rate limits:

| Tier | Requests | Example Methods |
|------|----------|-----------------|
| Tier 1 | 1/min | `search.messages` |
| Tier 2 | 20/min | `chat.postMessage` |
| Tier 3 | 50/min | `conversations.history` |
| Tier 4 | 100/min | `users.info` |

The server handles rate limit errors gracefully and reports them.

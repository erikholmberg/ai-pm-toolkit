# MCP Setup Guide

A step-by-step guide to setting up MCP servers for your AI-assisted PM workflow.

## Overview

Model Context Protocol (MCP) extends AI assistants with the ability to interact with external tools. This guide covers setup for Cursor and Claude Desktop.

---

## Prerequisites

### 1. Install Node.js

MCP servers run on Node.js 18+.

```bash
# Check if you have Node.js
node --version

# If not installed, use nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
```

### 2. Get API Credentials

You'll need API tokens for each service:

#### Jira/Confluence (Atlassian)
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it "MCP Server" and copy the token
4. Note your Atlassian email and host (e.g., `yourcompany.atlassian.net`)

#### GitHub
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `read:org`, `read:project`
4. Copy the token

---

## Installation

### Step 1: Clone or Navigate to pm-toolkit

```bash
cd /path/to/pm-toolkit/mcps/servers
```

### Step 2: Install Server Dependencies

```bash
# Install Jira server
cd jira-pm-assistant
npm install
npm run build

# Install Confluence server
cd ../confluence-docs
npm install
npm run build

# Install GitHub server
cd ../github-pm-tools
npm install
npm run build
```

### Step 3: Test Locally (Optional)

```bash
# Set environment variables
export JIRA_HOST=yourcompany.atlassian.net
export JIRA_EMAIL=your-email@company.com
export JIRA_API_TOKEN=your-token

# Run the server
node dist/index.js
```

---

## Configuration

### Cursor Configuration

1. Create or edit `.cursor/mcp.json` in your home directory or project:

```json
{
  "mcpServers": {
    "jira-pm-assistant": {
      "command": "node",
      "args": ["/absolute/path/to/pm-toolkit/mcps/servers/jira-pm-assistant/dist/index.js"],
      "env": {
        "JIRA_HOST": "yourcompany.atlassian.net",
        "JIRA_EMAIL": "your-email@company.com",
        "JIRA_API_TOKEN": "your-api-token"
      }
    },
    "confluence-docs": {
      "command": "node",
      "args": ["/absolute/path/to/pm-toolkit/mcps/servers/confluence-docs/dist/index.js"],
      "env": {
        "CONFLUENCE_HOST": "yourcompany.atlassian.net",
        "CONFLUENCE_EMAIL": "your-email@company.com",
        "CONFLUENCE_API_TOKEN": "your-api-token"
      }
    },
    "github-pm-tools": {
      "command": "node",
      "args": ["/absolute/path/to/pm-toolkit/mcps/servers/github-pm-tools/dist/index.js"],
      "env": {
        "GITHUB_TOKEN": "your-github-token",
        "GITHUB_OWNER": "your-org-or-username"
      }
    }
  }
}
```

2. Restart Cursor

3. Verify: Open Cursor Settings → Features → MCP Servers to see your servers

### Claude Desktop Configuration

1. Find your config file:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add MCP configuration:

```json
{
  "mcpServers": {
    "jira-pm-assistant": {
      "command": "node",
      "args": ["/absolute/path/to/pm-toolkit/mcps/servers/jira-pm-assistant/dist/index.js"],
      "env": {
        "JIRA_HOST": "yourcompany.atlassian.net",
        "JIRA_EMAIL": "your-email@company.com",
        "JIRA_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

3. Restart Claude Desktop

---

## Troubleshooting

### Server Not Appearing

1. **Check paths**: Ensure the path to `dist/index.js` is absolute and correct
2. **Check build**: Make sure you ran `npm run build` successfully
3. **Check logs**: 
   - Cursor: View → Toggle Developer Tools → Console
   - Claude: Check application logs

### Authentication Errors

1. **Verify credentials**: Test your API token with curl:
   ```bash
   # Test Jira
   curl -u "email@company.com:API_TOKEN" \
        "https://yourcompany.atlassian.net/rest/api/3/myself"
   ```

2. **Check permissions**: Ensure your API token has necessary scopes

### Server Crashes

1. **Check Node version**: Must be 18+
2. **Check dependencies**: Run `npm install` again
3. **Check for errors**: Run server manually to see error output

---

## Security Best Practices

### Do ✅
- Store credentials in environment variables
- Use `.env` files locally (added to `.gitignore`)
- Rotate API tokens periodically
- Use minimum required permissions

### Don't ❌
- Commit API tokens to git
- Share tokens via Slack/email
- Use production tokens for testing
- Give tokens more permissions than needed

### Using Environment Files

Create a `.env` file (never commit this):

```bash
# .env
JIRA_HOST=yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
```

Load in your shell:
```bash
source .env
```

Or use a tool like `direnv` for automatic loading.

---

## Next Steps

- Read [MCP Use Cases for PMs](./mcp-use-cases-for-pms.md) for ideas
- Explore individual server READMEs for detailed capabilities
- Consider building custom MCP servers for your specific tools


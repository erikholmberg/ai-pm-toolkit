# MCP Servers for Product Managers

Model Context Protocol (MCP) servers that extend AI assistants with PM-specific capabilities.

## What is MCP?

MCP (Model Context Protocol) allows AI assistants like Claude to interact with external tools and data sources. These servers give your AI assistant the ability to:

- 📋 Manage Jira tickets and sprints
- 📝 Search and create Confluence documentation
- 🔧 Interact with GitHub issues and pull requests

## Available Servers

| Server | Description | Status |
|--------|-------------|--------|
| [jira-pm-assistant](./servers/jira-pm-assistant/) | Create tickets, query sprints, generate release notes | Ready |
| [confluence-docs](./servers/confluence-docs/) | Search docs, publish PRDs, create meeting notes | Ready |
| [github-pm-tools](./servers/github-pm-tools/) | Track issues, generate release notes from PRs | Ready |

## Prerequisites

- Node.js 18+ 
- npm or yarn
- API tokens for the services you want to use

## Quick Start

### 1. Install a Server

```bash
cd servers/jira-pm-assistant
npm install
npm run build
```

### 2. Configure Credentials

Each server requires API credentials. Create a `.env` file in the server directory:

```bash
# Example for Jira
JIRA_HOST=your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
```

### 3. Add to Your AI Tool

#### For Cursor

Add to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "jira-pm-assistant": {
      "command": "node",
      "args": ["/path/to/pm-toolkit/mcps/servers/jira-pm-assistant/dist/index.js"],
      "env": {
        "JIRA_HOST": "your-company.atlassian.net",
        "JIRA_EMAIL": "your-email@company.com",
        "JIRA_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

#### For Claude Desktop

Add to your Claude config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "jira-pm-assistant": {
      "command": "node",
      "args": ["/path/to/pm-toolkit/mcps/servers/jira-pm-assistant/dist/index.js"],
      "env": {
        "JIRA_HOST": "your-company.atlassian.net",
        "JIRA_EMAIL": "your-email@company.com",
        "JIRA_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

## Security Notes

- ⚠️ Never commit API tokens to git
- ⚠️ Use environment variables or secure credential storage
- ⚠️ Review permissions requested by each server
- ⚠️ These servers can modify data—use with appropriate caution

## Guides

- [MCP Setup Guide](./guides/mcp-setup-guide.md) - Detailed setup instructions
- [MCP Use Cases for PMs](./guides/mcp-use-cases-for-pms.md) - Ideas for what you can do

## Building Your Own MCP Server

MCP servers are relatively simple to build. See the [MCP documentation](https://modelcontextprotocol.io/) for details.

Basic structure:

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";

const server = new Server({
  name: "my-server",
  version: "1.0.0",
}, {
  capabilities: {
    tools: {},
  },
});

// Define your tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "my_tool",
      description: "What this tool does",
      inputSchema: {
        type: "object",
        properties: {
          param: { type: "string", description: "Parameter description" }
        },
        required: ["param"]
      }
    }
  ]
}));

// Implement tool logic
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  // Handle tool calls
});
```

## Contributing

Have an MCP server that helps with PM work? Contributions welcome!


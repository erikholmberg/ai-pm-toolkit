# MCP Servers for Product Managers

Model Context Protocol (MCP) servers that extend AI assistants with PM-specific capabilities.

## What is MCP?

MCP (Model Context Protocol) allows AI assistants like Claude to interact with external tools and data sources. These servers give your AI assistant the ability to:

- 📋 Manage Jira tickets and sprints
- 📝 Search and create Confluence documentation
- 🔧 Interact with GitHub issues and pull requests
- 💬 Search Slack messages, extract action items, get channel summaries
- 🧪 Query Braintrust experiments and eval results
- 📊 Analyze LangSmith runs, traces, and project metrics
- 📝 Search and create Notion pages, meeting notes, query databases
- 📈 Query product analytics trends, funnels, and retention
- 📅 Prep for meetings, check free/busy, and create calendar events

## Available Servers

| Server | Description | Status |
|--------|-------------|--------|
| [jira-pm-assistant](./servers/jira-pm-assistant/) | Create tickets, query sprints, generate release notes | Ready |
| [confluence-docs](./servers/confluence-docs/) | Search docs, publish PRDs, create meeting notes | Ready |
| [notion-pm-tools](./servers/notion-pm-tools/) | Search/create Notion pages, meeting notes, list/query databases | Ready |
| [github-pm-tools](./servers/github-pm-tools/) | Track issues, generate release notes from PRs | Ready |
| [slack-pm-assistant](./servers/slack-pm-assistant/) | Search messages, extract action items, channel summaries | Ready |
| [braintrust-pm-tools](./servers/braintrust-pm-tools/) | Query experiments, eval results, datasets, logs | Ready |
| [langsmith-pm-tools](./servers/langsmith-pm-tools/) | Analyze runs, traces, project stats, eval results | Ready |
| [product-analytics-pm-tools](./servers/product-analytics-pm-tools/) | Read-only analytics tools (event trends, funnels, cohorts, retention) | Ready |
| [calendar-meetings-pm-tools](./servers/calendar-meetings-pm-tools/) | Meeting prep, event search, free/busy, event creation, agendas | Ready |

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
- [TOOLS.md](./TOOLS.md) - Server → tool name → when to use it (quick lookup)

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

## Suggested MCPs to add

Candidates beyond the [current servers](#available-servers). See [docs/suggested-tools.md](../docs/suggested-tools.md) for rationale. Tool lookup: [TOOLS.md](./TOOLS.md).

| Priority | Server | Purpose |
|----------|--------|---------|
| **High** | **Linear** | Issues, projects, cycles, roadmap. Same PM workflows as Jira for teams that use Linear. |
| — | **Notion** | ✅ [notion-pm-tools](./servers/notion-pm-tools/) |
| — | **Product analytics (sample)** | ✅ [product-analytics-pm-tools](./servers/product-analytics-pm-tools/) — read-only demo over bundled data; replace backend for Amplitude/Mixpanel/Pendo-style workflows. |
| — | **Calendar** | ✅ [calendar-meetings-pm-tools](./servers/calendar-meetings-pm-tools/) |
| **Medium** | **Customer support** | Read-only: Intercom, Zendesk, or Help Scout — tickets, themes, volume. Feedback synthesis and prioritization. |
| **Lower** | **Figma (read-only)** | List files, frame/screen names and links. Link specs to design; PRDs and eng handoff. |

**Quick wins:** Linear (if your users are on it). Notion, Calendar, and sample product analytics are already in-repo.

## Contributing

Have an MCP server that helps with PM work? Contributions welcome!


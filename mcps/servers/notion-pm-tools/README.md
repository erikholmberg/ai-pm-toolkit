# Notion PM Tools MCP Server

MCP server for Notion: search pages, create pages and meeting notes, list databases, query databases.

## Prerequisites

- A [Notion integration](https://www.notion.so/my-integrations). Create one at Notion → Settings → Connections → Develop or manage integrations.
- Share the pages or databases you want to access with that integration (click ••• on a page → Add connections → select your integration).

## Setup

### 1. Install & build

```bash
npm install
npm run build
```

### 2. Configure

Use your integration’s **Internal Integration Token** (from the integration’s Capabilities tab):

```bash
export NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Add to MCP config

**Cursor** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "notion-pm-tools": {
      "command": "node",
      "args": ["/path/to/ai-pm-toolkit/mcps/servers/notion-pm-tools/dist/index.js"],
      "env": {
        "NOTION_API_KEY": "secret_your_integration_token"
      }
    }
  }
}
```

**Claude Desktop** (e.g. `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS): same structure under `mcpServers`.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTION_API_KEY` | Yes | Notion integration token (starts with `secret_`) |

## Tools

| Tool | Description |
|------|-------------|
| `notion_search_pages` | Search pages by title (among pages shared with the integration). |
| `notion_list_databases` | List databases shared with the integration. |
| `notion_get_page` | Get a page’s title, URL, and content blocks. |
| `notion_create_page` | Create a new page under a parent page (title + optional markdown content). |
| `notion_create_page_in_database` | Create a new row in a database (title property + optional body). |
| `notion_create_meeting_notes` | Create a meeting notes page (title, date, attendees, agenda). |
| `notion_query_database` | Query a database (returns page IDs and titles). |

## Example prompts

- “Search Notion for the Q1 roadmap page.”
- “Create a meeting notes page under [parent page id] for the Sprint Review on 2025-03-20 with agenda: demo, feedback, next sprint.”
- “List my Notion databases.”
- “Get the content of this Notion page: [page id].”

## Security

- Do not commit `NOTION_API_KEY` or put it in version control.
- The integration only sees pages and databases you explicitly share with it.

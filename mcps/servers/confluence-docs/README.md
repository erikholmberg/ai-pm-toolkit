# Confluence Docs MCP Server

An MCP server for Confluence documentation workflows.

## Features

- 🔍 **Search Pages**: Search across your Confluence spaces
- 📄 **View Pages**: Get page content
- ✏️ **Create Pages**: Publish new documentation
- 📝 **Meeting Notes**: Create structured meeting notes from templates

## Setup

### 1. Install & Build

```bash
npm install
npm run build
```

### 2. Configure

```bash
export CONFLUENCE_HOST=yourcompany.atlassian.net
export CONFLUENCE_EMAIL=your-email@company.com
export CONFLUENCE_API_TOKEN=your-api-token
```

### 3. Add to MCP Config

```json
{
  "mcpServers": {
    "confluence-docs": {
      "command": "node",
      "args": ["/path/to/confluence-docs/dist/index.js"],
      "env": {
        "CONFLUENCE_HOST": "yourcompany.atlassian.net",
        "CONFLUENCE_EMAIL": "your-email@company.com",
        "CONFLUENCE_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

## Available Tools

### search_pages
Search for pages by content.

### get_page
Get the content of a specific page.

### create_page
Create a new Confluence page.

### list_spaces
List available spaces.

### create_meeting_notes
Create formatted meeting notes from a template.

## Example Usage

```
"Search Confluence for documentation about our authentication API"

"Create a meeting notes page for the Sprint Retrospective on 2024-12-15"

"Publish this PRD to the Platform team space in Confluence"
```


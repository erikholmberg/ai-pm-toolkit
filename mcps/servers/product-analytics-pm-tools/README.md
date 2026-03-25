# Product Analytics PM Tools MCP Server

Read-only MCP server for PM product analytics workflows. It supports core queries:

- Event trend over time
- Funnel conversion
- Retention by cohort
- Cohort comparison
- Segment comparison

## Data source

Set `ANALYTICS_DATA_PATH` to a local JSON file with this structure:

```json
{
  "events": [
    {
      "eventName": "signup_completed",
      "timestamp": "2026-03-01T12:00:00Z",
      "userId": "u1",
      "segment": "self-serve",
      "properties": { "country": "SE" }
    }
  ]
}
```

## Setup

```bash
npm install
npm run build
```

## Environment variables

- `ANALYTICS_DATA_PATH` (required): absolute path to analytics JSON export.

## Example MCP config

```json
{
  "mcpServers": {
    "product-analytics-pm-tools": {
      "command": "node",
      "args": ["/path/to/mcps/servers/product-analytics-pm-tools/dist/index.js"],
      "env": {
        "ANALYTICS_DATA_PATH": "/absolute/path/to/analytics-export.json"
      }
    }
  }
}
```

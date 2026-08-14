# Calendar Meetings PM Tools MCP Server

MCP server for Google Calendar meeting workflows: list upcoming meetings, search events, check free/busy, create meeting invites, and draft PM-style agendas.

## Features

- **Upcoming meetings**: Read meetings in a time window for standup prep or daily planning.
- **Event search**: Find roadmap reviews, customer calls, planning sessions, or follow-ups by keyword.
- **Event details**: Inspect attendees, links, agenda-style description lines, and organizer metadata.
- **Free/busy**: Check one or more calendars before scheduling.
- **Create events**: Create calendar invites, add attendees, and optionally generate a Google Meet link.
- **Agenda drafting**: Generate a structured agenda and calendar description from goals and topics.

## Prerequisites

- Node.js 18+
- A Google Cloud OAuth client with the Google Calendar API enabled
- A Google OAuth refresh token for the Google account whose calendar should be accessed

Recommended OAuth scope:

```text
https://www.googleapis.com/auth/calendar
```

For read-only usage, you can use:

```text
https://www.googleapis.com/auth/calendar.readonly
```

Read-only tokens cannot create events or check some free/busy scenarios depending on calendar sharing permissions.

## Setup

### 1. Install & build

```bash
npm install
npm run build
```

### 2. Configure

```bash
export GOOGLE_CLIENT_ID=your-google-oauth-client-id
export GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
export GOOGLE_REFRESH_TOKEN=your-google-refresh-token
export GOOGLE_CALENDAR_ID=primary
export CALENDAR_TIME_ZONE=America/Los_Angeles
```

`GOOGLE_CALENDAR_ID` and `CALENDAR_TIME_ZONE` are optional. The server defaults to `primary` and `UTC`.

### 3. Add to MCP config

**Cursor** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "calendar-meetings-pm-tools": {
      "command": "node",
      "args": ["/path/to/ai-pm-toolkit/mcps/servers/calendar-meetings-pm-tools/dist/index.js"],
      "env": {
        "GOOGLE_CLIENT_ID": "your-google-oauth-client-id",
        "GOOGLE_CLIENT_SECRET": "your-google-oauth-client-secret",
        "GOOGLE_REFRESH_TOKEN": "your-google-refresh-token",
        "GOOGLE_CALENDAR_ID": "primary",
        "CALENDAR_TIME_ZONE": "America/Los_Angeles"
      }
    }
  }
}
```

**Claude Desktop** (for example, `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS): use the same structure under `mcpServers`.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `GOOGLE_REFRESH_TOKEN` | Yes | Refresh token for the Google account |
| `GOOGLE_CALENDAR_ID` | No | Calendar ID to use by default; defaults to `primary` |
| `CALENDAR_TIME_ZONE` | No | IANA time zone for created events/free-busy; defaults to `UTC` |

## Tools

| Tool | Description |
|------|-------------|
| `calendar_list_events` | List upcoming events in a time window. |
| `calendar_search_events` | Search events by keyword across a past/future window. |
| `calendar_get_event` | Read details for one event. |
| `calendar_find_free_busy` | Check busy blocks for one or more calendars. |
| `calendar_create_event` | Create an event or meeting invite, optionally with Google Meet. |
| `calendar_prepare_meeting_brief` | Build a PM prep brief from upcoming meetings. |
| `calendar_draft_agenda` | Draft a structured agenda and reusable calendar description. |

## Example prompts

- "What meetings do I have in the next 24 hours?"
- "Find roadmap review meetings from the last 30 days."
- "Check free/busy for primary and product-lead@example.com tomorrow from 9 to 5."
- "Create a 30 minute customer escalation sync tomorrow at 10am with a Google Meet link."
- "Draft an agenda for a launch readiness review with goals: confirm blockers, assign owners, decide go/no-go."

## Security

- Do not commit Google OAuth client secrets, refresh tokens, `.env` files, or downloaded credential JSON.
- Prefer the narrowest Calendar API scope that supports your workflow.
- Review who can access created events and Google Meet links before sending invites.

# Jira PM Assistant MCP Server

An MCP server that provides Jira integration for Product Managers.

## Features

- 🔍 **Search Issues**: Query Jira using JQL
- 📋 **View Issues**: Get detailed issue information
- ✏️ **Create Issues**: Create new tickets from PRDs or user stories
- 🏃 **Sprint Status**: View current sprint information
- 📝 **Release Notes**: Generate release notes from completed issues

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Build

```bash
npm run build
```

### 3. Configure Environment

Set these environment variables:

```bash
export JIRA_HOST=yourcompany.atlassian.net
export JIRA_EMAIL=your-email@company.com
export JIRA_API_TOKEN=your-api-token
```

### 4. Add to MCP Config

Add to your Cursor or Claude Desktop config:

```json
{
  "mcpServers": {
    "jira-pm-assistant": {
      "command": "node",
      "args": ["/path/to/jira-pm-assistant/dist/index.js"],
      "env": {
        "JIRA_HOST": "yourcompany.atlassian.net",
        "JIRA_EMAIL": "your-email@company.com",
        "JIRA_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

## Available Tools

### search_issues
Search Jira using JQL.

```
"Search for all bugs in the Platform project that are in progress"
```

### get_issue
Get details of a specific issue.

```
"Show me the details of PLATFORM-123"
```

### create_issue
Create a new Jira issue.

```
"Create a Story in the Platform project for implementing SSO login"
```

### get_sprint
Get current sprint information.

```
"What's the status of the current sprint for board 42?"
```

### generate_release_notes
Generate release notes from completed issues.

```
"Generate release notes for all issues completed in Sprint 45"
```

## Example Usage

### Creating Issues from User Stories

```
"Create Jira tickets for these user stories in the AUTH project:
1. As a user, I want to log in with Google SSO
2. As a user, I want to reset my password via email
3. As an admin, I want to require 2FA for all users"
```

### Getting Sprint Status

```
"Show me all issues in the current sprint, grouped by status"
```

### Generating Release Notes

```
"Generate release notes for Sprint 45, categorizing by issue type"
```

## Troubleshooting

### Authentication Errors

Test your credentials:

```bash
curl -u "email@company.com:API_TOKEN" \
     "https://yourcompany.atlassian.net/rest/api/3/myself"
```

### Permission Errors

Ensure your API token has access to:
- Browse projects
- Create issues (if using create_issue)
- View sprints (if using sprint features)

## Security

- Never commit API tokens to git
- Use environment variables or secure credential storage
- Rotate tokens periodically


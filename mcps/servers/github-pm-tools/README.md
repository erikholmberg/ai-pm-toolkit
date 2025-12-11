# GitHub PM Tools MCP Server

An MCP server for GitHub workflows relevant to Product Managers.

## Features

- 📋 **List Issues**: Query and filter issues
- 🔍 **View Issues**: Get detailed issue information
- ✏️ **Create Issues**: Create new issues
- 🔀 **Pull Requests**: Track PRs and their status
- 📝 **Release Notes**: Generate release notes from merged PRs
- 📊 **Repo Stats**: Get repository health metrics

## Setup

### 1. Install & Build

```bash
npm install
npm run build
```

### 2. Configure

```bash
export GITHUB_TOKEN=your-github-token
export GITHUB_OWNER=your-org-or-username
```

### 3. Add to MCP Config

```json
{
  "mcpServers": {
    "github-pm-tools": {
      "command": "node",
      "args": ["/path/to/github-pm-tools/dist/index.js"],
      "env": {
        "GITHUB_TOKEN": "your-github-token",
        "GITHUB_OWNER": "your-org"
      }
    }
  }
}
```

## Available Tools

### list_issues
List and filter issues in a repository.

### get_issue
Get details of a specific issue.

### create_issue
Create a new issue.

### list_pull_requests
List PRs with filtering.

### generate_release_notes
Generate release notes from merged PRs.

### get_repo_stats
Get repository statistics.

## Example Usage

```
"Show me all open bugs in the platform-core repo"

"Generate release notes for v2.5.0 based on PRs merged since v2.4.0"

"Create an issue for implementing the new search feature in platform-core"
```


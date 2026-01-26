# LangSmith PM Tools MCP Server

An MCP server for LangSmith AI evaluation workflows relevant to Product Managers.

## Features

- 📊 **List Projects**: Browse your LangSmith projects
- 🔍 **Query Runs**: List and filter runs/traces
- 📈 **Project Stats**: Get statistics (error rates, latency, success rates)
- 🔬 **Traces**: Get detailed trace information with child runs
- 📚 **Datasets**: Manage and query test datasets
- ✅ **Eval Results**: Get evaluation results for projects

## Setup

### 1. Install & Build

```bash
npm install
npm run build
```

### 2. Configure

Get your API key from LangSmith: **Settings** > **API Keys**

```bash
export LANGSMITH_API_KEY=your-api-key
export LANGSMITH_ENDPOINT=https://api.smith.langchain.com  # Optional, for self-hosted
```

### 3. Add to MCP Config

```json
{
  "mcpServers": {
    "langsmith-pm-tools": {
      "command": "node",
      "args": ["/path/to/langsmith-pm-tools/dist/index.js"],
      "env": {
        "LANGSMITH_API_KEY": "your-api-key",
        "LANGSMITH_ENDPOINT": "https://api.smith.langchain.com"
      }
    }
  }
}
```

## Available Tools

### list_projects
List all LangSmith projects.

### get_project
Get detailed information about a specific project.

### list_runs
List runs/traces in a project with filtering options.

### get_run
Get detailed information about a specific run.

### get_trace
Get a trace with all child runs.

### get_project_stats
Get statistics for a project (run counts, error rates, average latency).

### list_datasets
List datasets in a project or all datasets.

### get_dataset
Get details of a specific dataset.

### query_traces
Query traces with advanced filtering.

### get_eval_results
Get evaluation results for a project or dataset.

## Example Usage

```
"Show me all runs in the chat-assistant project from the last 24 hours"

"Get statistics for the search-feature project. What's the error rate?"

"List all traces that had errors in the last week"

"Show me evaluation results for the latest dataset"

"What's the average latency for runs in the production project?"
```

## Use Cases for PMs

### Daily Health Checks
```
"Get statistics for the production project. Show me error rates 
and average latency from the last 24 hours."
```

### Debugging Issues
```
"Find all runs with errors in the chat-assistant project from 
the last hour. Show me the error messages."
```

### Performance Monitoring
```
"What's the average latency trend for the search project? 
Are there any performance regressions?"
```

### Evaluation Analysis
```
"Get evaluation results for the latest model. What's the 
accuracy and what are the failure cases?"
```

## API Reference

The server uses the LangSmith REST API. See [LangSmith Documentation](https://docs.smith.langchain.com/) for details.

For self-hosted LangSmith deployments, set `LANGSMITH_ENDPOINT` to your deployment URL.

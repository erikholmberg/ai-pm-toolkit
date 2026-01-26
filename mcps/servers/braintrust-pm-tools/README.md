# Braintrust PM Tools MCP Server

An MCP server for Braintrust AI evaluation workflows relevant to Product Managers.

## Features

- 📊 **List Projects**: Browse your Braintrust projects
- 🔬 **Experiments**: View experiments and their results
- 📈 **Eval Summaries**: Get summary statistics for experiments
- 📚 **Datasets**: Manage and query test datasets
- 📝 **Logs & Traces**: Query production logs and traces
- 🔄 **Compare Experiments**: Compare metrics across experiments

## Setup

### 1. Install & Build

```bash
npm install
npm run build
```

### 2. Configure

Get your API key from Braintrust: **Settings** > **Organization** > **API keys**

```bash
export BRAINTRUST_API_KEY=your-api-key
export BRAINTRUST_ORG_ID=your-org-id  # Optional
```

### 3. Add to MCP Config

```json
{
  "mcpServers": {
    "braintrust-pm-tools": {
      "command": "node",
      "args": ["/path/to/braintrust-pm-tools/dist/index.js"],
      "env": {
        "BRAINTRUST_API_KEY": "your-api-key",
        "BRAINTRUST_ORG_ID": "your-org-id"
      }
    }
  }
}
```

## Available Tools

### list_projects
List all Braintrust projects in your organization.

### get_project
Get detailed information about a specific project.

### list_experiments
List experiments in a project.

### get_experiment
Get detailed experiment information including results.

### get_experiment_summary
Get summary statistics for an experiment (run counts, average scores, etc.).

### list_datasets
List datasets in a project or organization.

### get_dataset
Get details of a specific dataset.

### query_logs
Query production logs and traces with time filters.

### compare_experiments
Compare metrics across multiple experiments.

## Example Usage

```
"Show me all experiments in the search-feature project"

"Get a summary of the latest experiment results"

"Compare the accuracy scores across these three experiments: exp-1, exp-2, exp-3"

"What are the production logs for the last 24 hours in the chat-assistant project?"

"List all datasets in my organization"
```

## Use Cases for PMs

### Daily Health Checks
```
"Get a summary of the latest experiment for our AI feature. 
Show me the average scores and any regressions."
```

### Release Decisions
```
"Compare these three model versions. Which has the best 
accuracy and lowest error rate?"
```

### Production Monitoring
```
"Query logs from the last hour. Are there any errors or 
quality issues I should know about?"
```

### Dataset Management
```
"List all datasets for the search project. How many test 
cases does each have?"
```

## API Reference

The server uses the Braintrust REST API. See [Braintrust API Documentation](https://braintrust.dev/docs/api-reference/introduction) for details.

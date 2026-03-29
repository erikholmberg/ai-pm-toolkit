#!/usr/bin/env node
/**
 * Jira PM Assistant MCP Server
 * 
 * An MCP server that provides Jira integration for Product Managers.
 * 
 * Capabilities:
 * - Search and query issues
 * - Create issues from PRDs/user stories
 * - Get sprint status
 * - Generate release notes
 * 
 * Environment Variables:
 * - JIRA_HOST: Your Jira host (e.g., yourcompany.atlassian.net)
 * - JIRA_EMAIL: Your Atlassian account email
 * - JIRA_API_TOKEN: Your Atlassian API token
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Configuration from environment
const JIRA_HOST = process.env.JIRA_HOST;
const JIRA_EMAIL = process.env.JIRA_EMAIL;
const JIRA_API_TOKEN = process.env.JIRA_API_TOKEN;

if (!JIRA_HOST || !JIRA_EMAIL || !JIRA_API_TOKEN) {
  console.error("Missing required environment variables: JIRA_HOST, JIRA_EMAIL, JIRA_API_TOKEN");
  process.exit(1);
}

const BASE_URL = `https://${JIRA_HOST}/rest/api/3`;
const AUTH_HEADER = `Basic ${Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString("base64")}`;

// Jira API helper
async function jiraRequest(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Authorization": AUTH_HEADER,
      "Content-Type": "application/json",
      "Accept": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Jira API error: ${response.status} - ${error}`);
  }

  return response.json();
}

// Create MCP server
const server = new Server(
  {
    name: "jira-pm-assistant",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "search_issues",
      description: "Use when: searching or reporting on Jira work with JQL (Jira Query Language).",
      inputSchema: {
        type: "object",
        properties: {
          jql: {
            type: "string",
            description: "JQL query string (e.g., 'project = PLATFORM AND status = \"In Progress\"')",
          },
          maxResults: {
            type: "number",
            description: "Maximum number of results (default 20)",
          },
        },
        required: ["jql"],
      },
    },
    {
      name: "get_issue",
      description: "Use when: you need full details for a specific Jira issue.",
      inputSchema: {
        type: "object",
        properties: {
          issueKey: {
            type: "string",
            description: "The issue key (e.g., PLATFORM-123)",
          },
        },
        required: ["issueKey"],
      },
    },
    {
      name: "create_issue",
      description: "Use when: creating a new Jira issue.",
      inputSchema: {
        type: "object",
        properties: {
          project: {
            type: "string",
            description: "Project key (e.g., PLATFORM)",
          },
          summary: {
            type: "string",
            description: "Issue title/summary",
          },
          description: {
            type: "string",
            description: "Issue description (supports markdown)",
          },
          issueType: {
            type: "string",
            description: "Issue type (e.g., Story, Bug, Task, Epic)",
          },
          priority: {
            type: "string",
            description: "Priority (e.g., Highest, High, Medium, Low, Lowest)",
          },
          labels: {
            type: "array",
            items: { type: "string" },
            description: "Labels to add to the issue",
          },
        },
        required: ["project", "summary", "issueType"],
      },
    },
    {
      name: "get_sprint",
      description: "Use when: you need current sprint information for a board.",
      inputSchema: {
        type: "object",
        properties: {
          boardId: {
            type: "number",
            description: "The board ID",
          },
        },
        required: ["boardId"],
      },
    },
    {
      name: "get_sprint_issues",
      description: "Use when: listing all issues in a sprint.",
      inputSchema: {
        type: "object",
        properties: {
          sprintId: {
            type: "number",
            description: "The sprint ID",
          },
        },
        required: ["sprintId"],
      },
    },
    {
      name: "generate_release_notes",
      description: "Use when: drafting release notes from completed Jira issues (sprint or version).",
      inputSchema: {
        type: "object",
        properties: {
          jql: {
            type: "string",
            description: "JQL query to find issues for release notes (e.g., 'project = PLATFORM AND status = Done AND sprint = 45')",
          },
        },
        required: ["jql"],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "search_issues": {
        const jql = args?.jql as string;
        const maxResults = (args?.maxResults as number) || 20;
        
        const result = await jiraRequest(
          `/search?jql=${encodeURIComponent(jql)}&maxResults=${maxResults}`
        );
        
        const issues = result.issues.map((issue: any) => ({
          key: issue.key,
          summary: issue.fields.summary,
          status: issue.fields.status?.name,
          priority: issue.fields.priority?.name,
          assignee: issue.fields.assignee?.displayName,
          issueType: issue.fields.issuetype?.name,
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ total: result.total, issues }, null, 2),
            },
          ],
        };
      }

      case "get_issue": {
        const issueKey = args?.issueKey as string;
        const issue = await jiraRequest(`/issue/${issueKey}`);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                key: issue.key,
                summary: issue.fields.summary,
                description: issue.fields.description,
                status: issue.fields.status?.name,
                priority: issue.fields.priority?.name,
                assignee: issue.fields.assignee?.displayName,
                reporter: issue.fields.reporter?.displayName,
                issueType: issue.fields.issuetype?.name,
                created: issue.fields.created,
                updated: issue.fields.updated,
                labels: issue.fields.labels,
              }, null, 2),
            },
          ],
        };
      }

      case "create_issue": {
        const issueData = {
          fields: {
            project: { key: args?.project as string },
            summary: args?.summary as string,
            description: args?.description ? {
              type: "doc",
              version: 1,
              content: [
                {
                  type: "paragraph",
                  content: [{ type: "text", text: args.description as string }],
                },
              ],
            } : undefined,
            issuetype: { name: args?.issueType as string },
            priority: args?.priority ? { name: args.priority as string } : undefined,
            labels: args?.labels as string[] || [],
          },
        };
        
        const result = await jiraRequest("/issue", {
          method: "POST",
          body: JSON.stringify(issueData),
        });
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                key: result.key,
                url: `https://${JIRA_HOST}/browse/${result.key}`,
              }, null, 2),
            },
          ],
        };
      }

      case "get_sprint": {
        const boardId = args?.boardId as number;
        const result = await jiraRequest(
          `/board/${boardId}/sprint?state=active`,
          // Note: This uses the Agile API, adjust BASE_URL if needed
        );
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "generate_release_notes": {
        const jql = args?.jql as string;
        const result = await jiraRequest(
          `/search?jql=${encodeURIComponent(jql)}&maxResults=100`
        );
        
        // Group issues by type
        const grouped: Record<string, any[]> = {};
        for (const issue of result.issues) {
          const type = issue.fields.issuetype?.name || "Other";
          if (!grouped[type]) grouped[type] = [];
          grouped[type].push({
            key: issue.key,
            summary: issue.fields.summary,
          });
        }
        
        // Format as release notes
        let releaseNotes = "# Release Notes\n\n";
        for (const [type, issues] of Object.entries(grouped)) {
          releaseNotes += `## ${type}s\n\n`;
          for (const issue of issues) {
            releaseNotes += `- **${issue.key}**: ${issue.summary}\n`;
          }
          releaseNotes += "\n";
        }
        
        return {
          content: [
            {
              type: "text",
              text: releaseNotes,
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Jira PM Assistant MCP server running");
}

main().catch(console.error);


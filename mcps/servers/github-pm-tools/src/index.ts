#!/usr/bin/env node
/**
 * GitHub PM Tools MCP Server
 * 
 * An MCP server that provides GitHub integration for Product Managers.
 * 
 * Capabilities:
 * - Query issues and PRs
 * - Generate release notes
 * - Track project status
 * 
 * Environment Variables:
 * - GITHUB_TOKEN: Your GitHub personal access token
 * - GITHUB_OWNER: Default org/user for repositories
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_OWNER = process.env.GITHUB_OWNER;

if (!GITHUB_TOKEN) {
  console.error("Missing required environment variable: GITHUB_TOKEN");
  process.exit(1);
}

const BASE_URL = "https://api.github.com";

async function githubRequest(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Authorization": `Bearer ${GITHUB_TOKEN}`,
      "Accept": "application/vnd.github.v3+json",
      "X-GitHub-Api-Version": "2022-11-28",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`GitHub API error: ${response.status} - ${error}`);
  }

  return response.json();
}

const server = new Server(
  {
    name: "github-pm-tools",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "list_issues",
      description: "Use when: browsing or filtering GitHub issues in a repository.",
      inputSchema: {
        type: "object",
        properties: {
          repo: {
            type: "string",
            description: "Repository name (uses GITHUB_OWNER as org)",
          },
          owner: {
            type: "string",
            description: "Repository owner (optional, defaults to GITHUB_OWNER)",
          },
          state: {
            type: "string",
            enum: ["open", "closed", "all"],
            description: "Issue state filter",
          },
          labels: {
            type: "string",
            description: "Comma-separated list of labels",
          },
          assignee: {
            type: "string",
            description: "Filter by assignee username",
          },
        },
        required: ["repo"],
      },
    },
    {
      name: "get_issue",
      description: "Use when: reading one GitHub issue in full.",
      inputSchema: {
        type: "object",
        properties: {
          repo: {
            type: "string",
            description: "Repository name",
          },
          owner: {
            type: "string",
            description: "Repository owner (optional)",
          },
          issueNumber: {
            type: "number",
            description: "Issue number",
          },
        },
        required: ["repo", "issueNumber"],
      },
    },
    {
      name: "create_issue",
      description: "Use when: filing a new GitHub issue.",
      inputSchema: {
        type: "object",
        properties: {
          repo: {
            type: "string",
            description: "Repository name",
          },
          owner: {
            type: "string",
            description: "Repository owner (optional)",
          },
          title: {
            type: "string",
            description: "Issue title",
          },
          body: {
            type: "string",
            description: "Issue body (markdown)",
          },
          labels: {
            type: "array",
            items: { type: "string" },
            description: "Labels to apply",
          },
          assignees: {
            type: "array",
            items: { type: "string" },
            description: "Usernames to assign",
          },
        },
        required: ["repo", "title"],
      },
    },
    {
      name: "list_pull_requests",
      description: "Use when: listing pull requests in a repository.",
      inputSchema: {
        type: "object",
        properties: {
          repo: {
            type: "string",
            description: "Repository name",
          },
          owner: {
            type: "string",
            description: "Repository owner (optional)",
          },
          state: {
            type: "string",
            enum: ["open", "closed", "all"],
            description: "PR state filter",
          },
          base: {
            type: "string",
            description: "Filter by base branch",
          },
        },
        required: ["repo"],
      },
    },
    {
      name: "generate_release_notes",
      description: "Use when: generating release notes from merged PRs between refs/tags.",
      inputSchema: {
        type: "object",
        properties: {
          repo: {
            type: "string",
            description: "Repository name",
          },
          owner: {
            type: "string",
            description: "Repository owner (optional)",
          },
          tagName: {
            type: "string",
            description: "New tag/version name",
          },
          previousTag: {
            type: "string",
            description: "Previous tag to compare from",
          },
          targetBranch: {
            type: "string",
            description: "Target branch (default: main)",
          },
        },
        required: ["repo", "tagName"],
      },
    },
    {
      name: "get_repo_stats",
      description: "Use when: summarizing repository activity and health metrics.",
      inputSchema: {
        type: "object",
        properties: {
          repo: {
            type: "string",
            description: "Repository name",
          },
          owner: {
            type: "string",
            description: "Repository owner (optional)",
          },
        },
        required: ["repo"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const owner = (args?.owner as string) || GITHUB_OWNER;
    const repo = args?.repo as string;

    switch (name) {
      case "list_issues": {
        const state = (args?.state as string) || "open";
        const labels = args?.labels as string;
        const assignee = args?.assignee as string;
        
        let endpoint = `/repos/${owner}/${repo}/issues?state=${state}&per_page=30`;
        if (labels) endpoint += `&labels=${labels}`;
        if (assignee) endpoint += `&assignee=${assignee}`;
        
        const issues = await githubRequest(endpoint);
        
        // Filter out PRs (they appear in issues endpoint)
        const issuesOnly = issues.filter((i: any) => !i.pull_request);
        
        const formatted = issuesOnly.map((issue: any) => ({
          number: issue.number,
          title: issue.title,
          state: issue.state,
          labels: issue.labels.map((l: any) => l.name),
          assignees: issue.assignees.map((a: any) => a.login),
          createdAt: issue.created_at,
          updatedAt: issue.updated_at,
          url: issue.html_url,
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ count: formatted.length, issues: formatted }, null, 2),
            },
          ],
        };
      }

      case "get_issue": {
        const issueNumber = args?.issueNumber as number;
        const issue = await githubRequest(`/repos/${owner}/${repo}/issues/${issueNumber}`);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                number: issue.number,
                title: issue.title,
                body: issue.body,
                state: issue.state,
                labels: issue.labels.map((l: any) => l.name),
                assignees: issue.assignees.map((a: any) => a.login),
                author: issue.user.login,
                createdAt: issue.created_at,
                updatedAt: issue.updated_at,
                closedAt: issue.closed_at,
                comments: issue.comments,
                url: issue.html_url,
              }, null, 2),
            },
          ],
        };
      }

      case "create_issue": {
        const issueData = {
          title: args?.title as string,
          body: args?.body as string,
          labels: args?.labels as string[],
          assignees: args?.assignees as string[],
        };
        
        const result = await githubRequest(`/repos/${owner}/${repo}/issues`, {
          method: "POST",
          body: JSON.stringify(issueData),
        });
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                number: result.number,
                url: result.html_url,
              }, null, 2),
            },
          ],
        };
      }

      case "list_pull_requests": {
        const state = (args?.state as string) || "open";
        const base = args?.base as string;
        
        let endpoint = `/repos/${owner}/${repo}/pulls?state=${state}&per_page=30`;
        if (base) endpoint += `&base=${base}`;
        
        const prs = await githubRequest(endpoint);
        
        const formatted = prs.map((pr: any) => ({
          number: pr.number,
          title: pr.title,
          state: pr.state,
          author: pr.user.login,
          labels: pr.labels.map((l: any) => l.name),
          draft: pr.draft,
          createdAt: pr.created_at,
          mergedAt: pr.merged_at,
          url: pr.html_url,
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ count: formatted.length, pullRequests: formatted }, null, 2),
            },
          ],
        };
      }

      case "generate_release_notes": {
        const tagName = args?.tagName as string;
        const previousTag = args?.previousTag as string;
        const targetBranch = (args?.targetBranch as string) || "main";
        
        const result = await githubRequest(`/repos/${owner}/${repo}/releases/generate-notes`, {
          method: "POST",
          body: JSON.stringify({
            tag_name: tagName,
            previous_tag_name: previousTag,
            target_commitish: targetBranch,
          }),
        });
        
        return {
          content: [
            {
              type: "text",
              text: result.body,
            },
          ],
        };
      }

      case "get_repo_stats": {
        const [repo_info, open_issues, open_prs] = await Promise.all([
          githubRequest(`/repos/${owner}/${repo}`),
          githubRequest(`/repos/${owner}/${repo}/issues?state=open&per_page=1`),
          githubRequest(`/repos/${owner}/${repo}/pulls?state=open&per_page=1`),
        ]);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                name: repo_info.name,
                description: repo_info.description,
                stars: repo_info.stargazers_count,
                forks: repo_info.forks_count,
                openIssues: repo_info.open_issues_count,
                defaultBranch: repo_info.default_branch,
                language: repo_info.language,
                lastPush: repo_info.pushed_at,
                url: repo_info.html_url,
              }, null, 2),
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

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("GitHub PM Tools MCP server running");
}

main().catch(console.error);


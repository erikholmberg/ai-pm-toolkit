#!/usr/bin/env node
/**
 * Braintrust PM Tools MCP Server
 * 
 * An MCP server that provides Braintrust integration for Product Managers.
 * 
 * Capabilities:
 * - Query experiments and eval results
 * - Manage datasets
 * - View project metrics
 * - Analyze logs and traces
 * 
 * Environment Variables:
 * - BRAINTRUST_API_KEY: Your Braintrust API key
 * - BRAINTRUST_ORG_ID: (Optional) Default organization ID
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const BRAINTRUST_API_KEY = process.env.BRAINTRUST_API_KEY;
const BRAINTRUST_ORG_ID = process.env.BRAINTRUST_ORG_ID;

if (!BRAINTRUST_API_KEY) {
  console.error("Missing required environment variable: BRAINTRUST_API_KEY");
  process.exit(1);
}

const BASE_URL = "https://api.braintrust.dev";

async function braintrustRequest(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Authorization": `Bearer ${BRAINTRUST_API_KEY}`,
      "Content-Type": "application/json",
      "Accept": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Braintrust API error: ${response.status} - ${error}`);
  }

  return response.json();
}

const server = new Server(
  {
    name: "braintrust-pm-tools",
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
      name: "list_projects",
      description: "Use when: listing Braintrust projects.",
      inputSchema: {
        type: "object",
        properties: {
          orgId: {
            type: "string",
            description: "Organization ID (optional, uses BRAINTRUST_ORG_ID if not provided)",
          },
          limit: {
            type: "number",
            description: "Maximum number of results (default 50)",
          },
        },
      },
    },
    {
      name: "get_project",
      description: "Use when: reading details of one Braintrust project.",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID",
          },
        },
        required: ["projectId"],
      },
    },
    {
      name: "list_experiments",
      description: "Use when: listing experiments in a Braintrust project.",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID",
          },
          limit: {
            type: "number",
            description: "Maximum number of results (default 50)",
          },
        },
        required: ["projectId"],
      },
    },
    {
      name: "get_experiment",
      description: "Use when: loading full details and results for one experiment.",
      inputSchema: {
        type: "object",
        properties: {
          experimentId: {
            type: "string",
            description: "Experiment ID",
          },
          includeResults: {
            type: "boolean",
            description: "Include detailed results (default true)",
          },
        },
        required: ["experimentId"],
      },
    },
    {
      name: "get_experiment_summary",
      description: "Use when: you need summary statistics for an experiment.",
      inputSchema: {
        type: "object",
        properties: {
          experimentId: {
            type: "string",
            description: "Experiment ID",
          },
        },
        required: ["experimentId"],
      },
    },
    {
      name: "list_datasets",
      description: "Use when: listing Braintrust datasets.",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID (optional, lists all if not provided)",
          },
          orgId: {
            type: "string",
            description: "Organization ID (optional)",
          },
          limit: {
            type: "number",
            description: "Maximum number of results (default 50)",
          },
        },
      },
    },
    {
      name: "get_dataset",
      description: "Use when: reading one Braintrust dataset.",
      inputSchema: {
        type: "object",
        properties: {
          datasetId: {
            type: "string",
            description: "Dataset ID",
          },
        },
        required: ["datasetId"],
      },
    },
    {
      name: "query_logs",
      description: "Use when: querying Braintrust logs or traces in a time window.",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID",
          },
          startTime: {
            type: "string",
            description: "Start time (ISO 8601 format)",
          },
          endTime: {
            type: "string",
            description: "End time (ISO 8601 format)",
          },
          limit: {
            type: "number",
            description: "Maximum number of results (default 100)",
          },
        },
        required: ["projectId"],
      },
    },
    {
      name: "compare_experiments",
      description: "Use when: comparing metrics across multiple experiments.",
      inputSchema: {
        type: "object",
        properties: {
          experimentIds: {
            type: "array",
            items: { type: "string" },
            description: "List of experiment IDs to compare",
          },
        },
        required: ["experimentIds"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const orgId = (args?.orgId as string) || BRAINTRUST_ORG_ID;

    switch (name) {
      case "list_projects": {
        const limit = (args?.limit as number) || 50;
        const endpoint = orgId 
          ? `/v1/project?org_id=${orgId}&limit=${limit}`
          : `/v1/project?limit=${limit}`;
        
        const result = await braintrustRequest(endpoint);
        
        const projects = (result.projects || result || []).map((p: any) => ({
          id: p.id,
          name: p.name,
          orgId: p.org_id || p.orgId,
          createdAt: p.created_at || p.createdAt,
          description: p.description || "",
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ count: projects.length, projects }, null, 2),
            },
          ],
        };
      }

      case "get_project": {
        const projectId = args?.projectId as string;
        const project = await braintrustRequest(`/v1/project/${projectId}`);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id: project.id,
                name: project.name,
                orgId: project.org_id || project.orgId,
                description: project.description || "",
                createdAt: project.created_at || project.createdAt,
                updatedAt: project.updated_at || project.updatedAt,
              }, null, 2),
            },
          ],
        };
      }

      case "list_experiments": {
        const projectId = args?.projectId as string;
        const limit = (args?.limit as number) || 50;
        
        const result = await braintrustRequest(
          `/v1/experiment?project_id=${projectId}&limit=${limit}`
        );
        
        const experiments = (result.experiments || result || []).map((e: any) => ({
          id: e.id,
          name: e.name,
          projectId: e.project_id || e.projectId,
          createdAt: e.created_at || e.createdAt,
          status: e.status || "unknown",
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ count: experiments.length, experiments }, null, 2),
            },
          ],
        };
      }

      case "get_experiment": {
        const experimentId = args?.experimentId as string;
        const includeResults = args?.includeResults !== false;
        
        const experiment = await braintrustRequest(`/v1/experiment/${experimentId}`);
        
        let results = null;
        if (includeResults) {
          try {
            const resultsData = await braintrustRequest(
              `/v1/experiment/${experimentId}/results`
            );
            results = resultsData;
          } catch {
            // Results may not be available
          }
        }
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id: experiment.id,
                name: experiment.name,
                projectId: experiment.project_id || experiment.projectId,
                createdAt: experiment.created_at || experiment.createdAt,
                status: experiment.status || "unknown",
                results,
              }, null, 2),
            },
          ],
        };
      }

      case "get_experiment_summary": {
        const experimentId = args?.experimentId as string;
        
        const experiment = await braintrustRequest(`/v1/experiment/${experimentId}`);
        
        // Calculate summary statistics
        let summary: any = {
          experimentId: experiment.id,
          experimentName: experiment.name,
          status: experiment.status || "unknown",
        };
        
        try {
          const results = await braintrustRequest(
            `/v1/experiment/${experimentId}/results`
          );
          
          if (results && Array.isArray(results)) {
            const totalRuns = results.length;
            const scores = results
              .map((r: any) => r.scores || {})
              .filter((s: any) => Object.keys(s).length > 0);
            
            summary.totalRuns = totalRuns;
            summary.completedRuns = results.filter((r: any) => r.status === "completed").length;
            
            // Aggregate scores if available
            if (scores.length > 0) {
              const scoreKeys = Object.keys(scores[0]);
              summary.averageScores = {};
              for (const key of scoreKeys) {
                const values = scores.map((s: any) => s[key]).filter((v: any) => typeof v === "number");
                if (values.length > 0) {
                  summary.averageScores[key] = 
                    values.reduce((a: number, b: number) => a + b, 0) / values.length;
                }
              }
            }
          }
        } catch {
          // Results may not be available
        }
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(summary, null, 2),
            },
          ],
        };
      }

      case "list_datasets": {
        const projectId = args?.projectId as string;
        const limit = (args?.limit as number) || 50;
        
        let endpoint = `/v1/dataset?limit=${limit}`;
        if (projectId) {
          endpoint += `&project_id=${projectId}`;
        } else if (orgId) {
          endpoint += `&org_id=${orgId}`;
        }
        
        const result = await braintrustRequest(endpoint);
        
        const datasets = (result.datasets || result || []).map((d: any) => ({
          id: d.id,
          name: d.name,
          projectId: d.project_id || d.projectId,
          orgId: d.org_id || d.orgId,
          createdAt: d.created_at || d.createdAt,
          exampleCount: d.example_count || d.exampleCount || 0,
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ count: datasets.length, datasets }, null, 2),
            },
          ],
        };
      }

      case "get_dataset": {
        const datasetId = args?.datasetId as string;
        const dataset = await braintrustRequest(`/v1/dataset/${datasetId}`);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id: dataset.id,
                name: dataset.name,
                projectId: dataset.project_id || dataset.projectId,
                orgId: dataset.org_id || dataset.orgId,
                createdAt: dataset.created_at || dataset.createdAt,
                exampleCount: dataset.example_count || dataset.exampleCount || 0,
                description: dataset.description || "",
              }, null, 2),
            },
          ],
        };
      }

      case "query_logs": {
        const projectId = args?.projectId as string;
        const startTime = args?.startTime as string;
        const endTime = args?.endTime as string;
        const limit = (args?.limit as number) || 100;
        
        let endpoint = `/v1/log?project_id=${projectId}&limit=${limit}`;
        if (startTime) endpoint += `&start_time=${encodeURIComponent(startTime)}`;
        if (endTime) endpoint += `&end_time=${encodeURIComponent(endTime)}`;
        
        const result = await braintrustRequest(endpoint);
        
        const logs = (result.logs || result || []).map((log: any) => ({
          id: log.id,
          projectId: log.project_id || log.projectId,
          timestamp: log.timestamp || log.created_at || log.createdAt,
          input: log.input,
          output: log.output,
          scores: log.scores || {},
          metadata: log.metadata || {},
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ count: logs.length, logs }, null, 2),
            },
          ],
        };
      }

      case "compare_experiments": {
        const experimentIds = args?.experimentIds as string[];
        
        const experiments = await Promise.all(
          experimentIds.map(async (id) => {
            try {
              const exp = await braintrustRequest(`/v1/experiment/${id}`);
              const summary = await braintrustRequest(`/v1/experiment/${id}/results`).catch(() => null);
              
              return {
                id: exp.id,
                name: exp.name,
                status: exp.status || "unknown",
                runCount: Array.isArray(summary) ? summary.length : 0,
                createdAt: exp.created_at || exp.createdAt,
              };
            } catch {
              return { id, error: "Failed to fetch" };
            }
          })
        );
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ experiments }, null, 2),
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
  console.error("Braintrust PM Tools MCP server running");
}

main().catch(console.error);

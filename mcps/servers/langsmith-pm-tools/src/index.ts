#!/usr/bin/env node
/**
 * LangSmith PM Tools MCP Server
 * 
 * An MCP server that provides LangSmith integration for Product Managers.
 * 
 * Capabilities:
 * - Query runs and traces
 * - Analyze experiments
 * - Manage datasets
 * - View project metrics
 * 
 * Environment Variables:
 * - LANGSMITH_API_KEY: Your LangSmith API key
 * - LANGSMITH_ENDPOINT: (Optional) Custom endpoint (default: https://api.smith.langchain.com)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const LANGSMITH_API_KEY = process.env.LANGSMITH_API_KEY;
const LANGSMITH_ENDPOINT = process.env.LANGSMITH_ENDPOINT || "https://api.smith.langchain.com";

if (!LANGSMITH_API_KEY) {
  console.error("Missing required environment variable: LANGSMITH_API_KEY");
  process.exit(1);
}

async function langsmithRequest(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${LANGSMITH_ENDPOINT}${endpoint}`, {
    ...options,
    headers: {
      "x-api-key": LANGSMITH_API_KEY,
      "Content-Type": "application/json",
      "Accept": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`LangSmith API error: ${response.status} - ${error}`);
  }

  return response.json();
}

const server = new Server(
  {
    name: "langsmith-pm-tools",
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
      description: "Use when: listing LangSmith projects.",
      inputSchema: {
        type: "object",
        properties: {
          limit: {
            type: "number",
            description: "Maximum number of results (default 50)",
          },
          nameContains: {
            type: "string",
            description: "Filter by project name containing this string",
          },
        },
      },
    },
    {
      name: "get_project",
      description: "Use when: reading details of one LangSmith project.",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID or name",
          },
        },
        required: ["projectId"],
      },
    },
    {
      name: "list_runs",
      description: "Use when: listing runs or traces in a LangSmith project.",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID or name",
          },
          runType: {
            type: "string",
            description: "Filter by run type (llm, chain, tool, retriever, etc.)",
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
          error: {
            type: "boolean",
            description: "Filter by error status (true for errors only)",
          },
        },
        required: ["projectId"],
      },
    },
    {
      name: "get_run",
      description: "Use when: inspecting one LangSmith run.",
      inputSchema: {
        type: "object",
        properties: {
          runId: {
            type: "string",
            description: "Run ID",
          },
        },
        required: ["runId"],
      },
    },
    {
      name: "get_trace",
      description: "Use when: loading a full trace including child runs.",
      inputSchema: {
        type: "object",
        properties: {
          traceId: {
            type: "string",
            description: "Trace ID",
          },
        },
        required: ["traceId"],
      },
    },
    {
      name: "get_project_stats",
      description: "Use when: summarizing project health (run counts, errors, latency).",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID or name",
          },
          startTime: {
            type: "string",
            description: "Start time for stats (ISO 8601 format)",
          },
          endTime: {
            type: "string",
            description: "End time for stats (ISO 8601 format)",
          },
        },
        required: ["projectId"],
      },
    },
    {
      name: "list_datasets",
      description: "Use when: listing LangSmith datasets.",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID (optional, lists all if not provided)",
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
      description: "Use when: reading one LangSmith dataset.",
      inputSchema: {
        type: "object",
        properties: {
          datasetId: {
            type: "string",
            description: "Dataset ID or name",
          },
        },
        required: ["datasetId"],
      },
    },
    {
      name: "query_traces",
      description: "Use when: querying LangSmith traces with filters.",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID or name",
          },
          filter: {
            type: "string",
            description: "Filter expression (e.g., 'eq(status, \"error\")')",
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
      name: "get_eval_results",
      description: "Use when: loading eval results for a project or dataset.",
      inputSchema: {
        type: "object",
        properties: {
          projectId: {
            type: "string",
            description: "Project ID or name",
          },
          datasetId: {
            type: "string",
            description: "Dataset ID (optional)",
          },
          limit: {
            type: "number",
            description: "Maximum number of results (default 100)",
          },
        },
        required: ["projectId"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "list_projects": {
        const limit = (args?.limit as number) || 50;
        const nameContains = args?.nameContains as string;
        
        let endpoint = `/api/v1/projects?limit=${limit}`;
        if (nameContains) {
          endpoint += `&name_contains=${encodeURIComponent(nameContains)}`;
        }
        
        const result = await langsmithRequest(endpoint);
        
        const projects = (result.projects || result || []).map((p: any) => ({
          id: p.id,
          name: p.name,
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
        const project = await langsmithRequest(`/api/v1/projects/${projectId}`);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id: project.id,
                name: project.name,
                description: project.description || "",
                createdAt: project.created_at || project.createdAt,
                updatedAt: project.updated_at || project.updatedAt,
              }, null, 2),
            },
          ],
        };
      }

      case "list_runs": {
        const projectId = args?.projectId as string;
        const runType = args?.runType as string;
        const startTime = args?.startTime as string;
        const endTime = args?.endTime as string;
        const limit = (args?.limit as number) || 100;
        const error = args?.error as boolean;
        
        let endpoint = `/api/v1/runs?project_name=${encodeURIComponent(projectId)}&limit=${limit}`;
        if (runType) endpoint += `&run_type=${runType}`;
        if (startTime) endpoint += `&start_time=${encodeURIComponent(startTime)}`;
        if (endTime) endpoint += `&end_time=${encodeURIComponent(endTime)}`;
        if (error !== undefined) endpoint += `&error=${error}`;
        
        const result = await langsmithRequest(endpoint);
        
        const runs = (result.runs || result || []).map((r: any) => ({
          id: r.id,
          traceId: r.trace_id || r.traceId,
          name: r.name || "",
          runType: r.run_type || r.runType || "unknown",
          status: r.status || "unknown",
          error: r.error || null,
          latency: r.latency || null,
          startTime: r.start_time || r.startTime,
          endTime: r.end_time || r.endTime,
          inputs: r.inputs || {},
          outputs: r.outputs || {},
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ count: runs.length, runs }, null, 2),
            },
          ],
        };
      }

      case "get_run": {
        const runId = args?.runId as string;
        const run = await langsmithRequest(`/api/v1/runs/${runId}`);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id: run.id,
                traceId: run.trace_id || run.traceId,
                name: run.name || "",
                runType: run.run_type || run.runType || "unknown",
                status: run.status || "unknown",
                error: run.error || null,
                latency: run.latency || null,
                startTime: run.start_time || run.startTime,
                endTime: run.end_time || run.endTime,
                inputs: run.inputs || {},
                outputs: run.outputs || {},
                metadata: run.metadata || {},
                feedback: run.feedback || [],
              }, null, 2),
            },
          ],
        };
      }

      case "get_trace": {
        const traceId = args?.traceId as string;
        const trace = await langsmithRequest(`/api/v1/traces/${traceId}`);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id: trace.id,
                name: trace.name || "",
                startTime: trace.start_time || trace.startTime,
                endTime: trace.end_time || trace.endTime,
                latency: trace.latency || null,
                status: trace.status || "unknown",
                runs: trace.runs || [],
              }, null, 2),
            },
          ],
        };
      }

      case "get_project_stats": {
        const projectId = args?.projectId as string;
        const startTime = args?.startTime as string;
        const endTime = args?.endTime as string;
        
        let endpoint = `/api/v1/runs?project_name=${encodeURIComponent(projectId)}&limit=1000`;
        if (startTime) endpoint += `&start_time=${encodeURIComponent(startTime)}`;
        if (endTime) endpoint += `&end_time=${encodeURIComponent(endTime)}`;
        
        const result = await langsmithRequest(endpoint);
        const runs = result.runs || result || [];
        
        const stats = {
          projectId,
          totalRuns: runs.length,
          errorRuns: runs.filter((r: any) => r.error || r.status === "error").length,
          successRuns: runs.filter((r: any) => !r.error && r.status === "success").length,
          averageLatency: null as number | null,
          errorRate: 0,
        };
        
        if (runs.length > 0) {
          stats.errorRate = (stats.errorRuns / stats.totalRuns) * 100;
          
          const latencies = runs
            .map((r: any) => r.latency)
            .filter((l: any) => typeof l === "number" && l > 0);
          
          if (latencies.length > 0) {
            stats.averageLatency = 
              latencies.reduce((a: number, b: number) => a + b, 0) / latencies.length;
          }
        }
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(stats, null, 2),
            },
          ],
        };
      }

      case "list_datasets": {
        const projectId = args?.projectId as string;
        const limit = (args?.limit as number) || 50;
        
        let endpoint = `/api/v1/datasets?limit=${limit}`;
        if (projectId) {
          endpoint += `&project_name=${encodeURIComponent(projectId)}`;
        }
        
        const result = await langsmithRequest(endpoint);
        
        const datasets = (result.datasets || result || []).map((d: any) => ({
          id: d.id,
          name: d.name,
          description: d.description || "",
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
        const dataset = await langsmithRequest(`/api/v1/datasets/${datasetId}`);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id: dataset.id,
                name: dataset.name,
                description: dataset.description || "",
                createdAt: dataset.created_at || dataset.createdAt,
                exampleCount: dataset.example_count || dataset.exampleCount || 0,
              }, null, 2),
            },
          ],
        };
      }

      case "query_traces": {
        const projectId = args?.projectId as string;
        const filter = args?.filter as string;
        const startTime = args?.startTime as string;
        const endTime = args?.endTime as string;
        const limit = (args?.limit as number) || 100;
        
        let endpoint = `/api/v1/traces?project_name=${encodeURIComponent(projectId)}&limit=${limit}`;
        if (filter) endpoint += `&filter=${encodeURIComponent(filter)}`;
        if (startTime) endpoint += `&start_time=${encodeURIComponent(startTime)}`;
        if (endTime) endpoint += `&end_time=${encodeURIComponent(endTime)}`;
        
        const result = await langsmithRequest(endpoint);
        
        const traces = (result.traces || result || []).map((t: any) => ({
          id: t.id,
          name: t.name || "",
          startTime: t.start_time || t.startTime,
          endTime: t.end_time || t.endTime,
          latency: t.latency || null,
          status: t.status || "unknown",
        }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ count: traces.length, traces }, null, 2),
            },
          ],
        };
      }

      case "get_eval_results": {
        const projectId = args?.projectId as string;
        const datasetId = args?.datasetId as string;
        const limit = (args?.limit as number) || 100;
        
        let endpoint = `/api/v1/runs?project_name=${encodeURIComponent(projectId)}&limit=${limit}`;
        if (datasetId) {
          endpoint += `&reference_example_id=${datasetId}`;
        }
        
        const result = await langsmithRequest(endpoint);
        const runs = result.runs || result || [];
        
        // Filter for evaluation runs and extract results
        const evalResults = runs
          .filter((r: any) => r.run_type === "chain" || r.name?.toLowerCase().includes("eval"))
          .map((r: any) => ({
            id: r.id,
            name: r.name || "",
            status: r.status || "unknown",
            inputs: r.inputs || {},
            outputs: r.outputs || {},
            feedback: r.feedback || [],
            latency: r.latency || null,
            startTime: r.start_time || r.startTime,
          }));
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ count: evalResults.length, results: evalResults }, null, 2),
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
  console.error("LangSmith PM Tools MCP server running");
}

main().catch(console.error);

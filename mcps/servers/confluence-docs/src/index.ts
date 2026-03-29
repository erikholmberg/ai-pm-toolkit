#!/usr/bin/env node
/**
 * Confluence Docs MCP Server
 * 
 * An MCP server that provides Confluence integration for Product Managers.
 * 
 * Capabilities:
 * - Search documentation
 * - Create and publish pages
 * - Create meeting notes
 * 
 * Environment Variables:
 * - CONFLUENCE_HOST: Your Confluence host (e.g., yourcompany.atlassian.net)
 * - CONFLUENCE_EMAIL: Your Atlassian account email
 * - CONFLUENCE_API_TOKEN: Your Atlassian API token
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const CONFLUENCE_HOST = process.env.CONFLUENCE_HOST;
const CONFLUENCE_EMAIL = process.env.CONFLUENCE_EMAIL;
const CONFLUENCE_API_TOKEN = process.env.CONFLUENCE_API_TOKEN;

if (!CONFLUENCE_HOST || !CONFLUENCE_EMAIL || !CONFLUENCE_API_TOKEN) {
  console.error("Missing required environment variables");
  process.exit(1);
}

const BASE_URL = `https://${CONFLUENCE_HOST}/wiki/api/v2`;
const AUTH_HEADER = `Basic ${Buffer.from(`${CONFLUENCE_EMAIL}:${CONFLUENCE_API_TOKEN}`).toString("base64")}`;

async function confluenceRequest(endpoint: string, options: RequestInit = {}) {
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
    throw new Error(`Confluence API error: ${response.status} - ${error}`);
  }

  return response.json();
}

const server = new Server(
  {
    name: "confluence-docs",
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
      name: "search_pages",
      description: "Use when: finding Confluence wiki pages by text search.",
      inputSchema: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Search query",
          },
          spaceKey: {
            type: "string",
            description: "Optional: Limit search to a specific space",
          },
          maxResults: {
            type: "number",
            description: "Maximum results (default 10)",
          },
        },
        required: ["query"],
      },
    },
    {
      name: "get_page",
      description: "Use when: reading the full content of a Confluence page.",
      inputSchema: {
        type: "object",
        properties: {
          pageId: {
            type: "string",
            description: "The page ID",
          },
        },
        required: ["pageId"],
      },
    },
    {
      name: "create_page",
      description: "Use when: publishing a new Confluence page.",
      inputSchema: {
        type: "object",
        properties: {
          spaceId: {
            type: "string",
            description: "The space ID to create the page in",
          },
          title: {
            type: "string",
            description: "Page title",
          },
          content: {
            type: "string",
            description: "Page content (HTML or markdown)",
          },
          parentPageId: {
            type: "string",
            description: "Optional: Parent page ID",
          },
        },
        required: ["spaceId", "title", "content"],
      },
    },
    {
      name: "list_spaces",
      description: "Use when: discovering available Confluence spaces.",
      inputSchema: {
        type: "object",
        properties: {
          type: {
            type: "string",
            description: "Space type filter (global, personal)",
          },
        },
      },
    },
    {
      name: "create_meeting_notes",
      description: "Use when: creating meeting notes from a template.",
      inputSchema: {
        type: "object",
        properties: {
          spaceId: {
            type: "string",
            description: "Space ID for the meeting notes",
          },
          meetingTitle: {
            type: "string",
            description: "Title of the meeting",
          },
          date: {
            type: "string",
            description: "Meeting date (YYYY-MM-DD)",
          },
          attendees: {
            type: "array",
            items: { type: "string" },
            description: "List of attendee names",
          },
          agenda: {
            type: "array",
            items: { type: "string" },
            description: "Agenda items",
          },
        },
        required: ["spaceId", "meetingTitle", "date"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "search_pages": {
        const query = args?.query as string;
        const spaceKey = args?.spaceKey as string;
        const maxResults = (args?.maxResults as number) || 10;
        
        let cql = `text ~ "${query}"`;
        if (spaceKey) {
          cql += ` AND space.key = "${spaceKey}"`;
        }
        
        const result = await confluenceRequest(
          `/search?cql=${encodeURIComponent(cql)}&limit=${maxResults}`
        );
        
        const pages = result.results?.map((item: any) => ({
          id: item.content?.id,
          title: item.content?.title,
          space: item.content?.space?.name,
          url: `https://${CONFLUENCE_HOST}/wiki${item.url}`,
          excerpt: item.excerpt,
        })) || [];
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ total: result.totalSize, pages }, null, 2),
            },
          ],
        };
      }

      case "get_page": {
        const pageId = args?.pageId as string;
        const page = await confluenceRequest(`/pages/${pageId}?body-format=storage`);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id: page.id,
                title: page.title,
                content: page.body?.storage?.value,
                version: page.version?.number,
                url: `https://${CONFLUENCE_HOST}/wiki/pages/${page.id}`,
              }, null, 2),
            },
          ],
        };
      }

      case "create_page": {
        const pageData = {
          spaceId: args?.spaceId as string,
          title: args?.title as string,
          parentId: args?.parentPageId as string,
          body: {
            representation: "storage",
            value: args?.content as string,
          },
        };
        
        const result = await confluenceRequest("/pages", {
          method: "POST",
          body: JSON.stringify(pageData),
        });
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                id: result.id,
                title: result.title,
                url: `https://${CONFLUENCE_HOST}/wiki/pages/${result.id}`,
              }, null, 2),
            },
          ],
        };
      }

      case "list_spaces": {
        const type = args?.type as string;
        let endpoint = "/spaces?limit=50";
        if (type) {
          endpoint += `&type=${type}`;
        }
        
        const result = await confluenceRequest(endpoint);
        
        const spaces = result.results?.map((space: any) => ({
          id: space.id,
          key: space.key,
          name: space.name,
          type: space.type,
        })) || [];
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ spaces }, null, 2),
            },
          ],
        };
      }

      case "create_meeting_notes": {
        const meetingTitle = args?.meetingTitle as string;
        const date = args?.date as string;
        const attendees = (args?.attendees as string[]) || [];
        const agenda = (args?.agenda as string[]) || [];
        
        const content = `
<h2>Meeting Details</h2>
<p><strong>Date:</strong> ${date}</p>
<p><strong>Attendees:</strong> ${attendees.join(", ") || "TBD"}</p>

<h2>Agenda</h2>
<ul>
${agenda.map((item) => `<li>${item}</li>`).join("\n") || "<li>TBD</li>"}
</ul>

<h2>Discussion Notes</h2>
<p><em>Add notes here...</em></p>

<h2>Action Items</h2>
<table>
<tr><th>Action</th><th>Owner</th><th>Due Date</th></tr>
<tr><td></td><td></td><td></td></tr>
</table>

<h2>Decisions</h2>
<ul>
<li><em>Add decisions made...</em></li>
</ul>
`;
        
        const pageData = {
          spaceId: args?.spaceId as string,
          title: `${meetingTitle} - ${date}`,
          body: {
            representation: "storage",
            value: content,
          },
        };
        
        const result = await confluenceRequest("/pages", {
          method: "POST",
          body: JSON.stringify(pageData),
        });
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                id: result.id,
                title: result.title,
                url: `https://${CONFLUENCE_HOST}/wiki/pages/${result.id}`,
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
  console.error("Confluence Docs MCP server running");
}

main().catch(console.error);


#!/usr/bin/env node
/**
 * Notion PM Tools MCP Server
 *
 * Search and create Notion pages, list databases, create meeting notes.
 * Requires pages/databases to be shared with your integration.
 *
 * Environment: NOTION_API_KEY (integration token from Notion → Settings → Integrations)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const NOTION_API_KEY = process.env.NOTION_API_KEY;
const NOTION_VERSION = "2022-06-28";

if (!NOTION_API_KEY) {
  console.error("Missing NOTION_API_KEY");
  process.exit(1);
}

const NOTION_HEADERS: Record<string, string> = {
  Authorization: `Bearer ${NOTION_API_KEY}`,
  "Notion-Version": NOTION_VERSION,
  "Content-Type": "application/json",
};

type NotionFetchOptions = {
  method?: string;
  body?: Record<string, unknown>;
  headers?: Record<string, string>;
};

async function notionFetch(path: string, options: NotionFetchOptions = {}): Promise<any> {
  const { method = "GET", body, headers = {} } = options;
  const res = await fetch(`https://api.notion.com${path}`, {
    method,
    headers: { ...NOTION_HEADERS, ...headers } as HeadersInit,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`Notion API ${res.status}: ${text}`);
  }
  return text ? JSON.parse(text) : {};
}

function richText(content: string): Array<{ type: "text"; text: { content: string } }> {
  return [{ type: "text" as const, text: { content } }];
}

function blockParagraph(text: string): object {
  return { type: "paragraph", paragraph: { rich_text: richText(text) } };
}

function blockHeading1(text: string): object {
  return { type: "heading_1", heading_1: { rich_text: richText(text) } };
}

function blockHeading2(text: string): object {
  return { type: "heading_2", heading_2: { rich_text: richText(text) } };
}

function blockBulletedItem(text: string): object {
  return { type: "bulleted_list_item", bulleted_list_item: { rich_text: richText(text) } };
}

/** Convert plain text with optional markdown-style headers into Notion blocks */
function textToBlocks(text: string): object[] {
  const blocks: object[] = [];
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  for (const line of lines) {
    const t = line.trim();
    if (!t) continue;
    if (t.startsWith("## ")) {
      blocks.push(blockHeading2(t.slice(3)));
    } else if (t.startsWith("# ")) {
      blocks.push(blockHeading1(t.slice(2)));
    } else if (t.startsWith("- ") || t.startsWith("* ")) {
      blocks.push(blockBulletedItem(t.slice(2)));
    } else {
      blocks.push(blockParagraph(t));
    }
  }
  return blocks.length ? blocks : [blockParagraph("(No content)")];
}

const server = new Server(
  { name: "notion-pm-tools", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "notion_search_pages",
      description: "Use when: searching Notion pages by title (integration must have access).",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query (title contains)" },
          page_size: { type: "number", description: "Max results (1–100, default 10)" },
        },
        required: ["query"],
      },
    },
    {
      name: "notion_list_databases",
      description: "Use when: listing databases visible to the Notion integration.",
      inputSchema: {
        type: "object",
        properties: {
          page_size: { type: "number", description: "Max results (default 20)" },
        },
      },
    },
    {
      name: "notion_get_page",
      description: "Use when: reading a Notion page (title, URL, block content).",
      inputSchema: {
        type: "object",
        properties: {
          page_id: { type: "string", description: "Notion page ID (UUID)" },
        },
        required: ["page_id"],
      },
    },
    {
      name: "notion_create_page",
      description: "Use when: creating a child page under a parent (plain text or markdown body).",
      inputSchema: {
        type: "object",
        properties: {
          parent_page_id: { type: "string", description: "Parent page ID (page must be shared with integration)" },
          title: { type: "string", description: "Page title" },
          content: { type: "string", description: "Body content (plain text or markdown: # ## - )" },
        },
        required: ["parent_page_id", "title"],
      },
    },
    {
      name: "notion_create_page_in_database",
      description: "Use when: adding a row as a new page in a Notion database.",
      inputSchema: {
        type: "object",
        properties: {
          database_id: { type: "string", description: "Notion database ID" },
          title_property: { type: "string", description: "Name of the title property (often 'Name' or 'Title')" },
          title: { type: "string", description: "Value for the title property" },
          content: { type: "string", description: "Optional body content for the new page" },
        },
        required: ["database_id", "title_property", "title"],
      },
    },
    {
      name: "notion_create_meeting_notes",
      description: "Use when: creating structured meeting notes under a parent page.",
      inputSchema: {
        type: "object",
        properties: {
          parent_page_id: { type: "string", description: "Parent page ID for the new page" },
          meeting_title: { type: "string", description: "Meeting title" },
          date: { type: "string", description: "Meeting date (e.g. YYYY-MM-DD)" },
          attendees: { type: "array", items: { type: "string" }, description: "Attendee names" },
          agenda: { type: "array", items: { type: "string" }, description: "Agenda items" },
        },
        required: ["parent_page_id", "meeting_title", "date"],
      },
    },
    {
      name: "notion_query_database",
      description: "Use when: querying a Notion database with filter/sort.",
      inputSchema: {
        type: "object",
        properties: {
          database_id: { type: "string", description: "Notion database ID" },
          page_size: { type: "number", description: "Max results (default 20)" },
        },
        required: ["database_id"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  const out = (obj: object) => ({
    content: [{ type: "text" as const, text: JSON.stringify(obj, null, 2) }],
  });
  const err = (message: string) => ({
    content: [{ type: "text" as const, text: `Error: ${message}` }],
    isError: true,
  });

  try {
    switch (name) {
      case "notion_search_pages": {
        const query = (args?.query as string) || "";
        const page_size = Math.min(100, Math.max(1, (args?.page_size as number) || 10));
        const body: Record<string, unknown> = {
          page_size,
          filter: { property: "object", value: "page" as const },
        };
        if (query) body.query = query;
        const data = await notionFetch("/v1/search", { method: "POST", body: body as Record<string, unknown> });
        const results = (data.results || []).map((p: any) => ({
          id: p.id,
          title: p.properties?.title?.title?.[0]?.plain_text ?? "(no title)",
          url: p.url,
          last_edited_time: p.last_edited_time,
        }));
        return out({ total: data.results?.length ?? 0, pages: results, has_more: !!data.next_cursor });
      }

      case "notion_list_databases": {
        const page_size = Math.min(100, Math.max(1, (args?.page_size as number) || 20));
        const data = await notionFetch("/v1/search", {
          method: "POST",
          body: {
            page_size,
            filter: { property: "object", value: "data_source" },
          } as Record<string, unknown>,
        });
        const results = (data.results || []).map((d: any) => ({
          id: d.id,
          title: (d.title && d.title[0]?.plain_text) ?? d.properties?.title?.title?.[0]?.plain_text ?? "(no title)",
          url: d.url,
        }));
        return out({ databases: results, has_more: !!data.next_cursor });
      }

      case "notion_get_page": {
        const page_id = (args?.page_id as string)?.replace(/-/g, "");
        if (!page_id) return err("page_id required");
        const page = await notionFetch(`/v1/pages/${page_id}`);
        const title =
          page.properties?.title?.title?.[0]?.plain_text ??
          (Object.values(page.properties || {})[0] as any)?.title?.[0]?.plain_text ??
          "(no title)";
        const blocksRes = await notionFetch(`/v1/blocks/${page_id}/children?page_size=100`);
        const blocks = (blocksRes.results || []).map((b: any) => {
          const type = b.type;
          const content = b[type];
          const text = content?.rich_text?.map((r: any) => r.plain_text).join(" ") ?? "";
          return { type, text };
        });
        return out({
          id: page.id,
          title,
          url: page.url,
          last_edited_time: page.last_edited_time,
          content_blocks: blocks,
        });
      }

      case "notion_create_page": {
        const parent_page_id = (args?.parent_page_id as string)?.replace(/-/g, "");
        const title = args?.title as string;
        const content = (args?.content as string) || "";
        if (!parent_page_id || !title) return err("parent_page_id and title required");

        const body: any = {
          parent: { type: "page_id", page_id: parent_page_id },
          properties: { title: { title: [{ type: "text", text: { content: title } }] } },
        };
        const blocks = textToBlocks(content);
        if (blocks.length) body.children = blocks;

        const created = await notionFetch("/v1/pages", { method: "POST", body: body as Record<string, unknown> });
        return out({
          success: true,
          id: created.id,
          url: created.url,
          title,
        });
      }

      case "notion_create_page_in_database": {
        const database_id = (args?.database_id as string)?.replace(/-/g, "");
        const title_property = args?.title_property as string;
        const title = args?.title as string;
        const content = (args?.content as string) || "";
        if (!database_id || !title_property || !title) return err("database_id, title_property, and title required");

        const body: any = {
          parent: { type: "database_id", database_id: database_id },
          properties: {
            [title_property]: { title: [{ type: "text", text: { content: title } }] },
          },
        };
        const blocks = textToBlocks(content);
        if (blocks.length) body.children = blocks;

        const created = await notionFetch("/v1/pages", { method: "POST", body: body as Record<string, unknown> });
        return out({
          success: true,
          id: created.id,
          url: created.url,
          title,
        });
      }

      case "notion_create_meeting_notes": {
        const parent_page_id = (args?.parent_page_id as string)?.replace(/-/g, "");
        const meeting_title = args?.meeting_title as string;
        const date = args?.date as string;
        const attendees = (args?.attendees as string[]) || [];
        const agenda = (args?.agenda as string[]) || [];
        if (!parent_page_id || !meeting_title || !date) return err("parent_page_id, meeting_title, and date required");

        const children = [
          blockHeading1(`${meeting_title} – ${date}`),
          blockHeading2("Attendees"),
          blockParagraph(attendees.length ? attendees.join(", ") : "TBD"),
          blockHeading2("Agenda"),
          ...(agenda.length ? agenda.map(blockBulletedItem) : [blockParagraph("TBD")]),
          blockHeading2("Notes"),
          blockParagraph("(Add notes here)"),
          blockHeading2("Action Items"),
          blockBulletedItem("(Add action items)"),
          blockHeading2("Decisions"),
          blockBulletedItem("(Add decisions)"),
        ];

        const body = {
          parent: { type: "page_id", page_id: parent_page_id },
          properties: { title: { title: [{ type: "text", text: { content: `${meeting_title} – ${date}` } }] } },
          children,
        };
        const created = await notionFetch("/v1/pages", { method: "POST", body: body as Record<string, unknown> });
        return out({
          success: true,
          id: created.id,
          url: created.url,
          title: `${meeting_title} – ${date}`,
        });
      }

      case "notion_query_database": {
        const database_id = (args?.database_id as string)?.replace(/-/g, "");
        const page_size = Math.min(100, Math.max(1, (args?.page_size as number) || 20));
        if (!database_id) return err("database_id required");
        const data = await notionFetch("/v1/databases/" + database_id + "/query", {
          method: "POST",
          body: { page_size } as Record<string, unknown>,
        });
        const results = (data.results || []).map((p: any) => {
          const props = p.properties || {};
          const titleKey = Object.keys(props).find((k) => (props as any)[k]?.title != null);
          const title = titleKey ? (props as any)[titleKey].title?.[0]?.plain_text : "(no title)";
          return { id: p.id, title, url: p.url, last_edited_time: p.last_edited_time };
        });
        return out({ results, has_more: !!data.next_cursor });
      }

      default:
        return err(`Unknown tool: ${name}`);
    }
  } catch (e) {
    return err(e instanceof Error ? e.message : String(e));
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Notion PM Tools MCP server running");
}

main().catch(console.error);

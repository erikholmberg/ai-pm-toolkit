#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

type AnalyticsEvent = {
  eventName: string;
  timestamp: string;
  userId: string;
  segment?: string;
  properties?: Record<string, unknown>;
};

type AnalyticsDataset = {
  events: AnalyticsEvent[];
};

const ANALYTICS_DATA_PATH = process.env.ANALYTICS_DATA_PATH;
if (!ANALYTICS_DATA_PATH) {
  console.error("Missing required environment variable: ANALYTICS_DATA_PATH");
  process.exit(1);
}

function loadDataset(): AnalyticsDataset {
  const content = readFileSync(ANALYTICS_DATA_PATH as string, "utf-8");
  const parsed = JSON.parse(content) as AnalyticsDataset;
  if (!Array.isArray(parsed.events)) {
    throw new Error("Invalid dataset. Expected JSON with an `events` array.");
  }
  return parsed;
}

function inRange(timestamp: string, start?: string, end?: string): boolean {
  const t = new Date(timestamp).getTime();
  if (Number.isNaN(t)) return false;
  if (start && t < new Date(start).getTime()) return false;
  if (end && t > new Date(end).getTime()) return false;
  return true;
}

function bySegment(events: AnalyticsEvent[], segment?: string): AnalyticsEvent[] {
  if (!segment) return events;
  return events.filter((e) => (e.segment ?? "unknown") === segment);
}

function periodKey(ts: string, granularity: string): string {
  const d = new Date(ts);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  if (granularity === "month") return `${y}-${m}`;
  if (granularity === "day") return `${y}-${m}-${day}`;
  const date = new Date(Date.UTC(y, d.getUTCMonth(), d.getUTCDate()));
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((date.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(weekNo).padStart(2, "0")}`;
}

const server = new Server(
  { name: "product-analytics-pm-tools", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "event_trend",
      description: "Use when: analyzing event volume and unique users over time (sample analytics dataset).",
      inputSchema: {
        type: "object",
        properties: {
          eventName: { type: "string", description: "Event to analyze" },
          startTime: { type: "string", description: "ISO timestamp lower bound" },
          endTime: { type: "string", description: "ISO timestamp upper bound" },
          granularity: { type: "string", enum: ["day", "week", "month"], description: "Time bucket" },
          segment: { type: "string", description: "Optional segment filter" },
        },
        required: ["eventName"],
      },
    },
    {
      name: "funnel_conversion",
      description: "Use when: measuring conversion through ordered funnel steps (sample analytics dataset).",
      inputSchema: {
        type: "object",
        properties: {
          steps: { type: "array", items: { type: "string" }, description: "Ordered event names" },
          startTime: { type: "string", description: "ISO timestamp lower bound" },
          endTime: { type: "string", description: "ISO timestamp upper bound" },
          segment: { type: "string", description: "Optional segment filter" },
        },
        required: ["steps"],
      },
    },
    {
      name: "retention_by_cohort",
      description: "Use when: estimating cohort retention (sample analytics dataset).",
      inputSchema: {
        type: "object",
        properties: {
          acquisitionEvent: { type: "string", description: "Event treated as acquisition" },
          returnEvent: { type: "string", description: "Return event (default any event)" },
          windows: { type: "array", items: { type: "number" }, description: "Day windows e.g. [1,7,30]" },
          segment: { type: "string", description: "Optional segment filter" },
        },
        required: ["acquisitionEvent"],
      },
    },
    {
      name: "cohort_compare",
      description: "Use when: comparing two segments on one event (sample analytics dataset).",
      inputSchema: {
        type: "object",
        properties: {
          eventName: { type: "string", description: "Event to compare" },
          cohortA: { type: "string", description: "Segment A" },
          cohortB: { type: "string", description: "Segment B" },
          startTime: { type: "string", description: "ISO timestamp lower bound" },
          endTime: { type: "string", description: "ISO timestamp upper bound" },
        },
        required: ["eventName", "cohortA", "cohortB"],
      },
    },
    {
      name: "segment_compare",
      description: "Use when: comparing event volume and uniques across segments (sample analytics dataset).",
      inputSchema: {
        type: "object",
        properties: {
          eventName: { type: "string", description: "Event to compare" },
          segments: { type: "array", items: { type: "string" }, description: "List of segments" },
          startTime: { type: "string", description: "ISO timestamp lower bound" },
          endTime: { type: "string", description: "ISO timestamp upper bound" },
        },
        required: ["eventName", "segments"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    const data = loadDataset();
    const startTime = args?.startTime as string | undefined;
    const endTime = args?.endTime as string | undefined;
    const filtered = data.events.filter((e) => inRange(e.timestamp, startTime, endTime));

    switch (name) {
      case "event_trend": {
        const eventName = args?.eventName as string;
        const granularity = (args?.granularity as string) || "week";
        const segment = args?.segment as string | undefined;
        const rows = bySegment(filtered, segment).filter((e) => e.eventName === eventName);
        const buckets = new Map<string, { events: number; users: Set<string> }>();
        for (const event of rows) {
          const key = periodKey(event.timestamp, granularity);
          if (!buckets.has(key)) buckets.set(key, { events: 0, users: new Set() });
          const bucket = buckets.get(key)!;
          bucket.events += 1;
          bucket.users.add(event.userId);
        }
        const trend = [...buckets.entries()]
          .sort((a, b) => a[0].localeCompare(b[0]))
          .map(([period, values]) => ({ period, events: values.events, uniqueUsers: values.users.size }));
        return { content: [{ type: "text", text: JSON.stringify({ eventName, trend }, null, 2) }] };
      }

      case "funnel_conversion": {
        const steps = (args?.steps as string[]) || [];
        if (steps.length < 2) throw new Error("steps must include at least 2 events");
        const segment = args?.segment as string | undefined;
        const rows = bySegment(filtered, segment);
        const byUser = new Map<string, Set<string>>();
        for (const event of rows) {
          if (!byUser.has(event.userId)) byUser.set(event.userId, new Set());
          byUser.get(event.userId)!.add(event.eventName);
        }
        const counts = steps.map((step) => {
          let n = 0;
          byUser.forEach((events) => {
            if (events.has(step)) n += 1;
          });
          return n;
        });
        const first = counts[0] || 1;
        const report = steps.map((step, i) => ({
          step,
          users: counts[i],
          stepConversionPct: i === 0 ? 100 : Number(((counts[i] / (counts[i - 1] || 1)) * 100).toFixed(2)),
          overallConversionPct: Number(((counts[i] / first) * 100).toFixed(2)),
        }));
        return { content: [{ type: "text", text: JSON.stringify({ steps: report }, null, 2) }] };
      }

      case "retention_by_cohort": {
        const acquisitionEvent = args?.acquisitionEvent as string;
        const returnEvent = args?.returnEvent as string | undefined;
        const windows = ((args?.windows as number[]) || [1, 7, 30]).sort((a, b) => a - b);
        const segment = args?.segment as string | undefined;
        const rows = bySegment(filtered, segment);

        const firstSeen = new Map<string, Date>();
        const eventsByUser = new Map<string, AnalyticsEvent[]>();
        for (const event of rows) {
          if (!eventsByUser.has(event.userId)) eventsByUser.set(event.userId, []);
          eventsByUser.get(event.userId)!.push(event);
          if (event.eventName === acquisitionEvent && !firstSeen.has(event.userId)) {
            firstSeen.set(event.userId, new Date(event.timestamp));
          }
        }
        const acquiredUsers = [...firstSeen.keys()];
        const retention = windows.map((windowDays) => {
          let retained = 0;
          for (const userId of acquiredUsers) {
            const acquiredAt = firstSeen.get(userId)!;
            const lower = acquiredAt.getTime() + windowDays * 86400000;
            const upper = lower + 86400000;
            const userEvents = eventsByUser.get(userId) || [];
            const found = userEvents.some((event) => {
              const t = new Date(event.timestamp).getTime();
              const eventMatch = returnEvent ? event.eventName === returnEvent : true;
              return eventMatch && t >= lower && t < upper;
            });
            if (found) retained += 1;
          }
          return {
            day: windowDays,
            retainedUsers: retained,
            totalUsers: acquiredUsers.length,
            retentionPct: acquiredUsers.length === 0 ? 0 : Number(((retained / acquiredUsers.length) * 100).toFixed(2)),
          };
        });
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ acquisitionEvent, returnEvent: returnEvent || "any", retention }, null, 2),
            },
          ],
        };
      }

      case "cohort_compare": {
        const eventName = args?.eventName as string;
        const cohortA = args?.cohortA as string;
        const cohortB = args?.cohortB as string;

        const onlyEvent = filtered.filter((e) => e.eventName === eventName);
        const usersA = new Set(onlyEvent.filter((e) => (e.segment ?? "unknown") === cohortA).map((e) => e.userId));
        const usersB = new Set(onlyEvent.filter((e) => (e.segment ?? "unknown") === cohortB).map((e) => e.userId));
        const totalUsersA = new Set(filtered.filter((e) => (e.segment ?? "unknown") === cohortA).map((e) => e.userId));
        const totalUsersB = new Set(filtered.filter((e) => (e.segment ?? "unknown") === cohortB).map((e) => e.userId));

        const rateA = totalUsersA.size === 0 ? 0 : (usersA.size / totalUsersA.size) * 100;
        const rateB = totalUsersB.size === 0 ? 0 : (usersB.size / totalUsersB.size) * 100;

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  eventName,
                  cohortA: { name: cohortA, convertedUsers: usersA.size, totalUsers: totalUsersA.size, conversionPct: Number(rateA.toFixed(2)) },
                  cohortB: { name: cohortB, convertedUsers: usersB.size, totalUsers: totalUsersB.size, conversionPct: Number(rateB.toFixed(2)) },
                  deltaPctPoints: Number((rateA - rateB).toFixed(2)),
                },
                null,
                2
              ),
            },
          ],
        };
      }

      case "segment_compare": {
        const eventName = args?.eventName as string;
        const segments = (args?.segments as string[]) || [];
        const rows = filtered.filter((e) => e.eventName === eventName);
        const comparison = segments.map((segment) => {
          const segmentRows = rows.filter((e) => (e.segment ?? "unknown") === segment);
          return {
            segment,
            eventCount: segmentRows.length,
            uniqueUsers: new Set(segmentRows.map((e) => e.userId)).size,
          };
        });
        return { content: [{ type: "text", text: JSON.stringify({ eventName, comparison }, null, 2) }] };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error: ${error instanceof Error ? error.message : String(error)}` }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Product Analytics PM Tools MCP server running");
}

main().catch(console.error);

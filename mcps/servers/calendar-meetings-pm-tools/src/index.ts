#!/usr/bin/env node
/**
 * Calendar Meetings PM Tools MCP Server
 *
 * Google Calendar-backed tools for Product Manager meeting workflows:
 * list upcoming meetings, search events, inspect one event, check free/busy,
 * create events, and draft meeting agendas.
 *
 * Environment:
 * - GOOGLE_CLIENT_ID
 * - GOOGLE_CLIENT_SECRET
 * - GOOGLE_REFRESH_TOKEN
 * - GOOGLE_CALENDAR_ID (optional, defaults to "primary")
 * - CALENDAR_TIME_ZONE (optional, defaults to "UTC")
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
const GOOGLE_REFRESH_TOKEN = process.env.GOOGLE_REFRESH_TOKEN;
const DEFAULT_CALENDAR_ID = process.env.GOOGLE_CALENDAR_ID || "primary";
const DEFAULT_TIME_ZONE = process.env.CALENDAR_TIME_ZONE || "UTC";

if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET || !GOOGLE_REFRESH_TOKEN) {
  console.error(
    "Missing required environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN"
  );
  process.exit(1);
}

type JsonObject = Record<string, unknown>;

type GoogleEventDate = {
  date?: string;
  dateTime?: string;
  timeZone?: string;
};

type GoogleEventAttendee = {
  email?: string;
  displayName?: string;
  responseStatus?: string;
  optional?: boolean;
};

type GoogleCalendarEvent = {
  id?: string;
  htmlLink?: string;
  summary?: string;
  description?: string;
  location?: string;
  status?: string;
  start?: GoogleEventDate;
  end?: GoogleEventDate;
  attendees?: GoogleEventAttendee[];
  organizer?: { email?: string; displayName?: string };
  creator?: { email?: string; displayName?: string };
  conferenceData?: {
    conferenceId?: string;
    entryPoints?: Array<{ entryPointType?: string; uri?: string; label?: string }>;
  };
};

let cachedAccessToken: string | null = null;
let accessTokenExpiresAt = 0;

async function getAccessToken(): Promise<string> {
  if (cachedAccessToken && Date.now() < accessTokenExpiresAt - 60_000) {
    return cachedAccessToken;
  }

  const body = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID!,
    client_secret: GOOGLE_CLIENT_SECRET!,
    refresh_token: GOOGLE_REFRESH_TOKEN!,
    grant_type: "refresh_token",
  });

  const response = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`Google OAuth ${response.status}: ${text}`);
  }

  const data = JSON.parse(text) as { access_token?: string; expires_in?: number };
  if (!data.access_token) {
    throw new Error("Google OAuth response did not include an access token");
  }

  cachedAccessToken = data.access_token;
  accessTokenExpiresAt = Date.now() + ((data.expires_in || 3600) * 1000);
  return cachedAccessToken;
}

async function googleCalendarFetch(path: string, options: { method?: string; body?: JsonObject } = {}): Promise<any> {
  const token = await getAccessToken();
  const { method = "GET", body } = options;
  const response = await fetch(`https://www.googleapis.com/calendar/v3${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`Google Calendar API ${response.status}: ${text}`);
  }
  return text ? JSON.parse(text) : {};
}

function clampNumber(value: unknown, defaultValue: number, min: number, max: number): number {
  const numericValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numericValue)) return defaultValue;
  return Math.min(max, Math.max(min, Math.trunc(numericValue)));
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter((item): item is string => typeof item === "string")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseDateInput(value: unknown, fallback: Date): string {
  if (typeof value !== "string" || !value.trim()) {
    return fallback.toISOString();
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`Invalid date/time: ${value}`);
  }
  return parsed.toISOString();
}

function eventTime(date?: GoogleEventDate): string | undefined {
  return date?.dateTime || date?.date;
}

function compactEvent(event: GoogleCalendarEvent): JsonObject {
  const meetingLinks =
    event.conferenceData?.entryPoints
      ?.filter((entryPoint) => entryPoint.uri)
      .map((entryPoint) => ({
        type: entryPoint.entryPointType,
        uri: entryPoint.uri,
        label: entryPoint.label,
      })) || [];

  return {
    id: event.id,
    summary: event.summary || "(no title)",
    status: event.status,
    start: eventTime(event.start),
    end: eventTime(event.end),
    location: event.location,
    organizer: event.organizer?.displayName || event.organizer?.email,
    htmlLink: event.htmlLink,
    meetingLinks,
    attendees:
      event.attendees?.map((attendee) => ({
        name: attendee.displayName,
        email: attendee.email,
        responseStatus: attendee.responseStatus,
        optional: attendee.optional,
      })) || [],
  };
}

function extractAgenda(description?: string): string[] {
  if (!description) return [];
  return description
    .replace(/<[^>]+>/g, " ")
    .split(/\r?\n/)
    .map((line) => line.replace(/^[-*]\s*/, "").trim())
    .filter(Boolean)
    .slice(0, 20);
}

function buildEventDate(value: unknown, timeZone: string): GoogleEventDate {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error("Event start and end must be non-empty date/time strings");
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return { date: value };
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`Invalid event date/time: ${value}`);
  }

  return { dateTime: value, timeZone };
}

function addQueryParam(params: URLSearchParams, key: string, value: unknown): void {
  if (typeof value === "string" && value.trim()) {
    params.set(key, value);
  }
}

const server = new Server(
  { name: "calendar-meetings-pm-tools", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "calendar_list_events",
      description: "Use when: listing upcoming calendar events or meetings in a time window.",
      inputSchema: {
        type: "object",
        properties: {
          calendar_id: { type: "string", description: "Calendar ID (default from GOOGLE_CALENDAR_ID or primary)" },
          time_min: { type: "string", description: "Start of window as ISO date/time (default now)" },
          time_max: { type: "string", description: "End of window as ISO date/time (default 7 days from now)" },
          max_results: { type: "number", description: "Maximum events to return (default 20, max 100)" },
          query: { type: "string", description: "Optional full-text search query" },
          include_cancelled: { type: "boolean", description: "Include cancelled events (default false)" },
        },
      },
    },
    {
      name: "calendar_search_events",
      description: "Use when: finding calendar events by keyword over the next or previous window.",
      inputSchema: {
        type: "object",
        properties: {
          query: { type: "string", description: "Search query" },
          calendar_id: { type: "string", description: "Calendar ID (default from GOOGLE_CALENDAR_ID or primary)" },
          days_back: { type: "number", description: "Days before now to search (default 30)" },
          days_ahead: { type: "number", description: "Days after now to search (default 30)" },
          max_results: { type: "number", description: "Maximum events to return (default 20, max 100)" },
        },
        required: ["query"],
      },
    },
    {
      name: "calendar_get_event",
      description: "Use when: reading details for one calendar event.",
      inputSchema: {
        type: "object",
        properties: {
          event_id: { type: "string", description: "Google Calendar event ID" },
          calendar_id: { type: "string", description: "Calendar ID (default from GOOGLE_CALENDAR_ID or primary)" },
        },
        required: ["event_id"],
      },
    },
    {
      name: "calendar_find_free_busy",
      description: "Use when: checking free/busy windows for one or more calendars.",
      inputSchema: {
        type: "object",
        properties: {
          calendar_ids: {
            type: "array",
            items: { type: "string" },
            description: "Calendar IDs to check (default from GOOGLE_CALENDAR_ID or primary)",
          },
          time_min: { type: "string", description: "Window start as ISO date/time (required)" },
          time_max: { type: "string", description: "Window end as ISO date/time (required)" },
          time_zone: { type: "string", description: "IANA time zone (default CALENDAR_TIME_ZONE or UTC)" },
        },
        required: ["time_min", "time_max"],
      },
    },
    {
      name: "calendar_create_event",
      description: "Use when: creating a calendar event or meeting invite.",
      inputSchema: {
        type: "object",
        properties: {
          calendar_id: { type: "string", description: "Calendar ID (default from GOOGLE_CALENDAR_ID or primary)" },
          summary: { type: "string", description: "Event title" },
          start: { type: "string", description: "Start as ISO date/time or YYYY-MM-DD for all-day events" },
          end: { type: "string", description: "End as ISO date/time or YYYY-MM-DD for all-day events" },
          time_zone: { type: "string", description: "IANA time zone for dateTime values" },
          attendees: { type: "array", items: { type: "string" }, description: "Attendee email addresses" },
          description: { type: "string", description: "Event description, agenda, or notes" },
          location: { type: "string", description: "Location or meeting room" },
          add_google_meet: { type: "boolean", description: "Create a Google Meet link (default false)" },
        },
        required: ["summary", "start", "end"],
      },
    },
    {
      name: "calendar_prepare_meeting_brief",
      description: "Use when: preparing a PM-style brief for upcoming meetings.",
      inputSchema: {
        type: "object",
        properties: {
          calendar_id: { type: "string", description: "Calendar ID (default from GOOGLE_CALENDAR_ID or primary)" },
          hours_ahead: { type: "number", description: "How many hours ahead to scan (default 24, max 168)" },
          max_results: { type: "number", description: "Maximum meetings to include (default 10, max 25)" },
        },
      },
    },
    {
      name: "calendar_draft_agenda",
      description: "Use when: drafting a structured agenda from meeting context and goals.",
      inputSchema: {
        type: "object",
        properties: {
          title: { type: "string", description: "Meeting title" },
          goals: { type: "array", items: { type: "string" }, description: "Desired outcomes" },
          topics: { type: "array", items: { type: "string" }, description: "Discussion topics" },
          attendees: { type: "array", items: { type: "string" }, description: "Attendee names or roles" },
          duration_minutes: { type: "number", description: "Meeting duration in minutes (default 30)" },
        },
        required: ["title"],
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
      case "calendar_list_events": {
        const calendarId = (args?.calendar_id as string) || DEFAULT_CALENDAR_ID;
        const now = new Date();
        const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
        const timeMin = parseDateInput(args?.time_min, now);
        const timeMax = parseDateInput(args?.time_max, sevenDaysFromNow);
        const maxResults = clampNumber(args?.max_results, 20, 1, 100);

        const params = new URLSearchParams({
          singleEvents: "true",
          orderBy: "startTime",
          maxResults: String(maxResults),
          timeMin,
          timeMax,
          showDeleted: args?.include_cancelled === true ? "true" : "false",
        });
        addQueryParam(params, "q", args?.query);

        const data = await googleCalendarFetch(`/calendars/${encodeURIComponent(calendarId)}/events?${params}`);
        return out({
          calendar_id: calendarId,
          time_min: timeMin,
          time_max: timeMax,
          events: ((data.items || []) as GoogleCalendarEvent[]).map(compactEvent),
        });
      }

      case "calendar_search_events": {
        const query = (args?.query as string) || "";
        if (!query.trim()) return err("query required");
        const calendarId = (args?.calendar_id as string) || DEFAULT_CALENDAR_ID;
        const now = Date.now();
        const daysBack = clampNumber(args?.days_back, 30, 0, 365);
        const daysAhead = clampNumber(args?.days_ahead, 30, 1, 365);
        const maxResults = clampNumber(args?.max_results, 20, 1, 100);
        const timeMin = new Date(now - daysBack * 24 * 60 * 60 * 1000).toISOString();
        const timeMax = new Date(now + daysAhead * 24 * 60 * 60 * 1000).toISOString();

        const params = new URLSearchParams({
          singleEvents: "true",
          orderBy: "startTime",
          maxResults: String(maxResults),
          timeMin,
          timeMax,
          q: query,
        });

        const data = await googleCalendarFetch(`/calendars/${encodeURIComponent(calendarId)}/events?${params}`);
        return out({
          calendar_id: calendarId,
          query,
          events: ((data.items || []) as GoogleCalendarEvent[]).map(compactEvent),
        });
      }

      case "calendar_get_event": {
        const eventId = (args?.event_id as string) || "";
        if (!eventId.trim()) return err("event_id required");
        const calendarId = (args?.calendar_id as string) || DEFAULT_CALENDAR_ID;
        const data = (await googleCalendarFetch(
          `/calendars/${encodeURIComponent(calendarId)}/events/${encodeURIComponent(eventId)}`
        )) as GoogleCalendarEvent;
        return out({
          ...compactEvent(data),
          description: data.description,
          agenda_items: extractAgenda(data.description),
          creator: data.creator?.displayName || data.creator?.email,
        });
      }

      case "calendar_find_free_busy": {
        if (typeof args?.time_min !== "string" || !args.time_min.trim()) return err("time_min required");
        if (typeof args?.time_max !== "string" || !args.time_max.trim()) return err("time_max required");
        const timeMin = parseDateInput(args.time_min, new Date());
        const timeMax = parseDateInput(args.time_max, new Date(Date.now() + 60 * 60 * 1000));
        const timeZone = (args?.time_zone as string) || DEFAULT_TIME_ZONE;
        const calendarIds = asStringArray(args?.calendar_ids);
        const items = (calendarIds.length ? calendarIds : [DEFAULT_CALENDAR_ID]).map((id) => ({ id }));

        const data = await googleCalendarFetch("/freeBusy", {
          method: "POST",
          body: { timeMin, timeMax, timeZone, items },
        });

        return out({
          time_min: timeMin,
          time_max: timeMax,
          time_zone: timeZone,
          calendars: data.calendars,
          groups: data.groups,
        });
      }

      case "calendar_create_event": {
        const calendarId = (args?.calendar_id as string) || DEFAULT_CALENDAR_ID;
        const summary = (args?.summary as string) || "";
        if (!summary.trim()) return err("summary required");
        const timeZone = (args?.time_zone as string) || DEFAULT_TIME_ZONE;
        const start = buildEventDate(args?.start, timeZone);
        const end = buildEventDate(args?.end, timeZone);
        const attendees = asStringArray(args?.attendees).map((email) => ({ email }));
        const requestBody: JsonObject = {
          summary,
          start,
          end,
          attendees,
        };

        if (typeof args?.description === "string") requestBody.description = args.description;
        if (typeof args?.location === "string") requestBody.location = args.location;

        const params = new URLSearchParams({ sendUpdates: attendees.length ? "all" : "none" });
        if (args?.add_google_meet === true) {
          params.set("conferenceDataVersion", "1");
          requestBody.conferenceData = {
            createRequest: {
              requestId: `pm-meeting-${Date.now()}`,
              conferenceSolutionKey: { type: "hangoutsMeet" },
            },
          };
        }

        const data = (await googleCalendarFetch(
          `/calendars/${encodeURIComponent(calendarId)}/events?${params}`,
          { method: "POST", body: requestBody }
        )) as GoogleCalendarEvent;

        return out({ calendar_id: calendarId, event: compactEvent(data) });
      }

      case "calendar_prepare_meeting_brief": {
        const calendarId = (args?.calendar_id as string) || DEFAULT_CALENDAR_ID;
        const hoursAhead = clampNumber(args?.hours_ahead, 24, 1, 168);
        const maxResults = clampNumber(args?.max_results, 10, 1, 25);
        const now = new Date();
        const timeMax = new Date(now.getTime() + hoursAhead * 60 * 60 * 1000);
        const params = new URLSearchParams({
          singleEvents: "true",
          orderBy: "startTime",
          maxResults: String(maxResults),
          timeMin: now.toISOString(),
          timeMax: timeMax.toISOString(),
          showDeleted: "false",
        });

        const data = await googleCalendarFetch(`/calendars/${encodeURIComponent(calendarId)}/events?${params}`);
        const meetings = ((data.items || []) as GoogleCalendarEvent[]).map((event) => ({
          ...compactEvent(event),
          agenda_items: extractAgenda(event.description),
          prep_prompts: [
            "What decision or outcome is needed?",
            "Which blockers or risks should be raised?",
            "What follow-up owner and due date should be captured?",
          ],
        }));

        return out({
          calendar_id: calendarId,
          window_hours: hoursAhead,
          meetings,
        });
      }

      case "calendar_draft_agenda": {
        const title = (args?.title as string) || "";
        if (!title.trim()) return err("title required");
        const goals = asStringArray(args?.goals);
        const topics = asStringArray(args?.topics);
        const attendees = asStringArray(args?.attendees);
        const durationMinutes = clampNumber(args?.duration_minutes, 30, 15, 240);
        const discussionItems = goals.length + topics.length;
        const topicTime = Math.max(5, Math.floor((durationMinutes - 10) / Math.max(1, discussionItems)));
        const agenda = [
          { section: "Context", minutes: 5, prompt: "Why are we meeting and what changed since last time?" },
          ...goals.map((goal) => ({ section: `Outcome: ${goal}`, minutes: topicTime, prompt: "Clarify decision, owner, and next step." })),
          ...topics.map((topic) => ({ section: topic, minutes: topicTime, prompt: "Discuss options, tradeoffs, blockers, and owner." })),
          { section: "Decisions and follow-ups", minutes: 5, prompt: "Confirm owners, due dates, and communication plan." },
        ];

        return out({
          title,
          duration_minutes: durationMinutes,
          attendees,
          agenda,
          calendar_description: [
            `# ${title}`,
            "",
            "## Goals",
            ...(goals.length ? goals.map((goal) => `- ${goal}`) : ["- Align on outcome and next steps"]),
            "",
            "## Agenda",
            ...agenda.map((item) => `- ${item.section} (${item.minutes} min): ${item.prompt}`),
          ].join("\n"),
        });
      }

      default:
        return err(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return err(error instanceof Error ? error.message : String(error));
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);

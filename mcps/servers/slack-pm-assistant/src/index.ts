#!/usr/bin/env node
/**
 * Slack PM Assistant MCP Server
 * 
 * An MCP server that provides Slack integration for Product Managers.
 * 
 * Capabilities:
 * - Search messages across channels
 * - Get channel history and summaries
 * - Post messages and updates
 * - Extract action items from conversations
 * - Get thread context
 * - List and discover channels
 * 
 * Environment Variables:
 * - SLACK_BOT_TOKEN: Your Slack Bot User OAuth Token (xoxb-...)
 * - SLACK_USER_TOKEN: (Optional) User token for search (xoxp-...)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { WebClient } from "@slack/web-api";

// Configuration from environment
const SLACK_BOT_TOKEN = process.env.SLACK_BOT_TOKEN;
const SLACK_USER_TOKEN = process.env.SLACK_USER_TOKEN;

if (!SLACK_BOT_TOKEN) {
  console.error("Missing required environment variable: SLACK_BOT_TOKEN");
  process.exit(1);
}

// Initialize Slack clients
const botClient = new WebClient(SLACK_BOT_TOKEN);
const userClient = SLACK_USER_TOKEN ? new WebClient(SLACK_USER_TOKEN) : null;

// Helper to format Slack timestamp to readable date
function formatTimestamp(ts: string): string {
  const date = new Date(parseFloat(ts) * 1000);
  return date.toISOString();
}

// Helper to extract action items from text
function extractActionItems(messages: any[]): string[] {
  const actionPatterns = [
    /(?:action item|todo|task|to-do|@\w+\s+(?:please|can you|will you|could you))[:\s]+(.+)/gi,
    /(?:i will|i'll|we will|we'll|we need to|we should|let's|need to)\s+(.+)/gi,
    /(?:by (?:eod|eow|friday|monday|tomorrow|next week))[:\s]*(.+)/gi,
  ];
  
  const actionItems: string[] = [];
  
  for (const msg of messages) {
    const text = msg.text || "";
    for (const pattern of actionPatterns) {
      const matches = text.matchAll(pattern);
      for (const match of matches) {
        if (match[1]) {
          actionItems.push(match[1].trim().substring(0, 200));
        }
      }
    }
  }
  
  return [...new Set(actionItems)]; // Deduplicate
}

// Helper to get user info and cache it
const userCache = new Map<string, string>();

async function getUserName(userId: string): Promise<string> {
  if (userCache.has(userId)) {
    return userCache.get(userId)!;
  }
  
  try {
    const result = await botClient.users.info({ user: userId });
    const name = result.user?.real_name || result.user?.name || userId;
    userCache.set(userId, name);
    return name;
  } catch {
    return userId;
  }
}

// Helper to resolve user mentions in text
async function resolveUserMentions(text: string): Promise<string> {
  const userMentions = text.match(/<@(\w+)>/g) || [];
  let resolvedText = text;
  
  for (const mention of userMentions) {
    const userId = mention.slice(2, -1);
    const userName = await getUserName(userId);
    resolvedText = resolvedText.replace(mention, `@${userName}`);
  }
  
  return resolvedText;
}

// Create MCP server
const server = new Server(
  {
    name: "slack-pm-assistant",
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
      name: "search_messages",
      description: "Use when: searching messages across Slack (user token may be required for full search).",
      inputSchema: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Search query (e.g., 'roadmap discussion', 'from:@sarah sprint planning')",
          },
          count: {
            type: "number",
            description: "Number of results to return (default 20, max 100)",
          },
          sort: {
            type: "string",
            enum: ["score", "timestamp"],
            description: "Sort by relevance (score) or recency (timestamp)",
          },
        },
        required: ["query"],
      },
    },
    {
      name: "get_channel_history",
      description: "Use when: reading recent messages from a Slack channel.",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: "Channel ID or name (e.g., 'C01234567' or 'product-team')",
          },
          limit: {
            type: "number",
            description: "Number of messages to retrieve (default 50, max 200)",
          },
          oldest: {
            type: "string",
            description: "Only messages after this timestamp (Unix timestamp or ISO date)",
          },
          latest: {
            type: "string",
            description: "Only messages before this timestamp",
          },
        },
        required: ["channel"],
      },
    },
    {
      name: "get_thread",
      description: "Use when: reading all replies in a Slack thread.",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: "Channel ID where the thread is",
          },
          threadTs: {
            type: "string",
            description: "Timestamp of the parent message",
          },
        },
        required: ["channel", "threadTs"],
      },
    },
    {
      name: "list_channels",
      description: "Use when: listing Slack channels the token can see.",
      inputSchema: {
        type: "object",
        properties: {
          types: {
            type: "string",
            description: "Channel types: public_channel, private_channel (comma-separated)",
          },
          limit: {
            type: "number",
            description: "Number of channels to return (default 100)",
          },
          excludeArchived: {
            type: "boolean",
            description: "Exclude archived channels (default true)",
          },
        },
      },
    },
    {
      name: "get_channel_info",
      description: "Use when: you need metadata for a Slack channel.",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: "Channel ID",
          },
        },
        required: ["channel"],
      },
    },
    {
      name: "post_message",
      description: "Use when: posting a message to a Slack channel or thread.",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: "Channel ID or name to post to",
          },
          text: {
            type: "string",
            description: "Message text (supports Slack markdown)",
          },
          threadTs: {
            type: "string",
            description: "Thread timestamp to reply to (optional)",
          },
          unfurlLinks: {
            type: "boolean",
            description: "Enable link previews (default true)",
          },
        },
        required: ["channel", "text"],
      },
    },
    {
      name: "summarize_channel",
      description: "Use when: summarizing recent channel activity (messages, participants, topics).",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: "Channel ID",
          },
          hours: {
            type: "number",
            description: "Look back this many hours (default 24, max 168)",
          },
        },
        required: ["channel"],
      },
    },
    {
      name: "extract_action_items",
      description: "Use when: extracting action items from recent channel messages.",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: "Channel ID",
          },
          hours: {
            type: "number",
            description: "Look back this many hours (default 24)",
          },
        },
        required: ["channel"],
      },
    },
    {
      name: "get_user_messages",
      description: "Use when: filtering recent messages by a specific user in a channel.",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: "Channel ID",
          },
          userId: {
            type: "string",
            description: "User ID to filter by",
          },
          limit: {
            type: "number",
            description: "Max messages to scan (default 200)",
          },
        },
        required: ["channel", "userId"],
      },
    },
    {
      name: "find_channel_by_name",
      description: "Use when: resolving a channel name to a channel ID.",
      inputSchema: {
        type: "object",
        properties: {
          name: {
            type: "string",
            description: "Channel name to search for (partial match)",
          },
        },
        required: ["name"],
      },
    },
    {
      name: "get_standup_summary",
      description: "Use when: generating a standup-style summary from recent channel activity.",
      inputSchema: {
        type: "object",
        properties: {
          channel: {
            type: "string",
            description: "Channel ID",
          },
          hours: {
            type: "number",
            description: "Look back this many hours (default 24)",
          },
        },
        required: ["channel"],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "search_messages": {
        if (!userClient) {
          return {
            content: [{
              type: "text",
              text: "Error: Message search requires SLACK_USER_TOKEN. Bot tokens cannot search messages.",
            }],
            isError: true,
          };
        }
        
        const query = args?.query as string;
        const count = Math.min((args?.count as number) || 20, 100);
        const sort = (args?.sort as string) || "score";
        
        const result = await userClient.search.messages({
          query,
          count,
          sort,
        });
        
        const messages = (result.messages?.matches || []).map((msg: any) => ({
          channel: msg.channel?.name,
          channelId: msg.channel?.id,
          user: msg.username,
          text: msg.text?.substring(0, 500),
          timestamp: formatTimestamp(msg.ts),
          permalink: msg.permalink,
        }));
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              total: result.messages?.total || 0,
              messages,
            }, null, 2),
          }],
        };
      }

      case "get_channel_history": {
        const channel = args?.channel as string;
        const limit = Math.min((args?.limit as number) || 50, 200);
        const oldest = args?.oldest as string;
        const latest = args?.latest as string;
        
        const historyArgs: any = { channel, limit };
        if (oldest) historyArgs.oldest = oldest;
        if (latest) historyArgs.latest = latest;
        
        const result = await botClient.conversations.history(historyArgs);
        
        const messages = await Promise.all(
          (result.messages || []).map(async (msg: any) => ({
            user: await getUserName(msg.user || "unknown"),
            text: await resolveUserMentions(msg.text || ""),
            timestamp: formatTimestamp(msg.ts || "0"),
            threadReplies: msg.reply_count || 0,
            reactions: msg.reactions?.map((r: any) => `${r.name}: ${r.count}`).join(", ") || "",
          }))
        );
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              channel,
              messageCount: messages.length,
              messages,
            }, null, 2),
          }],
        };
      }

      case "get_thread": {
        const channel = args?.channel as string;
        const threadTs = args?.threadTs as string;
        
        const result = await botClient.conversations.replies({
          channel,
          ts: threadTs,
        });
        
        const messages = await Promise.all(
          (result.messages || []).map(async (msg: any) => ({
            user: await getUserName(msg.user || "unknown"),
            text: await resolveUserMentions(msg.text || ""),
            timestamp: formatTimestamp(msg.ts || "0"),
          }))
        );
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              channel,
              threadTs,
              replyCount: messages.length - 1,
              messages,
            }, null, 2),
          }],
        };
      }

      case "list_channels": {
        const types = (args?.types as string) || "public_channel";
        const limit = (args?.limit as number) || 100;
        const excludeArchived = args?.excludeArchived !== false;
        
        const result = await botClient.conversations.list({
          types,
          limit,
          exclude_archived: excludeArchived,
        });
        
        const channels = (result.channels || []).map((ch: any) => ({
          id: ch.id,
          name: ch.name,
          topic: ch.topic?.value || "",
          purpose: ch.purpose?.value || "",
          memberCount: ch.num_members,
          isPrivate: ch.is_private,
        }));
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              total: channels.length,
              channels,
            }, null, 2),
          }],
        };
      }

      case "get_channel_info": {
        const channel = args?.channel as string;
        
        const result = await botClient.conversations.info({ channel });
        const ch = result.channel as any;
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              id: ch.id,
              name: ch.name,
              topic: ch.topic?.value || "",
              purpose: ch.purpose?.value || "",
              memberCount: ch.num_members,
              isPrivate: ch.is_private,
              isArchived: ch.is_archived,
              created: new Date((ch.created || 0) * 1000).toISOString(),
            }, null, 2),
          }],
        };
      }

      case "post_message": {
        const channel = args?.channel as string;
        const text = args?.text as string;
        const threadTs = args?.threadTs as string;
        const unfurlLinks = args?.unfurlLinks !== false;
        
        const postArgs: any = {
          channel,
          text,
          unfurl_links: unfurlLinks,
        };
        if (threadTs) postArgs.thread_ts = threadTs;
        
        const result = await botClient.chat.postMessage(postArgs);
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              success: true,
              channel: result.channel,
              timestamp: result.ts,
              message: "Message posted successfully",
            }, null, 2),
          }],
        };
      }

      case "summarize_channel": {
        const channel = args?.channel as string;
        const hours = Math.min((args?.hours as number) || 24, 168);
        
        const oldest = String((Date.now() / 1000) - (hours * 3600));
        
        const result = await botClient.conversations.history({
          channel,
          limit: 200,
          oldest,
        });
        
        const messages = result.messages || [];
        
        // Gather statistics
        const userMessages = new Map<string, number>();
        const threadStarters: any[] = [];
        let totalReactions = 0;
        
        for (const msg of messages) {
          const user = msg.user || "unknown";
          userMessages.set(user, (userMessages.get(user) || 0) + 1);
          
          if (msg.reply_count && msg.reply_count > 2) {
            threadStarters.push({
              text: (msg.text || "").substring(0, 100),
              replies: msg.reply_count,
            });
          }
          
          totalReactions += msg.reactions?.reduce((sum: number, r: any) => sum + r.count, 0) || 0;
        }
        
        // Get top participants
        const topParticipants = await Promise.all(
          [...userMessages.entries()]
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(async ([userId, count]) => ({
              user: await getUserName(userId),
              messages: count,
            }))
        );
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              channel,
              timeframe: `Last ${hours} hours`,
              summary: {
                totalMessages: messages.length,
                uniqueParticipants: userMessages.size,
                totalReactions,
                activeThreads: threadStarters.length,
              },
              topParticipants,
              activeThreads: threadStarters.slice(0, 5),
            }, null, 2),
          }],
        };
      }

      case "extract_action_items": {
        const channel = args?.channel as string;
        const hours = (args?.hours as number) || 24;
        
        const oldest = String((Date.now() / 1000) - (hours * 3600));
        
        const result = await botClient.conversations.history({
          channel,
          limit: 200,
          oldest,
        });
        
        const messages = result.messages || [];
        const actionItems = extractActionItems(messages);
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              channel,
              timeframe: `Last ${hours} hours`,
              messagesAnalyzed: messages.length,
              actionItems,
            }, null, 2),
          }],
        };
      }

      case "get_user_messages": {
        const channel = args?.channel as string;
        const userId = args?.userId as string;
        const limit = (args?.limit as number) || 200;
        
        const result = await botClient.conversations.history({
          channel,
          limit,
        });
        
        const userMessages = (result.messages || [])
          .filter((msg: any) => msg.user === userId)
          .map((msg: any) => ({
            text: msg.text?.substring(0, 300),
            timestamp: formatTimestamp(msg.ts || "0"),
            threadReplies: msg.reply_count || 0,
          }));
        
        const userName = await getUserName(userId);
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              channel,
              user: userName,
              userId,
              messageCount: userMessages.length,
              messages: userMessages,
            }, null, 2),
          }],
        };
      }

      case "find_channel_by_name": {
        const searchName = (args?.name as string).toLowerCase();
        
        const result = await botClient.conversations.list({
          types: "public_channel,private_channel",
          limit: 500,
          exclude_archived: true,
        });
        
        const matches = (result.channels || [])
          .filter((ch: any) => ch.name?.toLowerCase().includes(searchName))
          .map((ch: any) => ({
            id: ch.id,
            name: ch.name,
            topic: ch.topic?.value || "",
            memberCount: ch.num_members,
          }));
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              query: searchName,
              matchCount: matches.length,
              channels: matches,
            }, null, 2),
          }],
        };
      }

      case "get_standup_summary": {
        const channel = args?.channel as string;
        const hours = (args?.hours as number) || 24;
        
        const oldest = String((Date.now() / 1000) - (hours * 3600));
        
        const result = await botClient.conversations.history({
          channel,
          limit: 200,
          oldest,
        });
        
        const messages = result.messages || [];
        
        // Group messages by user
        const userActivity = new Map<string, {
          messages: string[];
          reactions: number;
          threads: number;
        }>();
        
        for (const msg of messages) {
          const userId = msg.user || "unknown";
          if (!userActivity.has(userId)) {
            userActivity.set(userId, { messages: [], reactions: 0, threads: 0 });
          }
          
          const activity = userActivity.get(userId)!;
          activity.messages.push((msg.text || "").substring(0, 150));
          activity.reactions += msg.reactions?.reduce((sum: number, r: any) => sum + r.count, 0) || 0;
          activity.threads += msg.reply_count || 0;
        }
        
        // Format standup summary
        const standupEntries = await Promise.all(
          [...userActivity.entries()].map(async ([userId, activity]) => ({
            user: await getUserName(userId),
            messageCount: activity.messages.length,
            engagementScore: activity.reactions + activity.threads,
            recentMessages: activity.messages.slice(0, 3),
          }))
        );
        
        // Sort by engagement
        standupEntries.sort((a, b) => b.engagementScore - a.engagementScore);
        
        // Extract action items
        const actionItems = extractActionItems(messages);
        
        return {
          content: [{
            type: "text",
            text: JSON.stringify({
              channel,
              timeframe: `Last ${hours} hours`,
              overview: {
                totalMessages: messages.length,
                activeMembers: userActivity.size,
              },
              memberActivity: standupEntries.slice(0, 10),
              actionItems: actionItems.slice(0, 10),
            }, null, 2),
          }],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error: any) {
    return {
      content: [{
        type: "text",
        text: `Error: ${error.message || String(error)}`,
      }],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Slack PM Assistant MCP server running");
}

main().catch(console.error);

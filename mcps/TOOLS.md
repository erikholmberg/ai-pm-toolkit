# MCP tool reference

Quick lookup: **server** → **tool name** → **when to use it**. Setup and env vars: each server’s `README.md` and [mcps/README.md](./README.md).

---

## jira-pm-assistant

| Tool | Use when |
|------|----------|
| `search_issues` | Searching or reporting on Jira work with JQL |
| `get_issue` | Reading one issue by key |
| `create_issue` | Creating a new Jira issue |
| `get_sprint` | You need current sprint info for a board |
| `get_sprint_issues` | Listing issues in a sprint |
| `generate_release_notes` | Drafting release notes from completed Jira work |

---

## confluence-docs

| Tool | Use when |
|------|----------|
| `search_pages` | Finding wiki pages by text |
| `get_page` | Reading a page’s body |
| `create_page` | Publishing a new page |
| `list_spaces` | Discovering spaces |
| `create_meeting_notes` | Creating meeting notes from a template |

---

## github-pm-tools

| Tool | Use when |
|------|----------|
| `list_issues` | Browsing or filtering repo issues |
| `get_issue` | Reading one issue |
| `create_issue` | Filing a new GitHub issue |
| `list_pull_requests` | Reviewing open/merged PRs |
| `generate_release_notes` | Changelog from merged PRs between tags |
| `get_repo_stats` | Repo health and activity |

---

## slack-pm-assistant

| Tool | Use when |
|------|----------|
| `search_messages` | Finding messages across channels (user token may be required) |
| `get_channel_history` | Reading recent messages in a channel |
| `get_thread` | Following a thread |
| `list_channels` | Discovering channels |
| `get_channel_info` | Channel metadata |
| `post_message` | Sending a message |
| `summarize_channel` | High-level recent activity summary |
| `extract_action_items` | Pulling tasks from discussion |
| `get_user_messages` | Messages from one user in a channel |
| `find_channel_by_name` | Resolving name → channel |
| `get_standup_summary` | Standup-style summary from activity |

---

## notion-pm-tools

| Tool | Use when |
|------|----------|
| `notion_search_pages` | Finding pages by title |
| `notion_list_databases` | Listing databases the integration can see |
| `notion_get_page` | Reading page content |
| `notion_create_page` | Creating a child page under a parent |
| `notion_create_page_in_database` | Adding a row/page to a database |
| `notion_create_meeting_notes` | Structured meeting notes page |
| `notion_query_database` | Filtering/sorting database rows |

---

## braintrust-pm-tools

| Tool | Use when |
|------|----------|
| `list_projects` | Listing Braintrust projects |
| `get_project` | Project details |
| `list_experiments` | Experiments in a project |
| `get_experiment` | Full experiment + results |
| `get_experiment_summary` | Summary stats for an experiment |
| `list_datasets` | Datasets in org/project |
| `get_dataset` | Dataset details |
| `query_logs` | Logs/traces in a time window |
| `compare_experiments` | Comparing metrics across experiments |

---

## langsmith-pm-tools

| Tool | Use when |
|------|----------|
| `list_projects` | Listing LangSmith projects |
| `get_project` | Project details |
| `list_runs` | Listing runs/traces |
| `get_run` | One run’s details |
| `get_trace` | Full trace with child runs |
| `get_project_stats` | Volume, errors, latency |
| `list_datasets` | Datasets |
| `get_dataset` | Dataset details |
| `query_traces` | Advanced trace filtering |
| `get_eval_results` | Eval results for project/dataset |

---

## product-analytics-pm-tools

Read-only analytics over bundled sample data (see server README). **Use when** exploring trends, funnels, retention, or segments in that dataset.

| Tool | Use when |
|------|----------|
| `event_trend` | Event volume and uniques over time |
| `funnel_conversion` | Step-through conversion |
| `retention_by_cohort` | Cohort retention curves |
| `cohort_compare` | Two-segment comparison for one event |
| `segment_compare` | Multi-segment volume comparison |

---

## calendar-meetings-pm-tools

| Tool | Use when |
|------|----------|
| `calendar_list_events` | Listing upcoming meetings or events in a time window |
| `calendar_search_events` | Finding meetings by keyword across a past/future window |
| `calendar_get_event` | Reading details, attendees, links, and agenda-style description lines for one event |
| `calendar_find_free_busy` | Checking free/busy blocks before scheduling |
| `calendar_create_event` | Creating a calendar event or meeting invite |
| `calendar_prepare_meeting_brief` | Preparing a PM-style brief for upcoming meetings |
| `calendar_draft_agenda` | Drafting a structured agenda and calendar description |

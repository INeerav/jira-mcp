# Jira MCP Server

An MCP (Model Context Protocol) server that connects Claude Code to Jira Cloud, providing reporting tools for issues, sprints, worklogs, and project summaries.

Built for Jira Cloud with Atlassian OAuth 2.0 (3LO) authentication — works with SAML/SSO environments where API tokens are disabled.

## Features

- **OAuth 2.0 authentication** with automatic token refresh
- **Corporate proxy support** via OS-level certificate trust store
- **12 reporting tools** exposed as MCP tools for Claude Code

## Available Tools

### Projects
| Tool | Description |
|---|---|
| `list_projects` | List all visible Jira projects |
| `get_project_summary` | Dashboard: open issues by type/priority + recent activity |

### Issues
| Tool | Description |
|---|---|
| `search_issues` | Query issues with JQL (Jira Query Language) |
| `get_issue` | Full details for a single issue |

### Sprints (via Agile API)
| Tool | Description |
|---|---|
| `list_boards` | List agile boards (scrum/kanban) |
| `list_sprints` | List sprints for a board |
| `get_sprint_report` | Detailed sprint report (completed/incomplete) |
| `get_velocity_report` | Velocity data across recent sprints |

### Sprints (via JQL - no Agile scope needed)
| Tool | Description |
|---|---|
| `get_active_sprint_issues` | Issues in the current active sprint |
| `get_sprint_issues_by_name` | Issues in a sprint by name, grouped by status |

### Worklogs
| Tool | Description |
|---|---|
| `get_issue_worklogs` | Time entries for a specific issue |
| `get_user_worklogs` | User's worklogs over a time window |

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Configure OAuth

Create a `.env` file (see `.env.example`):

```
ATLASSIAN_CLIENT_ID=your-client-id
ATLASSIAN_CLIENT_SECRET=your-client-secret
ATLASSIAN_REDIRECT_URI=http://localhost:9191/callback
```

See [docs/setup-guide.md](docs/setup-guide.md) for how to create an Atlassian OAuth app.

### 3. Authenticate

```bash
jira-mcp-login
```

Opens your browser for Atlassian OAuth consent. Tokens are saved locally to `.tokens.json`.

### 4. Add to Claude Code

Create or edit `~/.claude/.mcp.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "/path/to/python",
      "args": ["-m", "jira_mcp.server"],
      "cwd": "/path/to/jiramcp",
      "env": {
        "ATLASSIAN_CLIENT_ID": "your-client-id",
        "ATLASSIAN_CLIENT_SECRET": "your-client-secret",
        "ATLASSIAN_REDIRECT_URI": "http://localhost:9191/callback"
      }
    }
  }
}
```

Restart Claude Code. Then ask:

```
> List my Jira projects
> Show open bugs in MOB
> What's in the active sprint for PDW?
```

## Project Structure

```
jiramcp/
├── README.md
├── pyproject.toml              # Package config & dependencies
├── .env.example                # OAuth config template
├── .gitignore                  # Protects .env and .tokens.json
├── docs/
│   └── setup-guide.md          # Detailed step-by-step setup instructions
└── src/
    └── jira_mcp/
        ├── __init__.py
        ├── auth.py             # OAuth 2.0 flow, token storage & refresh
        ├── client.py           # Jira Cloud REST API client (v3 + Agile)
        └── server.py           # MCP server with 12 reporting tools
```

## Architecture

```
Claude Code  <──MCP──>  server.py  ──>  client.py  ──>  Jira Cloud REST API
                            │                               (api.atlassian.com)
                            │
                        auth.py
                        ├── OAuth 2.0 login flow (browser + localhost callback)
                        ├── Token storage (.tokens.json)
                        └── Auto-refresh on expiry
```

## Authentication Flow

1. User runs `jira-mcp-login`
2. Browser opens to Atlassian consent page (SSO/SAML if configured)
3. User grants access, Atlassian redirects to `localhost:9191/callback`
4. Auth code is exchanged for access + refresh tokens
5. Tokens are stored in `.tokens.json`
6. On each API call, tokens are validated and auto-refreshed if expired

## API Endpoints Used

| Endpoint | Purpose |
|---|---|
| `GET /rest/api/3/project` | List projects |
| `GET /rest/api/3/search/jql` | JQL issue search |
| `GET /rest/api/3/issue/{key}` | Issue details |
| `GET /rest/api/3/issue/{key}/worklog` | Issue worklogs |
| `GET /rest/agile/1.0/board` | List boards |
| `GET /rest/agile/1.0/board/{id}/sprint` | List sprints |
| `GET /rest/agile/1.0/sprint/{id}` | Sprint details |
| `GET /rest/agile/1.0/sprint/{id}/issue` | Sprint issues |

## Dependencies

- `mcp[cli]` — Model Context Protocol SDK
- `requests` — HTTP client for Jira REST API
- `python-dotenv` — Environment variable loading
- `truststore` — OS-level SSL certificate trust (handles corporate proxies)

## License

Internal use.

# Jira MCP Server - Setup Guide

Step-by-step instructions for setting up the Jira MCP server with Atlassian OAuth 2.0 authentication.

## Prerequisites

- Python 3.10+
- Access to a Jira Cloud instance (e.g. `n8000590795.atlassian.net`)
- An Atlassian account with permissions to create OAuth apps (or an admin who can)
- Claude Code CLI installed

## Step 1: Create an Atlassian OAuth 2.0 App

1. Go to [Atlassian Developer Console](https://developer.atlassian.com/console/myapps/)
2. Click **Create** > **OAuth 2.0 integration**
3. Name it (e.g. `jira-mcp`) and click **Create**
4. Under **Permissions**, click **Add** next to **Jira API** and configure these scopes:
   - `read:jira-work`
   - `read:jira-user`
   - `write:jira-work`
   - `manage:jira-project`
   - `manage:jira-configuration`
   - `manage:jira-webhook`
   - `manage:jira-data-provider`
5. *(Optional)* To enable board/sprint Agile APIs, also add **Jira Software** permissions:
   - `read:sprint:jira-software`
   - `read:board-scope:jira-software`
6. Under **Authorization**, set the callback URL to:
   ```
   http://localhost:9191/callback
   ```
7. Under **Settings**, copy:
   - **Client ID**
   - **Client Secret** (click "Generate" if needed)

## Step 2: Clone and Install

```bash
git clone <repo-url> jiramcp
cd jiramcp
pip install -e .
```

This installs two CLI commands:
- `jira-mcp` — runs the MCP server
- `jira-mcp-login` — runs the OAuth login flow

## Step 3: Configure Environment Variables

Copy the example and fill in your OAuth credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
ATLASSIAN_CLIENT_ID=your-client-id
ATLASSIAN_CLIENT_SECRET=your-client-secret
ATLASSIAN_REDIRECT_URI=http://localhost:9191/callback
```

## Step 4: Authenticate with Jira

Run the login command:

```bash
jira-mcp-login
```

This will:
1. Start a temporary HTTP server on `localhost:9191`
2. Open your browser to Atlassian's consent page
3. You sign in via SSO/SAML (if configured) and grant access
4. Atlassian redirects back to `localhost:9191/callback` with an auth code
5. The code is exchanged for access and refresh tokens
6. Tokens are saved to `.tokens.json` in the project root

You should see:

```
Opening browser for Atlassian authorization...
Waiting for callback on localhost:9191...
Exchanging code for tokens...
Authenticated successfully! Cloud ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Tokens saved to /path/to/jiramcp/.tokens.json
```

### Token Refresh

Tokens auto-refresh when they expire. If refresh fails, re-run `jira-mcp-login`.

### Corporate SSL/Proxy

The server uses `truststore` to leverage your OS certificate store. This handles corporate proxies that intercept HTTPS with custom certificates — no extra SSL config needed.

## Step 5: Test the Connection

Quick test to verify everything works:

```bash
python -c "
from jira_mcp.client import JiraClient
client = JiraClient()
projects = client.list_projects()
print(f'Connected! Found {len(projects)} projects.')
for p in projects[:5]:
    print(f'  {p[\"key\"]:15s} {p[\"name\"]}')
"
```

## Step 6: Configure Claude Code

Add the MCP server to your global Claude Code config:

**File: `~/.claude/.mcp.json`**

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

Find your Python path with `which python`.

Restart Claude Code to load the MCP server.

## Step 7: Verify in Claude Code

After restarting Claude Code, you can ask:

- "List my Jira projects"
- "Show open bugs in project MYPROJ"
- "What's in the active sprint for PDW?"
- "Get sprint report for Platform Enablement Q1S4"

## Troubleshooting

### "Not authenticated" error
Run `jira-mcp-login` to re-authenticate.

### SSL certificate errors
The `truststore` package should handle corporate proxies automatically. If issues persist, ensure your OS trust store has the proxy CA certificate installed.

### "scope does not match" on Agile API
The board/sprint Agile APIs require Jira Software scopes. Either:
- Add Jira Software permissions to your OAuth app (Step 1.5)
- Use the JQL-based tools (`get_active_sprint_issues`, `get_sprint_issues_by_name`) which work without Agile scopes

### Token expired and refresh fails
Re-run `jira-mcp-login`. This happens if the refresh token itself expires (typically after 90 days of inactivity).

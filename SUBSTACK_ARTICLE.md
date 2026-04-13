# How to Set Up Jira MCP: A Simple Guide

If you're tired of switching between Claude and Jira to manage your projects, there's a better way. Jira MCP lets you interact with your Jira instance directly from Claude Code.

## What is Jira MCP?

Jira MCP is a Model Context Protocol server that connects Claude to your Jira Cloud instance. Once set up, you can ask Claude things like:

- "List all open bugs in the SCRUM project"
- "What's in the active sprint?"
- "Show me the sprint report for Q1"

No more tab-switching. Just ask Claude.

## Prerequisites

You'll need:
- Python 3.10 or newer
- A Jira Cloud instance (n8000590795.atlassian.net, for example)
- An Atlassian account with permission to create OAuth apps
- Claude Code CLI installed

## Step 1: Create an OAuth App

1. Go to https://developer.atlassian.com/console/myapps/
2. Click **Create** > **OAuth 2.0 integration**
3. Name it "jira-mcp" and create it
4. Under **Permissions**, add **Jira API** with these scopes:
   - read:jira-work
   - read:jira-user
   - write:jira-work
   - manage:jira-project
   - manage:jira-configuration
   - manage:jira-webhook
   - manage:jira-data-provider

5. (Optional) For board/sprint views, also add **Jira Software**:
   - read:sprint:jira-software
   - read:board-scope:jira-software

6. Under **Authorization**, set callback URL to:
   ```
   http://localhost:9191/callback
   ```

7. Copy your **Client ID** and **Client Secret**

## Step 2: Clone and Install

```bash
git clone https://github.com/INeerav/jira-mcp.git jira-mcp
cd jira-mcp
pip install -e .
```

This installs two commands:
- `jira-mcp` - runs the server
- `jira-mcp-login` - handles OAuth login

## Step 3: Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add:
```
ATLASSIAN_CLIENT_ID=your-client-id
ATLASSIAN_CLIENT_SECRET=your-client-secret
ATLASSIAN_REDIRECT_URI=http://localhost:9191/callback
```

## Step 4: Authenticate

```bash
jira-mcp-login
```

This will:
1. Open your browser to Atlassian's login page
2. You sign in and grant access
3. Tokens are saved to `.tokens.json`

You should see:
```
Authenticated successfully! Cloud ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Tokens saved to /path/to/jira-mcp/.tokens.json
```

Tokens auto-refresh, so you won't need to re-authenticate often.

## Step 5: Verify the Connection

Test it quickly:

```bash
python -c "
from jira_mcp.client import JiraClient
client = JiraClient()
projects = client.list_projects()
print(f'Connected! Found {len(projects)} projects.')
"
```

## Step 6: Add to Claude Code

Update your Claude Code config at `~/.claude/.mcp.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "/path/to/python",
      "args": ["-m", "jira_mcp.server"],
      "cwd": "/path/to/jira-mcp",
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

Restart Claude Code and you're done.

## Step 7: Start Using It

In Claude Code, just ask:
- "List my Jira projects"
- "Show open bugs in project SCRUM"
- "What's in the active sprint?"
- "Get sprint report for PDW"

Claude will query your Jira instance and show you the results.

## Troubleshooting

**"Not authenticated" error?**
Run `jira-mcp-login` again.

**SSL certificate errors?**
Jira MCP uses the `truststore` package to handle corporate proxies automatically.

**"scope does not match" for board/sprint APIs?**
Make sure you added Jira Software permissions in Step 1. If you skipped it, add them now and re-authenticate.

**Token expired and refresh fails?**
Re-run `jira-mcp-login`. Refresh tokens expire after 90 days of inactivity.

## That's It

Jira MCP is designed to be simple. OAuth handles authentication securely, tokens auto-refresh, and the setup is straightforward. Once it's running, Claude has direct access to your Jira data without you leaving the editor.

No more context-switching. No more lost hours in browser tabs.

Happy shipping.

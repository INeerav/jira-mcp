# OAuth App Setup Reference Guide

## Quick Summary
You need to create one OAuth 2.0 app in Atlassian. This takes 5 minutes and gives you the credentials needed to run Jira MCP.

---

## Step-by-Step: Create Your OAuth App

### 1. Go to the Atlassian Developer Console
Visit: https://developer.atlassian.com/console/myapps/

You'll see your existing apps (if any) and a **Create** button.

### 2. Click Create > OAuth 2.0 Integration
- Click the **Create** button (top right)
- Select **OAuth 2.0 integration**
- Give it a name: `jira-mcp` (or whatever you prefer)
- Click **Create**

### 3. Add Jira API Permissions
Once created, you'll see the app details page.

Go to the **Permissions** tab:
- Click **Add** next to "Jira API"
- Select these scopes (required):
  - `read:jira-work` - Read issues and projects
  - `read:jira-user` - Read user info
  - `write:jira-work` - Create/update issues
  - `manage:jira-project` - Manage project settings
  - `manage:jira-configuration` - Manage Jira config
  - `manage:jira-webhook` - Manage webhooks
  - `manage:jira-data-provider` - Data provider access

**Optional: For board/sprint views**
- Also add **Jira Software** permissions:
  - `read:sprint:jira-software`
  - `read:board-scope:jira-software`

### 4. Set the Callback URL
Go to the **Authorization** tab:
- Set **Redirect URL(s)** to:
  ```
  http://localhost:9191/callback
  ```
- This is where Jira will redirect after you grant access

### 5. Copy Your Credentials
Go to the **Settings** tab:
- Copy **Client ID** - you'll need this
- Click "Generate" next to **Client Secret**
- Copy **Client Secret** - keep this safe

You now have everything you need!

---

## Checklist

- [ ] OAuth app created in Atlassian
- [ ] Jira API scopes added (7 required scopes)
- [ ] Jira Software scopes added (optional)
- [ ] Redirect URL set to `http://localhost:9191/callback`
- [ ] Client ID copied
- [ ] Client Secret copied and saved

---

## Your Credentials (Keep Safe)

When you've completed the setup, you'll have:

```
ATLASSIAN_CLIENT_ID=<your-client-id>
ATLASSIAN_CLIENT_SECRET=<your-client-secret>
ATLASSIAN_REDIRECT_URI=http://localhost:9191/callback
```

These go into your `.env` file. Never commit these to Git!

---

## Troubleshooting

**"App creation failed"**
Make sure you're logged into Atlassian with an admin account that has permission to create apps.

**"Can't find Jira API in permissions"**
Make sure you selected "OAuth 2.0 integration" (not API token).

**"Client Secret button doesn't appear"**
Refresh the page. It should appear under Settings.

**Redirect URL rejection**
Make sure it's exactly: `http://localhost:9191/callback` (no trailing slash, http not https)

---

## Next Steps

After creating the app:
1. Clone Jira MCP: `git clone https://github.com/INeerav/jira-mcp.git`
2. Create `.env` file with your Client ID and Secret
3. Run: `jira-mcp-login`
4. Authenticate and start using Jira MCP in Claude Code

That's it!

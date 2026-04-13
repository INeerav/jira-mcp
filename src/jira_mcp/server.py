"""Jira MCP Server — exposes Jira Server/Data Center reporting as MCP tools."""

import json
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from jira_mcp.client import JiraClient

load_dotenv()

mcp = FastMCP("jira-reports", instructions="Jira Cloud reporting tools. Use these to query issues, sprint data, and worklogs.")


def _client() -> JiraClient:
    return JiraClient()


def _fmt(obj: dict | list) -> str:
    """Pretty-format a JSON-serialisable object for MCP text output."""
    return json.dumps(obj, indent=2, default=str)


# ── Projects ──────────────────────────────────────────────────────────────────


@mcp.tool()
def list_projects() -> str:
    """List all Jira projects visible to the authenticated user.

    Returns project key, name, and lead for each project.
    """
    projects = _client().list_projects()
    result = [
        {"key": p["key"], "name": p["name"], "lead": p.get("lead", {}).get("displayName", "N/A")}
        for p in projects
    ]
    return _fmt(result)


# ── Issue Search (JQL) ────────────────────────────────────────────────────────


@mcp.tool()
def search_issues(jql: str, max_results: int = 50) -> str:
    """Search Jira issues using JQL (Jira Query Language).

    Args:
        jql: JQL query string. Examples:
            - "project = MYPROJ AND status = Open"
            - "assignee = currentUser() AND sprint in openSprints()"
            - "type = Bug AND priority = Critical AND created >= -7d"
        max_results: Maximum number of results to return (default 50, max 200).

    Returns a summary of matching issues with key, summary, status, assignee, and type.
    """
    data = _client().search_issues(jql, max_results=min(max_results, 200))
    issues = []
    for i in data.get("issues", []):
        f = i["fields"]
        issues.append({
            "key": i["key"],
            "summary": f.get("summary"),
            "status": f.get("status", {}).get("name"),
            "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
            "type": f.get("issuetype", {}).get("name"),
            "priority": (f.get("priority") or {}).get("name", "None"),
            "created": f.get("created"),
            "updated": f.get("updated"),
        })
    return _fmt({"total": data.get("total", 0), "returned": len(issues), "issues": issues})


@mcp.tool()
def get_issue(issue_key: str) -> str:
    """Get detailed information about a specific Jira issue.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".

    Returns full issue details including description, comments count, time tracking, and links.
    """
    i = _client().get_issue(issue_key)
    f = i["fields"]
    tt = f.get("timetracking", {})
    return _fmt({
        "key": i["key"],
        "summary": f.get("summary"),
        "description": f.get("description"),
        "status": f.get("status", {}).get("name"),
        "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
        "reporter": (f.get("reporter") or {}).get("displayName", "Unknown"),
        "type": f.get("issuetype", {}).get("name"),
        "priority": (f.get("priority") or {}).get("name", "None"),
        "labels": f.get("labels", []),
        "components": [c["name"] for c in f.get("components", [])],
        "created": f.get("created"),
        "updated": f.get("updated"),
        "resolution": (f.get("resolution") or {}).get("name"),
        "time_tracking": {
            "original_estimate": tt.get("originalEstimate"),
            "remaining_estimate": tt.get("remainingEstimate"),
            "time_spent": tt.get("timeSpent"),
        },
        "comments_count": f.get("comment", {}).get("total", 0),
        "subtasks": [{"key": s["key"], "summary": s["fields"]["summary"], "status": s["fields"]["status"]["name"]} for s in f.get("subtasks", [])],
        "links": [
            {
                "type": lnk["type"]["name"],
                "direction": "outward" if "outwardIssue" in lnk else "inward",
                "issue": (lnk.get("outwardIssue") or lnk.get("inwardIssue", {})).get("key"),
            }
            for lnk in f.get("issuelinks", [])
        ],
    })


# ── Boards ────────────────────────────────────────────────────────────────────


@mcp.tool()
def list_boards(project_key: str | None = None) -> str:
    """List Jira agile boards.

    Args:
        project_key: Optional project key to filter boards (e.g. "MYPROJ").

    Returns board id, name, and type (scrum/kanban).
    """
    data = _client().list_boards(project_key=project_key)
    boards = [
        {"id": b["id"], "name": b["name"], "type": b.get("type", "unknown")}
        for b in data.get("values", [])
    ]
    return _fmt(boards)


# ── Sprints ───────────────────────────────────────────────────────────────────


@mcp.tool()
def list_sprints(board_id: int, state: str | None = None) -> str:
    """List sprints for a given board.

    Args:
        board_id: The board ID (get this from list_boards).
        state: Optional filter — "active", "closed", or "future".

    Returns sprint id, name, state, and start/end dates.
    """
    data = _client().list_sprints(board_id, state=state)
    sprints = [
        {
            "id": s["id"],
            "name": s["name"],
            "state": s["state"],
            "start_date": s.get("startDate"),
            "end_date": s.get("endDate"),
            "complete_date": s.get("completeDate"),
        }
        for s in data.get("values", [])
    ]
    return _fmt(sprints)


@mcp.tool()
def get_sprint_report(board_id: int, sprint_id: int) -> str:
    """Get a detailed sprint report showing completed, incomplete, and removed issues.

    Args:
        board_id: The board ID.
        sprint_id: The sprint ID (get this from list_sprints).

    Returns sprint metadata plus categorized issue lists.
    """
    client = _client()
    data = client.get_sprint_report(board_id, sprint_id)
    sprint = data.get("sprint", {})
    issues_data = data.get("issues", {})

    completed = []
    not_completed = []
    for i in issues_data.get("issues", []):
        f = i["fields"]
        entry = {
            "key": i["key"],
            "summary": f.get("summary"),
            "type": f.get("issuetype", {}).get("name"),
            "status": f.get("status", {}).get("name"),
            "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
        }
        status_cat = f.get("status", {}).get("statusCategory", {}).get("key")
        if status_cat == "done":
            completed.append(entry)
        else:
            not_completed.append(entry)

    return _fmt({
        "sprint": {
            "id": sprint.get("id"),
            "name": sprint.get("name"),
            "state": sprint.get("state"),
            "start_date": sprint.get("startDate"),
            "end_date": sprint.get("endDate"),
            "complete_date": sprint.get("completeDate"),
        },
        "completed_issues": completed,
        "not_completed_issues": not_completed,
        "summary": {
            "total": len(completed) + len(not_completed),
            "completed": len(completed),
            "not_completed": len(not_completed),
        },
    })


@mcp.tool()
def get_velocity_report(board_id: int) -> str:
    """Get velocity data for a scrum board — shows issue counts per recent closed sprint.

    Args:
        board_id: The board ID.

    Returns per-sprint issue counts for recent closed sprints.
    """
    client = _client()
    data = client.get_velocity_chart(board_id)
    entries = []
    for sprint in data.get("sprints", []):
        sprint_id = sprint["id"]
        issues = client.get_sprint_issues(sprint_id)
        total = issues.get("total", 0)
        done = sum(
            1 for i in issues.get("issues", [])
            if i["fields"].get("status", {}).get("statusCategory", {}).get("key") == "done"
        )
        entries.append({
            "sprint_id": sprint_id,
            "sprint_name": sprint.get("name"),
            "total_issues": total,
            "completed_issues": done,
            "completion_rate": f"{round(done / total * 100)}%" if total else "N/A",
        })
    return _fmt(entries)


# ── Sprint queries via JQL (works without Agile API scope) ───────────────────


@mcp.tool()
def get_active_sprint_issues(project_key: str) -> str:
    """Get all issues in the current active sprint for a project.

    This uses JQL and works without Jira Software API scope.

    Args:
        project_key: The project key, e.g. "MYPROJ".

    Returns issues in the active sprint with status, assignee, and type.
    """
    data = _client().search_active_sprint_issues(project_key)
    issues = []
    for i in data.get("issues", []):
        f = i["fields"]
        issues.append({
            "key": i["key"],
            "summary": f.get("summary"),
            "status": f.get("status", {}).get("name"),
            "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
            "type": f.get("issuetype", {}).get("name"),
        })
    return _fmt({"project": project_key, "sprint": "active", "total": len(issues), "issues": issues})


@mcp.tool()
def get_sprint_issues_by_name(sprint_name: str, project_key: str | None = None) -> str:
    """Get all issues in a sprint by sprint name.

    This uses JQL and works without Jira Software API scope.

    Args:
        sprint_name: The exact sprint name, e.g. "Sprint 42".
        project_key: Optional project key to scope the search.

    Returns issues in the sprint grouped by status.
    """
    data = _client().search_sprint_issues_jql(sprint_name, project_key=project_key)
    done = []
    in_progress = []
    todo = []
    for i in data.get("issues", []):
        f = i["fields"]
        entry = {
            "key": i["key"],
            "summary": f.get("summary"),
            "status": f.get("status", {}).get("name"),
            "assignee": (f.get("assignee") or {}).get("displayName", "Unassigned"),
            "type": f.get("issuetype", {}).get("name"),
        }
        cat = f.get("status", {}).get("statusCategory", {}).get("key", "")
        if cat == "done":
            done.append(entry)
        elif cat == "indeterminate":
            in_progress.append(entry)
        else:
            todo.append(entry)
    return _fmt({
        "sprint_name": sprint_name,
        "done": done,
        "in_progress": in_progress,
        "todo": todo,
        "summary": {"done": len(done), "in_progress": len(in_progress), "todo": len(todo), "total": len(done) + len(in_progress) + len(todo)},
    })


# ── Worklogs ──────────────────────────────────────────────────────────────────


@mcp.tool()
def get_issue_worklogs(issue_key: str) -> str:
    """Get all worklogs (time entries) for a specific issue.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".

    Returns list of worklogs with author, time spent, date, and comment.
    """
    data = _client().get_issue_worklogs(issue_key)
    worklogs = [
        {
            "author": w.get("author", {}).get("displayName", "Unknown"),
            "time_spent": w.get("timeSpent"),
            "time_spent_seconds": w.get("timeSpentSeconds"),
            "started": w.get("started"),
            "comment": w.get("comment"),
            "created": w.get("created"),
        }
        for w in data.get("worklogs", [])
    ]
    total_seconds = sum(w.get("time_spent_seconds", 0) or 0 for w in worklogs)
    hours = total_seconds / 3600
    return _fmt({
        "issue_key": issue_key,
        "total_worklogs": len(worklogs),
        "total_time_spent_hours": round(hours, 2),
        "worklogs": worklogs,
    })


@mcp.tool()
def get_user_worklogs(username: str, days: int = 7, project_key: str | None = None) -> str:
    """Get worklogs for a specific user within a recent time window.

    This searches for issues the user has logged work on and retrieves their worklogs.

    Args:
        username: Jira username to search for.
        days: Number of past days to look back (default 7).
        project_key: Optional project key to scope the search.

    Returns worklogs grouped by issue with totals.
    """
    client = _client()
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    jql = f'worklogAuthor = "{username}" AND worklogDate >= "{since_date}"'
    if project_key:
        jql += f' AND project = "{project_key}"'

    data = client.search_issues(jql, fields="summary,worklog", max_results=200)
    result = []
    total_seconds = 0

    for issue in data.get("issues", []):
        issue_key = issue["key"]
        summary = issue["fields"].get("summary")
        worklogs = issue["fields"].get("worklog", {}).get("worklogs", [])

        user_worklogs = []
        for w in worklogs:
            author_name = w.get("author", {}).get("name", "")
            author_key = w.get("author", {}).get("key", "")
            if author_name == username or author_key == username:
                started = w.get("started", "")
                if started[:10] >= since_date:
                    secs = w.get("timeSpentSeconds", 0) or 0
                    total_seconds += secs
                    user_worklogs.append({
                        "time_spent": w.get("timeSpent"),
                        "time_spent_seconds": secs,
                        "started": started,
                        "comment": w.get("comment"),
                    })

        if user_worklogs:
            issue_seconds = sum(wl["time_spent_seconds"] for wl in user_worklogs)
            result.append({
                "issue_key": issue_key,
                "summary": summary,
                "worklogs": user_worklogs,
                "issue_total_hours": round(issue_seconds / 3600, 2),
            })

    return _fmt({
        "username": username,
        "period": f"last {days} days (since {since_date})",
        "total_hours": round(total_seconds / 3600, 2),
        "issues": result,
    })


# ── Summary / Dashboard ──────────────────────────────────────────────────────


@mcp.tool()
def get_project_summary(project_key: str) -> str:
    """Get a high-level summary of a Jira project including open issue counts by type and priority.

    Args:
        project_key: The project key, e.g. "MYPROJ".

    Returns issue counts broken down by type and priority, plus recent activity.
    """
    client = _client()

    type_data = client.search_issues(
        f'project = "{project_key}" AND resolution = Unresolved',
        fields="issuetype",
        max_results=0,
    )
    total_open = type_data.get("total", 0)

    by_type_jql = f'project = "{project_key}" AND resolution = Unresolved ORDER BY issuetype'
    by_type = client.search_issues(by_type_jql, fields="issuetype", max_results=200)
    type_counts: dict[str, int] = {}
    for i in by_type.get("issues", []):
        t = i["fields"].get("issuetype", {}).get("name", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    by_priority_jql = f'project = "{project_key}" AND resolution = Unresolved ORDER BY priority'
    by_priority = client.search_issues(by_priority_jql, fields="priority", max_results=200)
    priority_counts: dict[str, int] = {}
    for i in by_priority.get("issues", []):
        p = (i["fields"].get("priority") or {}).get("name", "None")
        priority_counts[p] = priority_counts.get(p, 0) + 1

    recent = client.search_issues(
        f'project = "{project_key}" AND updated >= -7d ORDER BY updated DESC',
        fields="summary,status,updated",
        max_results=10,
    )
    recent_issues = [
        {"key": i["key"], "summary": i["fields"].get("summary"), "status": i["fields"].get("status", {}).get("name"), "updated": i["fields"].get("updated")}
        for i in recent.get("issues", [])
    ]

    return _fmt({
        "project_key": project_key,
        "total_open_issues": total_open,
        "by_type": type_counts,
        "by_priority": priority_counts,
        "recently_updated": recent_issues,
    })


def main():
    mcp.run()


if __name__ == "__main__":
    main()

"""Jira Cloud REST API client using Atlassian OAuth 2.0."""

import requests

from jira_mcp.auth import get_valid_token

ATLASSIAN_API_BASE = "https://api.atlassian.com"


class JiraClient:
    """Client for Jira Cloud REST API via OAuth 2.0."""

    def __init__(self):
        access_token, cloud_id = get_valid_token()
        self.base_url = f"{ATLASSIAN_API_BASE}/ex/jira/{cloud_id}"
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {access_token}"
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["Accept"] = "application/json"

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = self.session.get(self._url(path), params=params)
        resp.raise_for_status()
        return resp.json()

    # ── Projects ──────────────────────────────────────────────

    def list_projects(self) -> list[dict]:
        return self._get("/rest/api/3/project")

    def get_project(self, project_key: str) -> dict:
        return self._get(f"/rest/api/3/project/{project_key}")

    # ── Issues / JQL ──────────────────────────────────────────

    def search_issues(
        self, jql: str, fields: str = "*navigable", max_results: int = 50, start_at: int = 0
    ) -> dict:
        return self._get(
            "/rest/api/3/search/jql",
            params={
                "jql": jql,
                "fields": fields,
                "maxResults": max_results,
                "startAt": start_at,
            },
        )

    def get_issue(self, issue_key: str, fields: str = "*all") -> dict:
        return self._get(f"/rest/api/3/issue/{issue_key}", params={"fields": fields})

    # ── Boards (Agile API) ────────────────────────────────────
    # Requires Jira Software scope in the OAuth app.
    # Falls back to JQL-based queries if scope is missing.

    def list_boards(self, project_key: str | None = None, max_results: int = 50) -> dict:
        params: dict = {"maxResults": max_results}
        if project_key:
            params["projectKeyOrId"] = project_key
        return self._get("/rest/agile/1.0/board", params=params)

    def get_board(self, board_id: int) -> dict:
        return self._get(f"/rest/agile/1.0/board/{board_id}")

    # ── Sprints ───────────────────────────────────────────────

    def list_sprints(
        self, board_id: int, state: str | None = None, max_results: int = 50
    ) -> dict:
        params: dict = {"maxResults": max_results}
        if state:
            params["state"] = state
        return self._get(f"/rest/agile/1.0/board/{board_id}/sprint", params=params)

    def get_sprint(self, sprint_id: int) -> dict:
        return self._get(f"/rest/agile/1.0/sprint/{sprint_id}")

    def get_sprint_issues(self, sprint_id: int, max_results: int = 200) -> dict:
        return self._get(
            f"/rest/agile/1.0/sprint/{sprint_id}/issue",
            params={"maxResults": max_results, "fields": "summary,status,assignee,issuetype,timetracking"},
        )

    def get_sprint_report(self, board_id: int, sprint_id: int) -> dict:
        """Fetch sprint report data by getting sprint info and its issues."""
        sprint = self.get_sprint(sprint_id)
        issues = self.get_sprint_issues(sprint_id)
        return {"sprint": sprint, "issues": issues}

    def get_velocity_chart(self, board_id: int) -> dict:
        """Build velocity data from recent closed sprints."""
        sprints_data = self.list_sprints(board_id, state="closed", max_results=10)
        return {"sprints": sprints_data.get("values", []), "board_id": board_id}

    # ── Sprint queries via JQL (no Agile API scope needed) ────

    def search_sprint_issues_jql(self, sprint_name: str, project_key: str | None = None, max_results: int = 200) -> dict:
        """Search for issues in a sprint by name using JQL."""
        jql = f'sprint = "{sprint_name}"'
        if project_key:
            jql += f' AND project = "{project_key}"'
        return self.search_issues(jql, fields="summary,status,assignee,issuetype,timetracking", max_results=max_results)

    def search_active_sprint_issues(self, project_key: str, max_results: int = 200) -> dict:
        """Get issues in the active sprint for a project using JQL."""
        jql = f'project = "{project_key}" AND sprint in openSprints()'
        return self.search_issues(jql, fields="summary,status,assignee,issuetype,timetracking", max_results=max_results)

    # ── Worklogs ──────────────────────────────────────────────

    def get_issue_worklogs(self, issue_key: str) -> dict:
        return self._get(f"/rest/api/3/issue/{issue_key}/worklog")

    def get_updated_worklogs(self, since_timestamp: int) -> dict:
        """Get worklog IDs updated after a Unix timestamp (millis)."""
        return self._get("/rest/api/3/worklog/updated", params={"since": since_timestamp})

    def get_worklogs_by_ids(self, worklog_ids: list[int]) -> list[dict]:
        """Fetch full worklog objects by their IDs."""
        resp = self.session.post(
            self._url("/rest/api/3/worklog/list"),
            json={"ids": worklog_ids},
        )
        resp.raise_for_status()
        return resp.json()

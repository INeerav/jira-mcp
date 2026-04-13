"""Atlassian OAuth 2.0 (3LO) authorization flow and token management."""

import json
import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import truststore
truststore.inject_into_ssl()

import requests

TOKEN_FILE = Path(__file__).parent.parent.parent / ".tokens.json"

ATLASSIAN_AUTH_URL = "https://auth.atlassian.com/authorize"
ATLASSIAN_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
ATLASSIAN_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"


def _get_config() -> tuple[str, str, str]:
    """Return (client_id, client_secret, redirect_uri) from env."""
    client_id = os.environ["ATLASSIAN_CLIENT_ID"]
    client_secret = os.environ["ATLASSIAN_CLIENT_SECRET"]
    redirect_uri = os.environ.get("ATLASSIAN_REDIRECT_URI", "http://localhost:9191/callback")
    return client_id, client_secret, redirect_uri


def save_tokens(data: dict) -> None:
    """Persist tokens to disk."""
    TOKEN_FILE.write_text(json.dumps(data, indent=2))


def load_tokens() -> dict | None:
    """Load tokens from disk, or None if not found."""
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def exchange_code(code: str) -> dict:
    """Exchange authorization code for access + refresh tokens."""
    client_id, client_secret, redirect_uri = _get_config()
    resp = requests.post(
        ATLASSIAN_TOKEN_URL,
        json={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    """Use a refresh token to get a new access token."""
    client_id, client_secret, _ = _get_config()
    resp = requests.post(
        ATLASSIAN_TOKEN_URL,
        json={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()


def get_cloud_id(access_token: str) -> str:
    """Fetch the Jira Cloud ID for the authorized site."""
    resp = requests.get(
        ATLASSIAN_RESOURCES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    resp.raise_for_status()
    resources = resp.json()
    if not resources:
        raise RuntimeError("No accessible Atlassian sites found for this token.")
    # Use first site, or match by URL if multiple
    return resources[0]["id"]


def get_valid_token() -> tuple[str, str]:
    """Return (access_token, cloud_id), refreshing if needed.

    Raises RuntimeError if no tokens exist (run login flow first).
    """
    tokens = load_tokens()
    if not tokens:
        raise RuntimeError(
            "Not authenticated. Run `jira-mcp-login` to authorize."
        )

    access_token = tokens["access_token"]
    cloud_id = tokens.get("cloud_id", "")

    # Try the token; if 401, refresh
    test = requests.get(
        ATLASSIAN_RESOURCES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if test.status_code == 401:
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("Token expired and no refresh token. Run `jira-mcp-login` again.")
        new_tokens = refresh_access_token(refresh_token)
        access_token = new_tokens["access_token"]
        # Preserve refresh token if not returned
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token
        new_tokens["cloud_id"] = cloud_id or get_cloud_id(access_token)
        save_tokens(new_tokens)
        return new_tokens["access_token"], new_tokens["cloud_id"]

    if not cloud_id:
        cloud_id = get_cloud_id(access_token)
        tokens["cloud_id"] = cloud_id
        save_tokens(tokens)

    return access_token, cloud_id


# ── Login CLI ─────────────────────────────────────────────────────────────────


def login():
    """Run the interactive OAuth login flow.

    1. Opens browser to Atlassian consent page.
    2. Starts local server on :9191 to capture the callback.
    3. Exchanges the code for tokens and saves them.
    """
    client_id, client_secret, redirect_uri = _get_config()

    scopes = "read:jira-work manage:jira-project manage:jira-configuration read:jira-user write:jira-work manage:jira-webhook manage:jira-data-provider offline_access"

    auth_url = (
        f"{ATLASSIAN_AUTH_URL}"
        f"?audience=api.atlassian.com"
        f"&client_id={client_id}"
        f"&scope={scopes.replace(' ', '%20')}"
        f"&redirect_uri={redirect_uri.replace(':', '%3A').replace('/', '%2F')}"
        f"&state=jira-mcp-login"
        f"&response_type=code"
        f"&prompt=consent"
    )

    captured_code = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal captured_code
            query = parse_qs(urlparse(self.path).query)
            captured_code = query.get("code", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            if captured_code:
                self.wfile.write(b"<h1>Authorized!</h1><p>You can close this tab and return to the terminal.</p>")
            else:
                error = query.get("error", ["unknown"])[0]
                self.wfile.write(f"<h1>Error: {error}</h1>".encode())

        def log_message(self, format, *args):
            pass  # Suppress request logs

    parsed = urlparse(redirect_uri)
    port = parsed.port or 9191

    server = HTTPServer(("localhost", port), CallbackHandler)

    print(f"Opening browser for Atlassian authorization...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print(f"Waiting for callback on localhost:{port}...")
    server.handle_request()
    server.server_close()

    if not captured_code:
        print("ERROR: No authorization code received.", file=sys.stderr)
        sys.exit(1)

    print("Exchanging code for tokens...")
    token_data = exchange_code(captured_code)

    access_token = token_data["access_token"]
    cloud_id = get_cloud_id(access_token)
    token_data["cloud_id"] = cloud_id

    save_tokens(token_data)
    print(f"Authenticated successfully! Cloud ID: {cloud_id}")
    print(f"Tokens saved to {TOKEN_FILE}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    login()

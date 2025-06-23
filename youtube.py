import os
import logging
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube"]

TOKEN_FILE_ENV = "YOUTUBE_TOKEN_FILE"
DEFAULT_TOKEN_PATH = "youtube_token.json"


def _credentials_from_env() -> Optional[Credentials]:
    """Return credentials built from environment variables if available."""
    refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    if refresh_token and client_id and client_secret:
        return Credentials(
            token=os.getenv("YOUTUBE_ACCESS_TOKEN"),
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
    return None


def _credentials_from_file(token_path: str) -> Optional[Credentials]:
    """Load stored credentials from ``token_path`` if it exists."""
    if os.path.exists(token_path):
        return Credentials.from_authorized_user_file(token_path, SCOPES)
    return None


def _run_oauth_flow(token_path: str) -> Credentials:
    """Prompt the user to authorize and store resulting credentials."""
    client_id = os.getenv("YOUTUBE_CLIENT_ID")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET required for OAuth")

    config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    credentials = flow.run_console()
    with open(token_path, "w") as f:
        f.write(credentials.to_json())
    logger.info("Saved YouTube credentials to %s", token_path)
    return credentials


def get_credentials() -> Credentials:
    """Return valid OAuth credentials, prompting the user if necessary."""
    token_path = os.getenv(TOKEN_FILE_ENV, DEFAULT_TOKEN_PATH)

    credentials = _credentials_from_env()
    if not credentials:
        credentials = _credentials_from_file(token_path)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            credentials = _run_oauth_flow(token_path)

    return credentials

def update_stream_title(broadcast_id: str, title: str) -> None:
    """Update the YouTube broadcast title."""
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    body: dict[str, Any] = {
        "id": broadcast_id,
        "snippet": {"title": title},
    }
    youtube.liveBroadcasts().update(part="snippet", body=body).execute()
    logger.info("Updated broadcast %s title to '%s'", broadcast_id, title)


def get_active_broadcast_id() -> str:
    """Return the ID of the authenticated user's active broadcast."""
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    response = (
        youtube.liveBroadcasts()
        .list(part="id", broadcastStatus="active", mine=True, maxResults=1)
        .execute()
    )
    items = response.get("items", [])
    if not items:
        raise ValueError("No active broadcasts found")
    broadcast_id = items[0]["id"]
    logger.info("Retrieved active broadcast ID %s", broadcast_id)
    return broadcast_id


def ensure_authenticated() -> None:
    """Prompt for OAuth if no valid credentials are present."""
    get_credentials()


__all__ = ["update_stream_title", "get_active_broadcast_id", "ensure_authenticated", "get_credentials"]


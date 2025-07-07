import os
import time
import json
import logging
import requests
import base64
from msal import ConfidentialClientApplication
from dotenv import load_dotenv, set_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bvc_bot_auth")

# Load .env
load_dotenv()
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")

# Environment variables
CLIENT_ID = os.getenv("BVC_ONENOTE_INGEST_BOT_ID")
CLIENT_SECRET = os.getenv("BVC_ONENOTE_INGEST_BOT_KEY")
BOT_USERNAME = os.getenv("BVC_SERVICE_BOT_NAME")
BOT_PASSWORD = os.getenv("BVC_SERVICE_BOT_PW")
REFRESH_TOKEN = os.getenv("BVC_BOT_REFRESH_TOKEN")
ACCESS_TOKEN = os.getenv("BVC_BOT_ACCESS_TOKEN")
TENANT_ID = os.getenv("TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default", "offline_access"]

def save_env_var(key, value):
    """Update a key in the .env file, always writing the value without surrounding single quotes."""
    # Remove any leading/trailing single or double quotes
    if isinstance(value, str):
        value = value.strip("'\"")
    set_key(ENV_PATH, key, value)

def is_token_valid(token: str) -> bool:
    """Check if the JWT access token is still valid (not expired)."""
    if not token:
        return False
    try:
        payload = token.split('.')[1]
        # Add padding if needed
        payload += '=' * (-len(payload) % 4)
        decoded = json.loads(
            base64.urlsafe_b64decode(payload.encode('utf-8')).decode('utf-8')
        )
        exp = decoded.get("exp")
        if not exp:
            return False
        # 2 min safety margin
        return int(exp) > int(time.time()) + 120
    except Exception as e:
        logger.warning(f"Could not decode token: {e}")
        return False

def refresh_access_token():
    """Use the refresh token to get a new access token (and refresh token if provided)."""
    logger.info("Refreshing access token using refresh token...")
    token_url = f"{AUTHORITY}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": os.getenv("BVC_BOT_REFRESH_TOKEN"),
        "scope": " ".join(SCOPE),
    }
    resp = requests.post(token_url, data=data)
    if resp.status_code != 200:
        logger.error(f"Failed to refresh token: {resp.status_code} {resp.text}")
        logger.error("Admin action required: Please re-run the interactive OAuth consent process.")
        return None, None
    tokens = resp.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if access_token:
        save_env_var("BVC_BOT_ACCESS_TOKEN", access_token)
        logger.info("Updated access token in .env")
    if refresh_token:
        save_env_var("BVC_BOT_REFRESH_TOKEN", refresh_token)
        logger.info("Updated refresh token in .env")
    return access_token, refresh_token

def get_graph_access_token() -> str:
    """Return a valid access token, refreshing if needed."""
    token = os.getenv("BVC_BOT_ACCESS_TOKEN")
    if is_token_valid(token):
        logger.info("Using cached access token.")
        return token
    logger.info("Access token expired or missing, attempting refresh...")
    access_token, _ = refresh_access_token()
    if access_token:
        return access_token
    raise RuntimeError("Could not obtain a valid access token. Admin action required.")

def graph_api_request(method, url, **kwargs):
    """Make a Microsoft Graph API request with automatic token management."""
    token = get_graph_access_token()
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    headers["Accept"] = "application/json"
    resp = requests.request(method, url, headers=headers, **kwargs)
    if resp.status_code == 401:
        logger.warning("Access token rejected, attempting one refresh...")
        # Try one refresh
        token, _ = refresh_access_token()
        if not token:
            raise RuntimeError("Token refresh failed. Admin action required.")
        headers["Authorization"] = f"Bearer {token}"
        resp = requests.request(method, url, headers=headers, **kwargs)
    if resp.status_code >= 400:
        logger.error(f"Graph API error: {resp.status_code} {resp.text}")
        resp.raise_for_status()
    return resp.json()

# Example usage: List SharePoint/OneNote notebooks
def list_tenant_notebooks():
    url = "https://graph.microsoft.com/v1.0/sites?search=*"
    return graph_api_request("GET", url)

if __name__ == "__main__":
    # Test: print the first site returned
    try:
        sites = list_tenant_notebooks()
        print(json.dumps(sites, indent=2))
    except Exception as e:
        logger.error(f"Test failed: {e}") 
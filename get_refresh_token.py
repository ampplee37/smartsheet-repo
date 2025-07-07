# get_refresh_token.py

import os
import msal

# ────────────────────────────────────────────────────────────────
# CONFIGURATION — public client device code flow (no client secret)
# ────────────────────────────────────────────────────────────────
CLIENT_ID   = "01052a2f-f52d-43d9-bd4b-ae505f839068"   # BVC OneNote Ingest Bot App ID
TENANT_ID   = "6418c11d-cf50-40f7-af02-05178e09a358"   # Azure AD Tenant ID
AUTHORITY   = f"https://login.microsoftonline.com/{TENANT_ID}"
# Only include your resource scopes here; MSAL auto-adds openid, profile, offline_access
SCOPES      = [
    "https://graph.microsoft.com/User.Read",            # sign-in + read user profile
    "https://graph.microsoft.com/Notes.ReadWrite.All",  # OneNote delegated permission
]  # use full resource scopes; MSAL will auto-add openid/profile/offline_access

# Create a PublicClientApplication for device code flow
app = msal.PublicClientApplication(
    client_id=CLIENT_ID,
    authority=AUTHORITY
)

# 1) Kick off device code flow
flow = app.initiate_device_flow(scopes=SCOPES)
if "user_code" not in flow:
    raise RuntimeError(f"Failed to initiate device flow: {flow}")
print(flow["message"])  # instructs user to visit URL + enter code

# 2) Acquire tokens (blocks until user completes browser auth)
result = app.acquire_token_by_device_flow(flow)

# 3) Inspect full response
print("\nResult:\n", result)

# 4) Capture refresh token
if "refresh_token" in result:
    print("\n✅ Refresh token:\n", result["refresh_token"])
else:
    print(
        "\n❌ No refresh token returned. "
        "Ensure 'Allow public client flows' is enabled, and your scopes are resource-based."
    )

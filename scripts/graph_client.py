"""
graph_client.py

What it does: Signs in to Microsoft Graph as the havlund-drift-check app
and gets an access token. The app only has read permissions (User.Read.All,
GroupMember.Read.All). Other scripts reuse this sign-in. Run it on its own
to test.

Inputs: .env file (ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CERT_THUMBPRINT,
        ENTRA_PRIVATE_KEY_PATH)
Outputs: when run directly, prints every Entra user, their employee ID,
         whether the account is on, and whether it's synced from AD
How to run: python scripts/graph_client.py
"""

import os

import msal
import requests
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("ENTRA_TENANT_ID")
CLIENT_ID = os.getenv("ENTRA_CLIENT_ID")
THUMBPRINT = os.getenv("ENTRA_CERT_THUMBPRINT")
KEY_PATH = os.getenv("ENTRA_PRIVATE_KEY_PATH")
GRAPH = "https://graph.microsoft.com/v1.0"

if not all([TENANT_ID, CLIENT_ID, THUMBPRINT, KEY_PATH]):
    raise SystemExit("Missing an ENTRA_ setting in .env. Check all 4 lines are filled in.")


def get_graph_token():
    """Sign in with the certificate and get a short-lived access token."""
    with open(KEY_PATH) as key_file:
        private_key = key_file.read()

    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        client_credential={"private_key": private_key, "thumbprint": THUMBPRINT},
    )
    # .default = use the permissions an admin already granted to this app
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise SystemExit(f"Sign-in failed: {result.get('error')}: {result.get('error_description')}")
    return result["access_token"]


def graph_get_all(path, token, params=None):
    """Read every page of results from Graph (it returns 100 at a time)."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH}{path}"
    items = []
    while url:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if not response.ok:
            raise SystemExit(f"Graph GET {path} failed ({response.status_code}): {response.text}")
        data = response.json()
        items += data.get("value", [])
        url = data.get("@odata.nextLink")  # next page, if there is one
        params = None  # the next page link already has the filters in it
    return items


if __name__ == "__main__":
    token = get_graph_token()
    print("Signed in to Microsoft Graph as the havlund-drift-check app.")

    users = graph_get_all(
        "/users",
        token,
        {"$select": "displayName,userPrincipalName,employeeId,accountEnabled,onPremisesSyncEnabled"},
    )
    print(f"Users found: {len(users)}")
    for user in users:
        state = "on" if user.get("accountEnabled") else "off"
        source = "synced from AD" if user.get("onPremisesSyncEnabled") else "cloud-only"
        print(f"- {user['userPrincipalName']} (employee ID {user.get('employeeId') or 'none'}, {state}, {source})")
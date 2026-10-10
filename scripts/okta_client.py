"""
okta_client.py

What it does: Signs in to Okta as the havlund-hr-sync service app and gets
an access token. Other scripts reuse this sign-in. Run it on its own to test.

Inputs: .env file (OKTA_ORG_URL, OKTA_CLIENT_ID, OKTA_PRIVATE_KEY_PATH)
Outputs: when run directly, prints every user in Okta and their status
How to run: python scripts/okta_client.py
"""

import os
import time
import uuid

import jwt
import requests
from dotenv import load_dotenv

load_dotenv()

ORG_URL = os.getenv("OKTA_ORG_URL")
CLIENT_ID = os.getenv("OKTA_CLIENT_ID")
KEY_PATH = os.getenv("OKTA_PRIVATE_KEY_PATH")
TOKEN_URL = f"{ORG_URL}/oauth2/v1/token"
SCOPES = "okta.users.read okta.users.manage okta.groups.read okta.groups.manage"

if not all([ORG_URL, CLIENT_ID, KEY_PATH]):
    raise SystemExit("Missing a setting in .env. Check all 3 lines are filled in.")


def get_access_token():
    """Sign in to Okta with the private key and get a short-lived access token."""
    with open(KEY_PATH) as key_file:
        private_key = key_file.read()

    now = int(time.time())
    claims = {
        "iss": CLIENT_ID,          # who is asking (the app)
        "sub": CLIENT_ID,          # who it is about (also the app)
        "aud": TOKEN_URL,          # who it is for (Okta's sign-in address)
        "iat": now,                # created now
        "exp": now + 300,          # expires in 5 minutes
        "jti": str(uuid.uuid4()),  # random ID so it can't be reused
    }
    signed_request = jwt.encode(claims, private_key, algorithm="RS256")

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "scope": SCOPES,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": signed_request,
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise SystemExit(f"Sign-in failed ({response.status_code}): {response.text}")
    return response.json()["access_token"]


if __name__ == "__main__":
    token = get_access_token()
    print("Signed in to Okta as the havlund-hr-sync app.")

    response = requests.get(
        f"{ORG_URL}/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    users = response.json()

    print(f"Users found: {len(users)}")
    for user in users:
        print(f"- {user['profile']['login']} ({user['status']})")
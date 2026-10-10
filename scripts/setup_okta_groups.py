"""
setup_okta_groups.py

What it does: Reads the groups in okta/access_rules.json and creates any
that are missing in Okta. Groups that already exist are skipped, so it is
safe to run more than once.

Inputs: okta/access_rules.json, .env (through okta_client)
Outputs: prints what it created or skipped
How to run:
  python scripts/setup_okta_groups.py --dry-run   (shows what would happen)
  python scripts/setup_okta_groups.py             (makes the changes)
"""

import json
import sys
from pathlib import Path

import requests

from okta_client import ORG_URL, get_access_token

RULES_FILE = Path(__file__).resolve().parent.parent / "okta" / "access_rules.json"
DRY_RUN = "--dry-run" in sys.argv


def main():
    rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    wanted = rules["groups"]

    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Accept": "application/json",
    }

    # Ask Okta for the groups it already has (GET = read, no body)
    response = requests.get(
        f"{ORG_URL}/api/v1/groups",
        headers=headers,
        params={"limit": 200},
        timeout=30,
    )
    response.raise_for_status()
    existing = {group["profile"]["name"] for group in response.json()}

    created = skipped = 0
    for name, description in wanted.items():
        if name in existing:
            print(f"Skipped (already exists): {name}")
            skipped += 1
            continue

        if DRY_RUN:
            print(f"Would create: {name}")
            created += 1
            continue

        # Create the group (POST = create, sends a JSON body)
        response = requests.post(
            f"{ORG_URL}/api/v1/groups",
            headers=headers,
            json={"profile": {"name": name, "description": description}},
            timeout=30,
        )
        if not response.ok:
            raise SystemExit(f"Failed to create {name} ({response.status_code}): {response.text}")
        print(f"Created: {name}")
        created += 1

    if DRY_RUN:
        print(f"\nDry run: would create {created}, skip {skipped}. Nothing was changed.")
    else:
        print(f"\nCreated {created}, skipped {skipped}.")


if __name__ == "__main__":
    main()
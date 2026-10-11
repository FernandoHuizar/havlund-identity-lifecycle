"""
hr_to_okta.py

What it does: Reads the HR export and creates new hires (joiners) in Okta
with the right username, job info, and groups. People already in Okta are
matched by employee ID and left alone for now (movers and leavers come next).

Inputs: sample-data/hr_export.csv, okta/access_rules.json, .env
Outputs: prints what it created or skipped
How to run:
  python scripts/hr_to_okta.py --dry-run   (shows what would happen)
  python scripts/hr_to_okta.py             (makes the changes)
"""

import csv
import json
import re
import sys
from pathlib import Path

import requests

from okta_client import ORG_URL, get_access_token

PROJECT = Path(__file__).resolve().parent.parent
HR_FILE = PROJECT / "sample-data" / "hr_export.csv"
RULES_FILE = PROJECT / "okta" / "access_rules.json"
DOMAIN = "havlundpharma.com"
DRY_RUN = "--dry-run" in sys.argv

# Okta pilot: only these departments go into Okta for now (free plan user limit)
PILOT_DEPARTMENTS = {"IT", "Quality"}


def load_hr_records():
    with open(HR_FILE, newline="", encoding="utf-8") as hr_file:
        return list(csv.DictReader(hr_file))


def okta_get(path, headers, params=None):
    """Read something from Okta (GET). Stops with Okta's error message if it fails."""
    response = requests.get(f"{ORG_URL}{path}", headers=headers, params=params, timeout=30)
    if not response.ok:
        raise SystemExit(f"Okta request failed ({response.status_code}): {response.text}")
    return response.json()


def get_okta_users(headers):
    """All Okta users, including deactivated ones, so old usernames stay retired."""
    users = okta_get("/api/v1/users", headers, {"limit": 200})
    users += okta_get("/api/v1/users", headers, {"limit": 200, "search": 'status eq "DEPROVISIONED"'})
    return users


def make_username(record, taken):
    """first.last@domain, all lowercase. If it was ever used, add a number."""
    first = re.sub(r"[^a-z]", "", record["first_name"].lower())
    last = re.sub(r"[^a-z]", "", record["last_name"].lower())
    base = f"{first}.{last}"
    login = f"{base}@{DOMAIN}"
    number = 2
    while login in taken:
        login = f"{base}{number}@{DOMAIN}"
        number += 1
    return login


def groups_for(record, rules):
    """Day-one groups for the job title, plus the contractor group if needed."""
    groups = list(rules["role_groups"][record["job_title"]])
    if record["employee_type"] == "Contractor":
        groups.append(rules["contractor_group"])
    return groups


def main():
    records = load_hr_records()
    rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Accept": "application/json",
    }

    # What Okta has right now
    okta_users = get_okta_users(headers)
    by_employee_id = {
        u["profile"]["employeeNumber"]: u
        for u in okta_users
        if u["profile"].get("employeeNumber")
    }
    taken = {u["profile"]["login"].lower() for u in okta_users}
    group_ids = {
        g["profile"]["name"]: g["id"]
        for g in okta_get("/api/v1/groups", headers, {"limit": 200})
    }

    pilot = [r for r in records if r["department"] in PILOT_DEPARTMENTS and r["status"] == "Active"]
    created = skipped = 0

    for record in sorted(pilot, key=lambda r: int(r["employee_id"])):
        employee_id = record["employee_id"]

        # Match on employee ID, never on name
        if employee_id in by_employee_id:
            login = by_employee_id[employee_id]["profile"]["login"]
            print(f"Skipped (already in Okta): {employee_id} {login}")
            skipped += 1
            continue

        login = make_username(record, taken)
        taken.add(login)
        groups = groups_for(record, rules)

        if DRY_RUN:
            print(f"Would create: {employee_id} {login} -> {', '.join(groups)}")
            created += 1
            continue

        profile = {
            "firstName": record["first_name"],
            "lastName": record["last_name"],
            "email": login,
            "login": login,
            "employeeNumber": employee_id,
            "title": record["job_title"],
            "department": record["department"],
            "userType": record["employee_type"],
            "managerId": record["manager_id"],
        }
        new_user = {
            "profile": {field: value for field, value in profile.items() if value},
            "groupIds": [group_ids[name] for name in groups],
        }

        # Create the user and add them to their groups in one call
        response = requests.post(
            f"{ORG_URL}/api/v1/users",
            headers=headers,
            params={"activate": "true"},
            json=new_user,
            timeout=30,
        )
        if not response.ok:
            raise SystemExit(f"Failed to create {login} ({response.status_code}): {response.text}")
        print(f"Created: {employee_id} {login} -> {', '.join(groups)}")
        created += 1

    if DRY_RUN:
        print(f"\nDry run: would create {created}, skip {skipped}. Nothing was changed.")
    else:
        print(f"\nCreated {created}, skipped {skipped}.")


if __name__ == "__main__":
    main()
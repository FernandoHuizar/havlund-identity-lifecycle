"""
hr_to_okta.py

What it does: Reads the HR export and keeps Okta in line with it.
- Joiners: new hires are created with the right username, job info, and groups.
- Movers: if HR changes someone's job, their Okta profile and groups are updated.
  Old groups are removed first, then new ones added, so no leftover access.
- Leavers: if HR marks someone as no longer active, or a contractor's end date
  has passed, all their groups are removed and their account is deactivated.
  Accounts are never deleted.
- Rehires: if someone comes back (active in HR with a start date after their
  account was turned off), the same account is turned back on with only the
  groups for their new job. If the start date is older, a person reviews it.
People are always matched on employee ID, never on name.

Inputs: sample-data/hr_export.csv, okta/access_rules.json, .env
Outputs: prints what it created, updated, offboarded, rehired, or left alone
How to run:
  python scripts/hr_to_okta.py --dry-run   (shows what would happen)
  python scripts/hr_to_okta.py             (makes the changes)
"""

import csv
import json
import re
import sys
from datetime import date
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


def is_active(record, today=None):
    """Active in HR and, for anyone with an end date, the end date hasn't passed.
    The end date is their last working day, so access ends the day after.
    This catches contractors whose contract ended but HR never marked them."""
    today = today or date.today()
    if record["status"] != "Active":
        return False
    return not (record["end_date"] and date.fromisoformat(record["end_date"]) < today)


def leaver_reason(record):
    """Why someone counts as a leaver, in plain words for the output."""
    if record["status"] != "Active":
        return f"HR status {record['status']}, end date {record['end_date'] or 'none'}"
    return f"contract ended {record['end_date']}"


def okta_request(method, path, headers, params=None, body=None):
    """Send one request to Okta. Stops with Okta's error message if it fails."""
    response = requests.request(
        method,
        f"{ORG_URL}{path}",
        headers=headers,
        params=params,
        json=body,
        timeout=30,
    )
    if not response.ok:
        raise SystemExit(f"Okta {method} {path} failed ({response.status_code}): {response.text}")
    return response.json() if response.content else None


def get_okta_users(headers):
    """All Okta users, including deactivated ones, so old usernames stay retired."""
    users = okta_request("GET", "/api/v1/users", headers, {"limit": 200})
    users += okta_request("GET", "/api/v1/users", headers, {"limit": 200, "search": 'status eq "DEPROVISIONED"'})
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


def profile_from_hr(record):
    """The Okta profile fields HR owns. Username and email are left out on
    purpose: they are set once when the account is made and never change."""
    profile = {
        "firstName": record["first_name"],
        "lastName": record["last_name"],
        "employeeNumber": record["employee_id"],
        "title": record["job_title"],
        "department": record["department"],
        "userType": record["employee_type"],
        "managerId": record["manager_id"],
    }
    return {field: value for field, value in profile.items() if value}


def current_managed_groups(user_id, managed_groups, headers):
    """The HP- groups a user is in right now."""
    return {
        g["profile"]["name"]
        for g in okta_request("GET", f"/api/v1/users/{user_id}/groups", headers)
        if g["profile"]["name"] in managed_groups
    }


def create_user(record, login, groups, group_ids, headers):
    """Joiner: create the account, turn it on, and add the groups in one call."""
    profile = profile_from_hr(record)
    profile["login"] = login
    profile["email"] = login
    body = {"profile": profile, "groupIds": [group_ids[name] for name in groups]}
    okta_request("POST", "/api/v1/users", headers, params={"activate": "true"}, body=body)


def update_user(okta_user, record, groups, group_ids, managed_groups, headers):
    """Mover: bring an existing user in line with HR. Returns the list of changes."""
    user_id = okta_user["id"]
    changes = []

    # Job info that is different from HR
    wanted = profile_from_hr(record)
    profile_changes = {
        field: value for field, value in wanted.items()
        if okta_user["profile"].get(field) != value
    }
    for field, value in profile_changes.items():
        changes.append(f"{field}: {okta_user['profile'].get(field)} -> {value}")

    # HP- groups they have now vs. what their job should get
    current = current_managed_groups(user_id, managed_groups, headers)
    to_remove = current - set(groups)
    to_add = set(groups) - current
    changes += [f"remove {name}" for name in sorted(to_remove)]
    changes += [f"add {name}" for name in sorted(to_add)]

    if DRY_RUN or not changes:
        return changes

    if profile_changes:
        # POST to a user = partial update (only the fields we send change)
        okta_request("POST", f"/api/v1/users/{user_id}", headers, body={"profile": profile_changes})
    # Remove old access first, so nobody holds old and new groups at the same time
    for name in to_remove:
        okta_request("DELETE", f"/api/v1/groups/{group_ids[name]}/users/{user_id}", headers)
    for name in to_add:
        okta_request("PUT", f"/api/v1/groups/{group_ids[name]}/users/{user_id}", headers)
    return changes


def offboard_user(okta_user, group_ids, managed_groups, headers):
    """Leaver: remove every HP- group, then deactivate the account.
    Deactivating ends all sign-ins and sessions. The account is kept, not
    deleted, so the audit trail stays and the username is never reused."""
    user_id = okta_user["id"]
    current = sorted(current_managed_groups(user_id, managed_groups, headers))
    changes = [f"remove {name}" for name in current] + ["deactivate account"]

    if DRY_RUN:
        return changes

    for name in current:
        okta_request("DELETE", f"/api/v1/groups/{group_ids[name]}/users/{user_id}", headers)
    okta_request("POST", f"/api/v1/users/{user_id}/lifecycle/deactivate", headers)
    return changes


def rehire_user(okta_user, record, groups, group_ids, managed_groups, headers):
    """Rehire: turn the old account back on, then give it the new job's info and
    groups. The leaver step removed every group, so no old access comes back."""
    changes = ["turn account back on"]
    if not DRY_RUN:
        okta_request("POST", f"/api/v1/users/{okta_user['id']}/lifecycle/activate", headers,
                     params={"sendEmail": "false"})
    changes += update_user(okta_user, record, groups, group_ids, managed_groups, headers)
    return changes


def main():
    records = load_hr_records()
    rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    managed_groups = set(rules["groups"])
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
        for g in okta_request("GET", "/api/v1/groups", headers, {"limit": 200})
    }

    pilot = [r for r in records if r["department"] in PILOT_DEPARTMENTS]
    created = updated = offboarded = rehired = unchanged = review = 0

    for record in sorted(pilot, key=lambda r: int(r["employee_id"])):
        employee_id = record["employee_id"]
        okta_user = by_employee_id.get(employee_id)

        # Leaver: HR says this person no longer works here, or their contract ended
        if not is_active(record):
            if okta_user is None or okta_user["status"] == "DEPROVISIONED":
                print(f"No changes: {employee_id} already off ({leaver_reason(record)})")
                unchanged += 1
                continue
            login = okta_user["profile"]["login"]
            changes = offboard_user(okta_user, group_ids, managed_groups, headers)
            print(f"{'Would offboard' if DRY_RUN else 'Offboarded'}: {employee_id} {login} "
                  f"({leaver_reason(record)})")
            for change in changes:
                print(f"      {change}")
            offboarded += 1
            continue

        groups = groups_for(record, rules)

        # Already in Okta (matched on employee ID): check for mover changes
        if okta_user is not None:
            login = okta_user["profile"]["login"]
            if okta_user["status"] == "DEPROVISIONED":
                # Only a new start date after the account was turned off counts as
                # a rehire. Otherwise the account may have been turned off by
                # mistake, so a person checks it instead of the script.
                turned_off_on = okta_user["statusChanged"][:10]
                if record["start_date"] > str(date.today()):
                    print(f"Waiting: {employee_id} {login} is rehired but starts {record['start_date']}. "
                          "No access before then")
                    unchanged += 1
                elif record["start_date"] > turned_off_on:
                    changes = rehire_user(okta_user, record, groups, group_ids, managed_groups, headers)
                    print(f"{'Would rehire' if DRY_RUN else 'Rehired'}: {employee_id} {login} "
                          f"(new start date {record['start_date']}, account was turned off {turned_off_on})")
                    for change in changes:
                        print(f"      {change}")
                    rehired += 1
                else:
                    print(f"Needs review: {employee_id} {login} is Active in HR but turned off in Okta "
                          f"since {turned_off_on}, and the HR start date ({record['start_date']}) is older")
                    review += 1
                continue
            changes = update_user(okta_user, record, groups, group_ids, managed_groups, headers)
            if changes:
                print(f"{'Would update' if DRY_RUN else 'Updated'}: {employee_id} {login}")
                for change in changes:
                    print(f"      {change}")
                updated += 1
            else:
                print(f"No changes: {employee_id} {login}")
                unchanged += 1
            continue

        # Not in Okta yet: joiner
        login = make_username(record, taken)
        taken.add(login)
        if not DRY_RUN:
            create_user(record, login, groups, group_ids, headers)
        print(f"{'Would create' if DRY_RUN else 'Created'}: {employee_id} {login} -> {', '.join(groups)}")
        created += 1

    summary = (f"created {created}, updated {updated}, offboarded {offboarded}, rehired {rehired}, "
               f"no changes {unchanged}, needs review {review}")
    if DRY_RUN:
        print(f"\nDry run: would have {summary}. Nothing was changed.")
    else:
        print(f"\nDone: {summary}.")


if __name__ == "__main__":
    main()
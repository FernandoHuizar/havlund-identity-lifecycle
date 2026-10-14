"""
drift_check.py

What it does: Compares the HR export (the source of truth) with Okta,
Active Directory and Entra ID, and reports anything that doesn't match.
It only reads. It never changes any system, because a person should review
each finding before anything is fixed.

Checks (in every system unless noted):
- LEAVER_STILL_ACTIVE: not active in HR, but the account is still on
- SOD_CONFLICT: in two groups that must never be together
- ORPHAN_ACCOUNT: account is on, but its employee ID isn't in HR
- LEAVER_NOT_MOVED (AD only): leaver is still in a department OU, so the
  leaver cleanup didn't run
- EXTRA_ACCESS: in an HP- group their job shouldn't have
- MISSING_ACCOUNT: active in HR (pilot), but no working account
- MISSING_ACCESS: missing an HP- group their job should have
- PROFILE_MISMATCH: title or department is different from HR
- NO_EMPLOYEE_ID: account (on or off) with no employee ID that isn't an
  approved exception

Inputs: sample-data/hr_export.csv, okta/access_rules.json, .env,
        reports/ad_export.csv (made on HP-DC01 by ad/export_ad_state.ps1)
Outputs: prints the findings and writes reports/drift_report.csv
How to run: python scripts/drift_check.py
"""

import csv
import json
from collections import defaultdict
from datetime import date

from graph_client import get_graph_token, graph_get_all
from okta_client import get_access_token
from hr_to_okta import (
    PILOT_DEPARTMENTS,
    PROJECT,
    RULES_FILE,
    get_okta_users,
    groups_for,
    load_hr_records,
    okta_request,
)

AD_EXPORT_FILE = PROJECT / "reports" / "ad_export.csv"
REPORT_FILE = PROJECT / "reports" / "drift_report.csv"
SEVERITY = {
    "LEAVER_STILL_ACTIVE": "High",
    "SOD_CONFLICT": "High",
    "ORPHAN_ACCOUNT": "High",
    "LEAVER_NOT_MOVED": "Medium",
    "EXTRA_ACCESS": "Medium",
    "MISSING_ACCOUNT": "Medium",
    "MISSING_ACCESS": "Low",
    "PROFILE_MISMATCH": "Low",
    "NO_EMPLOYEE_ID": "Low",
}
SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
SYSTEMS = ["Okta", "AD", "Entra"]


# Each system is read into the same simple shape, so one set of checks
# works for all three: id, login, employee_id, is_on, groups, title,
# department, ou (AD only).

def okta_accounts(managed_groups):
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Accept": "application/json",
    }
    accounts = []
    for user in get_okta_users(headers):
        groups = {
            g["profile"]["name"]
            for g in okta_request("GET", f"/api/v1/users/{user['id']}/groups", headers)
            if g["profile"]["name"] in managed_groups
        }
        accounts.append({
            "id": user["id"],
            "login": user["profile"]["login"],
            "employee_id": user["profile"].get("employeeNumber") or "",
            "is_on": user["status"] != "DEPROVISIONED",
            "groups": groups,
            "title": user["profile"].get("title"),
            "department": user["profile"].get("department"),
        })
    return accounts


def ad_accounts(managed_groups):
    """AD can't be reached from this PC, so this reads the export file made
    on the DC. The export time is printed so you know how fresh it is."""
    if not AD_EXPORT_FILE.exists():
        raise SystemExit("No AD export found. Run ad/export_ad_state.ps1 on HP-DC01 "
                         "and copy the file to reports/ad_export.csv.")
    # utf-8-sig: PowerShell adds an invisible marker at the start of the file
    with open(AD_EXPORT_FILE, newline="", encoding="utf-8-sig") as export:
        rows = list(csv.DictReader(export))
    accounts = []
    for row in rows:
        accounts.append({
            "id": row["username"],
            "login": row["upn"],
            "employee_id": row["employee_id"],
            "is_on": row["enabled"] == "True",
            "groups": {g for g in row["hp_groups"].split(";") if g in managed_groups},
            "title": row["title"],
            "department": row["department"],
            "ou": row["ou"],
        })
    exported_at = rows[0]["exported_at"] if rows else "unknown"
    return accounts, exported_at


def entra_accounts(managed_groups):
    token = get_graph_token()
    users = graph_get_all("/users", token, {
        "$select": "id,userPrincipalName,employeeId,accountEnabled,jobTitle,department",
    })
    # Read the members of each HP- group once, instead of each user's groups
    groups_by_user = defaultdict(set)
    hp_groups = graph_get_all("/groups", token, {
        "$filter": "startswith(displayName,'HP-')",
        "$select": "id,displayName",
    })
    for group in hp_groups:
        if group["displayName"] not in managed_groups:
            continue
        for member in graph_get_all(f"/groups/{group['id']}/members", token, {"$select": "id"}):
            groups_by_user[member["id"]].add(group["displayName"])

    return [{
        "id": user["id"],
        "login": user["userPrincipalName"],
        "employee_id": user.get("employeeId") or "",
        "is_on": bool(user.get("accountEnabled")),
        "groups": groups_by_user[user["id"]],
        "title": user.get("jobTitle"),
        "department": user.get("department"),
    } for user in users]


def check_system(system, accounts, records, rules, exceptions, add):
    """Run every check on one system's accounts."""
    hr_by_id = {r["employee_id"]: r for r in records}
    by_employee_id = {}

    for acct in accounts:
        if acct["id"] in exceptions:
            continue
        login, employee_id, groups = acct["login"], acct["employee_id"], acct["groups"]

        if not employee_id:
            state = "on" if acct["is_on"] else "off"
            add(system, "NO_EMPLOYEE_ID", "", login,
                f"Account is {state} but has no employee ID (ID {acct['id']}). "
                "Remove it or list it as an approved exception.")
            continue

        by_employee_id[employee_id] = acct
        record = hr_by_id.get(employee_id)

        if record is None:
            if acct["is_on"]:
                add(system, "ORPHAN_ACCOUNT", employee_id, login, "Account is on but this employee ID is not in HR.")
            continue

        if record["status"] != "Active":
            if acct["is_on"]:
                add(system, "LEAVER_STILL_ACTIVE", employee_id, login,
                    f"HR status is {record['status']} (end date {record['end_date'] or 'none'}) but the account is still on.")
            if groups:
                add(system, "EXTRA_ACCESS", employee_id, login,
                    f"No longer works here but is still in: {', '.join(sorted(groups))}")
            if "ou" in acct and not acct["ou"].startswith("OU=Disabled Users,"):
                add(system, "LEAVER_NOT_MOVED", employee_id, login,
                    "No longer works here but is still in a department OU. Run the leaver cleanup.")
            continue

        if not acct["is_on"]:
            continue  # reported as MISSING_ACCOUNT below

        expected = set(groups_for(record, rules))
        for name in sorted(groups - expected):
            add(system, "EXTRA_ACCESS", employee_id, login, f"In {name}, which a {record['job_title']} should not have.")
        for name in sorted(expected - groups):
            add(system, "MISSING_ACCESS", employee_id, login, f"Should be in {name} as a {record['job_title']}.")
        for pair in rules["never_together"]:
            if set(pair) <= groups:
                add(system, "SOD_CONFLICT", employee_id, login, f"In both {pair[0]} and {pair[1]}.")
        for field, hr_field in (("title", "job_title"), ("department", "department")):
            if acct[field] != record[hr_field]:
                add(system, "PROFILE_MISMATCH", employee_id, login,
                    f"{field} is '{acct[field]}' in {system} but '{record[hr_field]}' in HR.")

    # Active pilot people in HR with no working account in this system
    for record in records:
        if record["status"] != "Active" or record["department"] not in PILOT_DEPARTMENTS:
            continue
        acct = by_employee_id.get(record["employee_id"])
        if acct is None or not acct["is_on"]:
            login = acct["login"] if acct else ""
            add(system, "MISSING_ACCOUNT", record["employee_id"], login,
                f"Active in HR but has no working account in {system}.")


def main():
    records = load_hr_records()
    rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    managed_groups = set(rules["groups"])
    exceptions = rules.get("approved_exceptions", {})
    findings = []

    def add(system, check, employee_id, login, detail):
        findings.append({
            "check": check,
            "severity": SEVERITY[check],
            "system": system,
            "employee_id": employee_id,
            "login": login,
            "detail": detail,
        })

    okta = okta_accounts(managed_groups)
    ad, ad_exported_at = ad_accounts(managed_groups)
    entra = entra_accounts(managed_groups)
    for system, accounts in (("Okta", okta), ("AD", ad), ("Entra", entra)):
        check_system(system, accounts, records, rules, exceptions, add)

    # Report: worst problems first
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], SYSTEMS.index(f["system"]),
                                 f["check"], f["employee_id"]))
    REPORT_FILE.parent.mkdir(exist_ok=True)
    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as report:
        writer = csv.DictWriter(report, fieldnames=["check", "severity", "system", "employee_id", "login", "detail"])
        writer.writeheader()
        writer.writerows(findings)

    pilot_count = sum(1 for r in records if r["department"] in PILOT_DEPARTMENTS)
    print(f"Drift check {date.today()}: {len(records)} HR records ({pilot_count} in the pilot), "
          f"{len(exceptions)} approved exceptions.")
    print(f"Accounts read: Okta {len(okta)}, AD {len(ad)} (export from {ad_exported_at}), Entra {len(entra)}.\n")
    if not findings:
        print("No drift found.")
    for f in findings:
        print(f"[{f['severity']}] {f['system']} {f['check']}: {f['employee_id'] or '-'} {f['login']}")
        print(f"      {f['detail']}")
    print(f"\n{len(findings)} findings. Report saved to {REPORT_FILE.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
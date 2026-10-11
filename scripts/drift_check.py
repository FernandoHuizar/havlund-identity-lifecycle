"""
drift_check.py

What it does: Compares the HR export (the source of truth) with Okta and
reports anything that doesn't match. It only reads. It never changes Okta,
because a person should review each finding before anything is fixed.

Checks:
- LEAVER_STILL_ACTIVE: not active in HR, but the Okta account is still on
- SOD_CONFLICT: in two groups that must never be together
- ORPHAN_ACCOUNT: Okta account whose employee ID isn't in HR
- EXTRA_ACCESS: in an HP- group their job shouldn't have
- MISSING_ACCOUNT: active in HR (pilot), but no working Okta account
- MISSING_ACCESS: missing an HP- group their job should have
- PROFILE_MISMATCH: title or department is different from HR
- NO_EMPLOYEE_ID: account with no employee ID that isn't an approved exception

Inputs: sample-data/hr_export.csv, okta/access_rules.json, .env
Outputs: prints the findings and writes reports/drift_report.csv
How to run: python scripts/drift_check.py
"""

import csv
import json
from datetime import date

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

REPORT_FILE = PROJECT / "reports" / "drift_report.csv"
SEVERITY = {
    "LEAVER_STILL_ACTIVE": "High",
    "SOD_CONFLICT": "High",
    "ORPHAN_ACCOUNT": "High",
    "EXTRA_ACCESS": "Medium",
    "MISSING_ACCOUNT": "Medium",
    "MISSING_ACCESS": "Low",
    "PROFILE_MISMATCH": "Low",
    "NO_EMPLOYEE_ID": "Low",
}
SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def main():
    records = load_hr_records()
    hr_by_id = {r["employee_id"]: r for r in records}
    rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    managed_groups = set(rules["groups"])
    exceptions = rules.get("approved_exceptions", {})
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Accept": "application/json",
    }

    okta_users = get_okta_users(headers)
    findings = []

    def add(check, employee_id, login, detail):
        findings.append({
            "check": check,
            "severity": SEVERITY[check],
            "employee_id": employee_id,
            "login": login,
            "detail": detail,
        })

    # Part 1: look at every account in Okta
    okta_by_id = {}
    for user in okta_users:
        login = user["profile"]["login"]
        employee_id = user["profile"].get("employeeNumber", "")
        is_on = user["status"] != "DEPROVISIONED"
        groups = {
            g["profile"]["name"]
            for g in okta_request("GET", f"/api/v1/users/{user['id']}/groups", headers)
            if g["profile"]["name"] in managed_groups
        }

        if user["id"] in exceptions:
            continue

        if not employee_id:
            if is_on:
                add("NO_EMPLOYEE_ID", "", login,
                    f"Account is on but has no employee ID (Okta ID {user['id']}). "
                    "Confirm it is an approved admin or service account.")
            continue

        okta_by_id[employee_id] = user
        record = hr_by_id.get(employee_id)

        if record is None:
            if is_on:
                add("ORPHAN_ACCOUNT", employee_id, login, "Account is on but this employee ID is not in HR.")
            continue

        if record["status"] != "Active":
            if is_on:
                add("LEAVER_STILL_ACTIVE", employee_id, login,
                    f"HR status is {record['status']} (end date {record['end_date'] or 'none'}) but the account is still on.")
            if groups:
                add("EXTRA_ACCESS", employee_id, login,
                    f"No longer works here but is still in: {', '.join(sorted(groups))}")
            continue

        if not is_on:
            continue  # reported as MISSING_ACCOUNT in part 2

        expected = set(groups_for(record, rules))
        for name in sorted(groups - expected):
            add("EXTRA_ACCESS", employee_id, login, f"In {name}, which a {record['job_title']} should not have.")
        for name in sorted(expected - groups):
            add("MISSING_ACCESS", employee_id, login, f"Should be in {name} as a {record['job_title']}.")
        for pair in rules["never_together"]:
            if set(pair) <= groups:
                add("SOD_CONFLICT", employee_id, login, f"In both {pair[0]} and {pair[1]}.")
        for okta_field, hr_field in (("title", "job_title"), ("department", "department")):
            if user["profile"].get(okta_field) != record[hr_field]:
                add("PROFILE_MISMATCH", employee_id, login,
                    f"{okta_field} is '{user['profile'].get(okta_field)}' in Okta but '{record[hr_field]}' in HR.")

    # Part 2: active pilot people in HR with no working Okta account
    for record in records:
        if record["status"] != "Active" or record["department"] not in PILOT_DEPARTMENTS:
            continue
        user = okta_by_id.get(record["employee_id"])
        if user is None or user["status"] == "DEPROVISIONED":
            login = user["profile"]["login"] if user else ""
            add("MISSING_ACCOUNT", record["employee_id"], login, "Active in HR but has no working Okta account.")

    # Report: worst problems first
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], f["check"], f["employee_id"]))
    REPORT_FILE.parent.mkdir(exist_ok=True)
    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as report:
        writer = csv.DictWriter(report, fieldnames=["check", "severity", "employee_id", "login", "detail"])
        writer.writeheader()
        writer.writerows(findings)

    pilot_count = sum(1 for r in records if r["department"] in PILOT_DEPARTMENTS)
    print(f"Drift check {date.today()}: {len(records)} HR records ({pilot_count} in the Okta pilot), "
          f"{len(okta_users)} Okta accounts, {len(exceptions)} approved exceptions.\n")
    if not findings:
        print("No drift found.")
    for f in findings:
        print(f"[{f['severity']}] {f['check']}: {f['employee_id'] or '-'} {f['login']}")
        print(f"      {f['detail']}")
    print(f"\n{len(findings)} findings. Report saved to {REPORT_FILE.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
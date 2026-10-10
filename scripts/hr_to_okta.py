"""
hr_to_okta.py

What it does: Reads the HR export and works out what each pilot user should
look like in Okta (username, job info, groups). Part 1 only prints the plan.
Later parts will create, update, and turn off users in Okta.

Inputs: sample-data/hr_export.csv, okta/access_rules.json
Outputs: prints the plan
How to run: python scripts/hr_to_okta.py
"""

import csv
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
HR_FILE = PROJECT / "sample-data" / "hr_export.csv"
RULES_FILE = PROJECT / "okta" / "access_rules.json"
DOMAIN = "havlundpharma.com"

# Okta pilot: only these departments go into Okta for now (free plan user limit)
PILOT_DEPARTMENTS = {"IT", "Quality"}


def load_hr_records():
    with open(HR_FILE, newline="", encoding="utf-8") as hr_file:
        return list(csv.DictReader(hr_file))


def build_usernames(records):
    """first.last@domain, all lowercase. If the name is taken, add a number
    (emily.carter2). Sorted by employee_id so the earliest hire keeps the
    plain name. Built from all HR records, not just the pilot, so the same
    person always gets the same username."""
    usernames = {}
    taken = set()
    for record in sorted(records, key=lambda r: int(r["employee_id"])):
        first = re.sub(r"[^a-z]", "", record["first_name"].lower())
        last = re.sub(r"[^a-z]", "", record["last_name"].lower())
        base = f"{first}.{last}"
        name = base
        number = 2
        while name in taken:
            name = f"{base}{number}"
            number += 1
        taken.add(name)
        usernames[record["employee_id"]] = f"{name}@{DOMAIN}"
    return usernames


def groups_for(record, rules):
    """Day-one groups for the job title, plus the contractor group if needed."""
    groups = list(rules["role_groups"][record["job_title"]])
    if record["employee_type"] == "Contractor":
        groups.append(rules["contractor_group"])
    return groups


def main():
    records = load_hr_records()
    rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    usernames = build_usernames(records)

    pilot = [r for r in records if r["department"] in PILOT_DEPARTMENTS]
    print(f"HR records: {len(records)}. In the Okta pilot: {len(pilot)}.\n")

    for record in pilot:
        print(f"{record['employee_id']}  {usernames[record['employee_id']]}")
        print(f"      {record['job_title']}, {record['employee_type']}, {record['status']}")
        print(f"      Groups: {', '.join(groups_for(record, rules))}\n")

    numbered = [u for u in usernames.values() if re.search(r"\d@", u)]
    print(f"Name clashes handled with a number: {', '.join(numbered) or 'none'}")


if __name__ == "__main__":
    main()
# Build Progress

Where the lab stands right now. Updated as each part is finished.

## Done
- Repo set up with folders for each part of the lab
- Design doc: company, problem, scope, roles, access by role, field map, username rule, AD layout
- Problem log started
- Entra tenant cleaned up and renamed to Havlund Pharma
- havlundpharma.com added and verified as the primary domain
- Azure budget alert set to $10 a month
- Fake HR export (CSV) with 15 employees
- Azure block removed by Microsoft. Subscription havlund-lab created with a $10 budget.
- Okta service app havlund-hr-sync created (private key sign-in, 4 scopes, Org Admin role)
- Okta sign-in script working (scripts/okta_client.py signs in with the private key and lists users)
- Access rules config (okta/access_rules.json) and 9 HP- groups created in Okta by script (safe to rerun)
- Joiner in Okta working: hr_to_okta.py created the 7 pilot users with the right groups, matching on employee ID (safe to rerun)

## Build order
1. HR export (CSV file, like a Workday or ADP feed)
2. HR to Okta: joiner, mover, leaver
3. Drift check, part 1: HR vs Okta
4. Azure VM, Active Directory, Entra Connect
5. Add AD and Entra ID to the joiner, mover, leaver flows and the drift check
6. Contractor expiry and rehire, README, demo
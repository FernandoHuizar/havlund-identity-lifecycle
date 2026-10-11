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
- Mover in Okta working: promoted David Kim (QA Specialist to QA Manager). Script updated his title, removed HP-QA-Edit first, then added HP-QA-Approve
- Leaver in Okta working: terminated Jordan Reyes in HR. Script removed his groups and deactivated his account. Okta System Log shows each step with a time stamp
- Drift check part 1 working: drift_check.py compares HR with Okta and writes reports/drift_report.csv. Admin account listed as an approved exception

## Build order
1. HR export (CSV file, like a Workday or ADP feed)
2. HR to Okta: joiner, mover, leaver
3. Drift check, part 1: HR vs Okta
4. Azure VM, Active Directory, Entra Connect
5. Add AD and Entra ID to the joiner, mover, leaver flows and the drift check
6. Contractor expiry and rehire, README, demo

## Next step
Test the drift check: make 2 to 3 problems in Okta by hand (like an SOD conflict and an orphan account), run drift_check.py to catch them, then fix them.

## Planned: Azure VM (build order step 4)
- Subscription havlund-lab (Havlund Pharma tenant) with a $10 budget.
- VM HP-DC01 in resource group rg-havlund-lab, West US 2, Windows Server 2022 Datacenter Gen2, Standard_B2s, admin user hpadmin.
- No open inbound ports except RDP from my home IP only. Auto-shutdown every night. No Hybrid Benefit. Check the price before clicking Create.
- The disk costs money even when the VM is off, so only build it when step 4 starts. Delete the whole resource group when the lab is done.

## Later
- Add a custom endDate field in Okta for contractor expiry.
- Handle rehires (the sync script flags them as "Needs review" for now).
- Add my Gmail as a backup on the Okta admin account (it uses my Sierra College email).
- Change the havlund-lab budget alert email to my Gmail.